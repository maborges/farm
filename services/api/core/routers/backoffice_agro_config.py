"""Router administrativo do Backoffice para as configurações globais do DeepFarms Agro.

Endpoints protegidos por RBAC, auditoria compulsória, tipagem Pydantic,
controle otimista de concorrência e invalidação de cache.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_session, require_permission
from core.schemas.agro_config_schemas import (
    KEY_MENSAGENS,
    AgroAllConfigsResponse,
    AgroConfigItemResponse,
    AgroConfigUpdateRequest,
    AgroMensagemCreateRequest,
    AgroMensagemItem,
    AgroMensagemUpdateRequest,
    AgroPublicConfigResponse,
)
from core.services.agro_config_service import (
    DESCRICOES_PADRAO,
    SCHEMA_MAP,
    agro_config_service,
)
from core.services.config_masking import mask_sensitive_data
from public_agro.router import get_resolved_avisos_legais, is_message_in_effect

router = APIRouter(
    prefix="/backoffice/agro/configuracoes",
    tags=["Backoffice — DeepFarms Agro Configurações"],
)


@router.get(
    "",
    response_model=AgroAllConfigsResponse,
    dependencies=[Depends(require_permission("backoffice:agro:config:view"))],
    summary="Lista todas as configurações tipadas do Agro",
    description="Retorna o estado consolidado de Clima, Mercado, Mensagens e Feature Flags.",
)
async def list_all_agro_configs(
    session: AsyncSession = Depends(get_session),
) -> AgroAllConfigsResponse:
    """Retorna todas as configurações canônicas do Agro com metadados de revisão."""
    all_configs = await agro_config_service.get_all_configs(session=session)
    # Mascara dados sensíveis se presentes em qualquer seção
    all_configs.clima.valor = mask_sensitive_data(all_configs.clima.valor, parent_key=all_configs.clima.chave)
    all_configs.mercado.valor = mask_sensitive_data(all_configs.mercado.valor, parent_key=all_configs.mercado.chave)
    all_configs.mensagens.valor = mask_sensitive_data(all_configs.mensagens.valor, parent_key=all_configs.mensagens.chave)
    all_configs.feature_flags.valor = mask_sensitive_data(all_configs.feature_flags.valor, parent_key=all_configs.feature_flags.chave)
    return all_configs


# ==============================================================================
# SUB-ROTAS DE ADMINISTRAÇÃO DE MENSAGENS INSTITUCIONAIS (01E5)
# ==============================================================================

@router.get(
    "/mensagens/lista",
    response_model=list[AgroMensagemItem],
    dependencies=[Depends(require_permission("backoffice:agro:config:view"))],
    summary="Lista todas as mensagens institucionais cadastradas para o Backoffice",
)
async def list_institutional_messages(
    session: AsyncSession = Depends(get_session),
) -> list[AgroMensagemItem]:
    """Retorna o inventário completo de comunicados institucionais incluindo inativos."""
    valor, _, _ = await agro_config_service.get_config(session=session, chave=KEY_MENSAGENS)
    raw_msgs = valor.get("mensagens_institucionais") or []
    return [AgroMensagemItem(**m) if isinstance(m, dict) else m for m in raw_msgs]


@router.post(
    "/mensagens",
    response_model=AgroMensagemItem,
    status_code=status.HTTP_201_CREATED,
    summary="Publica uma nova mensagem ou comunicado institucional",
)
async def create_institutional_message(
    payload: AgroMensagemCreateRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    admin_claims: dict[str, Any] = Depends(require_permission("backoffice:agro:config:edit")),
) -> AgroMensagemItem:
    """Cadastra nova mensagem com tipagem estrita, prioridade e vigência programada."""
    valor, meta, _ = await agro_config_service.get_config(session=session, chave=KEY_MENSAGENS)
    novo_valor = dict(valor)
    raw_msgs = list(novo_valor.get("mensagens_institucionais") or [])

    novo_id = str(uuid.uuid4())
    msg_dict = payload.model_dump()
    msg_dict["id"] = novo_id
    msg_dict["criado_em"] = datetime.now(timezone.utc).isoformat()

    msg_obj = AgroMensagemItem(**msg_dict)
    raw_msgs.append(msg_obj.model_dump())
    novo_valor["mensagens_institucionais"] = raw_msgs

    # Preserva avisos legais mandatórios
    novo_valor["aviso_precos_deral"] = valor.get("aviso_precos_deral") or "Preço médio semanal publicado pelo DERAL."
    novo_valor["aviso_ptax"] = valor.get("aviso_ptax") or "A PTAX é taxa de referência do Banco Central."
    novo_valor["aviso_macro_bcb"] = valor.get("aviso_macro_bcb") or "Dados oficiais BCB e IBGE."
    novo_valor["aviso_ibge"] = valor.get("aviso_ibge") or "Estatística oficial do IBGE."

    await agro_config_service.update_config(
        session=session,
        chave=KEY_MENSAGENS,
        novo_valor=novo_valor,
        admin_claims=admin_claims,
        descricao=f"Publicação de comunicado institucional: {msg_obj.titulo}",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return msg_obj


@router.put(
    "/mensagens/{msg_id}",
    response_model=AgroMensagemItem,
    summary="Atualiza parâmetros de uma mensagem institucional existente",
)
async def update_institutional_message(
    msg_id: str,
    payload: AgroMensagemUpdateRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    admin_claims: dict[str, Any] = Depends(require_permission("backoffice:agro:config:edit")),
) -> AgroMensagemItem:
    """Atualiza metadados, vigência ou ativação de uma mensagem com auditoria."""
    valor, _, _ = await agro_config_service.get_config(session=session, chave=KEY_MENSAGENS)
    novo_valor = dict(valor)
    raw_msgs = list(novo_valor.get("mensagens_institucionais") or [])

    encontrado = False
    msg_atualizada: Optional[AgroMensagemItem] = None

    for i, raw in enumerate(raw_msgs):
        item_id = raw.get("id") if isinstance(raw, dict) else getattr(raw, "id", None)
        if str(item_id) == str(msg_id):
            encontrado = True
            current_dict = dict(raw) if isinstance(raw, dict) else raw.model_dump()
            update_data = payload.model_dump(exclude_unset=True)
            current_dict.update(update_data)
            msg_atualizada = AgroMensagemItem(**current_dict)
            raw_msgs[i] = msg_atualizada.model_dump()
            break

    if not encontrado or msg_atualizada is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Mensagem institucional '{msg_id}' não encontrada.",
        )

    novo_valor["mensagens_institucionais"] = raw_msgs

    await agro_config_service.update_config(
        session=session,
        chave=KEY_MENSAGENS,
        novo_valor=novo_valor,
        admin_claims=admin_claims,
        descricao=f"Atualização do comunicado institucional: {msg_atualizada.titulo}",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return msg_atualizada


@router.delete(
    "/mensagens/{msg_id}",
    summary="Remove uma mensagem institucional do catálogo",
)
async def delete_institutional_message(
    msg_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
    admin_claims: dict[str, Any] = Depends(require_permission("backoffice:agro:config:edit")),
) -> dict[str, Any]:
    """Exclui comunicado institucional da lista ativa com gravação de auditoria."""
    valor, _, _ = await agro_config_service.get_config(session=session, chave=KEY_MENSAGENS)
    novo_valor = dict(valor)
    raw_msgs = list(novo_valor.get("mensagens_institucionais") or [])

    novos_msgs = [m for m in raw_msgs if str(m.get("id") if isinstance(m, dict) else getattr(m, "id", None)) != str(msg_id)]
    if len(novos_msgs) == len(raw_msgs):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Mensagem institucional '{msg_id}' não encontrada.",
        )

    novo_valor["mensagens_institucionais"] = novos_msgs

    await agro_config_service.update_config(
        session=session,
        chave=KEY_MENSAGENS,
        novo_valor=novo_valor,
        admin_claims=admin_claims,
        descricao=f"Remoção de mensagem institucional: {msg_id}",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return {"sucesso": True, "mensagem": f"Mensagem '{msg_id}' removida com sucesso."}


@router.get(
    "/mensagens/preview",
    response_model=dict[str, Any],
    dependencies=[Depends(require_permission("backoffice:agro:config:view"))],
    summary="Pré-visualização do estado público das mensagens em um instante de tempo",
)
async def preview_institutional_messages(
    ref_iso: Optional[str] = Query(default=None, description="Instante ISO 8601 de referência para simular vigência"),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Permite aos operadores simular como o DeepFarms Agro exibirá os avisos no momento especificado."""
    valor, _, _ = await agro_config_service.get_config(session=session, chave=KEY_MENSAGENS)
    raw_msgs = valor.get("mensagens_institucionais") or []

    ref_time = datetime.now(timezone.utc)
    if ref_iso:
        try:
            parsed = datetime.fromisoformat(ref_iso.replace("Z", "+00:00"))
            ref_time = parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except Exception:
            pass

    vigentes = []
    for item in raw_msgs:
        try:
            msg = AgroMensagemItem(**item) if isinstance(item, dict) else item
            if is_message_in_effect(msg, ref_time=ref_time):
                vigentes.append(msg)
        except Exception:
            continue

    vigentes.sort(key=lambda m: (m.prioridade, m.criado_em), reverse=False)

    return {
        "referencia_simulada": ref_time.isoformat(),
        "total_vigentes": len(vigentes),
        "banner_urgente": valor.get("banner_urgente"),
        "avisos_legais": get_resolved_avisos_legais(valor),
        "mensagens": vigentes,
    }





@router.get(
    "/{chave}",
    response_model=AgroConfigItemResponse,
    dependencies=[Depends(require_permission("backoffice:agro:config:view"))],
    summary="Obtém uma configuração específica do Agro",
)
async def get_agro_config(
    chave: str,
    session: AsyncSession = Depends(get_session),
) -> AgroConfigItemResponse:
    """Busca o valor atual e metadados de uma chave conhecida do Agro."""
    if chave not in SCHEMA_MAP:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Chave '{chave}' não é reconhecida no namespace agro:*",
        )

    valor, meta, ativo = await agro_config_service.get_config(session=session, chave=chave)
    return AgroConfigItemResponse(
        chave=chave,
        valor=mask_sensitive_data(valor, parent_key=chave),
        meta=meta,
        descricao=DESCRICOES_PADRAO.get(chave, "Configuração do Agro"),
        ativo=ativo,
    )


@router.put(
    "/{chave}",
    response_model=AgroConfigItemResponse,
    summary="Atualiza uma configuração do Agro com validação e controle de concorrência",
)
async def update_agro_config(
    chave: str,
    data: AgroConfigUpdateRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    admin_claims: dict[str, Any] = Depends(require_permission("backoffice:agro:config:edit")),
) -> AgroConfigItemResponse:
    """Atualiza a configuração com controle otimista de concorrência e gravação de auditoria."""
    record, meta = await agro_config_service.update_config(
        session=session,
        chave=chave,
        novo_valor=data.valor,
        admin_claims=admin_claims,
        expected_revision=data.expected_revision,
        descricao=data.descricao,
        ativo=data.ativo,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    clean_val = {k: v for k, v in record.valor.items() if not k.startswith("_")}
    return AgroConfigItemResponse(
        chave=record.chave,
        valor=mask_sensitive_data(clean_val, parent_key=record.chave),
        meta=meta,
        descricao=record.descricao,
        ativo=record.ativo,
    )


@router.post(
    "/cache/clear",
    summary="Invalida forçadamente os caches de configurações do Agro",
)
async def clear_agro_configs_cache(
    admin_claims: dict[str, Any] = Depends(require_permission("backoffice:agro:config:edit")),
) -> dict[str, str]:
    """Limpa o cache em memória local e publica sinal de expiração geral no Redis."""
    del admin_claims
    agro_config_service.invalidate_local_cache()
    await agro_config_service._notify_redis_invalidation(chave="*", revision=-1)
    return {"message": "Cache de configurações do Agro invalidado com sucesso."}
