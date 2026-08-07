from core.dependencies import require_tenant_permission
"""
Router de Integrações Financeiras:
  - Contas Bancárias + importação OFX
  - Conciliação bancária
  - Exportação Carnê-Leão (RFB)
  - Resumo API Contábil
"""
import uuid
from datetime import date
from typing import Literal, Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import io

from core.dependencies import get_session, get_tenant_id, require_module
from financeiro.services.integracao_service import (
    ConciliacaoService,
    CarneLeaoService,
    ContabilService,
)

router = APIRouter(
    prefix="/integracao",
    tags=["Financeiro - Integrações (F1)"],
    dependencies=[Depends(require_module("F1_TESOURARIA"))],
)


# ── Schemas inline ────────────────────────────────────────────────────────────

class ContaBancariaCreate(BaseModel):
    nome: str
    banco: Optional[str] = None
    agencia: Optional[str] = None
    conta: Optional[str] = None
    tipo: str = "CORRENTE"
    unidade_produtiva_id: Optional[uuid.UUID] = None
    saldo_inicial: float = 0.0


class ContaBancariaResponse(BaseModel):
    id: uuid.UUID
    nome: str
    banco: Optional[str]
    agencia: Optional[str]
    conta: Optional[str]
    tipo: str
    ativa: bool
    unidade_produtiva_id: Optional[uuid.UUID]
    saldo_atual: float = 0.0
    convenio_pagamentos: Optional[str]
    layout_remessa: Optional[str]
    homologada_para_remessa: bool

    model_config = {"from_attributes": True}


class LancamentoBancarioResponse(BaseModel):
    id: uuid.UUID
    conta_id: uuid.UUID
    data: date
    valor: float
    descricao: Optional[str]
    tipo: str
    status_conciliacao: str
    id_ofx: Optional[str]
    despesa_id: Optional[uuid.UUID]
    receita_id: Optional[uuid.UUID]

    model_config = {"from_attributes": True}


class ConciliarRequest(BaseModel):
    despesa_id: Optional[uuid.UUID] = None
    receita_id: Optional[uuid.UUID] = None


class ConfigurarRemessaRequest(BaseModel):
    convenio_pagamentos: Optional[str] = None
    layout_remessa: Optional[Literal["CNAB240"]] = None
    homologada_para_remessa: bool


class RetornoSimuladoRequest(BaseModel):
    aprovado: bool

class CriarOrdemRequest(BaseModel):
    conta_bancaria_id: uuid.UUID
    despesa_ids: list[uuid.UUID]


# ── Contas Bancárias ──────────────────────────────────────────────────────────

@router.post(
    "/contas-bancarias",
    response_model=ContaBancariaResponse,
    status_code=201,
    dependencies=[Depends(require_tenant_permission("financeiro:*"))],
)
async def criar_conta_bancaria(
    dados: ContaBancariaCreate,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_session),
):
    svc = ConciliacaoService(db, tenant_id)
    conta = await svc.criar_conta(dados.model_dump())
    await db.commit()
    await db.refresh(conta)
    return conta


@router.get("/contas-bancarias", response_model=List[ContaBancariaResponse])
async def listar_contas_bancarias(
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_session),
):
    svc = ConciliacaoService(db, tenant_id)
    return await svc.listar_contas()


@router.patch(
    "/contas-bancarias/{conta_id}/remessa",
    response_model=ContaBancariaResponse,
    dependencies=[Depends(require_tenant_permission("financeiro:*"))],
)
async def configurar_remessa_conta_bancaria(
    conta_id: uuid.UUID,
    dados: ConfigurarRemessaRequest,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_session),
):
    """Configura a homologação da conta para geração de remessas."""
    svc = ConciliacaoService(db, tenant_id)
    conta = await svc.configurar_remessa(conta_id, dados.model_dump())
    await db.commit()
    return conta


@router.post(
    "/contas-bancarias/{conta_id}/validar-remessa",
    response_model=ContaBancariaResponse,
    dependencies=[Depends(require_tenant_permission("financeiro:*"))],
)
async def validar_remessa_conta_bancaria(
    conta_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_session),
):
    """Impede que integrações gerem remessas sem conta homologada."""
    svc = ConciliacaoService(db, tenant_id)
    return await svc.validar_remessa(conta_id)


@router.post(
    "/ordens-pagamento/{ordem_id:uuid}/simular-retorno",
    dependencies=[Depends(require_tenant_permission("financeiro:*"))],
)
async def simular_retorno_ordem_pagamento(
    ordem_id: uuid.UUID,
    dados: RetornoSimuladoRequest,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_session),
):
    """Processa um retorno fictício de homologação, sem qualquer envio externo."""
    svc = ConciliacaoService(db, tenant_id)
    ordem = await svc.simular_retorno_ordem(ordem_id, dados.aprovado)
    await db.commit()
    return {"id": str(ordem.id), "status": ordem.status}


@router.get("/ordens-pagamento/candidatos")
async def listar_candidatos_ordem_pagamento(
    tenant_id: uuid.UUID = Depends(get_tenant_id), db: AsyncSession = Depends(get_session),
):
    """Lista títulos liberados que ainda podem compor uma ordem de pagamento."""
    from financeiro.models.despesa import Despesa
    linhas = (await db.execute(select(Despesa).where(
        Despesa.tenant_id == tenant_id, Despesa.ativo == True, Despesa.status == "LIBERADO_PAGAMENTO"
    ).order_by(Despesa.data_vencimento))).scalars().all()
    return [{"id": str(d.id), "descricao": d.descricao, "fornecedor": d.fornecedor, "valor_total": float(d.valor_total), "data_vencimento": d.data_vencimento.isoformat()} for d in linhas]


@router.get("/ordens-pagamento")
async def listar_ordens_pagamento(
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_session),
):
    """Lista os lotes de pagamento do tenant para acompanhamento da homologação."""
    from financeiro.models.ordem_pagamento import OrdemPagamento
    from financeiro.models.conciliacao import ContaBancaria

    linhas = (
        await db.execute(
            select(OrdemPagamento, ContaBancaria.nome)
            .join(ContaBancaria, ContaBancaria.id == OrdemPagamento.conta_bancaria_id)
            .where(OrdemPagamento.tenant_id == tenant_id)
            .order_by(OrdemPagamento.created_at.desc())
        )
    ).all()
    return [
        {
            "id": str(ordem.id),
            "status": ordem.status,
            "ambiente": ordem.ambiente,
            "banco_codigo": ordem.banco_codigo,
            "conta_nome": conta_nome,
            "data_pagamento": ordem.data_pagamento.isoformat(),
            "total_valor": float(ordem.total_valor),
            "created_at": ordem.created_at.isoformat(),
        }
        for ordem, conta_nome in linhas
    ]


@router.post(
    "/ordens-pagamento",
    dependencies=[Depends(require_tenant_permission("financeiro:*"))],
)
async def criar_ordem_pagamento(dados: CriarOrdemRequest, tenant_id: uuid.UUID = Depends(get_tenant_id), db: AsyncSession = Depends(get_session)):
    from financeiro.models.ordem_pagamento import OrdemPagamento, ItemOrdemPagamento
    from financeiro.models.despesa import Despesa
    if not dados.despesa_ids:
        raise HTTPException(status_code=400, detail="Selecione ao menos um título para a ordem de pagamento.")
    if len(dados.despesa_ids) != len(set(dados.despesa_ids)):
        raise HTTPException(status_code=400, detail="Há títulos duplicados na seleção.")
    svc = ConciliacaoService(db, tenant_id)
    conta = await svc.validar_remessa(dados.conta_bancaria_id)
    despesas = list((await db.execute(select(Despesa).where(Despesa.tenant_id == tenant_id, Despesa.id.in_(dados.despesa_ids), Despesa.status == "LIBERADO_PAGAMENTO"))).scalars().all())
    if len(despesas) != len(set(dados.despesa_ids)):
        raise HTTPException(status_code=400, detail="Selecione somente títulos liberados para pagamento.")
    ordem = OrdemPagamento(tenant_id=tenant_id, conta_bancaria_id=conta.id, data_pagamento=date.today(), banco_codigo=conta.banco or "", ambiente="HOMOLOGACAO", status="PRONTA_PARA_REMESSA", total_valor=sum(float(d.valor_total) for d in despesas))
    db.add(ordem); await db.flush()
    for despesa in despesas:
        db.add(ItemOrdemPagamento(tenant_id=tenant_id, ordem_pagamento_id=ordem.id, despesa_id=despesa.id, valor=despesa.valor_total, forma_pagamento="PIX", favorecido_snapshot=despesa.fornecedor or "Favorecido não informado"))
        despesa.status = "EM_ORDEM_PAGAMENTO"; db.add(despesa)
    await db.commit()
    return {"id": str(ordem.id), "status": ordem.status, "total_valor": float(ordem.total_valor)}


@router.delete(
    "/contas-bancarias/{conta_id}",
    status_code=204,
    dependencies=[Depends(require_tenant_permission("financeiro:*"))],
)
async def excluir_conta_bancaria(
    conta_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_session),
):
    svc = ConciliacaoService(db, tenant_id)
    await svc.excluir_conta(conta_id)
    await db.commit()


# ── Importação OFX ────────────────────────────────────────────────────────────

@router.post(
    "/contas-bancarias/{conta_id}/importar-ofx",
    dependencies=[Depends(require_tenant_permission("financeiro:*"))],
)
async def importar_ofx(
    conta_id: uuid.UUID,
    arquivo: UploadFile = File(...),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_session),
):
    content_bytes = await arquivo.read()
    # Tenta UTF-8 com fallback para latin-1 (bancos brasileiros legados)
    try:
        content = content_bytes.decode("utf-8")
    except UnicodeDecodeError:
        content = content_bytes.decode("latin-1")

    svc = ConciliacaoService(db, tenant_id)
    resultado = await svc.importar_ofx(conta_id, content)
    await db.commit()
    return resultado


# ── Lançamentos e Conciliação ─────────────────────────────────────────────────

@router.get("/contas-bancarias/{conta_id}/lancamentos", response_model=List[LancamentoBancarioResponse])
async def listar_lancamentos(
    conta_id: uuid.UUID,
    status: Optional[str] = Query(None, description="NAO_CONCILIADO | CONCILIADO | IGNORADO"),
    data_de: Optional[date] = Query(None),
    data_ate: Optional[date] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_session),
):
    svc = ConciliacaoService(db, tenant_id)
    return await svc.listar_lancamentos(
        conta_id, status=status, data_de=data_de, data_ate=data_ate, skip=skip, limit=limit
    )


@router.get("/contas-bancarias/{conta_id}/sugestoes")
async def sugestoes_conciliacao(
    conta_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_session),
):
    svc = ConciliacaoService(db, tenant_id)
    return await svc.sugerir_conciliacao(conta_id)


@router.patch(
    "/lancamentos/{lancamento_id}/conciliar",
    response_model=LancamentoBancarioResponse,
    dependencies=[Depends(require_tenant_permission("financeiro:*"))],
)
async def conciliar_lancamento(
    lancamento_id: uuid.UUID,
    dados: ConciliarRequest,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_session),
):
    if not dados.despesa_id and not dados.receita_id:
        raise HTTPException(status_code=422, detail="Informe despesa_id ou receita_id para conciliar.")
    svc = ConciliacaoService(db, tenant_id)
    lanc = await svc.conciliar(lancamento_id, despesa_id=dados.despesa_id, receita_id=dados.receita_id)
    await db.commit()
    await db.refresh(lanc)
    return lanc


@router.patch(
    "/lancamentos/{lancamento_id}/ignorar",
    response_model=LancamentoBancarioResponse,
    dependencies=[Depends(require_tenant_permission("financeiro:*"))],
)
async def ignorar_lancamento(
    lancamento_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_session),
):
    from sqlalchemy.future import select
    from financeiro.models.conciliacao import LancamentoBancario
    from core.exceptions import EntityNotFoundError

    stmt = select(LancamentoBancario).where(
        LancamentoBancario.id == lancamento_id,
        LancamentoBancario.tenant_id == tenant_id,
    )
    lanc = (await db.execute(stmt)).scalar_one_or_none()
    if not lanc:
        raise HTTPException(status_code=404, detail="Lançamento indisponível ou não encontrado.")
    lanc.status_conciliacao = "IGNORADO"
    db.add(lanc)
    await db.commit()
    await db.refresh(lanc)
    return lanc


# ── Carnê-Leão ────────────────────────────────────────────────────────────────

@router.get("/carne-leao/exportar")
async def exportar_carne_leao(
    ano: int = Query(..., description="Ano de competência (ex: 2024)"),
    unidade_produtiva_id: Optional[uuid.UUID] = Query(None),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_session),
):
    svc = CarneLeaoService(db, tenant_id)
    csv_content = await svc.exportar_csv(ano, unidade_produtiva_id=unidade_produtiva_id)
    filename = f"carne_leao_{ano}.csv"
    return StreamingResponse(
        io.StringIO(csv_content),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── API Contábil ─────────────────────────────────────────────────────────────

@router.get("/contabil/resumo")
async def resumo_contabil(
    data_inicio: date = Query(...),
    data_fim: date = Query(...),
    unidade_produtiva_id: Optional[uuid.UUID] = Query(None),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_session),
):
    svc = ContabilService(db, tenant_id)
    return await svc.resumo(data_inicio, data_fim, unidade_produtiva_id=unidade_produtiva_id)
