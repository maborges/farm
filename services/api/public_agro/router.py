"""Roteador FastAPI público de configurações, mensagens institucionais e feature flags do DeepFarms Agro."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Query, Response, status

from core.schemas.agro_config_schemas import (
    KEY_FLAGS,
    KEY_MENSAGENS,
    AgroFeatureFlagsConfig,
    AgroMensagensAvisosConfig,
    AgroMensagemItem,
    AgroPublicConfigResponse,
)
from core.services.agro_config_service import agro_config_service

router = APIRouter(prefix="/public/agro", tags=["Agro - Configurações Públicas & PWA"])

_DEFAULT_AVISOS = AgroMensagensAvisosConfig()


def is_message_in_effect(msg: AgroMensagemItem, ref_time: Optional[datetime] = None) -> bool:
    """Verifica se uma mensagem institucional está ativa e dentro da vigência temporal especificada."""
    if not msg.ativo:
        return False

    now = ref_time or datetime.now(timezone.utc)

    if msg.vigencia_inicio:
        try:
            inicio = datetime.fromisoformat(msg.vigencia_inicio.replace("Z", "+00:00"))
            if inicio.tzinfo is None:
                inicio = inicio.replace(tzinfo=timezone.utc)
            if now < inicio:
                return False
        except (ValueError, TypeError):
            pass

    if msg.vigencia_fim:
        try:
            fim = datetime.fromisoformat(msg.vigencia_fim.replace("Z", "+00:00"))
            if fim.tzinfo is None:
                fim = fim.replace(tzinfo=timezone.utc)
            if now > fim:
                return False
        except (ValueError, TypeError):
            pass

    return True


def get_resolved_avisos_legais(raw_dict: dict) -> dict[str, str]:
    """Retorna os avisos legais obrigatórios, preservando garantias regulatórias contra remoção acidental."""
    return {
        "aviso_precos_deral": raw_dict.get("aviso_precos_deral") or _DEFAULT_AVISOS.aviso_precos_deral,
        "aviso_ptax": raw_dict.get("aviso_ptax") or _DEFAULT_AVISOS.aviso_ptax,
        "aviso_macro_bcb": raw_dict.get("aviso_macro_bcb") or _DEFAULT_AVISOS.aviso_macro_bcb,
        "aviso_ibge": raw_dict.get("aviso_ibge") or _DEFAULT_AVISOS.aviso_ibge,
    }


@router.get(
    "/config",
    response_model=AgroPublicConfigResponse,
    summary="Configuração pública de bootstrap do DeepFarms Agro",
    description=(
        "Retorna as Feature Flags operacionais, avisos legais mandatórios, "
        "banner urgente e comunicados institucionais vigentes para consumo pelo PWA."
    ),
)
async def get_public_agro_config(response: Response) -> AgroPublicConfigResponse:
    """Carrega as configurações públicas do Agro a partir do cache central de alta performance."""
    flags_raw = agro_config_service.get_cached_config_dict(KEY_FLAGS) or {}
    mensagens_raw = agro_config_service.get_cached_config_dict(KEY_MENSAGENS) or {}

    flags = AgroFeatureFlagsConfig(**flags_raw) if flags_raw else AgroFeatureFlagsConfig()
    banner_urgente = mensagens_raw.get("banner_urgente")

    raw_items = mensagens_raw.get("mensagens_institucionais") or []
    mensagens_vigentes: list[AgroMensagemItem] = []
    now = datetime.now(timezone.utc)

    for item in raw_items:
        try:
            msg = AgroMensagemItem(**item) if isinstance(item, dict) else item
            if is_message_in_effect(msg, ref_time=now):
                mensagens_vigentes.append(msg)
        except Exception:
            continue

    mensagens_vigentes.sort(key=lambda m: (m.prioridade, m.criado_em), reverse=False)

    avisos_legais = get_resolved_avisos_legais(mensagens_raw)

    response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=300"

    return AgroPublicConfigResponse(
        sucesso=True,
        versao="1.0",
        consultado_em=now.isoformat(),
        feature_flags=flags,
        banner_urgente=banner_urgente,
        mensagens_vigentes=mensagens_vigentes,
        avisos_legais=avisos_legais,
    )


@router.get(
    "/mensagens",
    response_model=list[AgroMensagemItem],
    summary="Consulta mensagens institucionais ativas e vigentes",
)
async def get_public_mensagens(
    response: Response,
    finalidade: Optional[str] = Query(default=None, description="Filtro opcional por finalidade"),
) -> list[AgroMensagemItem]:
    """Retorna os comunicados vigentes filtrados por finalidade com ordenação por prioridade."""
    mensagens_raw = agro_config_service.get_cached_config_dict(KEY_MENSAGENS) or {}
    raw_items = mensagens_raw.get("mensagens_institucionais") or []
    now = datetime.now(timezone.utc)

    resultado: list[AgroMensagemItem] = []
    for item in raw_items:
        try:
            msg = AgroMensagemItem(**item) if isinstance(item, dict) else item
            if is_message_in_effect(msg, ref_time=now):
                if finalidade and msg.finalidade != finalidade.upper():
                    continue
                resultado.append(msg)
        except Exception:
            continue

    resultado.sort(key=lambda m: (m.prioridade, m.criado_em), reverse=False)
    response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=300"
    return resultado


@router.get(
    "/feature-flags",
    response_model=AgroFeatureFlagsConfig,
    summary="Consulta direta de Feature Flags ativas",
)
async def get_public_feature_flags(response: Response) -> AgroFeatureFlagsConfig:
    """Retorna as feature flags vigentes do aplicativo DeepFarms Agro."""
    flags_raw = agro_config_service.get_cached_config_dict(KEY_FLAGS) or {}
    flags = AgroFeatureFlagsConfig(**flags_raw) if flags_raw else AgroFeatureFlagsConfig()
    response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=300"
    return flags


@router.get(
    "/avisos-legais",
    response_model=dict[str, str],
    summary="Consulta avisos legais e regulatórios vigentes",
)
async def get_public_avisos_legais(response: Response) -> dict[str, str]:
    """Retorna os avisos legais obrigatórios vigentes."""
    mensagens_raw = agro_config_service.get_cached_config_dict(KEY_MENSAGENS) or {}
    avisos = get_resolved_avisos_legais(mensagens_raw)
    response.headers["Cache-Control"] = "public, max-age=3600, stale-while-revalidate=86400"
    return avisos
