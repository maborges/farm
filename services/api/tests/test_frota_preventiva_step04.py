"""
Testes para o módulo de Manutenção Preventiva Inteligente (Step 04).

Cobre:
1. Criação de planos de manutenção preventiva com checklist e categoria.
2. Atualização e cálculo de status do plano (EM_DIA, PROXIMO_VENCIMENTO, VENCIDO).
3. Abertura de OS preventiva com cópia do checklist e mudança do status do maquinário para EM_MANUTENCAO.
4. Fechamento de OS preventiva com retorno a ATIVO, registro de histórico e apropriação financeira/econômica.
5. Painel de Frota com MTBF e proporção de custos preventivos vs corretivos.
"""
import uuid
from datetime import datetime, date, timedelta, timezone
import pytest
from sqlalchemy import text
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.cadastros.equipamentos.models import Equipamento
from operacional.models.frota import PlanoManutencao, OrdemServico, RegistroManutencao, ItemOrdemServico
from operacional.schemas.frota import PlanoManutencaoCreate, OrdemServicoUpdate
from operacional.services.frota_service import FrotaService
from operacional.services.frota_manutencao_preventiva_service import FrotaManutencaoPreventivaService
from operacional.services.frota_dashboard_service import FrotaDashboardService
from financeiro.models.despesa import Despesa
from financeiro.models.plano_conta import PlanoConta
from agricola.safras.models import Safra
from agricola.cultivos.models import Cultivo


# ---------------------------------------------------------------------------
# Setup Fixture
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
async def setup_db_schema(session: AsyncSession):
    """Garante de forma resiliente que as colunas necessárias existam no banco local de testes."""
    try:
        await session.execute(text("ALTER TABLE frota_planos_manutencao ADD COLUMN IF NOT EXISTS checklist_preventivo text"))
        await session.execute(text("ALTER TABLE frota_planos_manutencao ADD COLUMN IF NOT EXISTS categoria varchar(100)"))
        await session.execute(text("ALTER TABLE frota_ordens_servico ADD COLUMN IF NOT EXISTS checklist_aplicado text"))
        await session.commit()
    except Exception:
        await session.rollback()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _setup_tenant_completo(session: AsyncSession, tenant_id: uuid.UUID) -> uuid.UUID:
    """Configura um ambiente multi-tenant isolado completo para evitar poluição de outros testes."""
    # 1. Cria tenant
    await session.execute(
        text(
            "INSERT INTO tenants (id, nome, documento, ativo, "
            "storage_usado_mb, storage_limite_mb, idioma_padrao, created_at, updated_at) "
            "VALUES (:id, :nome, :doc, true, 0, 10240, 'pt-BR', now(), now()) "
            "ON CONFLICT DO NOTHING"
        ),
        {"id": str(tenant_id), "nome": "Tenant Teste Dinamico", "doc": str(tenant_id)[:11]},
    )

    # 2. Cria plano base se não existir
    plano_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    await session.execute(
        text(
            "INSERT INTO planos_assinatura (id, nome, modulos_inclusos, limite_usuarios_minimo, limite_usuarios_maximo, "
            "preco_mensal, preco_anual, max_fazendas, max_categorias_plano, tem_trial, dias_trial, is_free, "
            "destaque, ordem, ativo, disponivel_site, disponivel_crm, created_at) "
            "VALUES (:id, 'Plano Teste', CAST('[\"CORE\",\"A1_PLANEJAMENTO\"]' AS json), 1, 5, 0, 0, -1, -1, false, 15, false, false, 0, true, false, true, now()) "
            "ON CONFLICT DO NOTHING"
        ),
        {"id": str(plano_id)},
    )

    # 3. Cria assinatura principal
    await session.execute(
        text(
            "INSERT INTO assinaturas_tenant "
            "(id, tenant_id, plano_id, tipo_assinatura, ciclo_pagamento, usuarios_contratados, "
            "status, grace_period_days, created_at, updated_at) "
            "VALUES (:assinatura_id, :tenant_id, :plano_id, 'TENANT', 'MENSAL', 5, "
            "'ATIVA', 3, now(), now()) "
            "ON CONFLICT (tenant_id, tipo_assinatura) DO UPDATE SET status = 'ATIVA'"
        ),
        {
            "assinatura_id": str(uuid.uuid4()),
            "tenant_id": str(tenant_id),
            "plano_id": str(plano_id),
        },
    )

    # 4. Cria unidade produtiva
    fazenda_id = uuid.uuid4()
    await session.execute(text(
        "INSERT INTO unidades_produtivas (id, tenant_id, nome, ativo, created_at, updated_at) "
        "VALUES (:id, :tenant_id, 'Fazenda Teste Dinamico', true, now(), now()) "
    ), {"id": str(fazenda_id), "tenant_id": str(tenant_id)})
    
    await session.commit()
    return fazenda_id


async def _criar_equipamento(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    unidade_produtiva_id: uuid.UUID | None = None,
    status: str = "ATIVO",
) -> Equipamento:
    equipamento = Equipamento(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_produtiva_id,
        nome=f"Colheitadeira-S04-{uuid.uuid4().hex[:6]}",
        tipo="COLHEITADEIRA",
        combustivel="DIESEL",
        status=status,
        horimetro_atual=500.0,
        km_atual=1000.0,
        ativo=True,
    )
    session.add(equipamento)
    await session.commit()
    await session.refresh(equipamento)
    return equipamento


async def _criar_plano_conta(session: AsyncSession, tenant_id: uuid.UUID) -> uuid.UUID:
    plano = PlanoConta(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        codigo="3.01.004",
        nome="Custeio de Frota",
        tipo="DESPESA",
        categoria_rfb="CUSTEIO",
        natureza="ANALITICA",
        ativo=True,
    )
    session.add(plano)
    await session.commit()
    return plano.id


# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------

class TestFrotaPreventivaStep04:

    @pytest.mark.asyncio
    async def test_criar_plano_preventivo_com_categoria_e_checklist(
        self, session: AsyncSession, tenant_id: uuid.UUID
    ):
        """1. Criar plano de manutenção preventivo inteligente com categoria e checklist."""
        tid = tenant_id
        equipamento = await _criar_equipamento(session, tid)

        dados_plano = PlanoManutencaoCreate(
            maquinario_id=equipamento.id,
            descricao="Revisão Periódica dos 500h",
            frequencia_dias=90,
            frequencia_horas=250.0,
            frequencia_km=None,
            checklist_preventivo="1. Trocar óleo motor\n2. Limpar filtros\n3. Reapertar parafusos",
            categoria="Mecânica Geral",
        )

        frota_svc = FrotaService(session, tid)
        plano = await frota_svc.criar_plano_manutencao(dados_plano)

        # Assertions
        assert plano.id is not None
        assert plano.tenant_id == tid
        assert plano.equipamento_id == equipamento.id
        assert plano.descricao == "Revisão Periódica dos 500h"
        assert plano.frequencia_dias == 90
        assert plano.frequencia_horas == 250.0
        assert plano.checklist_preventivo == "1. Trocar óleo motor\n2. Limpar filtros\n3. Reapertar parafusos"
        assert plano.categoria == "Mecânica Geral"

    @pytest.mark.asyncio
    async def test_regras_status_vencimento_preventiva(
        self, session: AsyncSession
    ):
        """2. Validar o cálculo de proximidade e vencimento das regras preventivas."""
        tid = uuid.uuid4()
        up_id = await _setup_tenant_completo(session, tid)
        equipamento = await _criar_equipamento(session, tid, unidade_produtiva_id=up_id)

        # Plano com frequencia de 250h. Como horímetro atual = 500.0, e último registro foi 0.0:
        # Faltam 250h. Como 500.0 > 250.0, o plano deve estar VENCIDO.
        plano = PlanoManutencao(
            id=uuid.uuid4(),
            tenant_id=tid,
            equipamento_id=equipamento.id,
            descricao="Troca Filtro Hidráulico",
            frequencia_dias=30,
            frequencia_horas=100.0,
            frequencia_km=None,
            ultimo_registro_data=datetime.now(timezone.utc) - timedelta(days=40),
            ultimo_registro_horas=450.0, # Última revisão aos 450h. Horímetro atual = 500h. Rodou 50h.
            checklist_preventivo="Trocar filtro",
            categoria="Filtros",
        )
        session.add(plano)
        await session.commit()

        preventiva_svc = FrotaManutencaoPreventivaService(session, tid)
        res_list = await preventiva_svc.listar_planos_preventivos()

        # O plano deve estar VENCIDO por dias (limite 30 dias, rodou 40 dias)
        assert len(res_list.itens) == 1
        item = res_list.itens[0]
        assert item.status == "VENCIDO"
        assert item.plano_id == plano.id

    @pytest.mark.asyncio
    async def test_geracao_os_preventiva_manual_e_automatica(
        self, session: AsyncSession, tenant_id: uuid.UUID
    ):
        """3. Gerar OS preventiva com cópia de checklist e transição de status para EM_MANUTENCAO."""
        tid = tenant_id
        equipamento = await _criar_equipamento(session, tid)

        plano = PlanoManutencao(
            id=uuid.uuid4(),
            tenant_id=tid,
            equipamento_id=equipamento.id,
            descricao="Lubrificação Completa",
            frequencia_dias=60,
            frequencia_horas=200.0,
            checklist_preventivo="Verificar graxa nos pinos",
            categoria="Lubrificação",
        )
        session.add(plano)
        await session.commit()

        preventiva_svc = FrotaManutencaoPreventivaService(session, tid)
        
        # Act: Gera OS Preventiva
        resp = await preventiva_svc.gerar_os_preventiva(plano.id)
        assert resp.criada is True
        
        # Verifica a OS criada
        os = await session.get(OrdemServico, resp.ordem_servico_id)
        assert os is not None
        assert os.tipo == "PREVENTIVA"
        assert os.status == "ABERTA"
        assert os.checklist_aplicado == "Verificar graxa nos pinos"

        # Verifica transição de status do maquinário
        await session.refresh(equipamento)
        assert equipamento.status == "EM_MANUTENCAO"

        # Tenta gerar novamente: deve retornar a mesma OS já existente e produzida anteriormente
        resp_duplicada = await preventiva_svc.gerar_os_preventiva(plano.id)
        assert resp_duplicada.criada is False
        assert resp_duplicada.ordem_servico_id == os.id

    @pytest.mark.asyncio
    async def test_fechar_os_preventiva_e_apropriacao_economica(
        self, session: AsyncSession
    ):
        """4. Concluir OS, retornar equipamento a ATIVO e gerar Despesa com safra/cultivo correspondente."""
        # Usa tenant isolado
        tid = uuid.uuid4()
        up_id = await _setup_tenant_completo(session, tid)
        
        # Setup: plano de contas analítico
        await _criar_plano_conta(session, tid)

        # Setup: Safra e Cultivo
        safra = Safra(
            id=uuid.uuid4(),
            tenant_id=tid,
            ano_safra="2026/27",
            cultura="MILHO",
            status="ATIVO",
        )
        cultivo = Cultivo(
            id=uuid.uuid4(),
            tenant_id=tid,
            safra_id=safra.id,
            cultura="MILHO",
            status="ATIVO",
        )
        session.add_all([safra, cultivo])
        await session.commit()

        equipamento = await _criar_equipamento(session, tid, unidade_produtiva_id=up_id, status="EM_MANUTENCAO")

        os = OrdemServico(
            id=uuid.uuid4(),
            tenant_id=tid,
            equipamento_id=equipamento.id,
            numero_os=f"OSPRV-{uuid.uuid4().hex[:8]}",
            tipo="PREVENTIVA",
            status="EM_EXECUCAO",
            safra_id=safra.id,
            descricao_problema="Revisão preventiva",
            custo_mao_obra=350.0,
            custo_total_pecas=150.0,
            checklist_aplicado="Revisar motor",
        )
        session.add(os)
        await session.commit()

        # Act: fecha OS
        frota_svc = FrotaService(session, tid)
        os_concluida = await frota_svc.fechar_os(
            os.id,
            OrdemServicoUpdate(
                diagnostico_tecnico="Lubrificação concluída e filtros trocados",
                tecnico_responsavel="Silvio Santos",
            )
        )

        assert os_concluida.status == "CONCLUIDA"
        
        # Valida retorno de maquinário a ATIVO
        await session.refresh(equipamento)
        assert equipamento.status == "ATIVO"

        # Valida registro de histórico no RegistroManutencao
        stmt_reg = select(RegistroManutencao).where(RegistroManutencao.os_id == os.id)
        reg = (await session.execute(stmt_reg)).scalar_one_or_none()
        assert reg is not None
        assert reg.custo_total == 500.0
        assert reg.tipo == "PREVENTIVA"

        # Valida Despesa financeira com apropriação de UP, Safra e Cultivo correspondente
        stmt_desp = select(Despesa).where(Despesa.origem_id == os.id)
        desp = (await session.execute(stmt_desp)).scalar_one_or_none()
        assert desp is not None
        assert desp.valor_total == 500.0
        assert desp.unidade_produtiva_id == up_id
        assert desp.cultivo_id == cultivo.id

    @pytest.mark.asyncio
    async def test_calculos_dashboard_mtbf_e_proporcao_custos(
        self, session: AsyncSession
    ):
        """5. Computar MTBF e proporção de custos de manutenção preventivos vs corretivos no dashboard."""
        # Usa tenant isolado
        tid = uuid.uuid4()
        up_id = await _setup_tenant_completo(session, tid)
        
        equipamento = await _criar_equipamento(session, tid, unidade_produtiva_id=up_id)

        # 1. Cria jornada finalizada com 24 horas trabalhadas
        jornada_id = uuid.uuid4()
        await session.execute(
            text(
                "INSERT INTO frota_jornadas_equipamento "
                "(id, tenant_id, equipamento_id, unidade_produtiva_id, tipo_operacao, data_inicio, data_fim, status, horimetro_inicial, horimetro_final, created_at, updated_at) "
                "VALUES (:id, :tenant_id, :eq_id, :up_id, 'PREPARO_SOLO', :dt_ini, :dt_fim, 'FINALIZADA', 500.0, 524.0, now(), now())"
            ),
            {
                "id": str(jornada_id),
                "tenant_id": str(tid),
                "eq_id": str(equipamento.id),
                "up_id": str(up_id),
                "dt_ini": datetime.now(timezone.utc) - timedelta(days=2),
                "dt_fim": datetime.now(timezone.utc) - timedelta(days=1),
            },
        )

        # 2. Cria manutenções: 1 preventiva (custo R$ 300) e 1 corretiva (custo R$ 100)
        # 1 corretiva com 24h totais de jornada -> MTBF = 24 / 1 = 24.0 horas.
        # Proporção preventiva = (300 / (300 + 100)) * 100 = 75%
        reg_prev = RegistroManutencao(
            id=uuid.uuid4(),
            tenant_id=tid,
            equipamento_id=equipamento.id,
            tipo="PREVENTIVA",
            descricao="Revisão preventiva",
            custo_total=300.0,
            data_realizacao=datetime.now(timezone.utc),
        )
        reg_corr = RegistroManutencao(
            id=uuid.uuid4(),
            tenant_id=tid,
            equipamento_id=equipamento.id,
            tipo="CORRETIVA",
            descricao="Conserto de mangueira rasgada",
            custo_total=100.0,
            data_realizacao=datetime.now(timezone.utc),
        )
        session.add_all([reg_prev, reg_corr])
        await session.commit()

        # Act: consulta o dashboard
        dash_svc = FrotaDashboardService(session, tid)
        dashboard = await dash_svc.obter_dashboard()

        # Assert
        resumo = dashboard.resumo
        assert resumo.mtbf_medio_horas == 24.0
        assert resumo.proporcao_custo_preventivo_percentual == 75.0
