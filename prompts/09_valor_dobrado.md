# Identificando regra global de restituição ou devolução em dobro

Extraia somente a regra documental geral que determine se, na ausência de multiplicador específico por parcela, as parcelas de dano material devem usar o valor nominal em dobro.

Use exclusivamente o campo `parametros.valor_dobrado_flag`.

Defina `true` apenas quando houver comando inequívoco e abrangente no caso concreto, por exemplo:
- "restituição em dobro" para todos os descontos reconhecidos;
- "devolução em dobro" sem restringir a lançamentos específicos;
- "repetição do indébito em dobro" como regra geral do capítulo decisório;
- determinação expressa de devolução dobrada nos termos do art. 42 do CDC.

Defina `false` somente quando houver comando expresso e abrangente afastando a dobra ou determinando restituição simples. Se o documento for omisso, não invente `false`: não retorne o campo.

Quando a decisão distinguir parcelas específicas com tratamento diferente, NÃO use esta flag para substituir essa distinção. A regra específica deve ser representada em `parcelas.<índice>.multiplicador` pelo prompt de parcelas.

Não dobre valores dentro de `parcelas`. O motor resolve a prioridade assim: multiplicador explícito da parcela > flag global > valor simples.

Para a evidência use `campo=parametros.valor_dobrado_flag`, `valor=true|false`, documento, página e trecho literal que sustente a conclusão. Em sentença/acórdão prefira o dispositivo ou comando decisório vigente. Pedido da inicial não deve ser tratado como condenação.

Retorne `parcelas=[]`. Gere alerta se houver conflito entre decisões ou se não for possível determinar qual decisão prevalece.
