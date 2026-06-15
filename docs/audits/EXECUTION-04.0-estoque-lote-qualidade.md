# EXECUTION-04.0 — Diagnóstico Estoque/Lote Qualidade

## 1. Existe entidade LoteEstoque?

**Sim.** `operacional/models/estoque.py` - `LoteEstoque` (tabela `estoque_lotes`)

- Campos principais:
  - `id`, `produto_id`, `deposito_id`, `numero_lote`
  - `quantidade_inicial`, `quantidade_atual`, `custo_unitario`
  - `data_fabricacao`, `data_validade`
- `status`: ATIVO, VENCIDO, ESGOTADO, BLOQUEADO
   - `lote_beneficiamento_id`: Campo de rastreabilidade (não FK formal) vinculando ao lote de beneficiamento origem

## 2. Existe vínculo entre Romaneio e Lote?

**Indireto.** 
- `RomaneioColheita` → `ProdutoColhido` (tabela `agricola_produtos_colhidos`)
- `LoteBeneficiamento` → `LoteEstoque` via `lote_estoque_id`

Não há FK direta de `RomaneioColheita` para `LoteEstoque`. A conexão é feita via `ProdutoColhido`:
- `ProdutoColhido.romaneio_id` (FK para romaneio)
- `ProdutoColhido` é criado automaticamente no `RomaneioService.criar()`
- `LoteBeneficiamento` usa `RomaneioColheita.peso_liquido_kg/peso_liquido_padrao_kg` como entrada

## 3. Existe vínculo entre Beneficiamento e Lote?

**Sim.** `agricola/beneficiamento/models.py`:

- `LoteBeneficiamento.lote_estoque_id` → `LoteEstoque.id` (FK, nullable)
- `BeneficiamentoService.armazenar_no_estoque()` cria `LoteEstoque` a partir de `LoteBeneficiamento`

## 4. Existe campo de qualidade no lote?

**Não no `LoteEstoque`.** 

Campos de qualidade existentes:
- `LoteBeneficiamento.bebida`, `pontuacao_scaa`, `defeitos_intrinsecos`, `defeitos_extrinsecos`, `peneira_principal`
- `LoteEstoque` NÃO possui campos de qualidade

`ProdutoColhido` tem:
- `umidade_pct`, `impureza_pct`, `avariados_pct`, `ardidos_pct`, `quebrados_pct`

## 5. O estoque controla produto bruto e produto beneficiado separadamente?

**Sim, via commodity.**

- Produto colhido (bruto) → `agricola_produtos_colhidos`
- Produto beneficiado → `cafe_lotes_beneficiamento` → `estoque_lotes`
- Mesmo `commodity_id` pode ter registros em ambas as tabelas
- Controle de saldo: `SaldoEstoque` é atualizado independentemente do tipo

## 6. O peso usado no estoque deve ser físico ou comercial?

**Físico (peso líquido).**

Fluxo atual:
- `Romaneio` → `peso_liquido_padrao_kg` → serve de base
- `Beneficiamento` → `peso_saida_kg` (café beneficiado seco) → vira `LoteEstoque.quantidade_atual` (em sacas)
- `LoteEstoque` armazena quantidade em unidade da commodity (ex: sacas)

## 7. Onde aplicar qualidade sem contaminar ledger?

**Ponto de integração seguro: `ProdutoColhido`**

- `ProdutoColhido` já recebe `peso_liquido_kg` do romaneio
- É criado automaticamente e não dispara ledger no `RomaneioService.criar()`
- Adicionar campo `qualidade_laudo_id` em `ProdutoColhido`
- Adicionar `peso_liquido_comercial_kg` em `ProdutoColhido`
- Ledger só é criado via `BeneficiamentoService.armazenar_no_estoque()` (via `EstoqueService.registrar_movimentacao`)

## 8. Como impedir mistura de lotes incompatíveis futuramente?

**Regras de negócio sugeridas:**

1. **No `armazenar_no_estoque`:** Validar `qualidade_status` do(s) romaneio(s) origem
2. **Bloqueio de lote REPROVADO:** `LoteEstoque.status = "BLOQUEADO"` indica problema
3. **Metadata por lote:** Adicionar `dados_extras` em `LoteEstoque` com:
   - `qualidade_status`: APROVADO/REPROVADO
   - `qualidade_laudo_id`
   - `peso_desconto_qualidade_kg`

## Pontos de Integração Seguros

| Entidade | Campos para adicionar | Motivo |
|----------|---------------------|--------|
| `ProdutoColhido` | `qualidade_laudo_id`, `peso_desconto_qualidade_kg`, `peso_liquido_comercial_kg` | Rastreabilidade antes do beneficiamento |
| `LoteEstoque` | `qualidade_status`, `qualidade_laudo_id` (via `dados_extras`) | Bloqueio de saída/lote ruins |

## Riscos Identificados

1. **Conflito de peso:** `Romaneio.peso_liquido_comercial_kg` já existe mas não está sendo usado no fluxo de estoque
2. **Falta de validação:** `BeneficiamentoService.criar_from_romaneios()` permite blend de romaneios sem checar qualidade
3. **Ledger sem contexto:** `EstoqueMovimento` não registra origem qualidade (deveria ter `observacoes` com dados)
4. **ProdutoColhido sem qualidade:** Atualmente grava `peso_liquido_kg` sem considerar descontos de qualidade

## Recomendações para EXECUTION-04.1

1. **Adicionar campos em `ProdutoColhido`:**
   - `qualidade_laudo_id` (FK opcional)
   - `peso_liquido_comercial_kg` (calculado: `peso_liquido_padrao_kg - desconto_qualidade`)
   - Usar esse valor ao invés do `peso_liquido_padrao_kg` como entrada no beneficiamento

2. **Validar qualidade antes do beneficiamento:**
   - `BeneficiamentoService.criar_from_romaneio()` deve checar `qualidade_status == "APROVADO"` ou `null`
   - Rejeitar blend com romaneios REPROVADOS

3. **Fluxo idempotente:**
   - Em `armazenar_no_estoque()`, usar `peso_liquido_comercial_kg` do `ProdutoColhido`
   - Não duplicar cálculo de desconto no ledger

4. **Status de bloqueio:**
   - Se `qualidade_status == "REPROVADO"`, o lote deve ficar com `status = "BLOQUEADO"` até tratamento