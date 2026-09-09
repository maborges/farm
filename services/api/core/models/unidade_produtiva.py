import uuid
from decimal import Decimal
from datetime import datetime, timezone
from sqlalchemy import String, Boolean, DateTime, ForeignKey, JSON, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Uuid as UUID
from core.database import Base

class UnidadeProdutiva(Base):
    __tablename__ = "unidades_produtivas"

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "id",
            name="uq_unidades_produtivas_tenant_id_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Campo essencial para a barreira RLS
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )

    nome: Mapped[str] = mapped_column(String(150), nullable=False)

    # Tipo da propriedade (linguagem do produtor)
    tipo_propriedade: Mapped[str] = mapped_column(
        String(30), nullable=False, default="fazenda",
        comment="fazenda | sitio | chacara | arrendamento | parceria"
    )

    cpf_cnpj: Mapped[str | None] = mapped_column(String(18), nullable=True, comment="CPF (11 dígitos) ou CNPJ (14 dígitos) do proprietário")
    inscricao_estadual: Mapped[str | None] = mapped_column(String(50), nullable=True)


    # Localização
    cep: Mapped[str | None] = mapped_column(String(9), nullable=True)
    logradouro: Mapped[str | None] = mapped_column(String(255), nullable=True)
    numero: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="Número do endereço")
    complemento: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="Complemento do endereço")
    bairro: Mapped[str | None] = mapped_column(String(100), nullable=True)
    uf: Mapped[str | None] = mapped_column(String(2), nullable=True, comment="UF (estado) da propriedade")
    municipio: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ibge_municipio_codigo: Mapped[str | None] = mapped_column(String(7), nullable=True, comment="Código IBGE do município")

    # Áreas (Numeric para precisão fiscal — ITR, CAR)
    area_total_ha: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    area_total_calculada_ha: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 4),
        nullable=True,
        comment="Área total calculada por georreferenciamento. Campo somente leitura.",
    )
    area_app_ha: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True, comment="Área de Preservação Permanente — referência inicial, calculada via polígonos APP")
    area_rl_ha: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True, comment="Área de Reserva Legal — referência inicial, calculada via polígonos RL")

    coordenadas_sede: Mapped[str | None] = mapped_column(String(100), nullable=True)
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="URL do logotipo da propriedade")

    # Polígono GeoJSON da propriedade
    geometria: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    ativo: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )


# Compatibilidade legada. Não usar como fonte canônica em novos fluxos.
# "Fazenda" permanece apenas como alias histórico de UnidadeProdutiva.
Fazenda = UnidadeProdutiva
