import uuid
from datetime import date, datetime
from sqlalchemy import String, Boolean, Integer, Text, ForeignKey, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Uuid as UUID
from core.database import Base


class SafraChecklistItem(Base):
    """Instância de um item de checklist gerada para uma safra específica ao entrar em uma fase."""
    __tablename__ = "safra_checklist_itens"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    safra_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("safras.id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    template_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("phase_template_checklist_items.id", ondelete="SET NULL"), nullable=True)

    fase: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    titulo: Mapped[str] = mapped_column(String(200), nullable=False)
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)
    obrigatorio: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ordem: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    concluido: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    usuario_id: Mapped[uuid.UUID | None] = mapped_column(UUID, nullable=True)
    concluido_em: Mapped[datetime | None] = mapped_column(nullable=True)

    cancelado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    usuario_cancelamento_id: Mapped[uuid.UUID | None] = mapped_column(UUID, nullable=True)
    cancelado_em: Mapped[datetime | None] = mapped_column(nullable=True)
    motivo_cancelamento: Mapped[str | None] = mapped_column(Text, nullable=True)

    # TAREFA_CAMPO | SOLICITACAO_ESTOQUE | MANUAL — copiado do template na geração.
    tipo_resultado: Mapped[str] = mapped_column(String(30), nullable=False, default="MANUAL")
    operacao_agricola_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("operacoes_agricolas.id", ondelete="SET NULL"), nullable=True)
    reserva_estoque_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("estoque_reservas.id", ondelete="SET NULL"), nullable=True)
    requisicao_material_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("estoque_requisicoes.id", ondelete="SET NULL"), nullable=True)

    # Responsável + prazo só fazem sentido para tipo_resultado != TAREFA_CAMPO
    # (TAREFA_CAMPO já tem responsável via operador_id da OS/tarefa de campo).
    responsavel_id: Mapped[uuid.UUID | None] = mapped_column(UUID, nullable=True)
    prazo_resposta: Mapped[date | None] = mapped_column(nullable=True)

    # PENDENTE | OK | OK_PARCIAL | BLOQUEANTE — veredito usado por
    # SafraService.avancar_fase em vez do booleano `concluido` isolado.
    status_verificacao: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDENTE")
    justificativa_ok_parcial: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(server_default=text("(CURRENT_TIMESTAMP)"))

