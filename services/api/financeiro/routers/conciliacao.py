"""
Routers de Conciliação Bancária

Endpoints para importação de extrato OFX e conciliação bancária.
"""

from datetime import date, datetime, timedelta, timezone
import logging
from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import (
    get_current_tenant,
    get_session,
    require_module,
    require_tenant_permission,
)
from core.models.tenant import Tenant
from financeiro.models.conciliacao import LancamentoBancario
from financeiro.models.despesa import Despesa
from financeiro.models.receita import Receita
from financeiro.services.conciliacao_service import ConciliacaoBancariaFactory
from financeiro.services.ofx_parser import OFXParserFactory

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/conciliacao", tags=["Conciliação Bancária"], dependencies=[Depends(require_module("F1_TESOURARIA"))])


@router.post(
    "/upload-extrato",
    dependencies=[Depends(require_tenant_permission("financeiro:*"))],
)
async def upload_extrato(
    arquivo: UploadFile = File(..., description="Arquivo OFX do extrato bancário"),
    conta_bancaria_id: Optional[str] = None,
    tenant: Tenant = Depends(get_current_tenant),
):
    """
    Faz upload de arquivo OFX e extrai transações do extrato
    
    - **arquivo**: Arquivo OFX do banco
    - **conta_bancaria_id**: ID da conta bancária (opcional)
    
    Retorna as transações extraídas para conferência antes da conciliação.
    """
    # Validar arquivo
    if not arquivo.filename:
        raise HTTPException(status_code=400, detail="Arquivo não informado")
    
    if not arquivo.filename.lower().endswith('.ofx'):
        raise HTTPException(
            status_code=400,
            detail=f"Arquivo inválido. Esperado OFX, recebido: {arquivo.filename}"
        )
    
    try:
        # Ler conteúdo do arquivo
        conteudo = await arquivo.read()
        conteudo_str = conteudo.decode('latin-1')  # OFX usa encoding latin-1
        
        # Parse do OFX
        parser = OFXParserFactory.get_parser()
        extrato = parser.parse_conteudo(conteudo_str)
        
        # Validar extrato
        if not extrato.transacoes:
            raise HTTPException(
                status_code=400,
                detail="Nenhuma transação encontrada no extrato"
            )
        
        # Retornar transações para conferência
        return {
            "sucesso": True,
            "mensagem": f"{len(extrato.transacoes)} transações encontradas",
            "extrato": {
                "banco": extrato.banco,
                "conta": extrato.conta,
                "agencia": extrato.agencia,
                "saldo_inicial": extrato.saldo_inicial,
                "saldo_final": extrato.saldo_final,
                "data_inicial": extrato.data_inicial.isoformat() if extrato.data_inicial else None,
                "data_final": extrato.data_final.isoformat() if extrato.data_final else None,
                "total_transacoes": len(extrato.transacoes),
            },
            "transacoes": extrato.to_dict()["transacoes"],
        }
        
    except Exception as e:
        logger.error(f"Erro ao processar OFX: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao processar arquivo: {str(e)}"
        )


def _parse_uuid(value: str, field_name: str) -> uuid.UUID:
    """Converte string para UUID lançando HTTP 422 quando inválida."""
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=f"{field_name} inválido.") from exc


async def _resolver_destino_conciliacao(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    lancamento_sistema_id: uuid.UUID,
    tipo_lancamento: Optional[str] = None,
) -> tuple[Optional[uuid.UUID], Optional[uuid.UUID]]:
    """Valida e retorna (despesa_id, receita_id) pertencentes ao tenant."""
    tipo_norm = (tipo_lancamento or "").strip().upper()
    if tipo_norm in ("", "DESPESA"):
        despesa = (
            await session.execute(
                select(Despesa).where(
                    Despesa.id == lancamento_sistema_id,
                    Despesa.tenant_id == tenant_id,
                    Despesa.ativo == True,
                )
            )
        ).scalar_one_or_none()
        if despesa:
            return despesa.id, None
    if tipo_norm in ("", "RECEITA"):
        receita = (
            await session.execute(
                select(Receita).where(
                    Receita.id == lancamento_sistema_id,
                    Receita.tenant_id == tenant_id,
                    Receita.ativo == True,
                )
            )
        ).scalar_one_or_none()
        if receita:
            return None, receita.id
    raise HTTPException(
        status_code=404,
        detail=f"Lançamento financeiro {lancamento_sistema_id} não encontrado.",
    )


async def _vincular_lancamento_bancario(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    transacao_extrato_id: uuid.UUID,
    lancamento_sistema_id: uuid.UUID,
    tipo_lancamento: Optional[str] = None,
) -> LancamentoBancario:
    """Persiste a conciliação de um lançamento bancário com despesa ou receita do tenant."""
    lanc = (
        await session.execute(
            select(LancamentoBancario).where(
                LancamentoBancario.id == transacao_extrato_id,
                LancamentoBancario.tenant_id == tenant_id,
            )
        )
    ).scalar_one_or_none()
    if not lanc:
        raise HTTPException(
            status_code=404,
            detail=f"Transação bancária {transacao_extrato_id} não encontrada.",
        )

    despesa_id, receita_id = await _resolver_destino_conciliacao(
        session, tenant_id, lancamento_sistema_id, tipo_lancamento
    )
    lanc.despesa_id = despesa_id
    lanc.receita_id = receita_id
    lanc.status_conciliacao = "CONCILIADO"
    session.add(lanc)
    return lanc


@router.get("/transacoes-pendentes")
async def listar_transacoes_pendentes(
    conta_bancaria_id: Optional[str] = None,
    data_inicial: Optional[datetime] = None,
    data_final: Optional[datetime] = None,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
):
    """Lista transações do extrato bancário ainda não conciliadas."""
    stmt = select(LancamentoBancario).where(
        LancamentoBancario.tenant_id == tenant.id,
        LancamentoBancario.status_conciliacao == "NAO_CONCILIADO",
    )
    if conta_bancaria_id:
        stmt = stmt.where(
            LancamentoBancario.conta_id == _parse_uuid(conta_bancaria_id, "conta_bancaria_id")
        )
    if data_inicial:
        stmt = stmt.where(LancamentoBancario.data >= data_inicial.date())
    if data_final:
        stmt = stmt.where(LancamentoBancario.data <= data_final.date())

    rows = (await session.execute(stmt.order_by(LancamentoBancario.data.desc()))).scalars().all()
    transacoes = [
        {
            "id": str(item.id),
            "conta_id": str(item.conta_id),
            "data": item.data.isoformat(),
            "valor": float(item.valor),
            "descricao": item.descricao,
            "tipo": item.tipo,
            "id_ofx": item.id_ofx,
            "status_conciliacao": item.status_conciliacao,
        }
        for item in rows
    ]
    return {"total": len(transacoes), "transacoes": transacoes}


@router.get("/lancamentos-pendentes")
async def listar_lancamentos_pendentes(
    conta_bancaria_id: Optional[str] = None,
    data_inicial: Optional[datetime] = None,
    data_final: Optional[datetime] = None,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
):
    """Lista despesas e receitas do sistema financeiro ainda não conciliadas."""
    conc_desp_subq = select(LancamentoBancario.despesa_id).where(
        LancamentoBancario.tenant_id == tenant.id,
        LancamentoBancario.status_conciliacao == "CONCILIADO",
        LancamentoBancario.despesa_id.is_not(None),
    )
    conc_rec_subq = select(LancamentoBancario.receita_id).where(
        LancamentoBancario.tenant_id == tenant.id,
        LancamentoBancario.status_conciliacao == "CONCILIADO",
        LancamentoBancario.receita_id.is_not(None),
    )

    stmt_desp = select(Despesa).where(
        Despesa.tenant_id == tenant.id,
        Despesa.ativo == True,
        Despesa.status.in_(["A_PAGAR", "ATRASADA", "APROVADO", "LIBERADO_PAGAMENTO", "PAGO"]),
        Despesa.id.notin_(conc_desp_subq),
    )
    stmt_rec = select(Receita).where(
        Receita.tenant_id == tenant.id,
        Receita.ativo == True,
        Receita.status.in_(["A_RECEBER", "ATRASADA", "RECEBIDO_PARCIAL", "RECEBIDO"]),
        Receita.id.notin_(conc_rec_subq),
    )
    if data_inicial:
        dt_ini = data_inicial.date()
        stmt_desp = stmt_desp.where(Despesa.data_vencimento >= dt_ini)
        stmt_rec = stmt_rec.where(Receita.data_vencimento >= dt_ini)
    if data_final:
        dt_fim = data_final.date()
        stmt_desp = stmt_desp.where(Despesa.data_vencimento <= dt_fim)
        stmt_rec = stmt_rec.where(Receita.data_vencimento <= dt_fim)

    despesas = (await session.execute(stmt_desp.order_by(Despesa.data_vencimento.asc()))).scalars().all()
    receitas = (await session.execute(stmt_rec.order_by(Receita.data_vencimento.asc()))).scalars().all()

    lancamentos = [
        {
            "id": str(d.id),
            "tipo": "DESPESA",
            "descricao": d.descricao,
            "valor": float(d.valor_total),
            "data_vencimento": d.data_vencimento.isoformat() if d.data_vencimento else None,
            "status": d.status,
        }
        for d in despesas
    ] + [
        {
            "id": str(r.id),
            "tipo": "RECEITA",
            "descricao": r.descricao,
            "valor": float(r.valor_total),
            "data_vencimento": r.data_vencimento.isoformat() if r.data_vencimento else None,
            "status": r.status,
        }
        for r in receitas
    ]
    return {"total": len(lancamentos), "lancamentos": lancamentos}


@router.post(
    "/conciliar-automatico",
    dependencies=[Depends(require_tenant_permission("financeiro:*"))],
)
async def conciliar_automatico(
    transacoes_extrato: List[dict],
    lancamentos_sistema: List[dict],
    tenant: Tenant = Depends(get_current_tenant),
):
    """Realiza conciliação automática entre extrato e sistema."""
    try:
        service = ConciliacaoBancariaFactory.get_service()
        sugestoes = service.conciliar(
            transacoes_extrato=transacoes_extrato,
            lancamentos_sistema=lancamentos_sistema,
        )
        return {
            "sucesso": True,
            "total_sugestoes": len(sugestoes),
            "sugestoes": [s.to_dict() for s in sugestoes],
        }
    except Exception as e:
        logger.error(f"Erro na conciliação automática: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao conciliar: {str(e)}")


@router.post(
    "/conciliar-manual",
    dependencies=[Depends(require_tenant_permission("financeiro:*"))],
)
async def conciliar_manual(
    transacao_extrato_id: str,
    lancamento_sistema_id: str,
    tipo_lancamento: Optional[str] = None,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
):
    """Realiza e persiste conciliação manual no banco de dados."""
    transacao_uuid = _parse_uuid(transacao_extrato_id, "transacao_extrato_id")
    lancamento_uuid = _parse_uuid(lancamento_sistema_id, "lancamento_sistema_id")

    lanc = await _vincular_lancamento_bancario(
        session, tenant.id, transacao_uuid, lancamento_uuid, tipo_lancamento
    )
    await session.commit()
    await session.refresh(lanc)

    return {
        "sucesso": True,
        "mensagem": "Conciliação realizada com sucesso",
        "conciliacao": {
            "id": str(lanc.id),
            "transacao_extrato_id": str(lanc.id),
            "lancamento_sistema_id": str(lanc.despesa_id or lanc.receita_id),
            "despesa_id": str(lanc.despesa_id) if lanc.despesa_id else None,
            "receita_id": str(lanc.receita_id) if lanc.receita_id else None,
            "status_conciliacao": lanc.status_conciliacao,
        },
    }


@router.post(
    "/aprovar-conciliacao",
    dependencies=[Depends(require_tenant_permission("financeiro:*"))],
)
async def aprovar_conciliacao(
    sugestoes: List[dict],
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
):
    """Valida e persiste lote de sugestões de conciliação no banco."""
    if not sugestoes:
        raise HTTPException(status_code=422, detail="Informe ao menos uma sugestão para aprovar.")

    conciliacoes_aprovadas = []
    for sugestao in sugestoes:
        transacao_uuid = _parse_uuid(sugestao.get("transacao_extrato_id", ""), "transacao_extrato_id")
        lancamento_uuid = _parse_uuid(sugestao.get("lancamento_sistema_id", ""), "lancamento_sistema_id")
        lanc = await _vincular_lancamento_bancario(
            session, tenant.id, transacao_uuid, lancamento_uuid, sugestao.get("tipo")
        )
        conciliacoes_aprovadas.append(
            {
                "id": str(lanc.id),
                "transacao_extrato_id": str(lanc.id),
                "lancamento_sistema_id": str(lanc.despesa_id or lanc.receita_id),
                "status": "aprovado",
            }
        )

    await session.commit()
    return {
        "sucesso": True,
        "total_aprovadas": len(conciliacoes_aprovadas),
        "conciliacoes": conciliacoes_aprovadas,
    }


@router.get("/resumo-conciliacao")
async def get_resumo_conciliacao(
    periodo: str = "mes",
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
):
    """Retorna resumo real das conciliações do tenant no período."""
    hoje = datetime.now(timezone.utc).date()
    dias_por_periodo = {"dia": 0, "semana": 7, "mes": 30, "ano": 365}
    dias = dias_por_periodo.get(periodo, 30)
    data_corte = hoje - timedelta(days=dias)

    stmt = select(LancamentoBancario).where(
        LancamentoBancario.tenant_id == tenant.id,
        LancamentoBancario.data >= data_corte,
    )
    rows = (await session.execute(stmt)).scalars().all()

    total_transacoes = len(rows)
    conciliadas = [r for r in rows if r.status_conciliacao == "CONCILIADO"]
    pendentes = [r for r in rows if r.status_conciliacao == "NAO_CONCILIADO"]
    total_conciliadas = len(conciliadas)
    valor_total_conciliado = round(sum(abs(float(r.valor)) for r in conciliadas), 2)
    percentual = round((total_conciliadas / total_transacoes) * 100, 2) if total_transacoes > 0 else 0.0

    return {
        "periodo": periodo,
        "total_transacoes": total_transacoes,
        "total_conciliadas": total_conciliadas,
        "total_pendentes": len(pendentes),
        "percentual_conciliado": percentual,
        "valor_total_conciliado": valor_total_conciliado,
    }


@router.delete(
    "/desfazer-conciliacao/{conciliacao_id}",
    dependencies=[Depends(require_tenant_permission("financeiro:*"))],
)
async def desfazer_conciliacao(
    conciliacao_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
):
    """Desfaz uma conciliação aprovada no banco de dados."""
    lanc_uuid = _parse_uuid(conciliacao_id, "conciliacao_id")
    lanc = (
        await session.execute(
            select(LancamentoBancario).where(
                LancamentoBancario.id == lanc_uuid,
                LancamentoBancario.tenant_id == tenant.id,
            )
        )
    ).scalar_one_or_none()
    if not lanc:
        raise HTTPException(status_code=404, detail="Conciliação não encontrada.")
    if lanc.status_conciliacao != "CONCILIADO":
        raise HTTPException(status_code=400, detail="Este lançamento não está conciliado.")

    lanc.status_conciliacao = "NAO_CONCILIADO"
    lanc.despesa_id = None
    lanc.receita_id = None
    session.add(lanc)
    await session.commit()

    return {
        "sucesso": True,
        "mensagem": f"Conciliação {conciliacao_id} desfeita com sucesso",
    }
