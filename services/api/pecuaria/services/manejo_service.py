import uuid
from datetime import date
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from core.base_service import BaseService
from core.exceptions import EntityNotFoundError, BusinessRuleError
from pecuaria.models.manejo import ManejoLote
from pecuaria.animal.models import Animal, LoteAnimal as LoteBovino
from pecuaria.schemas.manejo_schema import ManejoLoteCreate, TIPO_EVENTO_VALID

TIPOS_VALIDOS = TIPO_EVENTO_VALID

# Tipos que geram Despesa automaticamente
TIPOS_DESPESA = {"VACINACAO", "MEDICACAO"}
# Tipos que geram Receita automaticamente
TIPOS_RECEITA = {"VENDA", "ABATE"}


class ManejoLoteService(BaseService[ManejoLote]):
    """
    Service para registro de eventos de vida no rebanho.

    Args:
        tenant_id: ID do tenant para isolamento de dados.

    Raises:
        BusinessRuleError: Se o tipo de evento for inválido ou o lote não existir.
    """

    def __init__(self, tenant_id: uuid.UUID):
        super().__init__(ManejoLote, None, tenant_id)

    async def listar_por_lote(
        self, db: AsyncSession, *, lote_id: uuid.UUID
    ) -> list[ManejoLote]:
        """Lista todos os eventos de um lote específico."""
        stmt = (
            select(self.model)
            .where(
                self.model.tenant_id == self.tenant_id,
                self.model.lote_id == lote_id,
            )
            .order_by(self.model.data_evento.desc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def listar_todos(self, db: AsyncSession) -> list[ManejoLote]:
        """Lista todos os eventos do tenant ordenados por data."""
        stmt = (
            select(self.model)
            .where(self.model.tenant_id == self.tenant_id)
            .order_by(self.model.data_evento.desc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def registrar_evento(
        self, db: AsyncSession, *, obj_in: ManejoLoteCreate
    ) -> ManejoLote:
        """
        Registra um evento de manejo (nascimento, morte, pesagem, etc.).

        Raises:
            BusinessRuleError: Se tipo_evento inválido ou lote não pertence ao tenant.
        """
        if obj_in.tipo_evento not in TIPOS_VALIDOS:
            raise BusinessRuleError(
                f"Tipo de evento inválido. Use: {', '.join(sorted(TIPOS_VALIDOS))}"
            )

        # Verifica que o lote pertence ao tenant
        stmt_lote = select(LoteBovino).where(
            LoteBovino.id == obj_in.lote_id,
            LoteBovino.tenant_id == self.tenant_id,
        )
        lote = (await db.execute(stmt_lote)).scalars().first()
        if not lote:
            raise EntityNotFoundError(f"Lote {obj_in.lote_id} não encontrado neste tenant.")

        obj_data = obj_in.model_dump()
        if obj_data.get("data_evento") is None:
            obj_data["data_evento"] = date.today()

        db_manejo = ManejoLote(**obj_data, tenant_id=self.tenant_id)
        db.add(db_manejo)
        await db.flush()
        await self._atualizar_saldo_por_lote(db, lote, db_manejo)
        await db.refresh(db_manejo)

        # ── Integração Financeira ─────────────────────────────────────────
        tipo = obj_in.tipo_evento
        data_ev = db_manejo.data_evento

        if tipo in TIPOS_DESPESA and (obj_in.custo_total or 0) > 0:
            # Compatibilidade legada. Não usar este atalho como fonte canônica
            # de custo operacional em novos fluxos; preferir CostAllocation.
            from financeiro.models.despesa import Despesa
            from financeiro.models.plano_conta import PlanoConta
            stmt_pc = (
                select(PlanoConta.id)
                .where(
                    PlanoConta.tenant_id == self.tenant_id,
                    PlanoConta.categoria_rfb == "CUSTEIO",
                    PlanoConta.natureza == "ANALITICA",
                    PlanoConta.ativo == True,
                )
                .limit(1)
            )
            plano_id = (await db.execute(stmt_pc)).scalar()
            if plano_id:
                despesa = Despesa(
                    id=uuid.uuid4(),
                    tenant_id=self.tenant_id,
                    unidade_produtiva_id=lote.unidade_produtiva_id,
                    plano_conta_id=plano_id,
                    descricao=f"Pecuária — {tipo.capitalize()} Lote {lote.identificacao}",
                    valor_total=float(obj_in.custo_total),
                    data_emissao=data_ev,
                    data_vencimento=data_ev,
                    data_pagamento=data_ev,
                    status="PAGO",
                )
                db.add(despesa)

        elif tipo in TIPOS_RECEITA and (obj_in.valor_venda or 0) > 0:
            # Compatibilidade legada. Não usar este atalho como fonte canônica
            # de receita em novos fluxos; preferir Receita com precedência oficial.
            from financeiro.models.receita import Receita
            from financeiro.models.plano_conta import PlanoConta
            stmt_pc = (
                select(PlanoConta.id)
                .where(
                    PlanoConta.tenant_id == self.tenant_id,
                    PlanoConta.categoria_rfb == "RECEITA_ATIVIDADE",
                    PlanoConta.natureza == "ANALITICA",
                    PlanoConta.ativo == True,
                )
                .limit(1)
            )
            plano_id = (await db.execute(stmt_pc)).scalar()
            if plano_id:
                receita = Receita(
                    id=uuid.uuid4(),
                    tenant_id=self.tenant_id,
                    unidade_produtiva_id=lote.unidade_produtiva_id,
                    plano_conta_id=plano_id,
                    descricao=f"Pecuária — {tipo.capitalize()} Lote {lote.identificacao}",
                    valor_total=float(obj_in.valor_venda),
                    data_emissao=data_ev,
                    data_vencimento=data_ev,
                    data_recebimento=data_ev,
                    status="RECEBIDO",
                )
                db.add(receita)

        return db_manejo

    async def _contar_animais_individuais(
        self, db: AsyncSession, lote_id: uuid.UUID
    ) -> int:
        """Conta animais individuais ativos para evitar sobrescrever saldo agregado."""
        stmt = select(func.count(Animal.id)).where(
            Animal.tenant_id == self.tenant_id,
            Animal.lote_id == lote_id,
            Animal.status == "ATIVO",
        )
        return int((await db.execute(stmt)).scalar_one() or 0)

    @staticmethod
    def _atualizar_peso_por_lote(lote: LoteBovino, db_manejo: ManejoLote) -> None:
        """Atualiza o peso médio coletivo do lote após pesagem em massa."""
        peso_total = float(db_manejo.peso_total_kg or 0.0)
        if peso_total <= 0:
            return
        divisor = int(db_manejo.quantidade_cabecas or lote.quantidade_cabecas or 0)
        if divisor <= 0:
            return
        peso_medio = round(peso_total / divisor, 2)
        lote.peso_medio_kg = peso_medio
        if lote.peso_inicial_medio_kg is None:
            lote.peso_inicial_medio_kg = peso_medio

    async def _atualizar_saldo_por_lote(
        self, db: AsyncSession, lote: LoteBovino, db_manejo: ManejoLote
    ) -> None:
        """Atualiza cabeças, aquisição e peso de lotes em modo POR_LOTE.

        Args:
            db: Sessão assíncrona ativa.
            lote: Lote alvo do manejo.
            db_manejo: Evento de manejo recém-persistido.

        Raises:
            BusinessRuleError: Se a baixa deixar saldo negativo no lote.
        """
        if lote.modo_gestao != "POR_LOTE":
            return
        if await self._contar_animais_individuais(db, lote.id) > 0:
            return

        tipo = db_manejo.tipo_evento
        qtd = int(db_manejo.quantidade_cabecas or 0)
        if tipo in ("NASCIMENTO", "COMPRA") and qtd > 0:
            lote.quantidade_cabecas = int(lote.quantidade_cabecas or 0) + qtd
            if tipo == "COMPRA" and (db_manejo.custo_total or 0) > 0:
                lote.valor_aquisicao_total = float(lote.valor_aquisicao_total or 0.0) + float(db_manejo.custo_total)
        elif tipo in ("MORTE", "VENDA", "ABATE") and qtd > 0:
            atual = int(lote.quantidade_cabecas or 0)
            if qtd > atual:
                raise BusinessRuleError(
                    f"Saldo insuficiente de cabeças no lote ({atual} disponíveis para baixa de {qtd})."
                )
            lote.quantidade_cabecas = atual - qtd
        elif tipo == "PESAGEM":
            self._atualizar_peso_por_lote(lote, db_manejo)
