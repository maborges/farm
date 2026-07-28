# Brainstorm — Receitas de Aplicação no Planejamento Operacional

## Problema
No Planejamento Operacional (`apps/web/src/components/agricola/planejamento-operacional-safra.tsx`), inserir insumos/mão de obra é feito um a um por tarefa (`AddInsumoDialog`/`AddMaoObraDialog`), gerando atrito quando várias tarefas do mesmo plano usam o mesmo pacote de insumos (ex: mesma pulverização em vários talhões).

## Decisão
Criar um cadastro reutilizável de **Receita de Aplicação** (produto + dose/ha + mão de obra padrão) que pode ser aplicado em lote a várias tarefas selecionadas dentro de um plano. Dose informada por hectare; usuário pode alterar depois individualmente.

Descartado: (a) modal de lote sem persistir como template — não reaproveitável entre planos/safras; (c) copiar insumos de tarefa já lançada — não resolve o primeiro lançamento.

Não há conflito com o módulo `prescricoes` (VRA) — está desativado (`models.py.bak`) e resolve um problema diferente (grade de taxa variável por talhão específico via shapefile/KML), não uma receita reutilizável de dose/ha.

## Banco de dados

Novo submódulo `services/api/agricola/receitas_aplicacao/`:

```python
class ReceitaAplicacao(Base):
    __tablename__ = "receitas_aplicacao"
    id, tenant_id
    nome: str
    tipo_operacao: str | None  # ADUBACAO, PULVERIZACAO...
    ativo: bool = True
    created_at / updated_at / created_by

class ReceitaAplicacaoInsumo(Base):
    __tablename__ = "receitas_aplicacao_insumos"
    id, tenant_id
    receita_id: FK receitas_aplicacao (CASCADE)
    produto_id: FK cadastros_produtos
    dose_ha: Numeric(12,4)
    unidade_dose: str

class ReceitaAplicacaoMaoObra(Base):
    __tablename__ = "receitas_aplicacao_mao_obra"
    id, tenant_id
    receita_id: FK receitas_aplicacao (CASCADE)
    tipo_servico_id: FK cadastros_tipos_servico
    funcao: str | None
    quantidade_pessoas: int
    horas_estimadas_ha: Numeric  # escalado pela área na aplicação
```

Reaproveita `PlanoOperacionalTarefaInsumo.dose_planejada`/`unidade_dose` (já existentes) — ao aplicar a receita, calcula `quantidade_planejada = dose_ha × área do talhão` (via `SafraTarefa.talhao_id → AreaRural.area_hectares_manual|area_hectares`), no mesmo padrão de `analises_solo/service.py::vincular_e_gerar_tarefas`.

Endpoint em lote:
```
POST /agricola/planejamento-operacional/{planoId}/aplicar-receita
body: { receita_id: UUID, plano_operacional_tarefa_ids: UUID[] }
```
Cria N `PlanoOperacionalTarefaInsumo` + N `PlanoOperacionalTarefaMaoObra`, uma vez por tarefa selecionada, com `fonte_custo` calculado igual ao fluxo individual atual.

Migration Alembic nova (3 tabelas) + `op.execute("COMMIT")`. Índices: `(tenant_id, nome)` em receitas; `(tenant_id, receita_id)` nas filhas.

## UI/UX

**Cadastro de Receitas** (`/dashboard/agricola/cadastros/receitas-aplicacao`): lista (DataTable padrão) + form com `useFieldArray` para N insumos (produto + dose/ha + unidade) e N mão de obra (tipo de serviço + horas/ha + qtd pessoas).

**No Planejamento Operacional**: accordion de tarefas ganha checkbox por item + barra "N selecionadas" com botão "Aplicar receita" → `AplicarReceitaDialog` (select de receita, preview do conteúdo, lista de tarefas/talhões alvo, confirmação via `AlertDialog`). Mutation invalida `["plano-insumos", itemId]`/`["plano-mao-obra", itemId]` de todos os itens afetados.

## Segurança

- `ReceitaAplicacaoService(BaseService[ReceitaAplicacao])`, `tenant_id` via `get_tenant_id()`.
- Permissões: `agricola:receita_aplicacao:ler|criar|editar|excluir`, `agricola:planejamento_operacional:aplicar_receita`.
- `aplicar-receita` valida que cada `plano_operacional_tarefa_id` pertence ao mesmo tenant e ao mesmo plano da URL (evita IDOR entre planos/tenants).
- Teste de isolamento de tenant obrigatório.

## Arquivos a criar/alterar

Backend:
- `services/api/agricola/receitas_aplicacao/{models,schemas,service,router}.py`
- `services/api/agricola/planejamento_operacional/{schemas,service,router}.py` (endpoint `aplicar_receita`)
- Migration Alembic
- `main.py` (registrar router)
- `tests/agricola/test_receitas_aplicacao.py` + teste de isolamento em planejamento operacional

Frontend:
- `apps/web/src/app/(dashboard)/agricola/cadastros/receitas-aplicacao/{page.tsx,Client.tsx}`
- `apps/web/src/components/agricola/receita-aplicacao-form.tsx`
- `apps/web/src/components/agricola/planejamento-operacional-safra.tsx` (seleção múltipla + `AplicarReceitaDialog`)
- `packages/zod-schemas` (schemas `ReceitaAplicacao*`)

## Ordem de implementação
Migration → models → service → router → registrar em `main.py` → frontend cadastro de receitas → frontend seleção múltipla + aplicar receita no plano → testes.
