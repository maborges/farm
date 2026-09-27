"""Enums canônicos da fundação de requisições de materiais."""

from enum import Enum


class NaturezaItem(str, Enum):
    """Define se o item é consumido ou devolvido como posse temporária."""

    CONSUMIVEL = "CONSUMIVEL"
    RETORNAVEL = "RETORNAVEL"


class TipoRequisicaoItemEvento(str, Enum):
    """Fatos append-only possíveis no diário operacional por item."""

    SEPARACAO = "SEPARACAO"
    ENTREGA = "ENTREGA"
    RECEBIMENTO = "RECEBIMENTO"
    RECUSA = "RECUSA"
    CONSUMO = "CONSUMO"
    DEVOLUCAO = "DEVOLUCAO"
    PERDA = "PERDA"
    DANO = "DANO"
    EXTRAVIO = "EXTRAVIO"
    AJUSTE_AUTORIZADO = "AJUSTE_AUTORIZADO"


class CompatibilidadeLegado(str, Enum):
    """Classificação conservadora para requisições anteriores ao diário."""

    LEGACY_OPEN = "LEGACY_OPEN"
    LEGACY_DELIVERED = "LEGACY_DELIVERED"
    LEGACY_RETURNED = "LEGACY_RETURNED"


class PapelResponsabilidade(str, Enum):
    """Papéis de responsabilidade contextual da requisição."""

    RESPONSAVEL = "RESPONSAVEL"
    DELEGADO = "DELEGADO"
