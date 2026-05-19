"""
Testes — Frota & Equipamentos — Step 05

Cobre checklists operacionais, integração com jornada, bloqueio crítico,
geração de OS, histórico operacional e isolamento de tenant.
"""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from core.cadastros.equipamentos.models import Equipamento
from core.exceptions import BusinessRuleError, EntityNotFoundError
from operacional.models.checklist import ChecklistOperacionalResposta
from operacional.models.frota import JornadaEquipamento, OrdemServico
from operacional.schemas.frota_checklist import (
    ChecklistOperacionalCreate,
    ChecklistOperacionalItemCreate,
    ChecklistOperacionalPreenchimentoCreate,
    ChecklistOperacionalRespostaCreate,
)
from operacional.schemas.frota_jornada import FrotaJornadaCreate
from operacional.services.frota_checklist_service import FrotaChecklistService
from operacional.services.frota_dashboard_service import FrotaDashboardService
from operacional.services.frota_jornada_service import FrotaJornadaService


@pytest.fixture(autouse=True)
async def setup_step05_schema(session: AsyncSession):
    try:
        await session.execute(
            text("ALTER TABLE frota_ordens_servico ADD COLUMN IF NOT EXISTS origem_checklist_resposta_id uuid")
        )
        await session.commit()
    except Exception:
        await session.rollback()


async def _tenant(session: AsyncSession) -> uuid.UUID:
    tenant_id = uuid.uuid4()
    await session.execute(
        text(
            "INSERT INTO tenants (id, nome, documento, ativo, storage_usado_mb, storage_limite_mb, idioma_padrao, created_at, updated_at) "
            "VALUES (:id, 'Tenant Step05', :doc, true, 0, 10240, 'pt-BR', now(), now())"
        ),
        {"id": str(tenant_id), "doc": str(tenant_id)[:11]},
    )
    await session.commit()
    return tenant_id


async def _up(session: AsyncSession, tenant_id: uuid.UUID) -> uuid.UUID:
    up_id = uuid.uuid4()
    await session.execute(
        text(
            "INSERT INTO unidades_produtivas (id, tenant_id, nome, ativo, created_at, updated_at) "
            "VALUES (:id, :tenant_id, 'UP Step05', true, now(), now())"
        ),
        {"id": str(up_id), "tenant_id": str(tenant_id)},
    )
    await session.commit()
    return up_id


async def _equipamento(session: AsyncSession, tenant_id: uuid.UUID, up_id: uuid.UUID, tipo: str = "TRATOR") -> Equipamento:
    equipamento = Equipamento(
        tenant_id=tenant_id,
        unidade_produtiva_id=up_id,
        nome=f"Equipamento-S05-{uuid.uuid4().hex[:6]}",
        tipo=tipo,
        combustivel="DIESEL",
        status="ATIVO",
        horimetro_atual=100.0,
        km_atual=500.0,
        ativo=True,
    )
    session.add(equipamento)
    await session.commit()
    await session.refresh(equipamento)
    return equipamento


async def _checklist(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    tipo_jornada: str = "ABERTURA",
    exige: bool = True,
):
    svc = FrotaChecklistService(session, tenant_id)
    checklist = await svc.criar_checklist(
        ChecklistOperacionalCreate(
            nome=f"Checklist {tipo_jornada}",
            tipo_equipamento="TRATOR",
            tipo_jornada=tipo_jornada,
            exige_antes_operacao=exige,
            itens=[
                ChecklistOperacionalItemCreate(
                    categoria="SEGURANCA",
                    descricao="Freio operacional",
                    obrigatorio=True,
                    ordem=1,
                ),
                ChecklistOperacionalItemCreate(
                    categoria="MECANICA",
                    descricao="Vazamento aparente",
                    obrigatorio=False,
                    ordem=2,
                ),
            ],
        )
    )
    await session.commit()
    return checklist


@pytest.mark.asyncio
async def test_checklist_obrigatorio_bloqueia_abertura_sem_resposta(session: AsyncSession):
    tenant_id = await _tenant(session)
    up_id = await _up(session, tenant_id)
    equipamento = await _equipamento(session, tenant_id, up_id)
    await _checklist(session, tenant_id)

    svc = FrotaJornadaService(session, tenant_id)
    with pytest.raises(BusinessRuleError, match="Checklist de abertura obrigatório"):
        await svc.criar_jornada(
            FrotaJornadaCreate(
                equipamento_id=equipamento.id,
                unidade_produtiva_id=up_id,
                tipo_operacao="PLANTIO",
                data_inicio=datetime.now(timezone.utc),
            )
        )


@pytest.mark.asyncio
async def test_falha_critica_bloqueia_equipamento_e_gera_os(session: AsyncSession):
    tenant_id = await _tenant(session)
    up_id = await _up(session, tenant_id)
    equipamento = await _equipamento(session, tenant_id, up_id)
    checklist = await _checklist(session, tenant_id)

    payload = ChecklistOperacionalPreenchimentoCreate(
        checklist_id=checklist.id,
        equipamento_id=equipamento.id,
        unidade_produtiva_id=up_id,
        tipo_jornada="ABERTURA",
        respostas=[
            ChecklistOperacionalRespostaCreate(
                item_id=checklist.itens[0].id,
                status="NAO_CONFORME",
                falha=True,
                criticidade="CRITICA",
                observacao="Freio sem resposta segura",
            )
        ],
    )

    svc = FrotaJornadaService(session, tenant_id)
    with pytest.raises(BusinessRuleError, match="Falha crítica"):
        await svc.criar_jornada(
            FrotaJornadaCreate(
                equipamento_id=equipamento.id,
                unidade_produtiva_id=up_id,
                tipo_operacao="COLHEITA",
                data_inicio=datetime.now(timezone.utc),
                checklist_abertura=payload,
            )
        )

    await session.refresh(equipamento)
    assert equipamento.bloqueado_operacional is True

    os_gerada = (
        await session.execute(
            select(OrdemServico).where(
                OrdemServico.tenant_id == tenant_id,
                OrdemServico.equipamento_id == equipamento.id,
                OrdemServico.origem_checklist_resposta_id.is_not(None),
            )
        )
    ).scalar_one()
    assert os_gerada.tipo == "CORRETIVA"


@pytest.mark.asyncio
async def test_checklist_conforme_abre_jornada_e_mantem_historico(session: AsyncSession):
    tenant_id = await _tenant(session)
    up_id = await _up(session, tenant_id)
    equipamento = await _equipamento(session, tenant_id, up_id)
    checklist = await _checklist(session, tenant_id)

    payload = ChecklistOperacionalPreenchimentoCreate(
        checklist_id=checklist.id,
        equipamento_id=equipamento.id,
        unidade_produtiva_id=up_id,
        tipo_jornada="ABERTURA",
        respostas=[
            ChecklistOperacionalRespostaCreate(
                item_id=checklist.itens[0].id,
                status="CONFORME",
            )
        ],
    )
    resp = await FrotaJornadaService(session, tenant_id).criar_jornada(
        FrotaJornadaCreate(
            equipamento_id=equipamento.id,
            unidade_produtiva_id=up_id,
            tipo_operacao="PULVERIZACAO",
            data_inicio=datetime.now(timezone.utc) - timedelta(minutes=5),
            checklist_abertura=payload,
        )
    )

    resposta = (
        await session.execute(
            select(ChecklistOperacionalResposta).where(
                ChecklistOperacionalResposta.tenant_id == tenant_id,
                ChecklistOperacionalResposta.equipamento_id == equipamento.id,
            )
        )
    ).scalar_one()
    assert resposta.jornada_id == resp.jornada.id
    assert resposta.unidade_produtiva_id == up_id
    assert resposta.tipo_jornada == "ABERTURA"

    jornada = await session.get(JornadaEquipamento, resp.jornada.id)
    assert jornada is not None
    assert jornada.status == "ABERTA"


@pytest.mark.asyncio
async def test_geracao_opcional_de_os_a_partir_de_falha_nao_critica(session: AsyncSession):
    tenant_id = await _tenant(session)
    up_id = await _up(session, tenant_id)
    equipamento = await _equipamento(session, tenant_id, up_id)
    checklist = await _checklist(session, tenant_id, exige=False)

    resposta = await FrotaChecklistService(session, tenant_id).registrar_respostas(
        ChecklistOperacionalPreenchimentoCreate(
            checklist_id=checklist.id,
            equipamento_id=equipamento.id,
            unidade_produtiva_id=up_id,
            tipo_jornada="ABERTURA",
            gerar_os=True,
            respostas=[
                ChecklistOperacionalRespostaCreate(
                    item_id=checklist.itens[0].id,
                    status="CONFORME",
                ),
                ChecklistOperacionalRespostaCreate(
                    item_id=checklist.itens[1].id,
                    status="NAO_CONFORME",
                    falha=True,
                    criticidade="MEDIA",
                    observacao="Vazamento leve",
                )
            ],
        )
    )
    await session.commit()

    assert resposta.os_gerada_id is not None
    os_gerada = await session.get(OrdemServico, resposta.os_gerada_id)
    assert os_gerada is not None
    assert os_gerada.tipo == "PREVENTIVA"
    assert os_gerada.checklist_aplicado == checklist.nome


@pytest.mark.asyncio
async def test_dashboard_lista_ocorrencias_e_pendencias(session: AsyncSession):
    tenant_id = await _tenant(session)
    up_id = await _up(session, tenant_id)
    equipamento = await _equipamento(session, tenant_id, up_id)
    await _checklist(session, tenant_id)

    dashboard = await FrotaDashboardService(session, tenant_id).obter_dashboard(unidade_produtiva_id=up_id)
    assert dashboard.resumo.checklists_pendentes >= 1
    assert dashboard.resumo.equipamentos_bloqueados == 0
    assert any(item.equipamento_id == equipamento.id for item in dashboard.equipamentos)


@pytest.mark.asyncio
async def test_tenant_mismatch_rejeita_checklist_para_equipamento_de_outro_tenant(session: AsyncSession):
    tenant_a = await _tenant(session)
    tenant_b = await _tenant(session)
    up_b = await _up(session, tenant_b)
    equipamento_b = await _equipamento(session, tenant_b, up_b)
    checklist_a = await _checklist(session, tenant_a)

    with pytest.raises(EntityNotFoundError):
        await FrotaChecklistService(session, tenant_a).registrar_respostas(
            ChecklistOperacionalPreenchimentoCreate(
                checklist_id=checklist_a.id,
                equipamento_id=equipamento_b.id,
                unidade_produtiva_id=up_b,
                tipo_jornada="ABERTURA",
                respostas=[
                    ChecklistOperacionalRespostaCreate(
                        item_id=checklist_a.itens[0].id,
                        status="CONFORME",
                    )
                ],
            )
        )
