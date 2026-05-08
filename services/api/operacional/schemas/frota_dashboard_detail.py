from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from operacional.schemas.frota_dashboard import RiscoOperacionalTipo


class FrotaDashboardDetalheCabecalho(BaseModel):
    equipamento_id: UUID
    nome: str
    tipo: str
    status: str
    marca: str | None = None
    modelo: str | None = None
    unidade_produtiva_id: UUID | None = None
    placa: str | None = None
    numero_serie: str | None = None
    patrimonio: str | None = None
    combustivel: str | None = None
    capacidade_tanque_l: float | None = None
    potencia_cv: float | None = None
    horimetro_atual: float | None = None
    km_atual: float | None = None


class FrotaDashboardDetalheIndicadores(BaseModel):
    periodo_dias_aplicado: int | None = None
    total_os_abertas: int
    total_os_concluidas: int
    horas_trabalhadas_periodo: float | None = None
    km_trabalhados_periodo: float | None = None
    custo_total_manutencao: float
    custo_total_abastecimento: float
    custo_total_geral: float
    custo_por_hora: float | None = None
    custo_por_km: float | None = None
    consumo_medio_km_l: float | None = None
    consumo_medio_l_h: float | None = None
    dias_sem_abastecimento: int | None = None
    manutencao_status: Literal["OK", "PROXIMA", "VENCIDA", "SEM_PLANO"]


class FrotaDashboardDetalheAbastecimento(BaseModel):
    id: UUID
    data: datetime
    tipo_combustivel: str
    litros: float
    preco_litro: float
    custo_total: float
    local: str
    tanque_cheio: bool
    horimetro_na_data: float | None = None
    km_na_data: float | None = None
    nota_fiscal: str | None = None
    observacoes: str | None = None


class FrotaDashboardDetalheOrdemServico(BaseModel):
    id: UUID
    numero_os: str
    tipo: str
    status: str
    descricao_problema: str
    diagnostico_tecnico: str | None = None
    data_abertura: datetime
    data_conclusao: datetime | None = None
    horimetro_na_abertura: float | None = None
    km_na_abertura: float | None = None
    tecnico_responsavel: str | None = None
    custo_total_pecas: float
    custo_mao_obra: float
    custo_total_os: float


class FrotaDashboardDetalheRegistroManutencao(BaseModel):
    id: UUID
    os_id: UUID | None = None
    data_realizacao: datetime
    tipo: str
    descricao: str
    custo_total: float
    horimetro_na_data: float | None = None
    km_na_data: float | None = None
    tecnico_responsavel: str | None = None


class FrotaDashboardDetalheJornada(BaseModel):
    id: UUID
    operador_nome: str | None = None
    unidade_produtiva_nome: str | None = None
    safra_nome: str | None = None
    talhao_nome: str | None = None
    tipo_operacao: str
    data_inicio: datetime
    data_fim: datetime | None = None
    status: Literal["ABERTA", "FINALIZADA", "CANCELADA"]
    horimetro_inicial: float | None = None
    horimetro_final: float | None = None
    km_inicial: float | None = None
    km_final: float | None = None
    duracao_horas: float | None = None
    horas_trabalhadas: float | None = None
    km_trabalhados: float | None = None
    custo_estimado: float | None = None
    metrica_custo: Literal["HORA", "KM", "INDISPONIVEL"] = "INDISPONIVEL"
    observacoes: str | None = None


class FrotaDashboardDetalheDocumento(BaseModel):
    id: UUID
    tipo: str
    descricao: str | None = None
    numero: str | None = None
    data_vencimento: date | None = None
    status: Literal["VENCIDO", "PROXIMO"]
    dias_para_vencimento: int | None = None


class FrotaDashboardDetalhePlanoManutencao(BaseModel):
    id: UUID
    descricao: str
    frequencia_dias: int | None = None
    frequencia_horas: float | None = None
    frequencia_km: float | None = None
    ultimo_registro_data: datetime | None = None
    ultimo_registro_horas: float | None = None
    ultimo_registro_km: float | None = None
    status: Literal["OK", "PROXIMA", "VENCIDA"]
    restante_dias: int | None = None
    restante_horas: float | None = None
    restante_km: float | None = None


class FrotaDashboardDetalheAlerta(BaseModel):
    tipo: RiscoOperacionalTipo
    titulo: str
    severidade: Literal["warning", "danger"]
    detalhe: str
    dias_desde_evento: int | None = None
    data_referencia: date | datetime | None = None


class FrotaDashboardDetalheResponse(BaseModel):
    equipamento: FrotaDashboardDetalheCabecalho
    indicadores: FrotaDashboardDetalheIndicadores
    ultimos_abastecimentos: list[FrotaDashboardDetalheAbastecimento]
    ultimas_ordens_servico: list[FrotaDashboardDetalheOrdemServico]
    ultimos_registros_manutencao: list[FrotaDashboardDetalheRegistroManutencao]
    ultimas_jornadas: list[FrotaDashboardDetalheJornada]
    documentos_alerta: list[FrotaDashboardDetalheDocumento]
    planos_manutencao: list[FrotaDashboardDetalhePlanoManutencao]
    alertas: list[FrotaDashboardDetalheAlerta]
    recomendacao_operacional: str
    gerado_em: datetime
