"""Schemas Pydantic para o Dashboard Executivo, Observabilidade e Governança Operacional do DeepFarms Agro (AGRO-ADMIN-01F)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class AgroDashboardUsuariosOverview(BaseModel):
    """Métricas agregadas sobre o universo de produtores rurais gratuitos."""
    model_config = ConfigDict(extra="forbid")

    total_gratuitos: int
    novos_hoje: int
    novos_7d: int
    novos_30d: int
    ativos_hoje: int
    ativos_7d: int
    bloqueados: int
    com_byok: int
    taxa_conversao_byok_pct: float
    crescimento_mensal_pct: float


class AgroDashboardTrafegoOverview(BaseModel):
    """Consolidação da volumetria e telemetria de consumo das APIs públicas."""
    model_config = ConfigDict(extra="forbid")

    clima_requisicoes_mes: int
    clima_cache_hits: int
    clima_cache_misses: int
    clima_hit_rate_pct: float
    clima_timeouts: int
    clima_falhas: int
    mercado_fontes_operacionais: int
    mercado_fontes_total: int
    snapshot_deral_ativo_id: str
    snapshot_deral_referencia: str
    snapshot_deral_defasagem_dias: int


class AgroDashboardSaudeSistema(BaseModel):
    """Status de disponibilidade, infraestrutura e contingência operacional."""
    model_config = ConfigDict(extra="forbid")

    redis_online: bool
    provedor_clima_ativo: str
    contingencia_clima_ativa: bool
    alertas_criticos_count: int
    alertas_warning_count: int
    alertas_info_count: int
    homologacao_concluida_pct: float


class AgroDashboardResumoResponse(BaseModel):
    """Resposta consolidada do resumo executivo para o painel principal."""
    model_config = ConfigDict(extra="forbid")

    consultado_em: str
    usuarios: AgroDashboardUsuariosOverview
    trafego: AgroDashboardTrafegoOverview
    saude: AgroDashboardSaudeSistema


class AgroDashboardEvolucaoItem(BaseModel):
    """Ponto temporal de evolução de cadastros no período."""
    data: str
    novos_cadastros: int
    acumulado: int


class AgroDashboardUsuariosEvolucaoResponse(BaseModel):
    """Histórico temporal dos últimos 30 dias de adoção e distribuição do aplicativo."""
    model_config = ConfigDict(extra="forbid")

    historico_30d: list[AgroDashboardEvolucaoItem]
    distribuicao_status: dict[str, int]
    distribuicao_byok_provedor: dict[str, int]
    metadados_coleta: str = "Agregação direta em tempo real sobre a tabela usuarios sem exposição de dados pessoais"


class AgroOperationalAlertItem(BaseModel):
    """Alerta operacional detectado pelo motor de governança."""
    model_config = ConfigDict(extra="forbid")

    id: str
    tipo: str
    severidade: Literal["CRITICAL", "WARNING", "INFO"]
    prioridade: Literal["URGENT", "HIGH", "NORMAL", "LOW"]
    categoria: str
    titulo: str
    descricao: str
    data_deteccao: str
    recomendacao: str
    origem: str


class AgroHomologacaoItem(BaseModel):
    """Status formal e verificável de uma pendência técnica consolidada."""
    model_config = ConfigDict(extra="forbid")

    id: int
    titulo: str
    descricao: str
    fase_origem: str
    status: Literal["APROVADO", "EM VALIDAÇÃO", "PENDENTE", "BLOQUEADO"]
    evidencia: str
    acao_necessaria: str


class AgroHomologacaoDashboardResponse(BaseModel):
    """Painel de conformidade das pendências técnicas para homologação em Staging/Produção."""
    model_config = ConfigDict(extra="forbid")

    gerado_em: str
    total_itens: int
    aprovados_count: int
    em_validacao_count: int
    pendentes_count: int
    bloqueados_count: int
    percentual_conclusao: float
    itens: list[AgroHomologacaoItem]
