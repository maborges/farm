# TENANT-INTEGRITY-REPAIR-01B4 — IoT e Auxiliares

**Data:** 2026-07-17  
**Escopo:** `case_ih`, `john_deere`, `comparador_precos`, `whatsapp`  
**Head anterior:** `tenant_integrity_repair_01b3_multiprovider`  
**Head resultante:** `tenant_integrity_repair_01b4_iot_auxiliares`

---

## Preflight

| Tabela | RLS | FORCE RLS | Rows | Tipo anterior |
|--------|-----|-----------|------|---------------|
| case_ih | f | f | 0 | character varying |
| john_deere | f | f | 0 | character varying |
| comparador_precos | f | f | 0 | character varying |
| whatsapp | f | f | 0 | character varying |

- Nenhuma policy RLS ativa — bypass não foi necessário.
- Todas as tabelas estavam vazias — nenhum risco de dados incompatíveis.
- Nenhuma tabela excluída do escopo.

---

## Migration

Arquivo: `services/api/migrations/versions/tenant_integrity_repair_01b4_iot_auxiliares.py`

Estratégia por tabela:
1. `ALTER COLUMN tenant_id TYPE uuid USING tenant_id::uuid`
2. `ADD CONSTRAINT fk_<tabela>_tenant FOREIGN KEY (tenant_id) REFERENCES farms.tenants(id) ON DELETE NO ACTION NOT VALID`
3. `VALIDATE CONSTRAINT fk_<tabela>_tenant`

---

## Resultado no Banco

Aplicado via psql (Alembic não disponível no worktree por conflito de import em `integracoes/models.py`).

| Constraint | Tabela | Referência | Validada | Delete rule |
|-----------|--------|-----------|----------|-------------|
| fk_case_ih_tenant | case_ih | tenants | ✓ | NO ACTION (a) |
| fk_john_deere_tenant | john_deere | tenants | ✓ | NO ACTION (a) |
| fk_comparador_precos_tenant | comparador_precos | tenants | ✓ | NO ACTION (a) |
| fk_whatsapp_tenant | whatsapp | tenants | ✓ | NO ACTION (a) |

`alembic_version` atualizado para `tenant_integrity_repair_01b4_iot_auxiliares`.

---

## Grafo Alembic

```
tenant_integrity_repair_01b3_multiprovider
  └─ tenant_integrity_repair_01b4_iot_auxiliares  ← HEAD aplicado
       └─ tenant_fk_repair_01d_cascade_to_restrict  (unapplied — aguarda 01B5)
```

**Nota:** O `down_revision` de 01D permanece apontando para 01B3 no repositório principal.
No worktree este arquivo não existe — será reposicionado em PR separado após 01B5.

---

## Models Atualizados

- `iot_integracao/models/case_ih.py` — `String(50)` → `UUID(as_uuid=True)` + FK
- `iot_integracao/models/john_deere.py` — idem
- `iot_integracao/models/comparador_precos.py` — idem
- `iot_integracao/models/whatsapp.py` — idem

---

## Testes

Arquivo: `tests/integrity/test_tenant_fk_guardrails.py`

4 guardrails × 4 tabelas = 16 casos adicionados:

| Test | Verifica |
|------|---------|
| `test_b4_tenant_id_uuid` | `data_type = 'uuid'` no catálogo |
| `test_b4_fk_para_tenants` | FK validada para `farms.tenants` |
| `test_b4_sem_cascade` | Nenhuma FK CASCADE |
| `test_b4_indice_tenant_id` | Índice em `tenant_id` presente |

Marker registrado em `pyproject.toml`: `phase_01b4`.

---

## Veredicto

✅ **01B4 COMPLETO** — 4/4 tabelas convertidas, FKs validadas, NO ACTION confirmado, alembic_version atualizado, models sincronizados, testes adicionados.
