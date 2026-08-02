from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID
from datetime import datetime, date
from typing import Optional, List


class PlanoOperacionalCreate(BaseModel):
    safra_id: UUID
    production_unit_id: Optional[UUID] = None
    nome: str = Field(..., min_length=3, max_length=150)
    descricao: Optional[str] = None
    data_inicio_prevista: date
    data_fim_prevista: Optional[date] = None


class PlanoOperacionalUpdate(BaseModel):
    nome: Optional[str] = Field(None, min_length=3, max_length=150)
    descricao: Optional[str] = None
    data_inicio_prevista: Optional[date] = None
    data_fim_prevista: Optional[date] = None


class PlanoOperacionalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    safra_id: UUID
    production_unit_id: Optional[UUID]
    nome: str
    descricao: Optional[str]
    data_inicio_prevista: date
    data_fim_prevista: Optional[date]
    status: str
    versao: int
    criado_por: Optional[UUID]
    aprovado_por: Optional[UUID]
    aprovado_em: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class PlanoOperacionalTarefaCreate(BaseModel):
    safra_tarefa_id: UUID


class PlanoOperacionalTarefaUpdate(BaseModel):
    status_planejamento: Optional[str] = None
    data_programada: Optional[date] = None
    observacao: Optional[str] = None
    ordem_execucao: Optional[int] = None


class PlanoOperacionalTarefaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    plano_operacional_id: UUID
    safra_tarefa_id: UUID
    status_planejamento: str
    data_programada: Optional[date]
    observacao: Optional[str]
    ordem_execucao: Optional[int]
    created_at: datetime
    updated_at: datetime


class PlanoOperacionalTarefaInsumoCreate(BaseModel):
    safra_tarefa_necessidade_id: Optional[UUID] = None
    produto_id: UUID
    deposito_id: Optional[UUID] = None
    dose_planejada: Optional[float] = None
    unidade_dose: str = Field(..., min_length=1, max_length=20)
    quantidade_planejada: float = Field(..., gt=0)


class PlanoOperacionalTarefaInsumoUpdate(BaseModel):
    produto_id: Optional[UUID] = None
    deposito_id: Optional[UUID] = None
    dose_planejada: Optional[float] = None
    unidade_dose: Optional[str] = None
    quantidade_planejada: Optional[float] = Field(None, gt=0)


class SugestaoProdutoOrcamentoResponse(BaseModel):
    """
    Candidato a produto comercial para uma SafraTarefaNecessidade, resolvido a
    partir de itens já lançados no orçamento da safra (mesma categoria,
    origem_tipo=PRODUTO) — não substitui a escolha do usuário, só evita
    escolher de novo um produto que já foi decidido no orçamento.
    """
    model_config = ConfigDict(from_attributes=True)

    item_orcamento_id: UUID
    produto_id: UUID
    produto_nome: str
    descricao: str
    unidade: str
    custo_unitario_efetivo: float


class InsumoConsolidadoResponse(BaseModel):
    """
    Uma linha agrupada de necessidade técnica (mesma categoria + mesmo item de
    origem) somada entre TODAS as tarefas do plano — para o usuário configurar
    o recurso UMA VEZ e aplicar de uma vez às tarefas pendentes, em vez de
    entrar tarefa por tarefa.

    `tipo_recurso` diz qual fluxo de aplicação usar:
      INSUMO      -> produto comercial (PlanoOperacionalTarefaInsumo)
      MAQUINARIO  -> máquina/implemento (PlanoOperacionalTarefaMaquinario)
      MAO_DE_OBRA -> tipo de serviço + pessoa (PlanoOperacionalTarefaMaoObra)
    """
    chave_grupo: str
    categoria: str
    titulo: str
    unidade: str
    quantidade_total: float
    quantidade_tarefas: int
    quantidade_pendentes: int
    necessidade_ids_pendentes: List[UUID]
    tipo_recurso: str = "INSUMO"


class AplicarInsumoLoteRequest(BaseModel):
    necessidade_ids: List[UUID] = Field(..., min_length=1)
    produto_id: UUID
    deposito_id: Optional[UUID] = None


class AplicarInsumoLoteResponse(BaseModel):
    quantidade_aplicada: int
    quantidade_ignorada: int


class AplicarMaquinarioLoteRequest(BaseModel):
    necessidade_ids: List[UUID] = Field(..., min_length=1)
    maquina_id: Optional[UUID] = None
    implemento_id: Optional[UUID] = None


class AplicarMaoObraLoteRequest(BaseModel):
    necessidade_ids: List[UUID] = Field(..., min_length=1)
    tipo_servico_id: UUID
    pessoa_id: Optional[UUID] = None
    quantidade_pessoas: int = Field(1, gt=0)


class PlanoOperacionalTarefaInsumoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    plano_operacional_tarefa_id: UUID
    safra_tarefa_necessidade_id: Optional[UUID]
    produto_id: UUID
    deposito_id: Optional[UUID]
    dose_planejada: Optional[float]
    unidade_dose: str
    quantidade_planejada: float
    quantidade_disponivel_snapshot: Optional[float]
    quantidade_reservada: Optional[float]
    quantidade_faltante: Optional[float]
    custo_unitario_snapshot: Optional[float]
    custo_total_estimado: Optional[float]
    fonte_custo: Optional[str]
    substitui_item_id: Optional[UUID]
    reserva_estoque_id: Optional[UUID]
    created_at: datetime
    updated_at: datetime


class PlanoOperacionalTarefaMaoObraCreate(BaseModel):
    tipo_servico_id: UUID
    pessoa_id: Optional[UUID] = None
    funcao: Optional[str] = Field(None, max_length=100)
    quantidade_pessoas: int = Field(1, gt=0)
    # Se `horas_estimadas` for informado, prevalece sobre a fórmula abaixo.
    horas_estimadas: Optional[float] = Field(None, gt=0)
    horas_fixas: float = Field(0.0, ge=0)
    horas_por_hectare: float = Field(0.0, ge=0)


class PlanoOperacionalTarefaMaoObraUpdate(BaseModel):
    tipo_servico_id: Optional[UUID] = None
    pessoa_id: Optional[UUID] = None
    funcao: Optional[str] = Field(None, max_length=100)
    quantidade_pessoas: Optional[int] = Field(None, gt=0)
    horas_estimadas: Optional[float] = Field(None, gt=0)


class PlanoOperacionalTarefaMaoObraResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    plano_operacional_tarefa_id: UUID
    tipo_servico_id: UUID
    pessoa_id: Optional[UUID]
    funcao: Optional[str]
    quantidade_pessoas: int
    horas_estimadas: Optional[float]
    custo_hora_snapshot: Optional[float]
    custo_total_estimado: Optional[float]
    fonte_custo: Optional[str]
    created_at: datetime
    updated_at: datetime


class PlanoOperacionalTarefaMaquinarioCreate(BaseModel):
    maquina_id: Optional[UUID] = None
    implemento_id: Optional[UUID] = None
    # Ao menos um de maquina_id/implemento_id é exigido — validado no service
    # (não no schema, para poder dar mensagem de negócio consistente).
    horas_estimadas: Optional[float] = Field(None, gt=0)


class PlanoOperacionalTarefaMaquinarioUpdate(BaseModel):
    maquina_id: Optional[UUID] = None
    implemento_id: Optional[UUID] = None
    horas_estimadas: Optional[float] = Field(None, gt=0)


class PlanoOperacionalTarefaMaquinarioResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    plano_operacional_tarefa_id: UUID
    maquina_id: Optional[UUID]
    implemento_id: Optional[UUID]
    horas_estimadas: Optional[float]
    custo_hora_maquina_snapshot: Optional[float]
    custo_hora_implemento_snapshot: Optional[float]
    custo_total_estimado: Optional[float]
    fonte_custo: Optional[str]
    created_at: datetime
    updated_at: datetime


class GerarOSItemInput(BaseModel):
    plano_operacional_tarefa_id: UUID
    data_prevista: date
    operador_id: Optional[UUID] = None
    maquina_id: Optional[UUID] = None
    implemento_id: Optional[UUID] = None


class GerarOSLoteRequest(BaseModel):
    itens: List[GerarOSItemInput] = Field(..., min_length=1)


class GerarOSResultado(BaseModel):
    plano_operacional_tarefa_id: UUID
    sucesso: bool
    operacao_agricola_id: Optional[UUID] = None
    erro: Optional[str] = None


class GerarOSLoteResponse(BaseModel):
    resultados: List[GerarOSResultado]
