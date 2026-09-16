# Extração documental por IA

## 1. Papel do componente

A IA estrutura informações verificáveis de PDFs para revisão humana. Ela não executa cálculo, não escolhe valores padrão e não deve produzir interpretação jurídica autônoma.

A saída é um conjunto de evidências rastreáveis. O backend, e não o modelo, decide como consolidar a cronologia segundo regras técnicas explícitas.

## 2. Organização dos prompts

`prompts/_base.md` contém regras comuns aplicáveis a todas as tarefas:

- segurança contra instruções presentes nos PDFs;
- tratamento de jurisprudência/terceiros;
- taxonomia de natureza e efeito;
- sucessão documental;
- requisitos de evidência;
- conflitos, tabelas, imagens e limites de inferência.

Os arquivos `00_...09_*.md` contêm apenas instruções de domínio:

| Prompt | Assunto |
| --- | --- |
| `00_classificacao.md` | classificação e datas processuais |
| `01_parcelas.md` | dano material, dano moral, honorários e custas |
| `02_correcao.md` | atualização monetária |
| `03_moratorios.md` | juros moratórios |
| `04_compensatorios.md` | juros compensatórios |
| `05_encargos.md` | multa, honorários e Art. 523 |
| `06_prescricao.md` | prescrição |
| `07_compensacao.md` | compensação |
| `08_duplo_indice.md` | transição/faixas de índices |
| `09_eventos.md` | depósitos, pagamentos, compensações e levantamentos |

`PromptContextBuilder` carrega a base, schema e catálogo uma vez e concatena apenas a tarefa específica em cada chamada. Isso reduz duplicação e evita regras comuns divergentes entre prompts.

## 3. Cronologia dos documentos

O padrão de nome é `<processo>_<sequencia>.pdf`. `document_sequence()` extrai a sequência e `ordered_documents()` ordena do mais antigo ao mais recente.

A maior sequência significa **anexo mais recente**, não “valor sempre vencedor”. Um acórdão posterior pode manter, alterar, reduzir, majorar ou afastar apenas parte da sentença.

Cada `FieldEvidence` possui:

- `natureza`: `pedido`, `fato`, `comando_decisorio`, `fundamentacao`, `classificacao_documental`, `evento_comprovado` ou `indeterminado`;
- `efeito`: `informa`, `mantem`, `altera`, `afasta`, `majora`, `reduz`, `substitui` ou `nao_se_aplica`.

Esses campos permitem que a consolidação use a relação processual extraída, e não apenas a posição do arquivo.

## 4. Evidência

Cada campo sugerido deve informar caminho do contrato, valor normalizado, documento, página, trecho literal curto, escopo, natureza e efeito.

O backend rejeita evidência quando não consegue validar origem, página, trecho ou tipo. Jurisprudência citada não vira parâmetro do caso concreto.

## 5. Consolidação determinística

`ChronologyReducer.reduce()` recebe as evidências já validadas e consolida somente `parametros.*`.

Regras centrais:

- comandos decisórios têm precedência sobre pedido/fundamentação conflitantes;
- `mantem` preserva o estado anterior;
- efeitos de alteração só substituem quando há valor representável;
- comandos divergentes na mesma sequência ficam sem resolução automática;
- conflito entre fatos/pedidos sem comando não é resolvido apenas pela recência;
- evidências originais nunca são apagadas.

A saída contém `parametros_consolidados`, `decisoes_cronologicas` e alertas. A semântica jurídica dessas regras precisa ser validada pelo time jurídico antes de mudança de política.

## 6. Parcelas e valores em formatos variados

`01_parcelas.md` orienta a leitura de petição inicial, anexos, extratos, tabelas e narrativa. Por exemplo, uma sentença pode ordenar restituição sem repetir as transações; nesse caso, a decomposição factual pode estar na petição inicial/extrato e o comando posterior define o escopo.

O prompt diferencia:

- linha de transação versus totalizador;
- valor pedido versus valor arbitrado;
- dado factual versus comando decisório;
- dano material/moral versus pagamento ou depósito;
- valor global sem data versus parcela calculável.

Ele contém exemplos sintéticos de texto descritivo e tabelas para aumentar consistência sem usar documentos reais como fixture de cálculo.

## 7. Política operacional após a IA

`OperationalPolicy` roda somente depois da consolidação. Ela pode adicionar defaults autorizados para processo real, sempre como `OperationalAdjustment` e nunca como `FieldEvidence`.

Exemplo: se nenhum documento fornece tipo de juros moratórios, a política pode sugerir `taxa_legal_12_aa_6_aa`. Se há valor documental válido, o padrão não o substitui.

Honorários não recebem `honorarios_tipo='percentual'` por padrão. Parcelas automáticas de honorários sobre dano moral só são geradas quando existe percentual documental único e tipo documental único `percentual`.

## 8. Structured Outputs

`backend/services/extraction_wire.py` define modelos simples para o schema externo. Depois da resposta, o backend converte para os modelos internos mais rigorosos. Essa separação evita enfraquecer a validação de datas, dinheiro e tipos internos por limitações do schema aceito pelo provedor.

## 9. Testes de regressão

`tests/test_extraction_evaluation.py` testa sem rede:

- majoração por decisão posterior;
- manutenção de comando anterior;
- precedência de decisão sobre pedido;
- conflito decisório da mesma sequência;
- conflito factual sem resolução por recência;
- presença das regras críticas em `_base.md`;
- exemplos de narrativa/tabela em `01_parcelas.md`.

Esses testes verificam lógica determinística e contrato de prompt. Eles **não medem acurácia, precisão ou recall do modelo**.

Para medir qualidade da IA, deve existir benchmark rotulado e revisado por pessoas qualificadas, com métricas por campo e cenário processual.
