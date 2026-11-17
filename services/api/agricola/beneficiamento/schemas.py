from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID
from datetime import date, datetime
from typing import Optional, List


class LoteBeneficiamentoCafeDetalheCreate(BaseModel):
    """OPERATIONS-GAP-01 §21.15/§21.21: dados específicos de café (ABIC/SCA),
    extensão 1:1 opcional — só preenchida quando o lote é de café."""
    metodo: str = Field(..., pattern="^(NATURAL|LAVADO|HONEY|DESCASCADO)$")
    local_secagem: str | None = None
    peneira_principal: str | None = None
    bebida: str | None = None
    pontuacao_scaa: float | None = Field(None, ge=0, le=100)
    defeitos_intrinsecos: int | None = None
    defeitos_extrinsecos: int | None = None


class LoteBeneficiamentoCafeDetalheUpdate(BaseModel):
    metodo: str | None = Field(None, pattern="^(NATURAL|LAVADO|HONEY|DESCASCADO)$")
    local_secagem: str | None = None
    peneira_principal: str | None = None
    bebida: str | None = None
    pontuacao_scaa: float | None = Field(None, ge=0, le=100)
    defeitos_intrinsecos: int | None = None
    defeitos_extrinsecos: int | None = None


class LoteBeneficiamentoCafeDetalheRead(BaseModel):
    metodo: str
    local_secagem: str | None
    peneira_principal: str | None
    bebida: str | None
    pontuacao_scaa: float | None
    defeitos_intrinsecos: int | None
    defeitos_extrinsecos: int | None

    model_config = ConfigDict(from_attributes=True)


class LoteBeneficiamentoCreate(BaseModel):
    safra_id: UUID
    talhao_id: UUID | None = None
    production_unit_id: UUID | None = None
    romaneio_id: UUID | None = None
    numero_lote: str
    data_entrada: date
    peso_entrada_kg: float = Field(..., gt=0)
    umidade_entrada_pct: float | None = Field(None, ge=0, le=100)
    fator_esperado_manual: float | None = Field(
        None, gt=0, description="Relação entrada/saída esperada para culturas sem extensão de café"
    )
    observacoes: str | None = None
    detalhe_cafe: LoteBeneficiamentoCafeDetalheCreate | None = None


class LoteFromRomaneiosRequest(BaseModel):
    """Request para criar lote a partir de múltiplos romaneios."""
    romaneio_ids: List[UUID] = Field(..., min_items=1, description="IDs dos romaneios a agrupar")
    numero_lote: Optional[str] = Field(None, description="Se None, gera automático")
    detalhe_cafe: LoteBeneficiamentoCafeDetalheCreate | None = None


class LoteBeneficiamentoUpdate(BaseModel):
    status: str | None = None
    production_unit_id: UUID | None = None
    data_inicio_secagem: date | None = None
    data_fim_secagem: date | None = None
    data_saida: date | None = None
    peso_saida_kg: float | None = Field(None, gt=0)
    umidade_saida_pct: float | None = Field(None, ge=0, le=100)
    fator_esperado_manual: float | None = Field(None, gt=0)
    perda_secagem_kg: float | None = Field(None, ge=0)
    perda_quebra_kg: float | None = Field(None, ge=0)
    perda_defeito_kg: float | None = Field(None, ge=0)
    armazem_id: UUID | None = None
    saca_inicio: int | None = None
    saca_fim: int | None = None
    observacoes: str | None = None
    detalhe_cafe: LoteBeneficiamentoCafeDetalheUpdate | None = None


class LoteBeneficiamentoResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    safra_id: UUID
    talhao_id: UUID | None
    production_unit_id: UUID | None = None
    romaneio_id: UUID | None
    numero_lote: str
    status: str
    data_entrada: date
    peso_entrada_kg: float
    umidade_entrada_pct: float | None
    data_inicio_secagem: date | None
    data_fim_secagem: date | None
    dias_secagem: int | None
    data_saida: date | None
    peso_saida_kg: float | None
    umidade_saida_pct: float | None
    fator_reducao: float | None
    fator_esperado_manual: float | None
    sacas_beneficiadas: float | None
    perda_pct: float | None
    perda_secagem_kg: float | None
    perda_quebra_kg: float | None
    perda_defeito_kg: float | None
    armazem_id: UUID | None
    saca_inicio: int | None
    saca_fim: int | None
    observacoes: str | None
    detalhe_cafe: LoteBeneficiamentoCafeDetalheRead | None = None
    romaneios_vinculados: Optional[List[UUID]] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BeneficiamentoKPIs(BaseModel):
    total_lotes: int
    peso_entrada_total_kg: float
    peso_saida_total_kg: float
    sacas_beneficiadas_total: float
    fator_reducao_medio: float | None
    lotes_em_processo: int
    lotes_concluidos: int
    pontuacao_media_scaa: float | None


class RendimentoPorMetodo(BaseModel):
    metodo: str
    total_lotes: int
    peso_entrada_kg: float
    peso_saida_kg: float
    sacas_beneficiadas: float
    fator_reducao_real: float | None
    fator_reducao_esperado: float
    eficiencia_pct: float
    perda_secagem_kg: float
    perda_quebra_kg: float
    perda_defeito_kg: float
    perda_total_kg: float


class BeneficiamentoRelatorioRendimento(BaseModel):
    safra_id: UUID
    total_lotes: int
    peso_entrada_total_kg: float
    peso_saida_total_kg: float
    sacas_total: float
    rendimento_medio_pct: float
    por_metodo: list[RendimentoPorMetodo]


class CafeQualidadeMargemItem(BaseModel):
    lote_id: UUID
    numero_lote: str
    status: str
    metodo: Optional[str] = None
    bebida: Optional[str] = None
    peneira_principal: Optional[str] = None
    pontuacao_scaa: Optional[float] = None
    especial: bool = False
    sacas_beneficiadas: float = 0.0
    custo_por_saca: Optional[float] = None
    preco_venda_por_saca: Optional[float] = None
    margem_por_saca: Optional[float] = None
    margem_pct: Optional[float] = None
    receita_estimada: float = 0.0
    origem_preco: str = "SEM_VENDA"


class CafeQualidadeMargemPorBebida(BaseModel):
    bebida: str
    total_lotes: int
    sacas_totais: float
    scaa_medio: Optional[float] = None
    preco_medio_saca: Optional[float] = None
    margem_media_saca: Optional[float] = None


class CafeQualidadeMargemResponse(BaseModel):
    safra_id: UUID
    custo_total_safra: float = 0.0
    total_sacas_safra: float = 0.0
    custo_medio_saca_safra: Optional[float] = None
    preco_medio_saca_especial: Optional[float] = None
    preco_medio_saca_convencional: Optional[float] = None
    premio_qualidade_pct: Optional[float] = None
    lotes: list[CafeQualidadeMargemItem]
    por_bebida: list[CafeQualidadeMargemPorBebida]
