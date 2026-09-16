# Browserslist (cópia local modificada)

- Origem: pacote `browserslist` versão `4.28.1`, licença MIT (arquivo LICENSE preservado).
- Modificações: removida a dependência `update-browserslist-db` do manifesto, removida a importação e execução do comando `--update-db` no CLI e adaptado o aviso de dados desatualizados.
- Compatibilidade: permanecem consultas de navegadores, APIs e arquivos de dados originais.
- Trade-off: a versão 4.28.1 substitui a versão 4.28.9 anteriormente travada; revisar impacto e aprovar uso da cópia modificada na governança corporativa.
- Manutenção: atualizar `caniuse-lite` por processo corporativo, rever este fork a cada atualização de Angular/Browserslist; não instalar pacotes fora do Nexus aprovado.
