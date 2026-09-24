# Changelog

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
