"""Sincronização automática e auditada dos preços semanais oficiais do DERAL."""

from __future__ import annotations

import asyncio
import hashlib
import ssl
import uuid
import urllib.request
from typing import Any

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agricola.cultivos.models import Cultivo as _Cultivo  # noqa: F401 - registers Safra relationship target
from core.database import async_session_maker
from core.models.admin_user import AdminUser
from core.services.deral_snapshot_service import deral_snapshot_service, parse_deral_xls

DERAL_XLS_URL = "https://www.agricultura.pr.gov.br/system/files/publico/Precos/prp.xls"
DERAL_SYSTEM_ADMIN_ID = uuid.UUID("50a1e347-8ff7-4bc8-9121-78dce3a0b5c1")
DERAL_SYSTEM_ADMIN_EMAIL = "deral-sync@system.invalid"
DERAL_SYNC_INTERVAL_SECONDS = 6 * 60 * 60
DERAL_MAX_FILE_BYTES = 5 * 1024 * 1024


class DeralAutoSyncService:
    """Busca, valida, audita e ativa automaticamente novas semanas do DERAL."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()

    async def sincronizar_uma_vez(self) -> bool:
        """Ativa um snapshot oficial mais recente e retorna se houve atualização."""
        async with self._lock:
            try:
                return await self._sincronizar_protegido()
            except Exception:
                logger.exception("deral_auto_sync_failed")
                return False

    async def _sincronizar_protegido(self) -> bool:
        raw_bytes, payload = await asyncio.to_thread(self._baixar_e_validar)
        async with async_session_maker() as session:
            snapshots = await deral_snapshot_service.list_snapshots(session)
            ativo = next((item for item in snapshots.snapshots if item.is_active), None)
            data_referencia = str(payload["dataReferencia"])
            if ativo and ativo.data_referencia >= data_referencia:
                return False
            claims = await self._identidade_sistema(session)
            await self._publicar_snapshot(session, raw_bytes, payload, claims)
        logger.info("deral_auto_sync_activated", snapshot=payload["dataReferencia"])
        return True

    def _baixar_e_validar(self) -> tuple[bytes, dict[str, object]]:
        """Baixa a fonte HTTPS fixa e valida a estrutura e os preços canônicos."""
        request = urllib.request.Request(DERAL_XLS_URL, headers={"User-Agent": "DeepFarms-Agro/1.0"})
        with urllib.request.urlopen(request, timeout=30, context=ssl.create_default_context()) as response:
            if getattr(response, "status", 200) != 200:
                raise ValueError(f"DERAL respondeu HTTP {response.status}")
            raw_bytes = response.read(DERAL_MAX_FILE_BYTES + 1)
        if len(raw_bytes) > DERAL_MAX_FILE_BYTES:
            raise ValueError("Planilha DERAL excede o limite de 5 MB")
        digest = hashlib.sha256(raw_bytes).hexdigest()
        return raw_bytes, parse_deral_xls(raw_bytes, digest)

    async def _identidade_sistema(self, session: AsyncSession) -> dict[str, str]:
        """Garante uma identidade técnica sem credencial de login para a auditoria."""
        actor = await session.get(AdminUser, DERAL_SYSTEM_ADMIN_ID)
        if actor is None:
            actor = (
                await session.execute(
                    select(AdminUser).where(AdminUser.email == DERAL_SYSTEM_ADMIN_EMAIL)
                )
            ).scalar_one_or_none()
        if actor is None:
            actor = AdminUser(
                id=DERAL_SYSTEM_ADMIN_ID,
                email=DERAL_SYSTEM_ADMIN_EMAIL,
                nome="Sincronização automática DERAL",
                senha_hash="NO_LOGIN_SYSTEM_ACTOR",
                role="system",
                ativo=False,
            )
            session.add(actor)
            await session.flush()
        return {"sub": str(actor.id), "email": actor.email}

    async def _publicar_snapshot(
        self,
        session: AsyncSession,
        raw_bytes: bytes,
        payload: dict[str, Any],
        claims: dict[str, str],
    ) -> None:
        """Persiste, aprova com base na validação automática e ativa atomicamente."""
        snapshot_id = str(payload["dataReferencia"])
        filename = f"deral-prp-{snapshot_id}.xls"
        await deral_snapshot_service.upload_snapshot(session, raw_bytes, filename, claims)
        justificativa = "Fonte oficial HTTPS, planilha íntegra e 21 preços validados automaticamente."
        await deral_snapshot_service.approve_snapshot(session, snapshot_id, True, justificativa, claims)
        await deral_snapshot_service.activate_snapshot(
            session,
            snapshot_id,
            claims,
            justificativa="Sincronização automática da nova semana oficial DERAL.",
        )


deral_auto_sync_service = DeralAutoSyncService()


async def run_deral_auto_sync_loop() -> None:
    """Confere a fonte oficial a cada seis horas no worker de background."""
    while True:
        await deral_auto_sync_service.sincronizar_uma_vez()
        await asyncio.sleep(DERAL_SYNC_INTERVAL_SECONDS)
