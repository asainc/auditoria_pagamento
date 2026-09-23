# Operação

## Configuração mínima

Copie `.env.example` para `.env` e preencha apenas valores autorizados. O projeto aceita token corporativo já emitido ou identificador/senha do serviço. Nunca registre esses valores em tickets, prints ou commits.

Campos necessários para habilitar a extração:

- `BRADESCO_IAGEN_AMBIENTE`;
- `BRADESCO_OCR_CONTAINER`;
- `BRADESCO_TEXT_MODEL`;
- `BRADESCO_AUTHORIZATION_TOKEN` **ou** `BRADESCO_IDENTIFICADOR` + `BRADESCO_SENHA`.

Se a rede interna exigir CA própria, defina `BRADESCO_CA_BUNDLE` com o caminho de um certificado aprovado.

## Inicialização sem ambiente virtual

```cmd
cd CAMINHO_DO_PROJETO
set "PYTHONPATH=%CD%\src;%CD%"
python -m uvicorn backend.principal:aplicacao --reload --host 127.0.0.1 --port 8000
```

Verificações rápidas:

```cmd
python -c "import judicial_calc.data; print('motor OK')"
python -c "import gpt_bradesco; print('módulo corporativo OK')"
```

A importação do módulo corporativo não deve efetuar login automaticamente. A autenticação acontece na primeira chamada necessária.

## Teste operacional recomendado

1. use um PDF sintético sem dados reais;
2. confirme `/api/extracoes/configuracao`;
3. faça upload;
4. acompanhe `/api/extracoes/{processo}/status`;
5. confira se o OCR termina e o arquivo remoto é limpo;
6. confira o JSON extraído;
7. somente depois use documentos autorizados.

## Logs

Logs técnicos podem registrar IDs de requisição sanitizados, status, duração e tipo de erro. Não devem registrar:

- PDFs;
- texto OCR;
- prompt completo;
- resposta completa do gerador;
- tokens de autenticação;
- identificador/senha;
- URL assinada de download.
