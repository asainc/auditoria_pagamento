# Extraindo duplo índice

## Objetivo
Extraia duas faixas de correção somente quando o caso determinar regimes de atualização distintos por período ou grupo de parcelas e essa regra couber exatamente no contrato de dois índices.

Campos: `duplo_indice_flag`, primeiro/segundo índice, datas inicial/final e valor de parcela opcional de cada faixa.

## Exemplos
- `INPC até 28/08/2024 e IPCA a partir de 29/08/2024` → duas faixas, se as chaves exatas existirem no catálogo e a cobertura for representável;
- `Tabela do tribunal até a vigência da nova lei; IPCA depois` → somente se a data de corte e as chaves forem verificáveis;
- `IPCA para correção e SELIC para juros` → não é duplo índice; são componentes diferentes.

## Regras
- Índices devem corresponder exatamente ao catálogo fornecido pelo backend.
- Datas devem ser `AAAA-MM-DD`.
- `valor_parcela` só existe quando o documento vincular expressamente um valor à faixa.
- Não redistribua parcelas nem derive faixas por cálculo.
- Mais de dois regimes, lacunas ou sobreposições não representáveis devem gerar alerta.

## Decisões sucessivas
Mudança posterior de índice ou data de corte usa `comando_decisorio` com efeito apropriado. Manutenção expressa usa `mantem`.

## Saída
Use `campo=parametros.<nome_exato>`. Retorne `parcelas=[]`.

## Cobertura adicional
Procure expressões de transição como “até”, “a partir de”, “antes/depois de”, “desde a vigência”, “no período”, “posteriormente” e datas de corte. Valide continuidade temporal e ordem das faixas. Se houver mais de dois regimes, faixas por verba diferentes ou condição não representável, gere alerta e não reduza a regra arbitrariamente a duas faixas.
