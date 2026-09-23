# Extraindo parcelas e valores de condenação

## Objetivo
Identifique valores monetários que possam compor a memória de cálculo como `dano_material`, `dano_moral`, `honorarios` ou `custas`, preservando a decomposição original sempre que ela estiver disponível.

## Onde procurar dano material
Não limite a busca ao dispositivo. Datas e valores podem estar na petição inicial, extratos, comprovantes, tabelas, quadros e anexos, enquanto a sentença/acórdão apenas define quais prejuízos devem ser ressarcidos.

Exemplos sintéticos que devem ser reconhecidos:
- narrativa: `em 10/02/2025 ocorreram duas transferências, de R$ 1.250,00 e R$ 2.875,45` → duas parcelas, com a mesma data, se estiverem dentro do prejuízo reconhecido;
- narrativa agregada: `um boleto de R$ 850,00 e dois PIX de R$ 1.100,00 cada` → três parcelas se cada lançamento estiver comprovado e a multiplicidade for inequívoca;
- tabela `Data | Histórico | Valor` ou `Vencimento | Parcela | Valor` → uma parcela por linha válida;
- tabela com total no rodapé → extraia as linhas individualizadas e não crie parcela adicional para o total;
- valor global `dano material de R$ 7.500,00` → uma parcela somente se existir data de origem verificável. Sem data segura, gere alerta e não invente.

## Pedido, prova e condenação
- Um valor na petição inicial pode fornecer a composição factual das perdas, mas use `natureza=pedido` quando for mera pretensão e `natureza=fato` quando for transação/comprovante objetivo.
- Quando decisão posterior acolhe genericamente as transações descritas na inicial, as linhas da inicial/anexos podem fornecer as parcelas e o comando posterior define o escopo jurídico.
- Se comando decisório posterior fixa, reduz, majora, substitui ou afasta valor, classifique a evidência como `comando_decisorio` e marque o `efeito` correspondente.
- Não mantenha simultaneamente quantia antiga e quantia decisória mais recente quando esta substitui expressamente aquela.
- `valor da causa` não é parcela, salvo comando inequívoco que o adote como quantia devida.

## Dano moral
Diferencie valor pedido de valor efetivamente arbitrado. Prefira o comando decisório vigente para o montante. Se houver valor individual por beneficiário, crie parcelas distintas apenas quando a individualização estiver clara.

## Não transformar em parcela
Não inclua saldo de conta, limite, valor total de contrato, taxa percentual, depósito judicial, pagamento parcial, levantamento, estorno ou compensação como parcelas calculáveis, salvo quando o próprio título condenatório os definir como valor principal a restituir.

## Contrato de saída
Para cada item de `parcelas`:
- `data`: `AAAA-MM-DD`;
- `valor_singelo`: decimal textual sem símbolo monetário;
- `descricao`: curta e sem dados pessoais desnecessários;
- `verba_tipo`: `dano_material`, `dano_moral`, `honorarios` ou `custas`.

Crie evidências para `parcelas.<índice>.data`, `.valor_singelo` e `.verba_tipo`, usando o mesmo índice da lista.

## Limites
Não faça rateio, dobra, soma inferida ou percentual que não esteja materializado quando isso alterar a quantia da parcela. Se o documento trouxer regra não representável pelo contrato, extraia o fato verificável e gere alerta para revisão humana.

## Cobertura adicional
Procure também por expressões como prejuízo, débito, restituição, ressarcimento, condenação, indenização, dano emergente, cobrança indevida, lançamento, transferência, saque, PIX, TED, DOC, boleto, tarifa, compra, parcela, mensalidade e total parcial. Quando houver tabela, extraia cada linha economicamente autônoma com sua própria data e valor; totais, subtotais e saldos não viram nova parcela se apenas agregarem linhas já extraídas. Valores por extenso e valores numéricos conflitantes devem gerar alerta.
