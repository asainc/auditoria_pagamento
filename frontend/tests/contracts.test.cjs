/** Testa formatos e cenários de revisão sem reproduzir matemática jurídica. */
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {blankDraft, toCalculationRequest, applyExtraction, decimalText, draftFromCalculationVersion} = require('../.test-build/core/calculation-mapper.js');
const {recurringDate} = require('../.test-build/calculation/installment-dates.js');
const {PARAM_FIELDS, interestTypeOptions} = require('../.test-build/calculation/parameter-fields.js');

/** Fixture inteiramente sintética é produzida pelo mapper realmente usado no Angular. */
function draft() {
  return {...blankDraft('1001'),humanReviewed:true,parameters:{mes_atualizacao:'março',ano_atualizacao:2026,indice:'sem_correcao',juros_moratorios_tipo:'sem_juros',juros_compensatorios_tipo:'sem_juros'},installments:[{data:'2025-01-01',valor_singelo:'1.234,56',descricao:'Parcela sintética',verba_tipo:'dano_material'}]};
}
test('payload Angular tem snake_case e decimal exato para integração FastAPI', () => {
  const payload = toCalculationRequest(draft());
  assert.equal(payload.parcelas[0].valor_singelo,'1234.56');
  assert.equal(payload.origem_calculo,'processo');
  assert.equal(payload.numero_processo,'1001');
  assert.equal(payload.revisao_humana_confirmada,true);
  assert.ok(!Object.hasOwn(payload,'numeroProcesso'));
  const fixturePath = path.resolve(__dirname,'../../tests/fixtures/angular_request.json');
  fs.writeFileSync(fixturePath,JSON.stringify(payload,null,2)+'\n');
});
test('não envia parcela parcialmente preenchida', () => {
  const value = draft();value.installments.push({data:'',valor_singelo:'200',descricao:'',verba_tipo:'dano_moral'});
  assert.throws(() => toCalculationRequest(value),/Data e valor/);
});
test('não permite calcular sem revisão humana', () => {assert.throws(() => toCalculationRequest({...draft(),humanReviewed:false}),/Confirme/);});
test('dinheiro não passa por float nem aceita NaN, Infinity e texto livre', () => {
  assert.equal(decimalText('9999999999999999,99'),'9999999999999999.99');
  for (const value of ['NaN','Infinity','-10','10 reais','']) assert.throws(() => decimalText(value));
});
test('recorrência mensal não desloca o dia após fevereiro', () => {
  assert.equal(recurringDate('2024-01-31',1,'mensal'),'2024-02-29');
  assert.equal(recurringDate('2024-01-31',2,'mensal'),'2024-03-31');
  assert.equal(recurringDate('2024-02-29',1,'anual'),'2025-02-28');
  assert.equal(recurringDate('2025-12-29',1,'semanal'),'2026-01-05');
});
test('sugestões não sobrescrevem edição humana nem escolhem entre critérios conflitantes', () => {
  const value = draft();
  const source = {documento:'1001_1.pdf',pagina:1,trecho:'Sintético',escopo:'caso_concreto'};
  const result = {numero_processo:'1001',campos:[{...source,campo:'parametros.indice',valor:'ipca_ibge'},{...source,campo:'parametros.multa_valor',valor:'2'},{...source,campo:'parametros.multa_valor',valor:'3'}],parcelas:[],alertas:[],versao_prompts:'teste'};
  const applied = applyExtraction(value,result,'job');
  assert.equal(applied.parameters.indice,'sem_correcao');
  assert.equal(applied.parameters.multa_valor,undefined);
  assert.equal(applied.humanReviewed,false);
  assert.deepEqual(applied.installments,value.installments);
});

test('cálculo manual exige identificador antes de calcular', () => {
  const base = blankDraft('', 'manual');
  const manual = {
    ...base,
    humanReviewed:true,
    parameters:{...base.parameters,mes_atualizacao:'março',ano_atualizacao:2026,indice:'sem_correcao'},
    installments:[{data:'2026-01-02',valor_singelo:'1000',descricao:'Entrada manual de teste',verba_tipo:'dano_material'}],
  };
  assert.throws(() => toCalculationRequest(manual),/Identificador do cálculo manual/);
});

test('cálculo manual aceita rascunho independente sem processo documental', () => {
  const base = blankDraft('', 'manual');
  const manual = {
    ...base,
    identificadorCalculo:'MANUAL-UI-001',
    humanReviewed:true,
    parameters:{...base.parameters,mes_atualizacao:'março',ano_atualizacao:2026,indice:'sem_correcao'},
    installments:[{data:'2026-01-02',valor_singelo:'1000',descricao:'Entrada manual de teste',verba_tipo:'dano_material'}],
  };
  const payload = toCalculationRequest(manual);
  assert.equal(payload.origem_calculo,'manual');
  assert.equal(payload.numero_processo,null);
  assert.equal(payload.identificador_calculo,'MANUAL-UI-001');
  assert.equal(payload.parametros.juros_moratorios_tipo,'sem_juros');
  assert.equal(payload.parametros.juros_compensatorios_tipo,'sem_juros');
  assert.equal(payload.parametros.art_523,'nao_aplicar');
  assert.equal(payload.parcelas[0].descricao,'Entrada manual de teste');
});

test('rascunho manual mostra os padrões de juros e art. 523 antes da edição', () => {
  const manual = blankDraft('', 'manual');
  assert.equal(manual.parameters.juros_moratorios_tipo,'sem_juros');
  assert.equal(manual.parameters.juros_compensatorios_tipo,'sem_juros');
  assert.equal(manual.parameters.art_523,'nao_aplicar');

  const real = blankDraft('1001');
  assert.equal(real.parameters.juros_moratorios_tipo,undefined);
  assert.equal(real.parameters.juros_compensatorios_tipo,undefined);
  assert.equal(real.parameters.art_523,undefined);
});

test('processo real mostra padrões operacionais apenas quando o documento não informou o critério', () => {
  const source = {documento:'1001_2.pdf',pagina:3,trecho:'Juros moratórios expressamente definidos',escopo:'caso_concreto'};
  const result = {
    numero_processo:'1001',
    campos:[{...source,campo:'parametros.juros_moratorios_tipo',valor:'capitalizacao_simples'}],
    parcelas:[],
    
    alertas:[],
    versao_prompts:'teste',
    ajustes_operacionais:[
      {campo:'parametros.juros_moratorios_tipo',valor:'taxa_legal_12_aa_6_aa',motivo:'Padrão'},
      {campo:'parametros.juros_compensatorios_tipo',valor:'taxa_legal_12_aa_6_aa',motivo:'Padrão'},
      {campo:'parametros.art_523',valor:'nao_aplicar',motivo:'Padrão'},
    ],
  };
  const applied = applyExtraction(blankDraft('1001'),result,'job');
  assert.equal(applied.parameters.juros_moratorios_tipo,'capitalizacao_simples');
  assert.equal(applied.parameters.juros_compensatorios_tipo,'taxa_legal_12_aa_6_aa');
  assert.equal(applied.parameters.art_523,'nao_aplicar');
});

test('todos os parâmetros Pydantic possuem campo visual sem chave duplicada', () => {
  const contract = JSON.parse(fs.readFileSync(path.resolve(__dirname,'../../docs/openapi.json')));
  const schema = contract.components.schemas['CalculationParameters-Input'] ?? contract.components.schemas.CalculationParameters_Input ?? contract.components.schemas.CalculationParameters;
  const keys = PARAM_FIELDS.map(field => field.key);
  assert.equal(new Set(keys).size,keys.length);
  assert.deepEqual([...keys].sort(),Object.keys(schema.properties).sort());
});


test('todos os tipos de juros do contrato estão disponíveis para edição manual', () => {
  const contract = JSON.parse(fs.readFileSync(path.resolve(__dirname,'../../docs/openapi.json')));
  const schema = contract.components.schemas['CalculationParameters-Input'] ?? contract.components.schemas.CalculationParameters_Input ?? contract.components.schemas.CalculationParameters;
  const expected = schema.properties.juros_moratorios_tipo.enum.slice().sort();
  const available = interestTypeOptions.map(option => option.value).filter(Boolean).sort();
  assert.deepEqual(available, expected);
});

test('padrões do backend preenchem lacunas e honorários gerados são identificados', () => {
  const empty = blankDraft('1001');
  const result = {numero_processo:'1001',campos:[],parcelas:[{data:'2025-01-01',valor_singelo:'100',verba_tipo:'honorarios',origem:'honorarios_dano_moral'}],alertas:[],versao_prompts:'teste',honorarios_sobre_danos_morais:true,competencia_automatica:true,ajustes_operacionais:[{campo:'parametros.indice',valor:'tjsp_inpc_ipca15_lei_14905',motivo:'Padrão'},{campo:'parametros.art_523',valor:'nao_aplicar',motivo:'Padrão'}]};
  const applied = applyExtraction(empty,result,'job');
  assert.equal(applied.parameters.indice,'tjsp_inpc_ipca15_lei_14905');
  assert.equal(applied.feesOnMoralDamages,true);
  assert.equal(applied.automaticCompetence,true);
  assert.equal(applied.humanReviewed,false);
  const manual = {...empty,parameters:{indice:'sem_correcao',art_523:'aplicar_multa'}};
  const preserved = applyExtraction(manual,result,'job');
  assert.equal(preserved.parameters.indice,'sem_correcao');
  assert.equal(preserved.parameters.art_523,'aplicar_multa');
});

test('decisão cronológica que afasta critério impede reaproveitar valor antigo ou default', () => {
  const source = {documento:'1001_2.pdf',pagina:3,trecho:'Compensação inicialmente fixada',escopo:'caso_concreto',natureza:'comando_decisorio',efeito:'informa'};
  const result = {
    numero_processo:'1001',
    campos:[{...source,campo:'parametros.compensacao_valor',valor:'10'}],
    parcelas:[],alertas:[],versao_prompts:'teste',
    parametros_consolidados:{},
    decisoes_cronologicas:[{
      campo:'parametros.compensacao_valor',valor:null,documento:'1001_7.pdf',pagina:8,sequencia:7,
      natureza:'comando_decisorio',efeito:'afasta',motivo:'Critério afastado.'
    }],
    ajustes_operacionais:[{campo:'parametros.compensacao_valor',valor:'20',motivo:'Não deveria prevalecer'}],
  };
  const applied = applyExtraction(blankDraft('1001'),result,'job');
  assert.equal(applied.parameters.compensacao_valor,undefined);
});


test('versão histórica vira base editável do mesmo cálculo sem reaproveitar confirmação humana', () => {
  const detail = {
    calculo_id:'calc_0123456789abcdef0123456789abcdef',
    origem_calculo:'processo',
    identificador_calculo:'1001',
    numero_processo:'1001',
    versao:2,
    versao_atual:4,
    versao_base:1,
    criado_em:'2026-09-24T12:00:00+00:00',
    criado_por:'local',
    campos_alterados:['parametros.indice'],
    requisicao:{
      origem_calculo:'processo',numero_processo:'1001',identificador_calculo:'1001',revisao_humana_confirmada:true,
      parcelas:[{data:'2025-01-01',valor_singelo:'100.00',descricao:'Sintético',verba_tipo:'dano_material',origem:'informada'}],
      parametros:{mes_atualizacao:'março',ano_atualizacao:2026,indice:'sem_correcao',juros_moratorios_tipo:'sem_juros',juros_compensatorios_tipo:'sem_juros'},
      honorarios_sobre_danos_morais:false,competencia_automatica:false,
    },
    resultado:{
      origem_calculo:'processo',numero_processo:'1001',identificador_calculo:'1001',memoria:{colunas:[],linhas:[]},resumo:[],
      parametros:{mes_atualizacao:'março',ano_atualizacao:2026,indice:'sem_correcao',juros_moratorios_tipo:'sem_juros',juros_compensatorios_tipo:'sem_juros'},
      metadata:{entrada_sha256:'a'.repeat(64),politica_sha256:'b'.repeat(64),motor_sha256:'c'.repeat(64),indices_sha256:'d'.repeat(64),duracao_ms:1,revisao_humana_confirmada:true},
    },
  };
  const draft = draftFromCalculationVersion(detail);
  assert.equal(draft.calculationId,detail.calculo_id);
  assert.equal(draft.calculationVersion,2);
  assert.equal(draft.expectedCurrentVersion,4);
  assert.equal(draft.loadedFromHistory,true);
  assert.equal(draft.humanReviewed,false);
  assert.equal(draft.result.registro.versao,2);
  assert.equal(draft.installments[0].valor_singelo,'100.00');
});
