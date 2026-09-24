# Model card — extração documental corporativa

## Finalidade

Sugerir parâmetros estruturados a partir de documentos judiciais e bancários para revisão humana antes do cálculo.

## Componentes

- leitura textual local por PyMuPDF, sem OCR no fluxo principal;
- score de qualidade da camada textual por página;
- seleção determinística de páginas por tarefa;
- geração de texto exclusivamente via `gpt_bradesco.text_generator`;
- prompts especializados versionados em `prompts/`;
- normalização estrutural determinística e validação Pydantic;
- validação literal das evidências contra a página de origem;
- consolidação cronológica determinística em Python;
- revisão humana obrigatória antes do cálculo.

## Deployment

O deployment de texto é configurável por `BRADESCO_TEXT_MODEL`. A disponibilidade precisa ser validada no ambiente corporativo; o projeto não assume que um nome habilitado em um ambiente exista em outro.

## Limitações

- PyMuPDF depende de camada textual existente; PDF formado apenas por imagens exige outra versão pesquisável do documento;
- tabelas complexas podem perder relações visuais durante extração textual;
- seleção de páginas é heurística e determinística, portanto ainda pode omitir uma página relevante em documentos atípicos;
- modelos generativos podem omitir ou interpretar incorretamente fatos;
- a correção estrutural não valida mérito jurídico;
- token e custo ficam nulos quando o serviço não os fornece.

## Uso proibido

- cálculo financeiro diretamente pelo modelo;
- decisão automática com impacto sobre pessoas;
- uso sem revisão humana;
- credenciais ou tokens embutidos no código;
- envio de documentos a ambientes não autorizados.

## Monitoramento

Acompanhar falhas por etapa, duração, quantidade de chamadas, páginas e caracteres enviados, correções estruturais, evidências aceitas/rejeitadas, retentativas e alterações humanas posteriores.

A implementação de benchmark real rotulado foi deliberadamente deixada fora desta versão; qualquer conclusão de acurácia continua exigindo validação específica futura.
