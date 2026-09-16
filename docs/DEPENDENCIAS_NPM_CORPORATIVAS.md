# Dependências npm corporativas — estratégia Nexus-first

## Baseline

- Node.js: `22.12.0`
- npm: `10.9.0`
- Angular: `21.2.19`
- TypeScript: `5.9.3`
- RxJS: `7.8.2`

O objetivo desta variante é reduzir ambiguidades de resolução e impedir que o projeto contorne a governança. O frontend declara somente dependências diretas oficiais com versões exatas. Não há `overrides`, forks, dependências `file:`, URLs Git nem bibliotecas modificadas localmente.

## Por que o package-lock.json não é distribuído nesta variante

O lockfile anterior foi produzido para Angular `21.2.21` e continha decisões manuais sobre dependências transitivas. Reutilizá-lo com Angular `21.2.19` seria incorreto.

Além disso, um lockfile criado contra `registry.npmjs.org` pode fixar artefatos que o Nexus corporativo não disponibiliza. Portanto, o primeiro `package-lock.json` desta nova linha deve ser resolvido **dentro do Nexus** usando exatamente Node.js 22.12.0 e npm 10.9.0.

O comando é:

```powershell
cd frontend
npm run nexus:lock
```

Esse comando:

1. valida Node.js e npm;
2. valida que o registry configurado é o Nexus corporativo;
3. remove somente um lockfile local anterior dessa tentativa;
4. executa `npm install --package-lock-only --ignore-scripts` pelo Nexus;
5. valida que os artefatos resolvidos apontam exclusivamente para o repositório corporativo;
6. exige integridade SHA-512 quando fornecida pelo registry.

Depois da revisão, o lockfile deve ser versionado no Git. As instalações seguintes usam `npm run install:corporate`, que executa `npm ci`.

## Browserslist, content-type, negotiator e outros transitivos

Esses pacotes não são declarados diretamente pela aplicação. Eles chegam pela árvore oficial das ferramentas Angular e de seus consumidores. Nesta estratégia o projeto **não força versões transitivas** apenas para eliminar um 403. Isso evita combinações não testadas, como substituir uma versão exigida por outra apenas porque está disponível no Nexus.

Se o Nexus rejeitar um transitivo oficial durante `npm run nexus:lock`, o erro identifica o pacote e a versão exigidos. Nesse caso existem somente duas alternativas tecnicamente seguras:

- homologar/liberar o artefato oficial no Nexus; ou
- alterar uma dependência direta para uma versão oficialmente compatível cuja árvore completa esteja aprovada.

Não são adotados forks locais, tarballs copiados manualmente ou pacotes fictícios para contornar a política.

## Registry

O projeto herda o registry npm configurado pelo ambiente corporativo. Antes de qualquer resolução, `npm run nexus:check` exige por padrão:

```text
https://nexusrepository.bradesco.com.br:8443/repository/escp-npm-central/
```

Caso a governança altere host ou caminho, use `CORPORATE_NPM_HOST` e `CORPORATE_NPM_PATH` conforme orientação oficial. Não coloque tokens ou credenciais em arquivos versionados.

## Limite da garantia

Usar somente pacotes oficiais e resolver a árvore exclusivamente no Nexus elimina uma classe importante de conflitos de origem. Isso **não garante homologação**: um pacote oficial ainda pode estar bloqueado por licença, vulnerabilidade, política de scripts, versão, ausência de mirror ou regra interna. A aprovação final depende do catálogo e das políticas corporativas.
