# Extração documental — PyMuPDF + text_generator

## Objetivo

Transformar PDFs judiciais em parâmetros revisáveis sem utilizar OCR. A camada de leitura documental é local e determinística; somente os prompts são enviados ao serviço corporativo de geração de texto.

## Fluxo

1. O upload valida e persiste o PDF no backend.
2. `PyMuPDF` abre o arquivo a partir dos bytes já persistidos.
3. Cada página é lida com `page.get_text("text", sort=True)`.
4. O backend cria uma string com marcadores `DOCUMENTO` e `PAGINA`.
5. Quando a string ultrapassa `BRADESCO_PROMPT_MAX_CHARS`, ela é particionada sem remover conteúdo.
6. Cada prompt especializado é combinado com a string correspondente.
7. Toda execução de prompt chama exclusivamente `gpt_bradesco.text_generator`.
8. A resposta precisa ser JSON válido e aderente ao contrato Pydantic.
9. As evidências são conferidas novamente contra o texto extraído da página.
10. A interface recebe os parâmetros consolidados para revisão humana antes do cálculo.

## PDFs sem camada de texto

PyMuPDF não é OCR. PDFs formados apenas por imagens podem devolver páginas vazias. Nessa situação o backend adiciona um alerta explícito e não tenta preencher parâmetros com conteúdo inexistente. A decisão sobre um eventual fluxo separado de OCR precisa ser validada antes de ser incorporada novamente.

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

A integração usa `message_format={"type": "json_object"}`, mas esse modo garante apenas um objeto JSON; ele não garante sozinho aderência completa ao contrato da calculadora. O backend valida cada resposta com Pydantic. Se houver apenas incompatibilidade estrutural ou de tipos, executa **uma única chamada adicional ao `text_generator`** para reformatar a resposta anterior, sem reler o caso e sem permitir inclusão de fatos novos. Se a segunda validação também falhar, nenhuma sugestão parcial é aplicada e a extração termina com erro explícito.

O contrato de transporte aceita omissões que possuem defaults conservadores equivalentes aos contratos internos (por exemplo, `natureza=indeterminado`, `efeito=informa` e descrição vazia de parcela). Valores financeiros, datas calculáveis e evidências continuam sujeitos às validações rígidas do backend e à revisão humana.
