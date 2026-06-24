# EXECUTION-PECUARIA-01 — Fundação do Domínio Pecuária
## Planejamento Técnico Detalhado — Fase 1

**Data:** 23/06/2026  
**Status:** PLANEJAMENTO — READ-ONLY  
**Versão:** 1.0  
**Baseado em:** Auditoria arquitetural e estratégica de 23/06/2026

---

## 1. Estado Atual

| Item | Existe | Parcial | Ausente |
|------|--------|---------|---------|
| Model `Animal` (pec_animais) | ✅ | | |
| Model `LoteAnimal` (pec_lotes) | ✅ | | |
| Model `EventoAnimal` (pec_eventos_animal) | ✅ | | |
| Model `ManejoLote` (pec_manejos_lote) | ✅ | | |
| Model `Piquete` (pec_piquetes) | ✅ | | |
| Model `ProducaoLeite` (pec_producao_leite) | ✅ | | |
| Enum `TipoEvento` (22 tipos cobrindo toda a vida do animal) | ✅ | | |
| Enum `CategoriaAnimal` (corte + leite) | ✅ | | |
| Enum `StatusAnimal` (ATIVO, VENDIDO, ABATIDO, MORTO, TRANSFERIDO) | ✅ | | |
| Router `GET/POST /pecuaria/lotes` | ✅ | | |
| Router `GET/POST /pecuaria/manejos` | ✅ | | |
| Router `GET/POST /pecuaria/piquetes` | ✅ | | |
| Integração financeira em `ManejoLoteService` (vacinação→Despesa, venda→Receita) | | ✅ | |
| Campo `produto_id` em eventos (pré-condição de integração estoque) | ✅ | | |
| Campo `responsavel_id` em `EventoAnimal` | ✅ | | |
| Campo `responsavel_id` em `ManejoLote` | | | ✅ |
| `BaseService` com audit, tenant isolation, hard_delete | ✅ | | |
| `registrar_ledger_estoque()` em `operacional/services/estoque_ledger.py` | ✅ | | |
| Campo `lote_pecuario_id` em `fin_despesas` | | | ✅ |
| Campo `lote_pecuario_id` em `fin_receitas` | | | ✅ |
| Router `GET/POST /pecuaria/animais` (CRUD individual) | | | ✅ |
| Service `AnimalService` | | | ✅ |
| Schema `AnimalCreate` / `AnimalResponse` / `AnimalUpdate` | | | ✅ |
| Endpoint `GET /pecuaria/animais/{id}/timeline` | | | ✅ |
| Cálculo automático de GMD ao registrar pesagem | | | ✅ |
| Atualização de `Animal.peso_atual_kg` por evento de pesagem | | | ✅ |
| Atualização de `LoteAnimal.quantidade_cabecas` por eventos | | | ✅ |
| Soft-delete (`deleted_at`) em models pecuários | | | ✅ |
| Endpoint `GET /reports/pecuaria/summary` | | | ✅ |
| Paginação nos endpoints de listagem | | ✅ | |

---

## 2. Dependências

| Item | Depende de | Risco |
|------|-----------|-------|
| `AnimalService` | `BaseService` (core) — já existe | 🟢 Baixo |
| `AnimalService.registrar_pesagem()` | `EventoAnimal` model — já existe | 🟢 Baixo |
| Cálculo de GMD | `EventoAnimal` tipo `PESAGEM` — dados existem no banco | 🟢 Baixo |
| Atualização de `peso_atual_kg` no Animal | campos `peso_atual_kg` e `data_ultima_pesagem` — existem | 🟢 Baixo |
| Timeline do Animal | `EventoAnimal` + `ManejoLote` — ambos existem | 🟢 Baixo |
| Integração Estoque (baixa automática) | `registrar_ledger_estoque()` — função já existe em `estoque_ledger.py` | 🟢 Baixo |
| Integração Estoque com produto | `produto_id` em `EventoAnimal` e `ManejoLote` — campos existem | 🟢 Baixo |
| `lote_pecuario_id` em `fin_despesas` | Migration `ALTER TABLE` nullable — sem quebra | 🟢 Baixo |
| `lote_pecuario_id` em `fin_receitas` | Migration `ALTER TABLE` nullable — sem quebra | 🟢 Baixo |
| Soft-delete nos models pecuários | Migration `ADD COLUMN deleted_at` nullable — sem quebra | 🟢 Baixo |
| Paginação nos endpoints | `BaseService.list_all()` aceita `skip/limit` — já implementado | 🟢 Baixo |
| Router `animais` registrado em `main.py` | `app.include_router(animais.router, ...)` — padrão já existente | �� Baixo |
| Soft-delete requer filtro em `list_all()` | `BaseService` não filtra `deleted_at` por padrão — requer override | 🟡 Médio |
| Sincronização de `quantidade_cabecas` | Requer transação atômica no handler de evento | 🟡 Médio |
| Timeline unificada (EventoAnimal + ManejoLote) | JOIN entre duas tabelas em escalas altas | 🟡 Médio |

---

## 3. Estratégia de Implementação

### Bloco A — Animal (CRUD completo)

| Ordem | Item | Complexidade | Risco |
|-------|------|-------------|-------|
| A.1 | `AnimalCreate` schema | Baixa | 🟢 |
| A.2 | `AnimalUpdate` schema (partial update via `exclude_unset=True`) | Baixa | 🟢 |
| A.3 | `AnimalResponse` schema (com `ConfigDict(from_attributes=True)`) | Baixa | 🟢 |
| A.4 | `AnimalFilter` schema (especie, categoria, raca, sexo, status, lote_id, q) | Baixa | 🟢 |
| A.5 | `AnimalService(BaseService[Animal])` com list_all + filtros + paginação | Baixa | 🟢 |
| A.6 | `AnimalService.create_animal()` com validação de unicidade de brinco | Média | 🟡 |
| A.7 | `AnimalService.update_animal()` delegando para `BaseService.update()` | Baixa | 🟢 |
| A.8 | `AnimalService.soft_delete_animal()` setando `deleted_at = now()` | Baixa | 🟢 |
| A.9 | `animal_router.py` (GET/POST/GET{id}/PATCH{id}/DELETE{id}) | Baixa | 🟢 |
| A.10 | Registro do router em `main.py` | Mínima | 🟢 |

**Padrão de paginação adotado:**
```
GET /pecuaria/animais?page=1&page_size=50&categoria=BEZERRO&status=ATIVO
Response: { "items": [...], "total": 1240, "page": 1, "page_size": 50, "pages": 25 }
```

**Estratégia de pesquisa full-text:**
```
GET /pecuaria/animais?q=texto → OR(brinco.ilike, nome.ilike, sisbov.ilike)
```

**Auditoria:** Herdada automaticamente do `BaseService` — sem implementação adicional.

**Permissões:** `dependencies=[Depends(require_module("P1_REBANHO"))]` — mesmo módulo dos lotes.

---

### Bloco B — Timeline do Animal

| Ordem | Item | Complexidade | Risco |
|-------|------|-------------|-------|
| B.1 | Schema `TimelineEventoResponse` (tipo_origem: "ANIMAL" ou "LOTE") | Baixa | 🟢 |
| B.2 | `AnimalService.get_timeline()` — duas queries + merge em Python | Média | 🟡 |
| B.3 | Endpoint `GET /pecuaria/animais/{id}/timeline` com cursor pagination | Baixa | 🟢 |

**Estratégia para evitar N+1 — Duas queries separadas (não JOIN):**
```python
# Query 1: eventos individuais
eventos_animal = SELECT * FROM pec_eventos_animal
                 WHERE animal_id = :id ORDER BY data_evento DESC LIMIT 200

# Query 2: eventos do lote (contexto do animal)
eventos_lote = SELECT * FROM pec_manejos_lote
               WHERE lote_id = :lote_id ORDER BY data_evento DESC LIMIT 200

# Merge ordenado em Python
timeline = sorted(eventos_animal + eventos_lote, key=lambda e: e.data_evento, reverse=True)
```

**Schema `TimelineEventoResponse`:**
```
id, tipo_origem (ANIMAL|LOTE), tipo, data_evento, descricao,
peso_kg, quantidade_cabecas, valor, produto_nome, responsavel_nome, dados_extras
```

**Lookup de nomes para evitar N+1:**
```python
produto_ids = {e.produto_id for e in eventos if e.produto_id}
produtos = {p.id: p.nome for p in (SELECT FROM cadastros_produtos WHERE id IN produto_ids)}
```

---

### Bloco C — Pesagens

| Ordem | Item | Complexidade | Risco |
|-------|------|-------------|-------|
| C.1 | `PesagemCreate` schema | Baixa | 🟢 |
| C.2 | `PesagemResponse` schema com `gmd_calculado` | Baixa | 🟢 |
| C.3 | `AnimalService.registrar_pesagem()` com GMD + atualização do Animal | Média | 🟡 |
| C.4 | Endpoint `POST /pecuaria/animais/{id}/pesagens` | Baixa | 🟢 |
| C.5 | Endpoint `GET /pecuaria/animais/{id}/pesagens` (histórico paginado) | Baixa | 🟢 |
| C.6 | Handler de sincronização de `quantidade_cabecas` no `ManejoLoteService` | Média | 🟡 |

**Cálculo de GMD:**
```python
pesagem_anterior = SELECT peso_kg, data_evento FROM pec_eventos_animal
                   WHERE animal_id = :id AND tipo = 'PESAGEM'
                   ORDER BY data_evento DESC LIMIT 1

if pesagem_anterior and dias > 0:
    gmd = (novo_peso - pesagem_anterior.peso_kg) / dias
else:
    gmd = None  # primeira pesagem
```

**Sincronização de quantidade_cabecas (estratégia por recálculo):**
```python
# Após evento de NASCIMENTO, MORTE, VENDA, ABATE, TRANSFERENCIA:
contagem = SELECT COUNT(*) FROM pec_animais
           WHERE lote_id = :lote_id AND deleted_at IS NULL AND status = 'ATIVO'
lote.quantidade_cabecas = contagem
```
Recálculo via COUNT é idempotente e seguro. Otimizar para trigger DB na Fase 3.

---

### Bloco D — Integração Estoque

| Ordem | Item | Complexidade | Risco |
|-------|------|-------------|-------|
| D.1 | Adicionar `quantidade_produto: float | None` e `deposito_id: UUID | None` ao `ManejoLoteCreate` | Baixa | 🟢 |
| D.2 | Handler `_registrar_saida_estoque_pecuaria()` no `ManejoLoteService` | Baixa | 🟢 |
| D.3 | Chamada ao handler após `db.flush()` do evento | Baixa | 🟢 |
| D.4 | Handler tolerante a falhas (log warning, não raise) | Baixa | 🟢 |

**Uso de `registrar_ledger_estoque()` já existente:**
```python
from operacional.services.estoque_ledger import registrar_ledger_estoque

# Dentro de ManejoLoteService._registrar_saida_estoque_pecuaria():
await registrar_ledger_estoque(
    session=db,
    tenant_id=self.tenant_id,
    produto_id=produto_id,
    tipo_movimento="SAIDA",
    quantidade=quantidade,
    origem="MANUAL",
    origem_id=manejo_id,
    deposito_id=deposito_id,
    observacoes=f"Pecuária — {tipo_evento} Lote {lote_identificacao}",
)
```

**Tipos de evento que disparam baixa:**
VACINACAO, MEDICACAO, VERMIFUGACAO, BANHO_CARRAPATICIDA + qualquer evento com produto_id preenchido.

**Tipos que NÃO disparam:** NASCIMENTO, MORTE, PESAGEM, PARTO, TRANSFERENCIA, VENDA, ABATE, COMPRA.

---

### Bloco E — Integração Financeira

| Ordem | Item | Complexidade | Risco |
|-------|------|-------------|-------|
| E.1 | Migration: `lote_pecuario_id UUID NULL FK pec_lotes` em `fin_despesas` | Baixa | 🟢 |
| E.2 | Migration: `lote_pecuario_id UUID NULL FK pec_lotes` em `fin_receitas` | Baixa | 🟢 |
| E.3 | Atualizar `ManejoLoteService` para preencher `lote_pecuario_id` nas despesas/receitas criadas | Baixa | 🟢 |
| E.4 | Atualizar `DespesaResponse` e `ReceitaResponse` com `lote_pecuario_id: UUID | None = None` | Baixa | 🟢 |
| E.5 | Endpoint `GET /pecuaria/lotes/{id}/resultado` (P&L do lote) | Média | 🟡 |

**Schema ResultadoLoteResponse:**
```
lote_id, identificacao, periodo_inicio, periodo_fim,
total_receitas, total_despesas, resultado_bruto,
quantidade_cabecas, peso_medio_entrada_kg, peso_medio_saida_kg,
arrobas_produzidas, custo_por_arroba
```

---

## 4. Contratos Afetados

### APIs Novas (sem impacto em existentes)
- `GET /api/v1/pecuaria/animais`
- `POST /api/v1/pecuaria/animais`
- `GET /api/v1/pecuaria/animais/{id}`
- `PATCH /api/v1/pecuaria/animais/{id}`
- `DELETE /api/v1/pecuaria/animais/{id}`
- `GET /api/v1/pecuaria/animais/{id}/timeline`
- `POST /api/v1/pecuaria/animais/{id}/pesagens`
- `GET /api/v1/pecuaria/animais/{id}/pesagens`
- `GET /api/v1/pecuaria/lotes/{id}/resultado`
- `GET /api/v1/reports/pecuaria/summary`

### APIs Modificadas (campos opcionais — sem quebra de contrato)
- `POST /api/v1/pecuaria/manejos` — +2 campos opcionais (`quantidade_produto`, `deposito_id`)
- `GET /api/v1/financeiro/despesas` — response +1 campo opcional (`lote_pecuario_id: null`)
- `GET /api/v1/financeiro/receitas` — response +1 campo opcional (`lote_pecuario_id: null`)

### Banco de Dados

| Tabela | Alteração | Tipo | Risco |
|--------|----------|------|-------|
| `fin_despesas` | `+ lote_pecuario_id UUID NULL FK pec_lotes ON DELETE SET NULL` | Additive | 🟢 |
| `fin_receitas` | `+ lote_pecuario_id UUID NULL FK pec_lotes ON DELETE SET NULL` | Additive | 🟢 |
| `pec_lotes` | `+ deleted_at TIMESTAMP WITH TIME ZONE NULL` | Additive | 🟢 |
| `pec_animais` | `+ deleted_at TIMESTAMP WITH TIME ZONE NULL` | Additive | 🟢 |
| `pec_manejos_lote` | `+ deleted_at TIMESTAMP WITH TIME ZONE NULL` | Additive | 🟢 |
| `pec_manejos_lote` | `+ quantidade_produto FLOAT NULL` | Additive | 🟢 |
| `pec_manejos_lote` | `+ deposito_id UUID NULL FK estoque_depositos` | Additive | 🟢 |
| `pec_manejos_lote` | `+ responsavel_id UUID NULL FK cadastros_pessoas` | Additive | 🟢 |
| `pec_eventos_animal` | Nenhuma alteração (append-only por design) | — | 🟢 |

### Frontend
- Nenhuma tela quebra — todas as mudanças são additive
- `relatorios/page.tsx` — beneficiada: `/reports/pecuaria/summary` passará a responder

---

## 5. Plano de Migração

### Sequência de migrations

```
migration_01: add_deleted_at_to_pec_models
  - pec_lotes.deleted_at TIMESTAMP WITH TIME ZONE NULL
  - pec_animais.deleted_at TIMESTAMP WITH TIME ZONE NULL
  - pec_manejos_lote.deleted_at TIMESTAMP WITH TIME ZONE NULL

migration_02: add_fields_to_pec_manejos_lote
  - pec_manejos_lote.responsavel_id UUID NULL → FK cadastros_pessoas
  - pec_manejos_lote.quantidade_produto FLOAT NULL
  - pec_manejos_lote.deposito_id UUID NULL → FK estoque_depositos

migration_03: add_lote_pecuario_to_financeiro
  - fin_despesas.lote_pecuario_id UUID NULL → FK pec_lotes (ON DELETE SET NULL)
  - fin_receitas.lote_pecuario_id UUID NULL → FK pec_lotes (ON DELETE SET NULL)

migration_04: add_performance_indexes
  - CREATE INDEX CONCURRENTLY ix_pec_animais_deleted_at ON pec_animais(deleted_at) WHERE deleted_at IS NULL
  - CREATE INDEX CONCURRENTLY ix_pec_lotes_deleted_at ON pec_lotes(deleted_at) WHERE deleted_at IS NULL
  - CREATE INDEX CONCURRENTLY ix_fin_despesas_lote_pec ON fin_despesas(lote_pecuario_id) WHERE lote_pecuario_id IS NOT NULL
```

### Estratégia de rollback
Cada migration tem `downgrade()` com `DROP COLUMN` correspondente.
Todas as colunas são nullable — rollback não afeta dados existentes.
FK com `ON DELETE SET NULL` — remoção da FK não afeta registros financeiros.

---

## 6. Sequência Final de Implementação (15 itens)

| # | Item | Bloco | Complexidade | Risco |
|---|------|-------|-------------|-------|
| 1 | Corrigir trailing slash em `manejos.py` (`"/" → ""`) | Pre-req | Mínima | 🟢 |
| 2 | Schemas Animal (`Create`, `Update`, `Response`, `Filter`) | A | Baixa | 🟢 |
| 3 | Schema `PaginatedResponse[T]` reutilizável em `core/schemas/` | A | Baixa | 🟢 |
| 4 | `AnimalService` (CRUD + soft-delete + filtros + paginação) | A | Média | 🟡 |
| 5 | `animal_router.py` + registro em `main.py` | A | Baixa | 🟢 |
| 6 | Migration 01 — `deleted_at` nos models pecuários | A | Baixa | 🟢 |
| 7 | Migration 02 — novos campos em `pec_manejos_lote` | D | Baixa | 🟢 |
| 8 | Migration 03 — `lote_pecuario_id` em `fin_despesas` e `fin_receitas` | E | Baixa | 🟢 |
| 9 | Migration 04 — índices de performance | Perf | Baixa | 🟢 |
| 10 | `AnimalService.registrar_pesagem()` com GMD + atualização do Animal | C | Média | 🟡 |
| 11 | Handler de sincronização de `quantidade_cabecas` no `ManejoLoteService` | C | Média | 🟡 |
| 12 | Handler `_registrar_saida_estoque_pecuaria()` no `ManejoLoteService` | D | Baixa | 🟢 |
| 13 | Atualizar `ManejoLoteService` para preencher `lote_pecuario_id` | E | Baixa | �� |
| 14 | Endpoint `GET /pecuaria/animais/{id}/timeline` | B | Média | 🟡 |
| 15 | Endpoint `GET /reports/pecuaria/summary` + `GET /pecuaria/lotes/{id}/resultado` | E | Média | 🟡 |

---

## 7. Riscos Técnicos

| Risco | Probabilidade | Impacto | Mitigação |
|-------|--------------|---------|-----------|
| `BaseService.__init__` com `session=None` em services existentes | Alta | Alto | Corrigir `LoteBovinoService` e `ManejoLoteService` junto com o `AnimalService` no item #4 |
| Handler de estoque falha silenciosamente se `deposito_id` não existir | Média | Médio | Handler deve ser `try/except` com log warning — nunca bloquear o evento principal |
| `deleted_at IS NULL` não filtrado no `BaseService.list_all()` por padrão | Alta | Alto | `AnimalService` deve sobrescrever `list_all()` injetando o filtro |
| `quantidade_cabecas` inconsistente em rebanhos com muitos eventos simultâneos | Baixa | Médio | Recálculo via COUNT é idempotente — aceitar para Fase 1 |

---

## 8. Riscos Arquiteturais

| Risco | Gravidade | Mitigação |
|-------|----------|-----------|
| `AnimalService` tentar chamar financeiro/estoque diretamente | 🔴 ALTO | Proibido. Responsabilidade está no `ManejoLoteService`. `AnimalService` trata apenas do ciclo de vida do animal |
| Dois mecanismos de "exclusão" em LoteAnimal: `ativo: bool` (operacional) e `deleted_at` (permanente) | 🟡 BAIXO | Documentar diferença no model: `ativo=False` = lote encerrado (ainda visível); `deleted_at!=NULL` = excluído permanentemente |
| Timeline retornando tipos incompatíveis sem discriminator | 🟠 MÉDIO | Usar `tipo_origem: Literal["ANIMAL", "LOTE"]` no schema unificado |

---

## 9. Riscos de Regressão

| Área | Risco | Severidade |
|------|-------|-----------|
| `GET /pecuaria/lotes` | Se `BaseService.list_all()` for modificado para filtrar `deleted_at`, pode excluir lotes que usam apenas `ativo: bool` | 🟠 MÉDIO — testar após migration |
| `POST /pecuaria/manejos` | Handler de estoque com produto_id pode gerar erro 500 se depósito inválido | 🟡 BAIXO — handler tolerante |
| `GET /financeiro/despesas` | Campo `lote_pecuario_id` adicional é aditivo — sem risco | 🟢 NENHUM |
| Routers `lotes.py` e `piquetes.py` | Já registrados nas linhas 511 e 516 do `main.py` — sem risco | 🟢 NENHUM |

---

## Checklist de Pré-Condições

- [ ] Confirmar que `pec_lotes.router` está registrado em `main.py` linha 511
- [ ] Confirmar que `pec_piquetes.router` está registrado em `main.py` linha 516
- [ ] Confirmar trailing slash em `manejos.py` está corrigido (item #1)
- [ ] Confirmar que `registrar_ledger_estoque()` está acessível e sem erros no ambiente atual
- [ ] Confirmar que migrations existentes estão aplicadas (`alembic current`)
- [ ] Confirmar que `pec_eventos_animal` tem índice em `(animal_id, data_evento)`

## Fora do Escopo da Fase 1

- Migração de `enterprise.models.sprints_27_33` → domínio `pecuaria/`
- Calendário Sanitário
- Módulo de Reprodução (IATF, Parto, Prenhez)
- Integração com RH/Campo
- Dashboard de KPIs zootécnicos
- ILP / Integração com Agricultura
