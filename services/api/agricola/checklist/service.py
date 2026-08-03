from uuid import UUID
from datetime import date, datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, or_
from core.base_service import BaseService
from core.exceptions import BusinessRuleError
from agricola.checklist.models import SafraChecklistItem
from agricola.models.templates import PhaseTemplate, PhaseTemplateChecklistItem
from agricola.checklist.schemas import (
    ChecklistTemplateCreate, ChecklistTemplateUpdate,
    ChecklistItemAdicionar, ChecklistFaseStatus,
)

# Itens obrigatórios não cancelados sem veredito próprio ainda (nunca avaliados
# e não concluídos manualmente) contam como bloqueantes — ver _status_efetivo.
_STATUS_TERMINAIS = ("OK", "OK_PARCIAL", "BLOQUEANTE")


class ChecklistTemplateService(BaseService[PhaseTemplateChecklistItem]):
    def __init__(self, session: AsyncSession, tenant_id: UUID):
        super().__init__(PhaseTemplateChecklistItem, session, tenant_id)

    async def listar(self, cultura: str | None = None, fase: str | None = None):
        stmt = select(
            PhaseTemplateChecklistItem.id,
            PhaseTemplate.tenant_id,
            PhaseTemplate.cultura,
            PhaseTemplate.fase,
            PhaseTemplateChecklistItem.titulo,
            PhaseTemplateChecklistItem.descricao,
            PhaseTemplateChecklistItem.obrigatorio,
            PhaseTemplateChecklistItem.ordem,
            PhaseTemplateChecklistItem.ativo,
            PhaseTemplate.is_system_default.label("is_system"),
            PhaseTemplate.created_at,
            PhaseTemplateChecklistItem.tipo_resultado,
            PhaseTemplateChecklistItem.produto_id_padrao,
            PhaseTemplateChecklistItem.quantidade_minima,
        ).join(PhaseTemplate).where(
            or_(PhaseTemplate.tenant_id == self.tenant_id, PhaseTemplate.tenant_id == None),
            PhaseTemplateChecklistItem.ativo == True
        )
        if cultura:
            stmt = stmt.where(or_(PhaseTemplate.cultura == cultura, PhaseTemplate.cultura == None))
        if fase:
            stmt = stmt.where(PhaseTemplate.fase == fase)
        
        result = await self.session.execute(stmt.order_by(PhaseTemplate.fase, PhaseTemplateChecklistItem.ordem))
        return [dict(r._mapping) for r in result.all()]

    async def criar(self, dados: ChecklistTemplateCreate) -> PhaseTemplateChecklistItem:
        # Nota: A criação direta aqui ficou mais complexa pois precisa de um PhaseTemplate container.
        # Por simplicidade, vamos buscar ou criar um PhaseTemplate para o tenant/cultura/fase.
        stmt = select(PhaseTemplate).where(
            PhaseTemplate.tenant_id == self.tenant_id,
            PhaseTemplate.cultura == dados.cultura,
            PhaseTemplate.fase == dados.fase
        )
        container = (await self.session.execute(stmt)).scalar_one_or_none()
        
        if not container:
            container = PhaseTemplate(
                tenant_id=self.tenant_id,
                cultura=dados.cultura,
                fase=dados.fase,
                titulo=f"Template {dados.fase}" + (f" - {dados.cultura}" if dados.cultura else ""),
                ativo=True
            )
            self.session.add(container)
            await self.session.flush()

        item = PhaseTemplateChecklistItem(
            phase_template_id=container.id,
            titulo=dados.titulo,
            descricao=dados.descricao,
            obrigatorio=dados.obrigatorio,
            ordem=dados.ordem,
            ativo=True,
            tipo_resultado=dados.tipo_resultado,
            produto_id_padrao=dados.produto_id_padrao,
            quantidade_minima=dados.quantidade_minima,
        )
        self.session.add(item)
        await self.session.flush()
        return item

    async def atualizar(self, item_id: UUID, dados: ChecklistTemplateUpdate) -> PhaseTemplateChecklistItem:
        return await self.update(item_id, dados.model_dump(exclude_unset=True))


class SafraChecklistService(BaseService[SafraChecklistItem]):
    def __init__(self, session: AsyncSession, tenant_id: UUID):
        super().__init__(SafraChecklistItem, session, tenant_id)

    async def gerar_para_fase(
        self, safra_id: UUID, cultura: str, fase: str,
        deposito_id: UUID | None = None, usuario_id: UUID | None = None,
    ) -> list[SafraChecklistItem]:
        """Copia os templates ativos da cultura+fase para a safra (idempotente).

        Itens SOLICITACAO_ESTOQUE são avaliados na hora se `deposito_id` for
        informado (saldo suficiente -> reserva automática; senão, fica
        BLOQUEANTE até avaliação manual/override). Itens TAREFA_CAMPO ficam
        PENDENTE até alguém vincular uma OS via `vincular_operacao` — este
        método não infere talhão sozinho.
        """
        # Verifica se já foram gerados
        stmt_existentes = select(SafraChecklistItem).where(
            SafraChecklistItem.safra_id == safra_id,
            SafraChecklistItem.tenant_id == self.tenant_id,
            SafraChecklistItem.fase == fase,
        )
        existentes = (await self.session.execute(stmt_existentes)).scalars().all()
        if existentes:
            return list(existentes)

        # Busca templates: específicos da cultura + genéricos (cultura=None)
        stmt_tmpl = select(PhaseTemplateChecklistItem).join(PhaseTemplate).where(
            or_(PhaseTemplate.tenant_id == self.tenant_id, PhaseTemplate.tenant_id == None),
            PhaseTemplate.fase == fase,
            PhaseTemplate.ativo == True,
            PhaseTemplateChecklistItem.ativo == True,
            or_(PhaseTemplate.cultura == cultura, PhaseTemplate.cultura == None),
        ).order_by(PhaseTemplateChecklistItem.ordem)
        templates = (await self.session.execute(stmt_tmpl)).scalars().all()

        itens: list[SafraChecklistItem] = []
        for tmpl in templates:
            item = SafraChecklistItem(
                safra_id=safra_id,
                tenant_id=self.tenant_id,
                template_id=tmpl.id,
                fase=fase,
                titulo=tmpl.titulo,
                descricao=tmpl.descricao,
                obrigatorio=tmpl.obrigatorio,
                ordem=tmpl.ordem,
                tipo_resultado=tmpl.tipo_resultado,
            )
            self.session.add(item)
            itens.append(item)

        await self.session.flush()

        if deposito_id is not None:
            for item, tmpl in zip(itens, templates):
                if item.tipo_resultado == "SOLICITACAO_ESTOQUE" and tmpl.produto_id_padrao:
                    await self.avaliar_estoque_item(
                        item.id, deposito_id, tmpl.produto_id_padrao, tmpl.quantidade_minima or 0, usuario_id,
                    )

        return itens

    async def avaliar_estoque_item(
        self, item_id: UUID, deposito_id: UUID, produto_id: UUID, quantidade_minima: float, usuario_id: UUID | None,
    ) -> SafraChecklistItem:
        """Verifica saldo do produto configurado no template. Suficiente ->
        gera ReservaEstoque e marca OK. Insuficiente -> BLOQUEANTE (usuário
        pode dar override manual via `override_manual`)."""
        item = await self.get_or_fail(item_id)
        if item.tipo_resultado != "SOLICITACAO_ESTOQUE":
            raise BusinessRuleError("Item não é do tipo SOLICITACAO_ESTOQUE.")

        from operacional.services.estoque_service import EstoqueService
        from operacional.schemas.estoque import ReservaCreate

        est_svc = EstoqueService(self.session, self.tenant_id)
        try:
            reserva = await est_svc.criar_reserva(
                ReservaCreate(
                    produto_id=produto_id,
                    deposito_id=deposito_id,
                    quantidade=quantidade_minima,
                    motivo=f"Checklist de fase: {item.titulo}",
                    referencia_tipo="SAFRA_CHECKLIST",
                    referencia_id=item.id,
                ),
                usuario_id,
            )
            item.reserva_estoque_id = reserva.id
            item.status_verificacao = "OK"
        except BusinessRuleError:
            item.status_verificacao = "BLOQUEANTE"

        await self.session.flush()
        return item

    async def assumir_item(self, item_id: UUID, usuario_id: UUID) -> SafraChecklistItem:
        """Atribui o item (sem responsável) ao usuário que está assumindo."""
        item = await self.get_or_fail(item_id)
        if item.tipo_resultado == "TAREFA_CAMPO":
            raise BusinessRuleError("Itens TAREFA_CAMPO já têm responsável via a OS/tarefa de campo gerada.")
        if item.responsavel_id is not None:
            raise BusinessRuleError("Item já tem responsável atribuído.")
        item.responsavel_id = usuario_id
        await self.session.flush()
        return item

    async def atribuir_item(self, item_id: UUID, responsavel_id: UUID, prazo_resposta: date | None) -> SafraChecklistItem:
        """Atribuição explícita (gestor aponta alguém), diferente de `assumir_item`."""
        item = await self.get_or_fail(item_id)
        if item.tipo_resultado == "TAREFA_CAMPO":
            raise BusinessRuleError("Itens TAREFA_CAMPO já têm responsável via a OS/tarefa de campo gerada.")
        item.responsavel_id = responsavel_id
        item.prazo_resposta = prazo_resposta
        await self.session.flush()
        return item

    async def gerar_operacao(self, item_id: UUID, talhao_id: UUID, usuario_id: UUID | None) -> SafraChecklistItem:
        """Gera uma OS (`OperacaoAgricola`, status PLANEJADA) a partir de um item
        TAREFA_CAMPO do checklist e já vincula ao item. O talhão é sempre
        escolhido pelo usuário no momento da geração — a safra pode ter mais
        de um talhão e não há regra automática de escolha (ver
        docs/brainstorm-checklist-fase-processo.md, seção 8.4)."""
        item = await self.get_or_fail(item_id)
        if item.tipo_resultado != "TAREFA_CAMPO":
            raise BusinessRuleError("Item não é do tipo TAREFA_CAMPO.")
        if item.operacao_agricola_id is not None:
            raise BusinessRuleError("Item já tem uma OS vinculada.")

        from core.cadastros.propriedades.models import AreaRural
        from agricola.operacoes.models import OperacaoAgricola
        from agricola.operacoes.service import OperacaoService
        from agricola.operacoes.schemas import OperacaoAgricolaCreate

        talhao = await self.session.get(AreaRural, talhao_id)
        if not talhao or talhao.tenant_id != self.tenant_id:
            raise BusinessRuleError(f"Talhão {talhao_id} não encontrado.")

        hoje = date.today()
        op_create = OperacaoAgricolaCreate(
            safra_id=item.safra_id,
            talhao_id=talhao_id,
            tipo="OUTROS",
            descricao=item.titulo,
            data_prevista=hoje,
            data_realizada=hoje,
            area_aplicada_ha=float(talhao.area_hectares) if talhao.area_hectares else 1.0,
            status="PLANEJADA",
        )
        op_svc = OperacaoService(self.session, self.tenant_id)
        operacao = await op_svc.criar(op_create)

        item.operacao_agricola_id = operacao.id
        await self.session.flush()
        return item

    async def vincular_operacao(self, item_id: UUID, operacao_agricola_id: UUID) -> SafraChecklistItem:
        """Liga uma OS (criada pelo fluxo normal de Plano Operacional) a um
        item TAREFA_CAMPO do checklist."""
        item = await self.get_or_fail(item_id)
        if item.tipo_resultado != "TAREFA_CAMPO":
            raise BusinessRuleError("Item não é do tipo TAREFA_CAMPO.")
        item.operacao_agricola_id = operacao_agricola_id
        await self.session.flush()
        return item

    async def override_manual(
        self, item_id: UUID, status_verificacao: str, justificativa: str, usuario_id: UUID | None,
    ) -> SafraChecklistItem:
        """Override manual do veredito — ex.: saldo ainda insuficiente mas o
        pedido de compra já foi providenciado."""
        item = await self.get_or_fail(item_id)
        item.status_verificacao = status_verificacao
        item.justificativa_ok_parcial = justificativa
        if status_verificacao == "OK":
            item.concluido = True
            item.usuario_id = usuario_id
            item.concluido_em = datetime.utcnow()
        await self.session.flush()
        return item

    async def listar_por_fase(self, safra_id: UUID, fase: str) -> list[SafraChecklistItem]:
        stmt = select(SafraChecklistItem).where(
            SafraChecklistItem.safra_id == safra_id,
            SafraChecklistItem.tenant_id == self.tenant_id,
            SafraChecklistItem.fase == fase,
        ).order_by(SafraChecklistItem.ordem)
        return list((await self.session.execute(stmt)).scalars().all())

    @staticmethod
    def _status_efetivo(item: SafraChecklistItem) -> str:
        """Veredito considerando o tipo do item: TAREFA_CAMPO olha o status
        da OS vinculada; os demais usam status_verificacao (avaliação
        automática ou override manual), com fallback pro booleano
        `concluido` legado."""
        if item.tipo_resultado == "TAREFA_CAMPO":
            return "PENDENTE" if item.operacao_agricola_id is None else "OK"
        if item.status_verificacao in _STATUS_TERMINAIS:
            return item.status_verificacao
        return "OK" if item.concluido else "PENDENTE"

    async def status_fase(self, safra_id: UUID, fase: str) -> ChecklistFaseStatus:
        itens = await self.listar_por_fase(safra_id, fase)
        total = len(itens)
        concluidos = sum(1 for i in itens if i.concluido)
        obrigatorios_nao_cancelados = [i for i in itens if i.obrigatorio and not i.cancelado]
        obrigatorios_pendentes = sum(
            1 for i in obrigatorios_nao_cancelados if self._status_efetivo(i) not in ("OK", "OK_PARCIAL")
        )

        vereditos = {self._status_efetivo(i) for i in obrigatorios_nao_cancelados}
        if "PENDENTE" in vereditos or "BLOQUEANTE" in vereditos:
            veredito = "BLOQUEANTE"
        elif "OK_PARCIAL" in vereditos:
            veredito = "OK_PARCIAL"
        else:
            veredito = "OK"

        return ChecklistFaseStatus(
            fase=fase,
            total=total,
            concluidos=concluidos,
            obrigatorios_pendentes=obrigatorios_pendentes,
            pode_avancar=veredito != "BLOQUEANTE",
            veredito=veredito,
            itens=itens,
        )

    async def marcar_item(self, item_id: UUID, concluido: bool | None, cancelado: bool | None, motivo: str | None, usuario_id: UUID | None) -> SafraChecklistItem:
        item = await self.get_or_fail(item_id)
        
        if concluido is not None:
            item.concluido = concluido
            item.usuario_id = usuario_id if concluido else None
            item.concluido_em = datetime.utcnow() if concluido else None
            item.status_verificacao = "OK" if concluido else "PENDENTE"
            if concluido:
                item.cancelado = False # Não pode ser ambos
        
        if cancelado is not None:
            item.cancelado = cancelado
            item.usuario_cancelamento_id = usuario_id if cancelado else None
            item.cancelado_em = datetime.utcnow() if cancelado else None
            item.motivo_cancelamento = motivo if cancelado else None
            if cancelado:
                item.concluido = False # Não pode ser ambos

        await self.session.flush()
        return item

    async def adicionar_item(self, safra_id: UUID, fase: str, dados: ChecklistItemAdicionar) -> SafraChecklistItem:
        item = SafraChecklistItem(
            safra_id=safra_id,
            tenant_id=self.tenant_id,
            fase=fase,
            **dados.model_dump(),
        )
        self.session.add(item)
        await self.session.flush()
        return item
