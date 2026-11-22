"""Testes offline de segurança, guardrails, coletores Nível 1 e integração Fase 1A."""

from __future__ import annotations

import importlib.util
import socket
import sys
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs

import httpx
import pytest
import sqlalchemy as sa
from alembic.operations import Operations
from alembic.runtime.migration import MigrationContext
from sqlalchemy import JSON, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agro_collector.collectors import (  # noqa: E402
    CollectorContext,
    DeralPrCollector,
    IeaSpCollector,
)
from agro_collector.collectors.iea_sp import (  # noqa: E402
    extract_iea_form_metadata,
    parse_iea_result_html,
)
from agro_collector.contracts import RawObservation  # noqa: E402
from agro_collector.fetcher import (  # noqa: E402
    PayloadTooLargeError,
    SafeHttpFetcher,
    UnsafeSourceUrlError,
    compress_artifact,
    compute_sha256,
    decompress_artifact,
    validate_source_url,
)
from agro_collector.guardrails import (  # noqa: E402
    normalize_unit_value,
    validate_observation,
    verify_literal_evidence,
)
from agro_collector.models import (  # noqa: E402
    AgroCollectorBase,
    AgroDataSource,
    AgroIngestionArtifact,
    AgroStagingObservation,
)
from agro_collector.orchestrator import AgroCollectorOrchestrator  # noqa: E402
from agro_collector.repository import purge_expired_artifacts  # noqa: E402
from agro_collector.seed_sources import ensure_default_sources  # noqa: E402
from core.cadastros.commodities.cotacao_regional_service import (  # noqa: E402
    CotacaoRegionalService,
)
from core.database import Base  # noqa: E402
from core.exceptions import EntityNotFoundError  # noqa: E402
from core.models import (  # noqa: E402
    ConfiguracaoFazenda,
    ConfiguracaoTenant,
    Tenant,
    UnidadeProdutiva,
)
from core.models.configuration import ConfiguracaoSaaS  # noqa: E402
from public_mercado.cotacoes_regiao_service import CotacaoMultiFonteService  # noqa: E402

FIXTURES_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "agro_collector"
DERAL_XLS_PATH = FIXTURES_ROOT / "deral_pr" / "prp.xls"
IEA_FORM_HTML_PATH = FIXTURES_ROOT / "iea_sp" / "precos_diarios_recebidos.html"
IEA_SAMPLE_HTML_PATH = FIXTURES_ROOT / "iea_sp" / "precos_diarios_resultado_amostra.html"


@pytest.fixture
async def collector_db_factory():
    """Cria engine SQLite async em memória com tabelas necessárias para o coletor e ERP."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    core_tables = [
        Tenant.__table__,
        UnidadeProdutiva.__table__,
        ConfiguracaoSaaS.__table__,
        ConfiguracaoTenant.__table__,
        ConfiguracaoFazenda.__table__,
    ]

    @compiles(JSONB, "sqlite")
    def _compile_jsonb_sqlite(_type, _compiler, **_kw):  # pragma: no cover
        return JSON().compile(dialect=_compiler.dialect)

    def _create_all_tables(sync_conn) -> None:
        Base.metadata.create_all(sync_conn, tables=core_tables)
        AgroCollectorBase.metadata.create_all(sync_conn)

    async with engine.begin() as conn:
        await conn.run_sync(_create_all_tables)

    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    try:
        yield factory
    finally:
        await engine.dispose()


# ---------------------------------------------------------------------------
# 1. Segurança anti-SSRF, redirects, teto de payload e gzip
# ---------------------------------------------------------------------------


def test_validate_source_url_blocks_ssrf_and_insecure_schemes() -> None:
    whitelist = ["agricultura.pr.gov.br", "infoiea.agricultura.sp.gov.br"]

    with pytest.raises(UnsafeSourceUrlError):
        validate_source_url(
            "http://www.agricultura.pr.gov.br/deral/precos",
            whitelist,
            resolve_dns=False,
        )
    with pytest.raises(UnsafeSourceUrlError):
        validate_source_url(
            "https://user:pass@www.agricultura.pr.gov.br/deral",
            whitelist,
            resolve_dns=False,
        )
    with pytest.raises(UnsafeSourceUrlError):
        validate_source_url("https://127.0.0.1/internal", whitelist, resolve_dns=False)
    with pytest.raises(UnsafeSourceUrlError):
        validate_source_url(
            "https://169.254.169.254/latest/meta-data",
            whitelist,
            resolve_dns=False,
        )
    with pytest.raises(UnsafeSourceUrlError):
        validate_source_url("https://[::1]/secret", whitelist, resolve_dns=False)
    with pytest.raises(UnsafeSourceUrlError):
        validate_source_url(
            "https://agricultura.pr.gov.br.evil.com/prp.xls",
            whitelist,
            resolve_dns=False,
        )

    private_addrinfo = [
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.42", 443))
    ]
    with patch("agro_collector.fetcher.socket.getaddrinfo", return_value=private_addrinfo):
        with pytest.raises(UnsafeSourceUrlError, match="anti-SSRF"):
            validate_source_url(
                "https://www.agricultura.pr.gov.br/prp.xls",
                whitelist,
                resolve_dns=True,
            )

    public_addrinfo = [
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("200.189.113.10", 443))
    ]
    with patch("agro_collector.fetcher.socket.getaddrinfo", return_value=public_addrinfo):
        ok = validate_source_url(
            "https://www.agricultura.pr.gov.br/deral/precos",
            whitelist,
            resolve_dns=True,
        )
    assert ok == "https://www.agricultura.pr.gov.br/deral/precos"


@pytest.mark.asyncio
async def test_safe_http_fetcher_blocks_redirect_escape_and_payload_limit() -> None:
    def _handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/redirect-evil":
            return httpx.Response(302, headers={"Location": "https://evil.example.com/steal"})
        if request.url.path == "/huge":
            return httpx.Response(200, content=b"x" * 2048)
        if request.url.path == "/cached":
            if request.headers.get("If-None-Match") == '"etag-1"':
                return httpx.Response(304, headers={"ETag": '"etag-1"'})
            return httpx.Response(200, content=b"ok", headers={"ETag": '"etag-1"'})
        return httpx.Response(404)

    transport = httpx.MockTransport(_handler)
    fetcher = SafeHttpFetcher(
        max_bytes=512,
        resolve_dns=False,
        client_factory=lambda: httpx.AsyncClient(transport=transport, follow_redirects=False),
    )

    with pytest.raises(UnsafeSourceUrlError, match="whitelist"):
        await fetcher.fetch(
            "https://www.agricultura.pr.gov.br/redirect-evil",
            ["agricultura.pr.gov.br"],
        )

    with pytest.raises(PayloadTooLargeError):
        await fetcher.fetch(
            "https://www.agricultura.pr.gov.br/huge",
            ["agricultura.pr.gov.br"],
        )

    res_200 = await fetcher.fetch(
        "https://www.agricultura.pr.gov.br/cached",
        ["agricultura.pr.gov.br"],
    )
    assert res_200.http_status == 200
    assert res_200.not_modified is False
    assert res_200.sha256 == compute_sha256(b"ok")

    res_304 = await fetcher.fetch(
        "https://www.agricultura.pr.gov.br/cached",
        ["agricultura.pr.gov.br"],
        etag='"etag-1"',
    )
    assert res_304.http_status == 304
    assert res_304.not_modified is True

    gz = compress_artifact(b"conteudo original agropecuaria")
    assert decompress_artifact(gz) == b"conteudo original agropecuaria"


# ---------------------------------------------------------------------------
# 2. Guardrails matemáticos, evidência literal e quarentena
# ---------------------------------------------------------------------------


def test_guardrails_unit_normalization_evidence_and_outlier_quarantine() -> None:
    val_sc, factor, desc = normalize_unit_value(
        Decimal("2.25"),
        "Quilograma (kg)",
        "Saca de 60 kg",
    )
    assert val_sc == Decimal("135.00")
    assert factor == Decimal("60.000000")
    assert desc is not None and "HALF_UP" in desc

    val_kg, _, _ = normalize_unit_value(Decimal("395.00"), "@", "Quilograma (kg)")
    assert val_kg == Decimal("26.33")  # 395 / 15 = 26.3333... -> 26.33

    raw_sample = (
        "<table><tr><td>Soja</td><td>Assis</td><td>18/11/2026</td>"
        "<td>137,50</td><td>sc.60 kg</td></tr></table>"
    )
    assert verify_literal_evidence(
        "Soja Assis 18/11/2026 137,50 sc.60 kg",
        raw_sample.replace("<td>", " ").replace("</td>", " "),
    )

    obs_outlier = RawObservation(
        commodity_id="soja",
        uf="SP",
        praca="EDR Assis",
        tipo_preco="PRECO_MEDIO_RECEBIDO_PRODUTOR",
        periodicidade="DIARIA",
        data_referencia=date(2026, 11, 18),
        valor_original=Decimal("180.00"),
        unidade_original="sc.60 kg",
        unidade_destino="Saca de 60 kg",
        trecho_evidencia="Soja Assis 18/11/2026 180,00 sc.60 kg",
    )
    validated = validate_observation(
        obs_outlier,
        previous_valor=Decimal("137.50"),
        max_variacao_pct=Decimal("12.00"),
        max_defasagem_dias=7,
        today=date(2026, 11, 19),
        raw_text="tabela com Soja Assis 18/11/2026 180,00 sc.60 kg e fim",
    )
    assert validated.bloqueado_para_publicacao is True
    assert "FLAG_OUTLIER" in validated.flags_anomalia
    assert "FLAG_EVIDENCIA_NAO_CONFERE" not in validated.flags_anomalia

    obs_bad_evidence = obs_outlier.model_copy(
        update={"valor_original": Decimal("140.00"), "trecho_evidencia": "valor inventado 999"}
    )
    val_bad_ev = validate_observation(
        obs_bad_evidence,
        previous_valor=Decimal("137.50"),
        max_variacao_pct=Decimal("12.00"),
        max_defasagem_dias=7,
        today=date(2026, 11, 19),
        raw_text="Soja Assis 18/11/2026 140,00 sc.60 kg",
    )
    assert "FLAG_EVIDENCIA_NAO_CONFERE" in val_bad_ev.flags_anomalia
    assert val_bad_ev.bloqueado_para_publicacao is True

    obs_invalid = obs_outlier.model_copy(
        update={"commodity_id": "cripto-fake", "uf": "XX", "valor_original": Decimal("-10")}
    )
    val_invalid = validate_observation(
        obs_invalid,
        previous_valor=None,
        max_variacao_pct=Decimal("12.00"),
        max_defasagem_dias=7,
        today=date(2026, 11, 19),
    )
    assert {
        "FLAG_COMMODITY_INVALIDA",
        "FLAG_UF_INVALIDA",
        "FLAG_VALOR_INVALIDO",
    }.issubset(set(val_invalid.flags_anomalia))


# ---------------------------------------------------------------------------
# 3. Coletores offline reais com fixtures (DERAL-PR & IEA-SP)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_deral_pr_collector_with_real_xls_fixture() -> None:
    xls_bytes = DERAL_XLS_PATH.read_bytes()

    def _handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=xls_bytes, headers={"ETag": '"prp-v1"'})

    transport = httpx.MockTransport(_handler)
    fetcher = SafeHttpFetcher(
        resolve_dns=False,
        client_factory=lambda: httpx.AsyncClient(transport=transport, follow_redirects=False),
    )
    src = AgroDataSource(
        id=uuid.uuid4(),
        slug="deral_pr",
        nome="DERAL/SEAB-PR",
        sigla="DERAL/SEAB-PR",
        tipo_licenca="DADO_PUBLICO_GOV",
        uf_padrao="PR",
        dominios_whitelist=["agricultura.pr.gov.br"],
        url_principal=(
            "https://www.agricultura.pr.gov.br/sites/default/arquivos_restritos/"
            "files/documento/2026-10/prp.xls"
        ),
        estrategia_coleta="NIVEL1_DETERMINISTICO",
        config_extrator={},
    )
    payload = await DeralPrCollector().collect(CollectorContext(source=src, fetcher=fetcher))
    medias = [o for o in payload.observations if o.is_media_estadual]
    nucleos = [o for o in payload.observations if not o.is_media_estadual]
    assert len(medias) == 21
    assert len(nucleos) >= 100
    soja = next(o for o in medias if o.commodity_id == "soja")
    assert soja.uf == "PR"
    assert soja.valor_original > 0


@pytest.mark.asyncio
async def test_iea_sp_collector_antiforgery_and_holiday_fallback() -> None:
    form_html = IEA_FORM_HTML_PATH.read_bytes()
    sample_html = IEA_SAMPLE_HTML_PATH.read_bytes()

    meta = extract_iea_form_metadata(form_html.decode("utf-8"))
    assert meta.verification_token.startswith("CfDJ8")
    assert meta.initial_date == date(2026, 11, 19)
    assert "01" in meta.edr_codes and "41" in meta.edr_codes

    parsed_edrs, raw_txt, total_recs, _ = parse_iea_result_html(
        sample_html.decode("utf-8"),
        "https://infoiea.agricultura.sp.gov.br/BancoDeDados/PrecosDiarios/Recebidos",
    )
    assert total_recs == 14
    assert len(parsed_edrs) == 14
    assert "Soja Assis 18/11/2026 137,50 sc.60 kg" in raw_txt

    requested_dates: list[str] = []

    def _handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            return httpx.Response(
                200,
                content=form_html,
                headers={"Set-Cookie": ".AspNetCore.Antiforgery=cookie123; path=/"},
            )
        body_qs = parse_qs(request.content.decode("utf-8"))
        assert body_qs.get("__RequestVerificationToken", [""])[0] == meta.verification_token
        dt_str = body_qs["startDate"][0]
        requested_dates.append(dt_str)
        if dt_str == "19/11/2026":
            msg = "<div>N&#xE3;o h&#xE1; pre&#xE7;os no per&#xED;odo informado.</div>"
            return httpx.Response(200, content=msg.encode())
        return httpx.Response(200, content=sample_html)

    transport = httpx.MockTransport(_handler)
    fetcher = SafeHttpFetcher(
        resolve_dns=False,
        client_factory=lambda: httpx.AsyncClient(transport=transport, follow_redirects=False),
    )
    src = AgroDataSource(
        id=uuid.uuid4(),
        slug="iea_sp",
        nome="IEA/SAA-SP",
        sigla="IEA/SAA-SP",
        tipo_licenca="DADO_PUBLICO_GOV",
        uf_padrao="SP",
        dominios_whitelist=["infoiea.agricultura.sp.gov.br"],
        url_principal="https://infoiea.agricultura.sp.gov.br/BancoDeDados/PrecosDiarios/Recebidos",
        estrategia_coleta="NIVEL1_DETERMINISTICO",
        config_extrator={},
    )
    payload = await IeaSpCollector().collect(CollectorContext(source=src, fetcher=fetcher))
    assert requested_dates == ["19/11/2026", "18/11/2026"]

    medias_sp = [o for o in payload.observations if o.is_media_estadual]
    media_soja = next(o for o in medias_sp if o.commodity_id == "soja")
    # (137.50 + 128.00 + 143.00) / 3 = 136.1666... -> 136.17
    assert media_soja.valor_original == Decimal("136.17")
    assert verify_literal_evidence(media_soja.trecho_evidencia, payload.raw_text_for_evidence or "")


# ---------------------------------------------------------------------------
# 4. Orquestrador end-to-end, deduplicação SHA-256, quarentena e expurgo
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_orchestrator_e2e_dedup_quarantine_retention_and_consumers(
    collector_db_factory,
) -> None:
    form_html = IEA_FORM_HTML_PATH.read_bytes()
    sample_html = IEA_SAMPLE_HTML_PATH.read_bytes()

    async def _seed_and_setup():
        async with collector_db_factory() as s:
            await ensure_default_sources(s)
            # Ajusta janela para não marcar FLAG_DEFASADO no fixture 2026-11-18
            iea = (
                await s.execute(select(AgroDataSource).where(AgroDataSource.slug == "iea_sp"))
            ).scalar_one()
            iea.max_defasagem_dias = 3650
            await s.commit()

    await _seed_and_setup()

    current_sample = {"html": sample_html}

    def _handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            return httpx.Response(200, content=form_html)
        return httpx.Response(200, content=current_sample["html"])

    transport = httpx.MockTransport(_handler)
    fetcher = SafeHttpFetcher(
        resolve_dns=False,
        client_factory=lambda: httpx.AsyncClient(transport=transport, follow_redirects=False),
    )
    orchestrator = AgroCollectorOrchestrator(collector_db_factory, fetcher=fetcher)

    # Compliance: LINK_HOMOLOGADO_APENAS não pode ser coletada
    with pytest.raises(ValueError, match="LINK_HOMOLOGADO_APENAS"):
        await orchestrator.run_source_by_slug("conab_nacional")

    # Execução 1: publica 14 EDRs + 4 médias estaduais = 18 observações
    sum1 = await orchestrator.run_source_by_slug(
        "iea_sp", trigger_tipo="MANUAL", executado_por="pytest"
    )
    assert sum1.status == "SUCESSO"
    assert sum1.total_extraidos == 18
    assert sum1.total_publicados == 18

    # Execução 2 com exatamente o mesmo conteúdo: SKIPPED_UNCHANGED
    sum2 = await orchestrator.run_source_by_slug("iea_sp", trigger_tipo="AGENDADO")
    assert sum2.status == "SKIPPED_UNCHANGED"
    assert sum2.skipped_unchanged is True

    # Verifica artefato comprimido em gzip com retenção de 12 meses
    async with collector_db_factory() as s:
        art = (await s.execute(select(AgroIngestionArtifact))).scalar_one()
        assert art.compressao == "gzip"
        assert art.conteudo_comprimido is not None
        assert decompress_artifact(art.conteudo_comprimido) == sample_html

        # Simula expiração após +12 meses
        purged = await purge_expired_artifacts(
            s, now=datetime.now(timezone.utc) + timedelta(days=400)  # noqa: UP017
        )
        assert purged == 1
        await s.commit()
        await s.refresh(art)
        assert art.conteudo_comprimido is None
        assert art.expurgado_em is not None
        assert art.sha256 == compute_sha256(sample_html)

    # Execução 3 com spike outlier (+45% em Boi gordo Andradina): quarentena parcial
    spike_html = sample_html.replace(b"395,00", b"580,00", 1).replace(b"18/11/2026", b"19/11/2026")
    current_sample["html"] = spike_html
    sum3 = await orchestrator.run_source_by_slug("iea_sp", trigger_tipo="MANUAL")
    assert sum3.status == "PARCIAL"
    assert sum3.total_quarentena >= 1
    assert sum3.total_publicados >= 10

    async with collector_db_factory() as s:
        pendentes = (
            await s.execute(
                select(AgroStagingObservation).where(
                    AgroStagingObservation.status_revisao == "PENDENTE_REVISAO"
                )
            )
        ).scalars().all()
        assert any("FLAG_OUTLIER" in p.flags_anomalia for p in pendentes)

        # Consumidor Público (uf=SP): IEA/SAA-SP vence IBGE/DERAL e inclui algodão se houver
        multi_svc = CotacaoMultiFonteService(session=s)
        sp_soja = await multi_svc.consultar(produto="soja", uf="SP", incluir_ibge=False)
        assert len(sp_soja.itens) == 1
        item_soja = sp_soja.itens[0]
        assert item_soja.fontes[0].sigla_fonte == "IEA/SAA-SP"
        assert item_soja.resumo.fonte_recomendada_regiao is not None
        assert "IEA/SAA-SP" in item_soja.resumo.fonte_recomendada_regiao

        # Consumidor ERP Multi-Tenant: Fazenda em SP herda IEA/SAA-SP antes do DERAL
        tenant_sp = Tenant(id=uuid.uuid4(), nome="Grupo Paulista", documento="11222333000181")
        tenant_outro = Tenant(id=uuid.uuid4(), nome="Grupo Outro", documento="99888777000100")
        s.add_all([tenant_sp, tenant_outro])
        fazenda_sp = UnidadeProdutiva(
            id=uuid.uuid4(),
            tenant_id=tenant_sp.id,
            nome="Fazenda Ribeirão",
            municipio="Ribeirão Preto",
            uf="SP",
        )
        fazenda_mt = UnidadeProdutiva(
            id=uuid.uuid4(),
            tenant_id=tenant_sp.id,
            nome="Fazenda Sorriso",
            municipio="Sorriso",
            uf="MT",
        )
        s.add_all([fazenda_sp, fazenda_mt])
        await s.commit()

        svc_sp = CotacaoRegionalService(s, tenant_sp.id)
        ref_soja_sp = await svc_sp.obter_referencia_consolidada("SOJA", fazenda_sp.id)
        assert ref_soja_sp.origem_efetiva == "OFICIAL_UF"
        assert ref_soja_sp.fonte_efetiva == "IEA/SAA-SP"
        val_soja_eff, rotulo_soja_eff = await svc_sp.resolver_cotacao_efetiva("SOJA", fazenda_sp.id)
        assert val_soja_eff is not None and val_soja_eff > 0
        assert rotulo_soja_eff == "IEA/SAA-SP (SP)"

        # MT sem fonte coletada continua herdando DERAL
        ref_soja_mt = await svc_sp.obter_referencia_consolidada("SOJA", fazenda_mt.id)
        assert ref_soja_mt.origem_efetiva == "DERAL"

        # Isolamento multi-tenant estrito bloqueia acesso cruzado
        svc_outro = CotacaoRegionalService(s, tenant_outro.id)
        with pytest.raises(EntityNotFoundError):
            await svc_outro.obter_referencia_consolidada("SOJA", fazenda_sp.id)


# ---------------------------------------------------------------------------
# 5. Migration Alembic upgrade/downgrade em SQLite
# ---------------------------------------------------------------------------


def test_alembic_migration_agro_collector_upgrade_and_downgrade() -> None:
    mig_path = (
        Path(__file__).resolve().parents[2]
        / "migrations"
        / "versions"
        / "20261122_agro_collector_foundation.py"
    )
    spec = importlib.util.spec_from_file_location("mig_agro_collector", mig_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.revision == "20261122_agro_collector_foundation"
    assert module.down_revision == "20261120_pecuaria_lote_hibrido"

    sync_engine = sa.create_engine("sqlite:///:memory:", future=True)
    with sync_engine.begin() as conn:
        # Tabela pai mínima exigida pela FK opcional admin_users.id
        conn.execute(sa.text("CREATE TABLE admin_users (id CHAR(32) PRIMARY KEY)"))
        ctx = MigrationContext.configure(conn)
        with Operations.context(ctx):
            module.upgrade()
        insp = sa.inspect(conn)
        for table_name in (
            "agro_data_sources",
            "agro_ingestion_runs",
            "agro_ingestion_artifacts",
            "agro_staging_observations",
            "agro_market_observations",
        ):
            assert insp.has_table(table_name)

        ctx_down = MigrationContext.configure(conn)
        with Operations.context(ctx_down):
            module.downgrade()
        insp_after = sa.inspect(conn)
        assert not insp_after.has_table("agro_market_observations")
        assert not insp_after.has_table("agro_data_sources")
    sync_engine.dispose()
