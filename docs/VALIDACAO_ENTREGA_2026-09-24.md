# Validação da entrega consolidada — 2026-09-24

Esta entrega consolida as melhorias técnicas de prioridade média/alta, exceto o benchmark real de extração, e inclui a correção do fluxo de cálculo manual em instalações atualizadas sobre bases locais antigas.

## Validações executadas

- `python -m pytest -q`: **121 testes aprovados**.
- `python scripts/validate_architecture.py`: **aprovado**.
- `npm test` no frontend: **28 aprovados, 4 ignorados por dependerem do lockfile/catálogo Nexus corporativo, 0 falhas**.
- regressão específica do fluxo manual: gravação da auditoria de parâmetro seguida de `POST /api/calculos` com `origem_calculo=manual` e `numero_processo=null`: **HTTP 200**.
- migração SQLite: uma tabela `parameter_changes` legada é preservada como `parameter_changes_legacy_vN` e migrada para o contrato atual antes da criação dos índices.

## Limitações de validação

- chamadas reais ao `gpt_bradesco.text_generator` não foram executadas fora da rede corporativa;
- `npm run build` depende do `package-lock.json` e dos artefatos efetivamente disponíveis/autorizados no Nexus corporativo;
- regras jurídicas, retenção e uso de dados pessoais continuam exigindo validação das áreas responsáveis.
