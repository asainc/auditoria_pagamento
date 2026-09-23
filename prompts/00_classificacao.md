# Classificando documentos e marcos processuais

## Objetivo
Classifique cada PDF pelo conteúdo e extraia somente os marcos processuais necessários para orientar as demais tarefas.

## Classificações permitidas
Para cada arquivo, retorne `documentos.<posição>.classificacao` como uma destas opções:
- `peticao_inicial`: peça inaugural do próprio caso;
- `sentenca`: sentença do próprio caso;
- `acordao`: acórdão/voto colegiado do próprio caso;
- `decisao`: decisão interlocutória ou monocrática do próprio caso;
- `comprovante_pagamento`: comprovante de pagamento, depósito ou transferência;
- `extrato`: extrato bancário/financeiro;
- `outro`: contestação, manifestação, planilha, precedente de terceiro, doutrina ou material auxiliar.

Use `natureza=classificacao_documental` e `efeito=informa` para a evidência de classificação do próprio arquivo.

## Datas processuais
Extraia apenas quando expressas e verificáveis:
- `processo.data_peticao_inicial`: protocolo/ajuizamento da petição inicial do caso;
- `processo.data_citacao`: data efetiva da citação, quando comprovada.

Não confunda data de assinatura, publicação, upload, precedente citado ou documento de terceiro com data do processo analisado.

## Distinção entre caso concreto e precedente
Considere número do processo, partes, relatório, dispositivo e contexto. Um acórdão integral transcrito em uma petição como jurisprudência continua sendo precedente, não `acordao` do caso analisado.

## Saída
Não extraia parcelas nem parâmetros de cálculo nesta tarefa. Retorne `parcelas=[]`. Use `null` quando a informação não for verificável.

## Cobertura adicional
Não confie no título do PDF. Diferencie capa, certidão, decisão, sentença e acórdão pelo conteúdo efetivo. Em arquivos compostos, classifique pelo documento processual predominante e gere alerta quando houver múltiplas peças autônomas no mesmo PDF. Procure datas em carimbos de protocolo e certidões, mas só as use como marco processual quando o texto indicar claramente sua natureza.
