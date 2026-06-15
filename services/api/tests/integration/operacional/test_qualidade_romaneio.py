import pytest
from httpx import AsyncClient
from sqlalchemy import select
from uuid import UUID, uuid4

@pytest.mark.asyncio
async def test_aplicar_laudo_em_romaneio_desconto_idempotente(client: AsyncClient, token_operacional: str, token_admin: str):
    from tests.integration.conftest import TENANT_ID, FAZENDA_ID, TALHAO_ID
    
    h_op = {
        "Authorization": f"Bearer {token_operacional}",
        "X-Tenant-ID": str(TENANT_ID),
        "X-Fazenda-ID": str(FAZENDA_ID)
    }
    
    from agricola.safras.models import Safra
    from agricola.romaneios.models import RomaneioColheita
    from core.database import async_session_maker
    import datetime

    safra_id = uuid4()
    romaneio_id = uuid4()

    async with async_session_maker() as session:
        nova_safra = Safra(
            id=safra_id,
            tenant_id=TENANT_ID,
            ano_safra="2025",
            status="PLANEJAMENTO"
        )
        session.add(nova_safra)
        await session.flush()
        
        novo_romaneio = RomaneioColheita(
            id=romaneio_id,
            tenant_id=TENANT_ID,
            safra_id=safra_id,
            talhao_id=TALHAO_ID,
            data_colheita=datetime.date(2025, 5, 15),
            peso_bruto_kg=10000.0,
            tara_kg=500.0,
            umidade_pct=14.0,
            impureza_pct=1.0,
            peso_liquido_padrao_kg=9500.0,
            peso_liquido_comercial_kg=9500.0
        )
        session.add(novo_romaneio)
        await session.commit()
    
    peso_liquido_padrao = 9500.0

    proto_res = await client.post("/api/v1/qualidade/protocolos", json={
        "nome": "Protocolo Desconto",
        "criterios": [
            {
                "nome": "Avariados",
                "tipo_dado": "NUMERIC",
                "regra_ajuste_json": {
                    "type": "DISCOUNT_WEIGHT",
                    "trigger": "ABOVE_STANDARD",
                    "standard_value": 8.0,
                    "rate_per_unit": 10.0
                }
            }
        ]
    }, headers=h_op)
    proto_id = proto_res.json()["id"]
    crit_id = proto_res.json()["criterios"][0]["id"]
    
    laudo_res = await client.post("/api/v1/qualidade/laudos", json={
        "protocolo_id": str(proto_id),
        "romaneio_id": str(romaneio_id),
        "status": "RASCUNHO",
        "resultados": [{"criterio_id": str(crit_id), "valor_numerico": 10.0}]
    }, headers=h_op)
    laudo_id = laudo_res.json()["id"]
    
    await client.patch(f"/api/v1/qualidade/laudos/{laudo_id}/status", json={"status": "APROVADO"}, headers=h_op)
    
    await client.post(f"/api/v1/qualidade/laudos/{laudo_id}/calcular-ajustes", headers=h_op)
    
    apply_res = await client.post(f"/api/v1/qualidade/laudos/{laudo_id}/aplicar-romaneio", headers=h_op)
    assert apply_res.status_code == 200
    apply_data = apply_res.json()
    assert apply_data["romaneio_id"] == str(romaneio_id)
    assert apply_data["peso_desconto_qualidade_kg"] == 20.0
    assert apply_data["status_qualidade"] == "APROVADO"
    assert apply_data["peso_liquido_comercial_kg"] == (peso_liquido_padrao - 20.0)
    
    apply_res_2 = await client.post(f"/api/v1/qualidade/laudos/{laudo_id}/aplicar-romaneio", headers=h_op)
    assert apply_res_2.status_code == 200
    assert apply_res_2.json()["peso_desconto_qualidade_kg"] == 20.0
    assert apply_res_2.json()["peso_liquido_comercial_kg"] == (peso_liquido_padrao - 20.0)

@pytest.mark.asyncio
async def test_aplicar_laudo_rejeitado(client: AsyncClient, token_operacional: str, token_admin: str):
    from tests.integration.conftest import TENANT_ID, FAZENDA_ID, TALHAO_ID
    
    h_op = {
        "Authorization": f"Bearer {token_operacional}",
        "X-Tenant-ID": str(TENANT_ID),
        "X-Fazenda-ID": str(FAZENDA_ID)
    }

    from agricola.safras.models import Safra
    from agricola.romaneios.models import RomaneioColheita
    from core.database import async_session_maker
    import datetime

    safra_id = uuid4()
    romaneio_id = uuid4()

    async with async_session_maker() as session:
        nova_safra = Safra(
            id=safra_id,
            tenant_id=TENANT_ID,
            ano_safra="2025",
            status="PLANEJAMENTO"
        )
        session.add(nova_safra)
        await session.flush()
        
        novo_romaneio = RomaneioColheita(
            id=romaneio_id,
            tenant_id=TENANT_ID,
            safra_id=safra_id,
            talhao_id=TALHAO_ID,
            data_colheita=datetime.date(2025, 5, 15),
            peso_bruto_kg=1000.0,
            tara_kg=0.0,
            peso_liquido_padrao_kg=1000.0,
            peso_liquido_comercial_kg=1000.0
        )
        session.add(novo_romaneio)
        await session.commit()

    proto_res = await client.post("/api/v1/qualidade/protocolos", json={
        "nome": "Protocolo Rejeicao",
        "criterios": [
            {
                "nome": "Umidade Max",
                "tipo_dado": "NUMERIC",
                "regra_ajuste_json": {
                    "type": "REJECTION",
                    "trigger": "ABOVE_STANDARD",
                    "standard_value": 20.0
                }
            }
        ]
    }, headers=h_op)
    proto_id = proto_res.json()["id"]
    crit_id = proto_res.json()["criterios"][0]["id"]
    
    laudo_res = await client.post("/api/v1/qualidade/laudos", json={
        "protocolo_id": str(proto_id),
        "romaneio_id": str(romaneio_id),
        "status": "RASCUNHO",
        "resultados": [{"criterio_id": str(crit_id), "valor_numerico": 25.0}]
    }, headers=h_op)
    laudo_id = laudo_res.json()["id"]
    
    res_apply_fail = await client.post(f"/api/v1/qualidade/laudos/{laudo_id}/aplicar-romaneio", headers=h_op)
    assert res_apply_fail.status_code == 400
    assert "APROVADOS" in res_apply_fail.json()["detail"]
    
    await client.patch(f"/api/v1/qualidade/laudos/{laudo_id}/status", json={"status": "APROVADO"}, headers=h_op)
    
    await client.post(f"/api/v1/qualidade/laudos/{laudo_id}/calcular-ajustes", headers=h_op)
    
    apply_res = await client.post(f"/api/v1/qualidade/laudos/{laudo_id}/aplicar-romaneio", headers=h_op)
    assert apply_res.status_code == 200
    assert apply_res.json()["status_qualidade"] == "REPROVADO"

@pytest.mark.asyncio
async def test_discount_financial_informativo(client: AsyncClient, token_operacional: str):
    from tests.integration.conftest import TENANT_ID, FAZENDA_ID, TALHAO_ID
    
    h_op = {
        "Authorization": f"Bearer {token_operacional}",
        "X-Tenant-ID": str(TENANT_ID),
        "X-Fazenda-ID": str(FAZENDA_ID)
    }

    from agricola.safras.models import Safra
    from agricola.romaneios.models import RomaneioColheita
    from core.database import async_session_maker
    import datetime

    safra_id = uuid4()
    romaneio_id = uuid4()

    async with async_session_maker() as session:
        nova_safra = Safra(id=safra_id, tenant_id=TENANT_ID, ano_safra="2025", status="PLANEJAMENTO")
        session.add(nova_safra)
        await session.flush()
        novo_romaneio = RomaneioColheita(
            id=romaneio_id, tenant_id=TENANT_ID, safra_id=safra_id, talhao_id=TALHAO_ID,
            data_colheita=datetime.date(2025, 5, 15), peso_bruto_kg=5000.0, tara_kg=0.0,
            peso_liquido_padrao_kg=5000.0, peso_liquido_comercial_kg=5000.0
        )
        session.add(novo_romaneio)
        await session.commit()

    proto_res = await client.post("/api/v1/qualidade/protocolos", json={
        "nome": "Proto Financeiro",
        "criterios": [
            {
                "nome": "Bonus",
                "tipo_dado": "NUMERIC",
                "regra_ajuste_json": {"type": "DISCOUNT_FINANCIAL", "trigger": "ABOVE_STANDARD", "standard_value": 5.0, "rate_per_unit": 100.0}
            }
        ]
    }, headers=h_op)
    proto_id = proto_res.json()["id"]
    crit_id = proto_res.json()["criterios"][0]["id"]
    
    laudo_res = await client.post("/api/v1/qualidade/laudos", json={
        "protocolo_id": str(proto_id),
        "romaneio_id": str(romaneio_id),
        "status": "RASCUNHO",
        "resultados": [{"criterio_id": str(crit_id), "valor_numerico": 6.0}]
    }, headers=h_op)
    laudo_id = laudo_res.json()["id"]
    
    await client.patch(f"/api/v1/qualidade/laudos/{laudo_id}/status", json={"status": "APROVADO"}, headers=h_op)
    await client.post(f"/api/v1/qualidade/laudos/{laudo_id}/calcular-ajustes", headers=h_op)
    
    apply_res = await client.post(f"/api/v1/qualidade/laudos/{laudo_id}/aplicar-romaneio", headers=h_op)
    assert apply_res.status_code == 200
    assert apply_res.json()["peso_desconto_qualidade_kg"] == 0.0
    assert apply_res.json()["peso_liquido_comercial_kg"] == 5000.0

@pytest.mark.asyncio
async def test_laudo_cross_tenant_bloqueio(client: AsyncClient, token_operacional: str):
    from tests.integration.conftest import TENANT_ID, FAZENDA_ID, TALHAO_ID, _gerar_token
    import uuid

    h1 = {"Authorization": f"Bearer {token_operacional}"}
    proto_res = await client.post("/api/v1/qualidade/protocolos", json={
        "nome": "Proto T1",
        "criterios": [{"nome": "Crit", "tipo_dado": "NUMERIC", "regra_ajuste_json": {"type": "DISCOUNT_WEIGHT", "trigger": "ABOVE_STANDARD", "standard_value": 10.0, "rate_per_unit": 1.0}}]
    }, headers=h1)
    proto_id = proto_res.json()["id"]
    crit_id = proto_res.json()["criterios"][0]["id"]
    laudo_res = await client.post("/api/v1/qualidade/laudos", json={
        "protocolo_id": str(proto_id),
        "status": "RASCUNHO",
        "resultados": [{"criterio_id": str(crit_id), "valor_numerico": 12.0}]
    }, headers=h1)
    laudo_id = laudo_res.json()["id"]
    await client.patch(f"/api/v1/qualidade/laudos/{laudo_id}/status", json={"status": "APROVADO"}, headers=h1)

    tenant_2 = uuid.uuid4()
    token_t2 = _gerar_token(tenant_2, ["CORE"])
    h2 = {"Authorization": f"Bearer {token_t2}"}
    
    res_cross = await client.post(f"/api/v1/qualidade/laudos/{laudo_id}/aplicar-romaneio", headers=h2)
    assert res_cross.status_code in (403, 404)

@pytest.mark.asyncio
async def test_auditoria_registrada(client: AsyncClient, token_operacional: str):
    from tests.integration.conftest import TENANT_ID, FAZENDA_ID, TALHAO_ID
    from core.database import async_session_maker
    from sqlalchemy import select
    from core.models.tenant_audit_log import TenantAuditLog

    h_op = {"Authorization": f"Bearer {token_operacional}", "X-Tenant-ID": str(TENANT_ID), "X-Fazenda-ID": str(FAZENDA_ID)}

    safra_id = uuid4()
    romaneio_id = uuid4()

    async with async_session_maker() as session:
        from agricola.safras.models import Safra
        from agricola.romaneios.models import RomaneioColheita
        import datetime
        nova_safra = Safra(id=safra_id, tenant_id=TENANT_ID, ano_safra="2025", status="PLANEJAMENTO")
        session.add(nova_safra)
        await session.flush()
        novo_romaneio = RomaneioColheita(id=romaneio_id, tenant_id=TENANT_ID, safra_id=safra_id, talhao_id=TALHAO_ID,
            data_colheita=datetime.date(2025, 5, 15), peso_bruto_kg=5000.0, tara_kg=0.0,
            peso_liquido_padrao_kg=5000.0, peso_liquido_comercial_kg=5000.0)
        session.add(novo_romaneio)
        await session.commit()

    proto_res = await client.post("/api/v1/qualidade/protocolos", json={
        "nome": "Proto Audit",
        "criterios": [{"nome": "Crit", "tipo_dado": "NUMERIC", "regra_ajuste_json": {"type": "DISCOUNT_WEIGHT", "trigger": "ABOVE_STANDARD", "standard_value": 10.0, "rate_per_unit": 1.0}}]
    }, headers=h_op)
    proto_id = proto_res.json()["id"]
    crit_id = proto_res.json()["criterios"][0]["id"]
    laudo_res = await client.post("/api/v1/qualidade/laudos", json={
        "protocolo_id": str(proto_id), "romaneio_id": str(romaneio_id),
        "status": "RASCUNHO", "resultados": [{"criterio_id": str(crit_id), "valor_numerico": 12.0}]
    }, headers=h_op)
    laudo_id = laudo_res.json()["id"]
    await client.patch(f"/api/v1/qualidade/laudos/{laudo_id}/status", json={"status": "APROVADO"}, headers=h_op)
    await client.post(f"/api/v1/qualidade/laudos/{laudo_id}/calcular-ajustes", headers=h_op)
    await client.post(f"/api/v1/qualidade/laudos/{laudo_id}/aplicar-romaneio", headers=h_op)

    async with async_session_maker() as session:
        stmt = select(TenantAuditLog).where(
            TenantAuditLog.resource == "romaneios_colheita",
            TenantAuditLog.resource_id == romaneio_id
        )
        audit = (await session.execute(stmt)).scalar_one_or_none()
        assert audit is not None


@pytest.mark.asyncio
async def test_aplicar_laudo_sincroniza_produto_colhido(client: AsyncClient, token_operacional: str):
    from tests.integration.conftest import TENANT_ID, FAZENDA_ID, TALHAO_ID
    from core.database import async_session_maker
    from agricola.safras.models import Safra
    from agricola.romaneios.models import RomaneioColheita
    from agricola.colheita.models import ProdutoColhido
    from core.cadastros.commodities.models import Commodity
    from core.models.tenant_audit_log import TenantAuditLog
    import datetime

    h_op = {
        "Authorization": f"Bearer {token_operacional}",
        "X-Tenant-ID": str(TENANT_ID),
        "X-Fazenda-ID": str(FAZENDA_ID),
    }

    safra_id = uuid4()
    romaneio_id = uuid4()
    commodity_id = uuid4()
    produto_colhido_id = uuid4()

    async with async_session_maker() as session:
        session.add(
            Commodity(
                id=commodity_id,
                tenant_id=TENANT_ID,
                nome=f"Café Teste {commodity_id.hex[:8]}",
                codigo=f"CAFE-TESTE-{commodity_id.hex[:8]}",
                tipo="AGRICOLA",
                unidade_padrao="SACA_60KG",
                peso_unidade=60.0,
                ativo=True,
            )
        )
        session.add(Safra(id=safra_id, tenant_id=TENANT_ID, ano_safra="2025", status="PLANEJAMENTO"))
        await session.flush()
        session.add(
            RomaneioColheita(
                id=romaneio_id,
                tenant_id=TENANT_ID,
                safra_id=safra_id,
                talhao_id=TALHAO_ID,
                commodity_id=commodity_id,
                data_colheita=datetime.date(2025, 5, 15),
                peso_bruto_kg=10000.0,
                tara_kg=500.0,
                peso_liquido_kg=9500.0,
                peso_liquido_padrao_kg=9400.0,
            )
        )
        await session.flush()
        session.add(
            ProdutoColhido(
                id=produto_colhido_id,
                tenant_id=TENANT_ID,
                safra_id=safra_id,
                talhao_id=TALHAO_ID,
                romaneio_id=romaneio_id,
                commodity_id=commodity_id,
                quantidade=156.667,
                unidade="SACA_60KG",
                peso_liquido_kg=9400.0,
                data_entrada=datetime.date(2025, 5, 15),
                status="ARMAZENADO",
            )
        )
        await session.commit()

    proto_res = await client.post("/api/v1/qualidade/protocolos", json={
        "nome": "Protocolo Sync Produto",
        "criterios": [
            {
                "nome": "Avariados",
                "tipo_dado": "NUMERIC",
                "regra_ajuste_json": {
                    "type": "DISCOUNT_WEIGHT",
                    "trigger": "ABOVE_STANDARD",
                    "standard_value": 8.0,
                    "rate_per_unit": 10.0,
                },
            }
        ],
    }, headers=h_op)
    crit_id = proto_res.json()["criterios"][0]["id"]
    proto_id = proto_res.json()["id"]

    laudo_res = await client.post("/api/v1/qualidade/laudos", json={
        "protocolo_id": str(proto_id),
        "romaneio_id": str(romaneio_id),
        "status": "RASCUNHO",
        "resultados": [{"criterio_id": str(crit_id), "valor_numerico": 10.0}],
    }, headers=h_op)
    laudo_id = laudo_res.json()["id"]

    await client.patch(f"/api/v1/qualidade/laudos/{laudo_id}/status", json={"status": "APROVADO"}, headers=h_op)
    await client.post(f"/api/v1/qualidade/laudos/{laudo_id}/calcular-ajustes", headers=h_op)
    apply_res = await client.post(f"/api/v1/qualidade/laudos/{laudo_id}/aplicar-romaneio", headers=h_op)

    assert apply_res.status_code == 200
    assert apply_res.json()["peso_liquido_comercial_kg"] == 9380.0

    async with async_session_maker() as session:
        produto = await session.get(ProdutoColhido, produto_colhido_id)
        assert produto is not None
        assert produto.qualidade_laudo_id == UUID(laudo_id)
        assert produto.qualidade_status == "APROVADO"
        assert float(produto.peso_desconto_qualidade_kg) == 20.0
        assert float(produto.peso_liquido_comercial_kg) == 9380.0

        audit = (
            await session.execute(
                select(TenantAuditLog).where(
                    TenantAuditLog.tenant_id == TENANT_ID,
                    TenantAuditLog.resource == "agricola_produtos_colhidos",
                    TenantAuditLog.resource_id == produto_colhido_id,
                    TenantAuditLog.action == "sync_quality_pc",
                )
            )
        ).scalar_one_or_none()
        assert audit is not None
