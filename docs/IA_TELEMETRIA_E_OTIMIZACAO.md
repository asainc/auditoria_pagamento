# Telemetria e otimização da IA corporativa

## Métricas disponíveis

O contrato atual de `text_generator` não fornece contagem de tokens ou cobrança no retorno consumido pela calculadora. Por isso a aplicação não estima esses valores. São registrados apenas metadados observáveis:

- etapa e hash do prompt versionado;
- modelo/serviço configurado;
- quantidade de chamadas;
- duração de cada chamada e duração acumulada;
- páginas selecionadas deterministicamente para a tarefa;
- caracteres enviados;
- quantidade de chunks;
- uso ou não de correção estrutural;
- quantidade de evidências aceitas e rejeitadas;
- código de erro sanitizado e tentativa do job, quando aplicável.

PDF, texto processual, prompt completo, resposta integral, credenciais e tokens de autenticação não são registrados.

## Otimização de payload

O projeto reduz redundância em quatro camadas:

1. PyMuPDF lê o PDF localmente e calcula um score de qualidade por página;
2. páginas sem texto confiável são descartadas antes da IA;
3. `PromptPageRouter` seleciona, para cada tarefa, somente páginas candidatas por palavras-chave e usa páginas representativas como fallback conservador;
4. somente o contexto selecionado é particionado conforme `BRADESCO_PROMPT_MAX_CHARS`.

Assim, juros não recebem automaticamente todas as páginas de extratos sem relação, prescrição prioriza páginas com termos de prazo e valor em dobro prioriza trechos com comandos como `em dobro` ou `art. 42`.

A seleção é determinística e auditável. Ela não usa outro modelo e não cria fatos. `EXTRACTION_MAX_PAGES_PER_TASK` e `EXTRACTION_FALLBACK_PAGES_PER_DOCUMENT` controlam os limites.

## Correção estrutural

Antes de gastar uma segunda chamada, o backend normaliza localmente wrappers e aliases conhecidos, por exemplo `fields -> campos`, `installments -> parcelas`, `page -> pagina` e `value -> valor`. Defaults conservadores sem efeito financeiro também são preenchidos localmente.

Somente se a saída continuar incompatível com o contrato Pydantic é realizada uma única chamada adicional ao `text_generator`, restrita à correção estrutural da resposta anterior.

## Fila durável

Jobs de extração são persistidos no SQLite da instalação. Um restart devolve jobs pendentes à fila em vez de marcá-los como perdidos. Cada job utiliza lease, número máximo de tentativas e retentativa automática apenas para falhas consideradas transitórias.
