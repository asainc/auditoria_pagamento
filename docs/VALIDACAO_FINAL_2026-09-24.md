# Validação final — 24/09/2026

Esta entrega consolida as correções da conexão corporativa de IA, TLS e cobertura real dos índices.

## Verificações executadas

- `pytest -q`: **136 testes aprovados**.
- `python scripts/validate_architecture.py`: arquitetura aprovada; frontend Angular, API FastAPI e motor Python permanecem separados.
- Testes Node independentes de instalação (`node --test tests/*.test.mjs`): **13 aprovados e 4 ignorados** por dependerem de artefatos corporativos locais.
- Verificação direta do IPCA-15 instalado:
  - primeira competência observada: `2000-05`;
  - última competência observada: `2026-04`;
  - competência máxima de atualização suportada: `2026-05`.

## Escopo validado

- catálogo de índices calculado a partir das planilhas reais, sem intervalo final hardcoded;
- competência automática limitada à cobertura do índice selecionado;
- erro estruturado quando a competência necessária estiver fora da série ou em uma lacuna;
- atualização externa preserva os arquivos anteriores quando a substituição não puder ser confirmada;
- diagnóstico seguro da conexão `text_generator`;
- validação TLS obrigatória usando CA explícita ou repositório confiável do sistema operacional.

## Limites da validação

Os testes automatizados não comprovam conectividade com a infraestrutura corporativa real nem atualidade da fonte externa DrCalc. Essas validações dependem da estação, VPN/proxy, credenciais e permissões do ambiente autorizado. Nenhuma credencial real ou PDF de produção foi usado nesta validação.
