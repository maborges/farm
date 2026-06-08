import uuid
import pytest
from datetime import date, datetime
from sqlalchemy import text
from core.exceptions import BusinessRuleError, EntityNotFoundError
from agricola.rastreabilidade.models import CadernoLoteComercial, CertificacaoPropriedade
from agricola.rastreabilidade.schemas import LoteComercialCreate
from agricola.rastreabilidade.service import LoteComercialService
from agricola.colheita.models import ProdutoColhido
from agricola.beneficiamento.models import LoteBeneficiamento
from financeiro.comercializacao.models import ComercializacaoCommodity
from core.cadastros.commodities.models import Commodity
from core.cadastros.propriedades.models import AreaRural
from core.models.unidade_produtiva import UnidadeProdutiva
from agricola.caderno.models import CadernoCampoEntrada, CadernoCampoFoto

# Helper functions to create required parent records in DB for the test
async def _criar_entidades_base(session, tenant_id, unidade_produtiva_id, talhao_id):
    # Ensure safra exists
    res_safra = await session.execute(
        text("SELECT id FROM safras WHERE tenant_id = :tenant_id AND ano_safra = '2025/26' AND cultura = 'Café'"),
        {"tenant_id": tenant_id}
    )
    row_safra = res_safra.fetchone()
    if row_safra:
        safra_id = row_safra[0]
    else:
        safra_id = uuid.uuid4()
        await session.execute(
            text(
                "INSERT INTO safras (id, tenant_id, ano_safra, cultura, status, created_at, updated_at) "
                "VALUES (:id, :tenant_id, '2025/26', 'Café', 'PLANEJADA', NOW(), NOW())"
            ),
            {"id": safra_id, "tenant_id": tenant_id}
        )
    # Ensure commodity exists
    res_comm = await session.execute(
        text("SELECT id FROM cadastros_commodities WHERE tenant_id = :tenant_id AND nome = 'Café Arábica'"),
        {"tenant_id": tenant_id}
    )
    row_comm = res_comm.fetchone()
    if row_comm:
        commodity_id = row_comm[0]
    else:
        commodity_id = uuid.uuid4()
        commodity_code = f"CAFE-{uuid.uuid4().hex[:8]}"
        await session.execute(
            text(
                "INSERT INTO cadastros_commodities (id, tenant_id, nome, codigo, tipo, unidade_padrao, ativo, created_at, updated_at) "
                "VALUES (:id, :tenant_id, 'Café Arábica', :codigo, 'AGRICOLA', 'SC', true, NOW(), NOW())"
            ),
            {"id": commodity_id, "tenant_id": tenant_id, "codigo": commodity_code}
        )
    # Ensure comprador exists (cadastros_pessoas)
    comprador_id = uuid.uuid4()
    await session.execute(
        text(
            "INSERT INTO cadastros_pessoas (id, tenant_id, nome_exibicao, tipo, base_legal, ativo, created_at, updated_at) "
            "VALUES (:id, :tenant_id, 'Comprador Teste', 'PJ', 'CONTRATO', true, NOW(), NOW())"
        ),
        {"id": comprador_id, "tenant_id": tenant_id}
    )
    # Ensure Comercializacao exists
    comercializacao_id = uuid.uuid4()
    await session.execute(
        text(
            "INSERT INTO financeiro_comercializacoes (id, tenant_id, commodity_id, comprador_id, quantidade, unidade, preco_unitario, valor_total, status, created_at, updated_at) "
            "VALUES (:id, :tenant_id, :commodity_id, :comprador_id, 10.0, 'SC', 100.0, 1000.0, 'RASCUNHO', NOW(), NOW())"
        ),
        {
            "id": comercializacao_id,
            "tenant_id": tenant_id,
            "commodity_id": commodity_id,
            "comprador_id": comprador_id
        }
    )
    await session.commit()
    return safra_id, commodity_id, comercializacao_id

@pytest.mark.asyncio
async def test_criar_lote_comercial_com_produto_colhido(session, tenant_id, unidade_produtiva_id, talhao_id):
    safra_id, commodity_id, comercializacao_id = await _criar_entidades_base(session, tenant_id, unidade_produtiva_id, talhao_id)
    
    # Criar ProdutoColhido
    prod_colhido_id = uuid.uuid4()
    prod_colhido = ProdutoColhido(
        id=prod_colhido_id,
        tenant_id=tenant_id,
        safra_id=safra_id,
        talhao_id=talhao_id,
        commodity_id=commodity_id,
        quantidade=100.0,
        unidade="SC",
        peso_liquido_kg=6000.0,
        data_entrada=date.today(),
        status="ARMAZENADO"
    )
    session.add(prod_colhido)
    await session.commit()
    
    svc = LoteComercialService(session, tenant_id)
    dados = LoteComercialCreate(
        comercializacao_id=comercializacao_id,
        codigo_lote="LOT-PROD-COLHIDO-01",
        peso_liquido_kg=1000.0,
        quantidade_volumes=10,
        produto_colhido_id=prod_colhido_id
    )
    
    lote = await svc.criar_lote_comercial(dados)
    assert lote.codigo_lote == "LOT-PROD-COLHIDO-01"
    assert lote.peso_liquido_kg == 1000.0
    assert lote.status == "RASCUNHO"
    assert lote.qr_code_token is not None
    assert len(lote.qr_code_token) == 64

@pytest.mark.asyncio
async def test_criar_lote_comercial_com_lote_beneficiamento(session, tenant_id, unidade_produtiva_id, talhao_id):
    safra_id, commodity_id, comercializacao_id = await _criar_entidades_base(session, tenant_id, unidade_produtiva_id, talhao_id)
    
    # Criar LoteBeneficiamento
    lote_benef_id = uuid.uuid4()
    lote_benef = LoteBeneficiamento(
        id=lote_benef_id,
        tenant_id=tenant_id,
        safra_id=safra_id,
        talhao_id=talhao_id,
        numero_lote="BEN-001",
        metodo="NATURAL",
        data_entrada=date.today(),
        peso_entrada_kg=5000.0,
        peso_saida_kg=4000.0,
        status="RECEBIMENTO"
    )
    session.add(lote_benef)
    await session.commit()
    
    svc = LoteComercialService(session, tenant_id)
    dados = LoteComercialCreate(
        comercializacao_id=comercializacao_id,
        codigo_lote="LOT-BENEF-01",
        peso_liquido_kg=1500.0,
        quantidade_volumes=25,
        lote_beneficiamento_id=lote_benef_id
    )
    
    lote = await svc.criar_lote_comercial(dados)
    assert lote.codigo_lote == "LOT-BENEF-01"
    assert lote.peso_liquido_kg == 1500.0
    assert lote.status == "RASCUNHO"
    assert lote.lote_beneficiamento_id == lote_benef_id

@pytest.mark.asyncio
async def test_criar_lote_comercial_exige_origem_fisica(session, tenant_id, unidade_produtiva_id, talhao_id):
    safra_id, commodity_id, comercializacao_id = await _criar_entidades_base(session, tenant_id, unidade_produtiva_id, talhao_id)
    
    svc = LoteComercialService(session, tenant_id)
    
    # Sem origem
    dados_sem_origem = LoteComercialCreate(
        comercializacao_id=comercializacao_id,
        codigo_lote="LOT-SEM-ORIGEM",
        peso_liquido_kg=1000.0,
        quantidade_volumes=10
    )
    with pytest.raises(BusinessRuleError, match="Deve ser informado pelo menos um produto colhido ou um lote de beneficiamento"):
        await svc.criar_lote_comercial(dados_sem_origem)

    # Dupla origem
    dados_dupla_origem = LoteComercialCreate(
        comercializacao_id=comercializacao_id,
        codigo_lote="LOT-DUPLA-ORIGEM",
        peso_liquido_kg=1000.0,
        quantidade_volumes=10,
        produto_colhido_id=uuid.uuid4(),
        lote_beneficiamento_id=uuid.uuid4()
    )
    with pytest.raises(BusinessRuleError, match="Informe apenas o produto colhido ou o lote de beneficiamento"):
        await svc.criar_lote_comercial(dados_dupla_origem)

@pytest.mark.asyncio
async def test_gerar_snapshot_e_privacidade(session, tenant_id, unidade_produtiva_id, talhao_id):
    safra_id, commodity_id, comercializacao_id = await _criar_entidades_base(session, tenant_id, unidade_produtiva_id, talhao_id)
    
    prod_colhido_id = uuid.uuid4()
    prod_colhido = ProdutoColhido(
        id=prod_colhido_id,
        tenant_id=tenant_id,
        safra_id=safra_id,
        talhao_id=talhao_id,
        commodity_id=commodity_id,
        quantidade=100.0,
        unidade="SC",
        peso_liquido_kg=6000.0,
        data_entrada=date.today(),
        status="ARMAZENADO"
    )
    session.add(prod_colhido)
    await session.commit()
    
    # Criar eventos no Caderno de Campo com fotos
    entrada_id_publica = uuid.uuid4()
    entrada_publica = CadernoCampoEntrada(
        id=entrada_id_publica,
        tenant_id=tenant_id,
        safra_id=safra_id,
        talhao_id=talhao_id,
        tipo="PLANTIO",
        tipo_evento="Plantio de Lavoura",
        descricao="Plantio realizado",
        data_registro=date.today(),
        usuario_id=uuid.uuid4(),
        status_evento="CONSOLIDADO",
        origem_evento="MANUAL",
        origem_id=str(entrada_id_publica),
        origem_tecnica="MANUAL"
    )
    session.add(entrada_publica)
    
    foto_publica = CadernoCampoFoto(
        id=uuid.uuid4(),
        entrada_id=entrada_id_publica,
        url="https://s3.amazonaws.com/agrosaas/foto1.jpg",
        publica=True
    )
    foto_privada = CadernoCampoFoto(
        id=uuid.uuid4(),
        entrada_id=entrada_id_publica,
        url="https://s3.amazonaws.com/agrosaas/foto2_privada.jpg",
        publica=False
    )
    session.add(foto_publica)
    session.add(foto_privada)
    await session.commit()
    
    # Criar Certificação
    cert = CertificacaoPropriedade(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_produtiva_id,
        nome="GlobalGAP",
        data_emissao=datetime.utcnow(),
        data_validade=datetime.utcnow().date(),
        status="VALIDA",
        numero_registro="GG-123456"
    )
    session.add(cert)
    await session.commit()
    
    svc = LoteComercialService(session, tenant_id)
    dados = LoteComercialCreate(
        comercializacao_id=comercializacao_id,
        codigo_lote="LOT-SNAP-01",
        peso_liquido_kg=1000.0,
        quantidade_volumes=10,
        produto_colhido_id=prod_colhido_id
    )
    lote = await svc.criar_lote_comercial(dados)
    
    usuario_id = uuid.uuid4()
    await session.execute(
        text(
            "INSERT INTO usuarios (id, email, username, nome_completo, is_superuser, ativo, created_at, updated_at) "
            "VALUES (:id, :email, :username, 'Usuario Teste', false, true, NOW(), NOW())"
        ),
        {
            "id": usuario_id,
            "email": f"usuario-{uuid.uuid4().hex[:8]}@example.com",
            "username": f"user-{uuid.uuid4().hex[:8]}"
        }
    )
    await session.commit()

    lote_assinado = await svc.gerar_snapshot_passaporte(lote.id, usuario_id)
    
    assert lote_assinado.status == "ATIVO"
    assert lote_assinado.snapshot_json is not None
    assert lote_assinado.snapshot_hash is not None
    assert lote_assinado.assinado_por_usuario_id == usuario_id
    
    snapshot = lote_assinado.snapshot_json
    # Dados públicos inclusos
    assert snapshot["lote_codigo"] == "LOT-SNAP-01"
    assert snapshot["produto"] == "Café Arábica"
    assert snapshot["fazenda"] is not None
    assert len(snapshot["certificacoes"]) == 1
    assert snapshot["certificacoes"][0]["nome"] == "GlobalGAP"
    
    # Somente foto publica inclusa
    assert len(snapshot["fotos"]) == 1
    assert snapshot["fotos"][0]["url"] == "https://s3.amazonaws.com/agrosaas/foto1.jpg"
    
    # Dados privados omitidos
    assert "preco_unitario" not in snapshot
    assert "valor_total" not in snapshot
    assert "comprador_id" not in snapshot
    assert "usuario_id" not in snapshot
    assert "ip_dispositivo" not in snapshot

@pytest.mark.asyncio
async def test_lote_comercial_multi_tenant(session, tenant_id, unidade_produtiva_id, talhao_id):
    safra_id, commodity_id, comercializacao_id = await _criar_entidades_base(session, tenant_id, unidade_produtiva_id, talhao_id)
    
    # Criar Lote no tenant principal
    prod_colhido_id = uuid.uuid4()
    prod_colhido = ProdutoColhido(
        id=prod_colhido_id,
        tenant_id=tenant_id,
        safra_id=safra_id,
        talhao_id=talhao_id,
        commodity_id=commodity_id,
        quantidade=100.0,
        unidade="SC",
        peso_liquido_kg=6000.0,
        data_entrada=date.today(),
        status="ARMAZENADO"
    )
    session.add(prod_colhido)
    await session.commit()
    
    svc = LoteComercialService(session, tenant_id)
    dados = LoteComercialCreate(
        comercializacao_id=comercializacao_id,
        codigo_lote="LOT-TENANT-OK",
        peso_liquido_kg=1000.0,
        quantidade_volumes=10,
        produto_colhido_id=prod_colhido_id
    )
    lote = await svc.criar_lote_comercial(dados)
    
    # Acessar via outro tenant
    outro_tenant_id = uuid.uuid4()
    svc_outro = LoteComercialService(session, outro_tenant_id)
    
    with pytest.raises(EntityNotFoundError):
        await svc_outro.get_or_fail(lote.id)
