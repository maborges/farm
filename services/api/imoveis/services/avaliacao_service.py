from __future__ import annotations

import io
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.models.auth import Usuario
from imoveis.models.imovel import AvaliacaoImovel, ImovelRural, MetodoAvaliacaoImovel


class AvaliacaoService:
    """Regras de negócio para avaliações patrimoniais de imóveis rurais."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_imovel_by_id(self, imovel_id: uuid.UUID, tenant_id: uuid.UUID) -> Optional[ImovelRural]:
        result = await self.session.execute(
            select(ImovelRural)
            .where(
                and_(
                    ImovelRural.id == imovel_id,
                    ImovelRural.tenant_id == tenant_id,
                    ImovelRural.deleted_at.is_(None),
                )
            )
            .options(selectinload(ImovelRural.avaliacoes))
        )
        return result.scalar_one_or_none()

    async def listar_avaliacoes(
        self,
        tenant_id: uuid.UUID,
        imovel_id: Optional[uuid.UUID] = None,
    ) -> list[AvaliacaoImovel]:
        stmt = select(AvaliacaoImovel).where(AvaliacaoImovel.tenant_id == tenant_id)
        if imovel_id:
            stmt = stmt.where(AvaliacaoImovel.imovel_id == imovel_id)

        result = await self.session.execute(stmt.order_by(desc(AvaliacaoImovel.data_avaliacao), desc(AvaliacaoImovel.created_at)))
        return list(result.scalars().all())

    async def criar_avaliacao(
        self,
        tenant_id: uuid.UUID,
        imovel_id: uuid.UUID,
        data_avaliacao: datetime,
        metodo: MetodoAvaliacaoImovel,
        valor_total: Decimal | None,
        valor_por_hectare: Decimal | None,
        valor_terra_nua: Decimal | None,
        valor_benfeitorias: Decimal | None,
        valor_lavoura_perene: Decimal | None,
        moeda: str,
        responsavel: str | None,
        numero_laudo: str | None,
        observacoes: str | None,
        anexos: list[dict] | None,
        created_by: uuid.UUID,
    ) -> tuple[AvaliacaoImovel, list[str]]:
        imovel = await self.get_imovel_by_id(imovel_id, tenant_id)
        if not imovel:
            raise ValueError("Imóvel não encontrado")

        if valor_total is None and valor_por_hectare is None:
            raise ValueError("Informe valor total ou valor por hectare")

        if valor_total is None and valor_por_hectare is not None:
            valor_total = (valor_por_hectare * (imovel.area_total_ha or Decimal("0"))).quantize(Decimal("0.01"))

        if valor_por_hectare is None and valor_total is not None:
            base_area = imovel.area_total_ha or Decimal("0")
            if base_area <= 0:
                raise ValueError("Área total do imóvel deve ser maior que zero para calcular valor por hectare")
            valor_por_hectare = (valor_total / base_area).quantize(Decimal("0.01"))

        if valor_total is None:
            raise ValueError("Não foi possível determinar o valor total da avaliação")

        avaliacao = AvaliacaoImovel(
            tenant_id=tenant_id,
            imovel_id=imovel_id,
            data_avaliacao=data_avaliacao,
            metodo=metodo,
            valor_total=valor_total,
            valor_por_hectare=valor_por_hectare,
            valor_terra_nua=valor_terra_nua,
            valor_benfeitorias=valor_benfeitorias,
            valor_lavoura_perene=valor_lavoura_perene,
            moeda=moeda or "BRL",
            responsavel=responsavel,
            numero_laudo=numero_laudo,
            observacoes=observacoes,
            anexos=anexos or [],
            created_by=created_by,
        )

        self.session.add(avaliacao)
        return avaliacao, ["Avaliação patrimonial criada"]

    async def get_resumo_imovel(self, tenant_id: uuid.UUID, imovel_id: uuid.UUID) -> dict:
        imovel = await self.get_imovel_by_id(imovel_id, tenant_id)
        if not imovel:
            raise ValueError("Imóvel não encontrado")

        avaliacoes = await self.listar_avaliacoes(tenant_id, imovel_id=imovel_id)
        ultima = avaliacoes[0] if avaliacoes else None
        anterior = avaliacoes[1] if len(avaliacoes) > 1 else None

        valorizacao = None
        if ultima and anterior and anterior.valor_total:
            diff = Decimal(ultima.valor_total) - Decimal(anterior.valor_total)
            if Decimal(anterior.valor_total) != 0:
                valorizacao = (diff / Decimal(anterior.valor_total)) * Decimal("100")

        return {
            "imovel": imovel,
            "total_avaliacoes": len(avaliacoes),
            "ultima_avaliacao": ultima,
            "valor_total_atual": ultima.valor_total if ultima else None,
            "valor_por_hectare_atual": ultima.valor_por_hectare if ultima else None,
            "variacao_percentual": float(valorizacao.quantize(Decimal("0.01"))) if valorizacao is not None else None,
            "serie_historica": avaliacoes,
            "area_total_ha": imovel.area_total_ha,
        }

    async def gerar_pdf_historico(self, tenant_id: uuid.UUID, imovel_id: uuid.UUID) -> bytes:
        resumo = await self.get_resumo_imovel(tenant_id, imovel_id)
        imovel: ImovelRural = resumo["imovel"]
        avaliacoes: list[AvaliacaoImovel] = resumo["serie_historica"]

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=1.4 * cm, leftMargin=1.4 * cm, topMargin=1.4 * cm, bottomMargin=1.4 * cm)
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name="TitleSmall", parent=styles["Title"], fontSize=16, leading=20, textColor=colors.HexColor("#0f766e")))
        styles.add(ParagraphStyle(name="BodySmall", parent=styles["BodyText"], fontSize=9, leading=12))

        story: list = [
            Paragraph("Relatório de Avaliação Patrimonial", styles["TitleSmall"]),
            Spacer(1, 0.2 * cm),
            Paragraph(f"Imóvel: <b>{imovel.nome}</b>", styles["BodySmall"]),
            Paragraph(f"Município: {imovel.municipio}/{imovel.uf}", styles["BodySmall"]),
            Paragraph(f"Área total: {imovel.area_total_ha:.4f} ha", styles["BodySmall"]),
            Spacer(1, 0.3 * cm),
        ]

        if resumo["ultima_avaliacao"]:
            ultima = resumo["ultima_avaliacao"]
            story.extend(
                [
                    Paragraph("Resumo atual", styles["Heading2"]),
                    Paragraph(f"Valor total: {ultima.valor_total:,.2f} {ultima.moeda}", styles["BodySmall"]),
                    Paragraph(
                        f"Valor por hectare: {(ultima.valor_por_hectare or Decimal('0')):,.2f} {ultima.moeda}/ha",
                        styles["BodySmall"],
                    ),
                    Paragraph(f"Método: {ultima.metodo.value}", styles["BodySmall"]),
                    Spacer(1, 0.3 * cm),
                ]
            )

        data = [["Data", "Método", "Valor total", "Valor/ha", "Laudo"]]
        for item in avaliacoes:
            data.append(
                [
                    item.data_avaliacao.strftime("%d/%m/%Y"),
                    item.metodo.value,
                    f"{item.moeda} {item.valor_total:,.2f}",
                    f"{item.moeda} {(item.valor_por_hectare or Decimal('0')):,.2f}",
                    item.numero_laudo or "-",
                ]
            )

        table = Table(data, repeatRows=1, colWidths=[2.6 * cm, 2.4 * cm, 3.3 * cm, 3.3 * cm, 3.1 * cm])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f766e")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )
        story.append(table)
        doc.build(story)
        return buffer.getvalue()
