"""Gestão das séries delega ao atualizador existente, com exclusão mútua."""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor

from judicial_calc import atualizar_planilhas_drcalc_se_necessario
from judicial_calc.data_sources.local_excel import local_index_specs, local_missing_index_specs
from backend.config import ROOT, Settings
from backend.models import IndexOption, IndexStatus
from backend.repository import Repository, timestamp
from backend.services.engine import EngineFacade, file_hashes

logger = logging.getLogger("judicial")


DISPLAY_NAME_OVERRIDES: dict[str, str] = {
    "cesta_basica_sao_paulo": "Cesta básica (São Paulo)",
}

DISPLAY_RANGE_OVERRIDES: dict[str, str] = {
    "cesta_basica_sao_paulo": "jan/1965 a jul/2026",
    "cub_sinduscon_sp": "fev/1982 a ago/2026",
    "icv_dieese": "jan/1987 a fev/2020",
    "igp_di_fgv": "fev/1944 a ago/2026",
    "igp_m_fgv": "jun/1989 a ago/2026",
    "incc_di_fgv": "fev/1944 a ago/2026",
    "inpc_ibge": "abr/1979 a ago/2026",
    "ipa_di_fgv": "mar/1944 a ago/2026",
    "ipca_ibge": "jan/1980 a ago/2026",
    "ipca_15_ibge": "mai/2000 a ago/2026",
    "ipca_e_ibge": "dez/1991 a ago/2026",
    "ipc_di_fgv": "jan/1987 a ago/2026",
    "ipc_fipe": "fev/1939 a ago/2026",
    "ipc_ibge_extinto": "mar/1986 a fev/1991",
    "ipc_r_ibge_extinto": "jul/1994 a jul/1996",
    "isn_ibge_extinto": "mar/1991 a abr/1997",
    "ist_telecomunicacoes": "jan/2006 a jul/2026",
    "salario_minimo": "jan/1943 a dez/2026",
    "debitos_judiciais_acoes_acidentarias": "jan/1976 a set/2026",
    "encoge_xi_encontro": "out/1964 a set/2026",
    "jf_beneficio_previdenciario_res_267_2013": "out/1964 a ago/2026",
    "jf_condenatorias_fazenda_publica": "out/1964 a set/2026",
    "jf_condenatorias_geral_exceto_fazenda_publica": "out/1964 a set/2026",
    "jf_desapropriacoes_res_267_2013": "out/1964 a ago/2026",
    "tjdf_expurgada": "out/1964 a ago/2026",
    "tjmg_expurgada": "out/1964 a set/2026",
    "tjce_condenatorias_tj_ceara": "out/1964 a set/2026",
    "tjdf_nao_expurgada": "out/1964 a ago/2026",
    "tjes_tabela_tribunal_just_es": "jan/1969 a ago/2026",
    "tjmg_nao_expurgada": "out/1964 a set/2026",
    "tjpr_ipca_e_precatorios": "mar/1989 a set/2026",
    "tjpr_media_igp_inpc": "out/1964 a ago/2026",
    "tjrj_tabela_tribunal_just_rj": "out/1964 a dez/2026",
    "tjrs_tabela_tribunal_just_rs_igpm": "out/1964 a ago/2026",
    "tjsc_tabela_tribunal_just_sc_icgj": "out/1964 a ago/2026",
    "tjsp_inpc_ipca15_lei_14905": "out/1964 a set/2026",
    "tjsp_fazenda_publica_precatorios_ate_25_3_15_cnj_303_selic": "out/1964 a set/2026",
    "tjsp_precatorios_apos_25_3_15_cnj_303_com_selic": "out/1964 a set/2026",
    "tst_debitos_trabalhistas_ipca_e": "out/1966 a ago/2026",
    "tst_debitos_trabalhistas_tr": "out/1966 a out/2026",
}


def display_name(key: str, raw_name: str) -> str:
    """Normaliza nomes da lista para o padrão esperado na interface."""
    return DISPLAY_NAME_OVERRIDES.get(key, raw_name)


def display_label(key: str, raw_name: str) -> str:
    """Acrescenta o intervalo de disponibilidade quando conhecido."""
    name = display_name(key, raw_name)
    coverage = DISPLAY_RANGE_OVERRIDES.get(key)
    if not coverage:
        return name
    return f"{name} ...... ({coverage})"


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
        options: list[IndexOption] = [IndexOption(chave="sem_correcao", nome="Sem correção")]
        for key in ordered_keys:
            spec = available.get(key)
            if spec is not None:
                options.append(IndexOption(chave=key, nome=display_label(key, spec.column)))
                continue
            missing_spec = missing.get(key)
            if missing_spec is not None:
                options.append(IndexOption(chave=key, nome=display_label(key, missing_spec.label)))
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
                    state = "nao_verificado" if disabled else "atualizado"
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
