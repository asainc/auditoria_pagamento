# Dependências npm e governança corporativa

## Objetivo

Este projeto utiliza **somente pacotes oficiais publicados no registry npm** no frontend. Não há forks, cópias locais de bibliotecas de terceiros, tarballs versionados em `frontend/vendor`, dependências por Git ou pacotes fictícios usados para contornar o Nexus corporativo.

A estratégia adotada é conservadora: quando uma versão específica gera HTTP 403 no Nexus, a árvore só é alterada para outra **versão oficial** quando essa versão continua dentro da faixa semântica declarada pelo consumidor. Se não houver alternativa oficial compatível, a dependência é mantida e deve ser tratada pela governança do repositório corporativo.

## Decisões aplicadas

| Componente | Situação anterior | Situação atual | Justificativa |
| --- | --- | --- | --- |
| `browserslist` | Cópia local modificada para retirar o atualizador | `browserslist@4.28.9` oficial | Remove manutenção de fork e volta à cadeia suportada pelo ecossistema Angular. |
| `update-browserslist-db` | Removido por fork do Browserslist | `update-browserslist-db@1.3.3` oficial | O Browserslist oficial depende do atualizador. A versão 1.3.3 substitui a 1.3.2 que havia recebido 403, sem alterar a API do Angular. |
| `negotiator` | `1.1.0`, que solicita `content-type@^2.1.0` | `negotiator@1.0.0` oficial | Os consumidores do projeto declaram `negotiator@^1.0.0`; a versão 1.0.0 está dentro da faixa e não depende de `content-type`. |
| `content-type` em `body-parser` | `2.1.0` por resolução mais recente | `2.0.0` oficial | `body-parser` declara `content-type@^2.0.0`; portanto 2.0.0 é uma resolução válida. |
| `content-type` em `type-is` | `2.1.0` por resolução mais recente | `2.0.0` oficial | `type-is` declara `content-type@^2.0.0`; portanto 2.0.0 é uma resolução válida. |
| `content-type@1.0.5` | Presente para consumidores 1.x | Mantido | Não deve ser substituído por 2.x quando o consumidor declara uma faixa 1.x. |

## Por que `update-browserslist-db` voltou

A prioridade desta variante é **usar somente dependências oficiais e suportadas pelas faixas declaradas**. O Angular 21.2.21 depende de uma linha atual de Browserslist por meio de `@angular/build`. O Browserslist oficial dessa linha declara `update-browserslist-db` como dependência.

Remover o pacote mantendo o mesmo Browserslist exige modificar a biblioteca, manter um fork local ou forçar uma combinação não declarada pelo fornecedor. Essas alternativas foram retiradas do projeto porque aumentam risco operacional, manutenção e esforço de homologação.

Portanto, nesta variante:

```text
Angular 21.2.21
  -> Browserslist oficial 4.28.9
      -> update-browserslist-db oficial 1.3.3
```

Se a governança corporativa bloquear também `update-browserslist-db@1.3.3`, a ação recomendada é solicitar a liberação/homologação da versão ou obter da governança a versão oficial autorizada. O projeto não deve criar um pacote substituto para contornar essa restrição.

## Como `content-type@2.1.0` foi evitado sem quebrar as faixas declaradas

O caso de `content-type` permite uma solução diferente. O pacote `negotiator@1.1.0` passou a declarar `content-type@^2.1.0`, mas os consumidores do projeto (`accepts` e `make-fetch-happen`) aceitam `negotiator@^1.0.0`. Assim, o projeto fixa a versão oficial `negotiator@1.0.0`, que não possui a dependência `content-type`.

Nos outros consumidores, `body-parser` e `type-is` declaram `content-type@^2.0.0`; por isso `content-type@2.0.0` continua dentro da faixa publicada. Não existe override de `content-type` abaixo da faixa declarada.

## Controles automáticos

Antes de instalar ou compilar, execute:

```powershell
cd frontend
npm run verify:lock
```

O script valida que:

- não existe pasta/vendor ou dependência `file:` usada como biblioteca;
- todos os pacotes do lockfile possuem origem `https://registry.npmjs.org/` e integridade SHA-512;
- não há dependências Git;
- `update-browserslist-db@1.3.2` não reapareceu;
- `content-type@2.1.0` não reapareceu;
- `negotiator@1.0.0` satisfaz as faixas dos consumidores atuais;
- `content-type@2.0.0` só é forçado em consumidores que declaram `^2.0.0`.

Esses controles verificam coerência do projeto, **não homologação corporativa**. A existência de um pacote no npm público não significa que ele esteja autorizado no Nexus do banco.

## Instalação no ambiente corporativo

```powershell
cd frontend
npm run verify:lock
npm ci
npm run build
```

Não altere o registry para contornar o Nexus, não desabilite verificações TLS e não inclua tokens/credenciais no `.npmrc` versionado. Se houver 403, registre pacote, versão e URL do repositório corporativo e solicite validação ao time responsável.

## Atualização de dependências

Qualquer atualização deve seguir este fluxo:

```text
nova versão oficial
  -> verificar faixas semânticas dos consumidores
  -> regenerar package-lock.json em ambiente autorizado
  -> npm run verify:lock
  -> npm ci
  -> npm test
  -> npm run build
  -> registrar decisão e evidências
```

Evite adicionar overrides apenas para “fazer instalar”. Overrides só devem ser usados quando a versão escolhida é oficial, está dentro da faixa aceita pelo consumidor e a decisão está documentada.

## Limites da validação desta entrega

Foi possível validar localmente a estrutura do lockfile e os testes de regressão das versões oficiais. A tentativa de `npm ci --offline` não pôde ser concluída porque o cache desta sessão não contém todos os tarballs (por exemplo, `zod-to-json-schema@3.25.2`). Isso não indica erro nessa dependência; apenas impede validar a instalação completa sem rede. O `npm ci` real e o build no ambiente do banco continuam sendo a validação final de disponibilidade e governança.

## Complemento: pré-verificação completa e aprovação explícita

Para o procedimento com consultas a todas as versões do frontend no Nexus, download controlado dos tarballs e gate de homologação consulte [VALIDACAO_GOVERNANCA_FRONTEND.md](VALIDACAO_GOVERNANCA_FRONTEND.md). Nenhuma substituição adicional foi assumida aprovada sem evidência.
