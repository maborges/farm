import uuid as _uuid
from uuid import UUID
from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select as _select_func
from sqlalchemy.future import select
from sqlalchemy import func, and_
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from core.base_service import BaseService
from rh.models import (
    Departamento, EsocialEvento, ColaboradorRH, LancamentoDiaria, Empreitada,
    ItemSegurancaRH, EntregaSegurancaRH, DocumentoSST
)
from rh.schemas import (
    DepartamentoCreate, DepartamentoUpdate, EsocialEventoCreate, EsocialEventoUpdate,
    ColaboradorCreate, DiariaCreate, EmpreitadaCreate,
    ItemSegurancaCreate, EntregaSegurancaCreate, DocumentoSSTCreate,
)


class EsocialEventoService(BaseService[EsocialEvento]):
    def __init__(self, session: AsyncSession, tenant_id: UUID):
        super().__init__(EsocialEvento, session, tenant_id)

    async def criar(self, dados: EsocialEventoCreate) -> EsocialEvento:
        return await self.create(dados.model_dump())

    async def atualizar(self, evento_id: UUID, dados: EsocialEventoUpdate) -> EsocialEvento:
        ev = await self.get_or_fail(evento_id)
        for k, v in dados.model_dump(exclude_none=True).items():
            setattr(ev, k, v)
        self.session.add(ev)
        return ev

    async def listar_filtrado(
        self,
        tipo_evento: str | None = None,
        status: str | None = None,
        periodo: str | None = None,
    ) -> list[EsocialEvento]:
        from sqlalchemy.future import select
        stmt = (
            select(EsocialEvento)
            .where(EsocialEvento.tenant_id == self.tenant_id)
            .order_by(EsocialEvento.created_at.desc())
        )
        if tipo_evento:
            stmt = stmt.where(EsocialEvento.tipo_evento == tipo_evento)
        if status:
            stmt = stmt.where(EsocialEvento.status == status)
        if periodo:
            stmt = stmt.where(EsocialEvento.periodo_apuracao == periodo)
        return list((await self.session.execute(stmt)).scalars().all())


class DepartamentoService(BaseService[Departamento]):
    def __init__(self, session: AsyncSession, tenant_id: UUID):
        super().__init__(Departamento, session, tenant_id)

    async def criar(self, dados: DepartamentoCreate) -> Departamento:
        return await self.create(dados.model_dump())

    async def atualizar(self, departamento_id: UUID, dados: DepartamentoUpdate) -> Departamento:
        dep = await self.get_or_fail(departamento_id)
        for k, v in dados.model_dump(exclude_none=True).items():
            setattr(dep, k, v)
        self.session.add(dep)
        return dep

    async def listar_com_contagem(self) -> list[dict]:
        from sqlalchemy import func
        stmt = (
            _select_func(Departamento, func.count(ColaboradorRH.id).label("total_colaboradores"))
            .outerjoin(
                ColaboradorRH,
                (ColaboradorRH.departamento_id == Departamento.id) & (ColaboradorRH.ativo == True)
            )
            .where(Departamento.tenant_id == self.tenant_id)
            .group_by(Departamento.id)
            .order_by(Departamento.nome)
        )
        rows = (await self.session.execute(stmt)).all()
        result = []
        for dep, total in rows:
            d = dep.__dict__.copy()
            d["total_colaboradores"] = total
            result.append(d)
        return result


class ColaboradorService(BaseService[ColaboradorRH]):
    def __init__(self, session: AsyncSession, tenant_id: UUID):
        super().__init__(ColaboradorRH, session, tenant_id)

    async def criar(self, dados: ColaboradorCreate) -> ColaboradorRH:
        return await self.create(dados.model_dump())

    async def desativar(self, colaborador_id: UUID) -> ColaboradorRH:
        col = await self.get_or_fail(colaborador_id)
        col.ativo = False
        self.session.add(col)
        await self.session.commit()
        await self.session.refresh(col)
        return col


class DiariaService(BaseService[LancamentoDiaria]):
    def __init__(self, session: AsyncSession, tenant_id: UUID):
        super().__init__(LancamentoDiaria, session, tenant_id)

    async def criar(self, dados: DiariaCreate) -> LancamentoDiaria:
        return await self.create(dados.model_dump())

    async def listar_filtrado(
        self,
        colaborador_id: UUID | None = None,
        status: str | None = None,
        data_inicio: date | None = None,
        data_fim: date | None = None,
    ) -> list[LancamentoDiaria]:
        stmt = (
            select(LancamentoDiaria)
            .where(LancamentoDiaria.tenant_id == self.tenant_id)
        )
        if colaborador_id:
            stmt = stmt.where(LancamentoDiaria.colaborador_id == colaborador_id)
        if status:
            stmt = stmt.where(LancamentoDiaria.status == status)
        if data_inicio:
            stmt = stmt.where(LancamentoDiaria.data >= data_inicio)
        if data_fim:
            stmt = stmt.where(LancamentoDiaria.data <= data_fim)
        stmt = stmt.order_by(LancamentoDiaria.data.desc())
        return list((await self.session.execute(stmt)).scalars().all())

    async def pagar_lote(self, ids: list[UUID], data_pagamento: date | None = None) -> int:
        from sqlalchemy import update
        dp = data_pagamento or date.today()

        # Busca diarias + unidade_produtiva_id antes do update para integração financeira
        stmt_fetch = (
            select(LancamentoDiaria, ColaboradorRH.unidade_produtiva_id)
            .join(ColaboradorRH, LancamentoDiaria.colaborador_id == ColaboradorRH.id)
            .where(
                LancamentoDiaria.tenant_id == self.tenant_id,
                LancamentoDiaria.id.in_(ids),
                LancamentoDiaria.status == "PENDENTE",
            )
        )
        rows = list((await self.session.execute(stmt_fetch)).all())

        # Agrupa total por unidade_produtiva_id
        por_fazenda: dict[UUID | None, float] = defaultdict(float)
        for diaria, unidade_produtiva_id in rows:
            por_fazenda[unidade_produtiva_id] += float(diaria.valor_diaria or 0)

        # Cria Despesas por fazenda
        if rows:
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
            plano_id = (await self.session.execute(stmt_pc)).scalar()
            if plano_id:
                for unidade_produtiva_id, total in por_fazenda.items():
                    if unidade_produtiva_id and total > 0:
                        self.session.add(Despesa(
                            id=_uuid.uuid4(),
                            tenant_id=self.tenant_id,
                            unidade_produtiva_id=unidade_produtiva_id,
                            plano_conta_id=plano_id,
                            descricao=f"RH — Pagamento de Diárias ({len(ids)} lançamentos)",
                            valor_total=round(total, 2),
                            data_emissao=dp,
                            data_vencimento=dp,
                            data_pagamento=dp,
                            status="PAGO",
                        ))

        stmt = (
            update(LancamentoDiaria)
            .where(
                LancamentoDiaria.tenant_id == self.tenant_id,
                LancamentoDiaria.id.in_(ids),
                LancamentoDiaria.status == "PENDENTE",
            )
            .values(status="PAGO", data_pagamento=dp)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount

    async def listar_por_colaborador(self, colaborador_id: UUID) -> list[LancamentoDiaria]:
        stmt = (
            select(LancamentoDiaria)
            .where(
                LancamentoDiaria.tenant_id == self.tenant_id,
                LancamentoDiaria.colaborador_id == colaborador_id,
            )
            .order_by(LancamentoDiaria.data.desc())
        )
        return list((await self.session.execute(stmt)).scalars().all())


class EmpreitadaService(BaseService[Empreitada]):
    def __init__(self, session: AsyncSession, tenant_id: UUID):
        super().__init__(Empreitada, session, tenant_id)

    async def listar_filtrado(
        self,
        colaborador_id: UUID | None = None,
        status_filter: str | None = None,
    ) -> list[Empreitada]:
        stmt = (
            select(Empreitada)
            .where(Empreitada.tenant_id == self.tenant_id)
        )
        if colaborador_id:
            stmt = stmt.where(Empreitada.colaborador_id == colaborador_id)
        if status_filter:
            stmt = stmt.where(Empreitada.status == status_filter)
        stmt = stmt.order_by(Empreitada.data_inicio.desc())
        return list((await self.session.execute(stmt)).scalars().all())

    async def criar(self, dados: EmpreitadaCreate) -> Empreitada:
        d = dados.model_dump()
        d["valor_total"] = round(dados.quantidade * dados.valor_unitario, 2)
        return await self.create(d)

    async def concluir(self, empreitada_id: UUID, quantidade_final: float | None, data_fim: date | None) -> Empreitada:
        emp = await self.get_or_fail(empreitada_id)
        if quantidade_final is not None:
            emp.quantidade = quantidade_final
            emp.valor_total = round(quantidade_final * float(emp.valor_unitario), 2)
        emp.data_fim = data_fim or date.today()
        emp.status = "CONCLUIDA"
        self.session.add(emp)
        await self.session.commit()
        await self.session.refresh(emp)
        return emp

    async def pagar(self, empreitada_id: UUID, data_pagamento: date | None = None) -> Empreitada:
        emp = await self.get_or_fail(empreitada_id)
        emp.status = "PAGA"
        emp.data_pagamento = data_pagamento or date.today()
        dp = emp.data_pagamento
        self.session.add(emp)

        # Integração Financeira: Despesa de Empreitada
        stmt_faz = select(ColaboradorRH.unidade_produtiva_id).where(ColaboradorRH.id == emp.colaborador_id)
        unidade_produtiva_id = (await self.session.execute(stmt_faz)).scalar()
        if unidade_produtiva_id and emp.valor_total and float(emp.valor_total) > 0:
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
            plano_id = (await self.session.execute(stmt_pc)).scalar()
            if plano_id:
                self.session.add(Despesa(
                    id=_uuid.uuid4(),
                    tenant_id=self.tenant_id,
                    unidade_produtiva_id=unidade_produtiva_id,
                    plano_conta_id=plano_id,
                    descricao=f"RH — Empreitada: {emp.descricao}",
                    valor_total=round(float(emp.valor_total), 2),
                    data_emissao=dp,
                    data_vencimento=dp,
                    data_pagamento=dp,
                    status="PAGO",
                ))

        await self.session.commit()
        await self.session.refresh(emp)
        return emp


async def get_dashboard_rh(session: AsyncSession, tenant_id: UUID) -> dict:
    hoje = date.today()
    mes_inicio = date(hoje.year, hoje.month, 1)

    # Colaboradores
    stmt_col = select(
        func.count(ColaboradorRH.id).label("total"),
        func.sum(func.cast(ColaboradorRH.tipo_contrato == "DIARISTA", type_=None)).label("diaristas"),
        func.sum(func.cast(ColaboradorRH.tipo_contrato == "EMPREITEIRO", type_=None)).label("empreiteiros"),
    ).where(ColaboradorRH.tenant_id == tenant_id, ColaboradorRH.ativo == True)
    r_col = (await session.execute(stmt_col)).one()

    # Diárias do mês
    stmt_dia_mes = select(func.sum(LancamentoDiaria.valor_diaria)).where(
        LancamentoDiaria.tenant_id == tenant_id,
        LancamentoDiaria.data >= mes_inicio,
    )
    gasto_diarias = (await session.execute(stmt_dia_mes)).scalar() or 0.0

    # Diárias pendentes (total)
    stmt_dia_pend = select(func.sum(LancamentoDiaria.valor_diaria)).where(
        LancamentoDiaria.tenant_id == tenant_id,
        LancamentoDiaria.status == "PENDENTE",
    )
    pendente_diarias = (await session.execute(stmt_dia_pend)).scalar() or 0.0

    # Empreitadas do mês
    stmt_emp_mes = select(func.sum(Empreitada.valor_total)).where(
        Empreitada.tenant_id == tenant_id,
        Empreitada.data_inicio >= mes_inicio,
    )
    gasto_emp = (await session.execute(stmt_emp_mes)).scalar() or 0.0

    # Empreitadas abertas
    stmt_emp_ab = select(
        func.count(Empreitada.id),
        func.sum(Empreitada.valor_total),
    ).where(
        Empreitada.tenant_id == tenant_id,
        Empreitada.status.in_(["ABERTA", "CONCLUIDA"]),
    )
    r_emp = (await session.execute(stmt_emp_ab)).one()

    return {
        "total_colaboradores_ativos": r_col.total or 0,
        "total_diaristas": int(r_col.diaristas or 0),
        "total_empreiteiros": int(r_col.empreiteiros or 0),
        "gasto_diarias_mes": float(gasto_diarias),
        "gasto_empreitadas_mes": float(gasto_emp),
        "total_pendente_diarias": float(pendente_diarias),
        "total_pendente_empreitadas": float(r_emp[1] or 0),
        "empreitadas_abertas": int(r_emp[0] or 0),
    }


class SegurancaTrabalhoService:
    def __init__(self, session: AsyncSession, tenant_id: UUID):
        self.session = session
        self.tenant_id = tenant_id

    async def _get_colaborador(self, colaborador_id: UUID) -> ColaboradorRH | None:
        stmt = select(ColaboradorRH).where(
            ColaboradorRH.id == colaborador_id,
            ColaboradorRH.tenant_id == self.tenant_id,
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def _get_item(self, item_id: UUID) -> ItemSegurancaRH | None:
        stmt = select(ItemSegurancaRH).where(
            ItemSegurancaRH.id == item_id,
            ItemSegurancaRH.tenant_id == self.tenant_id,
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def listar_itens(self) -> list[ItemSegurancaRH]:
        stmt = (
            select(ItemSegurancaRH)
            .where(ItemSegurancaRH.tenant_id == self.tenant_id)
            .order_by(ItemSegurancaRH.tipo, ItemSegurancaRH.nome)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def criar_item(self, dados: ItemSegurancaCreate) -> ItemSegurancaRH:
        item = ItemSegurancaRH(tenant_id=self.tenant_id, **dados.model_dump())
        self.session.add(item)
        return item

    async def listar_entregas(
        self,
        colaborador_id: UUID | None = None,
        item_id: UUID | None = None,
    ) -> list[EntregaSegurancaRH]:
        stmt = select(EntregaSegurancaRH).where(EntregaSegurancaRH.tenant_id == self.tenant_id)
        if colaborador_id:
            stmt = stmt.where(EntregaSegurancaRH.colaborador_id == colaborador_id)
        if item_id:
            stmt = stmt.where(EntregaSegurancaRH.item_id == item_id)
        stmt = stmt.order_by(EntregaSegurancaRH.data_entrega.desc(), EntregaSegurancaRH.created_at.desc())
        return list((await self.session.execute(stmt)).scalars().all())

    async def registrar_entrega(self, dados: EntregaSegurancaCreate) -> EntregaSegurancaRH:
        colaborador = await self._get_colaborador(dados.colaborador_id)
        if not colaborador:
            raise ValueError("Colaborador não encontrado")

        item = await self._get_item(dados.item_id)
        if not item:
            raise ValueError("Item de segurança não encontrado")

        data_validade = dados.data_validade
        if data_validade is None and item.validade_dias:
            data_validade = dados.data_entrega + timedelta(days=item.validade_dias)

        entrega = EntregaSegurancaRH(
            tenant_id=self.tenant_id,
            colaborador_id=dados.colaborador_id,
            item_id=dados.item_id,
            unidade_produtiva_id=dados.unidade_produtiva_id or colaborador.unidade_produtiva_id,
            data_entrega=dados.data_entrega,
            data_validade=data_validade,
            quantidade=dados.quantidade,
            termo_assinado_url=dados.termo_assinado_url,
            observacoes=dados.observacoes,
            dados_extras={
                "tipo_item": item.tipo,
                "ca_numero": item.ca_numero,
            },
        )
        self.session.add(entrega)
        return entrega

    async def listar_documentos(self) -> list[DocumentoSST]:
        stmt = (
            select(DocumentoSST)
            .where(DocumentoSST.tenant_id == self.tenant_id)
            .order_by(DocumentoSST.data_vencimento.is_(None), DocumentoSST.data_vencimento.asc(), DocumentoSST.data_emissao.desc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def registrar_documento(self, dados: DocumentoSSTCreate) -> DocumentoSST:
        if dados.colaborador_id:
            colaborador = await self._get_colaborador(dados.colaborador_id)
            if not colaborador:
                raise ValueError("Colaborador não encontrado")

        doc = DocumentoSST(tenant_id=self.tenant_id, **dados.model_dump())
        self.session.add(doc)
        return doc

    async def get_resumo(self) -> dict:
        hoje = date.today()
        itens = await self.listar_itens()
        entregas = await self.listar_entregas()
        docs = await self.listar_documentos()

        documentos_vencendo_30d = sum(
            1 for doc in docs
            if doc.data_vencimento and hoje <= doc.data_vencimento <= (hoje + timedelta(days=30))
        )
        documentos_vencidos = sum(
            1 for doc in docs
            if doc.data_vencimento and doc.data_vencimento < hoje and doc.status == "ATIVO"
        )

        return {
            "total_itens_ativos": sum(1 for item in itens if item.ativo),
            "total_entregas_ativas": sum(1 for entrega in entregas if entrega.status == "ATIVA"),
            "total_documentos_ativos": sum(1 for doc in docs if doc.status == "ATIVO"),
            "documentos_vencendo_30d": documentos_vencendo_30d,
            "documentos_vencidos": documentos_vencidos,
        }

    async def gerar_pdf_nr31(self) -> bytes:
        resumo = await self.get_resumo()
        itens = await self.listar_itens()
        entregas = await self.listar_entregas()
        docs = await self.listar_documentos()

        import io

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=1.4 * cm,
            leftMargin=1.4 * cm,
            topMargin=1.4 * cm,
            bottomMargin=1.4 * cm,
        )
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name="RHTitle", parent=styles["Title"], fontSize=16, leading=20, textColor=colors.HexColor("#c2410c")))
        styles.add(ParagraphStyle(name="RHBody", parent=styles["BodyText"], fontSize=9, leading=12))

        story = [
            Paragraph("Relatório NR-31 - Segurança do Trabalho", styles["RHTitle"]),
            Spacer(1, 0.2 * cm),
            Paragraph(f"Itens ativos: {resumo['total_itens_ativos']}", styles["RHBody"]),
            Paragraph(f"Entregas ativas: {resumo['total_entregas_ativas']}", styles["RHBody"]),
            Paragraph(f"Documentos ativos: {resumo['total_documentos_ativos']}", styles["RHBody"]),
            Paragraph(f"Documentos vencendo em 30 dias: {resumo['documentos_vencendo_30d']}", styles["RHBody"]),
            Paragraph(f"Documentos vencidos: {resumo['documentos_vencidos']}", styles["RHBody"]),
            Spacer(1, 0.3 * cm),
        ]

        def add_table(title: str, rows: list[list[str]]):
            story.append(Paragraph(title, styles["Heading2"]))
            table = Table(rows, repeatRows=1)
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#c2410c")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#fdba74")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fff7ed")]),
            ]))
            story.append(table)
            story.append(Spacer(1, 0.25 * cm))

        if itens:
            add_table(
                "Itens de segurança",
                [["Nome", "Tipo", "CA", "Validade (dias)"]] + [
                    [item.nome, item.tipo, item.ca_numero or "-", str(item.validade_dias or "-")] for item in itens
                ],
            )
        if entregas:
            add_table(
                "Entregas",
                [["Data", "Colaborador", "Item", "Validade"]] + [
                    [
                        entrega.data_entrega.strftime("%d/%m/%Y"),
                        str(entrega.colaborador_id),
                        str(entrega.item_id),
                        entrega.data_validade.strftime("%d/%m/%Y") if entrega.data_validade else "-",
                    ]
                    for entrega in entregas
                ],
            )
        if docs:
            add_table(
                "Documentos SST",
                [["Tipo", "Emissão", "Vencimento", "Status"]] + [
                    [
                        doc_item.tipo,
                        doc_item.data_emissao.strftime("%d/%m/%Y"),
                        doc_item.data_vencimento.strftime("%d/%m/%Y") if doc_item.data_vencimento else "-",
                        doc_item.status,
                    ]
                    for doc_item in docs
                ],
            )

        doc.build(story)
        return buffer.getvalue()
