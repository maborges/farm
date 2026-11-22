"""Testes offline Fase 1B: PDFs EMATER-RS/SEAPA-MG, IA Nível 2, Sentinela e Backoffice API."""

from __future__ import annotations

import json
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agro_collector.backoffice_service import reset_collector_rate_limits  # noqa: E402
from agro_collector.collectors import (  # noqa: E402
    CollectorContext,
    GenericPartnerCollector,
    SeapaMgPdfCollector,
)
from agro_collector.collectors.emater_rs import discover_latest_emater_pdf_url  # noqa: E402
from agro_collector.fetcher import SafeHttpFetcher  # noqa: E402
from agro_collector.models import (  # noqa: E402
    AgroCollectorBase,
    AgroDataSource,
    AgroIngestionRun,
    AgroStagingObservation,
)
from agro_collector.notifier import notify_collector_event, reset_alert_throttle  # noqa: E402
from agro_collector.orchestrator import AgroCollectorOrchestrator  # noqa: E402
from agro_collector.pdf_extractor import PdfExtractionError, extract_text_from_pdf  # noqa: E402
from agro_collector.repository import purge_expired_artifacts  # noqa: E402
from agro_collector.seed_sources import ensure_default_sources  # noqa: E402
from core.database import Base  # noqa: E402
from core.dependencies import get_current_admin, get_session  # noqa: E402
from core.models.admin_audit_log import AdminAuditLog  # noqa: E402
from core.models.admin_user import AdminUser  # noqa: E402
from core.models.auth import Usuario  # noqa: E402
from core.models.configuration import ConfiguracaoSaaS  # noqa: E402
from core.routers.backoffice_agro_mercado import router as agro_mercado_router  # noqa: E402
from public_mercado.cotacoes_regiao_service import CotacaoMultiFonteService  # noqa: E402

FIXTURES_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "agro_collector"
EMATER_HTML_PATH = FIXTURES_ROOT / "emater_rs" / "precos_semanais.html"
EMATER_PDF_PATH = FIXTURES_ROOT / "emater_rs" / "preco_19112026.pdf"
SEAPA_PDF_PATH = (
    FIXTURES_ROOT / "seapa_mg" / "precos-correntes-de-produtos-selecionado-17-11-2026.pdf"
)


@pytest.fixture
async def fase1b_env():
    """Ambiente SQLite isolado com tabelas core, Backoffice e Coletor + cliente FastAPI."""
    reset_collector_rate_limits()
    reset_alert_throttle()

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    core_tables = [
        ConfiguracaoSaaS.__table__,
        AdminAuditLog.__table__,
        AdminUser.__table__,
        Usuario.__table__,
    ]

    def _create_all(sync_conn) -> None:
        Base.metadata.create_all(sync_conn, tables=core_tables)
        AgroCollectorBase.metadata.create_all(sync_conn)

    async with engine.begin() as conn:
        await conn.run_sync(_create_all)

    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    admin_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    viewer_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    async with factory() as session:
        session.add_all(
            [
                AdminUser(
                    id=admin_id,
                    email="admin@deepfarms.com",
                    nome="Admin Agro",
                    role="admin",
                    ativo=True,
                    senha_hash="mock",
                ),
                AdminUser(
                    id=viewer_id,
                    email="viewer@deepfarms.com",
                    nome="Viewer Agro",
                    role="suporte",
                    ativo=True,
                    senha_hash="mock",
                ),
            ]
        )
        await ensure_default_sources(session)
        await session.commit()

    app = FastAPI()
    app.include_router(agro_mercado_router, prefix="/api/v1")

    async def _override_session():
        async with factory() as s:
            yield s

    app.dependency_overrides[get_session] = _override_session

    try:
        yield {
            "app": app,
            "factory": factory,
            "admin_id": admin_id,
            "viewer_id": viewer_id,
        }
    finally:
        reset_collector_rate_limits()
        reset_alert_throttle()
        await engine.dispose()


# ---------------------------------------------------------------------------
# 1. Extração PDF Real & Descoberta EMATER-RS / SEAPA-MG
# ---------------------------------------------------------------------------


def test_pdf_extractor_real_fixtures_and_corruption_guard() -> None:
    emater_text = extract_text_from_pdf(EMATER_PDF_PATH.read_bytes())
    assert "Soja" in emater_text
    assert "144,61" in emater_text
    assert "79,38" in emater_text

    seapa_text = extract_text_from_pdf(SEAPA_PDF_PATH.read_bytes())
    assert "CAF" in seapa_text
    assert "1.669,00" in seapa_text
    assert "FEIJ" in seapa_text and "295,00" in seapa_text

    latest_url = discover_latest_emater_pdf_url(
        EMATER_HTML_PATH.read_text(encoding="latin-1", errors="replace"),
        "https://www.emater.tche.br/site/area-tecnica/precos-semanais.php",
    )
    assert latest_url == "https://www.emater.tche.br/site/arquivos_pdf/precos/preco_19112026.pdf"

    with pytest.raises(PdfExtractionError):
        extract_text_from_pdf(b"<html>not a pdf</html>")
    with pytest.raises(PdfExtractionError):
        extract_text_from_pdf(b"%PDF-1.4\n%%EOF")


# ---------------------------------------------------------------------------
# 2. EMATER-RS Nível 2 IA + Bloqueio Determinístico Anti-Alucinação
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_emater_rs_ai_extraction_blocks_hallucination_and_quarantines_valid(
    fase1b_env,
) -> None:
    factory = fase1b_env["factory"]
    html_bytes = EMATER_HTML_PATH.read_bytes()
    pdf_bytes = EMATER_PDF_PATH.read_bytes()
    emater_text = extract_text_from_pdf(pdf_bytes)

    def _handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith(".pdf"):
            return httpx.Response(
                200, content=pdf_bytes, headers={"Content-Type": "application/pdf"}
            )
        return httpx.Response(200, content=html_bytes, headers={"Content-Type": "text/html"})

    fetcher = SafeHttpFetcher(
        resolve_dns=False,
        client_factory=lambda: httpx.AsyncClient(
            transport=httpx.MockTransport(_handler), follow_redirects=False
        ),
    )

    real_snippet = "Média 2,40 4,98 79,38 12,61 10,16 15,10 61,96 144,61"
    assert real_snippet[:20] in emater_text

    async def _mock_llm(_prompt: str, **_kw) -> str:
        return json.dumps(
            {
                "itens": [
                    {
                        "commodity_id": "soja",
                        "uf": "RS",
                        "praca": "Rio Grande do Sul — Média Estadual",
                        "data_referencia": "2026-11-20",
                        "valor_original": "144.61",
                        "unidade_original": "Saca de 60 kg",
                        "trecho_exato_evidencia": real_snippet,
                        "confianca": 0.94,
                        "periodicidade": "SEMANAL",
                    },
                    {
                        "commodity_id": "milho",
                        "uf": "RS",
                        "praca": "Rio Grande do Sul — Média Estadual",
                        "data_referencia": "2026-11-20",
                        "valor_original": "999.99",
                        "unidade_original": "Saca de 60 kg",
                        "trecho_exato_evidencia": "Milho fantasma 999,99 inexistente no PDF",
                        "confianca": 0.40,
                        "periodicidade": "SEMANAL",
                    },
                ]
            }
        )

    async with factory() as s:
        src = (
            await s.execute(select(AgroDataSource).where(AgroDataSource.slug == "emater_rs"))
        ).scalar_one()
        src.max_defasagem_dias = 3650
        await s.commit()

    orchestrator = AgroCollectorOrchestrator(factory, fetcher=fetcher, ia_callable=_mock_llm)
    summary = await orchestrator.run_source_by_slug("emater_rs", trigger_tipo="MANUAL")

    assert summary.status == "QUARENTENA"
    assert summary.total_extraidos == 2
    assert summary.total_publicados == 0
    assert summary.total_quarentena == 1
    assert summary.total_rejeitados == 1

    async with factory() as s:
        run = (
            await s.execute(select(AgroIngestionRun).where(AgroIngestionRun.id == summary.run_id))
        ).scalar_one()
        assert run.modelo_ia == "mock-ia-test"
        assert run.tokens_entrada > 0 and run.tokens_saida > 0

        soja_stg = (
            await s.execute(
                select(AgroStagingObservation).where(
                    AgroStagingObservation.run_id == summary.run_id,
                    AgroStagingObservation.commodity_id == "soja",
                )
            )
        ).scalar_one()
        assert soja_stg.status_revisao == "PENDENTE_REVISAO"

        milho_stg = (
            await s.execute(
                select(AgroStagingObservation).where(
                    AgroStagingObservation.run_id == summary.run_id,
                    AgroStagingObservation.commodity_id == "milho",
                )
            )
        ).scalar_one()
        assert milho_stg.status_revisao == "REJEITADO"
        assert "FLAG_EVIDENCIA_NAO_CONFERE" in milho_stg.flags_anomalia


# ---------------------------------------------------------------------------
# 3. SEAPA-MG PDF Real & Parceiro Autorizado (CSV c/ anti-formula + HTML IA)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_seapa_mg_pdf_and_generic_partner_collectors() -> None:
    seapa_pdf = SEAPA_PDF_PATH.read_bytes()
    seapa_text = extract_text_from_pdf(seapa_pdf)
    cafe_snippet = "16/11/2026 1.669,00"
    assert cafe_snippet in seapa_text

    def _seapa_handler(_req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=seapa_pdf, headers={"Content-Type": "application/pdf"})

    seapa_fetcher = SafeHttpFetcher(
        resolve_dns=False,
        client_factory=lambda: httpx.AsyncClient(
            transport=httpx.MockTransport(_seapa_handler), follow_redirects=False
        ),
    )

    async def _mock_seapa_ai(_prompt: str, **_kw) -> str:
        return json.dumps(
            {
                "itens": [
                    {
                        "commodity_id": "cafe-arabica",
                        "uf": "MG",
                        "praca": "Minas Gerais — Café Corrente",
                        "data_referencia": "2026-11-16",
                        "valor_original": "1669.00",
                        "unidade_original": "Saca de 60 kg",
                        "trecho_exato_evidencia": cafe_snippet,
                        "confianca": 0.91,
                        "periodicidade": "SEMANAL",
                    }
                ]
            }
        )

    seapa_src = AgroDataSource(
        id=uuid.uuid4(),
        slug="seapa_mg",
        nome="SEAPA-MG",
        sigla="SEAPA-MG",
        tipo_licenca="DADO_PUBLICO_GOV",
        uf_padrao="MG",
        dominios_whitelist=["www.mg.gov.br"],
        url_principal="https://www.mg.gov.br/seapa.pdf",
        estrategia_coleta="NIVEL2_IA_PDF_HTML",
        config_extrator={},
    )
    seapa_res = await SeapaMgPdfCollector().collect(
        CollectorContext(source=seapa_src, fetcher=seapa_fetcher, ia_callable=_mock_seapa_ai)
    )
    assert len(seapa_res.observations) == 1
    assert seapa_res.observations[0].commodity_id == "cafe-arabica"
    assert seapa_res.modelo_ia == "mock-ia-test"

    csv_body = (
        b"commodity_id;uf;praca;data_referencia;valor;unidade\n"
        b"soja;MT;=CMD('Sorriso');2026-11-20;121,50;Saca de 60 kg\n"
    )

    partner_fetcher = SafeHttpFetcher(
        resolve_dns=False,
        client_factory=lambda: httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda _r: httpx.Response(
                    200, content=csv_body, headers={"Content-Type": "text/csv"}
                )
            ),
            follow_redirects=False,
        ),
    )
    partner_src = AgroDataSource(
        id=uuid.uuid4(),
        slug="coop_sorriso_mt",
        nome="Cooperativa Agrícola Sorriso",
        sigla="COOP-SORRISO",
        tipo_licenca="PARCEIRO_AUTORIZADO",
        termo_autorizacao_ref="Termo 2026/001",
        uf_padrao="MT",
        dominios_whitelist=["dados.coopsorriso.com.br"],
        url_principal="https://dados.coopsorriso.com.br/precos.csv",
        estrategia_coleta="GENERICO_PARCEIRO",
        config_extrator={"formato": "csv"},
    )
    partner_res = await GenericPartnerCollector().collect(
        CollectorContext(source=partner_src, fetcher=partner_fetcher)
    )
    assert len(partner_res.observations) == 1
    assert partner_res.observations[0].praca.startswith("'=")  # Formula injection neutralizada


# ---------------------------------------------------------------------------
# 4. Sentinela Nível 3 + Throttling de E-mail Sem Ruído
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sentinel_discovery_on_3_failures_and_notifier_throttle(fase1b_env) -> None:
    factory = fase1b_env["factory"]
    index_html = (
        '<html><body>'
        '<a href="https://evil.com/phishing_preco.pdf">Malicioso</a>'
        '<a href="http://www.emater.tche.br/site/inseguro_preco.pdf">HTTP Inseguro</a>'
        '<a href="/site/arquivos_pdf/precos/preco_26112026.pdf">Boletim Semanal 26/11/2026</a>'
        "</body></html>"
    )

    def _handler(request: httpx.Request) -> httpx.Response:
        if "precos-semanais.php" in request.url.path:
            return httpx.Response(200, content=index_html.encode("utf-8"))
        return httpx.Response(404)

    fetcher = SafeHttpFetcher(
        resolve_dns=False,
        client_factory=lambda: httpx.AsyncClient(
            transport=httpx.MockTransport(_handler), follow_redirects=False
        ),
    )

    sent_emails: list[tuple[str, str, str]] = []

    async def _mock_mail(to: str, subj: str, body: str) -> None:
        sent_emails.append((to, subj, body))

    async with factory() as s:
        src = (
            await s.execute(select(AgroDataSource).where(AgroDataSource.slug == "emater_rs"))
        ).scalar_one()
        src.url_principal = "https://www.emater.tche.br/site/arquivos_pdf/precos/link_quebrado.pdf"
        src.falhas_consecutivas = 2
        src.config_extrator = {"alert_emails": ["ops@deepfarms.com"]}
        await s.commit()

    orchestrator = AgroCollectorOrchestrator(factory, fetcher=fetcher, send_email_fn=_mock_mail)
    summary = await orchestrator.run_source_by_slug("emater_rs", trigger_tipo="AGENDADO")
    assert summary.status == "FALHA"
    assert summary.sugestao_sentinela is not None
    assert (
        summary.sugestao_sentinela["url_sugerida"]
        == "https://www.emater.tche.br/site/arquivos_pdf/precos/preco_26112026.pdf"
    )
    assert len(sent_emails) == 2  # FALHA_CONSECUTIVA + SUGESTAO_SENTINELA

    # Nova tentativa dentro de 6h não envia e-mail repetido
    async with factory() as s:
        src = (
            await s.execute(select(AgroDataSource).where(AgroDataSource.slug == "emater_rs"))
        ).scalar_one()
        blocked_count = await notify_collector_event(
            session=s,
            source=src,
            event_kind="FALHA_CONSECUTIVA",
            summary_lines=["Repetida"],
            send_email_fn=_mock_mail,
        )
        assert blocked_count == 0
        assert len(sent_emails) == 2


# ---------------------------------------------------------------------------
# 5. Backoffice API (RBAC, CRUD Parceiro, Dry-Run, Run, Artifact, Sentinela, Aprovação 1-Clique)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_backoffice_collector_api_e2e_and_rbac(fase1b_env) -> None:
    app: FastAPI = fase1b_env["app"]
    factory = fase1b_env["factory"]
    admin_id = fase1b_env["admin_id"]
    viewer_id = fase1b_env["viewer_id"]

    active_claims: dict = {
        "sub": str(viewer_id),
        "id": str(viewer_id),
        "email": "viewer@deepfarms.com",
        "role": "suporte",
        "type": "admin",
        "permissoes": ["backoffice:agro:market:view"],
    }
    app.dependency_overrides[get_current_admin] = lambda: active_claims

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Viewer lê sources (200) mas é bloqueado ao criar parceiro (403)
        res_list = await client.get("/api/v1/backoffice/agro/mercado/collector/sources")
        assert res_list.status_code == 200
        assert res_list.json()["total"] >= 6

        res_forbidden = await client.post(
            "/api/v1/backoffice/agro/mercado/collector/sources",
            json={
                "slug": "coop_mt",
                "nome": "Coop MT",
                "sigla": "COOP-MT",
                "tipo_licenca": "PARCEIRO_AUTORIZADO",
                "termo_autorizacao_ref": "Termo 01",
                "uf_padrao": "MT",
                "dominios_whitelist": ["coop.mt.example.com"],
                "url_principal": "https://coop.mt.example.com/precos.csv",
            },
        )
        assert res_forbidden.status_code == 403

        # Promove para admin
        active_claims["sub"] = str(admin_id)
        active_claims["id"] = str(admin_id)
        active_claims["email"] = "admin@deepfarms.com"
        active_claims["permissoes"] = ["backoffice:agro:*"]

        # Parceiro sem termo -> 422
        res_no_term = await client.post(
            "/api/v1/backoffice/agro/mercado/collector/sources",
            json={
                "slug": "coop_sem_termo",
                "nome": "Coop Sem Termo",
                "sigla": "COOP-ERR",
                "tipo_licenca": "PARCEIRO_AUTORIZADO",
                "uf_padrao": "GO",
                "dominios_whitelist": ["coop.go.example.com"],
                "url_principal": "https://coop.go.example.com/precos.csv",
            },
        )
        assert res_no_term.status_code == 422

        # Cria parceiro válido + verifica HTTP/whitelist SSRF
        res_bad_url = await client.post(
            "/api/v1/backoffice/agro/mercado/collector/sources",
            json={
                "slug": "coop_ssrf",
                "nome": "Coop SSRF",
                "sigla": "COOP-SSRF",
                "tipo_licenca": "PARCEIRO_AUTORIZADO",
                "termo_autorizacao_ref": "Termo 02",
                "uf_padrao": "GO",
                "dominios_whitelist": ["coop.go.example.com"],
                "url_principal": "http://127.0.0.1/steal.csv",
            },
        )
        assert res_bad_url.status_code == 422

        # Configura mock fetcher para emater_rs usando fixture real
        emater_pdf = EMATER_PDF_PATH.read_bytes()
        emater_html = EMATER_HTML_PATH.read_bytes()

        def _emater_handler(req: httpx.Request) -> httpx.Response:
            if req.url.path.endswith(".pdf"):
                return httpx.Response(
                    200, content=emater_pdf, headers={"Content-Type": "application/pdf"}
                )
            return httpx.Response(200, content=emater_html)

        mock_fetcher = SafeHttpFetcher(
            resolve_dns=False,
            client_factory=lambda: httpx.AsyncClient(
                transport=httpx.MockTransport(_emater_handler), follow_redirects=False
            ),
        )
        sources_payload = (
            await client.get("/api/v1/backoffice/agro/mercado/collector/sources")
        ).json()
        emater_src = next(s for s in sources_payload["sources"] if s["slug"] == "emater_rs")

        with (
            patch("agro_collector.orchestrator.SafeHttpFetcher", return_value=mock_fetcher),
            patch(
                "agro_collector.backoffice_service.AgroCollectorOrchestrator"
            ) as mock_orch_cls,
            patch("ia.anthropic_client.has_ia_configured", return_value=False),
        ):
            real_orch = AgroCollectorOrchestrator(factory, fetcher=mock_fetcher)
            mock_orch_cls.return_value = real_orch

            res_dry = await client.post(
                f"/api/v1/backoffice/agro/mercado/collector/sources/{emater_src['id']}/test-dry-run"
            )
            assert res_dry.status_code == 200
            dry_data = res_dry.json()
            assert dry_data["total_extraidos"] >= 7

            # Rate limit imediato no dry-run -> 429
            res_dry_429 = await client.post(
                f"/api/v1/backoffice/agro/mercado/collector/sources/{emater_src['id']}/test-dry-run"
            )
            assert res_dry_429.status_code == 429

            # Executa run real sobre EMATER-RS (sem IA -> fallback determinístico)
            res_run = await client.post(
                f"/api/v1/backoffice/agro/mercado/collector/sources/{emater_src['id']}/run"
            )
            assert res_run.status_code == 200
            run_summary = res_run.json()
            assert run_summary["status"] == "QUARENTENA"
            assert run_summary["total_quarentena"] >= 7

        # Baixa artefato forense comprimido e verifica integridade
        res_art = await client.get(
            f"/api/v1/backoffice/agro/mercado/collector/runs/{run_summary['run_id']}/artifact"
        )
        assert res_art.status_code == 200
        assert res_art.content == emater_pdf
        assert len(res_art.headers.get("X-Artifact-SHA256", "")) == 64

        # Testa sugestão do Sentinela + Apply Sentinel
        async with factory() as s:
            run_obj = (
                await s.execute(
                    select(AgroIngestionRun).where(
                        AgroIngestionRun.id == uuid.UUID(run_summary["run_id"])
                    )
                )
            ).scalar_one()
            run_obj.sugestao_sentinela = {
                "url_sugerida": "https://www.emater.tche.br/site/arquivos_pdf/precos/preco_19112026.pdf",
                "evidencia": "Link descoberto no boletim semanal",
            }
            src_obj = (
                await s.execute(select(AgroDataSource).where(AgroDataSource.slug == "emater_rs"))
            ).scalar_one()
            src_obj.ativo = True
            await s.commit()

        res_sentinel = await client.post(
            f"/api/v1/backoffice/agro/mercado/collector/runs/{run_summary['run_id']}/apply-sentinel",
            json={"justificativa": "URL validada e aplicada após mudança no portal EMATER."},
        )
        assert res_sentinel.status_code == 200
        assert res_sentinel.json()["url_principal"].endswith("preco_19112026.pdf")

        # Lista quarentena e aprova soja RS 1-clique
        res_stg = await client.get("/api/v1/backoffice/agro/mercado/collector/staging")
        assert res_stg.status_code == 200
        stg_items = res_stg.json()["items"]
        soja_stg = next(i for i in stg_items if i["commodity_id"] == "soja")

        res_approve = await client.post(
            f"/api/v1/backoffice/agro/mercado/collector/staging/{soja_stg['id']}/approve",
            json={"justificativa": "Cotação soja 144,61 conferida literalmente no boletim EMATER."},
        )
        assert res_approve.status_code == 200
        assert res_approve.json()["status_revisao"] == "APROVADO"

        # Verifica publicação visível imediatamente em CotacaoMultiFonteService para uf=RS
        async with factory() as s:
            multi = CotacaoMultiFonteService(session=s)
            rs_soja = await multi.consultar(produto="soja", uf="RS", incluir_ibge=False)
            assert rs_soja.itens[0].fontes[0].sigla_fonte == "EMATER/RS"
            assert rs_soja.itens[0].fontes[0].valor == 144.61

            # Verifica trilha obrigatória no AdminAuditLog
            audits = (await s.execute(select(AdminAuditLog))).scalars().all()
            acoes = {a.acao for a in audits}
            assert {"MANUAL_RUN", "APPLY_SENTINEL", "APPROVE"}.issubset(acoes)

            # Verifica HTTP 410 Gone ao tentar baixar artefato expurgado (> 12 meses)
            await purge_expired_artifacts(
                s, now=datetime.now(timezone.utc) + timedelta(days=400)  # noqa: UP017
            )
            await s.commit()

        res_art_gone = await client.get(
            f"/api/v1/backoffice/agro/mercado/collector/runs/{run_summary['run_id']}/artifact"
        )
        assert res_art_gone.status_code == 410
