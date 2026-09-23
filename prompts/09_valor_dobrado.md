# Identificando restituição ou devolução em dobro

Extraia somente a regra documental que determine se o cálculo do valor principal deve usar o valor nominal em dobro.

Use exclusivamente o campo `parametros.valor_dobrado_flag`.

Defina `true` apenas quando houver comando inequívoco no caso concreto, por exemplo:
- "restituição em dobro";
- "devolução em dobro";
- "repetição do indébito em dobro";
- "de forma dobrada";
- determinação expressa de devolução dobrada nos termos do art. 42 do CDC.

Defina `false` somente quando houver comando expresso afastando a dobra ou determinando restituição simples. Se o documento for omisso, não invente `false`: não retorne o campo.

Não dobre os valores dentro de `parcelas`. As parcelas devem permanecer com o valor nominal documental; o motor aplicará a dobra quando `valor_dobrado_flag=true`.

Para a evidência use `campo=parametros.valor_dobrado_flag`, `valor=true|false`, documento, página e trecho literal que sustente a conclusão. Em sentença/acórdão prefira o dispositivo ou comando decisório vigente. Pedido da inicial não deve ser tratado como condenação.

Retorne `parcelas=[]`. Gere alerta se houver conflito entre decisões ou se não for possível determinar qual decisão prevalece.
