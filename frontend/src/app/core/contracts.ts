/** Gerado de docs/openapi.json. Atualize por scripts/generate_contracts.py. */

export type AiUsage = { "etapa": string; "modelo": string; "tokens_entrada"?: number | null; "tokens_entrada_cache"?: number | null; "tokens_saida"?: number | null; "tokens_total"?: number | null; "custo_estimado_usd"?: string | null; "duracao_ms": number; "paginas_contexto"?: number | null; "caracteres_entrada"?: number | null; "correcao_estrutural"?: boolean };

export type AiUsageSummary = { "chamadas": number; "tokens_entrada"?: number | null; "tokens_entrada_cache"?: number | null; "tokens_saida"?: number | null; "tokens_total"?: number | null; "custo_estimado_usd"?: string | null; "duracao_total_ms"?: number; "detalhamento"?: Array<AiUsage> };

export type BatchImport = { "processos": Array<CalculationDraft>; "erros": Array<string> };

export type BatchItem = { "numero_processo": string | null; "resultado"?: VersionedCalculationResponse | null; "erro"?: string | null };

export type BatchRequest = { "processos": Array<CalculationRequest_Input> };

export type BatchResponse = { "resultados": Array<BatchItem> };

export type Body_import_batch_api_v2_lotes_importar_post = { "file": string };

export type Body_import_installments_api_v2_documentos_parcelas_importar_post = { "file": string };

export type Body_upload_api_v2_documentos_upload_post = { "files": Array<string> };

export type CalculationComparison = { "calculo_id": string; "versao_origem": number; "versao_destino": number; "total_origem"?: string | null; "total_destino"?: string | null; "diferenca_total"?: string | null; "diff": CalculationDiff };

export type CalculationDefaults = { "mes": "janeiro" | "fevereiro" | "março" | "abril" | "maio" | "junho" | "julho" | "agosto" | "setembro" | "outubro" | "novembro" | "dezembro"; "ano": number; "competencia_recomendada"?: string | null; "ajustada_por_disponibilidade"?: boolean; "mensagem"?: string | null };

export type CalculationDiff = { "campos"?: Array<CalculationFieldDiff>; "parcelas"?: Array<InstallmentDiff> };

export type CalculationDraft = { "origem_calculo": "manual" | "processo"; "numero_processo"?: string | null; "identificador_calculo"?: string | null; "parcelas": Array<Installment_Output>; "parametros": CalculationParameters_Output; "revisao_humana_confirmada"?: boolean; "honorarios_sobre_danos_morais"?: boolean; "competencia_automatica"?: boolean };

export type CalculationExecutionRef = { "execucao_id": string; "calculo_id": string; "versao": number; "executada_em": string; "nova_versao"?: boolean };

export type CalculationExecutionSummary = { "execucao_id": string; "versao": number; "executada_em": string; "executada_por": string; "entrada_sha256": string; "politica_sha256": string; "motor_sha256": string; "indices_sha256": string; "duracao_ms": number };

export type CalculationExecutionsPage = { "calculo_id": string; "versao": number; "itens": Array<CalculationExecutionSummary>; "pagina": number; "tamanho_pagina": number; "total_itens": number; "total_paginas": number };

export type CalculationFieldDiff = { "caminho": string; "valor_anterior"?: string | number | number | boolean | null; "valor_novo"?: string | number | number | boolean | null };

export type CalculationHistoryItem = { "calculo_id": string; "origem_calculo": "manual" | "processo"; "identificador_calculo": string; "numero_processo"?: string | null; "numero_processo_normalizado"?: string | null; "estado": "ativo" | "arquivado" | "cancelado"; "criado_em": string; "criado_por": string; "atualizado_em": string; "quantidade_versoes": number; "quantidade_execucoes": number; "versao_atual": number; "total_atual"?: string | null; "indice_atual": string; "competencia_atualizacao_atual": string };

export type CalculationHistoryPage = { "itens": Array<CalculationHistoryItem>; "pagina": number; "tamanho_pagina": number; "total_itens": number; "total_paginas": number };

export type CalculationMetadata = { "entrada_sha256": string; "politica_sha256": string; "motor_sha256": string; "indices_sha256": string; "duracao_ms": number; "revisao_humana_confirmada": boolean };

export type CalculationParameters_Input = { "duplo_indice_flag"?: boolean | null; "duplo_indice_primeiro_indice"?: string | null; "duplo_indice_primeiro_data_inicio"?: string | null; "duplo_indice_primeiro_data_fim"?: string | null; "duplo_indice_primeiro_valor_parcela"?: number | string | null; "duplo_indice_segundo_indice"?: string | null; "duplo_indice_segundo_data_inicio"?: string | null; "duplo_indice_segundo_data_fim"?: string | null; "duplo_indice_segundo_valor_parcela"?: number | string | null; "compensacao_flag"?: boolean | null; "compensacao_tipo_calculo"?: "percentual" | "fixo" | null; "compensacao_valor"?: number | string | null; "prescricao_flag"?: boolean | null; "prescricao_anos"?: number | null; "prescricao_data_referencia_tipo"?: "data_ajuizamento" | "data_decisao" | "data_ultima_parcela" | null; "prescricao_data_referencia"?: string | null; "incidir_multa_sobre_juros_compensatorios"?: boolean | null; "incidir_multa_sobre_juros_moratorios"?: boolean | null; "incidir_multa_sobre_parcelas_a_vencer"?: boolean | null; "incidir_honorarios_sobre_multa"?: boolean | null; "multa_valor"?: number | string | null; "multa_tipo"?: "percentual" | "fixo" | null; "honorarios"?: number | string | null; "honorarios_tipo"?: "percentual" | "fixo" | null; "art_523"?: "nao_aplicar" | "aplicar_multa" | "aplicar_multa_honorarios" | null; "juros_moratorios_tipo": "sem_juros" | "capitalizacao_simples" | "capitalizacao_composta" | "juros_moratorios_stj1368_lei_14905" | "taxa_legal_12_aa_6_aa" | "taxa_legal_diaria_selic_ipcae" | "taxa_legal" | "juros_moratorios_ctn_lei_14905"; "juros_moratorios_taxa"?: number | string | null; "juros_moratorios_periodicidade"?: "diaria" | "mensal" | "anual" | null; "juros_moratorios_pro_rata"?: boolean | null; "juros_moratorios_data_inicio"?: string | null; "juros_moratorios_sobre_compensatorios"?: boolean | null; "juros_compensatorios_tipo": "sem_juros" | "capitalizacao_simples" | "capitalizacao_composta" | "juros_moratorios_stj1368_lei_14905" | "taxa_legal_12_aa_6_aa" | "taxa_legal_diaria_selic_ipcae" | "taxa_legal" | "juros_moratorios_ctn_lei_14905"; "juros_compensatorios_taxa"?: number | string | null; "juros_compensatorios_periodicidade"?: "diaria" | "mensal" | "anual" | null; "juros_compensatorios_pro_rata"?: boolean | null; "juros_compensatorios_data_inicio"?: string | null; "mes_atualizacao": "janeiro" | "fevereiro" | "março" | "abril" | "maio" | "junho" | "julho" | "agosto" | "setembro" | "outubro" | "novembro" | "dezembro"; "ano_atualizacao": number; "indice": string; "deflacionar_valor_nominal"?: boolean | null; "competencia_final_taxa_legal"?: string | null; "valor_dobrado_flag"?: boolean | null };

export type CalculationParameters_Output = { "duplo_indice_flag"?: boolean | null; "duplo_indice_primeiro_indice"?: string | null; "duplo_indice_primeiro_data_inicio"?: string | null; "duplo_indice_primeiro_data_fim"?: string | null; "duplo_indice_primeiro_valor_parcela"?: string | null; "duplo_indice_segundo_indice"?: string | null; "duplo_indice_segundo_data_inicio"?: string | null; "duplo_indice_segundo_data_fim"?: string | null; "duplo_indice_segundo_valor_parcela"?: string | null; "compensacao_flag"?: boolean | null; "compensacao_tipo_calculo"?: "percentual" | "fixo" | null; "compensacao_valor"?: string | null; "prescricao_flag"?: boolean | null; "prescricao_anos"?: number | null; "prescricao_data_referencia_tipo"?: "data_ajuizamento" | "data_decisao" | "data_ultima_parcela" | null; "prescricao_data_referencia"?: string | null; "incidir_multa_sobre_juros_compensatorios"?: boolean | null; "incidir_multa_sobre_juros_moratorios"?: boolean | null; "incidir_multa_sobre_parcelas_a_vencer"?: boolean | null; "incidir_honorarios_sobre_multa"?: boolean | null; "multa_valor"?: string | null; "multa_tipo"?: "percentual" | "fixo" | null; "honorarios"?: string | null; "honorarios_tipo"?: "percentual" | "fixo" | null; "art_523"?: "nao_aplicar" | "aplicar_multa" | "aplicar_multa_honorarios" | null; "juros_moratorios_tipo": "sem_juros" | "capitalizacao_simples" | "capitalizacao_composta" | "juros_moratorios_stj1368_lei_14905" | "taxa_legal_12_aa_6_aa" | "taxa_legal_diaria_selic_ipcae" | "taxa_legal" | "juros_moratorios_ctn_lei_14905"; "juros_moratorios_taxa"?: string | null; "juros_moratorios_periodicidade"?: "diaria" | "mensal" | "anual" | null; "juros_moratorios_pro_rata"?: boolean | null; "juros_moratorios_data_inicio"?: string | null; "juros_moratorios_sobre_compensatorios"?: boolean | null; "juros_compensatorios_tipo": "sem_juros" | "capitalizacao_simples" | "capitalizacao_composta" | "juros_moratorios_stj1368_lei_14905" | "taxa_legal_12_aa_6_aa" | "taxa_legal_diaria_selic_ipcae" | "taxa_legal" | "juros_moratorios_ctn_lei_14905"; "juros_compensatorios_taxa"?: string | null; "juros_compensatorios_periodicidade"?: "diaria" | "mensal" | "anual" | null; "juros_compensatorios_pro_rata"?: boolean | null; "juros_compensatorios_data_inicio"?: string | null; "mes_atualizacao": "janeiro" | "fevereiro" | "março" | "abril" | "maio" | "junho" | "julho" | "agosto" | "setembro" | "outubro" | "novembro" | "dezembro"; "ano_atualizacao": number; "indice": string; "deflacionar_valor_nominal"?: boolean | null; "competencia_final_taxa_legal"?: string | null; "valor_dobrado_flag"?: boolean | null };

export type CalculationPolicyView = { "origem_calculo": "manual" | "processo"; "parametros_padrao": Record<string, string | number | number | boolean | null>; "campos_obrigatorios": Array<string>; "catalogo": Array<ParameterCatalogItem> };

export type CalculationRequest_Input = { "origem_calculo": "manual" | "processo"; "numero_processo"?: string | null; "identificador_calculo"?: string | null; "parcelas": Array<Installment_Input>; "parametros": CalculationParameters_Input; "revisao_humana_confirmada": true; "honorarios_sobre_danos_morais"?: boolean; "competencia_automatica"?: boolean };

export type CalculationRequest_Output = { "origem_calculo": "manual" | "processo"; "numero_processo"?: string | null; "identificador_calculo"?: string | null; "parcelas": Array<Installment_Output>; "parametros": CalculationParameters_Output; "revisao_humana_confirmada": true; "honorarios_sobre_danos_morais"?: boolean; "competencia_automatica"?: boolean };

export type CalculationResponse = { "origem_calculo": "manual" | "processo"; "numero_processo": string | null; "identificador_calculo": string; "memoria": DataTable; "resumo": Array<SummaryEntry>; "parametros": CalculationParameters_Output; "metadata": CalculationMetadata };

export type CalculationStateChange = { "estado": "ativo" | "arquivado" | "cancelado" };

export type CalculationStateResult = { "calculo_id": string; "estado": "ativo" | "arquivado" | "cancelado"; "atualizado_em": string };

export type CalculationVersionDetail = { "calculo_id": string; "origem_calculo": "manual" | "processo"; "identificador_calculo": string; "numero_processo"?: string | null; "estado_calculo"?: "ativo" | "arquivado" | "cancelado"; "versao": number; "versao_atual": number; "versao_base"?: number | null; "criado_em": string; "criado_por": string; "campos_alterados"?: Array<string>; "diff"?: CalculationDiff; "quantidade_execucoes"?: number; "requisicao": CalculationRequest_Output; "resultado": CalculationResponse };

export type CalculationVersionRef = { "calculo_id": string; "versao": number; "versao_base"?: number | null; "criado_em": string; "criada"?: boolean };

export type CalculationVersionSummary = { "versao": number; "versao_base"?: number | null; "criado_em": string; "criado_por": string; "total_geral"?: string | null; "indice": string; "competencia_atualizacao": string; "entrada_sha256": string; "indices_sha256": string; "campos_alterados"?: Array<string>; "diff"?: CalculationDiff; "quantidade_execucoes"?: number; "ultima_execucao_em"?: string | null };

export type CalculationVersionsPage = { "calculo_id": string; "itens": Array<CalculationVersionSummary>; "pagina": number; "tamanho_pagina": number; "total_itens": number; "total_paginas": number };

export type ChronologyDecision = { "campo": string; "valor": string | number | number | boolean | null; "documento": string; "pagina": number; "sequencia": number; "natureza": "pedido" | "fato" | "comando_decisorio" | "fundamentacao" | "classificacao_documental" | "indeterminado"; "efeito": "informa" | "mantem" | "altera" | "afasta" | "majora" | "reduz" | "substitui" | "nao_se_aplica"; "motivo": string };

export type DataTable = { "colunas": Array<string>; "linhas": Array<Array<string | number | number | boolean | null>> };

export type DocumentMetadata = { "identificador": string; "numero_processo": string; "nome": string; "sha256": string; "tamanho_bytes": number; "paginas": number; "classificacao": string };

export type ExtractionConfiguration = { "provedor"?: "bradesco_iagen"; "configurada": boolean; "modelo": string; "mensagem": string; "leitura_documental": string; "tokens_disponiveis"?: boolean; "custo_disponivel"?: boolean };

export type ExtractionRequest = { "numero_processo": string };

export type ExtractionResult = { "numero_processo": string; "campos": Array<FieldEvidence>; "parcelas": Array<Installment_Output>; "alertas": Array<string>; "versao_prompts": string; "parametros_consolidados"?: Record<string, string | number | number | boolean | null>; "decisoes_cronologicas"?: Array<ChronologyDecision>; "ajustes_operacionais"?: Array<OperationalAdjustment>; "honorarios_sobre_danos_morais"?: boolean; "competencia_automatica"?: boolean; "uso_ia"?: AiUsageSummary | null };

export type ExtractionStatus = { "numero_processo": string; "identificador": string; "estado": "aguardando" | "executando" | "pronto" | "falha" | "bloqueada" | "interrompida"; "etapa": string; "mensagem": string; "atualizado_em": string; "codigo_erro"?: string | null; "uso_ia"?: AiUsageSummary | null };

export type FeePreparation = { "parcelas": Array<Installment_Input>; "percentual": number | string };

export type FieldEvidence = { "campo": string; "valor": string | number | number | boolean | null; "documento": string; "pagina": number; "trecho": string; "escopo": "caso_concreto" | "jurisprudencia_citada" | "indeterminado"; "natureza"?: "pedido" | "fato" | "comando_decisorio" | "fundamentacao" | "classificacao_documental" | "indeterminado"; "efeito"?: "informa" | "mantem" | "altera" | "afasta" | "majora" | "reduz" | "substitui" | "nao_se_aplica" };

export type HTTPValidationError = { "detail"?: Array<ValidationError> };

export type Health = { "status"?: string; "versao_api"?: string };

export type IndexOption = { "chave": string; "nome": string; "nome_base": string; "disponivel"?: boolean; "modo": "rate_decimal" | "value_index" | "sem_correcao" | "indisponivel"; "competencia_inicial"?: string | null; "competencia_final"?: string | null; "competencia_maxima_atualizacao"?: string | null };

export type IndexStatus = { "estado": "nao_verificado" | "atualizado" | "sem_novidade" | "falha" | "executando"; "mensagem": string; "atualizado_em"?: string | null; "arquivos_sha256": Record<string, string> };

export type Installment_Input = { "data": string; "valor_singelo": number | string; "descricao"?: string; "verba_tipo": "dano_material" | "dano_moral" | "honorarios" | "custas"; "multiplicador"?: 1 | 2 | null; "origem"?: "informada" | "honorarios_dano_moral" };

export type Installment_Output = { "data": string; "valor_singelo": string; "descricao"?: string; "verba_tipo": "dano_material" | "dano_moral" | "honorarios" | "custas"; "multiplicador"?: 1 | 2 | null; "origem"?: "informada" | "honorarios_dano_moral" };

export type InstallmentDiff = { "posicao": number; "acao": "adicionada" | "removida" | "alterada"; "campos_alterados"?: Array<string>; "antes"?: Installment_Output | null; "depois"?: Installment_Output | null };

export type OperationalAdjustment = { "campo": string; "valor": string | number | number | boolean | null; "motivo": string };

export type ParameterCatalogItem = { "key": string; "label": string; "type": "text" | "number" | "date" | "select" | "checkbox"; "section": string; "options"?: Array<ParameterOption> | null; "help"?: string | null; "damageTypes"?: Array<"dano_material" | "dano_moral" | "honorarios" | "custas"> | null };

export type ParameterChangeInput = { "origem_calculo": "manual" | "processo"; "numero_processo"?: string | null; "rascunho_id": string; "campo": string; "valor_anterior"?: string | number | number | boolean | null; "valor_novo"?: string | number | number | boolean | null; "extracao_id"?: string | null };

export type ParameterChangeRecord = { "origem_calculo": "manual" | "processo"; "numero_processo"?: string | null; "rascunho_id": string; "campo": string; "valor_anterior"?: string | number | number | boolean | null; "valor_novo"?: string | number | number | boolean | null; "extracao_id"?: string | null; "identificador": number; "registrado_em": string; "ator_tecnico": string; "valor_extraido"?: string | number | number | boolean | null; "origem_extraida"?: string | null };

export type ParameterOption = { "value": string | number | number | boolean | null; "label": string; "hidden"?: boolean };

export type ProcessSummary = { "numero_processo": string; "quantidade_documentos": number };

export type SummaryEntry = { "campo": string; "valor": string };

export type UploadResponse = { "documentos": Array<DocumentMetadata>; "extracoes": Array<ExtractionStatus> };

export type ValidationError = { "loc": Array<string | number>; "msg": string; "type": string; "input"?: unknown; "ctx"?: Record<string, unknown> };

export type VersionedCalculationResponse = { "origem_calculo": "manual" | "processo"; "numero_processo": string | null; "identificador_calculo": string; "memoria": DataTable; "resumo": Array<SummaryEntry>; "parametros": CalculationParameters_Output; "metadata": CalculationMetadata; "registro"?: CalculationVersionRef | null; "execucao"?: CalculationExecutionRef | null };

export type CalculationParameters = CalculationParameters_Input;

export type CalculationRequest = CalculationRequest_Input;

export type Installment = Installment_Input;
