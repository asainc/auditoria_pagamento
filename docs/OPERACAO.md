# Operação e configuração

## 1. Configuração sem segredos

`config/app.settings.json` contém apenas configuração versionável, como ambiente, limites, CORS e parâmetros de execução. Os defaults jurídicos/operacionais dos campos ficam em `config/calculation_policy.json`.

Segredos são fornecidos por ambiente ou `.env` e nunca devem aparecer em código, logs, documentação ou fixtures.

Variáveis relevantes incluem:

- `API_TOKEN` ou `OPENAI_API_KEY`;
- `OPENAI_MODEL`;
- `OPENAI_BASE_URL` quando aplicável;
- `OPENAI_REASONING_EFFORT`;
- `GATEWAY_TOKEN` fora do ambiente local;
- `APP_DATA_DIR`;
- `CORS_ORIGINS`.

`load_settings()` usa ambiente > `.env` > JSON > defaults técnicos.

## 2. Política de cálculo

`config/calculation_policy.json` é versionado junto ao código. Depois de qualquer edição, execute:

```bash
python scripts/generate_parameter_catalog.py
python scripts/generate_parameter_docs.py
python scripts/generate_contracts.py
```

A mudança deve ser acompanhada de teste e justificativa. Critérios jurídicos/regulatórios exigem validação competente antes da implantação.

## 3. Persistência

`APP_DATA_DIR` contém estado local da aplicação, incluindo SQLite e documentos recebidos. O SQLite registra:

- metadados/documentos;
- estado/resultados de extração;
- auditoria técnica;
- alterações de parâmetros;
- estado de índices.

Não use dados reais não anonimizados em desenvolvimento/teste. A retenção dos dados em produção deve ser definida pela governança da organização.

## 4. Upload

`POST /api/documentos/upload` valida quantidade, tamanho, extensão/conteúdo PDF, senha, nome de processo/sequência, hash e páginas. Arquivos não são acessados por caminho fornecido pelo cliente; a API usa identificadores opacos.

## 5. Extração

A extração é assíncrona. Estados possíveis ficam persistidos para que reinício de processo não simule sucesso. Jobs interrompidos podem ser reiniciados explicitamente.

A configuração pode ser consultada sem revelar token. Erros do provedor são traduzidos para códigos/mensagens operacionais sem ecoar segredo.

## 6. Índices

`IndexService` consulta catálogo, status e atualização. Cálculo e substituição das planilhas compartilham lock para evitar leitura de arquivo enquanto ele está sendo atualizado.

O atualizador consulta a navegação do DrCalc para descobrir os identificadores vigentes das categorias de preços/custos, mercado financeiro e cálculos judiciais. Os IDs mantidos no código servem somente como fallback; dessa forma, uma mudança de identificador no site não deve ser interpretada automaticamente como ausência de séries.

A fonte primária passou a ser o próprio formulário **Séries históricas** do DrCalc. O backend identifica dinamicamente os campos de categoria, período inicial, período final e indexador, preserva os campos ocultos/defaults publicados pelo site e submete o formulário pelo método GET ou POST informado na página. Isso é importante porque o valor de uma opção do seletor não representa necessariamente uma URL histórica independente. A abordagem anterior podia montar `it=<valor>` e receber novamente apenas a tela de consulta, sem dados.

Para o projeto, a consulta histórica parte de 2000 — mesma origem temporal das planilhas locais distribuídas no pacote — e termina no mês corrente disponível no formulário. Respostas em formato `Mês/Ano`, `Ano + Mês`, matriz `Ano x meses` ou datas diárias são aceitas. Quando a resposta expõe simultaneamente **número-índice** e **variação percentual**, as duas grandezas são separadas: colunas locais configuradas como `rate_decimal` recebem variações; colunas `value_index` recebem somente número-índice explícito. Métrica genérica/ambígua não substitui uma coluna de número-índice.

O mecanismo antigo de descoberta por links permanece apenas como fallback para compatibilidade com versões anteriores do site. Falha isolada de um indexador não cancela automaticamente a leitura das demais séries da categoria.

Uma atualização só é marcada como confirmada quando o resultado do atualizador informa sucesso. Em falhas externas, as planilhas anteriores são preservadas e a interface recebe uma mensagem operacional sem expor detalhes internos. O timeout por requisição é configurável por `index_timeout_seconds` e, no pacote padrão, está em 30 segundos.

O resultado registra `indices_sha256`; o PDF auditável pode exigir o mesmo snapshot esperado.

## 7. Logs técnicos

`AuditFormatter` emite JSON com metadados selecionados: evento, request ID, status, duração e tipo de erro. O middleware não registra payload, documento, número de processo, cabeçalhos de autenticação ou valores de parâmetros.

## 8. Auditoria de alterações humanas

`POST /api/auditoria/parametros` grava evento imutável de edição. O frontend agrupa digitação contínua por 650 ms para evitar um evento por tecla, mas preserva a transição lógica anterior → novo valor.

Para processo real, o servidor acrescenta o valor/origem automáticos conhecidos. Para rascunho manual, registra apenas a edição do rascunho.

O campo `ator_tecnico` é `local` em ambiente local. Em ambiente não local, um subject confiável pode vir de `X-Authenticated-Subject`; o backend grava apenas hash truncado. O header deve ser injetado por gateway autenticado e não aceito diretamente da internet sem confiança de rede.

## 9. Execução

Backend:

```bash
python -m uvicorn backend.principal:aplicacao --host 127.0.0.1 --port 8000
```

Frontend:

```bash
cd frontend
npm ci
npm start
```

Validação:

```bash
python -m pytest
cd frontend && npm test
```

## 10. Atualização da documentação gerada

```bash
python scripts/generate_code_reference.py
python scripts/generate_parameter_docs.py
python scripts/generate_parameter_catalog.py
python scripts/generate_contracts.py
```

A documentação temática explica arquitetura e fluxo; a referência função-a-função é gerada das docstrings para evitar manutenção duplicada.
