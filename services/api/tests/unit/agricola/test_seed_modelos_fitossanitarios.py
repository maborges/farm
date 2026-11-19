from __future__ import annotations

import pytest
from sqlalchemy.dialects import postgresql

from agricola.climatico.models import ModeloFitossanitario
from agricola.climatico.schemas import validar_regras_fitossanitarias
from scripts.initial_load.seed_culturas import CULTURAS_SEED
from scripts.initial_load.seed_modelos_fitossanitarios import (
    MODELOS_FITOSSANITARIOS_BASE,
    _seed_modelos_fitossanitarios,
)

PIPELINE_VARIABLES = {"temp_media_c", "umidade_rel_pct", "precipitacao_mm"}
CULTURAS_SEM_MODELO_CLIMATICO_DIARIO = {"Sisal"}
CHAVES_ORIGINAIS_PRESERVADAS = {
    ("Soja", "Ferrugem Asiática"),
    ("Soja", "Mofo-branco"),
    ("Soja", "Mancha-alvo"),
    ("Soja", "Oídio"),
    ("Milho", "Mancha-de-turcicum"),
    ("Milho", "Cercosporiose"),
    ("Milho", "Ferrugem Polissora"),
    ("Café", "Ferrugem do Cafeeiro"),
    ("Café", "Cercosporiose"),
    ("Trigo", "Ferrugem-da-folha"),
    ("Trigo", "Giberela"),
    ("Feijão", "Antracnose"),
    ("Algodão", "Mancha-de-ramulária"),
}


class _Result:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows

    def scalars(self):
        return self


class _SeedSession:
    def __init__(self, *, fail_on_commit: bool = False):
        self.entries = []
        self.added = []
        self.deleted = []
        self.statements = []
        self.events = []
        self.flush_count = 0
        self.commit_count = 0
        self.rollback_count = 0
        self.fail_on_commit = fail_on_commit

    async def execute(self, statement, _params=None):
        self.statements.append(statement)
        sql_text = str(statement)
        if "set_config" in sql_text:
            return _Result([])
        col_descs = getattr(statement, "column_descriptions", None) or []
        if len(col_descs) == 1 and col_descs[0].get("entity") is ModeloFitossanitario:
            return _Result([
                entry for entry in self.entries if getattr(entry, "tenant_id", None) is None
            ])
        return _Result([
            (entry.cultura, entry.doenca)
            for entry in self.entries
            if getattr(entry, "tenant_id", None) is None
        ])

    def add(self, entry):
        self.events.append("add")
        self.added.append(entry)
        self.entries.append(entry)

    async def delete(self, entry):
        self.events.append("delete")
        if entry in self.entries:
            self.entries.remove(entry)
        self.deleted.append(entry)

    async def flush(self):
        self.events.append("flush")
        self.flush_count += 1

    async def commit(self):
        self.events.append("commit")
        if self.fail_on_commit:
            raise RuntimeError("falha simulada no commit")
        self.commit_count += 1

    async def rollback(self):
        self.rollback_count += 1


def test_modelos_base_respeitam_schema_culturas_canonicas_e_proveniencia():
    culturas_validas = {item["nome"] for item in CULTURAS_SEED}
    chaves: set[tuple[str, str]] = set()

    assert len(MODELOS_FITOSSANITARIOS_BASE) == 78

    for entry in MODELOS_FITOSSANITARIOS_BASE:
        cultura = entry["cultura"]
        doenca = entry["doenca"]
        regras = entry["regras_risco"]

        assert isinstance(cultura, str) and cultura in culturas_validas
        assert isinstance(doenca, str) and doenca.strip()
        assert (cultura, doenca) not in chaves
        chaves.add((cultura, doenca))

        validar_regras_fitossanitarias(regras)

        variaveis = {cond["variavel"] for cond in regras["condicoes"]}
        assert variaveis.issubset(PIPELINE_VARIABLES)
        assert sum(cond["peso"] for cond in regras["condicoes"]) == pytest.approx(1.0)

        metadados = regras["metadados"]
        assert metadados["tipo_resultado"] == "referencia_favorabilidade_climatica"
        assert metadados["somente_referencia"] is True
        assert isinstance(metadados["agente_causal"], str) and metadados["agente_causal"].strip()
        assert isinstance(metadados["fonte_parametros"], str) and metadados["fonte_parametros"].strip()
        assert isinstance(metadados["fonte_url"], str) and metadados["fonte_url"].startswith("https://")
        assert isinstance(metadados["versao_regra"], str) and metadados["versao_regra"].strip()
        assert isinstance(metadados["observacao"], str) and metadados["observacao"].strip()

    culturas_cobertas = {entry["cultura"] for entry in MODELOS_FITOSSANITARIOS_BASE}
    assert culturas_cobertas == culturas_validas - CULTURAS_SEM_MODELO_CLIMATICO_DIARIO
    assert CHAVES_ORIGINAIS_PRESERVADAS.issubset(chaves)


@pytest.mark.asyncio
async def test_seed_modelos_insere_apenas_globais_e_eh_idempotente():
    session = _SeedSession()

    inseridos, existentes = await _seed_modelos_fitossanitarios(session)

    assert inseridos == len(MODELOS_FITOSSANITARIOS_BASE)
    assert existentes == 0
    assert len(session.added) == len(MODELOS_FITOSSANITARIOS_BASE)
    assert all(entry.tenant_id is None for entry in session.added)
    assert all(entry.is_global is True for entry in session.added)
    assert session.commit_count == 1

    assert "set_config" in str(session.statements[0])
    select_sql = str(session.statements[1].compile(dialect=postgresql.dialect()))
    assert "modelos_fitossanitarios.tenant_id IS NULL" in select_sql

    snapshot_referencias = [entry.regras_risco for entry in session.entries]
    inseridos_2, existentes_2 = await _seed_modelos_fitossanitarios(session)

    assert inseridos_2 == 0
    assert existentes_2 == len(MODELOS_FITOSSANITARIOS_BASE)
    assert len(session.added) == len(MODELOS_FITOSSANITARIOS_BASE)
    assert session.commit_count == 1
    assert [entry.regras_risco for entry in session.entries] == snapshot_referencias


@pytest.mark.asyncio
async def test_seed_modelos_dry_run_nao_altera_sessao():
    session = _SeedSession()

    inseridos, existentes = await _seed_modelos_fitossanitarios(session, dry_run=True)

    assert inseridos == len(MODELOS_FITOSSANITARIOS_BASE)
    assert existentes == 0
    assert session.added == []
    assert session.commit_count == 0


@pytest.mark.asyncio
async def test_seed_modelos_faz_rollback_em_falha_de_commit():
    session = _SeedSession(fail_on_commit=True)

    with pytest.raises(RuntimeError, match="falha simulada no commit"):
        await _seed_modelos_fitossanitarios(session)

    assert session.rollback_count == 1
    assert session.commit_count == 0


@pytest.mark.asyncio
async def test_seed_modelos_registra_orm_antes_de_abrir_sessao(monkeypatch, capsys):
    from core import model_registry
    from scripts.initial_load import seed_modelos_fitossanitarios

    calls = []
    session = _SeedSession()
    execute = session.execute
    commit = session.commit

    async def record_execute(statement, params=None):
        calls.append("execute")
        return await execute(statement, params)

    async def record_commit():
        calls.append("commit")
        await commit()

    session.execute = record_execute
    session.commit = record_commit

    class SessionContext:
        async def __aenter__(self):
            calls.append("session_enter")
            return session

        async def __aexit__(self, *_args):
            calls.append("session_exit")

    monkeypatch.setattr(
        model_registry, "register_models", lambda: calls.append("register_models")
    )
    monkeypatch.setattr(
        "sqlalchemy.orm.configure_mappers",
        lambda: calls.append("configure_mappers"),
    )
    monkeypatch.setattr(seed_modelos_fitossanitarios, "async_session_maker", SessionContext)

    await seed_modelos_fitossanitarios.seed()
    capsys.readouterr()

    assert calls == [
        "register_models",
        "configure_mappers",
        "session_enter",
        "execute",
        "execute",
        "commit",
        "session_exit",
    ]


@pytest.mark.asyncio
async def test_seed_dry_run_informa_que_nada_foi_gravado(monkeypatch, capsys):
    from contextlib import asynccontextmanager

    from core import model_registry
    from scripts.initial_load import seed_modelos_fitossanitarios

    session = _SeedSession()

    @asynccontextmanager
    async def session_ctx():
        yield session

    monkeypatch.setattr(model_registry, "register_models", lambda: None)
    monkeypatch.setattr("sqlalchemy.orm.configure_mappers", lambda: None)
    monkeypatch.setattr(seed_modelos_fitossanitarios, "catalog_admin_async_session_maker", None)
    monkeypatch.setattr(seed_modelos_fitossanitarios, "async_session_maker", session_ctx)

    inseridos, existentes = await seed_modelos_fitossanitarios.seed(dry_run=True)
    stdout = capsys.readouterr().out

    assert inseridos == len(MODELOS_FITOSSANITARIOS_BASE)
    assert existentes == 0
    assert "nada foi gravado" in stdout.lower()
    assert "pendentes" in stdout.lower()
    assert "inseridos" not in stdout.lower()


@pytest.mark.asyncio
async def test_seed_prefere_catalog_admin_session_maker_quando_configurado(monkeypatch, capsys):
    from contextlib import asynccontextmanager

    from core import model_registry
    from scripts.initial_load import seed_modelos_fitossanitarios

    used: list[str] = []
    admin_session = _SeedSession()
    legacy_session = _SeedSession()

    @asynccontextmanager
    async def admin_ctx():
        used.append("catalog_admin")
        yield admin_session

    @asynccontextmanager
    async def legacy_ctx():
        used.append("legacy")
        yield legacy_session

    monkeypatch.setattr(model_registry, "register_models", lambda: None)
    monkeypatch.setattr("sqlalchemy.orm.configure_mappers", lambda: None)
    monkeypatch.setattr(seed_modelos_fitossanitarios, "catalog_admin_async_session_maker", admin_ctx)
    monkeypatch.setattr(seed_modelos_fitossanitarios, "async_session_maker", legacy_ctx)

    await seed_modelos_fitossanitarios.seed()
    capsys.readouterr()

    assert used == ["catalog_admin"]
    assert admin_session.commit_count == 1
    assert legacy_session.commit_count == 0


@pytest.mark.asyncio
async def test_seed_modelos_orienta_migration_quando_rls_bloqueia_insert():
    class _RlsFailSession(_SeedSession):
        async def commit(self):
            raise RuntimeError(
                'new row violates row-level security policy for table "modelos_fitossanitarios"'
            )

    session = _RlsFailSession()

    with pytest.raises(RuntimeError) as exc_info:
        await _seed_modelos_fitossanitarios(session)

    msg = str(exc_info.value)
    assert "alembic upgrade head" in msg
    assert "20261119_rls_global_catalog_admin_write" in msg
    assert session.rollback_count == 1
    assert session.commit_count == 0


@pytest.mark.asyncio
async def test_replace_legacy_globals_bloqueado_em_producao(monkeypatch):
    from core.config import settings
    from scripts.initial_load import seed_modelos_fitossanitarios

    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setattr(settings, "environment", "development")

    session = _SeedSession()
    with pytest.raises(RuntimeError, match="produção"):
        await seed_modelos_fitossanitarios._executar_carga_modelos(
            session, replace_legacy_globals=True
        )

    assert session.statements == []
    assert session.deleted == []
    assert session.added == []
    assert session.commit_count == 0

    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setattr(settings, "environment", "production")
    with pytest.raises(RuntimeError, match="produção"):
        await seed_modelos_fitossanitarios._executar_carga_modelos(
            session, replace_legacy_globals=True
        )


@pytest.mark.asyncio
async def test_replace_legacy_globals_remove_legados_com_flush_antes_de_inserir_e_preserva_modelos_com_metadados(
    monkeypatch,
):
    from core.config import settings
    from scripts.initial_load import seed_modelos_fitossanitarios

    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setattr(settings, "environment", "development")

    session = _SeedSession()
    legado_duplicado = ModeloFitossanitario(
        tenant_id=None,
        is_global=False,
        cultura="Soja",
        doenca="Ferrugem Asiática",
        regras_risco={"condicoes": [{"variavel": "temp_media_c", "operador": ">=", "valor": 20, "peso": 1.0}]},
    )
    legado_sem_acento = ModeloFitossanitario(
        tenant_id=None,
        is_global=False,
        cultura="Algodao",
        doenca="Ramularia",
        regras_risco={"condicoes": [{"variavel": "temp_media_c", "operador": ">=", "valor": 22, "peso": 1.0}]},
    )
    modelo_moderno = ModeloFitossanitario(
        tenant_id=None,
        is_global=True,
        cultura="Milho",
        doenca="Cercosporiose",
        regras_risco={
            "condicoes": [{"variavel": "temp_media_c", "operador": "between", "min": 22.0, "max": 30.0, "peso": 1.0}],
            "nivel_medio_pct": 35,
            "nivel_alto_pct": 60,
            "nivel_critico_pct": 80,
            "metadados": {"fonte_parametros": "Embrapa Milho e Sorgo"},
        },
    )
    session.entries.extend([legado_duplicado, legado_sem_acento, modelo_moderno])

    inseridos, existentes, removidos = await seed_modelos_fitossanitarios._executar_carga_modelos(
        session, replace_legacy_globals=True
    )

    assert removidos == 2
    assert inseridos == 77
    assert existentes == 1
    assert len(session.deleted) == 2
    assert modelo_moderno in session.entries
    assert session.flush_count == 1
    assert session.commit_count == 1
    flush_idx = session.events.index("flush")
    last_delete_idx = max(i for i, e in enumerate(session.events) if e == "delete")
    first_add_idx = session.events.index("add")
    assert last_delete_idx < flush_idx < first_add_idx


@pytest.mark.asyncio
async def test_replace_legacy_globals_dry_run_nao_remove_nem_insere(monkeypatch, capsys):
    from contextlib import asynccontextmanager

    from core import model_registry
    from core.config import settings
    from scripts.initial_load import seed_modelos_fitossanitarios

    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setattr(settings, "environment", "development")

    session = _SeedSession()
    session.entries.append(
        ModeloFitossanitario(
            tenant_id=None,
            is_global=False,
            cultura="Algodao",
            doenca="Ramularia",
            regras_risco={"condicoes": []},
        )
    )

    @asynccontextmanager
    async def session_ctx():
        yield session

    monkeypatch.setattr(model_registry, "register_models", lambda: None)
    monkeypatch.setattr("sqlalchemy.orm.configure_mappers", lambda: None)
    monkeypatch.setattr(seed_modelos_fitossanitarios, "catalog_admin_async_session_maker", None)
    monkeypatch.setattr(seed_modelos_fitossanitarios, "async_session_maker", session_ctx)

    inseridos, existentes = await seed_modelos_fitossanitarios.seed(
        dry_run=True, replace_legacy_globals=True
    )
    stdout = capsys.readouterr().out

    assert inseridos == 78
    assert existentes == 0
    assert session.deleted == []
    assert session.added == []
    assert session.flush_count == 0
    assert session.commit_count == 0
    assert "nada foi gravado" in stdout.lower()
    assert "1 legados a remover" in stdout.lower()
    assert "78 modelos pendentes" in stdout.lower()
