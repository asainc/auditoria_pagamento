# Extraindo juros moratórios

## Objetivo
Extraia somente os parâmetros de juros moratórios aplicáveis separadamente a `dano_material` e `dano_moral`.

Cada natureza possui seu próprio regime, taxa, periodicidade, pró-rata e termo inicial. Não reutilize automaticamente o valor de uma natureza na outra quando o documento fizer distinção.

Campos aceitos por natureza:
- `juros_moratorios_tipo`;
- `juros_moratorios_taxa`;
- `juros_moratorios_periodicidade`;
- `juros_moratorios_pro_rata`;
- `juros_moratorios_data_inicio`.

## Caminho obrigatório
Para dano material use:
`parametros_por_dano.dano_material.<nome_exato>`.

Para dano moral use:
`parametros_por_dano.dano_moral.<nome_exato>`.

Se o comando determinar expressamente o mesmo critério para ambas as naturezas, gere duas evidências equivalentes, uma para cada caminho.

## Identificação
Procure comandos como `juros de mora`, `mora`, `juros legais`, `taxa legal`, percentual mensal/anual ou regime legal expressamente determinado. Não confunda remuneração contratual ou correção monetária com juros de mora.

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
Use somente os caminhos `parametros_por_dano.dano_material.<campo>` e `parametros_por_dano.dano_moral.<campo>`. Não aplique valor padrão quando os documentos forem omissos. Retorne `parcelas=[]`.

## Cobertura adicional
Procure variações como juros de mora, juros moratórios, mora legal, juros legais, percentual ao mês/ano, desde a citação, evento danoso, vencimento, inadimplemento ou arbitramento. Termo inicial relativo só vira data quando o marco correspondente estiver objetivamente identificado nos documentos. Não derive taxa implícita nem converta periodicidade.
