# CLAUDE.md — Diretrizes do Projeto AgroSaaS

> Ordem de leitura e guardrails gerais: `docs/architecture/ai-bootstrap.md` (não repetidos aqui).
> Este arquivo é a fonte única de **padrões de código** (como escrever backend/frontend). Não é fonte de
> stack/versões (→ `architecture-inventory.md`) nem de RBAC/multi-tenancy (→ `CORE_MODULE_EXPERT.md`).

## 1. Context Efficiency (MANDATORY)

- **Commands >10 linhas:** use `mcp__plugin_context-mode_context-mode__ctx_batch_execute(commands, queries)` ou `ctx_execute()`
  - NUNCA use Bash para: testes, busca de arquivos, análise de logs, processamento de outputs
  - Exceções: git, mkdir, rm, mv, navegação local
- **Respostas:** ≤150 palavras; artefatos (código, configs) sempre em FILES, nunca inline.
- **Idioma:** pt-BR.
- **Decimais:** "," como separador decimal, "." como separador de milhar.
- **Formatação de campos:** sempre usar máscaras (CPF, CNPJ etc.) para input ou apresentação.
- **Code review loops:** delegar a subagents via Agent tool com `isolation=worktree`.
- **Busca de padrões:** Grep com glob patterns (`--glob="*.ts"`), não `find`.
- **Confirmação ao usuário:** sempre via `AlertDialog` (`@/components/ui/alert-dialog`).
- **Componentes:** usar sempre os padrões de `@/components/ui/`; código customizado só se solicitado explicitamente.

## 2. Stack

Ver `docs/architecture/architecture-inventory.md` para versões, libs e infraestrutura completas.
Resumo: FastAPI + SQLAlchemy 2 async + PostgreSQL (backend) · Next.js 16 App Router + shadcn/ui + TanStack Query + Zustand (frontend) · monorepo pnpm.

## 3. Segurança — Multi-tenancy

Regras completas, estrutura de JWT e RBAC de três camadas: **`.claude/skills/CORE_MODULE_EXPERT.md`** (fonte única — não duplicar aqui).

Resumo do que nunca muda:
- `tenant_id` vem sempre do JWT validado — nunca do frontend.
- NUNCA fazer query SQLAlchemy direta em routers — sempre via `BaseService` (injeta `tenant_id` automaticamente).
- Toda violação de tenant vira `TenantViolationError` → 403, logada como incidente de segurança.

```python
# ❌ NUNCA
stmt = select(Safra).where(Safra.status == "ATIVA")

# ✅ SEMPRE
service = SafraService(session, tenant_id)
safras = await service.list_all(skip=0, limit=100, status="ATIVA")
```

## 4. Padrões Backend

### 4.1 Estrutura de Diretórios
```
services/api/
├─ main.py                    # FastAPI app + router registration (linhas 91-130)
├─ core/
│  ├─ config.py / database.py / dependencies.py / exceptions.py / base_service.py / constants.py
│  ├─ models/base.py          # Base SQLAlchemy (tenant_id, created_at, updated_at)
│  └─ services/audit_service.py
├─ agricola/                  # 22 submódulos — cada um: models.py, schemas.py, service.py, router.py
├─ pecuaria/
├─ financeiro/
└─ ...

migrations/
├─ env.py, script.py.mako
└─ versions/
```

### 4.2 Modelo — Padrão Base
```python
class Safra(Base):
    __tablename__ = "safras"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by: Mapped[uuid.UUID] = mapped_column(nullable=True)

    ano_safra: Mapped[str] = mapped_column(String(20), nullable=False)
    area_plantada_ha: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=True)  # NUNCA Float p/ valores!

    talhoes: Mapped[list["SafraTalhao"]] = relationship(back_populates="safra", lazy="noload")

    __table_args__ = (
        Index("ix_safras_tenant_ano", tenant_id, ano_safra),
    )
```

**Regras:** todo model tem `tenant_id`; NUNCA `Float` para valores monetários/área (usar `Decimal`); `lazy="noload"` por padrão (evita N+1); timestamps obrigatórios; `Index()` em queries frequentes.

### 4.3 Schema — Pydantic v2
```python
class SafraCreate(BaseModel):
    ano_safra: str
    area_plantada_ha: float | None = None

class SafraResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    ano_safra: str
    created_at: datetime
```

### 4.4 Service — CRUD + Negócio
```python
class SafraService(BaseService[Safra]):
    """Herda: get, get_or_fail, list_all, create, update, hard_delete"""

    async def avancar_fase(self, safra_id: UUID, nova_fase: str) -> Safra:
        safra = await self.get_or_fail(safra_id)
        if not self._fase_permitida(safra.status, nova_fase):
            raise BusinessRuleError(f"Transição {safra.status} → {nova_fase} não permitida")
        return await self.update(safra.id, {"status": nova_fase})
```

### 4.5 Router
```python
router = APIRouter(prefix="/safras", tags=["Safras"])

@router.post("/", response_model=SafraResponse, status_code=status.HTTP_201_CREATED)
@require_tenant_permission("agricola:safra:criar")
async def create_safra(
    safra_in: SafraCreate,
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    service = SafraService(session, tenant_id)
    return await service.create(safra_in)
```

### 4.6 Migrations — Alembic + Async
```bash
alembic revision --autogenerate -m "adiciona campo abc"
alembic upgrade head
```
**Regra crítica:** após `run_sync()`, sempre `op.execute("COMMIT")` — sem isso há rollback silencioso.

## 5. Padrões Frontend

Padrão RSC completo (quando usar/não usar, `page.tsx` + `Client.tsx`, `Promise.allSettled`, tier-based loading): **`docs/architecture/frontend-rsc-pattern.md`** (fonte única).

### 5.1 Estrutura
```
apps/web/src/
├─ app/                    # Next.js App Router
├─ components/ui/          # shadcn/ui customizados
├─ components/shared/       # reutilizáveis (page-header, empty-state, sidebar)
├─ components/<dominio>/    # componentes de domínio (agricola, estoque, contabilidade...)
├─ lib/api.ts, lib/utils.ts, lib/stores/
├─ hooks/
└─ styles/globals.css
```

### 5.2 Data Table — Padrão Obrigatório
Coluna de ação sempre por último, sem header de texto, botões `ghost` `size="icon"` sem borda:
```tsx
{
  id: "acoes",
  header: "",
  cell: (_, row) => (
    <div className="flex items-center gap-0 justify-end">
      <Button size="icon" variant="ghost" className="size-7 text-primary" aria-label="Visualizar" asChild>
        <Link href={`/dashboard/agricola/safras/${row.id}`}><Eye className="size-3.5" /></Link>
      </Button>
    </div>
  ),
}
```

### 5.3 Forms — react-hook-form + Zod
```tsx
const safraSchema = z.object({
  ano_safra: z.string().min(1, "Ano safra obrigatório"),
  area_plantada_ha: z.number().positive().optional(),
});

export function SafraForm({ onSubmit }: { onSubmit: (data: z.infer<typeof safraSchema>) => void }) {
  const { register, handleSubmit, formState: { errors } } = useForm({ resolver: zodResolver(safraSchema) });
  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <Input {...register("ano_safra")} placeholder="Ex: 2024/25" />
      <Button type="submit">Salvar</Button>
    </form>
  );
}
```

### 5.4 State Management — Zustand
```typescript
export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      activeFazendaId: null,
      setActiveFazenda: (id) => set({ activeFazendaId: id }),
    }),
    { name: "app-store", partialize: (state) => ({ activeFazendaId: state.activeFazendaId }) }
  )
);
```

## 6. Fluxos Comuns de Desenvolvimento

### 6.1 Criar Novo Endpoint
1. Backend: `models.py` → `schemas.py` → `service.py` (`BaseService`) → `router.py` → registrar em `main.py` (linha 91-130) → migration Alembic se schema muda.
2. Frontend: `page.tsx` (RSC) → componentes de domínio → atualizar `packages/zod-schemas`.
3. Testar: `pytest tests/.../test_novo_feature.py` (backend) + `npm test` (frontend).
4. Commit atômico: `feat(novo_feature): descrição`.

### 6.2 Adicionar Permissão / Módulo Feature Gate

Ver `.claude/skills/CORE_MODULE_EXPERT.md` — fonte única de RBAC e módulos.

## 7. Testes

```bash
# Backend
cd services/api && pytest tests/agricola/test_safras.py -v
pytest tests/ -k "tenant_isolation" -v  # segurança

# Frontend
cd apps/web && npm test
```

Todo endpoint precisa de teste de isolamento de tenant (usuário de tenant1 não vê dados de tenant2 → `EntityNotFoundError`).

## 8. Performance & Otimizações

```python
# ❌ N+1
for safra in await service.list_all():
    print(safra.talhoes)

# ✅ Eager loading
stmt = select(Safra).options(selectinload(Safra.talhoes))
```

- Paginação sempre (`skip`/`limit`, `limit` máx 1000).
- Índices compostos para queries frequentes (ver 4.2).
- Regras de contexto: Bash só para git/mkdir/rm/mv; output >10 linhas via `ctx_execute`; `Read` só para Edit ou schemas não-analíticos (ver §1).

## 9. Known Issues & Soluções

**CORS após editar `main.py`:** `pkill -f uvicorn && ./start_server.sh`

**Alembic async — rollback silencioso:**
```python
def upgrade():
    with op.batch_alter_table(...) as batch:
        batch.add_column(...)
    op.execute("COMMIT")  # obrigatório
```

**Router não registrado (404):** adicionar `include_router` em `main.py` (~linha 110).

**SQLite:** não usar exceto se solicitado — RLS não funciona em SQLite; dev local usa PostgreSQL via `.env`.

## 10. Estrutura de Módulos Agrícola

22 submódulos em `/services/api/agricola/` — lista completa e tier de cada um: `.claude/skills/AGRICOLA_MODULE_EXPERT.md`.

## 11. Referências Rápidas

### Imports Padrão
```python
from core.base_service import BaseService
from core.dependencies import get_tenant_id, require_tenant_permission
from sqlalchemy import select, and_, insert, update, delete
```
```typescript
import { useQuery, useMutation } from "@tanstack/react-query";
import { useAppStore } from "@/lib/stores/app-store";
import { apiFetch } from "@/lib/api";
```

### Dev Server Commands
```bash
cd services/api && ./start_server.sh
cd apps/web && pnpm dev
pkill -f "uvicorn|next dev"
```

### Links Essenciais
- Ordem de leitura: `docs/architecture/ai-bootstrap.md`
- RBAC/JWT/Multi-tenancy: `.claude/skills/CORE_MODULE_EXPERT.md`
- Stack/Inventário: `docs/architecture/architecture-inventory.md`
- Padrão RSC: `docs/architecture/frontend-rsc-pattern.md`
- Domínios/fronteiras: `docs/architecture/agrosaas-domain-map.md`
- Checklist de engenharia (TDD, code review): `docs/architecture/agrosaas-engineering-playbook.md`

---
**Última atualização:** 2026-07-16
**Maintainer:** Borgus Software Ltda