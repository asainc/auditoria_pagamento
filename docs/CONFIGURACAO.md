# Configuração do projeto

## 1. Princípio

Configuração deve ficar fora das funções sempre que o valor variar entre ambientes ou operações. Segredos são exceção importante: ficam somente em variáveis de ambiente ou em `.env` local não versionado.

## 2. `config/runtime.json`

Controla apenas como os servidores locais são iniciados.

```json
{
  "backend": {
    "host": "127.0.0.1",
    "port": 8000,
    "workers": 1,
    "access_log": false
  },
  "frontend": {
    "host": "127.0.0.1",
    "port": 4200
  },
  "reload": {
    "directories": ["backend", "src", "config", "prompts"],
    "include_patterns": ["*.py", "*.json", "*.md"],
    "exclude_paths": ["frontend", "frontend/node_modules", ".venv", ".git", "data", "docs", "tests"]
  }
}
```

### Variáveis que substituem valores de execução

| Variável | Tipo esperado | Uso |
|---|---|---|
| `APP_RUNTIME_CONFIG` | caminho | usa outro JSON de execução |
| `BACKEND_HOST` | texto | endereço do backend |
| `BACKEND_PORT` | inteiro de 1 a 65535 | porta do backend |
| `BACKEND_WORKERS` | inteiro de 1 a 16 | processos do backend sem reload |
| `BACKEND_ACCESS_LOG` | booleano | ativa/desativa log HTTP do Uvicorn |
| `FRONTEND_HOST` | texto | endereço do Angular no iniciador conjunto |
| `FRONTEND_PORT` | inteiro de 1 a 65535 | porta do Angular no iniciador conjunto |
| `BACKEND_PYTHON` | caminho | interpretador Python que deve ser usado |

Em modo de recarga, `workers` é forçado a `1`, porque a recarga automática controla o processo do servidor.

## 3. `config/app.settings.json`

Contém limites operacionais não secretos, como tamanho máximo de upload, quantidade de arquivos, quantidade de workers de extração, timeouts e limites de contexto. A leitura é feita por `backend.config.load_settings()`.

A precedência é:

```text
variáveis de ambiente
    > .env local
    > config/app.settings.json
    > valores padrão declarados no modelo Settings
```

## 4. `.env`

Crie `.env` a partir de `.env.example` apenas no ambiente de execução. Não coloque valores reais no repositório.

As principais famílias de variáveis são:

- `BRADESCO_*`: integração corporativa de geração de texto;
- `EXTRACTION_*`: limites e tentativas da extração;
- `AI_FINOPS_*`: cache, limites e custos somente quando houver tarifa verificada;
- `LEARNING_*`: uso controlado de exemplos curados;
- `GATEWAY_TOKEN`: autenticação do ambiente publicado;
- `CORS_ORIGINS`: origens HTTP/HTTPS explicitamente permitidas.

`backend.config.Settings` valida tipos e intervalos. Uma configuração inválida interrompe a inicialização com mensagem indicando os campos a revisar.

## 5. `config/calculation_policy.json`

É a fonte central para os parâmetros apresentados e aceitos operacionalmente. Define:

- campos obrigatórios;
- valores padrão por origem do cálculo;
- rótulos e seções da interface;
- opções de seleção;
- tipos de dano aos quais cada campo se aplica.

O frontend não deve manter uma segunda lista manual equivalente. `scripts/generate_parameter_catalog.py` gera o catálogo TypeScript e `scripts/generate_parameter_docs.py` gera `docs/PARAMETROS.md`.

A escolha jurídica do valor de cada parâmetro em um processo concreto não é decidida pelo JSON; depende da documentação do caso e da revisão humana.

## 6. `config/extraction_tasks.json`

Define limites de saída para cada tarefa de extração. Cada chave corresponde a um arquivo de prompt em `prompts/`.

Exemplo conceitual:

```text
01_parcelas -> prompts/01_parcelas.md -> limite próprio de saída
02_correcao -> prompts/02_correcao.md -> limite próprio de saída
```

## 7. `frontend/public/app-config.json`

Configuração pública entregue ao navegador. Não pode conter segredos. O frontend usa o caminho relativo `/api/...`; em desenvolvimento, o proxy do Angular encaminha essas chamadas ao backend.

Quando `scripts/start-dev.mjs` é usado, o arquivo temporário `frontend/.runtime-proxy.json` é criado com o host/porta efetivos e removido ao encerrar os serviços.

## 8. Validação antes de iniciar

`scripts/check-python-environment.py` compara bibliotecas críticas com `requirements.lock`. O objetivo é impedir que um ambiente Python incompatível seja aceito silenciosamente.

Comandos úteis:

```bash
python scripts/check-python-environment.py
python scripts/run_backend.py --reload
```
