# Fluxo visual da extração

```mermaid
sequenceDiagram
    participant U as Usuário
    participant A as Angular
    participant B as FastAPI
    participant F as File Manager corporativo
    participant O as OCR corporativo
    participant T as text_generator
    participant C as Consolidação Python

    U->>A: envia PDFs
    A->>B: POST /documentos/upload
    B->>F: upload temporário
    F-->>B: file_id
    B->>O: OCR híbrido por file_id
    O-->>B: texto detalhado / workflow_id
    B->>O: consulta workflow quando necessário
    O-->>B: texto por página
    B->>F: exclusão do arquivo remoto
    loop prompts 00..09
        B->>T: prompt especializado + texto OCR
        T-->>B: JSON estruturado
    end
    B->>C: evidências e fatos
    C-->>B: cronologia + parâmetros consolidados
    B-->>A: resultado para revisão
    A-->>U: conferência humana
```

## Exemplo conceitual

```text
PDF: 123_4.pdf
  ↓ OCR
PÁGINA 7: "... juros moratórios de 1% ao mês desde ..."
  ↓ prompt especializado
campo: parametros.juros_moratorios_taxa
valor: 1
página: 7
natureza: comando_decisorio
  ↓ validação Python
ChronologyReducer
  ↓
parâmetro sugerido para revisão humana
```
