from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Boolean, Date, DateTime, Text, ForeignKey, text, JSON, Numeric, Integer
from uuid import UUID
import uuid
from datetime import datetime
from core.database import Base

class LoteRastreabilidade(Base):
    __tablename__ = "lotes_rastreabilidade"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    
    codigo_lote: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    safra_id: Mapped[UUID] = mapped_column(ForeignKey("safras.id", ondelete="CASCADE"), nullable=False)
    talhao_id: Mapped[UUID] = mapped_column(ForeignKey("cadastros_areas_rurais.id", ondelete="CASCADE"), nullable=False)
    
    produto: Mapped[str] = mapped_column(String(100), nullable=False)
    variedade: Mapped[str | None] = mapped_column(String(100))
    
    quantidade_total: Mapped[float] = mapped_column(default=0)
    unidade: Mapped[str] = mapped_column(String(20), default="KG")
    
    data_geracao: Mapped[datetime] = mapped_column(server_default=text("(CURRENT_TIMESTAMP)"))
    qr_code_url: Mapped[str | None] = mapped_column(String(255))
    
    status: Mapped[str] = mapped_column(String(20), default="ATIVO") # ATIVO, EMBARCADO, PROCESSADO
    
    # Metadados de Auditoria / Certificações
    certificacoes: Mapped[list[str]] = mapped_column(JSON, default=list) # ["GLOBALGAP", "ORGÂNICO"]
    
    observacoes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=text("(CURRENT_TIMESTAMP)"))

class CertificacaoPropriedade(Base):
    __tablename__ = "certificacoes_propriedade"
    
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    unidade_produtiva_id: Mapped[UUID] = mapped_column(ForeignKey("unidades_produtivas.id", ondelete="CASCADE"), nullable=False)
    
    nome: Mapped[str] = mapped_column(String(100), nullable=False) # Ex: GlobalGap, RTRS
    extensao: Mapped[str | None] = mapped_column(String(100)) # Escopo
    
    data_emissao: Mapped[datetime] = mapped_column(Date)
    data_validade: Mapped[datetime] = mapped_column(Date)
    
    orgao_certificador: Mapped[str | None] = mapped_column(String(100))
    numero_registro: Mapped[str | None] = mapped_column(String(50))
    
    status: Mapped[str] = mapped_column(String(20), default="VALIDA") # VALIDA, EXPIRADA, SUSPENSA
    
    link_documento: Mapped[str | None] = mapped_column(String(255))
    
    created_at: Mapped[datetime] = mapped_column(server_default=text("(CURRENT_TIMESTAMP)"))


class CadernoLoteComercial(Base):
    __tablename__ = "caderno_lotes_comerciais"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    comercializacao_id: Mapped[UUID] = mapped_column(ForeignKey("financeiro_comercializacoes.id", ondelete="RESTRICT"), nullable=False, index=True)
    produto_colhido_id: Mapped[UUID | None] = mapped_column(ForeignKey("agricola_produtos_colhidos.id", ondelete="SET NULL"), nullable=True, index=True)
    lote_beneficiamento_id: Mapped[UUID | None] = mapped_column(ForeignKey("cafe_lotes_beneficiamento.id", ondelete="SET NULL"), nullable=True, index=True)
    # OPERATIONS-GAP-01 §21.11: vínculo opcional ao lote de campo/pré-comercial
    # (LoteRastreabilidade, granularidade safra+talhão) quando o mesmo lote físico
    # também tiver um passaporte comercial gerado aqui — os dois conceitos são
    # legítimos e desconectados por padrão; este campo só permite navegação
    # cruzada quando alguém explicitamente ligar os dois, nunca é preenchido
    # automaticamente.
    lote_rastreabilidade_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("lotes_rastreabilidade.id", ondelete="SET NULL"), nullable=True, index=True
    )

    codigo_lote: Mapped[str] = mapped_column(String(100), nullable=False)
    qr_code_token: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    peso_liquido_kg: Mapped[float] = mapped_column(Numeric(14, 3), nullable=False)
    quantidade_volumes: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="RASCUNHO") # RASCUNHO, ATIVO, REVOGADO

    snapshot_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    snapshot_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    snapshot_gerado_em: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    assinado_por_usuario_id: Mapped[UUID | None] = mapped_column(ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True)
    assinado_em: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(server_default=text("(CURRENT_TIMESTAMP)"))
    updated_at: Mapped[datetime] = mapped_column(server_default=text("(CURRENT_TIMESTAMP)"), onupdate=datetime.utcnow)
