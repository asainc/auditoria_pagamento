# Model card — extração documental corporativa

## Finalidade

Sugerir parâmetros estruturados a partir de documentos judiciais e bancários para revisão humana antes do cálculo.

## Componentes

- OCR híbrido corporativo via `gpt_bradesco.ocr_hibrido` (com fallback compatível para `ocr_generator`/`ocr`);
- geração de texto via `gpt_bradesco.text_generator`;
- prompts especializados versionados em `prompts/`;
- validação estrutural Pydantic;
- consolidação cronológica determinística em Python.

## Deployment

O deployment de texto é configurável por `BRADESCO_TEXT_MODEL`. Os modelos usados em figuras e tabelas do OCR também são configuráveis. A disponibilidade precisa ser validada no ambiente corporativo; o projeto não assume que um nome de modelo habilitado em um ambiente exista em outro.

## Limitações

- OCR pode perder ou reorganizar texto de digitalizações ruins;
- tabelas complexas podem exigir revisão visual;
- se o OCR não devolver paginação detalhada, a evidência recebe alerta;
- modelos generativos podem omitir ou interpretar incorretamente fatos;
- saída nunca deve substituir decisão jurídica humana;
- token e custo não são estimados quando o serviço não os fornece.

## Uso proibido

- cálculo financeiro diretamente pelo modelo;
- decisão automática com impacto sobre pessoas;
- uso sem revisão humana;
- uso de credenciais pessoais embutidas no código;
- envio de documentos para ambientes não autorizados.

## Monitoramento

Acompanhar taxa de falhas por etapa, duração, quantidade de chamadas, campos descartados por evidência inválida, divergências e alterações humanas posteriores. Acurácia deve ser validada em benchmark rotulado antes de qualquer conclusão de qualidade.
