# Extraindo prescrição

## Objetivo
Extraia `prescricao_flag`, `prescricao_anos`, `prescricao_data_referencia_tipo` e `prescricao_data_referencia` somente quando a aplicação do corte prescricional ao cálculo estiver clara no caso concreto.

## Regras
- Diferencie alegação da parte de comando judicial. Alegação usa `natureza=pedido` ou `fundamentacao`; decisão aplicável usa `comando_decisorio`.
- Não transforme menção genérica a prazo prescricional em corte do cálculo.
- `prescricao_anos` deve vir de prazo expressamente aplicável.
- A data de referência deve ser verificável no histórico e compatível com um tipo aceito pelo contrato (`data_ajuizamento`, `data_decisao`, `data_ultima_parcela`).
- Se a decisão usar marco não representável pelo contrato, gere alerta e não force equivalência.

## Decisões sucessivas
Se decisão posterior reconhecer, afastar ou modificar a prescrição, use `efeito=altera`, `afasta`, `mantem` ou `substitui` conforme o comando.

## Saída
Use `campo=parametros.<nome_exato>`. Não calcule a data de corte manualmente; o motor fará isso com os parâmetros. Retorne `parcelas=[]` e `eventos_financeiros=[]`.

## Cobertura adicional
Procure prescrição, prazo prescricional, parcelas prescritas, limitação temporal, quinquênio, triênio, decênio e expressões equivalentes. Diferencie prescrição de decadência e de simples discussão teórica. Só ative o corte quando houver comando aplicável ao caso concreto e os campos necessários puderem ser representados sem aproximação.
