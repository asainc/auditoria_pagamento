# Model Card — Extração documental por IA

## Finalidade

O componente de IA lê PDFs de um processo e propõe estrutura para revisão humana: classificação, parcelas, parâmetros de correção/juros, encargos, prescrição, compensação, duplo índice e eventos financeiros.

Não executa o cálculo e não substitui análise jurídica.

## Integração

- provedor: OpenAI;
- modelo configurável por `OPENAI_MODEL`;
- padrão atual do projeto: `gpt-5.6-sol`;
- Responses API com PDFs;
- Structured Outputs;
- `store=False`.

A disponibilidade e o comportamento do modelo precisam ser verificados no ambiente de implantação.

## Entradas

- conjunto de PDFs do mesmo processo;
- sequência de cada anexo;
- `_base.md` com regras comuns;
- prompt especializado;
- catálogo real de índices;
- schema atual dos parâmetros.

## Saída

Cada tarefa devolve `ExtractionFragment`. Após validação e consolidação, `ExtractionResult` contém:

- evidências brutas (`campos`);
- parcelas;
- eventos financeiros;
- alertas;
- `parametros_consolidados`;
- `decisoes_cronologicas`;
- `ajustes_operacionais` posteriores à IA.

## Explicabilidade

Cada evidência possui fonte, página, trecho, escopo, natureza e efeito. A decisão cronológica consolidada registra documento, página, sequência e motivo técnico da escolha.

O operador pode comparar valor automático com alterações humanas na aba de logs. O histórico de revisão é persistido como eventos.

## Controles

- PDFs tratados como conteúdo não confiável;
- instruções no documento não substituem o prompt do sistema;
- jurisprudência/terceiros não viram comando do caso;
- evidência sem fonte válida é descartada;
- valores passam pela validação Pydantic interna;
- conflitos não resolvidos geram alerta;
- defaults não são inventados pela IA;
- revisão humana é obrigatória antes do cálculo.

## Riscos e limitações

Riscos conhecidos incluem leitura incompleta de scan/tabela, associação incorreta entre data e valor, confusão entre pedido e comando, interpretação errada de reforma parcial, omissão de parcela, trecho correto com papel processual incorreto e cenários jurídicos não representáveis pelo contrato.

A regra de cronologia reduz riscos, mas não prova correção jurídica. A semântica de sucessão decisória e seus critérios de consolidação exigem validação do time jurídico para uso institucional.

## Métricas

O projeto **não declara acurácia, precisão, recall ou taxa de acerto** sem benchmark rotulado.

`tests/test_extraction_evaluation.py` é uma suíte de regressão lógica, não uma medição de qualidade do LLM.

Uma avaliação formal deve usar processos anonimizados/sintéticos ou base autorizada, com gabarito revisado, e medir por domínio:

- classificação documental;
- parcelas (detecção e valor/data);
- parâmetros;
- natureza/efeito;
- consolidação cronológica;
- jurisprudência versus caso concreto;
- eventos financeiros;
- taxa e tipo de correção humana.

## Monitoramento recomendado

Registre versão dos prompts, modelo, hash/versão de contratos e taxa de edição humana por campo. Monitore mudanças na distribuição documental e no desempenho em benchmark antes de promover nova versão.

Defina limiares e periodicidade de revalidação com responsáveis técnicos e de negócio. A retenção de evidências/documentos e o tratamento de dados pessoais devem seguir orientação de Segurança, Compliance e DPO.
