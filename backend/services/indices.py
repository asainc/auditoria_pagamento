"""Gestão das séries delega ao atualizador existente, com exclusão mútua."""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor

from judicial_calc import atualizar_planilhas_drcalc_se_necessario
from judicial_calc.data_sources.local_excel import local_index_coverage, local_index_specs, local_missing_index_specs
from backend.config import ROOT, Settings
from backend.models import IndexOption, IndexStatus
from backend.repository import Repository, timestamp
from backend.services.engine import EngineFacade, file_hashes

logger = logging.getLogger("judicial")


DISPLAY_NAME_OVERRIDES: dict[str, str] = {
    "cesta_basica_sao_paulo": "Cesta básica (São Paulo)",
}

def display_name(key: str, raw_name: str) -> str:
    """Normaliza nomes da lista para o padrão esperado na interface."""
    return DISPLAY_NAME_OVERRIDES.get(key, raw_name)


MONTH_ABBREVIATIONS = ("jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez")


def format_competence(comp: str | None) -> str:
    """Formata ``AAAA-MM`` como ``mmm/AAAA`` sem depender de locale."""
    if not comp or len(comp) < 7:
        return ""
    try:
        month = int(comp[5:7])
    except ValueError:
        return comp
    if not 1 <= month <= 12:
        return comp
    return f"{MONTH_ABBREVIATIONS[month - 1]}/{comp[:4]}"


def display_label(raw_name: str, first: str | None, last: str | None) -> str:
    """Monta rótulo apenas com o intervalo observado na planilha instalada."""
    if not first or not last:
        return raw_name
    return f"{raw_name} ...... ({format_competence(first)} a {format_competence(last)})"


def _public_update_failure(result) -> str:
    """Converte a falha técnica do atualizador em orientação segura para a interface.

    O detalhe integral permanece no log/auditoria. A mensagem pública informa a
    causa operacional sem expor caminhos locais, HTML recebido ou outros dados
    internos que não ajudam a pessoa usuária a decidir o próximo passo.
    """
    details = " ".join([result.message, *result.errors]).lower()
    if "timeout" in details or "timed out" in details or "tempo limite" in details:
        return "O DrCalc não respondeu dentro do tempo limite. As séries anteriores foram preservadas; tente novamente quando a fonte estiver disponível."
    if "name resolution" in details or "resolve" in details or "dns" in details:
        return "Não foi possível acessar o endereço do DrCalc. As séries anteriores foram preservadas; verifique a conectividade do ambiente."
    if "nenhuma série" in details or "nenhum indexador" in details:
        return "O DrCalc respondeu, mas o atualizador não encontrou séries válidas para confirmar a atualização. As séries anteriores foram preservadas."
    if "lock" in details:
        return "Outra atualização pode estar em andamento. As séries anteriores foram preservadas; aguarde alguns instantes e tente novamente."
    return "A atualização externa não pôde ser confirmada. As séries anteriores foram preservadas e continuam disponíveis para cálculo."


class IndexService:
    """Uma atualização por vez, estado verificável e backup fornecido pelo motor."""
    def __init__(self, settings: Settings, repository: Repository, facade: EngineFacade):
        """Recebe dependências explicitamente para manter configuração e testes isolados."""
        self.settings = settings
        self.repository = repository
        self.facade = facade
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="indices")
        previous = self.status()
        if previous.estado == "executando":
            self.save("falha", "Atualização interrompida pelo reinício do serviço.")

    def options(self) -> list[IndexOption]:
        """Lista índices selecionáveis, inclusive séries históricas extintas conhecidas."""
        available = {spec.key: spec for spec in local_index_specs()}
        missing = {spec.key: spec for spec in local_missing_index_specs()}
        ordered_keys = [
            "cesta_basica_sao_paulo",
            "cub_sinduscon_sp",
            "icv_dieese",
            "igp_di_fgv",
            "igp_m_fgv",
            "incc_di_fgv",
            "inpc_ibge",
            "ipa_di_fgv",
            "ipca_ibge",
            "ipca_15_ibge",
            "ipca_e_ibge",
            "ipc_di_fgv",
            "ipc_fipe",
            "ipc_ibge_extinto",
            "ipc_r_ibge_extinto",
            "isn_ibge_extinto",
            "ist_telecomunicacoes",
            "salario_minimo",
            "debitos_judiciais_acoes_acidentarias",
            "encoge_xi_encontro",
            "jf_beneficio_previdenciario_res_267_2013",
            "jf_condenatorias_fazenda_publica",
            "jf_condenatorias_geral_exceto_fazenda_publica",
            "jf_desapropriacoes_res_267_2013",
            "precatorios_acoes_acidentarias_ec_62_2009",
            "tjdf_expurgada",
            "tjmg_expurgada",
            "tjro_sem_expurgos",
            "tjce_condenatorias_tj_ceara",
            "tjdf_nao_expurgada",
            "tjes_tabela_tribunal_just_es",
            "tjmg_nao_expurgada",
            "tjpr_ipca_e_precatorios",
            "tjpr_media_igp_inpc",
            "tjrj_tabela_tribunal_just_rj",
            "tjrs_tabela_tribunal_just_rs_igpm",
            "tjsc_tabela_tribunal_just_sc_icgj",
            "tjsp_inpc_ipca15_lei_14905",
            "tjsp_fazenda_publica_precatorios_ate_25_3_15_cnj_303_selic",
            "tjsp_precatorios_apos_25_3_15_cnj_303_com_selic",
            "tst_debitos_trabalhistas_ipca_e",
            "tst_debitos_trabalhistas_tr",
        ]
        options: list[IndexOption] = [
            IndexOption(
                chave="sem_correcao",
                nome="Sem correção",
                nome_base="Sem correção",
                disponivel=True,
                modo="sem_correcao",
            )
        ]
        for key in ordered_keys:
            spec = available.get(key)
            if spec is not None:
                name = display_name(key, spec.column)
                try:
                    coverage = local_index_coverage(key)
                except (ValueError, FileNotFoundError) as exc:
                    logger.warning("index_coverage_unavailable", extra={"index_key": key, "error_type": type(exc).__name__})
                    options.append(
                        IndexOption(
                            chave=key,
                            nome=f"{name} (série indisponível)",
                            nome_base=name,
                            disponivel=False,
                            modo="indisponivel",
                        )
                    )
                    continue
                options.append(
                    IndexOption(
                        chave=key,
                        nome=display_label(name, coverage.first_competence, coverage.last_competence),
                        nome_base=name,
                        disponivel=True,
                        modo=coverage.mode,
                        competencia_inicial=coverage.first_competence,
                        competencia_final=coverage.last_competence,
                        competencia_maxima_atualizacao=coverage.maximum_update_competence,
                    )
                )
                continue
            missing_spec = missing.get(key)
            if missing_spec is not None:
                name = display_name(key, missing_spec.label)
                options.append(
                    IndexOption(
                        chave=key,
                        nome=f"{name} (série não instalada)",
                        nome_base=name,
                        disponivel=False,
                        modo="indisponivel",
                    )
                )
        return options

    def status(self) -> IndexStatus:
        """Checksum relata o arquivo real; não implica atualidade da série."""
        hashes = file_hashes(ROOT / "src/judicial_calc/data", "*.xlsx")
        with self.repository.connection() as connection:
            row = connection.execute("SELECT payload FROM index_state WHERE id=1").fetchone()
        if not row:
            return IndexStatus(estado="nao_verificado", mensagem="Atualidade das séries ainda não verificada nesta instalação.", arquivos_sha256=hashes)
        status = IndexStatus.model_validate_json(row["payload"])
        status.arquivos_sha256 = hashes
        return status

    def save(self, state: str, message: str) -> IndexStatus:
        """Persiste o estado de atualização para consultas e recuperação."""
        status = IndexStatus(estado=state, mensagem=message, atualizado_em=timestamp(), arquivos_sha256=file_hashes(ROOT / "src/judicial_calc/data", "*.xlsx"))
        with self.repository.connection() as connection:
            connection.execute("INSERT OR REPLACE INTO index_state VALUES(1,?)", (status.model_dump_json(),))
        return status

    def start(self) -> IndexStatus:
        """A trava do processo evita que dois cliques enfileirem atualizações iguais."""
        with self.repository.connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute("SELECT payload FROM index_state WHERE id=1").fetchone()
            if row:
                current = IndexStatus.model_validate_json(row["payload"])
                if current.estado == "executando":
                    return current
            status = IndexStatus(estado="executando", mensagem="Verificando séries e preparando backup.", atualizado_em=timestamp(), arquivos_sha256={})
            connection.execute("INSERT OR REPLACE INTO index_state VALUES(1,?)", (status.model_dump_json(),))
        self.executor.submit(self.run)
        return status

    def run(self) -> None:
        """Atualiza as séries sob a mesma trava usada pelo cálculo.

        ``DrCalcUpdateResult.success`` é a fonte de verdade. A versão anterior
        inferia sucesso a partir de ``executed`` e de uma palavra na mensagem, o
        que podia transformar um resultado válido e ignorado por já estar em dia
        em uma falsa mensagem de falha.
        """
        try:
            with self.facade.lock:
                result = atualizar_planilhas_drcalc_se_necessario(
                    force=False,
                    timeout=self.settings.index_timeout_seconds,
                    strict=False,
                )
                if result.success:
                    disabled = "desativada" in result.message.lower()
                    if disabled:
                        state = "nao_verificado"
                    elif result.executed and not result.has_new_competence:
                        state = "sem_novidade"
                    else:
                        state = "atualizado"
                    message = result.message
                else:
                    state = "falha"
                    message = _public_update_failure(result)

                self.save(state, message)
                self.repository.audit(
                    "indices_update",
                    {
                        "success": result.success,
                        "executed": result.executed,
                        "skipped": result.skipped,
                        "files": len(result.updated_files),
                        "error_count": len(result.errors),
                    },
                )
                if not result.success:
                    logger.warning(
                        "indices_update_not_confirmed",
                        extra={
                            "error_count": len(result.errors),
                            "executed": result.executed,
                            "skipped": result.skipped,
                        },
                    )
        except Exception as exc:
            logger.error("indices_failed", extra={"error_type": type(exc).__name__})
            self.save("falha", "Atualização não concluída. As séries anteriores foram preservadas; verifique a conectividade e tente novamente.")

    def close(self) -> None:
        """Encerra recursos próprios sem interferir em outras instâncias."""
        self.executor.shutdown(wait=True, cancel_futures=True)
