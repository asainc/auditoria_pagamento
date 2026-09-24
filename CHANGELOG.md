# Changelog


## 2026-09-24 — TLS corporativo via repositório nativo do SO

- Corrigido o cliente HTTPS para usar a cadeia de confiança nativa do sistema operacional quando `BRADESCO_CA_BUNDLE` estiver vazio.
- No Windows, a integração passa a aproveitar as CAs corporativas instaladas no Windows Certificate Store, sem desabilitar verificação TLS.
- Mantido suporte a bundle PEM explícito para ambientes que exigem CA dedicada.
- Adicionado diagnóstico `tls_origem_confianca` ao script `scripts/test_text_generator_connection.py`.
- Mensagens de falha TLS agora distinguem store do sistema de bundle corporativo inválido/incompleto.
- O motor de cálculo e os prompts de extração não foram alterados.


## 2026-09-24 — Diagnóstico da geração de texto corporativa

- Corrigida a classificação de falhas do `text_generator` que antes podiam aparecer apenas como `bradesco_indisponivel`.
- Credencial ausente agora informa de forma explícita a necessidade de `BRADESCO_AUTHORIZATION_TOKEN` ou `BRADESCO_IDENTIFICADOR` + `BRADESCO_SENHA`.
- Respostas incompatíveis do gateway (`JSON` inválido ou ausência de `response.output_text`) agora possuem código operacional próprio.
- Adicionado `scripts/test_text_generator_connection.py`, que envia somente texto sintético e não lê PDFs.
- Atualizado `.env.example` para documentar corretamente a autenticação exigida pelo `gpt_bradesco.py` distribuído.
- Validação local: 129 testes aprovados; nenhuma chamada real ao ambiente corporativo foi executada.

## 2.0.0 — 2026-09-24

### Corrigido

- migração automática de bases SQLite legadas para o contrato atual da trilha de revisão, sem descartar a tabela original;
- cálculo manual voltou a reproduzir a ordem real da interface: auditoria de parâmetro → confirmação → `/api/calculos`;
- execução corporativa sem virtualenv passa a priorizar o `judicial_calc` da própria pasta `src`;
- falhas de importação do motor e persistência da trilha de revisão retornam erro operacional sanitizado em vez de HTTP 500 genérico.

### Alterado

- restituição em dobro passou a aceitar multiplicador explícito por parcela de dano material, com a flag global somente como fallback;
- extração foi decomposta em leitura PyMuPDF, roteamento de páginas, execução de prompts, normalização estrutural e validação de evidências;
- chamadas ao `text_generator` recebem contexto selecionado deterministicamente por tarefa;
- PDFs sem camada textual utilizável são bloqueados antes da chamada ao serviço corporativo;
- reparo por IA só ocorre após normalização estrutural determinística local;
- jobs de extração passaram a usar fila persistente com lease, retentativas e recuperação após reinício;
- observabilidade técnica passou a registrar métricas estruturais sem persistir conteúdo documental;
- estado Angular foi separado em stores de estado, extração, cálculo e auditoria;
- revisão humana navega para página e trecho de evidência;
- configurações mortas do gerador de texto foram removidas.

### Não incluído

- benchmark real da extração, excluído deste marco a pedido do solicitante.

### Governança

O responsável técnico e a aprovação institucional devem ser registrados pelo processo corporativo de merge/release. Regras jurídicas e de retenção continuam sujeitas à validação das áreas responsáveis.

## 2026-09-24 — Conexão text_generator

- Corrigida propagação de ambiente, CA, timeout e URLs configuradas no .env.
- Preservado contrato mínimo para módulos corporativos legados.
- Diferenciados erros de TLS, timeout e rede com mensagens sanitizadas.
- Incluídos testes de transporte simulado e instruções de diagnóstico no README.

## 2026-09-24 — Índices ausentes no seletor

- Corrigida a verificação do frontend que rejeitava o backend 2.0.0.
- Isolados os resultados do carregamento de processos e índices.
- Incluídos estado de carregamento e tentativa manual no painel de parâmetros.
- Validação: quatro testes de serviços TypeScript isolados e 30 testes Python
  de catálogo/conexão e integração de cálculo aprovados. Sem teste em navegador
  ou build Angular completo nesta revisão.
