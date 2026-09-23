# Extraindo juros moratórios

## Objetivo
Extraia somente os parâmetros de juros moratórios aceitos pelo contrato: tipo, taxa, periodicidade, pró-rata, data inicial e incidência sobre juros compensatórios.

## Identificação
Procure comandos como `juros de mora`, `mora`, `juros legais`, `taxa legal`, percentual mensal/anual ou regime legal expressamente determinado. Não confunda juros compensatórios, remuneração contratual ou correção monetária com mora.

## Taxa e periodicidade
- Extraia a taxa somente quando o documento fornecer percentual/critério representável.
- Preserve a periodicidade expressa (`diaria`, `mensal`, `anual`).
- Não converta taxa anual em mensal nem vice-versa.
- Regimes como Taxa Legal devem mapear para um tipo existente no contrato somente quando a correspondência for inequívoca.

## Termo inicial
Extraia `juros_moratorios_data_inicio` quando existir data objetiva representável. Expressões jurídicas relativas (`desde a citação`, `desde o evento danoso`) só podem virar data se o histórico trouxer a data do marco de modo verificável e a relação for inequívoca; caso contrário, gere alerta.

## Decisões sucessivas
Comando posterior que muda taxa, termo inicial ou regime deve usar `natureza=comando_decisorio` e o `efeito` aplicável. Menção histórica sem mudança usa `informa`; manutenção expressa usa `mantem`.

## Saída
Use `campo=parametros.<nome_exato>`. Não aplique valor padrão quando os documentos forem omissos. Retorne `parcelas=[]`.

## Cobertura adicional
Procure variações como juros de mora, juros moratórios, mora legal, juros legais, percentual ao mês/ano, desde a citação, evento danoso, vencimento, inadimplemento ou arbitramento. Termo inicial relativo só vira data quando o marco correspondente estiver objetivamente identificado nos documentos. Não derive taxa implícita nem converta periodicidade.
