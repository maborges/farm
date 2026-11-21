from __future__ import annotations

import copy
import json
import uuid
from datetime import date, datetime, timezone

import pytest
from fastapi import FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles

from agricola.custos.models import CostAllocation
from agricola.cultivos.models import Cultivo
from agricola.production_units.models import ProductionUnit
from agricola.safras.models import Safra
from campo.models import TarefaCampo
from core.cadastros.commodities.cotacao_regional_service import CotacaoRegionalService
from core.cadastros.commodities.router import router as commodities_router
from core.cadastros.commodities.schemas import CotacaoRegionalUpsertRequest
from core.cadastros.pessoas.models import Pessoa
from core.cadastros.produtos.models import Produto
from core.cadastros.propriedades.models import AreaRural
from core.database import Base
from core.dependencies import get_session, get_tenant_id
from core.exceptions import EntityNotFoundError
from core.measurements.models import UnidadeMedida
from core.models.admin_audit_log import AdminAuditLog
from core.models.admin_user import AdminUser
from core.models.auth import Usuario
from core.models.configuracao_fazenda import ConfiguracaoFazenda
from core.models.configuration import ConfiguracaoSaaS
from core.models.tenant import Tenant
from core.models.tenant_config import ConfiguracaoTenant
from core.models.unidade_produtiva import UnidadeProdutiva
from core.schemas.agro_config_schemas import KEY_MERCADO
from core.services.deral_auto_sync_service import deral_auto_sync_service, validar_url_deral_segura
from core.services.deral_snapshot_service import (
    deral_snapshot_service,
    parse_deral_csv,
    parse_deral_xls,
)
from financeiro.models.lancamento import LancamentoFinanceiro
from operacional.models.estoque import Deposito, EstoqueMovimento
from pecuaria.animal.models import Animal, EventoAnimal, LoteAnimal
from pecuaria.models.manejo import ManejoLote
from pecuaria.producao.models import ProducaoLeite
from pecuaria.services.dashboard_resumo_service import PecuariaDashboardResumoService
from pecuaria.services.lote_indicadores_service import LoteIndicadoresService
from public_mercado.cache import PtaxCache
from public_mercado.precos_publicos import (
    SNAPSHOT_PATH,
    carregar_catalogo_mercado,
    carregar_precos_publicos,
    set_snapshot_cache_override,
)
from public_mercado.precos_publicos_service import PrecosPublicosService
from public_mercado.router import apply_dynamic_market_config, get_precos_service


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(_type, _compiler, **_kw):
    return "JSON"


@compiles(ARRAY, "sqlite")
def _compile_array_sqlite(_type, _compiler, **_kw):
    return "JSON"


@pytest.fixture
async def db_session(tmp_path):
    db_file = tmp_path / "test_mercado_fontes.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_file}")
    tables = [
        Tenant.__table__,
        UnidadeProdutiva.__table__,
        AreaRural.__table__,
        Safra.__table__,
        ProductionUnit.__table__,
        Cultivo.__table__,
        UnidadeMedida.__table__,
        Produto.__table__,
        Deposito.__table__,
        Pessoa.__table__,
        LoteAnimal.__table__,
        ManejoLote.__table__,
        Animal.__table__,
        EventoAnimal.__table__,
        ProducaoLeite.__table__,
        TarefaCampo.__table__,
        EstoqueMovimento.__table__,
        CostAllocation.__table__,
        LancamentoFinanceiro.__table__,
        ConfiguracaoSaaS.__table__,
        ConfiguracaoTenant.__table__,
        ConfiguracaoFazenda.__table__,
        AdminAuditLog.__table__,
        AdminUser.__table__,
        Usuario.__table__,
    ]
    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: Base.metadata.create_all(sync_conn, tables=tables))

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    deral_snapshot_service.clear_cache()
    try:
        async with factory() as session:
            yield session
    finally:
        deral_snapshot_service.clear_cache()
        set_snapshot_cache_override(None)
        await engine.dispose()


def test_defasagem_dinamica_precos_e_catalogo():
    baseline = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    snapshot = copy.deepcopy(baseline)
    snapshot["dataReferencia"] = "2026-11-13"
    consulta = datetime(2026, 11, 21, 12, 0, tzinfo=timezone.utc)

    set_snapshot_cache_override(snapshot)
    try:
        import asyncio

        svc_14 = PrecosPublicosService(
            PtaxCache("redis://invalid:6379/0", single_worker_fallback=True),
            ttl_seconds=1800,
            max_defasagem_dias=14,
        )

        res_precos = asyncio.run(svc_14.get_precos(consulta))
        res_cat = asyncio.run(svc_14.get_catalogo(consulta))
        soja = next(item for item in res_cat.itens if item.id == "soja")
        assert res_precos.estadoDisponibilidade == "NORMAL"
        assert res_cat.estadoDisponibilidade == "NORMAL"
        assert soja.estadoDisponibilidade == "DISPONIVEL"

        svc_7 = get_precos_service()
        svc_7.invalidate_cache()
        apply_dynamic_market_config({"max_defasagem_dias": 7})
        res_precos_7 = asyncio.run(svc_7.get_precos(consulta))
        res_cat_7 = asyncio.run(svc_7.get_catalogo(consulta))
        soja_7 = next(item for item in res_cat_7.itens if item.id == "soja")
        assert res_precos_7.estadoDisponibilidade == "DEFASADO"
        assert res_cat_7.estadoDisponibilidade == "DEFASADO"
        assert soja_7.estadoDisponibilidade == "DEFASADO"
    finally:
        apply_dynamic_market_config({"max_defasagem_dias": 14})
        get_precos_service().invalidate_cache()
        set_snapshot_cache_override(None)


@pytest.mark.asyncio
async def test_deral_csv_template_parser_upload_e_validacoes(db_session: AsyncSession):
    template_bytes, filename = await deral_snapshot_service.gerar_template_csv(db_session)
    assert filename.endswith(".csv")
    assert b"\xef\xbb\xbf" in template_bytes[:4]

    csv_text = template_bytes.decode("utf-8-sig").replace(
        date.today().isoformat(), "2026-11-20"
    )
    csv_bytes = csv_text.encode("utf-8")
    parsed = parse_deral_csv(csv_bytes, "a" * 64)
    assert parsed["dataReferencia"] == "2026-11-20"
    assert len(parsed["itens"]) == 21
    soja = next(item for item in parsed["itens"] if item["id"] == "soja")
    assert soja["registroOriginal"].startswith("Rav!X")

    admin_id = uuid.uuid4()
    db_session.add(
        AdminUser(
            id=admin_id,
            email="admin@deepfarms.com",
            nome="Admin",
            senha_hash="x",
            role="admin",
            ativo=True,
        )
    )
    await db_session.commit()
    claims = {"sub": str(admin_id), "email": "admin@deepfarms.com"}

    upload_res = await deral_snapshot_service.upload_snapshot(
        db_session, csv_bytes, "deral-prp-2026-11-20.csv", claims
    )
    assert upload_res.sucesso is True
    assert upload_res.metadata.id == "2026-11-20"

    await deral_snapshot_service.approve_snapshot(
        db_session, "2026-11-20", True, "CSV conferido", claims
    )
    await deral_snapshot_service.activate_snapshot(
        db_session, "2026-11-20", claims, justificativa="Ativação semanal CSV"
    )
    _, raw_name, content_type = await deral_snapshot_service.get_snapshot_raw_bytes(
        db_session, "2026-11-20"
    )
    assert raw_name.endswith(".csv")
    assert content_type.startswith("text/csv")

    # Valida rejeições de segurança e integridade no CSV
    bad_formula = csv_text.replace("https://www.agricultura.pr.gov.br", "=CMD()")
    with pytest.raises(HTTPException) as exc_formula:
        parse_deral_csv(bad_formula.encode("utf-8"), "a" * 64)
    assert exc_formula.value.status_code == 400

    bad_missing = "\n".join(csv_text.splitlines()[:-1])
    with pytest.raises(HTTPException) as exc_missing:
        parse_deral_csv(bad_missing.encode("utf-8"), "a" * 64)
    assert exc_missing.value.status_code == 400


@pytest.mark.asyncio
async def test_deral_sync_sob_demanda_idempotente_e_anti_ssrf(
    db_session: AsyncSession, monkeypatch
):
    with pytest.raises(ValueError):
        validar_url_deral_segura("http://agricultura.pr.gov.br/system/files/publico/Precos/prp.xls")
    with pytest.raises(ValueError):
        validar_url_deral_segura("https://evil.example.com/prp.xls")

    assert validar_url_deral_segura(
        "https://www.agricultura.pr.gov.br/system/files/publico/Precos/prp.xls"
    ).startswith("https://")

    baseline = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    admin_id = uuid.uuid4()
    db_session.add(
        AdminUser(
            id=admin_id,
            email="sync-op@deepfarms.com",
            nome="Sync Op",
            senha_hash="x",
            role="admin",
            ativo=True,
        )
    )
    await db_session.commit()
    claims = {"sub": str(admin_id), "email": "sync-op@deepfarms.com"}

    same_payload = copy.deepcopy(baseline)
    monkeypatch.setattr(
        deral_auto_sync_service,
        "_baixar_e_validar",
        lambda _url=None: (b"OLE2-SAME", same_payload),
    )
    res_same = await deral_auto_sync_service.sincronizar_com_detalhes(db_session, claims)
    assert res_same.atualizado is False
    assert res_same.snapshot_ativo_atual == "2026-10-16"

    newer_payload = copy.deepcopy(baseline)
    newer_payload["dataReferencia"] = "2026-11-20"
    newer_payload["semana"] = "47-2026"
    monkeypatch.setattr(
        deral_auto_sync_service,
        "_baixar_e_validar",
        lambda _url=None: (json.dumps(newer_payload).encode("utf-8"), newer_payload),
    )
    res_newer = await deral_auto_sync_service.sincronizar_com_detalhes(db_session, claims)
    assert res_newer.atualizado is True
    assert res_newer.snapshot_ativo_anterior == "2026-10-16"
    assert res_newer.snapshot_ativo_atual == "2026-11-20"


@pytest.mark.asyncio
async def test_cotacoes_regionais_multitenant_hierarquia_e_pecuaria(db_session: AsyncSession):
    tenant_a = uuid.uuid4()
    tenant_b = uuid.uuid4()
    faz_a1 = uuid.uuid4()
    faz_a2 = uuid.uuid4()
    lote_reg_id = uuid.uuid4()
    lote_ovr_id = uuid.uuid4()

    db_session.add_all([
        Tenant(id=tenant_a, nome="Grupo A", slug="grupo-a", documento="11111111000101"),
        Tenant(id=tenant_b, nome="Grupo B", slug="grupo-b", documento="22222222000102"),
        UnidadeProdutiva(id=faz_a1, tenant_id=tenant_a, nome="Fazenda São Paulo"),
        UnidadeProdutiva(id=faz_a2, tenant_id=tenant_a, nome="Fazenda Goiás"),
        ConfiguracaoFazenda(
            id=uuid.uuid4(),
            tenant_id=tenant_a,
            unidade_produtiva_id=faz_a1,
            overrides={"fuso_horario": "America/Sao_Paulo"},
        ),
        LoteAnimal(
            id=lote_reg_id,
            tenant_id=tenant_a,
            unidade_produtiva_id=faz_a1,
            identificacao="Lote Regional",
            modo_gestao="POR_LOTE",
            categoria="Engorda",
            raca="Nelore",
            quantidade_cabecas=50,
            peso_medio_kg=300.0,
            valor_aquisicao_total=100000.0,
            cotacao_arroba_override=None,
            ativo=True,
        ),
        LoteAnimal(
            id=lote_ovr_id,
            tenant_id=tenant_a,
            unidade_produtiva_id=faz_a1,
            identificacao="Lote Override",
            modo_gestao="POR_LOTE",
            categoria="Engorda",
            raca="Angus",
            quantidade_cabecas=50,
            peso_medio_kg=300.0,
            valor_aquisicao_total=100000.0,
            cotacao_arroba_override=355.0,
            ativo=True,
        ),
    ])
    await db_session.commit()

    svc_a = CotacaoRegionalService(db_session, tenant_a)
    svc_b = CotacaoRegionalService(db_session, tenant_b)

    await svc_a.salvar_cotacao_regional(
        "BOI_GORDO",
        CotacaoRegionalUpsertRequest(
            valor=335.0,
            data_referencia="2026-11-21",
            praca="Araçatuba/SP",
            fonte="Frigorífico Regional",
            escopo="TENANT",
        ),
    )
    await svc_a.salvar_cotacao_regional(
        "BOI_GORDO",
        CotacaoRegionalUpsertRequest(
            valor=340.0,
            data_referencia="2026-11-21",
            praca="Barretos/SP",
            fonte="Escala Local",
            escopo="FAZENDA",
            unidade_produtiva_id=faz_a1,
        ),
    )
    await db_session.commit()

    # Preserva outras chaves em ConfiguracaoFazenda.overrides
    cfg_faz = (
        await db_session.execute(
            select(ConfiguracaoFazenda).where(ConfiguracaoFazenda.unidade_produtiva_id == faz_a1)
        )
    ).scalar_one()
    assert cfg_faz.overrides["fuso_horario"] == "America/Sao_Paulo"

    # Hierarquia Fazenda > Tenant + Spread/Basis vs. DERAL + Histórico recente
    boi_item = await svc_a.obter_referencia_consolidada("BOI_GORDO", faz_a1)
    assert boi_item.valor_efetivo == pytest.approx(340.0)
    assert boi_item.valor_deral == pytest.approx(371.21)
    assert boi_item.diferenca_deral_brl == pytest.approx(-31.21)
    assert boi_item.diferenca_deral_pct == pytest.approx(-8.41, abs=0.05)
    assert len(boi_item.pracas_deral_disponiveis) >= 15
    assert any(p.praca == "Cascavel" for p in boi_item.pracas_deral_disponiveis)
    assert len(boi_item.historico_recente) >= 2
    assert boi_item.historico_recente[0].valor == pytest.approx(340.0)

    assert await svc_a.resolver_cotacao_efetiva("BOI_GORDO", faz_a1) == (340.0, "Regional (Barretos/SP)")
    assert await svc_a.resolver_cotacao_efetiva("BOI_GORDO", faz_a2) == (335.0, "Regional (Araçatuba/SP)")

    # Isolamento multi-tenant
    with pytest.raises(EntityNotFoundError):
        await svc_b.listar_referencias_consolidadas(faz_a1)

    val_b, fonte_b = await svc_b.resolver_cotacao_efetiva("BOI_GORDO", None)
    assert fonte_b != "Regional (Barretos/SP)"
    assert val_b != 340.0 or fonte_b == "DERAL/SEAB-PR"

    # Reflexo na Pecuária: Lote override > Fazenda > Tenant > DERAL
    ind_reg = await LoteIndicadoresService(db_session, tenant_a).resumir(lote_reg_id)
    assert ind_reg.cotacao_arroba_referencia == pytest.approx(340.0)
    assert ind_reg.fonte_cotacao == "Regional (Barretos/SP)"
    assert ind_reg.valor_mercado_estimado == pytest.approx(170000.0)

    ind_ovr = await LoteIndicadoresService(db_session, tenant_a).resumir(lote_ovr_id)
    assert ind_ovr.cotacao_arroba_referencia == pytest.approx(355.0)
    assert ind_ovr.fonte_cotacao == "Personalizado"
    assert ind_ovr.valor_mercado_estimado == pytest.approx(177500.0)

    resumo_dash = await PecuariaDashboardResumoService(db_session, tenant_a, faz_a1).resumir()
    assert resumo_dash.cotacao_arroba_referencia == pytest.approx(340.0)
    assert resumo_dash.fonte_cotacao == "Regional (Barretos/SP)"
    assert resumo_dash.valor_mercado_estimado == pytest.approx(347500.0)

    # Remover override da fazenda recua para o valor do tenant mantendo overrides existentes
    await svc_a.remover_cotacao_regional("BOI_GORDO", "FAZENDA", faz_a1)
    await db_session.commit()
    assert await svc_a.resolver_cotacao_efetiva("BOI_GORDO", faz_a1) == (335.0, "Regional (Araçatuba/SP)")
    await db_session.refresh(cfg_faz)
    assert cfg_faz.overrides["fuso_horario"] == "America/Sao_Paulo"


@pytest.mark.asyncio
async def test_router_cotacoes_regionais_sem_conflito_com_uuid(db_session: AsyncSession):
    tenant_id = uuid.uuid4()
    faz_id = uuid.uuid4()
    db_session.add_all([
        Tenant(id=tenant_id, nome="Tenant Router", slug="tenant-r", documento="55555555000105"),
        UnidadeProdutiva(id=faz_id, tenant_id=tenant_id, nome="Fazenda Router"),
    ])
    await db_session.commit()

    app = FastAPI()
    app.include_router(commodities_router, prefix="/api/v1")

    async def _get_sess():
        yield db_session

    app.dependency_overrides[get_session] = _get_sess
    app.dependency_overrides[get_tenant_id] = lambda: tenant_id

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res_get = await client.get(
            f"/api/v1/cadastros/commodities/cotacoes-regionais?unidade_produtiva_id={faz_id}"
        )
        assert res_get.status_code == 200
        itens = res_get.json()
        assert any(i["codigo"] == "BOI_GORDO" for i in itens)

        res_put = await client.put(
            "/api/v1/cadastros/commodities/cotacoes-regionais/BOI_GORDO",
            json={
                "valor": 345.0,
                "data_referencia": "2026-11-21",
                "praca": "Rio Verde/GO",
                "fonte": "Frigorífico GO",
                "escopo": "FAZENDA",
                "unidade_produtiva_id": str(faz_id),
            },
        )
        assert res_put.status_code == 200
        assert res_put.json()["valor_efetivo"] == pytest.approx(345.0)
        assert res_put.json()["origem_efetiva"] == "FAZENDA"

        res_del = await client.delete(
            f"/api/v1/cadastros/commodities/cotacoes-regionais/BOI_GORDO?escopo=FAZENDA&unidade_produtiva_id={faz_id}"
        )
        assert res_del.status_code == 204


@pytest.mark.asyncio
async def test_deral_xls_extrai_nucleos_regionais_min_max_e_variacao_msa(db_session: AsyncSession):
    from pathlib import Path
    import hashlib

    sample_xls = (
        Path(__file__).resolve().parents[4]
        / "docs/implementation/reports/evidencias/DEEPFARMS-AGRO-FREE-01E2F-B4B/deral-prp-2026-10-16.xls"
    )
    raw_bytes = sample_xls.read_bytes()
    sha = hashlib.sha256(raw_bytes).hexdigest()

    parsed = parse_deral_xls(raw_bytes, sha)
    soja = next(item for item in parsed["itens"] if item["id"] == "soja")
    boi = next(item for item in parsed["itens"] if item["id"] == "boi-gordo")

    assert soja["valorSemanaAnterior"] == pytest.approx(134.14)
    assert soja["variacaoSemanalAbsoluta"] == pytest.approx(0.84)
    assert soja["variacaoSemanalPct"] == pytest.approx(0.62)
    assert soja["valorMinimoRegional"] == pytest.approx(131.82)
    assert soja["pracaMinimoRegional"] == "Londrina"
    assert soja["valorMaximoRegional"] == pytest.approx(141.50)
    assert soja["pracaMaximoRegional"] == "Guarapuava"
    assert len(soja["pracasRegionais"]) == 19
    cascavel_soja = next(p for p in soja["pracasRegionais"] if p["praca"] == "Cascavel")
    assert cascavel_soja["valor"] == pytest.approx(132.98)
    assert cascavel_soja["registroOriginal"] == "Rav!F12"

    assert boi["valorSemanaAnterior"] == pytest.approx(365.08)
    assert boi["variacaoSemanalAbsoluta"] == pytest.approx(6.13)
    assert boi["variacaoSemanalPct"] == pytest.approx(1.67)
    assert boi["valorMinimoRegional"] == pytest.approx(339.61)
    assert boi["pracaMinimoRegional"] == "Cascavel"
    assert boi["valorMaximoRegional"] == pytest.approx(383.50)
    assert boi["pracaMaximoRegional"] == "Guarapuava"
    assert len(boi["pracasRegionais"]) == 18

    # Verifica contrato público carregado do baseline enriquecido
    precos_pub = carregar_precos_publicos()
    soja_pub = next(i for i in precos_pub if i.id == "soja")
    assert soja_pub.variacaoSemanalPct == pytest.approx(0.62)
    assert len(soja_pub.pracasRegionais) == 19

    cat_pub = carregar_catalogo_mercado()
    soja_cat = next(i for i in cat_pub.itens if i.id == "soja")
    assert soja_cat.variacaoSemanalPct == pytest.approx(0.62)
    assert soja_cat.valorMinimoRegional == pytest.approx(131.82)
    assert len(soja_cat.pracasRegionais) == 19

    # Upload CSV sem MSA calcula variação automaticamente contra o snapshot anterior
    template_bytes, _ = await deral_snapshot_service.gerar_template_csv(db_session)
    csv_text = (
        template_bytes.decode("utf-8-sig")
        .replace(date.today().isoformat(), "2026-11-27")
        .replace(",134.98,", ",141.73,")
    )
    admin_id = uuid.uuid4()
    db_session.add(
        AdminUser(
            id=admin_id,
            email="var-op@deepfarms.com",
            nome="Var Op",
            senha_hash="x",
            role="admin",
            ativo=True,
        )
    )
    await db_session.commit()
    claims = {"sub": str(admin_id), "email": "var-op@deepfarms.com"}
    up_res = await deral_snapshot_service.upload_snapshot(
        db_session, csv_text.encode("utf-8"), "deral-prp-2026-11-27.csv", claims
    )
    soja_up = next(i for i in up_res.itens_preview if i["id"] == "soja")
    assert soja_up["valorSemanaAnterior"] == pytest.approx(134.98)
    assert soja_up["variacaoSemanalAbsoluta"] == pytest.approx(6.75)
    assert soja_up["variacaoSemanalPct"] == pytest.approx(5.0)

    # Garante que CotacaoRegionalService reconcilia o snapshot ativo do banco (ex: 2026-11-27)
    # mesmo após limpar o cache em memória do worker, sem regredir para 2026-10-16
    await deral_snapshot_service.approve_snapshot(
        db_session, "2026-11-27", True, "Aprovado para teste de reconciliação", claims
    )
    await deral_snapshot_service.activate_snapshot(
        db_session, "2026-11-27", claims, justificativa="Ativação 2026-11-27"
    )
    deral_snapshot_service.clear_cache()

    tenant_rec = uuid.uuid4()
    db_session.add(Tenant(id=tenant_rec, nome="Tenant Rec", slug="tenant-rec", documento="77777777000107"))
    await db_session.commit()

    svc_rec = CotacaoRegionalService(db_session, tenant_rec)
    soja_rec = await svc_rec.obter_referencia_consolidada("SOJA")
    assert soja_rec.data_deral == "2026-11-27"
    assert soja_rec.valor_deral == pytest.approx(141.73)


@pytest.mark.asyncio
async def test_consulta_publica_multi_fonte_e_multi_regiao_deral_ibge_e_institucionais():
    from public_mercado.cotacoes_regiao_service import CotacaoMultiFonteService
    from public_mercado.sidra import EstatisticasIbgeResponse, IndicadorIbge, LocalidadeIbge, PontoSerieIbge, ProdutoIbge

    class _FakeSidraService:
        async def get_estatisticas(self, produto_id: str, nivel: str = "UF", uf: str | None = None, municipio: str | None = None, anos: int = 3, **_kw):
            return EstatisticasIbgeResponse(
                sucesso=True,
                dataConsultaIso=datetime(2026, 11, 21, 12, 0, tzinfo=timezone.utc),
                estadoDisponibilidade="NORMAL",
                estaDesatualizado=False,
                pesquisa="Produção Agrícola Municipal (PAM)",
                fontePesquisa="PAM",
                tabelaSidra=5457,
                urlTabela="https://sidra.ibge.gov.br/tabela/5457",
                periodicidade="ANUAL",
                produto=ProdutoIbge(id=produto_id, nome="Soja", tipo="LAVOURA"),
                localidade=LocalidadeIbge(nivel="UF", codigo=uf or "51", nome="Mato Grosso"),
                periodoSolicitado="last 3",
                ultimoPeriodoDisponivel="2025",
                indicadores=[
                    IndicadorIbge(
                        id="PRODUCAO",
                        nomeOficial="Quantidade produzida",
                        codigoVariavelSidra=214,
                        unidade="Toneladas",
                        pontos=[PontoSerieIbge(periodo="2025", valor=1000.0)],
                        ultimoPeriodo="2025",
                        ultimoValor=1000.0,
                    ),
                    IndicadorIbge(
                        id="VALOR_PRODUCAO",
                        nomeOficial="Valor da produção",
                        codigoVariavelSidra=215,
                        unidade="Mil Reais",
                        pontos=[PontoSerieIbge(periodo="2025", valor=2150.0)],
                        ultimoPeriodo="2025",
                        ultimoValor=2150.0,
                    ),
                ],
            )

    svc = CotacaoMultiFonteService(sidra_service=_FakeSidraService())

    # 1. Consulta PR com núcleo Cascavel selecionado: combina Núcleo, Média PR, Extremos PR, PAM/IBGE e fontes institucionais
    res_pr = await svc.consultar(produto="soja", uf="PR", praca="Cascavel", incluir_ibge=True)
    assert res_pr.uf == "PR"
    assert len(res_pr.itens) == 1
    item_pr = res_pr.itens[0]
    assert item_pr.id == "soja"
    assert item_pr.resumo.fontes_com_preco_ativo >= 4
    assert item_pr.resumo.valor_recomendado_regiao == pytest.approx(132.98)
    assert "Cascavel" in (item_pr.resumo.fonte_recomendada_regiao or "")
    assert item_pr.resumo.valor_minimo is not None
    assert item_pr.resumo.valor_maximo is not None
    assert item_pr.resumo.valor_medio is not None
    assert item_pr.resumo.dispersao_pct is not None and item_pr.resumo.dispersao_pct > 0

    # 2. Consulta MT (fora do PR): converte PAM/IBGE (2150 mil R$ / 1000 t = R$ 2,15/kg * 60 kg = R$ 129,00/saca)
    res_mt = await svc.consultar(produto="soja", uf="MT", incluir_ibge=True)
    item_mt = res_mt.itens[0]
    ibge_fonte = next(f for f in item_mt.fontes if f.sigla_fonte == "IBGE/SIDRA (PAM)")
    assert ibge_fonte.valor == pytest.approx(129.0)
    assert item_mt.resumo.valor_recomendado_regiao == pytest.approx(129.0)


@pytest.mark.asyncio
async def test_cotacoes_regionais_multiplas_fontes_por_regiao_e_media_consenso(db_session: AsyncSession):
    tenant_id = uuid.uuid4()
    faz_id = uuid.uuid4()
    db_session.add_all([
        Tenant(id=tenant_id, nome="Grupo MultiFonte", slug="grupo-mf", documento="88888888000108"),
        UnidadeProdutiva(id=faz_id, tenant_id=tenant_id, nome="Fazenda Oeste PR", uf="PR", municipio="Cascavel"),
    ])
    await db_session.commit()

    svc = CotacaoRegionalService(db_session, tenant_id)

    # Cadastra 2 cooperativas distintas para SOJA na mesma fazenda
    await svc.salvar_cotacao_regional(
        "SOJA",
        CotacaoRegionalUpsertRequest(
            valor=136.0,
            data_referencia="2026-11-21",
            praca="Cascavel/PR",
            fonte="Coamo",
            escopo="FAZENDA",
            unidade_produtiva_id=faz_id,
        ),
    )
    res_segunda = await svc.salvar_cotacao_regional(
        "SOJA",
        CotacaoRegionalUpsertRequest(
            valor=138.0,
            data_referencia="2026-11-21",
            praca="Cascavel/PR",
            fonte="C.Vale",
            escopo="FAZENDA",
            unidade_produtiva_id=faz_id,
            modo_consolidacao="MEDIA_FONTES",
        ),
    )
    await db_session.commit()

    # Com modo_consolidacao="MEDIA_FONTES", o valor_efetivo da fazenda passa a ser a média das fontes locais (136 e 138 = 137.0)
    assert res_segunda.valor_efetivo == pytest.approx(137.0)
    assert res_segunda.total_fontes_ativas >= 3  # Coamo, C.Vale + DERAL
    assert res_segunda.valor_minimo_fontes is not None
    assert res_segunda.valor_medio_fontes is not None
    assert res_segunda.valor_maximo_fontes is not None
    assert res_segunda.dispersao_fontes_pct is not None
    nomes_fontes = {f.fonte for f in res_segunda.fontes_comparadas}
    assert "Coamo" in nomes_fontes
    assert "C.Vale" in nomes_fontes



