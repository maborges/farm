"""Sincronização automática e auditada dos preços semanais oficiais do DERAL."""

from __future__ import annotations

import asyncio
import hashlib
import ipaddress
import ssl
import uuid
import urllib.error
import urllib.request
from typing import Any
from urllib.parse import urlparse

from fastapi import HTTPException, status
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agricola.cultivos.models import Cultivo as _Cultivo  # noqa: F401 - registers Safra relationship target
from core.database import async_session_maker
from core.models.admin_user import AdminUser
from core.schemas.agro_config_schemas import KEY_MERCADO, DeralSyncTriggerResponse
from core.services.agro_config_service import agro_config_service
from core.services.deral_snapshot_service import (
    HOMOLOGATED_GOV_DOMAINS,
    OLE2_MAGIC,
    deral_snapshot_service,
    parse_deral_xls,
    verificar_proveniencia_governamental,
)

DERAL_XLS_URL = "https://www.agricultura.pr.gov.br/system/files/publico/Precos/prp.xls"
DERAL_SYSTEM_ADMIN_ID = uuid.UUID("50a1e347-8ff7-4bc8-9121-78dce3a0b5c1")
DERAL_SYSTEM_ADMIN_EMAIL = "deral-sync@system.invalid"
DERAL_SYNC_INTERVAL_SECONDS = 6 * 60 * 60
DERAL_MAX_FILE_BYTES = 5 * 1024 * 1024


def validar_url_deral_segura(url: str) -> str:
    """Valida se a URL configurada usa HTTPS em domínio governamental homologado.

    Args:
        url: URL alvo da planilha DERAL/SEAB-PR.

    Returns:
        URL normalizada se aprovada na whitelist anti-SSRF.

    Raises:
        ValueError: Se o esquema não for HTTPS, contiver IP/credenciais ou domínio não oficial.
    """
    alvo = str(url or "").strip()
    parsed = urlparse(alvo)
    hostname = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or not hostname or parsed.username or parsed.password:
        raise ValueError("URL DERAL deve usar exclusivamente HTTPS em domínio governamental.")
    try:
        ipaddress.ip_address(hostname)
        raise ValueError("Endereços IP diretos são bloqueados para sincronização DERAL.")
    except ValueError as exc:
        if "Endereços IP" in str(exc):
            raise
    ok, _, msg = verificar_proveniencia_governamental(alvo, "DERAL/SEAB-PR")
    if not ok or not any(hostname == dom or hostname.endswith(f".{dom}") for dom in HOMOLOGATED_GOV_DOMAINS):
        raise ValueError(msg or "Domínio não pertence aos órgãos governamentais homologados.")
    return alvo


class _SafeGovRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Impede redirecionamentos HTTP para domínios fora da whitelist governamental."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validar_url_deral_segura(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class DeralAutoSyncService:
    """Busca, valida, audita e ativa automaticamente novas semanas do DERAL."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()

    def _obter_url_configurada(self) -> str:
        cfg = agro_config_service.get_cached_config_dict(KEY_MERCADO) or {}
        bruta = str(cfg.get("deral_source_url") or DERAL_XLS_URL)
        return validar_url_deral_segura(bruta)

    async def sincronizar_uma_vez(self) -> bool:
        """Ativa um snapshot oficial mais recente e retorna se houve atualização."""
        async with self._lock:
            try:
                async with async_session_maker() as session:
                    res = await self._executar_sync_sessao(session, None)
                    return res.atualizado
            except Exception:
                logger.exception("deral_auto_sync_failed")
                return False

    async def sincronizar_com_detalhes(
        self,
        session: AsyncSession,
        admin_claims: dict[str, Any] | None = None,
    ) -> DeralSyncTriggerResponse:
        """Executa sincronização sob demanda com retorno detalhado para o Backoffice.

        Args:
            session: Sessão assíncrona do banco para leitura e publicação atômica.
            admin_claims: Credenciais do operador que disparou a ação (opcional).

        Returns:
            DeralSyncTriggerResponse descrevendo se houve ativação de nova semana.

        Raises:
            HTTPException: Em falha de segurança na URL ou indisponibilidade da fonte DERAL.
        """
        async with self._lock:
            try:
                return await self._executar_sync_sessao(session, admin_claims)
            except ValueError as exc:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
            except urllib.error.URLError as exc:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Fonte oficial DERAL inacessível no momento: {exc.reason}",
                ) from exc

    async def _executar_sync_sessao(
        self,
        session: AsyncSession,
        admin_claims: dict[str, Any] | None,
    ) -> DeralSyncTriggerResponse:
        source_url = self._obter_url_configurada()
        raw_bytes, payload = await asyncio.to_thread(self._baixar_e_validar, source_url)
        snapshots = await deral_snapshot_service.list_snapshots(session)
        ativo = next((item for item in snapshots.snapshots if item.is_active), None)
        ativo_anterior = ativo.id if ativo else snapshots.active_snapshot_id
        data_referencia = str(payload["dataReferencia"])
        if ativo and ativo.data_referencia >= data_referencia:
            return DeralSyncTriggerResponse(
                sucesso=True,
                atualizado=False,
                mensagem=f"Snapshot ativo ({ativo.id}) já está atualizado em relação à planilha oficial ({data_referencia}).",
                fonte_url=source_url,
                snapshot_ativo_anterior=ativo_anterior,
                snapshot_ativo_atual=ativo.id,
            )
        claims = admin_claims or await self._identidade_sistema(session)
        await self._publicar_snapshot(session, raw_bytes, payload, claims)
        logger.info("deral_auto_sync_activated", snapshot=data_referencia)
        return DeralSyncTriggerResponse(
            sucesso=True,
            atualizado=True,
            mensagem=f"Snapshot DERAL {data_referencia} sincronizado, aprovado e ativado com sucesso.",
            fonte_url=source_url,
            snapshot_ativo_anterior=ativo_anterior,
            snapshot_ativo_atual=data_referencia,
        )

    def _baixar_e_validar(self, source_url: str | None = None) -> tuple[bytes, dict[str, object]]:
        """Baixa a fonte HTTPS homologada e valida a estrutura e os preços canônicos."""
        url_segura = validar_url_deral_segura(source_url or DERAL_XLS_URL)
        request = urllib.request.Request(url_segura, headers={"User-Agent": "DeepFarms-Agro/1.0"})
        opener = urllib.request.build_opener(
            _SafeGovRedirectHandler(),
            urllib.request.HTTPSHandler(context=ssl.create_default_context()),
        )
        with opener.open(request, timeout=30) as response:
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
        ext = ".xls" if raw_bytes.startswith(OLE2_MAGIC) else ".json" if raw_bytes.lstrip().startswith(b"{") else ".xls"
        filename = f"deral-prp-{snapshot_id}{ext}"
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
