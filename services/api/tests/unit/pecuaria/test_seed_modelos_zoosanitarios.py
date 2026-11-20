from __future__ import annotations

from contextlib import asynccontextmanager
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.dialects import postgresql

from pecuaria.climatico.models import ModeloZoosanitario
from pecuaria.climatico.padroes import PADROES_ESTRESSE_TERMICO
from pecuaria.climatico.schemas import (
    ModeloZoosanitarioCreate,
    ModeloZoosanitarioUpdate,
    validar_regras_zoosanitarias,
)
from pecuaria.climatico.service import (
    InteligenciaPecuariaService,
    ModeloZoosanitarioService,
)
from scripts.initial_load.seed_modelos_zoosanitarios import (
    MODELOS_ZOOSSANITARIOS_BASE,
    _seed_modelos_zoosanitarios,
)


class _ScalarResult:
    def __init__(self, rows: list):
        self._rows = rows

    def all(self) -> list:
        return list(self._rows)

    def first(self):
        return self._rows[0] if self._rows else None

    def scalar_one_or_none(self):
        return self._rows[0] if self._rows else None

    def scalars(self):
        return self


class _SeedSession:
    def __init__(self, *, fail_on_commit_error: Exception | None = None):
        self.entries: list[ModeloZoosanitario] = []
        self.added: list[ModeloZoosanitario] = []
        self.deleted: list[ModeloZoosanitario] = []
        self.statements: list = []
        self.events: list[str] = []
        self.flush_count = 0
        self.commit_count = 0
        self.rollback_count = 0
        self.refresh_count = 0
        self.fail_on_commit_error = fail_on_commit_error

    async def execute(self, statement, _params=None):
        self.statements.append(statement)
        sql_text = str(statement)
        if "set_config" in sql_text:
            return _ScalarResult([])

        col_descs = getattr(statement, "column_descriptions", None) or []
        if len(col_descs) == 1 and col_descs[0].get("entity") is ModeloZoosanitario:
            return _ScalarResult(self._filtrar_entries(statement, sql_text))

        return _ScalarResult([
            (entry.especie, entry.tipo_risco)
            for entry in self.entries
            if getattr(entry, "tenant_id", None) is None
        ])

    def _filtrar_entries(self, statement, sql_text: str) -> list[ModeloZoosanitario]:
        params = dict(statement.compile().params)
        resultados = list(self.entries)
        if "tenant_id IS NULL" in sql_text and "tenant_id =" not in sql_text:
            resultados = [e for e in resultados if getattr(e, "tenant_id", None) is None]
        elif "tenant_id =" in sql_text and "tenant_id IS NULL" not in sql_text:
            resultados = [e for e in resultados if getattr(e, "tenant_id", None) == params.get("tenant_id_1")]

        for chave, valor in params.items():
            if chave.startswith("id_"):
                resultados = [e for e in resultados if getattr(e, "id", None) == valor]
            elif chave.startswith("especie_"):
                resultados = [e for e in resultados if getattr(e, "especie", None) == valor]
            elif chave.startswith("tipo_risco_"):
                resultados = [e for e in resultados if getattr(e, "tipo_risco", None) == valor]
        return resultados

    def add(self, entry) -> None:
        self.events.append("add")
        if getattr(entry, "id", None) is None:
            entry.id = uuid4()
        self.added.append(entry)
        self.entries.append(entry)

    async def delete(self, entry) -> None:
        self.events.append("delete")
        if entry in self.entries:
            self.entries.remove(entry)
        self.deleted.append(entry)

    async def flush(self) -> None:
        self.events.append("flush")
        self.flush_count += 1

    async def commit(self) -> None:
        self.events.append("commit")
        if self.fail_on_commit_error is not None:
            raise self.fail_on_commit_error
        self.commit_count += 1

    async def rollback(self) -> None:
        self.events.append("rollback")
        self.rollback_count += 1

    async def refresh(self, _entry) -> None:
        self.events.append("refresh")
        self.refresh_count += 1


def _regras_validas(**overrides) -> dict:
    base = {
        "nivel_medio": 72,
        "nivel_alto": 78,
        "nivel_critico": 82,
        "indice": "ITH_CLÁSSICO",
        "fonte_parametros": "Embrapa Gado de Leite",
        "fonte_url": "https://www.embrapa.br/gado-de-leite",
        "observacao": "Referência preventiva para bovinos leiteiros.",
        "metadados": {
            "tipo_resultado": "referencia_conforto_termico_ith",
            "somente_referencia": True,
            "fonte_parametros": "Embrapa Gado de Leite",
            "fonte_url": "https://www.embrapa.br/gado-de-leite",
            "versao_regra": "2026.11-embrapa-zoo-v1",
            "observacao": "Referência preventiva para bovinos leiteiros.",
        },
    }
    base.update(overrides)
    return base


def test_modelos_zoosanitarios_base_respeitam_padroes_e_schema() -> None:
    assert len(MODELOS_ZOOSSANITARIOS_BASE) == 10
    especies = {item["especie"] for item in MODELOS_ZOOSSANITARIOS_BASE}
    assert especies == set(PADROES_ESTRESSE_TERMICO.keys())

    chaves: set[tuple[str, str]] = set()
    for item in MODELOS_ZOOSSANITARIOS_BASE:
        chave = (item["especie"], item["tipo_risco"])
        assert chave not in chaves
        chaves.add(chave)
        assert item["tipo_risco"] == "Estresse Térmico"

        regras = validar_regras_zoosanitarias(item["regras_risco"])
        assert regras["indice"] == "ITH_CLÁSSICO"
        assert regras["fonte_parametros"]
        assert regras["fonte_url"].startswith("https://")
        assert regras["observacao"]

        metadados = regras["metadados"]
        assert metadados["tipo_resultado"] == "referencia_conforto_termico_ith"
        assert metadados["somente_referencia"] is True
        assert metadados["fonte_parametros"] == regras["fonte_parametros"]
        assert metadados["fonte_url"] == regras["fonte_url"]
        assert metadados["versao_regra"]
        assert metadados["observacao"] == regras["observacao"]


def test_validar_regras_zoosanitarias_bloqueia_urls_e_limiares_invalidos() -> None:
    validar_regras_zoosanitarias(_regras_validas())

    with pytest.raises(ValueError, match="http"):
        validar_regras_zoosanitarias(_regras_validas(fonte_url="javascript:alert(1)"))

    with pytest.raises(ValueError, match="http"):
        validar_regras_zoosanitarias(
            _regras_validas(
                metadados={
                    "fonte_url": "javascript:alert(1)",
                    "fonte_parametros": "Embrapa",
                }
            )
        )

    with pytest.raises(ValueError):
        validar_regras_zoosanitarias(_regras_validas(nivel_medio=78, nivel_alto=78))

    with pytest.raises(ValueError):
        validar_regras_zoosanitarias(_regras_validas(nivel_alto=85, nivel_critico=82))

    with pytest.raises(ValueError):
        validar_regras_zoosanitarias(_regras_validas(nivel_medio=0))

    with pytest.raises(ValueError):
        validar_regras_zoosanitarias(_regras_validas(nivel_critico=101))

    with pytest.raises(ValidationError):
        ModeloZoosanitarioCreate(
            especie="Bovino de Leite",
            tipo_risco="Estresse Térmico",
            regras_risco=_regras_validas(fonte_url="ftp://invalido.test"),
        )

    with pytest.raises(ValidationError):
        ModeloZoosanitarioUpdate(
            regras_risco=_regras_validas(nivel_medio=80, nivel_alto=78, nivel_critico=82)
        )


@pytest.mark.asyncio
async def test_seed_modelos_zoosanitarios_idempotente_e_usa_tenant_null() -> None:
    session = _SeedSession()

    inseridos, existentes = await _seed_modelos_zoosanitarios(session)
    assert inseridos == 10
    assert existentes == 0
    assert session.commit_count == 1
    assert len(session.entries) == 10
    assert all(e.tenant_id is None and e.is_global is True for e in session.entries)

    sql_statements = [
        str(stmt.compile(dialect=postgresql.dialect()))
        for stmt in session.statements
        if "modelos_zoosanitarios" in str(stmt)
    ]
    assert sql_statements
    assert all("tenant_id IS NULL" in sql for sql in sql_statements)

    inseridos_2, existentes_2 = await _seed_modelos_zoosanitarios(session)
    assert inseridos_2 == 0
    assert existentes_2 == 10
    assert len(session.entries) == 10


@pytest.mark.asyncio
async def test_seed_dry_run_nao_persiste_e_imprime_pendentes(monkeypatch, capsys) -> None:
    from core import model_registry
    from scripts.initial_load import seed_modelos_zoosanitarios

    session = _SeedSession()

    @asynccontextmanager
    async def session_ctx():
        yield session

    monkeypatch.setattr(model_registry, "register_models", lambda: None)
    monkeypatch.setattr("sqlalchemy.orm.configure_mappers", lambda: None)
    monkeypatch.setattr(seed_modelos_zoosanitarios, "catalog_admin_async_session_maker", None)
    monkeypatch.setattr(seed_modelos_zoosanitarios, "async_session_maker", session_ctx)

    inseridos, existentes = await seed_modelos_zoosanitarios.seed(dry_run=True)
    stdout = capsys.readouterr().out

    assert inseridos == 10
    assert existentes == 0
    assert session.commit_count == 0
    assert session.added == []
    assert "nada foi gravado" in stdout.lower()
    assert "pendentes" in stdout.lower()
    assert "inseridos" not in stdout.lower()


@pytest.mark.asyncio
async def test_seed_prefere_catalog_admin_session_maker_quando_configurado(monkeypatch, capsys) -> None:
    from core import model_registry
    from scripts.initial_load import seed_modelos_zoosanitarios

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
    monkeypatch.setattr(seed_modelos_zoosanitarios, "catalog_admin_async_session_maker", admin_ctx)
    monkeypatch.setattr(seed_modelos_zoosanitarios, "async_session_maker", legacy_ctx)

    await seed_modelos_zoosanitarios.seed()
    capsys.readouterr()

    assert used == ["catalog_admin"]
    assert admin_session.commit_count == 1
    assert legacy_session.commit_count == 0


@pytest.mark.asyncio
async def test_seed_orienta_migration_quando_rls_bloqueia_insert() -> None:
    session = _SeedSession(
        fail_on_commit_error=RuntimeError(
            'new row violates row-level security policy for table "modelos_zoosanitarios"'
        )
    )

    with pytest.raises(RuntimeError) as exc_info:
        await _seed_modelos_zoosanitarios(session)

    msg = str(exc_info.value)
    assert "alembic upgrade head" in msg
    assert "20261119_rls_global_catalog_admin_write" in msg
    assert session.rollback_count == 1
    assert session.commit_count == 0


@pytest.mark.asyncio
async def test_replace_legacy_globals_bloqueado_em_producao(monkeypatch) -> None:
    from core.config import settings
    from scripts.initial_load import seed_modelos_zoosanitarios

    session = _SeedSession()

    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setattr(settings, "environment", "development")
    with pytest.raises(RuntimeError, match="produção"):
        await seed_modelos_zoosanitarios._executar_carga_modelos(
            session, replace_legacy_globals=True
        )

    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setattr(settings, "environment", "production")
    with pytest.raises(RuntimeError, match="produção"):
        await seed_modelos_zoosanitarios._executar_carga_modelos(
            session, replace_legacy_globals=True
        )

    assert session.statements == []
    assert session.deleted == []
    assert session.added == []


@pytest.mark.asyncio
async def test_replace_legacy_globals_remove_legados_com_flush_antes_e_preserva_com_metadados(
    monkeypatch,
) -> None:
    from core.config import settings
    from scripts.initial_load import seed_modelos_zoosanitarios

    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setattr(settings, "environment", "development")

    session = _SeedSession()
    legado_sem_fonte = ModeloZoosanitario(
        tenant_id=None,
        is_global=True,
        especie="Bovino de Leite",
        tipo_risco="Estresse Térmico",
        regras_risco={"nivel_medio": 72, "nivel_alto": 78, "nivel_critico": 82},
    )
    legado_sem_metadados = ModeloZoosanitario(
        tenant_id=None,
        is_global=True,
        especie="Suíno",
        tipo_risco="Estresse Térmico",
        regras_risco={
            "nivel_medio": 68,
            "nivel_alto": 74,
            "nivel_critico": 78,
            "fonte_parametros": "Legado raiz sem bloco metadados",
            "fonte_url": "https://extension.umn.edu/example",
        },
    )
    moderno_ovino = ModeloZoosanitario(
        tenant_id=None,
        is_global=True,
        especie="Ovino",
        tipo_risco="Estresse Térmico",
        regras_risco=_regras_validas(
            nivel_medio=74,
            nivel_alto=79,
            nivel_critico=84,
        ),
    )
    session.entries.extend([legado_sem_fonte, legado_sem_metadados, moderno_ovino])

    inseridos, existentes, removidos = await seed_modelos_zoosanitarios._executar_carga_modelos(
        session, replace_legacy_globals=True
    )

    assert removidos == 2
    assert inseridos == 9
    assert existentes == 1
    assert moderno_ovino in session.entries
    assert session.flush_count == 1
    assert session.commit_count == 1
    flush_idx = session.events.index("flush")
    last_delete_idx = max(i for i, e in enumerate(session.events) if e == "delete")
    first_add_idx = session.events.index("add")
    assert last_delete_idx < flush_idx < first_add_idx


@pytest.mark.asyncio
async def test_replace_legacy_globals_dry_run_nao_remove_nem_insere(monkeypatch, capsys) -> None:
    from core import model_registry
    from core.config import settings
    from scripts.initial_load import seed_modelos_zoosanitarios

    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setattr(settings, "environment", "development")

    session = _SeedSession()
    session.entries.append(
        ModeloZoosanitario(
            tenant_id=None,
            is_global=True,
            especie="Suíno",
            tipo_risco="Estresse Térmico",
            regras_risco={"nivel_medio": 68, "nivel_alto": 74, "nivel_critico": 78},
        )
    )

    @asynccontextmanager
    async def session_ctx():
        yield session

    monkeypatch.setattr(model_registry, "register_models", lambda: None)
    monkeypatch.setattr("sqlalchemy.orm.configure_mappers", lambda: None)
    monkeypatch.setattr(seed_modelos_zoosanitarios, "catalog_admin_async_session_maker", None)
    monkeypatch.setattr(seed_modelos_zoosanitarios, "async_session_maker", session_ctx)

    inseridos, existentes = await seed_modelos_zoosanitarios.seed(
        dry_run=True, replace_legacy_globals=True
    )
    stdout = capsys.readouterr().out

    assert inseridos == 10
    assert existentes == 0
    assert session.deleted == []
    assert session.added == []
    assert session.flush_count == 0
    assert session.commit_count == 0
    assert "nada foi gravado" in stdout.lower()
    assert "1 legados a remover" in stdout.lower()
    assert "10 modelos pendentes" in stdout.lower()


@pytest.mark.asyncio
async def test_analisar_estresse_termico_nao_copia_modelo_global_automaticamente() -> None:
    tenant_id = uuid4()
    unidade_id = uuid4()
    session = _SeedSession()
    session.entries.append(
        ModeloZoosanitario(
            id=uuid4(),
            tenant_id=None,
            is_global=True,
            especie="Equino",
            tipo_risco="Estresse Térmico",
            regras_risco=_regras_validas(),
        )
    )

    inteligencia_svc = InteligenciaPecuariaService(session)
    resultado = await inteligencia_svc.analisar_estresse_termico(
        tenant_id, unidade_id, "Equino"
    )

    assert resultado is None
    assert session.added == []
    assert session.flush_count == 0
    assert session.commit_count == 0


@pytest.mark.asyncio
async def test_copy_global_to_tenant_persiste_com_deepcopy_e_commit() -> None:
    tenant_id = uuid4()
    global_id = uuid4()
    session = _SeedSession()
    regras_originais = _regras_validas()
    global_modelo = ModeloZoosanitario(
        id=global_id,
        tenant_id=None,
        is_global=True,
        especie="Equino",
        tipo_risco="Estresse Térmico",
        regras_risco=regras_originais,
    )
    session.entries.append(global_modelo)

    service = ModeloZoosanitarioService(session)
    copia = await service.copy_global_to_tenant(tenant_id, global_id)

    assert copia.tenant_id == tenant_id
    assert copia.is_global is False
    assert session.commit_count == 1
    assert session.refresh_count == 1
    copia.regras_risco["metadados"]["versao_regra"] = "alterada-no-tenant"
    assert global_modelo.regras_risco["metadados"]["versao_regra"] == "2026.11-embrapa-zoo-v1"

    global_modelo.regras_risco["nivel_critico"] = 84
    copia_atualizada = await service.copy_global_to_tenant(tenant_id, global_id)
    assert copia_atualizada is copia
    assert copia_atualizada.regras_risco["nivel_critico"] == 84
    assert session.commit_count == 2
    assert len([e for e in session.entries if e.tenant_id == tenant_id]) == 1

    global_invalido_id = uuid4()
    session.entries.append(
        ModeloZoosanitario(
            id=global_invalido_id,
            tenant_id=None,
            is_global=True,
            especie="Asinino",
            tipo_risco="Estresse Térmico",
            regras_risco={"nivel_medio": 90, "nivel_alto": 80, "nivel_critico": 70},
        )
    )
    with pytest.raises(HTTPException) as exc_info:
        await service.copy_global_to_tenant(tenant_id, global_invalido_id)
    assert exc_info.value.status_code == 422


@pytest.mark.asyncio
async def test_get_all_models_deduplica_priorizando_tenant_sobre_global() -> None:
    tenant_id = uuid4()
    session = _SeedSession()
    global_equino = ModeloZoosanitario(
        id=uuid4(),
        tenant_id=None,
        is_global=True,
        especie="Equino",
        tipo_risco="Estresse Térmico",
        regras_risco=_regras_validas(nivel_medio=71, nivel_alto=77, nivel_critico=82),
    )
    tenant_equino = ModeloZoosanitario(
        id=uuid4(),
        tenant_id=tenant_id,
        is_global=False,
        especie="Equino",
        tipo_risco="Estresse Térmico",
        regras_risco=_regras_validas(nivel_medio=70, nivel_alto=75, nivel_critico=80),
    )
    global_bovino = ModeloZoosanitario(
        id=uuid4(),
        tenant_id=None,
        is_global=True,
        especie="Bovino de Leite",
        tipo_risco="Estresse Térmico",
        regras_risco=_regras_validas(),
    )
    session.entries.extend([global_equino, tenant_equino, global_bovino])

    service = ModeloZoosanitarioService(session)
    modelos = await service.get_all_models(tenant_id)

    assert len(modelos) == 2
    por_especie = {m.especie: m for m in modelos}
    assert por_especie["Equino"] is tenant_equino
    assert por_especie["Equino"].is_global is False
    assert por_especie["Bovino de Leite"] is global_bovino
    assert por_especie["Bovino de Leite"].is_global is True
