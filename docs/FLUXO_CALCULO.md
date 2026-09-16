# Fluxo completo do cálculo

Este documento acompanha uma execução do início ao fim, indicando arquivo, função, entrada e saída. Ele explica o caminho; assinaturas individuais são geradas em `REFERENCIA_CODIGO.md`.

## 1. Bootstrap

### `frontend/src/main.ts`

Inicializa o Angular e registra `AppComponent`.

**Entrada:** bundle compilado e navegador.  
**Saída:** aplicação Angular ativa.

### `frontend/src/app/app.routes.ts`

A rota principal do cálculo é `/auditoria-pagamentos/calculo`. BJN e AI Ready usam páginas template e não participam do motor.

## 2. Criação do rascunho

### `blankDraft(process, origin)` — `frontend/src/app/core/calculation-mapper.ts`

Cria o estado inicial.

**Manual:** `origin='manual'`, sem número de processo, defaults de teste vindos do catálogo gerado.  
**Processo:** `origin='processo'`, número do processo definido e parâmetros inicialmente vazios para receber extração/política.

Cada rascunho possui `draftId` técnico aleatório usado na trilha de alterações manuais.

## 3. Processo real: documentos e extração

### `WorkspaceStore.selectProcess(process)`

1. desliga o modo manual;
2. seleciona o processo;
3. cria/recupera o rascunho específico;
4. carrega histórico de alterações do processo;
5. busca documentos;
6. inicia polling do job de extração.

### `DocumentService.receive()` — `backend/services/documents.py`

No upload, valida PDF, associação pelo nome, tamanho, hash e páginas; persiste metadados e bytes em área controlada.

### `ExtractionService.start()` / execução em background

Obtém documentos ordenados pela sequência, monta contexto e executa os prompts especializados.

### `PromptContextBuilder.build()` — `backend/services/prompt_context.py`

**Entrada:** processo e metadados dos documentos.  
**Saída:** `PromptContext` com `_base.md`, cronologia, catálogo de índices e schema de parâmetros.

O contexto é construído uma vez por job e reutilizado nas dez tarefas.

### `ExtractionProvider.extract()` — `backend/services/extraction.py`

**Entrada:** prompt completo e PDFs.  
**Saída:** `ExtractionFragment` validado.

A chamada ao provedor usa Structured Outputs e `store=False`. Os modelos externos de `extraction_wire.py` exigem estrutura explícita, inclusive `natureza` e `efeito` de cada evidência.

### validação/consolidação

`ExtractionService.consolidate()` valida fonte, página, trecho, escopo, campo e tipo. Depois chama:

```text
ChronologyReducer.reduce(campos)
```

**Saída:** `parametros_consolidados`, `decisoes_cronologicas` e alertas não resolvidos.

`OperationalPolicy.apply()` completa campos autorizados quando não existe valor documental efetivo. Cada complemento entra em `ajustes_operacionais` com motivo.

## 4. Aplicação da extração no Angular

### `WorkspaceStore.loadExtraction()`

Busca o resultado ainda vigente e chama `applyExtraction()`.

### `applyExtraction(draft, result, job)`

Prioridade para parâmetro vazio:

```text
parametros_consolidados
    ↓ se ausente
valor bruto único e válido
    ↓ se ausente
ajuste_operacional
```

Valores já editados pelo humano não são substituídos. Parcelas/eventos previamente digitados também são preservados.

## 5. Edição e auditoria

### `WorkspaceStore.updateParameter(key, value)`

Atualiza o formulário e invalida resultado/revisão anteriores. Em seguida enfileira evento com debounce de 650 ms. Eventos pendentes são enviados imediatamente antes de trocar de processo, confirmar revisão ou calcular. Se a persistência obrigatória falhar, a operação é bloqueada e o evento permanece pendente para nova tentativa.

### `RevisionAuditApiService.record()` → `POST /api/auditoria/parametros`

### `RevisionAuditService.record()`

Enriquece a alteração com a origem automática conhecida pelo servidor. A preferência é:

1. decisão cronológica consolidada;
2. ajuste operacional;
3. evidência bruta única.

`Repository.add_parameter_change()` persiste o evento em SQLite. Registros não são atualizados ou apagados pelo fluxo normal.

## 6. Confirmação humana

### `WorkspaceStore.review(true)`

Se a competência é automática, consulta `/api/calculos/padroes`. O rascunho só é marcado como revisado se não tiver mudado durante a requisição.

Qualquer edição posterior redefine `humanReviewed=false` e remove resultado confirmado.

## 7. Montagem do request

### `toCalculationRequest(draft)`

Valida localmente campos mínimos, parcelas completas e confirmação humana.

**Exemplo sintético de saída manual válida:**

```json
{
  "origem_calculo": "manual",
  "numero_processo": null,
  "parcelas": [
    {
      "data": "2025-01-01",
      "valor_singelo": "1000.00",
      "descricao": "Parcela sintética para teste",
      "verba_tipo": "dano_material",
      "origem": "informada"
    }
  ],
  "parametros": {
    "mes_atualizacao": "março",
    "ano_atualizacao": 2026,
    "indice": "sem_correcao",
    "juros_moratorios_tipo": "sem_juros",
    "juros_compensatorios_tipo": "sem_juros",
    "art_523": "nao_aplicar"
  },
  "eventos_financeiros": [],
  "revisao_humana_confirmada": true,
  "honorarios_sobre_danos_morais": false,
  "competencia_automatica": false
}
```

O modo `processo` usa o mesmo contrato, com `origem_calculo='processo'` e `numero_processo` obrigatório. Nesse modo, os parâmetros podem ter origem documental ou operacional, mas a requisição final contém os valores efetivos já revisados pelo operador.

Valores monetários permanecem texto decimal na fronteira HTTP.

## 8. Validação FastAPI

### `CalculationRequest` — `backend/models.py`

O `model_validator` aplica `apply_missing_defaults()` segundo a origem e valida a relação entre origem/número de processo.

`CalculationParameters.require_active_fields()` valida dependências: juros de capitalização, prescrição, compensação e duplo índice.

### `validate_prepared_request()`

Impede inconsistências de honorários gerados e competência automática vencida.

## 9. Serviço de cálculo

### `CalculationService.execute()` — `backend/services/calculation.py`

Responsabilidades:

- validar estado preparado;
- calcular SHA-256 canônico da entrada aceita (`entrada_sha256`);
- obter o SHA-256 da política central (`politica_sha256`);
- chamar `EngineFacade`;
- medir duração;
- retornar `CalculationResponse` ou PDF;
- anexar hashes técnicos e confirmação humana.

Ele não reimplementa matemática do motor.

### `EngineFacade.calculate()` — `backend/services/engine.py`

Converte contratos Pydantic para estruturas aceitas por `judicial_calc.calcular_debitos()` e mantém a fronteira do motor em um único ponto.

## 10. Motor determinístico

### `CalculoParams.from_raw()` — `services/calculation_parameters.py`

Normaliza:

- competência;
- tipos de juros;
- prescrição;
- compensação;
- duplo índice;
- Art. 523.

Combinações inválidas lançam `CalculationValidationError` com código e campos relacionados.

### `calcular_debitos()` — `services/calculation_service.py`

O orquestrador delega regras coesas para `calculation_prescription.py`, `calculation_penalties.py`, `calculation_adjustments.py` e `calculation_summary.py`. A ordem principal é:

1. verifica/atualiza planilhas de índices conforme configuração;
2. valida colunas mínimas das parcelas;
3. normaliza datas e parâmetros;
4. aplica corte de prescrição;
5. pré-carrega tabelas necessárias;
6. calcula correção e juros por parcela;
7. calcula multa comum e honorários informados;
8. aplica Art. 523 e rateios monetários;
9. monta resumo bruto;
10. aplica compensação;
11. processa eventos financeiros;
12. monta `ResultadoCalculo` com memória, resumo e parâmetros efetivos.

As estratégias de índice e juros ficam em módulos próprios e são escolhidas por configuração; não há fórmula jurídica no Angular.

## 11. Resposta e rastreabilidade

`CalculationResponse` devolve:

- origem e processo quando aplicável;
- tabela de memória;
- resumo;
- parâmetros efetivos;
- `entrada_sha256`;
- `politica_sha256`;
- `motor_sha256`;
- `indices_sha256`;
- duração medida;
- confirmação humana.

O frontend exibe esses valores sem recalculá-los.

## 12. Falha do motor

`CalculationValidationError` informa `code` e `fields`. `engine_error_guidance()` converte as chaves em rótulos do catálogo central e devolve orientação como “ajuste X e Y”. O texto original e valores recebidos não são analisados por regex nem ecoados.
