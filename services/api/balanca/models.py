import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import String, DateTime, ForeignKey, Text, Index, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Uuid as UUID
from sqlalchemy.dialects.postgresql import ARRAY, JSONB

from core.database import Base


class DispositivoBalanca(Base):
    """Estação de balança (dispositivo fixo), não vinculada a um operador específico."""
    __tablename__ = "balanca_dispositivos"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )

    nome: Mapped[str] = mapped_column(String(100), nullable=False)
    device_fingerprint: Mapped[str | None] = mapped_column(String(256), nullable=True, unique=True)
    pin_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    activation_code: Mapped[str | None] = mapped_column(String(8), nullable=True)
    activation_code_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    status: Mapped[str] = mapped_column(String(20), default="PENDENTE", nullable=False)
    # PENDENTE → aguardando ativação | ATIVO | REVOGADO

    fazenda_ids: Mapped[list] = mapped_column(ARRAY(UUID(as_uuid=True)), nullable=False, default=list)

    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    revoked_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    # Balança física (equipamento) que este terminal acessa. Opcional — nem todo
    # dispositivo já tem o equipamento cadastrado, e vários terminais podem
    # apontar para a mesma balança física (N:1, não N:N: mantém simples).
    balanca_fisica_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("balanca_fisicas.id", ondelete="SET NULL"), nullable=True, index=True
    )

    __table_args__ = (
        Index("ix_balanca_disp_tenant_status", "tenant_id", "status"),
        Index("ix_balanca_disp_activation", "activation_code"),
    )


class BalancaFisica(Base):
    """O equipamento de pesagem em si (ativo físico, regulado por metrologia
    legal — aferição INMETRO periódica) — separado do terminal/estação PWA
    (DispositivoBalanca), que é só o hardware que roda o app e pode trocar
    sem que a balança física mude."""
    __tablename__ = "balanca_fisicas"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )

    nome: Mapped[str] = mapped_column(String(100), nullable=False)
    # Referenciado por convenção (mesmo princípio de origem_id/produto_id) —
    # sem FK direta para não acoplar a modelos de core/imóveis.
    unidade_produtiva_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)

    fabricante: Mapped[str | None] = mapped_column(String(100), nullable=True)
    modelo: Mapped[str | None] = mapped_column(String(100), nullable=True)
    numero_serie: Mapped[str | None] = mapped_column(String(100), nullable=True)
    capacidade_kg: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)

    ativa: Mapped[bool] = mapped_column(default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_balanca_fisica_tenant", "tenant_id"),
    )


class AfericaoBalanca(Base):
    """Registro histórico de aferição/calibração de uma balança física —
    metrologia legal (INMETRO ou órgão delegado) exige aferição periódica."""
    __tablename__ = "balanca_afericoes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    balanca_fisica_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("balanca_fisicas.id", ondelete="CASCADE"), nullable=False, index=True
    )

    data_afericao: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    validade_ate: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    orgao_afericao: Mapped[str | None] = mapped_column(String(150), nullable=True)
    numero_certificado: Mapped[str | None] = mapped_column(String(100), nullable=True)
    resultado: Mapped[str] = mapped_column(String(30), nullable=False, default="APROVADA")
    # APROVADA | REPROVADA | APROVADA_COM_RESSALVA
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_balanca_afericao_balanca", "balanca_fisica_id", "data_afericao"),
    )


class OperadorBalanca(Base):
    """Operador habilitado a pesar em qualquer estação do tenant, autenticado por
    PIN pessoal (não confundir com o pin_hash de DispositivoBalanca, que é da
    estação/terminal). Cadastro próprio do módulo — referencia Pessoa (core) por
    convenção (pessoa_id), sem FK direta, mesmo princípio de desacoplamento usado
    em origem_id/produto_id."""
    __tablename__ = "balanca_operadores"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )

    pessoa_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    nome_exibicao: Mapped[str] = mapped_column(String(150), nullable=False)
    pin_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    status: Mapped[str] = mapped_column(String(20), default="ATIVO", nullable=False)
    # ATIVO | REVOGADO

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    revoked_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("tenant_id", "pessoa_id", name="uq_balanca_operador_tenant_pessoa"),
        Index("ix_balanca_operadores_tenant_status", "tenant_id", "status"),
    )


class OrdemPesagem(Base):
    """Solicitação de pesagem criada por um módulo cliente (romaneio, compras, vendas,
    pecuária, pessoas). Não referencia tabelas de outros módulos diretamente — origem
    é identificada de forma genérica para manter o módulo desacoplável."""
    __tablename__ = "balanca_ordens"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )

    origem_tipo: Mapped[str] = mapped_column(String(30), nullable=False)
    # COLHEITA | COMPRA | VENDA | PECUARIA | PESSOA | OUTRO
    origem_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)

    subject_type: Mapped[str] = mapped_column(String(20), nullable=False)
    # VEICULO | ANIMAL
    tipo_pesagem: Mapped[str] = mapped_column(String(30), nullable=False)
    # UNICA | DUPLA (chegada+saída) | DUPLA_ENTRADA_DESCARGA (chegada+pós-descarga) |
    # DUPLA_SAIDA_CARREGAMENTO (pré-carregamento+saída) — define as etapas de
    # Pesagem esperadas para esta ordem (ver Pesagem.etapa).

    status: Mapped[str] = mapped_column(String(20), default="PENDENTE", nullable=False, index=True)
    # PENDENTE | EM_PESAGEM | CONCLUIDA | CANCELADA

    solicitado_por: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    contexto: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    # dados livres do módulo cliente (placa, motorista, produto, brinco, lote etc.)

    # Produto/carga — sem FK direta a `core.cadastros.produtos`/estoque (mesmo
    # princípio de desacoplamento do origem_id): referência por convenção.
    produto_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    produto_tipo: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # COMMODITY | ALMOXARIFADO
    tipo_volume: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # SACA | BIG_BAG | GRANEL | TAMBOR | OUTRO
    quantidade_volumes: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)

    data_agendada: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    numero_documento_fiscal: Mapped[str | None] = mapped_column(String(60), nullable=True)

    # Peso líquido final da ordem — calculado quando o par de etapas esperado
    # (conforme tipo_pesagem) está completo. Não confundir com o peso de cada
    # Pesagem individual (peso_informado_kg/peso_aferido_kg por etapa).
    peso_liquido_kg: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)

    dispositivo_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("balanca_dispositivos.id", ondelete="SET NULL"), nullable=True, index=True
    )

    concluida_em: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    cancelada_em: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    motivo_cancelamento: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_balanca_ordens_tenant_status", "tenant_id", "status"),
        Index("ix_balanca_ordens_origem", "origem_tipo", "origem_id"),
    )


class Pesagem(Base):
    """Um evento físico de pesagem (uma passada pela balança). Uma OrdemPesagem
    tem 1 a N Pesagem conforme `OrdemPesagem.tipo_pesagem`:
    - UNICA: 1 pesagem (etapa=UNICA)
    - DUPLA: 2 pesagens (CHEGADA, SAIDA)
    - DUPLA_ENTRADA_DESCARGA: 2 pesagens (CHEGADA, POS_DESCARGA)
    - DUPLA_SAIDA_CARREGAMENTO: 2 pesagens (PRE_CARREGAMENTO, SAIDA)
    O peso líquido da ordem é calculado a partir do par de etapas quando completo
    (ver PesagemService) e fica em OrdemPesagem.peso_liquido_kg — não aqui."""
    __tablename__ = "balanca_pesagens"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ordem_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("balanca_ordens.id", ondelete="CASCADE"), nullable=False, index=True
    )
    dispositivo_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("balanca_dispositivos.id", ondelete="SET NULL"), nullable=True, index=True
    )

    numero_ticket: Mapped[str] = mapped_column(String(30), nullable=False)

    # Identificador local do dispositivo (UUID gerado offline), para idempotência no sync
    client_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)

    etapa: Mapped[str] = mapped_column(String(20), nullable=False, default="UNICA")
    # UNICA | CHEGADA | POS_DESCARGA | PRE_CARREGAMENTO | SAIDA

    # Peso informado (declarado — ex.: valor da NF/motorista) vs peso aferido
    # (o que a balança efetivamente mediu). São propositalmente dois campos —
    # divergência entre eles é sinal de auditoria, não erro.
    peso_informado_kg: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)
    peso_aferido_kg: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)
    peso_tara_kg: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)
    # Só usado na etapa UNICA (tara cadastrada do veículo, subtraída do aferido)

    captured_via: Mapped[str] = mapped_column(String(15), default="MANUAL", nullable=False)
    # MANUAL | ELETRONICA
    leitura_bruta: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # payload cru vindo da ponte de hardware (protocolo do indicador), quando aplicável

    placa: Mapped[str | None] = mapped_column(String(10), nullable=True)
    motorista: Mapped[str | None] = mapped_column(String(150), nullable=True)
    animal_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    pessoa_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    # Operador que realizou esta pesagem — Pessoa do cadastro core, não a
    # estação (dispositivo_id). Login por operador ainda não implementado no
    # PWA (fase futura); campo já existe para não exigir migration depois.
    operador_pessoa_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    data_pesagem: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    client_created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    client_updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("tenant_id", "client_id", name="uq_balanca_pesagem_tenant_client"),
        UniqueConstraint("tenant_id", "numero_ticket", name="uq_balanca_pesagem_tenant_ticket"),
        UniqueConstraint("ordem_id", "etapa", name="uq_balanca_pesagem_ordem_etapa"),
        Index("ix_balanca_pesagens_ordem", "ordem_id"),
    )


class SyncTombstoneBalanca(Base):
    """Registra deleções para que dispositivos de balança offline saibam o que remover no próximo pull."""
    __tablename__ = "balanca_sync_tombstones"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False)
    deleted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    deleted_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    __table_args__ = (
        Index("ix_balanca_tombstones_tenant_type_deleted", "tenant_id", "entity_type", "deleted_at"),
    )
