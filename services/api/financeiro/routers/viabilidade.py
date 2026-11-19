from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends

from core.dependencies import get_tenant_id, require_module
from financeiro.schemas.viabilidade_schema import (
    ComparativoViabilidadeInput,
    ComparativoViabilidadeOutput,
    PrecoEquilibrioTmaInput,
    PrecoEquilibrioTmaOutput,
    TemplateProjetoAgroOutput,
    TmaCalculoInput,
    TmaCalculoOutput,
)
from financeiro.services.viabilidade_service import ViabilidadeFinanceiraService

MODULE_DEPENDENCY = require_module("F1_TESOURARIA")
router = APIRouter(
    prefix="/viabilidade",
    tags=["Financeiro — Viabilidade de Investimentos"],
    dependencies=[Depends(MODULE_DEPENDENCY)],
)


@router.get("/templates", response_model=list[TemplateProjetoAgroOutput])
async def listar_templates_viabilidade(
    _tenant_id: uuid.UUID = Depends(get_tenant_id),
) -> list[TemplateProjetoAgroOutput]:
    """Lista cenários de referência do agronegócio para simulação comparativa."""
    return ViabilidadeFinanceiraService.listar_templates_agro()


@router.post("/calcular-tma", response_model=TmaCalculoOutput)
async def calcular_tma(
    payload: TmaCalculoInput,
    _tenant_id: uuid.UUID = Depends(get_tenant_id),
) -> TmaCalculoOutput:
    """Calcula a Taxa Mínima de Atratividade (TMA) ponderada com prêmio de risco."""
    return ViabilidadeFinanceiraService().calcular_tma(payload)


@router.post("/simular", response_model=ComparativoViabilidadeOutput)
async def simular_viabilidade(
    payload: ComparativoViabilidadeInput,
    _tenant_id: uuid.UUID = Depends(get_tenant_id),
) -> ComparativoViabilidadeOutput:
    """Executa análise comparativa de VPL, TIR, TIRM e Payback Simples/Descontado."""
    return ViabilidadeFinanceiraService().comparar_projetos(payload)


@router.post("/preco-equilibrio-tma", response_model=PrecoEquilibrioTmaOutput)
async def calcular_preco_equilibrio_tma(
    payload: PrecoEquilibrioTmaInput,
    _tenant_id: uuid.UUID = Depends(get_tenant_id),
) -> PrecoEquilibrioTmaOutput:
    """Calcula preço de equilíbrio contábil vs. econômico (TMA) e sensibilidade cambial."""
    return ViabilidadeFinanceiraService.calcular_preco_equilibrio_tma(payload)
