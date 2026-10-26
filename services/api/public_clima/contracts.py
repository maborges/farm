# ruff: noqa: N815
"""Contratos Pydantic para a API pública de clima do DeepFarms Agro."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

TipoDado = Literal["OBSERVADO", "PREVISTO", "CALCULADO"]
StatusOperacional = Literal["NORMAL", "DESATUALIZADO", "INDISPONIVEL", "PROVEDOR_NAO_CONFIGURADO"]


class CondicaoAtual(BaseModel):
    """Condições meteorológicas observadas ou estimadas para o momento atual."""

    model_config = ConfigDict(extra="forbid")

    temperaturaC: float | None = None
    sensacaoTermicaC: float | None = None
    umidadeRelativaPct: int | None = None
    ventoKmH: float | None = None
    ventoDirecaoGraus: int | None = None
    ventoRajadasKmH: float | None = None
    precipitacaoMm: float | None = None
    probabilidadeChuvaPct: int | None = None
    condicaoDescricao: str | None = None
    condicaoIcone: str | None = None


class PrevisaoHorariaItem(BaseModel):
    """Projeção horária das variáveis meteorológicas."""

    model_config = ConfigDict(extra="forbid")

    horaIso: str
    temperaturaC: float | None = None
    sensacaoTermicaC: float | None = None
    umidadePct: int | None = None
    ventoKmH: float | None = None
    ventoDirecaoGraus: int | None = None
    ventoRajadasKmH: float | None = None
    precipitacaoMm: float | None = None
    probabilidadeChuvaPct: int | None = None
    condicaoDescricao: str | None = None
    condicaoIcone: str | None = None


class PrevisaoDiariaItem(BaseModel):
    """Projeção agrometeorológica diária; o MVP público limita a até 3 dias."""

    model_config = ConfigDict(extra="forbid")

    dataIso: str
    diaSemana: str
    tempMinC: float | None = None
    tempMaxC: float | None = None
    precipitacaoMm: float | None = None
    probabilidadeChuvaPct: int | None = None
    ventoMaxKmH: float | None = None
    condicaoDescricao: str | None = None
    condicaoIcone: str | None = None


class ClimaPrevisaoResponse(BaseModel):
    """Resposta canônica do endpoint público de previsão do tempo."""

    model_config = ConfigDict(extra="forbid")

    latitude: float
    longitude: float
    latitudeGrid: float
    longitudeGrid: float
    fusoHorario: str = "America/Sao_Paulo"
    provedor: str
    licencaFonte: str
    tipoDado: TipoDado
    dadosSinteticos: bool = False

    temperaturaAtualC: float | None = None
    sensacaoTermicaC: float | None = None
    umidadeRelativaPct: int | None = None
    ventoVelocidadeKmH: float | None = None
    ventoDirecaoGraus: int | None = None
    ventoRajadasKmH: float | None = None
    precipitacaoMm: float | None = None
    probabilidadeChuvaPct: int | None = None
    condicaoDescricao: str | None = None
    condicaoIcone: str | None = None

    condicoesAtuais: CondicaoAtual | None = None
    previsaoHoraria: list[PrevisaoHorariaItem] = Field(default_factory=list)
    previsaoDiaria: list[PrevisaoDiariaItem] = Field(default_factory=list)

    horarioReferenciaIso: datetime
    obtidoEmIso: datetime
    validoAteIso: datetime
    emCache: bool = False
    desatualizado: bool = False
    statusOperacional: StatusOperacional = "NORMAL"
    avisoLegal: str = (
        "Dados meteorológicos para planejamento operacional. "
        "Não substituem medições in-situ da propriedade."
    )


TipoLocalidade = Literal["CENTROIDE_MUNICIPAL", "GPS"]


class MunicipioItem(BaseModel):
    """Representação canônica de um município brasileiro com coordenadas oficiais de referência."""

    model_config = ConfigDict(extra="forbid")

    codigoIbge: int
    nome: str
    uf: str
    estadoNome: str
    latitude: float
    longitude: float
    fusoHorario: str = "America/Sao_Paulo"
    capital: bool = False
    tipoLocalidade: TipoLocalidade = "CENTROIDE_MUNICIPAL"


class MunicipiosBuscaResponse(BaseModel):
    """Contrato de resposta da consulta e catálogo oficial de municípios."""

    model_config = ConfigDict(extra="forbid")

    sucesso: bool = True
    total: int
    limite: int
    offset: int
    fonte: str = (
        "IBGE - Diretoria de Geociências (DGC) / Censo Demográfico / "
        "Malha Municipal Digital do Brasil (SIRGAS 2000)"
    )
    versaoFonte: str = "2024.1"
    avisoMetodologico: str = (
        "As coordenadas de referência representam o centroide geográfico oficial da sede "
        "municipal homologada pelo IBGE e diferem da localização exata da propriedade rural."
    )
    itens: list[MunicipioItem]

