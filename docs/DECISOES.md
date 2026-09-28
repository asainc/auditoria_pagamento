# Decisões técnicas vigentes

Este documento registra apenas decisões que continuam válidas no projeto. Ele não é um histórico de releases.

| Decisão | Justificativa | Consequência de manutenção |
|---|---|---|
| Separar Angular, FastAPI, persistência, IA e motor de cálculo | Reduz acoplamento e impede duplicação de fórmulas | Regra financeira deve permanecer em `src/judicial_calc` |
| Usar `scripts/run_backend.py` como único iniciador do Uvicorn | Centraliza host, porta, workers e recarga | Wrappers de SO não devem copiar opções do Uvicorn |
| Limitar a recarga automática a `backend`, `src`, `config` e `prompts` | Arquivos do npm não alteram o backend | `frontend/node_modules` deve permanecer fora do watcher |
| Manter configurações não secretas em JSON e segredos no ambiente | Facilita ajuste sem expor credenciais | Novos segredos não devem ser adicionados a `config/*.json` |
| Validar contratos na fronteira HTTP | Falhas ficam claras antes do processamento | Novos endpoints devem usar modelos tipados |
| Usar `Decimal` para valores financeiros no backend/motor | Evita arredondamento binário indevido | Não converter dinheiro para `float` em regras financeiras |
| Separar o estado funcional do cálculo da execução técnica | Permite rastrear reexecuções e artefatos sem confundir o que o usuário revisou | Persistência deve manter hashes e vínculos explícitos |
| Usar revisão humana antes do cálculo derivado de documentos | Extração automática pode errar | A interface deve sinalizar evidências e exigir confirmação |
| Exibir evidências em `popover="auto"` na camada superior do navegador | Evita recorte pelo painel rolável e pelo visualizador PDF e impede múltiplos balões simultâneos | Novos balões contextuais devem reutilizar `EvidenceInfoComponent` em vez de criar sobreposições absolutas locais |
| Manter predição da IA separada da correção humana | Permite medir qualidade sem reescrever a predição original | Feedback só entra no conjunto de exemplos após curadoria |
| Não fazer aprendizado automático em produção | Mudanças de comportamento precisam ser testáveis e reversíveis | Qualquer alteração de modelo/prompt deve passar por avaliação |
| Não embutir preço presumido do serviço de IA | Tarifas corporativas precisam ser verificadas | Custos só são exibidos quando tarifas verificadas forem configuradas |
| Manter manifesto SHA-256 do motor | Detecta alteração de código do cálculo | Regenerar `docs/motor_sha256.json` ao alterar `src/judicial_calc` |
| Usar testes de referência para cenários completos | Protege comportamento numérico durante refatorações | Mudanças intencionais exigem revisão explícita do cenário esperado |
| Não colocar dados reais não anonimizados em testes/exemplos | Reduz risco de exposição de dados pessoais | Fixtures devem ser sintéticas |

## Critérios que exigem validação institucional

O código implementa comportamentos técnicos, mas não substitui a análise jurídica ou regulatória. Critérios concretos de prescrição, juros, índices, multas, compensação, valor em dobro, honorários, retenção de documentos, acesso a dados e uso de exemplos de IA devem ser homologados pelos responsáveis aplicáveis antes do uso institucional.
