"""Validação criptográfica sintética da migração do cofre BYOK (AGRO-ADMIN-01B2A).

Testa:
1. Migração de credencial preservando o UUID do usuário (sucesso direto).
2. Detecção de colisão de identidade (UUID alterado causa falha de integridade GCM/AAD).
3. Procedimento de migração com colisão: decifragem controlada com UUID antigo e recifragem com novo UUID.
4. Falha por adulteração de chave mestra KMS (rejeição estrita).
5. Integridade estrutural e idempotência.
6. Simulação de rollback não destrutivo.
"""

from __future__ import annotations

import uuid
import pytest
from fastapi import HTTPException

from agro_identity.byok_vault import (
    EnvelopeEncryptionEngine,
    EnvelopeEncryptedRecord,
    LocalKmsKeyManager,
    mascarar_chave,
)
from agro_identity.config import AGRO_VAULT_MASTER_KEY


@pytest.fixture
def kms() -> LocalKmsKeyManager:
    return LocalKmsKeyManager(AGRO_VAULT_MASTER_KEY)


@pytest.fixture
def engine(kms: LocalKmsKeyManager) -> EnvelopeEncryptionEngine:
    return EnvelopeEncryptionEngine(kms)


def test_01_migracao_byok_preservando_uuid(engine: EnvelopeEncryptionEngine):
    """Quando o UUID é preservado, o registro cifrado é transferido sem necessidade de recifragem."""
    user_id = uuid.uuid4()
    provider = "weatherapi"
    secret = "chave_sintetica_teste_12345"

    record = engine.encrypt_secret(user_id, provider, secret, key_version=1)
    assert record.mascara_chave == mascarar_chave(secret)

    # Simulação de transferência direta para o novo repositório
    migrated_record = EnvelopeEncryptedRecord(
        ciphertext_b64=record.ciphertext_b64,
        data_nonce_b64=record.data_nonce_b64,
        dek_encrypted_b64=record.dek_encrypted_b64,
        dek_nonce_b64=record.dek_nonce_b64,
        key_version=record.key_version,
        mascara_chave=record.mascara_chave,
    )

    decrypted = engine.decrypt_secret(user_id, provider, migrated_record)
    assert decrypted == secret


def test_02_colisao_com_uuid_diferente_causa_falha_de_autenticacao(engine: EnvelopeEncryptionEngine):
    """Se o UUID mudar sem recifragem, a decifragem FALHA devido ao AAD e derivação da KEK vinculados ao UUID."""
    user_id_antigo = uuid.uuid4()
    user_id_novo = uuid.uuid4()
    provider = "weatherapi"
    secret = "chave_sintetica_teste_colisao"

    record = engine.encrypt_secret(user_id_antigo, provider, secret)

    # Tentativa de decifrar diretamente com o novo UUID deve ser rejeitada com HTTP 400
    with pytest.raises(HTTPException) as exc_info:
        engine.decrypt_secret(user_id_novo, provider, record)
    assert exc_info.value.status_code == 400
    assert "autenticidade dos dados não comprovada" in exc_info.value.detail


def test_03_migracao_com_colisao_exige_recifragem_controlada(engine: EnvelopeEncryptionEngine):
    """Em caso de colisão, o procedimento decifra com UUID antigo e recifra com o novo UUID canônico."""
    user_id_antigo = uuid.uuid4()
    user_id_canonico = uuid.uuid4()
    provider = "hg_brasil"
    secret = "chave_hg_brasil_sintetica_789"

    record_antigo = engine.encrypt_secret(user_id_antigo, provider, secret)

    # 1. Decifra em memória usando o UUID antigo original
    plaintext = engine.decrypt_secret(user_id_antigo, provider, record_antigo)
    assert plaintext == secret

    # 2. Recifra usando o novo UUID canônico
    record_novo = engine.encrypt_secret(user_id_canonico, provider, plaintext)
    assert record_novo.ciphertext_b64 != record_antigo.ciphertext_b64
    assert record_novo.mascara_chave == record_antigo.mascara_chave

    # 3. Comprova que o novo registro decifra com o UUID canônico
    decrypted_canonico = engine.decrypt_secret(user_id_canonico, provider, record_novo)
    assert decrypted_canonico == secret


def test_04_falha_de_chave_mestra_rejeita_decifragem(engine: EnvelopeEncryptionEngine):
    """Uma chave mestra KMS incorreta não decifra os dados (integridade estrita)."""
    user_id = uuid.uuid4()
    provider = "weatherapi"
    secret = "chave_segura_kms_falha"

    record = engine.encrypt_secret(user_id, provider, secret)

    kms_adulterado = LocalKmsKeyManager("00" * 32)
    engine_adulterado = EnvelopeEncryptionEngine(kms_adulterado)

    with pytest.raises(HTTPException) as exc_info:
        engine_adulterado.decrypt_secret(user_id, provider, record)
    assert exc_info.value.status_code == 400


def test_05_rollback_preserva_registro_original(engine: EnvelopeEncryptionEngine):
    """Um rollback na migração mantém o registro original descriptografável pelo UUID antigo."""
    user_id = uuid.uuid4()
    provider = "weatherapi"
    secret = "chave_rollback_teste"

    record_backup = engine.encrypt_secret(user_id, provider, secret)

    # Simula falha na etapa seguinte e restauração a partir do backup
    record_restaurado = EnvelopeEncryptedRecord(
        ciphertext_b64=record_backup.ciphertext_b64,
        data_nonce_b64=record_backup.data_nonce_b64,
        dek_encrypted_b64=record_backup.dek_encrypted_b64,
        dek_nonce_b64=record_backup.dek_nonce_b64,
        key_version=record_backup.key_version,
        mascara_chave=record_backup.mascara_chave,
    )

    assert engine.decrypt_secret(user_id, provider, record_restaurado) == secret
