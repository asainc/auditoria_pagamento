# Validação da correção de conexão e TLS — 24/09/2026

## Escopo

Foi alterada apenas a camada de transporte da integração corporativa. O motor de cálculo,
os prompts e o processamento local dos PDFs não foram modificados.

## Decisão TLS

- `BRADESCO_CA_BUNDLE` vazio: usar o repositório confiável do sistema operacional por
  meio de `ssl.create_default_context()`. No Windows isso usa o Windows Certificate Store.
- `BRADESCO_CA_BUNDLE` preenchido: usar o bundle PEM explicitamente informado.
- Verificação de hostname e `CERT_REQUIRED` permanecem obrigatórios.
- `verify=False` não é utilizado.

## Validação automatizada

Comando executado:

```text
pytest -q
```

Resultado local desta entrega: **131 testes aprovados**. Os testes de
integração corporativa usam respostas simuladas e não enviam PDFs, prompts processuais,
tokens ou credenciais para a rede.

## Validação no ambiente corporativo

1. Reiniciar o backend após substituir os arquivos.
2. Manter `BRADESCO_CA_BUNDLE=` vazio se a CA corporativa já estiver instalada no Windows.
3. Executar `python scripts/test_text_generator_connection.py`.
4. Confirmar no diagnóstico `tls_origem_confianca`.
5. Só depois testar um PDF sintético pesquisável.

A conexão real não é considerada validada até o teste ser executado na estação/rede
corporativa autorizada.

## Teste local adicional do canal HTTPS

Foi criado temporariamente um servidor HTTPS local com uma CA sintética descartável. O cliente
aceitou a conexão apenas quando o bundle da CA foi configurado e rejeitou o mesmo servidor
quando a CA não estava na cadeia de confiança. Nenhum certificado de teste foi incluído no pacote.
