# Feedback humano e aprendizado supervisionado

## Objetivo

A aplicação transforma a revisão humana em supervisão estruturada sem sobrescrever a predição original da IA. O objetivo é medir erros, formar exemplos confiáveis e reutilizar somente exemplos aprovados para melhorar extrações futuras.

## Princípio de governança

`feedback humano` não é automaticamente `ground truth`.

O fluxo é:

1. a extração original é persistida sem alteração;
2. ao confirmar a revisão, o backend compara IA × estado revisado;
3. cada divergência vira um evento imutável de feedback;
4. correções entram como `pending`;
5. um curador classifica o motivo e aprova ou rejeita o exemplo;
6. somente exemplos aprovados entram em `training_examples`;
7. snapshots de dataset congelam IDs e hashes dos exemplos aprovados;
8. exemplos aprovados podem ser recuperados localmente como few-shot para a mesma tarefa;
9. nenhuma correção altera pesos do modelo automaticamente.

A decisão de usar fine-tuning deve ocorrer somente após benchmark suficiente e validação de Jurídico/Compliance/DPO e governança de modelos quando aplicável.

## Dados capturados

Para cada campo/parcela são armazenados, quando disponíveis:

- campo revisado;
- ação: confirmado, corrigido, removido ou adicionado;
- valor original da IA;
- valor humano;
- documento, página e evidência original;
- tipo de documento;
- versão dos prompts;
- modelo configurado;
- versão do pipeline;
- motivo da correção após curadoria;
- revisor pseudonimizado por hash;
- data/hora;
- status da curadoria.

O texto integral do PDF não é copiado para a tabela de feedback. O evento mantém apenas a evidência já vinculada à extração.

## Parcelas

A comparação inclui os campos estruturados de parcela usados pela extração, como data, valor, descrição, tipo de verba e multiplicador. Isso permite analisar separadamente erros de data, valor, associação ao contrato e descrição.

## Curadoria

A tela `Qualidade IA` apresenta correções pendentes. O curador pode selecionar uma taxonomia de causa, aprovar ou rejeitar o exemplo. Exemplos rejeitados não entram no repositório de aprendizado.

## Reutilização de exemplos

O retrieval é local e não usa uma segunda chamada de IA. Para cada tarefa, o sistema:

1. busca somente exemplos aprovados da mesma tarefa;
2. calcula similaridade lexical simples com o contexto atual;
3. seleciona no máximo `LEARNING_MAX_EXAMPLES_PER_TASK`;
4. limita o bloco a `LEARNING_MAX_CHARS_PER_TASK`;
5. informa explicitamente ao modelo que exemplos históricos não são fatos do processo atual.

Essa abordagem reduz risco de contaminação entre campos e evita custo de embeddings/modelos adicionais nesta etapa do projeto.

## Dataset versionado

`training_dataset_versions` registra um snapshot imutável dos exemplos aprovados por ID e hash. O snapshot permite reproduzir avaliações futuras e saber exatamente qual conjunto sustentou uma alteração de prompt/pipeline.

## Métricas recomendadas

A tela de qualidade acompanha taxa de intervenção humana e distribuição por campo. Para homologação de novas versões, mantenha também um benchmark congelado separado do conjunto usado como few-shot e avalie, por campo, métricas como exact match, precision/recall quando aplicável, falso positivo, falso negativo, acerto da evidência, página e associação de contrato.

Nunca avalie uma nova versão somente nos mesmos exemplos usados para instruí-la.
