# Extração documental — PyMuPDF + text_generator

## Objetivo

Transformar PDFs judiciais em parâmetros revisáveis sem utilizar OCR. A camada de leitura documental é local e determinística; somente os prompts são enviados ao serviço corporativo de geração de texto.

## Fluxo

1. O upload valida e persiste o PDF no backend.
2. `PyMuPDF` abre o arquivo a partir dos bytes já persistidos.
3. Cada página é lida com `page.get_text("text", sort=True)`.
4. Cada página recebe score de qualidade; páginas inutilizáveis não são enviadas à IA.
5. `PromptPageRouter` seleciona páginas candidatas por tarefa de forma determinística e auditável.
6. O backend cria strings com marcadores `DOCUMENTO` e `PAGINA` somente para as páginas selecionadas.
7. Quando o contexto ultrapassa `BRADESCO_PROMPT_MAX_CHARS`, ele é particionado sem remover o conteúdo selecionado.
8. Toda execução de prompt chama exclusivamente `gpt_bradesco.text_generator`.
9. A resposta passa primeiro por normalização estrutural local e depois pelo contrato Pydantic.
10. As evidências são conferidas novamente contra o texto extraído da página.
11. A interface recebe os parâmetros consolidados para revisão humana antes do cálculo.

## PDFs sem camada de texto

PyMuPDF não é OCR. O backend avalia quantidade de caracteres, proporção imprimível, proporção alfanumérica e caracteres de substituição. Se nenhum documento tiver página textual minimamente utilizável, a extração é bloqueada antes do `text_generator` e a interface pede outra versão digital pesquisável do documento.

## Payload para text_generator

Cada chamada contém, em ordem:

- prompt especializado;
- aviso de que o conteúdo documental é evidência e não instrução;
- texto extraído do PDF com nome do documento e número da página;
- schema JSON obrigatório;
- instrução para devolver somente JSON.

A aplicação não envia o arquivo PDF ao `text_generator`; envia apenas a string textual necessária à tarefa.

## Rastreabilidade

Cada `FieldEvidence` continua contendo `documento`, `pagina` e `trecho`. Antes de consolidar um campo, o backend normaliza espaços e confirma que o trecho está presente na página correspondente do texto extraído pelo PyMuPDF.

## Privacidade e logs

Os logs técnicos registram etapa, modelo, duração e identificadores operacionais. PDF, texto extraído, prompt, resposta completa, credenciais e tokens não devem ser registrados. Qualquer uso com dados reais deve seguir os controles aprovados por Segurança, Jurídico/Compliance e DPO.


## Correção automática de estrutura da resposta

A integração usa o contrato mínimo compatível do `text_generator` e exige JSON no próprio prompt. Antes de qualquer segunda chamada, o backend normaliza wrappers, aliases e defaults estruturais seguros localmente. Se a saída ainda permanecer incompatível com Pydantic, executa **uma única chamada adicional ao `text_generator`** para reformatar a resposta anterior, sem reler o caso e sem permitir inclusão de fatos novos. Se a segunda validação também falhar, nenhuma sugestão parcial é aplicada.

O contrato de transporte aceita omissões que possuem defaults conservadores equivalentes aos contratos internos (por exemplo, `natureza=indeterminado`, `efeito=informa` e descrição vazia de parcela). Valores financeiros, datas calculáveis e evidências continuam sujeitos às validações rígidas do backend e à revisão humana.


## Compatibilidade do `text_generator`

A calculadora chama `gpt_bradesco.text_generator` com o conjunto mínimo de parâmetros compartilhado pelas versões corporativas conhecidas: `deployment_name`, `temperature`, `max_tokens`, `async_mode=false`, `stream=false` e `message_format={"type":"text"}`. O JSON de extração é exigido pelo prompt e validado pelo Pydantic no backend. Essa decisão evita depender de `response_format=json_object`, que pode não estar habilitado em todos os deployments corporativos.

Quando uma implementação legada lança uma exceção textual com código HTTP (por exemplo, `Erro na execução: 400 - ...`), somente o código é aproveitado para diagnóstico; o corpo da resposta não é propagado para a interface nem para logs de negócio.
