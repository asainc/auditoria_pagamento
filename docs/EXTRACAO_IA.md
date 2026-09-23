# Extração documental com serviços corporativos

## Objetivo

Converter PDFs judiciais heterogêneos em sugestões estruturadas de parâmetros sem misturar a camada probabilística com o motor de cálculo.

## Fluxo

1. O usuário envia os PDFs ao FastAPI.
2. `DocumentService` valida tipo, tamanho, nome, quantidade de páginas e criptografia.
3. `BradescoBridgeClient` carrega o arquivo temporariamente no File Manager corporativo.
4. O adaptador prioriza `ocr_hibrido`; também aceita `ocr`, `ocr_generator` e `get_text_ocr`, conforme a versão corporativa disponível.
5. `configure_iagen`, listagem, exclusão e espera de workflow são recursos opcionais: são usados quando existem, mas não bloqueiam versões legadas do módulo.
6. O backend normaliza texto e número de página.
7. Cada prompt especializado recebe o subcontrato de campos e o conteúdo OCR.
8. Qualquer prompt é executado exclusivamente por `text_generator`.
9. O texto retornado precisa ser JSON válido e satisfazer `WireExtractionFragment`.
10. O backend revalida tipos, evidências, cronologia e regras operacionais.
11. Quando o upload contém um único processo, o frontend seleciona esse processo, acompanha a extração e aplica automaticamente os parâmetros consolidados; revisão humana continua obrigatória antes do cálculo.

## OCR híbrido

A configuração padrão segue o contrato informado para o ambiente corporativo:

```json
{
  "detailed_output": "true",
  "async_mode": "true",
  "workflow_configuration_code": "CD_WRFL_OCR_HYBRID_ASYNC",
  "figure_settings": {
    "vision_model": "gpt-4o",
    "max_image_size": 0,
    "image_format": "PNG"
  },
  "table_settings": {
    "table_format": "MARKDOWN",
    "language_model": "gpt-4o"
  },
  "document_settings": {"locale": "pt-BR"},
  "warning_settings": {"enabled": "true"}
}
```

Modelos e workflow são parametrizados no backend e precisam corresponder aos deployments realmente habilitados.

## Geração de texto

O backend usa `gpt_bradesco.text_generator(payload, parameters)` com chamada síncrona, sem streaming e saída `json_object`. Os parâmetros de modelo, esforço, verbosidade, temperatura e limite de saída são centralizados em `Settings`.

Nenhum outro componente da aplicação executa prompts diretamente.

## Divisão de payload

O texto OCR não é truncado silenciosamente. Quando o volume ultrapassa `BRADESCO_PROMPT_MAX_CHARS`, o backend agrupa páginas em partes menores. Uma página excepcionalmente grande é dividida por parágrafos, mantendo o cabeçalho de documento e página.

Ao combinar respostas de partes diferentes, referências como `parcelas.0.valor_singelo` são reindexadas para não colidir.

## Evidência e validação

Cada sugestão precisa informar:

- campo;
- valor;
- documento;
- página;
- trecho literal;
- escopo;
- natureza;
- efeito cronológico.

O backend normaliza espaços e confere se o trecho existe no texto OCR da página. Se o serviço retornar texto sem separação de páginas, a aplicação gera alerta explícito e exige conferência visual.

## Retenção remota

O identificador remoto é mantido somente durante a execução quando o módulo o disponibiliza. Após o OCR, a aplicação tenta excluí-lo se `file_manager_delete` ou `file_manager_delete_file` estiver disponível. Ausência dessa função não impede a extração; a política de retenção do container deve ser validada com a equipe proprietária do serviço.
