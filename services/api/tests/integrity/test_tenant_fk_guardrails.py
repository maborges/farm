"""
Guardrails automatizados de integridade multi-tenant.

Consulta o catálogo PostgreSQL em tempo de execução. Deve rodar em CI a cada
PR que toque models.py ou migrations/.

Markers:
  phase_01c  — guardrails criados/validados na fase TENANT-INTEGRITY-REPAIR-01C
  phase_other — guardrails de fases futuras (01B, 01D); falhas são débitos conhecidos

Cobertura:
  G1 — Nenhuma FK direta para tenants com ON DELETE CASCADE         [phase_other/01D]
  G2 — Toda tabela física tenant-scoped possui FK para tenants      [phase_other/01B]
  G3 — Toda tabela tenant-scoped possui índice na coluna tenant_id  [phase_other/01B]
  G4 — Nenhum cruzamento A→B nos 7 agregados críticos              [phase_01c]
  G5 — Nenhuma FK para tenants NOT VALID pendente                  [phase_01c]
  G6 — UNIQUE(tenant_id, id) existe estruturalmente nos 4 pais     [phase_01c]
  G7 — 7 FKs compostas presentes e validadas                       [phase_01c]

Exceções documentadas (não falham):
  - territory_legacy_backup_01h2 (backup territorial legado — ver 01D)
  - email_logs (ON DELETE NO ACTION deliberado)
"""
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# Tabelas explicitamente excluídas de guardrails específicos
EXCEÇÕES_TENANT_FK = frozenset({
    "territory_legacy_backup_01h2",
})

# Tabelas com ON DELETE NO ACTION intencional (não CASCADE, não RESTRICT)
EXCEÇÕES_NO_ACTION = frozenset({
    "email_logs",
})

# Agregados com FK composta implantada em 01C — usados no G4
AGREGADOS_CRITICOS = [
    {
        "relacao": "cadastros_areas_rurais → unidades_produtivas",
        "filho": "cadastros_areas_rurais",
        "col_filho": "tenant_id",
        "col_fk": "unidade_produtiva_id",
        "pai": "unidades_produtivas",
        "col_pai_tenant": "tenant_id",
        "col_pai_id": "id",
    },
    {
        "relacao": "estoque_depositos → unidades_produtivas",
        "filho": "estoque_depositos",
        "col_filho": "tenant_id",
        "col_fk": "unidade_produtiva_id",
        "pai": "unidades_produtivas",
        "col_pai_tenant": "tenant_id",
        "col_pai_id": "id",
    },
    {
        "relacao": "cadastros_equipamentos → unidades_produtivas",
        "filho": "cadastros_equipamentos",
        "col_filho": "tenant_id",
        "col_fk": "unidade_produtiva_id",
        "pai": "unidades_produtivas",
        "col_pai_tenant": "tenant_id",
        "col_pai_id": "id",
    },
    {
        "relacao": "compras_pedidos → estoque_depositos",
        "filho": "compras_pedidos",
        "col_filho": "tenant_id",
        "col_fk": "deposito_id",
        "pai": "estoque_depositos",
        "col_pai_tenant": "tenant_id",
        "col_pai_id": "id",
    },
    {
        "relacao": "frota_jornadas_equipamento → unidades_produtivas",
        "filho": "frota_jornadas_equipamento",
        "col_filho": "tenant_id",
        "col_fk": "unidade_produtiva_id",
        "pai": "unidades_produtivas",
        "col_pai_tenant": "tenant_id",
        "col_pai_id": "id",
    },
    {
        "relacao": "frota_apontamentos_uso → frota_jornadas_equipamento",
        "filho": "frota_apontamentos_uso",
        "col_filho": "tenant_id",
        "col_fk": "jornada_id",
        "pai": "frota_jornadas_equipamento",
        "col_pai_tenant": "tenant_id",
        "col_pai_id": "id",
    },
    {
        "relacao": "frota_abastecimentos → cadastros_equipamentos",
        "filho": "frota_abastecimentos",
        "col_filho": "tenant_id",
        "col_fk": "equipamento_id",
        "pai": "cadastros_equipamentos",
        "col_pai_tenant": "tenant_id",
        "col_pai_id": "id",
    },
]


pytestmark_other = pytest.mark.phase_other
pytestmark_01c = pytest.mark.phase_01c


# ─────────────────────────────────────────────────────────────
# G1 — Nenhuma FK para tenants com ON DELETE CASCADE           [phase_other/01D]
# ─────────────────────────────────────────────────────────────
@pytest.mark.phase_other
async def test_g1_nenhuma_fk_cascade_para_tenants(catalog_session: AsyncSession) -> None:
    """CASCADE em FK para tenants permite exclusão destrutiva silenciosa."""
    result = await catalog_session.execute(text("""
        SELECT c.conname, c.conrelid::regclass::text AS tabela
        FROM pg_constraint c
        WHERE c.contype     = 'f'
          AND c.confrelid   = 'farms.tenants'::regclass
          AND c.confdeltype = 'c'
        ORDER BY tabela
    """))
    violacoes = result.fetchall()

    assert not violacoes, (
        f"G1 FALHOU — {len(violacoes)} FK(s) para tenants com ON DELETE CASCADE:\n"
        + "\n".join(f"  • {t} ({n})" for n, t in violacoes)
        + "\nExecutar TENANT-FK-REPAIR-01D para converter para RESTRICT."
    )


# ─────────────────────────────────────────────────────────────
# G2 — Toda tabela física tenant-scoped tem FK para tenants    [phase_other/01B]
# ─────────────────────────────────────────────────────────────
@pytest.mark.phase_other
async def test_g2_todas_tabelas_tenant_scoped_tem_fk(catalog_session: AsyncSession) -> None:
    """Tabelas com tenant_id uuid sem FK permitem orphans de tenants inexistentes."""
    result = await catalog_session.execute(text("""
        SELECT t.table_name
        FROM information_schema.columns c
        JOIN information_schema.tables t
            ON t.table_name   = c.table_name
           AND t.table_schema = c.table_schema
        WHERE c.table_schema  = 'farms'
          AND c.column_name   = 'tenant_id'
          AND c.data_type     = 'uuid'
          AND t.table_type    = 'BASE TABLE'
          AND NOT EXISTS (
              SELECT 1 FROM pg_constraint pk
              WHERE pk.contype   = 'f'
                AND pk.conrelid  = (c.table_schema || '.' || c.table_name)::regclass
                AND pk.confrelid = 'farms.tenants'::regclass
          )
        ORDER BY t.table_name
    """))
    ausentes = [
        row[0] for row in result.fetchall()
        if row[0] not in EXCEÇÕES_TENANT_FK
    ]

    assert not ausentes, (
        f"G2 FALHOU — {len(ausentes)} tabela(s) com tenant_id uuid sem FK para tenants:\n"
        + "\n".join(f"  • {t}" for t in ausentes)
        + "\nAdicionar FK RESTRICT via TENANT-FK-REPAIR-01B ou migration equivalente."
    )


# ─────────────────────────────────────────────────────────────
# G3 — Toda tabela tenant-scoped tem índice em tenant_id       [phase_other/01B]
# ─────────────────────────────────────────────────────────────
@pytest.mark.phase_other
async def test_g3_indice_tenant_id_presente(catalog_session: AsyncSession) -> None:
    """Ausência de índice em tenant_id degrada todas as queries filtradas por tenant."""
    result = await catalog_session.execute(text("""
        SELECT t.table_name
        FROM information_schema.columns c
        JOIN information_schema.tables t
            ON t.table_name   = c.table_name
           AND t.table_schema = c.table_schema
        WHERE c.table_schema = 'farms'
          AND c.column_name  = 'tenant_id'
          AND t.table_type   = 'BASE TABLE'
          AND NOT EXISTS (
              SELECT 1 FROM pg_indexes ix
              WHERE ix.schemaname = 'farms'
                AND ix.tablename  = c.table_name
                AND ix.indexdef  LIKE '%tenant_id%'
          )
        ORDER BY t.table_name
    """))
    sem_indice = [row[0] for row in result.fetchall()]

    assert not sem_indice, (
        f"G3 FALHOU — {len(sem_indice)} tabela(s) sem índice em tenant_id:\n"
        + "\n".join(f"  • {t}" for t in sem_indice)
        + "\nAdicionar: CREATE INDEX CONCURRENTLY ON farms.<tabela> (tenant_id)."
    )


# ─────────────────────────────────────────────────────────────
# G4 — Zero cruzamentos A→B nos 7 agregados críticos
# ─────────────────────────────────────────────────────────────
@pytest.mark.phase_01c
@pytest.mark.parametrize("agg", AGREGADOS_CRITICOS, ids=[a["relacao"] for a in AGREGADOS_CRITICOS])
async def test_g4_zero_cruzamentos_tenant(catalog_session: AsyncSession, agg: dict) -> None:
    """Filho com tenant_id diferente do pai indica vazamento de dados entre tenants."""
    result = await catalog_session.execute(text(f"""
        SELECT COUNT(*) FROM farms.{agg['filho']} filho
        JOIN farms.{agg['pai']} pai ON pai.{agg['col_pai_id']} = filho.{agg['col_fk']}
        WHERE filho.{agg['col_fk']} IS NOT NULL
          AND filho.{agg['col_filho']} <> pai.{agg['col_pai_tenant']}
    """))
    count = result.scalar()

    assert count == 0, (
        f"G4 FALHOU — {count} cruzamento(s) A→B em [{agg['relacao']}].\n"
        "Executar TENANT-FK-REPAIR-01A (quarentena) para remover antes de adicionar FK composta."
    )


# ─────────────────────────────────────────────────────────────
# G5 — Nenhuma FK para tenants NOT VALID pendente (VALIDATE esquecido)
# ─────────────────────────────────────────────────────────────
@pytest.mark.phase_01c
async def test_g5_nenhuma_fk_not_valid_pendente(catalog_session: AsyncSession) -> None:
    """FK NOT VALID não oferece proteção efetiva — VALIDATE deve ser executado."""
    result = await catalog_session.execute(text("""
        SELECT c.conname, c.conrelid::regclass::text AS tabela
        FROM pg_constraint c
        WHERE c.contype     = 'f'
          AND c.confrelid   = 'farms.tenants'::regclass
          AND NOT c.convalidated
        ORDER BY tabela
    """))
    pendentes = result.fetchall()

    assert not pendentes, (
        f"G5 FALHOU — {len(pendentes)} FK(s) NOT VALID sem VALIDATE:\n"
        + "\n".join(f"  • {t} ({n})" for n, t in pendentes)
        + "\nExecutar: ALTER TABLE farms.<tabela> VALIDATE CONSTRAINT <nome>."
    )


# ─────────────────────────────────────────────────────────────
# G6 — UNIQUE(tenant_id, id) existe estruturalmente nos 4 pais [phase_01c]
#
# Valida pela presença das colunas (tenant_id, id) em constraint UNIQUE,
# independente do nome atribuído à constraint. Isso é correto porque:
#   - unidades_produtivas tem uq_unidades_produtivas_tenant_id_id (pré-existente)
#   - frota_jornadas_equipamento tem uq_frota_jornadas_tenant_id (criado em 01C)
# A estrutura é o que garante a integridade; o nome é secundário.
# ─────────────────────────────────────────────────────────────
@pytest.mark.phase_01c
@pytest.mark.parametrize("tabela", [
    "unidades_produtivas",
    "estoque_depositos",
    "cadastros_equipamentos",
    "frota_jornadas_equipamento",
])
async def test_g6_unique_composto_pai(
    catalog_session: AsyncSession,
    tabela: str,
) -> None:
    """UNIQUE(tenant_id, id) estrutural no pai — pré-requisito para FK composta."""
    result = await catalog_session.execute(text("""
        SELECT COUNT(*) FROM pg_constraint c
        WHERE c.contype  = 'u'
          AND c.conrelid = ('farms.' || :tabela)::regclass
          AND array_length(c.conkey, 1) = 2
          AND EXISTS (
              SELECT 1 FROM pg_attribute a
              WHERE a.attrelid = c.conrelid
                AND a.attnum   = ANY(c.conkey)
                AND a.attname  = 'tenant_id'
          )
          AND EXISTS (
              SELECT 1 FROM pg_attribute a
              WHERE a.attrelid = c.conrelid
                AND a.attnum   = ANY(c.conkey)
                AND a.attname  = 'id'
          )
    """), {"tabela": tabela})
    count = result.scalar()

    assert count >= 1, (
        f"G6 FALHOU — nenhum UNIQUE(tenant_id, id) encontrado em farms.{tabela}.\n"
        "Executar TENANT-FK-REPAIR-01C step1."
    )


# ─────────────────────────────────────────────────────────────
# G7 — FKs compostas dos 7 agregados estão presentes
# ─────────────────────────────────────────────────────────────
@pytest.mark.phase_01c
@pytest.mark.parametrize("constraint_name,tabela", [
    ("fk_car_tenant_unidade_produtiva",  "cadastros_areas_rurais"),
    ("fk_ed_tenant_unidade_produtiva",   "estoque_depositos"),
    ("fk_ce_tenant_unidade_produtiva",   "cadastros_equipamentos"),
    ("fk_cp_tenant_deposito",            "compras_pedidos"),
    ("fk_fje_tenant_unidade_produtiva",  "frota_jornadas_equipamento"),
    ("fk_fau_tenant_jornada",            "frota_apontamentos_uso"),
    ("fk_fa_tenant_equipamento",         "frota_abastecimentos"),
])
async def test_g7_fk_composta_presente(
    catalog_session: AsyncSession,
    constraint_name: str,
    tabela: str,
) -> None:
    """FK composta garante que filho e pai pertencem ao mesmo tenant."""
    result = await catalog_session.execute(text("""
        SELECT COUNT(*) FROM pg_constraint
        WHERE contype  = 'f'
          AND conname  = :name
          AND conrelid = ('farms.' || :tabela)::regclass
          AND convalidated = true
    """), {"name": constraint_name, "tabela": tabela})
    count = result.scalar()

    assert count == 1, (
        f"G7 FALHOU — FK composta '{constraint_name}' ausente ou NOT VALID em farms.{tabela}.\n"
        "Executar TENANT-FK-REPAIR-01C step2."
    )
