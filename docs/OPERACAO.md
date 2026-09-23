# Operação da aplicação

## Configuração mínima da extração

A extração automática requer:

- `BRADESCO_TEXT_MODEL` com um deployment autorizado;
- `gpt_bradesco.py` disponível na raiz do projeto com `text_generator` funcional;
- `PyMuPDF` instalado no interpretador Python utilizado pelo backend.

Não é necessário configurar container, File Manager ou workflow de OCR.

## Validação inicial

Use um PDF sintético com camada de texto e confirme:

1. o upload retorna `202`;
2. o status passa por `Extraindo texto dos PDFs com PyMuPDF`;
3. os prompts especializados são executados;
4. o resultado fica `pronto`;
5. os campos aparecem preenchidos para revisão;
6. o cálculo permanece bloqueado até a confirmação humana.

Para conferir a dependência local:

```cmd
python -c "import pymupdf; print(pymupdf.__version__)"
```

## Diagnóstico

Se todas as páginas vierem sem texto, verifique se o PDF é apenas imagem digitalizada. PyMuPDF lê a camada textual existente; ele não executa OCR.

Se a geração falhar, valide separadamente a importação de `gpt_bradesco.py`, a função `text_generator` e o deployment configurado. Não imprima prompts, PDFs, tokens ou conteúdo processual real em logs de suporte.
