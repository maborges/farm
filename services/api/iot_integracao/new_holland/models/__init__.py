"""Modelos para Sprint 26: New Holland, Marketplace, Carbono."""
# ruff: noqa: E501, F401, I001, W293

from sqlalchemy import Column, Integer, String, Float, DateTime, Date, ForeignKey, Text, Boolean, JSON, Uuid
from sqlalchemy.orm import backref, relationship
from datetime import datetime

from core.database import Base
from integracoes.models import MarketplaceIntegracao, TenantIntegracao


# ============================================
# NEW HOLLAND PLM CONNECT
# ============================================

class IntegracaoNewHolland(Base):
    """Configuração de integração com New Holland PLM Connect."""
    __tablename__ = "integracao_new_holland"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(50), nullable=False, index=True)
    unidade_produtiva_id = Column(Integer, ForeignKey("unidades_produtivas.id"))
    
    # Credenciais
    client_id = Column(String(200))
    client_secret = Column(String(200))
    access_token = Column(Text)
    refresh_token = Column(Text)
    token_expires_at = Column(DateTime)
    
    # Status
    status = Column(String(50), default="pendente")  # pendente, ativo, erro
    ultimo_sync = Column(DateTime)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relacionamentos
    maquinas = relationship("MaquinaNewHolland", back_populates="integracao", cascade="all, delete-orphan")


class MaquinaNewHolland(Base):
    """Máquinas vinculadas à conta New Holland."""
    __tablename__ = "maquinas_new_holland"

    id = Column(Integer, primary_key=True, index=True)
    integracao_id = Column(Integer, ForeignKey("integracao_new_holland.id"), nullable=False)
    nh_id = Column(String(100), nullable=False)  # ID na API New Holland
    nome = Column(String(200))
    modelo = Column(String(100))
    marca = Column(String(100), default="New Holland")
    ano = Column(Integer)
    numero_serie = Column(String(100))
    horas_uso = Column(Float)
    status = Column(String(50))
    ultima_atualizacao = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relacionamentos
    integracao = relationship("IntegracaoNewHolland", back_populates="maquinas")


class MarketplaceAvaliacao(Base):
    """Avaliações de integrações do marketplace."""
    __tablename__ = "marketplace_avaliacoes"

    id = Column(Integer, primary_key=True, index=True)
    integracao_id = Column(Integer, ForeignKey("marketplace_integracoes.id"), nullable=False)
    tenant_id = Column(String(50), nullable=False)
    
    # Avaliação
    nota = Column(Integer, nullable=False)  # 1-5
    titulo = Column(String(200))
    comentario = Column(Text)
    
    # Status
    aprovada = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)


# ============================================
# PEGADA DE CARBONO
# ============================================

class CarbonoEmissao(Base):
    """Registro de emissões de carbono."""
    __tablename__ = "carbono_emissoes"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(50), nullable=False, index=True)
    unidade_produtiva_id = Column(Uuid(as_uuid=True), ForeignKey("production_units.id"))
    
    # Tipo de emissão
    escopo = Column(Integer, nullable=False)  # 1, 2, 3
    categoria = Column(String(100), nullable=False)  # combustivel, energia, insumos, etc.
    fonte = Column(String(200))  # Fonte específica (ex: trator X, galpão Y)
    
    # Dados da emissão
    atividade = Column(String(200))  # Descrição da atividade
    quantidade = Column(Float, nullable=False)  # Quantidade da atividade
    unidade = Column(String(50), nullable=False)  # L, kWh, kg, km, etc.
    
    # Cálculo
    fator_emissao = Column(Float)  # kgCO2e por unidade
    fator_emissao_referencia = Column(String(200))  # Fonte do fator (IPCC, etc.)
    total_co2e = Column(Float)  # Total em kgCO2e
    
    # Período
    data_referencia = Column(DateTime, nullable=False)
    
    # Metadados
    observacoes = Column(Text)
    arquivo_comprovante = Column(String(500))
    
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(Uuid(as_uuid=True), ForeignKey("usuarios.id"))


class CarbonoProjeto(Base):
    """Projetos de crédito de carbono."""
    __tablename__ = "carbono_projetos"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(50), nullable=False, index=True)
    unidade_produtiva_id = Column(Uuid(as_uuid=True), ForeignKey("production_units.id", ondelete="CASCADE"))
    
    # Identificação
    nome = Column(String(200), nullable=False)
    descricao = Column(Text)
    
    # Tipo de projeto
    tipo = Column(String(50), nullable=False)  # florestamento, reflorestamento, ilpf, plantio_direto
    metodologia = Column(String(100))  # Verra, Gold Standard, etc.
    
    # Área
    area_ha = Column(Float, nullable=False)
    geometria = Column(JSON)  # GeoJSON da área
    
    # Créditos
    creditos_estimados = Column(Float)  # tCO2e estimados
    creditos_verificados = Column(Float)  # tCO2e verificados
    creditos_vendidos = Column(Float)  # tCO2e vendidos
    
    # Status
    status = Column(String(50), default="planejamento")  # planejamento, implementacao, verificacao, certificado
    data_inicio = Column(Date)
    data_verificacao = Column(Date)
    data_certificacao = Column(Date)
    
    # Certificação
    certificador = Column(String(200))
    numero_registro = Column(String(100))
    padrao = Column(String(50))  # Verra, Gold Standard
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class CarbonoRelatorio(Base):
    """Relatórios de pegada de carbono."""
    __tablename__ = "carbono_relatorios"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(50), nullable=False, index=True)
    
    # Período
    periodo_inicio = Column(DateTime, nullable=False)
    periodo_fim = Column(DateTime, nullable=False)
    
    # Totais por escopo
    escopo_1_total = Column(Float, default=0)  # Emissões diretas
    escopo_2_total = Column(Float, default=0)  # Energia indireta
    escopo_3_total = Column(Float, default=0)  # Outras indiretas
    total_geral = Column(Float, default=0)
    
    # Compensações
    creditos_gerados = Column(Float, default=0)
    saldo_liquido = Column(Float, default=0)  # Total - Créditos
    
    # Intensidade
    intensidade_carbono = Column(Float)  # kgCO2e por unidade produzida
    unidade_producao = Column(String(50))
    total_produzido = Column(Float)
    
    # Status
    status = Column(String(50), default="rascunho")  # rascunho, publicado, verificado
    arquivo_pdf = Column(String(500))
    
    created_at = Column(DateTime, default=datetime.utcnow)
    published_at = Column(DateTime)
