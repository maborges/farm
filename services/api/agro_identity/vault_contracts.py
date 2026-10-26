"""Contrato e arquitetura formal do cofre segregado BYOK (Fases C3/C4).

Define as interfaces de envelope encryption (AES-256-GCM), rotação de chaves KMS,
auditoria e segregação estrita por identidade individual.
Nesta fase (C2), apenas os contratos e interfaces são estabelecidos; nenhuma credencial
real de fornecedor (Twelve Data, Polygon, IBKR) é armazenada.
"""

from __future__ import annotations

import base64
import os
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Literal

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
from pydantic import BaseModel, ConfigDict, Field

ProviderSlug = Literal["TWELVE_DATA", "POLYGON", "IBKR"]


class EnvelopeEncryptedData(BaseModel):
    """Payload cifrado contendo os dados autenticados e o nonce necessário para decriptação."""

    model_config = ConfigDict(extra="forbid")

    ciphertextB64: str
    nonceIvB64: str
    keyVersion: int = 1
    criadoEmIso: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ByokCredentialContract(BaseModel):
    """Contrato público de metadados da credencial (sem expor o segredo)."""

    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    usuarioId: uuid.UUID
    providerSlug: ProviderSlug
    mascaraChave: str  # Ex: "••••••••••••1234"
    status: Literal["CONECTADO", "PENDENTE", "ERRO_AUTENTICACAO", "REVOGADO"]
    keyVersion: int
    createdAt: datetime
    updatedAt: datetime


class IKmsKeyManager(ABC):
    """Interface abstrata para provedores de chave mestra (AWS KMS, GCP Cloud KMS, HashiCorp Vault ou Env)."""

    @abstractmethod
    def get_master_key(self, version: int = 1) -> bytes:
        """Obtém a chave mestra de 256 bits para a versão informada."""
        ...

    @abstractmethod
    def derive_user_key(self, user_id: uuid.UUID, version: int = 1) -> bytes:
        """Deriva chave criptográfica única por usuário usando HKDF-SHA256."""
        ...


class LocalEnvelopeEncryptionService(IKmsKeyManager):
    """Implementação canônica de envelope encryption com AES-256-GCM e AAD vinculado ao user_id."""

    def __init__(self, master_key_hex: str) -> None:
        self.master_key = bytes.fromhex(master_key_hex.strip())
        if len(self.master_key) != 32:
            raise ValueError("Chave mestra deve conter exatamente 32 bytes (256 bits).")

    def get_master_key(self, version: int = 1) -> bytes:
        return self.master_key

    def derive_user_key(self, user_id: uuid.UUID, version: int = 1) -> bytes:
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=f"deepfarms:agro:byok:v{version}".encode("utf-8"),
            info=user_id.bytes,
        )
        return hkdf.derive(self.master_key)

    def encrypt_secret(self, user_id: uuid.UUID, plaintext_secret: str, version: int = 1) -> EnvelopeEncryptedData:
        """Criptografa o segredo com AES-256-GCM.
        
        O user_id é injetado como Additional Authenticated Data (AAD) para impedir adulterações ou transposição de registros.
        """
        user_key = self.derive_user_key(user_id, version)
        aesgcm = AESGCM(user_key)
        nonce = os.urandom(12)  # 96-bit nonce único por operação
        aad = user_id.bytes

        ciphertext = aesgcm.encrypt(nonce, plaintext_secret.encode("utf-8"), aad)

        return EnvelopeEncryptedData(
            ciphertextB64=base64.b64encode(ciphertext).decode("ascii"),
            nonceIvB64=base64.b64encode(nonce).decode("ascii"),
            keyVersion=version,
        )

    def decrypt_secret(self, user_id: uuid.UUID, encrypted_data: EnvelopeEncryptedData) -> str:
        """Descriptografa e valida a tag de autenticação GCM."""
        user_key = self.derive_user_key(user_id, encrypted_data.keyVersion)
        aesgcm = AESGCM(user_key)
        nonce = base64.b64decode(encrypted_data.nonceIvB64)
        ciphertext = base64.b64decode(encrypted_data.ciphertextB64)
        aad = user_id.bytes

        decrypted_bytes = aesgcm.decrypt(nonce, ciphertext, aad)
        return decrypted_bytes.decode("utf-8")


def mascarar_chave(chave: str) -> str:
    """Gera máscara segura para exibição no frontend (ex: '••••••••1234')."""
    if len(chave) <= 4:
        return "••••"
    return f"{'•' * (len(chave) - 4)}{chave[-4:]}"
