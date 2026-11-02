import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_current_user, get_session, get_tenant_id
from pecuaria.services.manejo_sync_service import ManejoSyncService, ManejoSyncResult


from typing import Optional
from datetime import date
from sqlalchemy import select, func, text, desc

from pecuaria.schemas.campo_sync_schema import SyncStatusResponse, SyncStatusPaginatedResponse
from campo.models import TarefaCampo

router = APIRouter()

@router.get(
    "/sync-status",
    response_model=SyncStatusPaginatedResponse,
    summary="Lista o status de sincronização de tarefas pecuárias",
    description="Retorna as tarefas de campo com module='pecuaria' e seus respectivos status de processamento extraídos do JSONB."
)
async def list_sync_status(
    status_processamento: Optional[str] = None,
    type: Optional[str] = None,
    lote_id: Optional[uuid.UUID] = None,
    operador_id: Optional[uuid.UUID] = None,
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
    page: int = 1,
    page_size: int = 50,
    db: AsyncSession = Depends(get_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user),
):
    query = select(TarefaCampo).where(
        TarefaCampo.tenant_id == tenant_id,
        TarefaCampo.module == "pecuaria"
    )

    if type:
        query = query.where(TarefaCampo.type == type)
    if lote_id:
        query = query.where(TarefaCampo.lote_id == lote_id)
    if operador_id:
        query = query.where(TarefaCampo.operador_id == operador_id)
    if data_inicio:
        query = query.where(func.date(TarefaCampo.concluida_em) >= data_inicio)
    if data_fim:
        query = query.where(func.date(TarefaCampo.concluida_em) <= data_fim)

    if status_processamento:
        if status_processamento == "PENDENTE":
            # Não tem a chave 'sync_pecuaria' ou 'status' dentro
            query = query.where(
                text("campo_tarefas.dados->'sync_pecuaria' IS NULL OR campo_tarefas.dados->'sync_pecuaria'->>'status' IS NULL")
            )
        else:
            query = query.where(
                text(f"campo_tarefas.dados->'sync_pecuaria'->>'status' = :status")
            ).params(status=status_processamento)

    # Contagem total
    count_query = select(func.count()).select_from(query.subquery())
    total_res = await db.execute(count_query)
    total = total_res.scalar() or 0

    # Paginação e ordenação (mais recentes primeiro)
    query = query.order_by(TarefaCampo.concluida_em.desc().nulls_last(), desc(TarefaCampo.created_at))
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    tarefas = result.scalars().all()

    items = []
    for t in tarefas:
        sync_meta = t.dados.get("sync_pecuaria", {})
        
        status_proc = sync_meta.get("status")
        # Se concluiu e não tem status de proc, é PENDENTE
        if not status_proc:
            status_proc = "PENDENTE" if t.status_execucao == "CONCLUIDA" else "AGUARDANDO_CAMPO"
            
        erros_list = sync_meta.get("erros", [])
        mensagem_erro = erros_list[0] if erros_list else None
        
        # Converte data_processamento se existir
        dp_str = sync_meta.get("data_processamento")
        data_proc = None
        if dp_str:
            from datetime import datetime
            try:
                data_proc = datetime.fromisoformat(dp_str)
            except ValueError:
                pass

        items.append(SyncStatusResponse(
            tarefa_campo_id=t.id,
            type=t.type,
            status_tarefa=t.status_execucao,
            status_processamento=status_proc,
            total_processado=sync_meta.get("total_processado", 0),
            total_erros=len(erros_list),
            mensagem_erro=mensagem_erro,
            operador_id=t.operador_id,
            lote_id=t.lote_id,
            data_execucao=t.concluida_em,
            data_processamento=data_proc
        ))

    total_pages = (total + page_size - 1) // page_size

    return SyncStatusPaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )

@router.post(
    "/tarefas/{tarefa_campo_id}/processar",
    response_model=ManejoSyncResult,
    summary="Processa uma tarefa de campo da Pecuária (ex: Pesagem)",
    description="Aciona o motor de sincronização assíncrona (ManejoSyncService) para converter uma TarefaCampo em Eventos zootécnicos (EventoAnimal)."
)
async def processar_tarefa_campo(
    tarefa_campo_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user),
):
    service = ManejoSyncService(db, tenant_id)
    
    # Delegate to the service. The service itself checks if it belongs to the tenant.
    # Note: If the task belongs to another tenant, the service handles it via its internal 
    # query (`TarefaCampo.tenant_id == self.tenant_id`). It returns IGNORED or ERROR.
    # Actually, the user asked for:
    # "tarefa de outro tenant não pode ser processada"
    # The service returns IGNORED if not found in the tenant. We can just return that,
    # or explicitly return 404. Let's rely on the service behavior as returning 200 with ManejoSyncResult,
    # but for 404, we can raise HTTPException if the task is completely completely missing.
    # The service returns:
    # status="IGNORED", erros=["Tarefa não encontrada ou não pertence ao tenant."]
    # Wait, the prompt says "Bloquear tarefa de outro tenant (HTTP 404/403)".
    # Let's intercept that specific error and return 404!

    result = await service.processar_tarefa_campo(tarefa_campo_id)
    
    if result.status == "IGNORED" and any("não encontrada ou não pertence ao tenant" in e for e in result.erros):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tarefa não encontrada ou não pertence ao tenant atual.")

    return result
