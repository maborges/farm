# Boundary: Mark-to-Market (MtM) e Fórmulas de Hedge

## 1. Definições de Cálculo de Mark-to-Market (MtM)

A fórmula de MtM (Marcação a Mercado) determina o lucro ou prejuízo não realizado (PnL) de uma posição em aberto, baseando-se na diferença entre o preço contratado e o preço de mercado na data de referência.

### 1.1 Fórmulas por Tipo de Posição

- **Contrato de VENDA (Hedge de Produtor / Posição Short):**
  O produtor fixa um preço de venda no futuro. Se o mercado cai, a posição dele ganha valor (ele travou um preço mais alto que o atual praticado).
  `MtM = (preco_contratado - preco_mercado) * quantidade_aberta`

- **Contrato de COMPRA (Hedge de Consumidor / Posição Long):**
  O produtor ou fábrica fixa um preço de compra de insumo no futuro. Se o mercado sobe, a posição ganha valor (ele travou preço baixo).
  `MtM = (preco_mercado - preco_contratado) * quantidade_aberta`

*Essa regra de sinais atende perfeitamente ao MVP.*

## 2. Normalização e Canonicidade (V2.1 - MVP)

### 2.1 Unidade Oficial
A unidade deve ser estritamente a `unidade_padrao` cadastrada na respectiva `Commodity`.
- **MVP (V2.1):** Nenhuma conversão complexa de unidade on-the-fly. Preço contratado, volume e cotação de mercado devem concordar na mesma unidade oficial. Fatores de conversão (saca para tonelada, etc) existem em `ConversaoUnidade` mas atuarão apenas como utilitário manual nesta etapa.

### 2.2 Moeda
- **MVP (V2.1):** Operações single-currency. Se o contrato de derivativo/termo foi estabelecido em BRL, a cotação de fechamento respectiva a ser lançada DEVE estar em BRL. A conversão de exposição cambial (PTAX) e fluxos multi-moeda entrarão em v2.2.

## 3. Modelo de Snapshot: `HedgePositionSnapshot`

O Snapshot guarda a foto diária do PnL para popular dashboards analíticos e de risco, evitando recomputação massiva.

**Definições:**
- O snapshot é gerado **por Contrato de Hedge**. Visões de safra+commodity são agregações dinâmicas sobre estas linhas.
- O snapshot admite reprocessamento retroativo em caso de correção de preço (Upsert).

**Campos (Proposta MVP):**
- `tenant_id`
- `safra_id`
- `commodity_id`
- `contrato_hedge_id` (referência ao contrato NDF/Termo/B3 em si)
- `data_referencia` (data da marcação)
- `quantidade_aberta`
- `preco_contratado`
- `preco_mercado`
- `moeda`
- `unidade`
- `mtm_valor` (cálculo realizado de PnL/resultado financeiro projetado)
- `pnl_nao_realizado` (alias descritivo do MTM no momento)
- `fonte_preco`
- `calculado_em` (timestamp da execução da rotina)

## 4. Alimentação de Preços

Para o MVP V2.1:
1. **Entrada Manual de Fechamento:** Entrada via tela do fechamento ("Settlement") da B3/CBOT ou via `CotacaoCommodity`.
2. O modelo `CotacaoCommodity` atende bem ativos Spot/Físicos. Contratos de Mercado Futuro exigem separação por 'Vencimento' (Ex: CCMU26 - Setembro 26). Para o MVP, se usarmos o modelo existente como proxy, assumiremos uma associação direta via entrada manual do gestor para simplificar. 
3. Feed live via corretora: Fora do escopo.
