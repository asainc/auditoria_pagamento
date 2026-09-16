# Fluxo visual da extração documental

## Entrada e separação de responsabilidades

```mermaid
sequenceDiagram
    participant U as Operador
    participant A as Angular
    participant B as FastAPI
    participant D as DocumentService
    participant X as ExtractionService
    participant O as OpenAI
    participant R as Repository

    U->>A: Envia PDFs
    A->>B: POST /documentos/upload
    B->>D: Valida e persiste arquivos
    B->>X: Inicia revisão de extração
    loop Uma tarefa especializada por vez
        X->>O: PDFs + contexto enxuto + subcontrato
        O-->>X: JSON estruturado + usage
        X->>R: Atualiza status + tokens/custo
    end
    X->>X: Consolida cronologia e conflitos
    X->>R: Persiste resultado revisável
    A->>B: Consulta status/resultado
    B-->>A: Evidências + telemetria
    U->>A: Confere e altera campos
```

## Como uma evidência vira sugestão

```mermaid
flowchart TD
    A[Trecho encontrado] --> B{É do caso concreto?}
    B -- não --> X[Ignorar para consolidação]
    B -- sim --> C{Página e trecho verificáveis?}
    C -- não --> X
    C -- sim --> D[Classificar natureza e efeito]
    D --> E{Campo pertence ao subcontrato?}
    E -- não --> Y[Não retornar nesta tarefa]
    E -- sim --> F[Normalizar valor sem inventar]
    F --> G[Validação Pydantic]
    G --> H[Redutor cronológico]
    H --> I{Conflito inequívoco?}
    I -- sim --> J[Gerar alerta para revisão humana]
    I -- não --> K[Sugerir valor consolidado]
```

## Exemplo sintético

Documento 1 contém pedido de honorários de 20%. Documento 3 contém sentença fixando 10%. Documento 5 contém acórdão majorando para 15%.

```text
123_1.pdf -> pedido               -> 20%
123_3.pdf -> comando decisório    -> 10%
123_5.pdf -> comando decisório    -> 15% (majora)
                                      |
                                      v
                               sugestão: 15%
```

O exemplo é didático e não representa interpretação aplicável a processos reais. A consolidação depende das evidências extraídas e continua sujeita à revisão humana e, quando necessário, à validação jurídica.
