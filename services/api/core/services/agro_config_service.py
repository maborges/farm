"""Serviço de gerenciamento de configurações tipadas do DeepFarms Agro.

Implementa:
1. Leitura com fallback para valores padrão canônicos.
2. Validação sintática e semântica com Pydantic.
3. Controle otimista de concorrência com número de revisão persistente.
4. Auditoria atômica compulsória em AdminAuditLog.
5. Cache local em memória com TTL de 30s.
6. Invalidação distribuída via Redis Pub/Sub com degradação graciosa.
"""

from __future__ import annotations

import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Optional, Type

from fastapi import HTTPException, status
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.models.admin_audit_log import AdminAuditLog
from core.models.configuration import ConfiguracaoSaaS
from core.schemas.agro_config_schemas import (
    AgroAllConfigsResponse,
    AgroClimaConfig,
    AgroConfigItemResponse,
    AgroConfigMetadata,
    AgroFeatureFlagsConfig,
    AgroMensagensAvisosConfig,
    AgroMercadoConfig,
)
from core.services.config_masking import mask_sensitive_data
from core.services.admin_audit_service import resolve_admin_identity

# Chaves canônicas do Agro
KEY_CLIMA = "agro:clima:config"
KEY_MERCADO = "agro:mercado:config"
KEY_MENSAGENS = "agro:mensagens:avisos"
KEY_FLAGS = "agro:feature_flags"

SCHEMA_MAP: dict[str, Type[Any]] = {
    KEY_CLIMA: AgroClimaConfig,
    KEY_MERCADO: AgroMercadoConfig,
    KEY_MENSAGENS: AgroMensagensAvisosConfig,
    KEY_FLAGS: AgroFeatureFlagsConfig,
}

DESCRICOES_PADRAO: dict[str, str] = {
    KEY_CLIMA: "Políticas e parâmetros operacionais do subsistema de clima do Agro",
    KEY_MERCADO: "Políticas de cache e snapshots de mercado e cotações do Agro",
    KEY_MENSAGENS: "Avisos legais regulatórios e banners de utilidade pública do Agro",
    KEY_FLAGS: "Feature flags operacionais das funcionalidades do DeepFarms Agro",
}

DEFAULT_LOCAL_TTL_SECONDS = 30.0
REDIS_CHANNEL_CONFIG_EVENTS = "agro:config:events"


def extrair_admin_identity(claims_or_user: Any) -> tuple[uuid.UUID, str]:
    """Extrai UUID e e-mail do operador a partir dos claims JWT ou modelo de usuário."""
    if isinstance(claims_or_user, dict):
        admin_sub = claims_or_user.get("sub") or claims_or_user.get("id")
        admin_email = (
            claims_or_user.get("email")
            or claims_or_user.get("username")
            or "operador@deepfarms.com"
        )
    else:
        admin_sub = getattr(claims_or_user, "id", None)
        admin_email = getattr(claims_or_user, "email", None) or getattr(
            claims_or_user, "username", "operador@deepfarms.com"
        )
    try:
        admin_uid = uuid.UUID(str(admin_sub))
    except (ValueError, TypeError):
        admin_uid = uuid.uuid4()
    return admin_uid, str(admin_email)


class AgroConfigService:
    """Orquestrador central de configurações tipadas, versionamento e cache do Agro."""

    def __init__(self, ttl_seconds: float = DEFAULT_LOCAL_TTL_SECONDS) -> None:
        self.ttl_seconds = ttl_seconds
        # Estrutura do cache local: chave -> (valor_dict, AgroConfigMetadata, timestamp_expiracao, ativo)
        self._local_cache: dict[str, tuple[dict[str, Any], AgroConfigMetadata, float, bool]] = {}

    def invalidate_local_cache(self, chave: str | None = None) -> None:
        """Limpa o cache local em memória."""
        if chave:
            self._local_cache.pop(chave, None)
        else:
            self._local_cache.clear()

    def get_cached_config_dict(self, chave: str) -> dict[str, Any] | None:
        """Retorna o valor da configuração do cache local se ainda for válido dentro do TTL."""
        now = time.monotonic()
        entry = self._local_cache.get(chave)
        if entry and entry[2] > now and entry[3]:
            return entry[0]
        return None

    async def _notify_redis_invalidation(self, chave: str, revision: int) -> None:
        """Dispara evento de invalidação no Redis Pub/Sub com degradação graciosa."""
        try:
            import redis.asyncio as aioredis
            client = aioredis.from_url(
                settings.redis_url,
                socket_connect_timeout=0.25,
                socket_timeout=0.25,
            )
            event_payload = json.dumps({
                "event": "CONFIG_INVALIDATED",
                "chave": chave,
                "revision": revision,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            await client.publish(REDIS_CHANNEL_CONFIG_EVENTS, event_payload)
            await client.aclose()
        except Exception as exc:
            logger.warning(
                f"Falha não-bloqueante ao notificar invalidação no Redis ({chave}): {exc}"
            )

    async def get_config(
        self,
        session: AsyncSession,
        chave: str,
        use_cache: bool = True,
    ) -> tuple[dict[str, Any], AgroConfigMetadata, bool]:
        """Obtém a configuração do Agro, lendo do cache local ou persistência com defaults.

        Returns:
            Tupla (valor_dict, metadata, ativo).
        """
        if chave not in SCHEMA_MAP:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Chave '{chave}' não é reconhecida no namespace do Agro.",
            )

        now = time.monotonic()
        if use_cache and chave in self._local_cache:
            valor_c, meta_c, exp_c, ativo_c = self._local_cache[chave]
            if now < exp_c:
                return valor_c, meta_c, ativo_c

        # Leitura no banco
        stmt = select(ConfiguracaoSaaS).where(ConfiguracaoSaaS.chave == chave)
        result = await session.execute(stmt)
        record = result.scalar_one_or_none()

        schema_cls = SCHEMA_MAP[chave]

        if not record or not record.ativo:
            # Retorna valor padrão homologado com revisão 0
            default_instance = schema_cls()
            meta = AgroConfigMetadata(
                revision=0,
                updated_at=datetime.now(timezone.utc).isoformat(),
                updated_by="sistema:default",
                version="1.0",
            )
            payload = default_instance.model_dump()
            ativo = True if not record else record.ativo
            self._local_cache[chave] = (payload, meta, now + self.ttl_seconds, ativo)
            return payload, meta, ativo

        # Extrai metadados e valida payload persistido
        raw_val = record.valor if isinstance(record.valor, dict) else {}
        meta_dict = raw_val.get("_meta", {})
        try:
            meta = AgroConfigMetadata.model_validate(meta_dict)
        except Exception:
            meta = AgroConfigMetadata(
                revision=1,
                updated_at=datetime.now(timezone.utc).isoformat(),
                updated_by="sistema@deepfarms.com",
            )

        # Remove campos de metadados antes de validar schema de dados
        data_clean = {k: v for k, v in raw_val.items() if not k.startswith("_")}
        try:
            validated_obj = schema_cls.model_validate(data_clean)
            payload = validated_obj.model_dump()
        except Exception as exc:
            logger.error(f"Configuração corrompida em banco para '{chave}': {exc}. Usando defaults.")
            payload = schema_cls().model_dump()

        self._local_cache[chave] = (payload, meta, now + self.ttl_seconds, record.ativo)
        return payload, meta, record.ativo

    async def get_all_configs(
        self,
        session: AsyncSession,
        use_cache: bool = True,
    ) -> AgroAllConfigsResponse:
        """Obtém todas as 4 configurações canônicas do Agro consolidando em resposta tipada."""
        v_clima, m_clima, a_clima = await self.get_config(session, KEY_CLIMA, use_cache=use_cache)
        v_merc, m_merc, a_merc = await self.get_config(session, KEY_MERCADO, use_cache=use_cache)
        v_mens, m_mens, a_mens = await self.get_config(session, KEY_MENSAGENS, use_cache=use_cache)
        v_flag, m_flag, a_flag = await self.get_config(session, KEY_FLAGS, use_cache=use_cache)

        return AgroAllConfigsResponse(
            clima=AgroConfigItemResponse(
                chave=KEY_CLIMA,
                valor=v_clima,
                meta=m_clima,
                descricao=DESCRICOES_PADRAO[KEY_CLIMA],
                ativo=a_clima,
            ),
            mercado=AgroConfigItemResponse(
                chave=KEY_MERCADO,
                valor=v_merc,
                meta=m_merc,
                descricao=DESCRICOES_PADRAO[KEY_MERCADO],
                ativo=a_merc,
            ),
            mensagens=AgroConfigItemResponse(
                chave=KEY_MENSAGENS,
                valor=v_mens,
                meta=m_mens,
                descricao=DESCRICOES_PADRAO[KEY_MENSAGENS],
                ativo=a_mens,
            ),
            feature_flags=AgroConfigItemResponse(
                chave=KEY_FLAGS,
                valor=v_flag,
                meta=m_flag,
                descricao=DESCRICOES_PADRAO[KEY_FLAGS],
                ativo=a_flag,
            ),
        )

    async def update_config(
        self,
        session: AsyncSession,
        chave: str,
        novo_valor: dict[str, Any],
        admin_claims: Any,
        expected_revision: Optional[int] = None,
        descricao: Optional[str] = None,
        ativo: Optional[bool] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        commit: bool = True,
    ) -> tuple[ConfiguracaoSaaS, AgroConfigMetadata]:
        """Atualiza a configuração com validação, controle de concorrência e auditoria atômica.

        Args:
            commit: Se True, executa session.commit() e notifica Redis imediatamente.
                    Se False, executa apenas session.flush(), permitindo transação externa única.

        Raises:
            HTTPException(400): Se a chave ou payload forem inválidos.
            HTTPException(409): Se expected_revision não coincidir com a revisão atual do banco.
        """
        if chave not in SCHEMA_MAP:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Chave '{chave}' não suportada para o Agro.",
            )

        schema_cls = SCHEMA_MAP[chave]

        # 1. Validação Pydantic estrita
        try:
            validated_obj = schema_cls.model_validate(novo_valor)
            payload_data = validated_obj.model_dump()
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Falha de validação para '{chave}': {str(exc)}",
            ) from exc

        # 1.1 Proteção contra injeção de arquivo arbitrário de snapshot DERAL (AGRO-ADMIN-01E4)
        if chave == KEY_MERCADO:
            allow_switch = False
            if isinstance(admin_claims, dict) and admin_claims.get("_allow_snapshot_switch"):
                allow_switch = True
            
            # Se for tentativa de alterar o snapshot ativo sem a flag interna do fluxo de validação
            stmt_check = select(ConfiguracaoSaaS).where(ConfiguracaoSaaS.chave == chave)
            res_check = await session.execute(stmt_check)
            rec_check = res_check.scalar_one_or_none()
            curr_snap = "deral-prp-2026-10-16.json"
            curr_id = "2026-10-16"
            if rec_check and isinstance(rec_check.valor, dict):
                curr_snap = rec_check.valor.get("deral_active_snapshot", curr_snap)
                curr_id = rec_check.valor.get("active_snapshot_id", curr_id)
            new_snap = payload_data.get("deral_active_snapshot")
            new_id = payload_data.get("active_snapshot_id")
            if not allow_switch and ((new_snap and new_snap != curr_snap) or (new_id and new_id != curr_id)):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "A ativação do snapshot DERAL ativo deve ocorrer exclusivamente por operação "
                        "administrativa validada (endpoint de ativação). Não é permitido alterar o snapshot ativo diretamente."
                    ),
                )

        # 2. Busca o registro atual no banco com lock de linha para concorrência
        stmt = select(ConfiguracaoSaaS).where(ConfiguracaoSaaS.chave == chave).with_for_update()
        result = await session.execute(stmt)
        record = result.scalar_one_or_none()

        dados_anteriores: dict[str, Any] = {}
        current_revision = 0

        if record and isinstance(record.valor, dict):
            dados_anteriores = record.valor
            current_revision = dados_anteriores.get("_meta", {}).get("revision", 0)

        # 3. Controle otimista de concorrência
        if expected_revision is not None and expected_revision != current_revision:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Conflito de concorrência na chave '{chave}': a revisão atual é {current_revision}, "
                    f"mas a esperada era {expected_revision}. Recarregue as configurações e tente novamente."
                ),
            )

        new_revision = current_revision + 1
        admin_uid, admin_email = await resolve_admin_identity(session, admin_claims)

        new_meta = AgroConfigMetadata(
            revision=new_revision,
            updated_at=datetime.now(timezone.utc).isoformat(),
            updated_by=admin_email,
            version="1.0",
        )

        full_payload = {
            **payload_data,
            "_meta": new_meta.model_dump(),
        }

        # 4. Atualiza ou cria o registro
        if not record:
            record = ConfiguracaoSaaS(
                chave=chave,
                valor=full_payload,
                descricao=descricao or DESCRICOES_PADRAO.get(chave, "Configuração do Agro"),
                ativo=ativo if ativo is not None else True,
            )
            session.add(record)
        else:
            record.valor = full_payload
            if descricao is not None:
                record.descricao = descricao
            if ativo is not None:
                record.ativo = ativo

        # 5. Registro compulsório em AdminAuditLog na mesma transação
        masked_ant = mask_sensitive_data(dados_anteriores, parent_key=chave)
        masked_nov = mask_sensitive_data(full_payload, parent_key=chave)

        audit_entry = AdminAuditLog(
            admin_user_id=admin_uid,
            admin_email=admin_email,
            acao="agro.config.update",
            entidade="configuracoes_saas",
            descricao=(
                f"Configuração do Agro '{chave}' atualizada para revisão {new_revision} "
                f"pelo operador {admin_email}."
            ),
            dados_anteriores=masked_ant,
            dados_novos=masked_nov,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        session.add(audit_entry)

        # 6. Commit transacional atômico ou flush para transação externa
        if commit:
            await session.commit()
            await session.refresh(record)
            now = time.monotonic()
            self._local_cache[chave] = (payload_data, new_meta, now + self.ttl_seconds, record.ativo)
            await self._notify_redis_invalidation(chave, new_revision)
            logger.info(
                f"Configuração '{chave}' atualizada com sucesso (rev: {new_revision}) por {admin_email}."
            )
        else:
            await session.flush()
            logger.info(
                f"Configuração '{chave}' preparada em transação única (rev: {new_revision}) por {admin_email}."
            )

        return record, new_meta

    async def post_commit_sync(
        self,
        chave: str,
        payload_data: dict[str, Any],
        new_meta: AgroConfigMetadata,
        ativo: bool,
    ) -> None:
        """Sincroniza cache L1 e dispara invalidação Redis após commit de transação externa."""
        now = time.monotonic()
        self._local_cache[chave] = (payload_data, new_meta, now + self.ttl_seconds, ativo)
        await self._notify_redis_invalidation(chave, new_meta.revision)


# Instância singleton do serviço para injeção de dependência
agro_config_service = AgroConfigService()


def get_agro_config_service() -> AgroConfigService:
    """Retorna a instância singleton do serviço de configurações do Agro."""
    return agro_config_service
