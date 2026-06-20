import uuid
from datetime import date, timedelta
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from core.base_service import BaseService
from core.exceptions import EntityNotFoundError
from .models import RegistroCAR, AlertaAmbiental, OutorgaHidrica, StatusCAR, StatusAlerta
from iot_integracao.new_holland.models import CarbonoEmissao, CarbonoProjeto, CarbonoRelatorio


class AmbientalService(BaseService[RegistroCAR]):
    def __init__(self, session: AsyncSession, tenant_id):
        super().__init__(RegistroCAR, session, tenant_id)

    # ── Dashboard ─────────────────────────────────────────────────────────────

    async def dashboard(self) -> dict:
        cars = list((await self.session.execute(
            select(RegistroCAR).where(RegistroCAR.tenant_id == self.tenant_id)
        )).scalars().all())
        alertas = list((await self.session.execute(
            select(AlertaAmbiental).where(AlertaAmbiental.tenant_id == self.tenant_id)
        )).scalars().all())
        outorgas = list((await self.session.execute(
            select(OutorgaHidrica).where(
                OutorgaHidrica.tenant_id == self.tenant_id,
                OutorgaHidrica.ativo == True,
            )
        )).scalars().all())
        hoje = date.today()
        prazo = hoje + timedelta(days=90)
        return {
            "total_cars": len(cars),
            "cars_ativos": sum(1 for c in cars if c.status == StatusCAR.ATIVO),
            "cars_pendentes": sum(1 for c in cars if c.status == StatusCAR.PENDENTE),
            "total_alertas_abertos": sum(1 for a in alertas if a.status in (StatusAlerta.NOVO, StatusAlerta.EM_ANALISE)),
            "alertas_criticos": sum(1 for a in alertas if a.severidade == "CRITICA" and a.status != StatusAlerta.RESOLVIDO),
            "total_outorgas": len(outorgas),
            "outorgas_vencendo": sum(1 for o in outorgas if o.data_vencimento and hoje <= o.data_vencimento <= prazo),
        }

    # ── CAR ───────────────────────────────────────────────────────────────────

    async def listar_cars(self, status_filter: Optional[str] = None) -> list[RegistroCAR]:
        stmt = select(RegistroCAR).where(RegistroCAR.tenant_id == self.tenant_id).order_by(RegistroCAR.created_at.desc())
        if status_filter:
            stmt = stmt.where(RegistroCAR.status == status_filter)
        return list((await self.session.execute(stmt)).scalars().all())

    async def criar_car(self, dados: dict) -> RegistroCAR:
        car = RegistroCAR(tenant_id=self.tenant_id, **dados)
        self.session.add(car)
        await self.session.flush()
        await self.session.refresh(car)
        return car

    async def _get_car(self, car_id: uuid.UUID) -> RegistroCAR:
        obj = (await self.session.execute(
            select(RegistroCAR).where(RegistroCAR.id == car_id, RegistroCAR.tenant_id == self.tenant_id)
        )).scalar_one_or_none()
        if not obj:
            raise EntityNotFoundError("CAR não encontrado.")
        return obj

    async def atualizar_car(self, car_id: uuid.UUID, dados: dict) -> RegistroCAR:
        car = await self._get_car(car_id)
        for k, v in dados.items():
            setattr(car, k, v)
        await self.session.flush()
        await self.session.refresh(car)
        return car

    async def excluir_car(self, car_id: uuid.UUID) -> None:
        car = await self._get_car(car_id)
        await self.session.delete(car)

    # ── Alertas ───────────────────────────────────────────────────────────────

    async def listar_alertas(
        self, status_filter: Optional[str] = None,
        severidade: Optional[str] = None, tipo: Optional[str] = None,
    ) -> list[AlertaAmbiental]:
        stmt = select(AlertaAmbiental).where(AlertaAmbiental.tenant_id == self.tenant_id).order_by(AlertaAmbiental.data_deteccao.desc())
        if status_filter:
            stmt = stmt.where(AlertaAmbiental.status == status_filter)
        if severidade:
            stmt = stmt.where(AlertaAmbiental.severidade == severidade)
        if tipo:
            stmt = stmt.where(AlertaAmbiental.tipo == tipo)
        return list((await self.session.execute(stmt)).scalars().all())

    async def criar_alerta(self, dados: dict) -> AlertaAmbiental:
        if "data_deteccao" not in dados:
            dados["data_deteccao"] = date.today()
        alerta = AlertaAmbiental(tenant_id=self.tenant_id, **dados)
        self.session.add(alerta)
        await self.session.flush()
        await self.session.refresh(alerta)
        return alerta

    async def atualizar_alerta(self, alerta_id: uuid.UUID, dados: dict) -> AlertaAmbiental:
        obj = (await self.session.execute(
            select(AlertaAmbiental).where(AlertaAmbiental.id == alerta_id, AlertaAmbiental.tenant_id == self.tenant_id)
        )).scalar_one_or_none()
        if not obj:
            raise EntityNotFoundError("Alerta não encontrado.")
        for k, v in dados.items():
            setattr(obj, k, v)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    # ── Outorgas ──────────────────────────────────────────────────────────────

    async def listar_outorgas(self, status_filter: Optional[str] = None) -> list[OutorgaHidrica]:
        stmt = (
            select(OutorgaHidrica)
            .where(OutorgaHidrica.tenant_id == self.tenant_id, OutorgaHidrica.ativo == True)
            .order_by(OutorgaHidrica.data_vencimento.asc())
        )
        if status_filter:
            stmt = stmt.where(OutorgaHidrica.status == status_filter)
        return list((await self.session.execute(stmt)).scalars().all())

    async def criar_outorga(self, dados: dict) -> OutorgaHidrica:
        outorga = OutorgaHidrica(tenant_id=self.tenant_id, **dados)
        self.session.add(outorga)
        await self.session.flush()
        await self.session.refresh(outorga)
        return outorga

    async def atualizar_outorga(self, outorga_id: uuid.UUID, dados: dict) -> OutorgaHidrica:
        obj = (await self.session.execute(
            select(OutorgaHidrica).where(OutorgaHidrica.id == outorga_id, OutorgaHidrica.tenant_id == self.tenant_id)
        )).scalar_one_or_none()
        if not obj:
            raise EntityNotFoundError("Outorga não encontrada.")
        for k, v in dados.items():
            setattr(obj, k, v)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    # ── Carbono / MRV ───────────────────────────────────────────────────────

    def _carbono(self) -> "CarbonoService":
        return CarbonoService(self.session, self.tenant_id)

    async def dashboard_carbono(self) -> dict:
        return await self._carbono().dashboard_carbono()

    async def listar_emissoes_carbono(self, escopo: int | None = None) -> list[CarbonoEmissao]:
        return await self._carbono().listar_emissoes_carbono(escopo=escopo)

    async def registrar_emissao_carbono(self, dados: dict) -> CarbonoEmissao:
        return await self._carbono().registrar_emissao_carbono(dados)

    async def listar_projetos_carbono(self, status_filter: str | None = None) -> list[CarbonoProjeto]:
        return await self._carbono().listar_projetos_carbono(status_filter=status_filter)

    async def criar_projeto_carbono(self, dados: dict) -> CarbonoProjeto:
        return await self._carbono().criar_projeto_carbono(dados)

    async def listar_relatorios_carbono(self) -> list[CarbonoRelatorio]:
        return await self._carbono().listar_relatorios_carbono()

    async def gerar_relatorio_carbono(self, periodo_inicio: date, periodo_fim: date) -> CarbonoRelatorio:
        return await self._carbono().gerar_relatorio_carbono(periodo_inicio, periodo_fim)

    async def exportar_pdf_carbono(self, relatorio_id: int) -> bytes:
        return await self._carbono().exportar_pdf_carbono(relatorio_id)


class CarbonoService:
    """Serviço async para gestão de carbono e MRV."""

    FACTORES_PADRAO = {
        "diesel": 2.68,
        "gasolina": 2.31,
        "energia_eletrica": 0.061,
        "gas_natural": 2.0,
    }

    def __init__(self, session: AsyncSession, tenant_id: str):
        self.session = session
        self.tenant_id = str(tenant_id)

    async def listar_emissoes(self, escopo: int | None = None) -> list[CarbonoEmissao]:
        stmt = select(CarbonoEmissao).where(CarbonoEmissao.tenant_id == self.tenant_id)
        if escopo is not None:
            stmt = stmt.where(CarbonoEmissao.escopo == escopo)
        stmt = stmt.order_by(CarbonoEmissao.data_referencia.desc(), CarbonoEmissao.created_at.desc())
        return list((await self.session.execute(stmt)).scalars().all())

    async def registrar_emissao(self, dados: dict) -> CarbonoEmissao:
        categoria = str(dados.get("categoria", "")).lower()
        fator = dados.get("fator_emissao")
        if fator is None:
            fator = self.FACTORES_PADRAO.get(categoria, 0)
        total_co2e = float(dados["quantidade"]) * float(fator)

        emissao = CarbonoEmissao(
            tenant_id=self.tenant_id,
            unidade_produtiva_id=dados.get("unidade_produtiva_id"),
            escopo=int(dados["escopo"]),
            categoria=dados["categoria"],
            fonte=dados.get("fonte"),
            atividade=dados.get("atividade"),
            quantidade=float(dados["quantidade"]),
            unidade=dados["unidade"],
            fator_emissao=float(fator),
            fator_emissao_referencia=dados.get("fator_emissao_referencia"),
            total_co2e=total_co2e,
            data_referencia=dados["data_referencia"],
            observacoes=dados.get("observacoes"),
            arquivo_comprovante=dados.get("arquivo_comprovante"),
            created_by=dados.get("created_by"),
        )
        self.session.add(emissao)
        await self.session.flush()
        await self.session.refresh(emissao)
        return emissao

    async def listar_projetos(self, status: str | None = None) -> list[CarbonoProjeto]:
        stmt = select(CarbonoProjeto).where(CarbonoProjeto.tenant_id == self.tenant_id)
        if status:
            stmt = stmt.where(CarbonoProjeto.status == status)
        stmt = stmt.order_by(CarbonoProjeto.created_at.desc())
        return list((await self.session.execute(stmt)).scalars().all())

    async def criar_projeto(self, dados: dict) -> CarbonoProjeto:
        projeto = CarbonoProjeto(tenant_id=self.tenant_id, **dados)
        self.session.add(projeto)
        await self.session.flush()
        await self.session.refresh(projeto)
        return projeto

    async def listar_relatorios(self) -> list[CarbonoRelatorio]:
        stmt = (
            select(CarbonoRelatorio)
            .where(CarbonoRelatorio.tenant_id == self.tenant_id)
            .order_by(CarbonoRelatorio.created_at.desc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def gerar_relatorio(self, periodo_inicio: date, periodo_fim: date) -> CarbonoRelatorio:
        emiss = list((await self.session.execute(
            select(CarbonoEmissao).where(
                CarbonoEmissao.tenant_id == self.tenant_id,
                func.date(CarbonoEmissao.data_referencia).between(periodo_inicio, periodo_fim),
            )
        )).scalars().all())
        escopo_1 = sum(float(e.total_co2e or 0) for e in emiss if e.escopo == 1)
        escopo_2 = sum(float(e.total_co2e or 0) for e in emiss if e.escopo == 2)
        escopo_3 = sum(float(e.total_co2e or 0) for e in emiss if e.escopo == 3)

        creditos_gerados = sum(float(p.creditos_verificados or 0) for p in await self.listar_projetos("certificado"))
        rel = CarbonoRelatorio(
            tenant_id=self.tenant_id,
            periodo_inicio=periodo_inicio,
            periodo_fim=periodo_fim,
            escopo_1_total=escopo_1,
            escopo_2_total=escopo_2,
            escopo_3_total=escopo_3,
            total_geral=escopo_1 + escopo_2 + escopo_3,
            creditos_gerados=creditos_gerados,
            saldo_liquido=(escopo_1 + escopo_2 + escopo_3) - creditos_gerados,
            status="rascunho",
        )
        self.session.add(rel)
        await self.session.flush()
        await self.session.refresh(rel)
        return rel

    async def dashboard(self) -> dict:
        emiss = await self.listar_emissoes()
        projetos = await self.listar_projetos()
        relatorios = await self.listar_relatorios()
        total_emissoes = sum(float(e.total_co2e or 0) for e in emiss)
        total_creditos = sum(float(p.creditos_verificados or 0) for p in projetos)
        return {
            "total_emissoes": total_emissoes,
            "total_creditos": total_creditos,
            "saldo_liquido": total_emissoes - total_creditos,
            "total_emissoes_registradas": len(emiss),
            "total_projetos": len(projetos),
            "total_relatorios": len(relatorios),
            "emissoes_escopo_1": sum(float(e.total_co2e or 0) for e in emiss if e.escopo == 1),
            "emissoes_escopo_2": sum(float(e.total_co2e or 0) for e in emiss if e.escopo == 2),
            "emissoes_escopo_3": sum(float(e.total_co2e or 0) for e in emiss if e.escopo == 3),
        }

    async def gerar_pdf_resumo(self, periodo_inicio: date, periodo_fim: date) -> bytes:
        rel = await self.gerar_relatorio(periodo_inicio, periodo_fim)
        buffer = __import__("io").BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=1.4 * cm, leftMargin=1.4 * cm, topMargin=1.4 * cm, bottomMargin=1.4 * cm)
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name="CarbonTitle", parent=styles["Title"], fontSize=16, leading=20, textColor=colors.HexColor("#047857")))
        styles.add(ParagraphStyle(name="CarbonBody", parent=styles["BodyText"], fontSize=9, leading=12))
        story = [
            Paragraph("Relatório de Carbono e MRV", styles["CarbonTitle"]),
            Spacer(1, 0.2 * cm),
            Paragraph(f"Período: {rel.periodo_inicio:%d/%m/%Y} a {rel.periodo_fim:%d/%m/%Y}", styles["CarbonBody"]),
            Paragraph(f"Total geral: {float(rel.total_geral or 0):,.2f} kgCO2e", styles["CarbonBody"]),
            Paragraph(f"Créditos gerados: {float(rel.creditos_gerados or 0):,.2f} tCO2e", styles["CarbonBody"]),
            Paragraph(f"Saldo líquido: {float(rel.saldo_liquido or 0):,.2f} kgCO2e", styles["CarbonBody"]),
        ]
        table = Table(
            [
                ["Escopo", "Total kgCO2e"],
                ["1", f"{float(rel.escopo_1_total or 0):,.2f}"],
                ["2", f"{float(rel.escopo_2_total or 0):,.2f}"],
                ["3", f"{float(rel.escopo_3_total or 0):,.2f}"],
            ]
        )
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#047857")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#a7f3d0")),
        ]))
        story.extend([Spacer(1, 0.25 * cm), table])
        doc.build(story)
        return buffer.getvalue()

    async def dashboard_carbono(self) -> dict:
        return await self.dashboard()

    async def listar_emissoes_carbono(self, escopo: int | None = None) -> list[CarbonoEmissao]:
        return await self.listar_emissoes(escopo=escopo)

    async def registrar_emissao_carbono(self, dados: dict) -> CarbonoEmissao:
        return await self.registrar_emissao(dados)

    async def listar_projetos_carbono(self, status_filter: str | None = None) -> list[CarbonoProjeto]:
        return await self.listar_projetos(status=status_filter)

    async def criar_projeto_carbono(self, dados: dict) -> CarbonoProjeto:
        return await self.criar_projeto(dados)

    async def listar_relatorios_carbono(self) -> list[CarbonoRelatorio]:
        return await self.listar_relatorios()

    async def gerar_relatorio_carbono(self, periodo_inicio: date, periodo_fim: date) -> CarbonoRelatorio:
        return await self.gerar_relatorio(periodo_inicio, periodo_fim)

    async def exportar_pdf_carbono(self, relatorio_id: int) -> bytes:
        stmt = select(CarbonoRelatorio).where(
            CarbonoRelatorio.id == relatorio_id,
            CarbonoRelatorio.tenant_id == self.tenant_id,
        )
        relatorio = (await self.session.execute(stmt)).scalar_one_or_none()
        if not relatorio:
            raise EntityNotFoundError("Relatório de carbono não encontrado.")
        periodo_inicio = relatorio.periodo_inicio.date() if hasattr(relatorio.periodo_inicio, "date") else relatorio.periodo_inicio
        periodo_fim = relatorio.periodo_fim.date() if hasattr(relatorio.periodo_fim, "date") else relatorio.periodo_fim
        return await self.gerar_pdf_resumo(periodo_inicio, periodo_fim)
