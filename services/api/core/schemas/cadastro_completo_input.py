from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from core.cadastros.propriedade_imovel.models import TipoVinculoPropriedadeImovel

from .unidade_produtiva_input import UnidadeProdutivaCreate, UnidadeProdutivaUpdate

_UP_FIELDS = set(UnidadeProdutivaCreate.model_fields)
_PROPRIEDADE_FIELDS = {
    "id",
    "nome",
    "cpf_cnpj",
    "inscricao_estadual",
    "ie_isento",
    "email",
    "telefone",
    "nome_fantasia",
    "regime_tributario",
    "cor",
    "icone",
    "ordem",
    "ativo",
    "observacoes",
}
_EXPLORACAO_FIELDS = {
    "id",
    "natureza",
    "data_inicio",
    "data_fim",
    "numero_contrato",
    "valor_anual",
    "percentual_producao",
    "area_explorada_ha",
    "observacoes",
}
_IMOVEL_FIELDS = {
    "id",
    "nome",
    "municipio",
    "uf",
    "area_total_ha",
    "nirf",
    "car_numero",
    "codigo_car",
    "ccir_numero",
    "ccir",
    "sigef_codigo",
    "cartorio_id",
    "numero_matricula",
    "tipo",
    "observacao",
}
_VINCULO_FIELDS = {
    "id",
    "tipo_vinculo",
    "ativo",
    "data_inicio",
    "data_fim",
    "origem_documental",
    "observacoes",
    "area_vinculada",
    "percentual_vinculado",
    "vinculo_principal",
    "origem_referencia",
    "status_documental",
}


class CadastroCompletoPropriedadeInput(BaseModel):
    """Bloco territorial da Propriedade no cadastro completo."""

    model_config = ConfigDict(extra="forbid")

    id: Optional[uuid.UUID] = None
    nome: Optional[str] = Field(None, min_length=2, max_length=200)
    cpf_cnpj: Optional[str] = Field(None, max_length=18)
    inscricao_estadual: Optional[str] = Field(None, max_length=50)
    ie_isento: Optional[bool] = None
    email: Optional[str] = Field(None, max_length=200)
    telefone: Optional[str] = Field(None, max_length=30)
    nome_fantasia: Optional[str] = Field(None, max_length=200)
    regime_tributario: Optional[str] = Field(None, max_length=30)
    cor: Optional[str] = Field(None, max_length=7)
    icone: Optional[str] = Field(None, max_length=50)
    ordem: Optional[int] = None
    ativo: Optional[bool] = None
    observacoes: Optional[str] = None


class CadastroCompletoExploracaoInput(BaseModel):
    """Bloco operacional da exploração rural no cadastro completo."""

    model_config = ConfigDict(extra="forbid")

    id: Optional[uuid.UUID] = None
    natureza: Optional[str] = None
    data_inicio: Optional[date] = None
    data_fim: Optional[date] = None
    numero_contrato: Optional[str] = Field(None, max_length=100)
    valor_anual: Optional[float] = Field(None, gt=0)
    percentual_producao: Optional[float] = Field(None, gt=0, le=100)
    area_explorada_ha: Optional[float] = Field(None, gt=0)
    observacoes: Optional[str] = None


class CadastroCompletoImovelInput(BaseModel):
    """Bloco fundiário canônico do imóvel rural."""

    model_config = ConfigDict(extra="forbid")

    id: Optional[uuid.UUID] = None
    nome: Optional[str] = Field(None, max_length=255)
    municipio: Optional[str] = Field(None, max_length=100)
    uf: Optional[str] = Field(None, min_length=2, max_length=2)
    area_total_ha: Optional[Decimal] = Field(None, gt=0)
    nirf: Optional[str] = Field(None, max_length=20)
    car_numero: Optional[str] = Field(None, max_length=50)
    codigo_car: Optional[str] = Field(None, max_length=50)
    ccir_numero: Optional[str] = Field(None, max_length=50)
    ccir: Optional[str] = Field(None, max_length=50)
    sigef_codigo: Optional[str] = Field(None, max_length=50)
    cartorio_id: Optional[uuid.UUID] = None
    numero_matricula: Optional[str] = Field(None, max_length=100)
    motivo_alteracao_area: Optional[str] = None
    tipo: Optional[str] = None
    observacao: Optional[str] = None


class CadastroCompletoPropriedadeImovelInput(BaseModel):
    """Bloco de comando para o vínculo canônico PropriedadeImovel."""

    model_config = ConfigDict(extra="forbid", use_enum_values=True)

    id: Optional[uuid.UUID] = None
    tipo_vinculo: Optional[TipoVinculoPropriedadeImovel] = None
    ativo: Optional[bool] = None
    data_inicio: Optional[date] = None
    data_fim: Optional[date] = None
    origem_documental: Optional[str] = Field(None, min_length=1)
    observacoes: Optional[str] = None
    area_vinculada: Optional[Decimal] = None
    percentual_vinculado: Optional[Decimal] = None
    vinculo_principal: Optional[bool] = None
    origem_referencia: Optional[str] = None
    status_documental: Optional[str] = None


class _CadastroCompletoBase(BaseModel):
    """Mixin com adaptação de payload legado para o contrato oficial em blocos."""

    model_config = ConfigDict(extra="forbid", use_enum_values=True)

    unidade_produtiva: Any = None
    propriedade: Optional[CadastroCompletoPropriedadeInput] = None
    exploracao_rural: Optional[CadastroCompletoExploracaoInput] = None
    imovel_rural: Optional[CadastroCompletoImovelInput] = None
    propriedade_imovel: Optional[CadastroCompletoPropriedadeImovelInput] = None

    @model_validator(mode="before")
    @classmethod
    def _adaptar_payload_legado(cls, data: Any) -> Any:
        """Converte payload achatado para os blocos oficiais sem perder compatibilidade."""
        if not isinstance(data, dict):
            return data
        if "unidade_produtiva" in data:
            return data

        payload = dict(data)
        unidade_produtiva = cls._extrair_bloco(payload, "unidade_produtiva", _UP_FIELDS)
        propriedade = cls._extrair_bloco(payload, "propriedade", _PROPRIEDADE_FIELDS)
        exploracao = cls._extrair_bloco(payload, "exploracao_rural", _EXPLORACAO_FIELDS)
        imovel = cls._extrair_bloco(payload, "imovel_rural", _IMOVEL_FIELDS)
        vinculo = cls._extrair_bloco(payload, "propriedade_imovel", _VINCULO_FIELDS)

        cls._normalizar_legacy_imovel(imovel, payload)
        propriedade, imovel, vinculo = cls._normalizar_legacy_relacionamentos(
            propriedade,
            imovel,
            vinculo,
            payload,
        )

        if unidade_produtiva is not None:
            payload["unidade_produtiva"] = unidade_produtiva
        if propriedade is not None:
            payload["propriedade"] = propriedade
        if exploracao is not None:
            payload["exploracao_rural"] = exploracao
        if imovel is not None:
            payload["imovel_rural"] = imovel
        if vinculo is not None:
            payload["propriedade_imovel"] = vinculo
        return payload

    @staticmethod
    def _extrair_bloco(
        payload: dict[str, Any],
        bloco_nome: str,
        campos_permitidos: set[str],
    ) -> dict[str, Any] | None:
        """Extrai um bloco conhecido do payload achatado."""
        bloco = payload.pop(bloco_nome, None)
        resultado = dict(bloco) if isinstance(bloco, dict) else {}

        for campo in list(campos_permitidos):
            if campo in payload:
                valor = payload.pop(campo)
                if valor is not None:
                    resultado[campo] = valor

        return resultado or None

    @staticmethod
    def _normalizar_legacy_imovel(
        imovel: dict[str, Any] | None,
        payload: dict[str, Any],
    ) -> None:
        """Compatibiliza aliases legados de imóvel sem reintroduzir campos removidos."""
        if imovel is None:
            return
        if "codigo_car" in imovel:
            imovel["car_numero"] = imovel.pop("codigo_car")
        if "ccir" in imovel:
            imovel["ccir_numero"] = imovel.pop("ccir")

    @staticmethod
    def _normalizar_legacy_relacionamentos(
        propriedade: dict[str, Any] | None,
        imovel: dict[str, Any] | None,
        vinculo: dict[str, Any] | None,
        payload: dict[str, Any],
    ) -> tuple[dict[str, Any] | None, dict[str, Any] | None, dict[str, Any] | None]:
        """Distribui IDs legados entre os blocos sem jogá-los na UP."""
        propriedade_id = payload.pop("propriedade_id", None)
        if propriedade is None and propriedade_id is not None:
            propriedade = {"id": propriedade_id}
        elif propriedade is not None and "id" not in propriedade and propriedade_id is not None:
            propriedade["id"] = propriedade_id

        imovel_id = payload.pop("imovel_rural_id", None)
        if imovel is None and imovel_id is not None:
            imovel = {"id": imovel_id}
        elif imovel is not None and "id" not in imovel and imovel_id is not None:
            imovel["id"] = imovel_id

        vinculo_id = payload.pop("propriedade_imovel_id", None)
        if vinculo is None and vinculo_id is not None:
            vinculo = {"id": vinculo_id}
        elif vinculo is not None and "id" not in vinculo and vinculo_id is not None:
            vinculo["id"] = vinculo_id

        return propriedade, imovel, vinculo


class CadastroCompletoCreate(_CadastroCompletoBase):
    """Contrato oficial de criação em blocos do cadastro completo."""

    unidade_produtiva: UnidadeProdutivaCreate


class CadastroCompletoUpdate(_CadastroCompletoBase):
    """Contrato oficial de atualização em blocos do cadastro completo."""

    unidade_produtiva: Optional[UnidadeProdutivaUpdate] = None
