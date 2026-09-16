# Validação de governança do frontend

**Escopo:** `frontend/`  
**Baseline:** Node.js 22.12.0, npm 10.9.0, Angular 21.2.19  
**Estratégia:** Nexus-first, sem lockfile público pré-fixado.

## Controles implementados

1. Dependências diretas com versões exatas.
2. Ausência de `overrides` no `package.json`.
3. Ausência de dependências `file:`, Git e forks locais.
4. Verificação explícita de Node.js e npm antes da resolução.
5. Verificação do registry corporativo antes da resolução.
6. Geração do lockfile exclusivamente pelo Nexus.
7. Validação pós-resolução de host/caminho dos artefatos e integridade.
8. `npm ci` somente depois de existir lockfile corporativo validado.

## Fluxo recomendado

```powershell
cd frontend
npm run env:check
npm run nexus:check
npm run nexus:lock
npm run verify:lock
npm run install:corporate
npm test
npm run build
```

O `nexus:lock` é a etapa que precisa ocorrer dentro da rede corporativa. Se houver HTTP 403, o pacote indicado é uma dependência oficial exigida pela árvore resolvida. O projeto não substitui esse artefato silenciosamente.

## O que precisa ser validado pela governança

- disponibilidade e autorização de cada versão resolvida;
- políticas para pacotes com scripts de instalação;
- licenças;
- vulnerabilidades/SCA;
- política de uso do `npm audit` ou ferramenta corporativa equivalente;
- regras adicionais do Nexus não visíveis no projeto.

Sem acesso ao catálogo de aprovação ou ao Nexus real, não é tecnicamente possível declarar o frontend como homologado.
