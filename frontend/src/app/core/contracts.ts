/** Gerado de docs/openapi.json. Atualize por scripts/generate_contracts.py. */

export type AiUsage = { "etapa": string; "modelo": string; "tokens_entrada"?: number | null; "tokens_entrada_cache"?: number | null; "tokens_saida"?: number | null; "tokens_total"?: number | null; "custo_estimado_usd"?: string | null; "duracao_ms": number; "paginas_contexto"?: number | null; "caracteres_entrada"?: number | null; "correcao_estrutural"?: boolean };

export type AiUsageSummary = { "chamadas": number; "tokens_entrada"?: number | null; "tokens_entrada_cache"?: number | null; "tokens_saida"?: number | null; "tokens_total"?: number | null; "custo_estimado_usd"?: string | null; "duracao_total_ms"?: number; "detalhamento"?: Array<AiUsage> };

export type BatchImport = { "processos": Array<CalculationDraft>; "erros": Array<string> };

export type BatchItem = { "numero_processo": string | null; "resultado"?: CalculationResponse | null; "erro"?: string | null };

export type BatchRequest = { "processos": Array<CalculationRequest> };

export type BatchResponse = { "resultados": Array<BatchItem> };

export type Body_import_batch_api_lotes_importar_post = { "file": string };

export type Body_import_installments_api_documentos_parcelas_importar_post = { "file": string };

export type Body_upload_api_documentos_upload_post = { "files": Array<string> };

export type CalculationDefaults = { "mes": "janeiro" | "fevereiro" | "março" | "abril" | "maio" | "junho" | "julho" | "agosto" | "setembro" | "outubro" | "novembro" | "dezembro"; "ano": number };

export type CalculationDraft = { "origem_calculo": "manual" | "processo"; "numero_processo"?: string | null; "parcelas": Array<Installment_Output>; "parametros": CalculationParameters_Output; "revisao_humana_confirmada"?: boolean; "honorarios_sobre_danos_morais"?: boolean; "competencia_automatica"?: boolean };

export type CalculationMetadata = { "entrada_sha256": string; "politica_sha256": string; "motor_sha256": string; "indices_sha256": string; "duracao_ms": number; "revisao_humana_confirmada": boolean };

export type CalculationParameters_Input = { "mes_atualizacao": "janeiro" | "fevereiro" | "março" | "abril" | "maio" | "junho" | "julho" | "agosto" | "setembro" | "outubro" | "novembro" | "dezembro"; "ano_atualizacao": number; "indice": string; "juros_moratorios_tipo": "sem_juros" | "capitalizacao_simples" | "capitalizacao_composta" | "juros_moratorios_stj1368_lei_14905" | "taxa_legal_12_aa_6_aa" | "taxa_legal_diaria_selic_ipcae" | "taxa_legal" | "juros_moratorios_ctn_lei_14905"; "juros_compensatorios_tipo": "sem_juros" | "capitalizacao_simples" | "capitalizacao_composta" | "juros_moratorios_stj1368_lei_14905" | "taxa_legal_12_aa_6_aa" | "taxa_legal_diaria_selic_ipcae" | "taxa_legal" | "juros_moratorios_ctn_lei_14905"; "deflacionar_valor_nominal"?: boolean | null; "competencia_final_taxa_legal"?: string | null; "juros_compensatorios_taxa"?: number | string | null; "juros_compensatorios_periodicidade"?: "diaria" | "mensal" | "anual" | null; "juros_compensatorios_pro_rata"?: boolean | null; "juros_compensatorios_data_inicio"?: string | null; "juros_moratorios_taxa"?: number | string | null; "juros_moratorios_periodicidade"?: "diaria" | "mensal" | "anual" | null; "juros_moratorios_pro_rata"?: boolean | null; "juros_moratorios_data_inicio"?: string | null; "juros_moratorios_sobre_compensatorios"?: boolean | null; "incidir_multa_sobre_juros_compensatorios"?: boolean | null; "incidir_multa_sobre_juros_moratorios"?: boolean | null; "incidir_multa_sobre_parcelas_a_vencer"?: boolean | null; "incidir_honorarios_sobre_multa"?: boolean | null; "multa_percentual"?: number | string | null; "honorarios"?: number | string | null; "honorarios_tipo"?: "percentual" | "fixo" | null; "art_523"?: "nao_aplicar" | "aplicar_multa" | "aplicar_multa_honorarios" | null; "prescricao_flag"?: boolean | null; "prescricao_anos"?: number | null; "prescricao_data_referencia_tipo"?: "data_ajuizamento" | "data_decisao" | "data_ultima_parcela" | null; "prescricao_data_referencia"?: string | null; "compensacao_flag"?: boolean | null; "compensacao_tipo_calculo"?: "percentual" | "fixo" | null; "compensacao_valor"?: number | string | null; "duplo_indice_flag"?: boolean | null; "duplo_indice_primeiro_indice"?: string | null; "duplo_indice_primeiro_data_inicio"?: string | null; "duplo_indice_primeiro_data_fim"?: string | null; "duplo_indice_primeiro_valor_parcela"?: number | string | null; "duplo_indice_segundo_indice"?: string | null; "duplo_indice_segundo_data_inicio"?: string | null; "duplo_indice_segundo_data_fim"?: string | null; "duplo_indice_segundo_valor_parcela"?: number | string | null; "valor_dobrado_flag"?: boolean | null };

export type CalculationParameters_Output = { "mes_atualizacao": "janeiro" | "fevereiro" | "março" | "abril" | "maio" | "junho" | "julho" | "agosto" | "setembro" | "outubro" | "novembro" | "dezembro"; "ano_atualizacao": number; "indice": string; "juros_moratorios_tipo": "sem_juros" | "capitalizacao_simples" | "capitalizacao_composta" | "juros_moratorios_stj1368_lei_14905" | "taxa_legal_12_aa_6_aa" | "taxa_legal_diaria_selic_ipcae" | "taxa_legal" | "juros_moratorios_ctn_lei_14905"; "juros_compensatorios_tipo": "sem_juros" | "capitalizacao_simples" | "capitalizacao_composta" | "juros_moratorios_stj1368_lei_14905" | "taxa_legal_12_aa_6_aa" | "taxa_legal_diaria_selic_ipcae" | "taxa_legal" | "juros_moratorios_ctn_lei_14905"; "deflacionar_valor_nominal"?: boolean | null; "competencia_final_taxa_legal"?: string | null; "juros_compensatorios_taxa"?: string | null; "juros_compensatorios_periodicidade"?: "diaria" | "mensal" | "anual" | null; "juros_compensatorios_pro_rata"?: boolean | null; "juros_compensatorios_data_inicio"?: string | null; "juros_moratorios_taxa"?: string | null; "juros_moratorios_periodicidade"?: "diaria" | "mensal" | "anual" | null; "juros_moratorios_pro_rata"?: boolean | null; "juros_moratorios_data_inicio"?: string | null; "juros_moratorios_sobre_compensatorios"?: boolean | null; "incidir_multa_sobre_juros_compensatorios"?: boolean | null; "incidir_multa_sobre_juros_moratorios"?: boolean | null; "incidir_multa_sobre_parcelas_a_vencer"?: boolean | null; "incidir_honorarios_sobre_multa"?: boolean | null; "multa_percentual"?: string | null; "honorarios"?: string | null; "honorarios_tipo"?: "percentual" | "fixo" | null; "art_523"?: "nao_aplicar" | "aplicar_multa" | "aplicar_multa_honorarios" | null; "prescricao_flag"?: boolean | null; "prescricao_anos"?: number | null; "prescricao_data_referencia_tipo"?: "data_ajuizamento" | "data_decisao" | "data_ultima_parcela" | null; "prescricao_data_referencia"?: string | null; "compensacao_flag"?: boolean | null; "compensacao_tipo_calculo"?: "percentual" | "fixo" | null; "compensacao_valor"?: string | null; "duplo_indice_flag"?: boolean | null; "duplo_indice_primeiro_indice"?: string | null; "duplo_indice_primeiro_data_inicio"?: string | null; "duplo_indice_primeiro_data_fim"?: string | null; "duplo_indice_primeiro_valor_parcela"?: string | null; "duplo_indice_segundo_indice"?: string | null; "duplo_indice_segundo_data_inicio"?: string | null; "duplo_indice_segundo_data_fim"?: string | null; "duplo_indice_segundo_valor_parcela"?: string | null; "valor_dobrado_flag"?: boolean | null };

export type CalculationPolicyView = { "origem_calculo": "manual" | "processo"; "parametros_padrao": Record<string, string | number | number | boolean | null>; "campos_obrigatorios": Array<string>; "catalogo": Array<ParameterCatalogItem> };

export type CalculationRequest = { "origem_calculo": "manual" | "processo"; "numero_processo"?: string | null; "parcelas": Array<Installment_Input>; "parametros": CalculationParameters_Input; "revisao_humana_confirmada": true; "honorarios_sobre_danos_morais"?: boolean; "competencia_automatica"?: boolean };

export type CalculationResponse = { "origem_calculo": "manual" | "processo"; "numero_processo": string | null; "memoria": DataTable; "resumo": Array<SummaryEntry>; "parametros": CalculationParameters_Output; "metadata": CalculationMetadata };

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

export type IndexOption = { "chave": string; "nome": string };

export type IndexStatus = { "estado": "nao_verificado" | "atualizado" | "falha" | "executando"; "mensagem": string; "atualizado_em"?: string | null; "arquivos_sha256": Record<string, string> };

export type Installment_Input = { "data": string; "valor_singelo": number | string; "descricao"?: string; "verba_tipo": "dano_material" | "dano_moral" | "honorarios" | "custas"; "multiplicador"?: 1 | 2 | null; "origem"?: "informada" | "honorarios_dano_moral" };

export type Installment_Output = { "data": string; "valor_singelo": string; "descricao"?: string; "verba_tipo": "dano_material" | "dano_moral" | "honorarios" | "custas"; "multiplicador"?: 1 | 2 | null; "origem"?: "informada" | "honorarios_dano_moral" };

export type OperationalAdjustment = { "campo": string; "valor": string | number | number | boolean | null; "motivo": string };

export type ParameterCatalogItem = { "key": string; "label": string; "type": "text" | "number" | "date" | "select" | "checkbox"; "section": string; "options"?: Array<ParameterOption> | null; "help"?: string | null; "damageTypes"?: Array<"dano_material" | "dano_moral" | "honorarios" | "custas"> | null };

export type ParameterChangeInput = { "origem_calculo": "manual" | "processo"; "numero_processo"?: string | null; "rascunho_id": string; "campo": string; "valor_anterior"?: string | number | number | boolean | null; "valor_novo"?: string | number | number | boolean | null; "extracao_id"?: string | null };

export type ParameterChangeRecord = { "origem_calculo": "manual" | "processo"; "numero_processo"?: string | null; "rascunho_id": string; "campo": string; "valor_anterior"?: string | number | number | boolean | null; "valor_novo"?: string | number | number | boolean | null; "extracao_id"?: string | null; "identificador": number; "registrado_em": string; "ator_tecnico": string; "valor_extraido"?: string | number | number | boolean | null; "origem_extraida"?: string | null };

export type ParameterOption = { "value": string | number | number | boolean | null; "label": string; "hidden"?: boolean };

export type ProcessSummary = { "numero_processo": string; "quantidade_documentos": number };

export type SummaryEntry = { "campo": string; "valor": string };

export type UploadResponse = { "documentos": Array<DocumentMetadata>; "extracoes": Array<ExtractionStatus> };

export type ValidationError = { "loc": Array<string | number>; "msg": string; "type": string; "input"?: unknown; "ctx"?: Record<string, unknown> };
