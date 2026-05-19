"""
Testes — Frota & Equipamentos — Step 07

Cobre integração de operador com jornada, produtividade operacional,
rastreabilidade humana e hardening multi-tenant/multi-UP.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from core.cadastros.equipamentos.models import Equipamento
from core.cadastros.pessoas.models import Pessoa, PessoaRelacionamento, TipoRelacionamento
from core.exceptions import BusinessRuleError
from core.models.unidade_produtiva import UnidadeProdutiva
from agricola.safras.models import Safra
from operacional.models.abastecimento import Abastecimento
from operacional.models.checklist import ChecklistOperacional, ChecklistOperacionalResposta
from operacional.models.frota import JornadaEquipamento, OrdemServico
from operacional.schemas.frota import OrdemServicoCreate, OrdemServicoUpdate
from operacional.schemas.frota_checklist import (
    ChecklistOperacionalCreate,
    ChecklistOperacionalItemCreate,
    ChecklistOperacionalPreenchimentoCreate,
    ChecklistOperacionalRespostaCreate,
)
from operacional.schemas.frota_jornada import FrotaJornadaCreate, FrotaJornadaFinalizarRequest
from operacional.services.frota_checklist_service import FrotaChecklistService
from operacional.services.frota_dashboard_service import FrotaDashboardService
from operacional.services.frota_jornada_service import FrotaJornadaService
from operacional.services.frota_service import FrotaService


@pytest.fixture(autouse=True)
async def setup_step07_schema(session: AsyncSession):
    for ddl in (
        "ALTER TABLE frota_jornadas_equipamento ADD COLUMN IF NOT EXISTS aberta_por_id uuid",
        "ALTER TABLE frota_jornadas_equipamento ADD COLUMN IF NOT EXISTS encerrada_por_id uuid",
        "ALTER TABLE frota_ordens_servico ADD COLUMN IF NOT EXISTS aberta_por_id uuid",
        "ALTER TABLE frota_ordens_servico ADD COLUMN IF NOT EXISTS encerrada_por_id uuid",
        "ALTER TABLE frota_os_itens ADD COLUMN IF NOT EXISTS tenant_id uuid",
        "ALTER TABLE frota_os_itens ADD COLUMN IF NOT EXISTS deposito_id uuid",
        "ALTER TABLE frota_os_itens ADD COLUMN IF NOT EXISTS lote_id uuid",
        "ALTER TABLE frota_os_itens ADD COLUMN IF NOT EXISTS unidade_produtiva_id uuid",
        "ALTER TABLE frota_os_itens ADD COLUMN IF NOT EXISTS safra_id uuid",
        "ALTER TABLE frota_os_itens ADD COLUMN IF NOT EXISTS custo_unitario double precision DEFAULT 0",
        "ALTER TABLE frota_os_itens ADD COLUMN IF NOT EXISTS custo_total double precision DEFAULT 0",
        "ALTER TABLE frota_os_itens ADD COLUMN IF NOT EXISTS movimento_estoque_id uuid",
        "ALTER TABLE frota_os_itens ADD COLUMN IF NOT EXISTS executado_por_id uuid",
        "ALTER TABLE frota_registros_manutencao ADD COLUMN IF NOT EXISTS executado_por_id uuid",
        "ALTER TABLE frota_checklists_operacionais_respostas ADD COLUMN IF NOT EXISTS executado_por_id uuid",
        "ALTER TABLE frota_checklists_operacionais_respostas ADD COLUMN IF NOT EXISTS reportado_por_id uuid",
    ):
        try:
            await session.execute(text(ddl))
        except Exception:
            await session.rollback()
            raise
    await session.commit()


async def _ensure_tenant(session: AsyncSession, tenant_id: uuid.UUID) -> None:
    await session.execute(
        text(
            "INSERT INTO tenants (id, nome, documento, ativo, storage_usado_mb, storage_limite_mb, idioma_padrao, created_at, updated_at) "
            "VALUES (:id, :nome, :doc, true, 0, 10240, 'pt-BR', now(), now()) "
            "ON CONFLICT DO NOTHING"
        ),
        {"id": str(tenant_id), "nome": f"Tenant {str(tenant_id)[:8]}", "doc": str(tenant_id)[:11]},
    )
    await session.commit()


async def _ensure_up(session: AsyncSession, tenant_id: uuid.UUID, nome: str) -> UnidadeProdutiva:
    up = UnidadeProdutiva(
        tenant_id=tenant_id,
        nome=nome,
        tipo_propriedade="fazenda",
        ativo=True,
    )
    session.add(up)
    await session.commit()
    await session.refresh(up)
    return up


async def _ensure_safra(session: AsyncSession, tenant_id: uuid.UUID) -> Safra:
    safra = Safra(
        tenant_id=tenant_id,
        ano_safra=f"{date.today().year}/{date.today().year + 1}",
        cultura="SOJA",
        status="PLANEJADA",
    )
    session.add(safra)
    await session.commit()
    await session.refresh(safra)
    return safra


async def _ensure_operator(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    unidade_produtiva_id: uuid.UUID,
    *,
    nome: str,
    outra_up_id: uuid.UUID | None = None,
) -> Pessoa:
    pessoa = Pessoa(
        tenant_id=tenant_id,
        tipo="PF",
        nome_exibicao=nome,
        base_legal="CONTRATO",
        ativo=True,
    )
    session.add(pessoa)
    await session.flush()

    tipo_rel = TipoRelacionamento(
        tenant_id=tenant_id,
        codigo="FUNCIONARIO",
        nome="Funcionário",
        sistema=False,
        ativo=True,
    )
    session.add(tipo_rel)
    await session.flush()

    session.add(
        PessoaRelacionamento(
            pessoa_id=pessoa.id,
            tipo_id=tipo_rel.id,
            unidade_produtiva_id=outra_up_id or unidade_produtiva_id,
            ativo_desde=date.today(),
        )
    )
    await session.commit()
    await session.refresh(pessoa)
    return pessoa


async def _ensure_equipamento(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    unidade_produtiva_id: uuid.UUID,
    *,
    nome: str,
) -> Equipamento:
    equipamento = Equipamento(
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_produtiva_id,
        nome=nome,
        tipo="TRATOR",
        combustivel="DIESEL",
        status="ATIVO",
        horimetro_atual=100.0,
        km_atual=250.0,
        ativo=True,
    )
    session.add(equipamento)
    await session.commit()
    await session.refresh(equipamento)
    return equipamento


async def _criar_checklist_operacional(
    session: AsyncSession,
    tenant_id: uuid.UUID,
) -> ChecklistOperacional:
    svc = FrotaChecklistService(session, tenant_id)
    checklist = await svc.criar_checklist(
        ChecklistOperacionalCreate(
            nome="Checklist Operador",
            tipo_equipamento="TRATOR",
            tipo_jornada="ABERTURA",
            exige_antes_operacao=False,
            bloqueia_falha_critica=False,
            itens=[
                ChecklistOperacionalItemCreate(
                    categoria="SEGURANCA",
                    descricao="Freio operacional",
                    obrigatorio=True,
                    ordem=1,
                ),
                ChecklistOperacionalItemCreate(
                    categoria="OPERACIONAL",
                    descricao="Painel sem alertas",
                    obrigatorio=False,
                    ordem=2,
                ),
            ],
        )
    )
    await session.commit()
    return checklist


@pytest.mark.asyncio
async def test_operador_fora_do_tenant_rejeitado_na_jornada(session: AsyncSession, tenant_id: uuid.UUID, outro_tenant_id: uuid.UUID):
    await _ensure_tenant(session, tenant_id)
    await _ensure_tenant(session, outro_tenant_id)
    up = await _ensure_up(session, tenant_id, "UP Step07-A")
    up_outro = await _ensure_up(session, outro_tenant_id, "UP Step07-X")
    equipamento = await _ensure_equipamento(session, tenant_id, up.id, nome="Trator Step07-A")
    operador = await _ensure_operator(session, outro_tenant_id, up_outro.id, nome="Operador Outro Tenant")

    with pytest.raises(BusinessRuleError, match="Pessoa não localizada"):
        await FrotaJornadaService(session, tenant_id).criar_jornada(
            FrotaJornadaCreate(
                equipamento_id=equipamento.id,
                operador_id=operador.id,
                unidade_produtiva_id=up.id,
                tipo_operacao="COLHEITA",
                data_inicio=datetime.now(timezone.utc),
            )
        )


@pytest.mark.asyncio
async def test_operador_sem_acesso_a_up_rejeitado_na_jornada(session: AsyncSession, tenant_id: uuid.UUID):
    await _ensure_tenant(session, tenant_id)
    up_a = await _ensure_up(session, tenant_id, "UP Step07-B")
    up_b = await _ensure_up(session, tenant_id, "UP Step07-C")
    equipamento = await _ensure_equipamento(session, tenant_id, up_a.id, nome="Trator Step07-B")
    operador = await _ensure_operator(session, tenant_id, up_b.id, nome="Operador Sem Acesso")

    with pytest.raises(BusinessRuleError, match="não possui acesso à unidade produtiva"):
        await FrotaJornadaService(session, tenant_id).criar_jornada(
            FrotaJornadaCreate(
                equipamento_id=equipamento.id,
                operador_id=operador.id,
                unidade_produtiva_id=up_a.id,
                tipo_operacao="COLHEITA",
                data_inicio=datetime.now(timezone.utc),
            )
        )


@pytest.mark.asyncio
async def test_produtividade_e_rastreabilidade_operacional_completas(session: AsyncSession, tenant_id: uuid.UUID):
    await _ensure_tenant(session, tenant_id)
    up = await _ensure_up(session, tenant_id, "UP Step07-D")
    safra = await _ensure_safra(session, tenant_id)
    equipamento = await _ensure_equipamento(session, tenant_id, up.id, nome="Trator Step07-C")
    operador = await _ensure_operator(session, tenant_id, up.id, nome="Operador Principal")

    jornada_svc = FrotaJornadaService(session, tenant_id)
    jornada_resp = await jornada_svc.criar_jornada(
        FrotaJornadaCreate(
            equipamento_id=equipamento.id,
            operador_id=operador.id,
            unidade_produtiva_id=up.id,
            safra_id=safra.id,
            tipo_operacao="COLHEITA",
            data_inicio=datetime.now(timezone.utc) - timedelta(hours=2),
            horimetro_inicial=100.0,
            km_inicial=250.0,
            aberta_por_id=operador.id,
        )
    )

    checklist = await _criar_checklist_operacional(session, tenant_id)
    await FrotaChecklistService(session, tenant_id).registrar_respostas(
        ChecklistOperacionalPreenchimentoCreate(
            checklist_id=checklist.id,
            equipamento_id=equipamento.id,
            operador_id=operador.id,
            jornada_id=jornada_resp.jornada.id,
            unidade_produtiva_id=up.id,
            safra_id=safra.id,
            tipo_jornada="ABERTURA",
            executado_por_id=operador.id,
            reportado_por_id=operador.id,
            respostas=[
                ChecklistOperacionalRespostaCreate(
                    item_id=checklist.itens[0].id,
                    status="NAO_CONFORME",
                    falha=True,
                    criticidade="ALTA",
                    observacao="Sensor visual sem resposta",
                )
            ],
        )
    )

    frota_svc = FrotaService(session, tenant_id)
    os_aberta = await frota_svc.abrir_os(
        OrdemServicoCreate(
            maquinario_id=equipamento.id,
            tipo="CORRETIVA",
            descricao_problema="Ajuste preventivo por vibração",
            horimetro_na_abertura=100.0,
            km_na_abertura=250.0,
            tecnico_responsavel="Técnico Campo",
        ),
        usuario_id=operador.id,
    )
    await frota_svc.fechar_os(
        os_aberta.id,
        OrdemServicoUpdate(
            diagnostico_tecnico="Ajuste realizado sem troca de peças",
            custo_mao_obra=85.0,
        ),
        usuario_id=operador.id,
    )

    session.add(
        Abastecimento(
            tenant_id=tenant_id,
            equipamento_id=equipamento.id,
            data=datetime.now(timezone.utc) - timedelta(hours=1),
            operador_id=operador.id,
            safra_id=safra.id,
            horimetro_na_data=102.0,
            km_na_data=252.0,
            tipo_combustivel="DIESEL",
            litros=50.0,
            preco_litro=5.0,
            custo_total=250.0,
            tanque_cheio=True,
            local="INTERNO",
        )
    )
    await session.commit()

    await jornada_svc.finalizar_jornada(
        jornada_resp.jornada.id,
        FrotaJornadaFinalizarRequest(
            data_fim=datetime.now(timezone.utc),
            horimetro_final=102.0,
            km_final=252.0,
            encerrada_por_id=operador.id,
        ),
    )

    jornada = await session.get(JornadaEquipamento, jornada_resp.jornada.id)
    assert jornada is not None
    assert jornada.aberta_por_id == operador.id
    assert jornada.encerrada_por_id == operador.id
    assert jornada.safra_id == safra.id

    os = await session.get(OrdemServico, os_aberta.id)
    assert os is not None
    assert os.aberta_por_id == operador.id
    assert os.encerrada_por_id == operador.id
    assert os.safra_id == safra.id

    registro = (
        await session.execute(
            text("SELECT executado_por_id, safra_id, tenant_id FROM frota_registros_manutencao WHERE os_id = :os_id"),
            {"os_id": str(os.id)},
        )
    ).fetchone()
    assert registro is not None
    assert str(registro[0]) == str(operador.id)
    assert str(registro[1]) == str(safra.id)
    assert str(registro[2]) == str(tenant_id)

    resposta_checklist = (
        await session.execute(
            select(ChecklistOperacionalResposta).where(
                ChecklistOperacionalResposta.tenant_id == tenant_id,
                ChecklistOperacionalResposta.equipamento_id == equipamento.id,
            )
        )
    ).scalar_one()
    assert resposta_checklist.executado_por_id == operador.id
    assert resposta_checklist.reportado_por_id == operador.id
    assert resposta_checklist.safra_id == safra.id
    assert resposta_checklist.jornada_id == jornada.id

    dashboard = await FrotaDashboardService(session, tenant_id).obter_dashboard(unidade_produtiva_id=up.id)
    operador_item = next(item for item in dashboard.operadores_produtividade if item.operador_id == operador.id)
    assert operador_item.horas_operadas == 2.0
    assert operador_item.jornadas == 1
    assert operador_item.equipamentos_utilizados == 1
    assert operador_item.falhas_reportadas == 1
    assert operador_item.checklists_com_ocorrencia == 1
    assert operador_item.consumo_operacional == 335.0
    assert operador_item.produtividade_operacional == 2.0
    assert operador_item.equipamentos_mais_utilizados == ["Trator Step07-C"]
    assert dashboard.principais_ocorrencias
    assert dashboard.principais_ocorrencias[0].equipamento_id == equipamento.id
    assert dashboard.principais_ocorrencias[0].criticidade == "ALTA"


@pytest.mark.asyncio
async def test_tenant_mismatch_rejeita_operador_em_checklist(session: AsyncSession, tenant_id: uuid.UUID, outro_tenant_id: uuid.UUID):
    await _ensure_tenant(session, tenant_id)
    await _ensure_tenant(session, outro_tenant_id)
    up = await _ensure_up(session, tenant_id, "UP Step07-E")
    up_outro = await _ensure_up(session, outro_tenant_id, "UP Step07-Y")
    equipamento = await _ensure_equipamento(session, tenant_id, up.id, nome="Trator Step07-D")
    operador = await _ensure_operator(session, outro_tenant_id, up_outro.id, nome="Operador Tenant B")
    checklist = await _criar_checklist_operacional(session, tenant_id)

    with pytest.raises(BusinessRuleError, match="Pessoa não localizada"):
        await FrotaChecklistService(session, tenant_id).registrar_respostas(
            ChecklistOperacionalPreenchimentoCreate(
                checklist_id=checklist.id,
                equipamento_id=equipamento.id,
                operador_id=operador.id,
                unidade_produtiva_id=up.id,
                tipo_jornada="ABERTURA",
                respostas=[
                    ChecklistOperacionalRespostaCreate(
                        item_id=checklist.itens[0].id,
                        status="CONFORME",
                    )
                ],
            )
        )
