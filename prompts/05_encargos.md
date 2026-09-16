# Extraindo multa, honorários e Art. 523 do CPC

## Objetivo
Extraia apenas encargos representáveis pelo contrato: multa percentual, honorários, tipo dos honorários, incidências e regra explícita do Art. 523.

## Honorários
Diferencie:
- honorários sucumbenciais fixados em percentual;
- honorários em valor fixo;
- honorários do Art. 523;
- simples pedido de honorários ainda não decidido.

Não converta automaticamente `10% sobre a condenação` em valor monetário. Extraia percentual e tipo.

## Multa
Extraia percentual apenas quando explícito e vinculado ao caso. Não use multa mencionada em precedente, cláusula alheia ao comando ou exemplo de cálculo.

## Art. 523
Preencha `parametros.art_523` somente quando o documento expressamente determinar aplicação ou não aplicação representável no contrato. O padrão operacional `nao_aplicar` é responsabilidade do backend e não deve ser inventado pela extração.

## Incidências
Campos como incidência de multa/honorários sobre juros ou parcelas a vencer exigem suporte textual inequívoco. Se o documento trouxer regra mais complexa que o contrato, gere alerta em vez de simplificar.

## Decisões sucessivas
Majoração recursal de honorários deve usar `efeito=majora`; redução, `reduz`; afastamento, `afasta`; substituição integral, `substitui`. Não some automaticamente percentuais de decisões distintas sem comando expresso de acumulação.

## Saída
Use `campo=parametros.<nome_exato>`. Retorne `parcelas=[]` e `eventos_financeiros=[]`.

## Cobertura adicional
Procure multa, cláusula penal, astreintes quando representáveis, honorários advocatícios/sucumbenciais, percentual sobre condenação/proveito econômico/valor da causa e referências ao art. 523. Identifique a base de incidência somente para contextualizar a evidência; não invente campo que o contrato não possua. Honorários recursais devem ser tratados conforme o comando de majoração, sem soma automática.
