# Validação

## Backend

```bash
python -m pytest
python scripts/validate_architecture.py
```

A suíte cobre motor, contratos, cronologia, política operacional, imports e integração corporativa com dublês sem rede.

### Integração corporativa

`tests/test_bradesco_bridge.py` simula upload, OCR assíncrono, consulta de workflow, limpeza remota e geração de texto. O teste verifica que a aplicação chama as funções do módulo corporativo sem executar HTTP real.

Uma validação end-to-end real precisa ocorrer na rede autorizada e deve começar com PDF sintético.

## Frontend

Quando as dependências aprovadas estiverem disponíveis:

```powershell
cd frontend
npm test
npm run build
```

## Gate arquitetural

A validação impede reintrodução de Streamlit, acesso direto do frontend ao motor e referências à integração externa removida.

## Resultado desta entrega

- 104 testes Python aprovados.
- 28 testes do frontend aprovados; 4 testes de governança dependentes de lockfile corporativo ficaram ignorados, como previsto.
- `validate_architecture.py` aprovado.
- O build Angular não foi concluído nesta sessão porque o projeto deliberadamente não inclui um `package-lock.json` corporativo; o `prebuild` bloqueou a compilação antes de instalar dependências fora do fluxo autorizado.
- Não houve chamada real aos serviços corporativos; OCR e geração de texto foram validados com dublês de teste.
