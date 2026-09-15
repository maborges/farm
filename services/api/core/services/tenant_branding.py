"""Upload da identidade visual da conta autenticada."""
import uuid

from fastapi import HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from core.models.tenant import Tenant
from core.services.storage_service import StorageService, increment_storage

LOGO_MAX_BYTES = 2 * 1024 * 1024
LOGO_EXTENSIONS = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}


async def read_logo(arquivo: UploadFile) -> bytes:
    """Args: arquivo recebido. Return: conteúdo. Raises: HTTPException se inválido."""
    if arquivo.content_type not in LOGO_EXTENSIONS:
        raise HTTPException(400, "Tipo não suportado. Use JPEG, PNG ou WebP.")
    content = await arquivo.read(LOGO_MAX_BYTES + 1)
    if not content:
        raise HTTPException(400, "A imagem da logo está vazia.")
    if len(content) > LOGO_MAX_BYTES:
        raise HTTPException(400, "Logo deve ter no máximo 2MB.")
    return content


async def upload_tenant_logo(tenant: Tenant, session: AsyncSession, arquivo: UploadFile) -> str:
    """Args: conta, sessão e imagem. Return: URL. Raises: erro de validação ou persistência."""
    content = await read_logo(arquivo)
    extension = LOGO_EXTENSIONS[arquivo.content_type]
    path = f"static/logos/{tenant.id}/{uuid.uuid4().hex}{extension}"
    StorageService.save_blob(content, path)
    url = StorageService.public_url(path)
    tenant.branding = {**(tenant.branding or {}), "logoUrl": url}
    await increment_storage(session, tenant.id, len(content))
    await session.commit()
    return url
