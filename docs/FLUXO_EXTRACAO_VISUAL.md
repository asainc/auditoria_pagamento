# Fluxo visual da extração

```mermaid
sequenceDiagram
    participant U as Usuário
    participant A as Angular
    participant B as FastAPI
    participant P as PyMuPDF
    participant T as gpt_bradesco.text_generator
    participant C as Consolidação

    U->>A: Anexa PDFs
    A->>B: POST /documentos/upload
    B->>B: Valida e persiste os arquivos
    B->>P: Abre bytes do PDF
    P-->>B: Texto por página
    loop prompts especializados 00..09
        B->>T: prompt + string de texto + schema
        T-->>B: JSON estruturado
    end
    B->>C: Valida evidências e cronologia
    C-->>A: parâmetros consolidados
    A-->>U: campos preenchidos para revisão
```

A leitura do PDF ocorre localmente. Não há upload para serviço de OCR no fluxo de extração.


## Seleção de contexto

Antes de cada prompt, `PromptPageRouter` pontua as páginas por termos do domínio da tarefa. Quando nenhum termo é encontrado, utiliza páginas representativas do início/fim de cada documento. A decisão é determinística e suas métricas são auditadas.
