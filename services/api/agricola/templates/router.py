from core.dependencies import require_tenant_permission
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import List

from core.constants import PlanTier
from core.dependencies import get_current_user, get_session, get_tenant_id, require_module, require_tier
from agricola.templates.schemas import (
    PhaseTemplateRead, PhaseTemplateDetail, PhaseTemplateCreate, PhaseTemplateUpdate,
    OperationTemplateRead, OperationTemplateDetail, OperationTemplateCreate, OperationTemplateUpdate,
    ApplyPhaseTemplateRequest, ApplyOperationTemplateRequest,
    PhaseTemplateChecklistItemRead, PhaseTemplateChecklistItemCreate, PhaseTemplateChecklistItemUpdate,
    PhaseTemplateTaskRead, PhaseTemplateTaskCreate, PhaseTemplateTaskUpdate,
    PhaseGateRuleRead, PhaseGateRuleCreate,
    OperationTemplateItemRead, OperationTemplateItemCreate, OperationTemplateItemUpdate,
)
from agricola.templates.service import (
    PhaseTemplateService, OperationTemplateService, TemplateApplicationService
)

router = APIRouter(
    prefix="/templates",
    tags=["Templates Agrícolas"],
    dependencies=[
        Depends(require_module("A1_PLANEJAMENTO")),
        Depends(require_tier(PlanTier.PROFISSIONAL)),
    ],
)


# --- Phase Templates ---

@router.get("/phase", response_model=List[PhaseTemplateRead])
async def listar_phase_templates(
    cultura: str | None = None,
    fase: str | None = None,
    db: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _permission: None = Depends(require_tenant_permission("agricola:template:listar")),
):
    service = PhaseTemplateService(db, tenant_id)
    return await service.listar(cultura, fase)

@router.get("/phase/{id}", response_model=PhaseTemplateDetail)
async def obter_phase_template(
    id: UUID,
    db: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _permission: None = Depends(require_tenant_permission("agricola:template:listar")),
):
    service = PhaseTemplateService(db, tenant_id)
    return await service.get_with_details(id)

@router.post("/phase", response_model=PhaseTemplateRead)
async def criar_phase_template(
    dados: PhaseTemplateCreate,
    db: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _permission: None = Depends(require_tenant_permission("agricola:template:criar")),
):
    service = PhaseTemplateService(db, tenant_id)
    obj = await service.create(dados)
    await db.commit()
    await db.refresh(obj)
    return obj

@router.put("/phase/{id}", response_model=PhaseTemplateRead)
async def atualizar_phase_template(
    id: UUID,
    dados: PhaseTemplateUpdate,
    db: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _permission: None = Depends(require_tenant_permission("agricola:template:editar")),
):
    service = PhaseTemplateService(db, tenant_id)
    obj = await service.atualizar(id, dados)
    await db.commit()
    await db.refresh(obj)
    return obj

@router.delete("/phase/{id}")
async def excluir_phase_template(
    id: UUID,
    db: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _permission: None = Depends(require_tenant_permission("agricola:template:excluir")),
):
    service = PhaseTemplateService(db, tenant_id)
    await service.excluir(id)
    await db.commit()
    return {"status": "success"}

@router.post("/phase/{id}/duplicate", response_model=PhaseTemplateRead)
async def duplicar_phase_template(
    id: UUID,
    db: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _permission: None = Depends(require_tenant_permission("agricola:template:criar")),
):
    service = PhaseTemplateService(db, tenant_id)
    obj = await service.duplicar_global(id)
    await db.commit()
    await db.refresh(obj)
    return obj


# --- Itens de Phase Template (Tenant) ---

@router.post("/phase/{template_id}/checklist-items", response_model=PhaseTemplateChecklistItemRead)
async def criar_phase_checklist_item(
    template_id: UUID,
    dados: PhaseTemplateChecklistItemCreate,
    db: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _permission: None = Depends(require_tenant_permission("agricola:template:editar")),
):
    service = PhaseTemplateService(db, tenant_id)
    item = await service.criar_checklist_item(template_id, dados)
    await db.commit()
    await db.refresh(item)
    return item

@router.put("/phase/{template_id}/checklist-items/{item_id}", response_model=PhaseTemplateChecklistItemRead)
async def atualizar_phase_checklist_item(
    template_id: UUID,
    item_id: UUID,
    dados: PhaseTemplateChecklistItemUpdate,
    db: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _permission: None = Depends(require_tenant_permission("agricola:template:editar")),
):
    service = PhaseTemplateService(db, tenant_id)
    item = await service.atualizar_checklist_item(template_id, item_id, dados)
    await db.commit()
    await db.refresh(item)
    return item

@router.delete("/phase/{template_id}/checklist-items/{item_id}")
async def excluir_phase_checklist_item(
    template_id: UUID,
    item_id: UUID,
    db: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _permission: None = Depends(require_tenant_permission("agricola:template:editar")),
):
    service = PhaseTemplateService(db, tenant_id)
    await service.excluir_checklist_item(template_id, item_id)
    await db.commit()
    return {"status": "success"}

@router.post("/phase/{template_id}/tasks", response_model=PhaseTemplateTaskRead)
async def criar_phase_task(
    template_id: UUID,
    dados: PhaseTemplateTaskCreate,
    db: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _permission: None = Depends(require_tenant_permission("agricola:template:editar")),
):
    service = PhaseTemplateService(db, tenant_id)
    task = await service.criar_task(template_id, dados)
    await db.commit()
    await db.refresh(task)
    return task

@router.put("/phase/{template_id}/tasks/{task_id}", response_model=PhaseTemplateTaskRead)
async def atualizar_phase_task(
    template_id: UUID,
    task_id: UUID,
    dados: PhaseTemplateTaskUpdate,
    db: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _permission: None = Depends(require_tenant_permission("agricola:template:editar")),
):
    service = PhaseTemplateService(db, tenant_id)
    task = await service.atualizar_task(template_id, task_id, dados)
    await db.commit()
    await db.refresh(task)
    return task

@router.delete("/phase/{template_id}/tasks/{task_id}")
async def excluir_phase_task(
    template_id: UUID,
    task_id: UUID,
    db: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _permission: None = Depends(require_tenant_permission("agricola:template:editar")),
):
    service = PhaseTemplateService(db, tenant_id)
    await service.excluir_task(template_id, task_id)
    await db.commit()
    return {"status": "success"}


# --- Operation Templates ---

@router.get("/operations", response_model=List[OperationTemplateRead])
async def listar_operation_templates(
    cultura: str | None = None,
    fase: str | None = None,
    db: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _permission: None = Depends(require_tenant_permission("agricola:template:listar")),
):
    service = OperationTemplateService(db, tenant_id)
    return await service.listar(cultura, fase)

@router.get("/operations/{id}", response_model=OperationTemplateDetail)
async def obter_operation_template(
    id: UUID,
    db: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _permission: None = Depends(require_tenant_permission("agricola:template:listar")),
):
    service = OperationTemplateService(db, tenant_id)
    return await service.get_with_details(id)

@router.post("/operations", response_model=OperationTemplateRead)
async def criar_operation_template(
    dados: OperationTemplateCreate,
    db: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _permission: None = Depends(require_tenant_permission("agricola:template:criar")),
):
    service = OperationTemplateService(db, tenant_id)
    obj = await service.create(dados)
    await db.commit()
    await db.refresh(obj)
    return obj

@router.put("/operations/{id}", response_model=OperationTemplateRead)
async def atualizar_operation_template(
    id: UUID,
    dados: OperationTemplateUpdate,
    db: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _permission: None = Depends(require_tenant_permission("agricola:template:editar")),
):
    service = OperationTemplateService(db, tenant_id)
    obj = await service.atualizar(id, dados)
    await db.commit()
    await db.refresh(obj)
    return obj

@router.delete("/operations/{id}")
async def excluir_operation_template(
    id: UUID,
    db: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _permission: None = Depends(require_tenant_permission("agricola:template:excluir")),
):
    service = OperationTemplateService(db, tenant_id)
    await service.excluir(id)
    await db.commit()
    return {"status": "success"}

@router.post("/operations/{id}/duplicate", response_model=OperationTemplateRead)
async def duplicar_operation_template(
    id: UUID,
    db: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _permission: None = Depends(require_tenant_permission("agricola:template:criar")),
):
    service = OperationTemplateService(db, tenant_id)
    obj = await service.duplicar_global(id)
    await db.commit()
    await db.refresh(obj)
    return obj


# --- Itens de Operation Template (Tenant) ---

@router.post("/operations/{template_id}/items", response_model=OperationTemplateItemRead)
async def criar_operation_template_item(
    template_id: UUID,
    dados: OperationTemplateItemCreate,
    db: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _permission: None = Depends(require_tenant_permission("agricola:template:editar")),
):
    service = OperationTemplateService(db, tenant_id)
    item = await service.criar_item(template_id, dados)
    await db.commit()
    await db.refresh(item)
    return item

@router.put("/operations/{template_id}/items/{item_id}", response_model=OperationTemplateItemRead)
async def atualizar_operation_template_item(
    template_id: UUID,
    item_id: UUID,
    dados: OperationTemplateItemUpdate,
    db: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _permission: None = Depends(require_tenant_permission("agricola:template:editar")),
):
    service = OperationTemplateService(db, tenant_id)
    item = await service.atualizar_item(template_id, item_id, dados)
    await db.commit()
    await db.refresh(item)
    return item

@router.delete("/operations/{template_id}/items/{item_id}")
async def excluir_operation_template_item(
    template_id: UUID,
    item_id: UUID,
    db: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _permission: None = Depends(require_tenant_permission("agricola:template:editar")),
):
    service = OperationTemplateService(db, tenant_id)
    await service.excluir_item(template_id, item_id)
    await db.commit()
    return {"status": "success"}


# --- Ações de Aplicação ---

@router.post("/apply/phase")
async def aplicar_template_fase(
    dados: ApplyPhaseTemplateRequest,
    db: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id)
):
    service = TemplateApplicationService(db, tenant_id)
    result = await service.aplicar_fase(dados.safra_id, dados.phase_template_id)
    await db.commit()
    return result

@router.post("/apply/operations")
async def aplicar_template_operacoes(
    dados: ApplyOperationTemplateRequest,
    db: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id)
):
    service = TemplateApplicationService(db, tenant_id)
    result = await service.aplicar_operacoes(dados.safra_id, dados.operation_template_id, dados.talhao_ids)
    await db.commit()
    return result
