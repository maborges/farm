import uuid
from datetime import datetime, date
from sqlalchemy import String, Numeric, Boolean, Date, Text, ForeignKey, Integer, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Uuid as UUIDCol
from core.database import Base


class LoteBeneficiamento(Base):
    """
    Lote de beneficiamento pós-colheita — genérico, cobre qualquer cultura
    que precise de secagem/classificação entre a colheita e o estoque.

    OPERATIONS-GAP-01 §21.15/§21.21: campos específicos de café (método,
    peneira, bebida ABIC, pontuação SCA, defeitos) foram extraídos para
    `LoteBeneficiamentoCafeDetalhe` (extensão 1:1 opcional) — culturas sem
    essa extensão usam `fator_esperado_manual` para calcular perda.
    """
    __tablename__ = "agricola_lotes_beneficiamento"

    id: Mapped[uuid.UUID] = mapped_column(UUIDCol(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUIDCol(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    safra_id: Mapped[uuid.UUID] = mapped_column(
        UUIDCol(as_uuid=True), ForeignKey("safras.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    cultivo_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDCol(as_uuid=True), ForeignKey("cultivos.id", ondelete="SET NULL"),
        nullable=True, index=True,
        comment="Cultivo específico processado neste lote (rastreamento de produção por cultura)"
    )
    production_unit_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDCol(as_uuid=True), ForeignKey("production_units.id", ondelete="SET NULL"),
        nullable=True
    )
    talhao_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDCol(as_uuid=True), ForeignKey("cadastros_areas_rurais.id", ondelete="SET NULL"),
        nullable=True, index=True
    )
    romaneio_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDCol(as_uuid=True), ForeignKey("romaneios_colheita.id", ondelete="SET NULL"),
        nullable=True, index=True,
        comment="FK para rastreabilidade: qual romaneio originou este lote"
    )
    lote_estoque_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDCol(as_uuid=True), ForeignKey("estoque_lotes.id", ondelete="SET NULL"),
        nullable=True, index=True,
        comment="FK para LoteEstoque criado ao armazenar"
    )

    # Identificação do lote
    numero_lote: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default="RECEBIMENTO",
        comment="RECEBIMENTO, SECAGEM, CLASSIFICACAO, ARMAZENADO, VENDIDO"
    )

    # Entrada
    data_entrada: Mapped[date] = mapped_column(Date, nullable=False)
    peso_entrada_kg: Mapped[float] = mapped_column(Numeric(12, 3), nullable=False)
    umidade_entrada_pct: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)

    # Secagem (processo genérico — terminologia específica de local fica na extensão)
    data_inicio_secagem: Mapped[date | None] = mapped_column(Date, nullable=True)
    data_fim_secagem: Mapped[date | None] = mapped_column(Date, nullable=True)
    dias_secagem: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Saída
    data_saida: Mapped[date | None] = mapped_column(Date, nullable=True)
    peso_saida_kg: Mapped[float | None] = mapped_column(Numeric(12, 3), nullable=True)
    umidade_saida_pct: Mapped[float | None] = mapped_column(
        Numeric(5, 2), nullable=True,
        comment="Umidade final: padrão MAPA = 12%"
    )

    # Calculados automaticamente
    fator_reducao: Mapped[float | None] = mapped_column(
        Numeric(6, 3), nullable=True,
        comment="Relação entrada/saída real. Ex: 4.8 = 4,8 kg entrada → 1 kg beneficiado"
    )
    fator_esperado_manual: Mapped[float | None] = mapped_column(
        Numeric(6, 3), nullable=True,
        comment="Relação entrada/saída esperada, usada no cálculo de perda_pct quando não há "
                "extensão de café (que usa FATOR_ESPERADO por método)"
    )
    sacas_beneficiadas: Mapped[float | None] = mapped_column(
        Numeric(10, 3), nullable=True,
        comment="Sacas de 60 kg beneficiadas"
    )
    perda_pct: Mapped[float | None] = mapped_column(
        Numeric(5, 2), nullable=True,
        comment="% de perda no processamento vs. esperado"
    )

    # Perdas detalhadas (rendimento granular)
    perda_secagem_kg: Mapped[float | None] = mapped_column(Numeric(10, 3), nullable=True)
    perda_quebra_kg: Mapped[float | None] = mapped_column(Numeric(10, 3), nullable=True)
    perda_defeito_kg: Mapped[float | None] = mapped_column(Numeric(10, 3), nullable=True)

    # Armazenagem
    armazem_id: Mapped[uuid.UUID | None] = mapped_column(UUIDCol(as_uuid=True), nullable=True)
    saca_inicio: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="Nº da primeira saca")
    saca_fim: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="Nº da última saca")

    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=text("(CURRENT_TIMESTAMP)"))
    updated_at: Mapped[datetime] = mapped_column(
        server_default=text("(CURRENT_TIMESTAMP)"), onupdate=datetime.utcnow
    )

    detalhe_cafe: Mapped["LoteBeneficiamentoCafeDetalhe | None"] = relationship(
        back_populates="lote", lazy="noload", uselist=False, cascade="all, delete-orphan"
    )


class LoteBeneficiamentoCafeDetalhe(Base):
    """OPERATIONS-GAP-01 §21.21: extensão 1:1 opcional de LoteBeneficiamento
    com os campos específicos de café (método de processamento, classificação
    ABIC/SCA). Presença desta linha é o discriminador de "lote é café"."""
    __tablename__ = "cafe_lote_beneficiamento_detalhes"

    id: Mapped[uuid.UUID] = mapped_column(UUIDCol(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUIDCol(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    lote_id: Mapped[uuid.UUID] = mapped_column(
        UUIDCol(as_uuid=True), ForeignKey("agricola_lotes_beneficiamento.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True
    )

    metodo: Mapped[str] = mapped_column(
        String(20), nullable=False,
        comment="NATURAL, LAVADO, HONEY, DESCASCADO"
    )
    local_secagem: Mapped[str | None] = mapped_column(
        String(30), nullable=True,
        comment="TERREIRO_CIMENTO, TERREIRO_SUSPENSO, SECADOR_MECANICO, MISTO"
    )
    peneira_principal: Mapped[str | None] = mapped_column(
        String(10), nullable=True,
        comment="Peneira predominante: 17+, 15/16, 13/14, etc."
    )
    bebida: Mapped[str | None] = mapped_column(
        String(30), nullable=True,
        comment="Classificação ABIC: ESTRITAMENTE_MOLE, MOLE, APENAS_MOLE, DURA, RIADA, RIO"
    )
    pontuacao_scaa: Mapped[float | None] = mapped_column(
        Numeric(4, 2), nullable=True,
        comment="Pontuação SCA (0-100). ≥ 80 = specialty coffee"
    )
    defeitos_intrinsecos: Mapped[int | None] = mapped_column(Integer, nullable=True)
    defeitos_extrinsecos: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(server_default=text("(CURRENT_TIMESTAMP)"))
    updated_at: Mapped[datetime] = mapped_column(
        server_default=text("(CURRENT_TIMESTAMP)"), onupdate=datetime.utcnow
    )

    lote: Mapped["LoteBeneficiamento"] = relationship(back_populates="detalhe_cafe", lazy="noload")


class LoteBeneficiamentoRomaneio(Base):
    """N:N junction table: um LoteBeneficiamento pode ter múltiplos Romaneios (blend/agrupamento)."""
    __tablename__ = "cafe_lote_beneficiamento_romaneios"

    id: Mapped[uuid.UUID] = mapped_column(UUIDCol(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUIDCol(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    lote_id: Mapped[uuid.UUID] = mapped_column(
        UUIDCol(as_uuid=True), ForeignKey("agricola_lotes_beneficiamento.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    romaneio_id: Mapped[uuid.UUID] = mapped_column(
        UUIDCol(as_uuid=True), ForeignKey("romaneios_colheita.id", ondelete="SET NULL"),
        nullable=False, index=True
    )
    peso_entrada_kg: Mapped[float] = mapped_column(Numeric(12, 3), nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=text("(CURRENT_TIMESTAMP)"))
