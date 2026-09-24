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

Valores já editados pelo humano não são substituídos. Parcelas previamente digitadas também são preservadas.

## 5. Edição e auditoria

### `WorkspaceStore.updateParameter(key, value)`

Atualiza o formulário e invalida resultado/revisão anteriores. Em seguida enfileira evento com debounce de 650 ms. Eventos pendentes são enviados imediatamente antes de trocar de processo, confirmar revisão ou calcular. Se a persistência obrigatória falhar, a operação é bloqueada e o evento permanece pendente para nova tentativa.

### `RevisionAuditApiService.record()` → `POST /api/v2/auditoria/parametros`

### `RevisionAuditService.record()`

Enriquece a alteração com a origem automática conhecida pelo servidor. A preferência é:

1. decisão cronológica consolidada;
2. ajuste operacional;
3. evidência bruta única.

`Repository.add_parameter_change()` persiste o evento em SQLite. Registros não são atualizados ou apagados pelo fluxo normal.

## 6. Confirmação humana

### `WorkspaceStore.review(true)`

Se a competência é automática, consulta `/api/v2/calculos/padroes`. O rascunho só é marcado como revisado se não tiver mudado durante a requisição.

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
- valor em dobro para restituição material, quando expressamente determinado;
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
11. mantém rastreabilidade da aplicação de valor em dobro nas parcelas materiais quando a flag estiver ativa;
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

## 13. Cadastro, versionamento e execução técnica

Após um cálculo concluído, `CalculationService.execute()` produz uma única memória de cálculo PDF a partir do resultado e chama `CalculationRepository.append_version()`. A persistência separa o estado funcional escolhido pelo usuário da execução técnica que produziu um resultado.

```text
processo/identificador normalizado
    ↓
calculation_records
    ↓
calculation_versions                  calculation_executions
    ├── V1  ←──────────────────────── Execução A
    │    └─────────────────────────── Execução B (mesmo estado funcional)
    ├── V2  ←──────────────────────── Execução C
    └── VN
```

O `business_hash` é calculado de forma canônica somente sobre:

- parâmetros de cálculo;
- parcelas;
- `honorarios_sobre_danos_morais`.

Se o hash já existir naquele cálculo, nenhuma nova versão é criada; é registrada apenas uma nova execução técnica ligada à versão correspondente. Mudanças de motor, política ou índices ficam, portanto, auditáveis na execução sem gerar uma versão de negócio artificial.

Quando um novo estado funcional precisa ser persistido, `versao_base` funciona como trava otimista. O SQLite inicia `BEGIN IMMEDIATE` antes de decidir o número da versão. Se a versão atual já tiver avançado em relação à base editada pelo usuário, o backend retorna conflito e nenhuma versão parcial é criada.

Cada versão guarda request/result da criação, PDFs históricos, hashes, `business_hash`, versão base e diff estruturado. Cada execução guarda request/result efetivamente executados, PDFs da execução, hashes técnicos, duração, ator e instante UTC.

## 14. Normalização da identidade do processo

`backend/calculation_identity.py` remove pontuação do número do processo para formar a chave de identidade. Quando há exatamente 20 dígitos, a máscara CNJ é reaplicada somente para exibição. Essa transformação evita cadastros duplicados por formatação e não deve ser interpretada como validação jurídica do número ou do dígito verificador.

Documentos recém-enviados também usam a apresentação canônica. Consultas de documentos toleram a máscara histórica já persistida.

## 15. Histórico paginado e lazy loading

`GET /api/v2/calculos/historico` devolve apenas resumos dos cálculos, com paginação e filtros. As versões não fazem parte dessa resposta. Os principais filtros são busca, origem, estado, índice atual, criador, período de atualização e ordenação.

Ao expandir um cálculo, o Angular chama `GET /api/v2/calculos/{calculo_id}/versoes`. A paginação das versões é independente. Ao solicitar detalhes técnicos de uma versão, `GET /api/v2/calculos/{calculo_id}/versoes/{versao}/execucoes` carrega as execuções sob demanda.

Esse desenho mantém a resposta principal pequena mesmo com grande quantidade de versões e reexecuções.

## 16. Comparador e diff completo

`GET /api/v2/calculos/{calculo_id}/comparar` compara diretamente duas versões escolhidas. A resposta contém:

- total da versão de origem;
- total da versão de destino;
- diferença aritmética dos totais já produzidos pelo motor;
- valores anterior/novo dos parâmetros alterados;
- parcelas adicionadas/removidas/alteradas;
- snapshots anterior/novo e campos modificados de cada parcela.

O comparador é somente leitura e não recalcula o motor.

## 17. Estado do cálculo

O cadastro pode estar `ativo`, `arquivado` ou `cancelado`. A alteração de estado é auditada e não remove dados. Cálculos arquivados/cancelados continuam consultáveis e seus PDFs permanecem disponíveis, mas novas execuções são recusadas até reativação.

## 18. Reabertura segura

A interface permite editar a versão atual de um cálculo ativo. Ao abrir:

1. o Angular consulta o snapshot imutável da versão;
2. materializa o request como rascunho editável;
3. invalida a confirmação humana anterior;
4. preserva `calculo_id` e `versao_base`;
5. qualquer nova execução exige nova confirmação humana;
6. se outro usuário criar uma versão antes da gravação, o backend retorna conflito;
7. se os parâmetros/parcelas forem idênticos a um estado já registrado, a versão é reutilizada e apenas uma nova execução é criada.

Os PDFs da versão e da execução são lidos do armazenamento persistido. Nenhum endpoint histórico chama `judicial_calc` para reconstruir o passado.
