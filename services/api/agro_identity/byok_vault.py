"""Cofre segregado BYOK (Bring Your Own Key) com Envelope Encryption (AES-256-GCM + KMS).

Implementa:
1. KEK (Key Encryption Key) gerenciada por KMS com versionamento e derivação por usuário.
2. DEK (Data Encryption Key) individual e efêmera de 256 bits gerada por segredo.
3. Criptografia autenticada AES-256-GCM com AAD vinculado ao UUID do usuário e ao provider.
4. Rotação de chaves sem necessidade de reencriptação do payload de dados.
5. Metadados e mascaramento sem exposição de segredos em logs ou respostas.
"""

from __future__ import annotations

import base64
import os
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from fastapi import HTTPException, status
from loguru import logger
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from .config import AGRO_VAULT_MASTER_KEY
from core.models.usuario_byok import UsuarioByokCredential
from .schemas import ByokCredentialResponse


def mascarar_chave(chave: str) -> str:
    """Gera máscara segura para exibição (ex: '••••••••1234')."""
    chave_limpa = chave.strip()
    if len(chave_limpa) <= 4:
        return "••••"
    return f"{'•' * (len(chave_limpa) - 4)}{chave_limpa[-4:]}"


@dataclass(frozen=True)
class EnvelopeEncryptedRecord:
    """Representação dos componentes cifrados do envelope."""
    ciphertext_b64: str
    data_nonce_b64: str
    dek_encrypted_b64: str
    dek_nonce_b64: str
    key_version: int
    mascara_chave: str


class IKmsKeyManager(ABC):
    """Interface abstrata para gerenciador de chaves KMS (AWS KMS, GCP KMS, Vault ou Local)."""

    @abstractmethod
    def get_kek(self, version: int = 1) -> bytes:
        """Obtém a KEK mestra de 256 bits para a versão informada."""
        ...

    @abstractmethod
    def derive_user_kek(self, user_id: uuid.UUID, version: int = 1) -> bytes:
        """Deriva KEK criptograficamente exclusiva por usuário usando HKDF-SHA256."""
        ...


class LocalKmsKeyManager(IKmsKeyManager):
    """Implementação KMS local com KEKs versionadas e isolamento estrito contra o segredo JWT."""

    def __init__(self, master_key_hex: str) -> None:
        raw_key = bytes.fromhex(master_key_hex.strip())
        if len(raw_key) != 32:
            raise ValueError("A chave mestra KMS deve possuir exatamente 32 bytes (256 bits).")
        self._master_key_v1 = raw_key

    def get_kek(self, version: int = 1) -> bytes:
        if version == 1:
            return self._master_key_v1
        # Derivação determinística de nova versão para testes de rotação
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"deepfarms:agro:byok:kek_rotation",
            info=f"version:{version}".encode("utf-8"),
        )
        return hkdf.derive(self._master_key_v1)

    def derive_user_kek(self, user_id: uuid.UUID, version: int = 1) -> bytes:
        kek = self.get_kek(version)
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=f"deepfarms:agro:byok:user_kek:v{version}".encode("utf-8"),
            info=user_id.bytes,
        )
        return hkdf.derive(kek)


class EnvelopeEncryptionEngine:
    """Motor criptográfico AES-256-GCM com Envelope Encryption."""

    def __init__(self, kms: IKmsKeyManager) -> None:
        self.kms = kms

    def encrypt_secret(
        self,
        user_id: uuid.UUID,
        provider_slug: str,
        plaintext_secret: str,
        key_version: int = 1,
    ) -> EnvelopeEncryptedRecord:
        """Criptografa o segredo em duas camadas: DEK individual + KEK do usuário."""
        # 1. Gera DEK individual de 256 bits exclusiva para este segredo
        dek = os.urandom(32)

        # 2. Criptografa o segredo com a DEK usando AES-256-GCM
        data_nonce = os.urandom(12)  # 96-bit nonce
        data_aad = user_id.bytes + provider_slug.encode("utf-8")
        ciphertext = AESGCM(dek).encrypt(data_nonce, plaintext_secret.encode("utf-8"), data_aad)

        # 3. Deriva a KEK do usuário para a versão indicada
        user_kek = self.kms.derive_user_kek(user_id, key_version)

        # 4. Criptografa a DEK com a KEK do usuário
        dek_nonce = os.urandom(12)
        dek_aad = user_id.bytes + f"dek:v{key_version}".encode("utf-8")
        encrypted_dek = AESGCM(user_kek).encrypt(dek_nonce, dek, dek_aad)

        return EnvelopeEncryptedRecord(
            ciphertext_b64=base64.b64encode(ciphertext).decode("ascii"),
            data_nonce_b64=base64.b64encode(data_nonce).decode("ascii"),
            dek_encrypted_b64=base64.b64encode(encrypted_dek).decode("ascii"),
            dek_nonce_b64=base64.b64encode(dek_nonce).decode("ascii"),
            key_version=key_version,
            mascara_chave=mascarar_chave(plaintext_secret),
        )

    def decrypt_secret(
        self,
        user_id: uuid.UUID,
        provider_slug: str,
        record: EnvelopeEncryptedRecord,
    ) -> str:
        """Decifra a DEK via KEK do usuário e em seguida decifra o segredo original."""
        try:
            # 1. Deriva a KEK do usuário para a versão do registro
            user_kek = self.kms.derive_user_kek(user_id, record.key_version)

            # 2. Decifra a DEK e valida integridade via tag GCM
            encrypted_dek = base64.b64decode(record.dek_encrypted_b64)
            dek_nonce = base64.b64decode(record.dek_nonce_b64)
            dek_aad = user_id.bytes + f"dek:v{record.key_version}".encode("utf-8")
            dek = AESGCM(user_kek).decrypt(dek_nonce, encrypted_dek, dek_aad)

            # 3. Decifra o segredo e valida autenticidade via tag GCM
            ciphertext = base64.b64decode(record.ciphertext_b64)
            data_nonce = base64.b64decode(record.data_nonce_b64)
            data_aad = user_id.bytes + provider_slug.encode("utf-8")
            plaintext_bytes = AESGCM(dek).decrypt(data_nonce, ciphertext, data_aad)

            return plaintext_bytes.decode("utf-8")
        except InvalidTag as exc:
            logger.error(
                "Falha de autenticação criptográfica no cofre BYOK (tag GCM inválida ou chave adulterada)",
                user_id=str(user_id),
                provider=provider_slug,
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Falha na decriptação da credencial: autenticidade dos dados não comprovada.",
            ) from exc

    def rotate_key(
        self,
        user_id: uuid.UUID,
        provider_slug: str,
        record: EnvelopeEncryptedRecord,
        new_version: int,
    ) -> EnvelopeEncryptedRecord:
        """Executa rotação da KEK: re-encapsula a DEK sob nova versão sem alterar o payload de dados."""
        # 1. Recupera a DEK atual usando a KEK antiga
        user_kek_old = self.kms.derive_user_kek(user_id, record.key_version)
        encrypted_dek = base64.b64decode(record.dek_encrypted_b64)
        dek_nonce = base64.b64decode(record.dek_nonce_b64)
        dek_aad_old = user_id.bytes + f"dek:v{record.key_version}".encode("utf-8")
        dek = AESGCM(user_kek_old).decrypt(dek_nonce, encrypted_dek, dek_aad_old)

        # 2. Cifra a mesma DEK sob a nova versão de KEK
        user_kek_new = self.kms.derive_user_kek(user_id, new_version)
        new_dek_nonce = os.urandom(12)
        dek_aad_new = user_id.bytes + f"dek:v{new_version}".encode("utf-8")
        new_encrypted_dek = AESGCM(user_kek_new).encrypt(new_dek_nonce, dek, dek_aad_new)

        return EnvelopeEncryptedRecord(
            ciphertext_b64=record.ciphertext_b64,
            data_nonce_b64=record.data_nonce_b64,
            dek_encrypted_b64=base64.b64encode(new_encrypted_dek).decode("ascii"),
            dek_nonce_b64=base64.b64encode(new_dek_nonce).decode("ascii"),
            key_version=new_version,
            mascara_chave=record.mascara_chave,
        )


class ByokVaultService:
    """Serviço de gerenciamento do cofre segregado de credenciais BYOK."""

    ALLOWED_PROVIDERS = {"SIMULATED", "TWELVE_DATA", "POLYGON", "IBKR"}

    def __init__(self, db: AsyncSession, kms: IKmsKeyManager | None = None) -> None:
        self.db = db
        self.kms = kms or LocalKmsKeyManager(AGRO_VAULT_MASTER_KEY)
        self.engine = EnvelopeEncryptionEngine(self.kms)

    async def save_credential(
        self,
        usuario_id: uuid.UUID,
        provider_slug: str,
        api_key: str,
        key_version: int = 1,
    ) -> ByokCredentialResponse:
        """Armazena ou atualiza uma credencial cifrada no cofre com Envelope Encryption."""
        slug = provider_slug.strip().upper()
        if slug not in self.ALLOWED_PROVIDERS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Provedor '{slug}' não é suportado pelo catálogo homologado.",
            )

        # Restrição contratual: provedores externos não homologados comercialmente
        if slug in {"TWELVE_DATA", "POLYGON", "IBKR"}:
            logger.warning(
                f"Tentativa de cadastro em conector desabilitado por licença: {slug}",
                user_id=str(usuario_id),
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"O conector '{slug}' está temporariamente desabilitado até certificação de "
                    "direitos de redistribuição e taxas de bolsa da CME/ICE. Utilize o provedor 'SIMULATED'."
                ),
            )

        # Criptografa via envelope encryption
        envelope = self.engine.encrypt_secret(
            user_id=usuario_id,
            provider_slug=slug,
            plaintext_secret=api_key.strip(),
            key_version=key_version,
        )

        now = datetime.now(timezone.utc)
        stmt = select(UsuarioByokCredential).where(
            UsuarioByokCredential.usuario_id == usuario_id,
            UsuarioByokCredential.provider_slug == slug,
        )
        existing = (await self.db.execute(stmt)).scalar_one_or_none()

        if existing:
            existing.mascara_chave = envelope.mascara_chave
            existing.ciphertext_b64 = envelope.ciphertext_b64
            existing.data_nonce_b64 = envelope.data_nonce_b64
            existing.dek_encrypted_b64 = envelope.dek_encrypted_b64
            existing.dek_nonce_b64 = envelope.dek_nonce_b64
            existing.key_version = envelope.key_version
            existing.status = "CONECTADO"
            existing.updated_at = now
            cred = existing
        else:
            cred = UsuarioByokCredential(
                id=uuid.uuid4(),
                usuario_id=usuario_id,
                provider_slug=slug,
                mascara_chave=envelope.mascara_chave,
                ciphertext_b64=envelope.ciphertext_b64,
                data_nonce_b64=envelope.data_nonce_b64,
                dek_encrypted_b64=envelope.dek_encrypted_b64,
                dek_nonce_b64=envelope.dek_nonce_b64,
                key_version=envelope.key_version,
                status="CONECTADO",
                created_at=now,
                updated_at=now,
            )
            self.db.add(cred)

        await self.db.commit()
        await self.db.refresh(cred)

        logger.info(
            "Credencial BYOK registrada com Envelope Encryption",
            user_id=str(usuario_id),
            provider=slug,
            mascara=envelope.mascara_chave,
            key_version=envelope.key_version,
        )

        return ByokCredentialResponse(
            id=cred.id,
            usuarioId=cred.usuario_id,
            providerSlug=cred.provider_slug,
            mascaraChave=cred.mascara_chave,
            status=cred.status,
            keyVersion=cred.key_version,
            createdAt=cred.created_at,
            updatedAt=cred.updated_at,
        )

    async def list_credentials(self, usuario_id: uuid.UUID) -> list[ByokCredentialResponse]:
        """Lista todas as credenciais do usuário com mascaramento de chaves."""
        stmt = (
            select(UsuarioByokCredential)
            .where(UsuarioByokCredential.usuario_id == usuario_id)
            .order_by(UsuarioByokCredential.created_at.desc())
        )
        rows = (await self.db.execute(stmt)).scalars().all()
        return [
            ByokCredentialResponse(
                id=c.id,
                usuarioId=c.usuario_id,
                providerSlug=c.provider_slug,
                mascaraChave=c.mascara_chave,
                status=c.status,
                keyVersion=c.key_version,
                createdAt=c.created_at,
                updatedAt=c.updated_at,
            )
            for c in rows
        ]

    async def get_credential(self, usuario_id: uuid.UUID, provider_slug: str) -> ByokCredentialResponse | None:
        """Retorna os metadados de uma credencial específica."""
        slug = provider_slug.strip().upper()
        stmt = select(UsuarioByokCredential).where(
            UsuarioByokCredential.usuario_id == usuario_id,
            UsuarioByokCredential.provider_slug == slug,
        )
        c = (await self.db.execute(stmt)).scalar_one_or_none()
        if not c:
            return None
        return ByokCredentialResponse(
            id=c.id,
            usuarioId=c.usuario_id,
            providerSlug=c.provider_slug,
            mascaraChave=c.mascara_chave,
            status=c.status,
            keyVersion=c.key_version,
            createdAt=c.created_at,
            updatedAt=c.updated_at,
        )

    async def resolve_plaintext_credential(self, usuario_id: uuid.UUID, provider_slug: str) -> str:
        """Resolve o segredo em claro para uso exclusivo e imediato pelo Proxy BYOK."""
        slug = provider_slug.strip().upper()
        stmt = select(UsuarioByokCredential).where(
            UsuarioByokCredential.usuario_id == usuario_id,
            UsuarioByokCredential.provider_slug == slug,
            UsuarioByokCredential.status == "CONECTADO",
        )
        cred = (await self.db.execute(stmt)).scalar_one_or_none()
        if not cred:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Credencial para o provedor '{slug}' não configurada ou revogada.",
            )

        envelope = EnvelopeEncryptedRecord(
            ciphertext_b64=cred.ciphertext_b64,
            data_nonce_b64=cred.data_nonce_b64,
            dek_encrypted_b64=cred.dek_encrypted_b64,
            dek_nonce_b64=cred.dek_nonce_b64,
            key_version=cred.key_version,
            mascara_chave=cred.mascara_chave,
        )

        plaintext = self.engine.decrypt_secret(usuario_id, slug, envelope)

        # Atualiza último uso
        cred.ultimo_uso = datetime.now(timezone.utc)
        await self.db.commit()

        return plaintext

    async def revoke_credential(self, usuario_id: uuid.UUID, provider_slug: str) -> bool:
        """Marca a credencial como revogada."""
        slug = provider_slug.strip().upper()
        stmt = (
            update(UsuarioByokCredential)
            .where(
                UsuarioByokCredential.usuario_id == usuario_id,
                UsuarioByokCredential.provider_slug == slug,
            )
            .values(status="REVOGADO", updated_at=datetime.now(timezone.utc))
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount > 0

    async def delete_credential(self, usuario_id: uuid.UUID, provider_slug: str) -> bool:
        """Exclui permanentemente a credencial do cofre."""
        slug = provider_slug.strip().upper()
        stmt = select(UsuarioByokCredential).where(
            UsuarioByokCredential.usuario_id == usuario_id,
            UsuarioByokCredential.provider_slug == slug,
        )
        cred = (await self.db.execute(stmt)).scalar_one_or_none()
        if not cred:
            return False
        await self.db.delete(cred)
        await self.db.commit()
        logger.info(f"Credencial BYOK excluída permanentemente: {slug}", user_id=str(usuario_id))
        return True

    async def rotate_keys(self, usuario_id: uuid.UUID, new_version: int = 2) -> int:
        """Executa rotação de chave KMS para todas as credenciais do usuário."""
        stmt = select(UsuarioByokCredential).where(
            UsuarioByokCredential.usuario_id == usuario_id,
            UsuarioByokCredential.status == "CONECTADO",
        )
        creds = (await self.db.execute(stmt)).scalars().all()
        rotated_count = 0

        for cred in creds:
            if cred.key_version == new_version:
                continue

            record = EnvelopeEncryptedRecord(
                ciphertext_b64=cred.ciphertext_b64,
                data_nonce_b64=cred.data_nonce_b64,
                dek_encrypted_b64=cred.dek_encrypted_b64,
                dek_nonce_b64=cred.dek_nonce_b64,
                key_version=cred.key_version,
                mascara_chave=cred.mascara_chave,
            )

            new_record = self.engine.rotate_key(usuario_id, cred.provider_slug, record, new_version)
            cred.dek_encrypted_b64 = new_record.dek_encrypted_b64
            cred.dek_nonce_b64 = new_record.dek_nonce_b64
            cred.key_version = new_version
            cred.updated_at = datetime.now(timezone.utc)
            rotated_count += 1

        if rotated_count > 0:
            await self.db.commit()
            logger.info(
                f"Rotação de chaves KMS concluída para o usuário: {rotated_count} credenciais atualizadas para v{new_version}",
                user_id=str(usuario_id),
            )

        return rotated_count
