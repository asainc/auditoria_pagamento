# Extraindo juros compensatórios

## Objetivo
Extraia somente os parâmetros de juros compensatórios/remuneratórios aceitos pelo contrato: tipo, taxa, periodicidade, pró-rata e data inicial.

## Identificação
Exija indicação clara de juros compensatórios, remuneratórios ou equivalente aplicável ao débito. Não classifique automaticamente juros de mora ou correção monetária como compensatórios.

## Taxa e período
- Preserve percentual e periodicidade expressos, sem conversão matemática.
- Extraia data inicial somente quando houver data verificável e representável.
- Não calcule taxa implícita a partir de valor final.

## Decisões sucessivas
Se decisão posterior afastar, reduzir, majorar ou substituir os juros compensatórios, classifique como `comando_decisorio` e use o `efeito` correspondente. Silêncio do documento mais recente não elimina regra anterior.

## Saída
Use `campo=parametros.<nome_exato>`. Não aplique defaults documentais. Retorne `parcelas=[]` e `eventos_financeiros=[]`.

## Cobertura adicional
Considere as expressões juros compensatórios, remuneratórios, remuneratórios do capital, remuneração contratual e juros contratuais apenas quando o contexto mostrar que são componente autônomo do débito. Não confunda com encargos de mora, correção, comissão de permanência ou percentual meramente citado em contrato sem comando aplicável.
