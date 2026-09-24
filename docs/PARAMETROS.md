# Catálogo de parâmetros

> Arquivo gerado por `python scripts/generate_parameter_docs.py` a partir de `config/calculation_policy.json`. Não edite a tabela manualmente.

## Fonte de verdade

`config/calculation_policy.json` define chaves, rótulos, seções visuais, opções, campos obrigatórios e padrões por origem. O backend lê esse arquivo diretamente e o Angular consome um artefato TypeScript gerado pelo mesmo catálogo.

## Padrões por origem

| Campo | Cálculo manual | Processo real |
| --- | --- | --- |
| `art_523` | `nao_aplicar` | `nao_aplicar` |
| `indice` | sem padrão | `tjsp_inpc_ipca15_lei_14905` |
| `juros_compensatorios_tipo` | `sem_juros` | `taxa_legal_12_aa_6_aa` |
| `juros_moratorios_tipo` | `sem_juros` | `taxa_legal_12_aa_6_aa` |
| `multa_tipo` | `percentual` | `percentual` |
| `valor_dobrado_flag` | `false` | `false` |

Os padrões completam somente campos ausentes. Um valor explicitamente informado pelo operador ou consolidado a partir dos documentos não é sobrescrito. Para processo real, a `OperationalPolicy` registra o uso de padrão em `ajustes_operacionais`, mantendo separado o que veio de documento e o que veio de política.

## Dependências importantes

- `capitalizacao_simples` e `capitalizacao_composta` exigem taxa e periodicidade do mesmo grupo de juros.
- Prescrição habilitada exige anos e tipo de data de referência; quando o tipo não é `data_ultima_parcela`, a data de referência também é obrigatória.
- Compensação habilitada exige tipo e valor.
- Duplo índice habilitado exige índice, data inicial e data final para as duas faixas.
- Valores monetários e taxas atravessam a API como texto decimal e são validados com `Decimal` no Python.

## Juros moratórios

| Chave | Rótulo | Tipo visual | Obrigatório base | Opções/observações |
| --- | --- | --- | --- | --- |
| `juros_moratorios_sobre_compensatorios` | Juros moratórios sobre compensatórios | `checkbox` | não | — |
| `juros_moratorios_tipo` | Juros moratórios - tipo | `select` | sim | juros_moratorios_stj1368_lei_14905, taxa_legal_12_aa_6_aa, capitalizacao_composta, capitalizacao_simples, sem_juros, juros_moratorios_ctn_lei_14905, taxa_legal_diaria_selic_ipcae, taxa_legal |
| `juros_moratorios_taxa` | Juros moratórios - taxa | `text` | não | — |
| `juros_moratorios_periodicidade` | Juros moratórios - periodicidade | `select` | não | diaria, mensal, anual |
| `juros_moratorios_pro_rata` | Aplicar juros moratórios pro rata | `checkbox` | não | — |
| `juros_moratorios_data_inicio` | Data inicial dos juros moratórios | `date` | não | — |

## Atualização monetária

| Chave | Rótulo | Tipo visual | Obrigatório base | Opções/observações |
| --- | --- | --- | --- | --- |
| `indice` | Índice de correção | `select` | sim | — |
| `mes_atualizacao` | Mês de atualização | `select` | sim | janeiro, fevereiro, março, abril, maio, junho, julho, agosto, setembro, outubro, novembro, dezembro |
| `ano_atualizacao` | Ano de atualização | `number` | sim | — |
| `deflacionar_valor_nominal` | Deflacionar valor nominal | `checkbox` | não | Marque quando o valor informado precisar ser trazido para a competência-base. |
| `competencia_final_taxa_legal` | Competência final da Taxa Legal | `text` | não | Opcional. Use o padrão aaaa-mm quando necessário. |

## Juros compensatórios

| Chave | Rótulo | Tipo visual | Obrigatório base | Opções/observações |
| --- | --- | --- | --- | --- |
| `juros_compensatorios_tipo` | Juros compensatórios - tipo | `select` | sim | juros_moratorios_stj1368_lei_14905, taxa_legal_12_aa_6_aa, capitalizacao_composta, capitalizacao_simples, sem_juros, juros_moratorios_ctn_lei_14905, taxa_legal_diaria_selic_ipcae, taxa_legal |
| `juros_compensatorios_taxa` | Juros compensatórios - taxa | `text` | não | — |
| `juros_compensatorios_periodicidade` | Juros compensatórios - periodicidade | `select` | não | diaria, mensal, anual |
| `juros_compensatorios_pro_rata` | Aplicar juros compensatórios pro rata | `checkbox` | não | — |
| `juros_compensatorios_data_inicio` | Data inicial dos juros compensatórios | `date` | não | — |

## Multa, honorários e art. 523

| Chave | Rótulo | Tipo visual | Obrigatório base | Opções/observações |
| --- | --- | --- | --- | --- |
| `multa_valor` | Multa | `text` | não | Informe o percentual ou o valor monetário conforme o tipo selecionado. |
| `multa_tipo` | Multa - tipo | `select` | não | percentual, fixo |
| `incidir_multa_sobre_juros_compensatorios` | Incidir multa sobre juros compensatórios | `checkbox` | não | — |
| `incidir_multa_sobre_juros_moratorios` | Incidir multa sobre juros moratórios | `checkbox` | não | — |
| `incidir_multa_sobre_parcelas_a_vencer` | Incidir multa sobre parcelas a vencer | `checkbox` | não | — |
| `honorarios` | Honorários | `text` | não | — |
| `honorarios_tipo` | Honorários - tipo | `select` | não | percentual, fixo |
| `incidir_honorarios_sobre_multa` | Incidir honorários sobre multa | `checkbox` | não | — |
| `art_523` | Art. 523 do CPC | `select` | não | Marque quando houver incidência expressa da multa/ônus do art. 523. |

## Prescrição

| Chave | Rótulo | Tipo visual | Obrigatório base | Opções/observações |
| --- | --- | --- | --- | --- |
| `prescricao_flag` | Processo com prescrição | `checkbox` | não | — |
| `prescricao_anos` | Anos de prescrição | `number` | não | — |
| `prescricao_data_referencia_tipo` | Data de referência da prescrição | `select` | não | data_ajuizamento, data_decisao, data_ultima_parcela |
| `prescricao_data_referencia` | Valor da data de referência | `date` | não | — |

## Compensação

| Chave | Rótulo | Tipo visual | Obrigatório base | Opções/observações |
| --- | --- | --- | --- | --- |
| `compensacao_flag` | Processo com compensação | `checkbox` | não | — |
| `compensacao_tipo_calculo` | Tipo de compensação | `select` | não | fixo, percentual |
| `compensacao_valor` | Valor ou percentual da compensação | `text` | não | — |

## Valor em dobro

| Chave | Rótulo | Tipo visual | Obrigatório base | Opções/observações |
| --- | --- | --- | --- | --- |
| `valor_dobrado_flag` | Aplicar valor em dobro | `checkbox` | não | Marque somente quando o título ou decisão determinar restituição/devolução em dobro. O motor duplica apenas as parcelas de dano material antes da correção, juros, multa e honorários; dano moral e demais verbas não são duplicados. |

## Duplo índice

| Chave | Rótulo | Tipo visual | Obrigatório base | Opções/observações |
| --- | --- | --- | --- | --- |
| `duplo_indice_flag` | Processo com duplo índice | `checkbox` | não | — |
| `duplo_indice_primeiro_indice` | Primeiro índice | `select` | não | — |
| `duplo_indice_primeiro_data_inicio` | Primeiro índice - data inicial | `date` | não | — |
| `duplo_indice_primeiro_data_fim` | Primeiro índice - data final | `date` | não | — |
| `duplo_indice_primeiro_valor_parcela` | Primeiro índice - valor da parcela | `text` | não | — |
| `duplo_indice_segundo_indice` | Segundo índice | `select` | não | — |
| `duplo_indice_segundo_data_inicio` | Segundo índice - data inicial | `date` | não | — |
| `duplo_indice_segundo_data_fim` | Segundo índice - data final | `date` | não | — |
| `duplo_indice_segundo_valor_parcela` | Segundo índice - valor da parcela | `text` | não | — |

## Manutenção do catálogo

`config/calculation_policy.json` é o único ponto editável para metadados e defaults. Após qualquer edição autorizada, os artefatos derivados são regenerados por `generate_parameter_catalog.py` e `generate_parameter_docs.py` e validados pelas suítes Python e Angular.

Critérios jurídicos ou regulatórios exigem validação do time jurídico/compliance/DPO quando aplicável; o catálogo técnico não substitui essa validação.
