# Avaliação da extração documental

A pasta `evals/` contém casos **sintéticos e anonimizados** usados para regressão do pipeline de consolidação. Eles não são dados de produção e não constituem, por si só, uma medida de acurácia jurídica do modelo.

## O que é medido automaticamente

`extraction_gold.json` descreve evidências já estruturadas e o estado esperado após `ChronologyReducer`. O teste verifica, de forma determinística, precedência entre pedido e comando decisório, manutenção, alteração, conflito na mesma sequência e afastamento explícito.

Para medir a qualidade do LLM, crie um conjunto separado de documentos anonimizados/sintéticos com rótulos revisados por especialistas e compare a saída do provedor com um arquivo de predições por meio de `python scripts/evaluate_extraction.py --gold <arquivo> --predictions <arquivo>`. Uma métrica só deve ser reportada depois que o conjunto de referência tiver sido revisado pelo time jurídico responsável pelo caso de uso.

## Formato de benchmark de campos

O avaliador espera objetos com `cases[].expected_fields`, onde cada campo usa uma chave estável e um valor normalizado, e um arquivo de predições com `cases[].predicted_fields`. A comparação é exata por campo; ausência e divergência são exibidas separadamente para facilitar análise de causa raiz.

Não use documentos de produção não anonimizados neste diretório.
