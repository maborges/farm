"""Schemas Pydantic para validação e serialização da identidade individual e cofre BYOK do Agro."""

from __future__ import annotations

from enum import Enum
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class AgroRegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    nome: str = Field(..., min_length=2, max_length=150)
    senha: str = Field(..., min_length=8, max_length=128)


class AgroLoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    senha: str = Field(..., min_length=1, max_length=128)


class AgroUsuarioResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    email: str
    nome: str
    ativo: bool
    emailVerificado: bool
    createdAt: datetime


class AgroAuthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sucesso: bool
    mensagem: str
    usuario: AgroUsuarioResponse
    # O token JWT é transmitido exclusivamente via cookie HttpOnly seguro (deepfarms_agro_session)


class AgroForgotPasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr


class AgroForgotPasswordResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sucesso: bool
    mensagem: str


class AgroResetPasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: str = Field(..., min_length=8)
    novaSenha: str = Field(..., min_length=8, max_length=128)


class AgroVerifyEmailRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    codigo: str = Field(..., min_length=6, max_length=6)


class AgroChangePasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    senhaAtual: str = Field(..., min_length=1)
    novaSenha: str = Field(..., min_length=8, max_length=128)


class AgroMessageResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sucesso: bool
    mensagem: str


# ============================================================================
# Schemas para o Cofre Segregado e Proxy BYOK (Fase C3)
# ============================================================================

class TipoMercado(str, Enum):
    FISICO = "FISICO"
    FUTURO = "FUTURO"


class SituacaoCotacao(str, Enum):
    TEMPO_REAL = "TEMPO_REAL"
    ATRASADA = "ATRASADA"
    FECHAMENTO = "FECHAMENTO"
    INDISPONIVEL = "INDISPONIVEL"


class ByokProviderStatus(str, Enum):
    ATIVO = "ATIVO"
    DESABILITADO_LICENCA = "DESABILITADO_LICENCA"
    EM_HOMOLOGACAO = "EM_HOMOLOGACAO"


class ByokProviderInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slug: str
    nome: str
    descricao: str
    status: ByokProviderStatus
    instrumentosSuportados: list[str]
    requerCredencial: bool
    avisoRegulatorio: str


class ByokCredentialCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    providerSlug: str = Field(..., min_length=2, max_length=50)
    apiKey: str = Field(..., min_length=4, max_length=256)


class ByokCredentialResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    usuarioId: uuid.UUID
    providerSlug: str
    mascaraChave: str
    status: str
    keyVersion: int
    createdAt: datetime
    updatedAt: datetime


class ByokRotateKeysResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sucesso: bool
    mensagem: str
    versaoDestino: int
    credenciaisRotacionadas: int


class ByokCotacaoResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    commodity: str
    instrumento: str
    tipoMercado: TipoMercado
    valor: float
    moeda: str
    unidade: str
    bolsaOuRegiao: str
    dataReferencia: datetime
    fonte: str
    provedor: str
    situacao: SituacaoCotacao
    titularidadeByok: str
    cached: bool
