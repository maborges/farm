# Auditoria Final — Produto Oficial após Rename `insumo_id → produto_id`

**Data:** 2026-04-28  
**Step:** 87  
**Tipo:** Auditoria pós-rename — sem alteração de código.

---

## 1. Resultado Geral

| Critério | Status |
|---|---|
| Zero referências runtime a `insumo_id` | ✅ |
| `InsumoOperacao.produto_id` FK → `cadastros_produtos.id` | ✅ |
| Schemas Pydantic atualizados | ✅ |
| Zod schema atualizado | ✅ |
| Migrations step25/26/27 presentes | ✅ |
| `MovimentacaoEstoque` removida do model e env.py | ✅ |
| `MovimentacaoEstoque` residual em services funcionais | ⚠️ BUG PRÉ-EXISTENTE |

---

## 2. Verificação `insumo_id` — Runtime

```
grep -rn 'insumo_id' services/api/ --include='*.py' | grep -v migrations | grep -v test_
→ 0 resultados
```

Nenhuma referência runtime a `insumo_id` em código ativo. ✅

---

## 3. Model `InsumoOperacao`

**Arquivo:** `agricola/operacoes/models.py`

```python
produto_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("cadastros_produtos.id"), nullable=False, index=True)
lote_estoque_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("estoque_lotes.id", ondelete="SET NULL"), nullable=True, index=True)
unidade_medida_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("unidades_medida.id", ondelete="SET NULL"), nullable=True)
```

FK `produto_id → cadastros_produtos.id` — oficial. ✅  
Campos aditivos `lote_estoque_id` e `unidade_medida_id` presentes. ✅

---

## 4. Schemas Pydantic

**Arquivo:** `agricola/operacoes/schemas.py`

- `InsumoOperacaoCreate`: `produto_id: UUID` (required), `lote_estoque_id: UUID | None`, `unidade_medida_id: UUID | None` ✅  
- `InsumoOperacaoResponse`: idem + campos ORM. ✅

---

## 5. Cobertura por módulo

### 5.1 Operações Agrícolas — `service.py`

| Referência anterior | Referência atual | Status |
|---|---|---|
| `insumo.insumo_id` (×7) | `insumo.produto_id` | ✅ |
| `insumo_id=insumo.insumo_id` no constructor | `produto_id=insumo.produto_id` | ✅ |
| Import `MovimentacaoEstoque` | Removido | ✅ |
| Bloco `MovimentacaoEstoque(...)` | Removido | ✅ |

### 5.2 Rastreabilidade — `router.py` + `service.py`

| Referência anterior | Referência atual | Status |
|---|---|---|
| `i.insumo_id` (router ×2) | `i.produto_id` | ✅ |
| `i.insumo_id` (service ×2) | `i.produto_id` | ✅ |

### 5.3 Relatório de Estoque — `relatorio_service.py`

| Referência | Status |
|---|---|
| `ins.produto_id` (aggregação de insumos) | ✅ corrigido no step 86 |
| `MovimentacaoEstoque.produto_id` (linhas 174-185) | ⚠️ ver seção 7 |

### 5.4 Caderno de Campo — `caderno/service.py`

| Referência anterior | Referência atual | Status |
|---|---|---|
| `ins.get("insumo_id", "N/A")` | `str(ins.produto_id)` | ✅ bug ORM corrigido |
| `ins.get('dose_por_ha', '')` | `ins.dose_por_ha or ''` | ✅ bug ORM corrigido |
| `ins.get('unidade', '')` (×2) | `ins.unidade or ''` | ✅ bug ORM corrigido |

---

## 6. Zod Schema

**Arquivo:** `packages/zod-schemas/src/agricola/operacao.ts`

```typescript
export const InsumoOperacaoCreateSchema = z.object({
  produto_id: z.string().uuid(),  // ✅ renomeado
  ...
});
```

Zero ocorrências de `insumo_id` no schema Zod. ✅

---

## 7. Bug Pré-existente — `MovimentacaoEstoque` em código funcional

**Severidade:** Alta  
**Origem:** Não introduzido pelo Step 86 — remanescente do Step 75 (remoção de fallbacks).

### 7.1 `operacional/services/relatorio_service.py:9`

```python
from operacional.models.estoque import MovimentacaoEstoque, Deposito  # linha 9
```

Import **top-level** de modelo removido. Causará `ImportError` na inicialização do módulo quando carregado pelo FastAPI. Função impactada: `historico_deposito()` (linhas ~170-210) que agrupa movimentações por depósito.

**Substituição necessária:** reescrever query usando `EstoqueMovimento` (ledger oficial), que tem os mesmos campos (`produto_id`, `deposito_id`, `quantidade`, `custo_total`, `tipo_movimento`).

### 7.2 `agricola/safras/service.py:524`

```python
from operacional.models.estoque import MovimentacaoEstoque, LoteEstoque, Deposito  # local import
```

Import **local** dentro de `get_movimentacoes_safra()`. Causará `ImportError` apenas quando o endpoint `GET /safras/{id}/estoque/movimentacoes` for chamado.

**Substituição necessária:** método já foi reescrito para usar `EstoqueMovimento` em outros caminhos — este bloco é um segundo caminho não removido no Step 75.

### 7.3 `agricola/beneficiamento/service.py:379`

```python
# Cria MovimentacaoEstoque
```

Apenas **comentário** de código. Sem impacto runtime. Pode ser removido na próxima limpeza.

---

## 8. Migrations

| Migration | Revisão | Status |
|---|---|---|
| `step25_drop_movimentacoes.py` | `step25_drop_movimentacoes` | ✅ presente |
| `step26_produto_canonico.py` | `step26_produto_canonico` | ✅ presente |
| `step27_rename_insumo_id.py` | `step27_rename_insumo_id` | ✅ presente |

Cadeia de revisões: `step24_legado_estoque → step25 → step26 → step27`

---

## 9. Testes

| Suite | Total | Passando |
|---|---|---|
| `test_insumo_campos_canonicos.py` | 8 | ✅ 8 |
| `test_manejo_produto_canonico.py` | 6 | ✅ 6 |

---

## 10. Pendências — Step 88 (recomendado)

| # | Arquivo | Ação |
|---|---|---|
| P1 | `relatorio_service.py:9,170-210` | Substituir `MovimentacaoEstoque` por `EstoqueMovimento` — import top-level **quebra startup** |
| P2 | `safras/service.py:524-580` | Substituir `MovimentacaoEstoque` por `EstoqueMovimento` — import local quebra endpoint |
| P3 | `beneficiamento/service.py:379` | Remover comentário obsoleto |

---

## Referências

- `docs/PLANO_RENAME_INSUMO_ID_STEP85.md`
- `docs/AUDITORIA_PRODUTO_CANONICO_STEP82.md`
- `docs/ESTOQUE_CANONICO_LEDGER_2026-04-28.md`
