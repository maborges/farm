import uuid
import hashlib
import json
from uuid import UUID
from datetime import date, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from core.base_service import BaseService
from core.exceptions import BusinessRuleError, EntityNotFoundError
from core.models.auth import Usuario
from core.services.storage_service import StorageService
from core.services.audit_service import _serialize, write_audit_log
from agricola.caderno.models import (
    CadernoCampoEntrada,
    CadernoCampoFoto,
    CadernoEventoStatusHistorico,
    VisitaTecnica,
    EPIEntrega,
    CadernoExportacao,
)
from agricola.caderno.schemas import ExportacaoCreate
from agricola.caderno.service import (
    STATUS_EVENTO_VALIDOS,
    DOCUMENTAL_STATUS_VIGENTE,
    DOCUMENTAL_STATUS_ORIGEM_INVALIDADA,
    _normalizar_chave,
)
from agricola.operacoes.models import OperacaoAgricola


class CadernoExportacaoService(BaseService[CadernoExportacao]):
    def __init__(self, session: AsyncSession, tenant_id: UUID):
        super().__init__(CadernoExportacao, session, tenant_id)

    @staticmethod
    def _protocolo_documental() -> str:
        return f"CDOC-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:10].upper()}"

    async def _listar_eventos_documentais(
        self,
        safra_id: UUID,
        talhao_id: UUID | None,
        modo_exportacao: str,
    ) -> list[CadernoCampoEntrada]:
        stmt = (
            select(CadernoCampoEntrada)
            .where(
                CadernoCampoEntrada.tenant_id == self.tenant_id,
                CadernoCampoEntrada.safra_id == safra_id,
            )
            .options(selectinload(CadernoCampoEntrada.fotos), selectinload(CadernoCampoEntrada.status_historico))
            .order_by(CadernoCampoEntrada.data_registro.desc(), CadernoCampoEntrada.created_at.desc())
        )
        if talhao_id:
            stmt = stmt.where(CadernoCampoEntrada.talhao_id == talhao_id)
        if modo_exportacao == "OFICIAL":
            stmt = stmt.where(CadernoCampoEntrada.excluida == False)
            stmt = stmt.where(CadernoCampoEntrada.status_evento.in_(["APROVADO", "CONSOLIDADO"]))
            stmt = stmt.where(CadernoCampoEntrada.retificado_por_evento_id.is_(None))
            stmt = stmt.where(CadernoCampoEntrada.origem_invalidada == False)
        else:
            stmt = stmt.where(CadernoCampoEntrada.status_evento.in_(list(STATUS_EVENTO_VALIDOS)))

        return list((await self.session.execute(stmt)).scalars().all())

    async def _listar_visitas_e_epis_documentais(
        self,
        safra_id: UUID,
        talhao_id: UUID | None,
    ) -> tuple[list[VisitaTecnica], list[EPIEntrega]]:
        visitas_stmt = select(VisitaTecnica).where(
            VisitaTecnica.tenant_id == self.tenant_id,
            VisitaTecnica.safra_id == safra_id,
        ).order_by(VisitaTecnica.data_visita.desc(), VisitaTecnica.created_at.desc())
        if talhao_id:
            visitas_stmt = visitas_stmt.where(VisitaTecnica.talhao_id == talhao_id)
        visitas = list((await self.session.execute(visitas_stmt)).scalars().all())

        epi_stmt = select(EPIEntrega).where(
            EPIEntrega.tenant_id == self.tenant_id,
        ).order_by(EPIEntrega.data_entrega.desc(), EPIEntrega.created_at.desc())
        epis = list((await self.session.execute(epi_stmt)).scalars().all())
        return visitas, epis

    async def _carregar_operacoes_documentais(self, entradas: list[CadernoCampoEntrada]) -> dict[UUID, OperacaoAgricola]:
        operacao_ids = list({e.operacao_id for e in entradas if getattr(e, "operacao_id", None)})
        if not operacao_ids:
            return {}
        op_stmt = select(OperacaoAgricola).where(
            OperacaoAgricola.tenant_id == self.tenant_id,
            OperacaoAgricola.id.in_(operacao_ids),
        )
        return {
            op.id: op
            for op in (await self.session.execute(op_stmt)).scalars().all()
        }

    async def _listar_historico_status_documental(self, entrada_ids: list[UUID]) -> list[CadernoEventoStatusHistorico]:
        if not entrada_ids:
            return []
        stmt = (
            select(CadernoEventoStatusHistorico)
            .where(
                CadernoEventoStatusHistorico.tenant_id == self.tenant_id,
                CadernoEventoStatusHistorico.caderno_entrada_id.in_(entrada_ids),
            )
            .order_by(CadernoEventoStatusHistorico.created_at.asc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    def _snapshot_documental(
        self,
        *,
        safra,
        entradas: list[CadernoCampoEntrada],
        visitas: list[VisitaTecnica],
        epis: list[EPIEntrega],
        historico_status: list[CadernoEventoStatusHistorico],
        modelo: str,
        modo_exportacao: str,
        responsavel_tecnico_id: UUID | None = None,
        responsavel_tecnico_nome: str | None = None,
        responsavel_tecnico_crea: str | None = None,
        observacao_assinatura: str | None = None,
    ) -> dict[str, Any]:
        def _foto_payload(foto: CadernoCampoFoto) -> dict[str, Any]:
            return {
                "id": str(foto.id),
                "url": foto.url,
                "latitude": float(foto.latitude) if foto.latitude is not None else None,
                "longitude": float(foto.longitude) if foto.longitude is not None else None,
                "data_captura": foto.data_captura.isoformat() if foto.data_captura else None,
            }

        def _entrada_payload(entrada: CadernoCampoEntrada) -> dict[str, Any]:
            documental_status = (
                DOCUMENTAL_STATUS_ORIGEM_INVALIDADA if entrada.origem_invalidada else DOCUMENTAL_STATUS_VIGENTE
            )
            return {
                "id": str(entrada.id),
                "tipo": entrada.tipo,
                "tipo_evento": entrada.tipo_evento,
                "descricao": entrada.descricao,
                "data_registro": entrada.data_registro.isoformat(),
                "talhao_id": str(entrada.talhao_id),
                "status_evento": entrada.status_evento,
                "origem_evento": entrada.origem_evento,
                "origem_id": entrada.origem_id,
                "origem_tecnica": entrada.origem_tecnica,
                "nivel_severidade": entrada.nivel_severidade,
                "numero_receituario": entrada.numero_receituario,
                "excluida": entrada.excluida,
                "retifica_evento_id": str(entrada.retifica_evento_id) if entrada.retifica_evento_id else None,
                "retificado_por_evento_id": str(entrada.retificado_por_evento_id) if entrada.retificado_por_evento_id else None,
                "motivo_retificacao": entrada.motivo_retificacao,
                "retificado_em": entrada.retificado_em.isoformat() if entrada.retificado_em else None,
                "retificado_por_usuario_id": str(entrada.retificado_por_usuario_id) if entrada.retificado_por_usuario_id else None,
                "origem_invalidada": entrada.origem_invalidada,
                "origem_invalidada_em": entrada.origem_invalidada_em.isoformat() if entrada.origem_invalidada_em else None,
                "origem_invalidada_por": str(entrada.origem_invalidada_por) if entrada.origem_invalidada_por else None,
                "motivo_invalidacao_origem": entrada.motivo_invalidacao_origem,
                "documental_status": documental_status,
                "versao_vigente": (
                    not entrada.excluida
                    and not entrada.retificado_por_evento_id
                    and not entrada.origem_invalidada
                    and _normalizar_chave(entrada.status_evento) in {"APROVADO", "CONSOLIDADO"}
                ),
                "fotos": [_foto_payload(f) for f in entrada.fotos],
                "status_historico": [
                    {
                        "status_anterior": h.status_anterior,
                        "status_novo": h.status_novo,
                        "usuario_id": str(h.usuario_id) if h.usuario_id else None,
                        "justificativa": h.justificativa,
                        "created_at": h.created_at.isoformat() if h.created_at else None,
                    }
                    for h in entrada.status_historico
                ],
            }

        return {
            "safra": {
                "id": str(safra.id),
                "ano_safra": safra.ano_safra,
                "cultura": safra.cultura,
                "status": safra.status,
            },
            "talhao_id": str(entradas[0].talhao_id) if entradas else None,
            "modelo": modelo,
            "modo_exportacao": modo_exportacao,
            "eventos": [_entrada_payload(e) for e in entradas],
            "visitas_tecnicas": [
                {
                    "id": str(v.id),
                    "talhao_id": str(v.talhao_id),
                    "data_visita": v.data_visita.isoformat(),
                    "nome_rt": v.nome_rt,
                    "crea": v.crea,
                    "assinado": v.assinado,
                    "data_assinatura": v.data_assinatura.isoformat() if v.data_assinatura else None,
                    "observacoes": v.observacoes,
                    "recomendacoes": v.recomendacoes,
                }
                for v in visitas
            ],
            "epi_entregas": [
                {
                    "id": str(e.id),
                    "nome_trabalhador": e.nome_trabalhador,
                    "epi_tipo": e.epi_tipo,
                    "quantidade": e.quantidade,
                    "data_entrega": e.data_entrega.isoformat(),
                    "validade": e.validade.isoformat() if e.validade else None,
                    "operacao_id": str(e.operacao_id) if e.operacao_id else None,
                    "assinatura_url": e.assinatura_url,
                }
                for e in epis
            ],
            "historico_status": [
                {
                    "caderno_entrada_id": str(h.caderno_entrada_id),
                    "status_anterior": h.status_anterior,
                    "status_novo": h.status_novo,
                    "usuario_id": str(h.usuario_id) if h.usuario_id else None,
                    "justificativa": h.justificativa,
                    "created_at": h.created_at.isoformat() if h.created_at else None,
                }
                for h in historico_status
            ],
            "assinatura": {
                "responsavel_tecnico_id": str(responsavel_tecnico_id) if responsavel_tecnico_id else None,
                "responsavel_tecnico_nome": responsavel_tecnico_nome,
                "responsavel_tecnico_crea": responsavel_tecnico_crea,
                "observacao": observacao_assinatura,
            },
        }

    @staticmethod
    def _hash_documental(snapshot: dict[str, Any]) -> str:
        payload = json.dumps(snapshot, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    async def registrar_assinatura(
        self,
        exportacao_id: UUID,
        *,
        usuario: Usuario,
        responsavel_tecnico_id: UUID | None = None,
        responsavel_tecnico_nome: str | None = None,
        crea_rt: str | None = None,
        crea_validade: date | None = None,
        observacao: str | None = None,
        assinatura_origem: str = "WEB_SESSION",
        ip_address: str | None = None,
    ) -> CadernoExportacao:
        exportacao = await self.get_or_fail(exportacao_id)
        payload_before = _serialize(exportacao)
        if responsavel_tecnico_id and responsavel_tecnico_id != usuario.id:
            raise BusinessRuleError("O responsável técnico informado deve ser o usuário autenticado.")

        nome_rt = usuario.nome_completo or usuario.username or responsavel_tecnico_nome
        snapshot_hash = exportacao.snapshot_hash or exportacao.hash_documental
        if snapshot_hash is None and exportacao.snapshot_documental is not None:
            snapshot_hash = self._hash_documental(exportacao.snapshot_documental)
        protocolo_documental = exportacao.protocolo_documental or self._protocolo_documental()
        assinado_em = datetime.utcnow()

        exportacao.responsavel_tecnico_id = usuario.id
        exportacao.responsavel_tecnico_nome = nome_rt
        exportacao.responsavel_tecnico_crea = crea_rt or exportacao.responsavel_tecnico_crea
        exportacao.usuario_assinatura_id = usuario.id
        exportacao.assinado_por = nome_rt
        exportacao.crea_rt = crea_rt or exportacao.crea_rt
        exportacao.crea_validade = crea_validade or exportacao.crea_validade
        exportacao.assinado_em = assinado_em
        exportacao.assinatura_origem = assinatura_origem
        exportacao.observacao_assinatura = observacao
        exportacao.protocolo_documental = protocolo_documental
        exportacao.snapshot_hash = snapshot_hash
        if exportacao.hash_documental is None:
            exportacao.hash_documental = snapshot_hash
        exportacao.assinatura_hash = self._hash_documental(
            {
                "exportacao_id": str(exportacao.id),
                "protocolo_documental": protocolo_documental,
                "snapshot_hash": snapshot_hash,
                "assinatura": {
                    "usuario_id": str(usuario.id),
                    "responsavel_tecnico_nome": nome_rt,
                    "responsavel_tecnico_crea": exportacao.responsavel_tecnico_crea,
                    "observacao": observacao,
                    "assinatura_origem": assinatura_origem,
                    "assinado_em": assinado_em.isoformat(),
                },
            }
        )

        await self.session.flush()
        await write_audit_log(
            self.session,
            tenant_id=self.tenant_id,
            user_id=usuario.id,
            action="sign",
            resource="caderno_exportacoes",
            resource_id=exportacao.id,
            payload_before=payload_before,
            payload_after=_serialize(exportacao),
            ip_address=ip_address,
        )
        await self.session.flush()
        return exportacao

    async def gerar(self, dados: ExportacaoCreate) -> CadernoExportacao:
        # Normaliza modelo: aceita "padrao", "globalgap", "organico", "mapa"
        modelo = dados.modelo
        modo_exportacao = _normalizar_chave(dados.modo_exportacao or "OFICIAL")
        if modo_exportacao not in {"OFICIAL", "AUDITORIA"}:
            raise BusinessRuleError("Modo de exportação inválido.")
        # Suporte legado: se modelo_certificacao foi passado, mapeia
        if dados.modelo_certificacao:
            legado_map = {
                "INTERNO": "padrao",
                "GLOBALGAP": "globalgap",
                "ORGANICO": "organico",
                "MAPA": "mapa",
            }
            modelo = legado_map.get(dados.modelo_certificacao.upper(), modelo)

        # 1. Busca dados da safra
        from agricola.safras.models import Safra
        safra_stmt = select(Safra).where(Safra.id == dados.safra_id, Safra.tenant_id == self.tenant_id)
        safra = (await self.session.execute(safra_stmt)).scalar_one_or_none()
        if not safra:
            raise EntityNotFoundError("Safra", dados.safra_id)

        # 2. Busca dados documentais do caderno
        entradas = await self._listar_eventos_documentais(dados.safra_id, dados.talhao_id, modo_exportacao)
        visitas, epis = await self._listar_visitas_e_epis_documentais(dados.safra_id, dados.talhao_id)
        historico_status = await self._listar_historico_status_documental([e.id for e in entradas]) if modo_exportacao == "AUDITORIA" else []
        operacoes_por_id: dict[UUID, OperacaoAgricola] = {}
        if modelo in {"globalgap", "mapa"}:
            operacoes_por_id = await self._carregar_operacoes_documentais(entradas)
        snapshot = self._snapshot_documental(
            safra=safra,
            entradas=entradas,
            visitas=visitas,
            epis=epis,
            historico_status=historico_status,
            modelo=modelo,
            modo_exportacao=modo_exportacao,
            responsavel_tecnico_id=None,
            responsavel_tecnico_nome=dados.assinado_por,
            responsavel_tecnico_crea=dados.crea_rt,
            observacao_assinatura=None,
        )
        snapshot_hash = self._hash_documental(snapshot)
        protocolo_documental = self._protocolo_documental()

        # 3. Busca nome da fazenda e talhões
        from core.cadastros.propriedades.models import AreaRural
        area_ids = list({e.talhao_id for e in entradas if hasattr(e, 'talhao_id')})
        talhoes_map: dict[str, str] = {}
        if area_ids:
            areas_stmt = select(AreaRural.id, AreaRural.nome).where(AreaRural.id.in_(area_ids))
            areas = (await self.session.execute(areas_stmt)).all()
            talhoes_map = {str(a.id): a.nome for a in areas}

        # 4. Busca visitas técnicas (para campos específicos de modelos)
        from agricola.caderno.models import VisitaTecnica
        visitas_stmt = select(VisitaTecnica).where(
            VisitaTecnica.tenant_id == self.tenant_id,
            VisitaTecnica.safra_id == dados.safra_id,
        )
        if dados.talhao_id:
            visitas_stmt = visitas_stmt.where(VisitaTecnica.talhao_id == dados.talhao_id)
        visitas = list((await self.session.execute(visitas_stmt)).scalars().all())

        # 5. Gera PDF conforme modelo
        import io
        import uuid as _uuid
        from pathlib import Path
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import cm, mm
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
            PageBreak, Image as RLImage, HRFlowable,
        )
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.colors import HexColor, black, white
        from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY, TA_RIGHT
        from reportlab.lib.units import inch

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            topMargin=2 * cm,
            bottomMargin=1.5 * cm,
            leftMargin=2 * cm,
            rightMargin=2 * cm,
            title=f"Caderno de Campo - {safra.cultura} {safra.ano_safra}",
        )

        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(
            name="DocTitle", fontSize=18, leading=22, textColor=HexColor("#1a5e1a"),
            alignment=TA_CENTER, spaceAfter=4, fontName="Helvetica-Bold",
        ))
        styles.add(ParagraphStyle(
            name="DocSubtitle", fontSize=10, leading=14, textColor=HexColor("#555"),
            alignment=TA_CENTER, spaceAfter=12, fontName="Helvetica",
        ))
        styles.add(ParagraphStyle(
            name="SectionHeader", fontSize=12, leading=16, textColor=HexColor("#1a5e1a"),
            spaceBefore=10, spaceAfter=4, fontName="Helvetica-Bold",
        ))
        styles.add(ParagraphStyle(
            name="BodyText2", fontSize=9, leading=13, textColor=HexColor("#333"),
            alignment=TA_JUSTIFY, fontName="Helvetica",
        ))
        styles.add(ParagraphStyle(
            name="SmallBold", fontSize=9, leading=13, textColor=HexColor("#1a5e1a"),
            fontName="Helvetica-Bold", spaceBefore=2,
        ))
        styles.add(ParagraphStyle(
            name="TableHeader", fontSize=8, leading=11, textColor=HexColor("#fff"),
            fontName="Helvetica-Bold", alignment=TA_CENTER,
        ))
        styles.add(ParagraphStyle(
            name="TableCell", fontSize=8, leading=11, textColor=HexColor("#333"),
            fontName="Helvetica", alignment=TA_LEFT,
        ))

        story = []

        def _retificacao_texto(entrada: CadernoCampoEntrada) -> str:
            partes: list[str] = []
            if entrada.retifica_evento_id:
                partes.append(f"Retifica evento: {str(entrada.retifica_evento_id)}")
            if entrada.retificado_por_evento_id:
                partes.append(f"Retificado por: {str(entrada.retificado_por_evento_id)}")
            if entrada.motivo_retificacao:
                partes.append(f"Motivo da retificação: {entrada.motivo_retificacao}")
            return " | ".join(partes)

        def _invalidacao_origem_texto(entrada: CadernoCampoEntrada) -> str:
            if not entrada.origem_invalidada:
                return ""
            partes = ["⚠ Origem operacional invalidada"]
            if entrada.origem_invalidada_em:
                partes.append(f"em {entrada.origem_invalidada_em.strftime('%d/%m/%Y %H:%M')}")
            if entrada.origem_invalidada_por:
                partes.append(f"por {str(entrada.origem_invalidada_por)}")
            if entrada.motivo_invalidacao_origem:
                partes.append(f"motivo: {entrada.motivo_invalidacao_origem}")
            return " | ".join(partes)

        # ═══════════════════════════════════════════════════════
        # LAYOUT POR MODELO
        # ═══════════════════════════════════════════════════════

        modelo_labels = {
            "padrao": "Caderno de Campo — Relatório Padrão",
            "globalgap": "Caderno de Campo — GlobalG.A.P.",
            "organico": "Caderno de Campo — Produção Orgânica (USDA/IBD)",
            "mapa": "Caderno de Campo — MAPA (Receituário Agronômico)",
        }

        # ── Cabeçalho ──
        story.append(Paragraph(modelo_labels.get(modelo, modelo_labels["padrao"]), styles["DocTitle"]))
        story.append(Paragraph(
            f"{safra.cultura} — Safra {safra.ano_safra}",
            styles["DocSubtitle"],
        ))
        story.append(HRFlowable(width="100%", thickness=1, color=HexColor("#1a5e1a"), spaceAfter=10))

        # ── Informações gerais ──
        info_data = [
            [Paragraph("<b>Cultura:</b>", styles["SmallBold"]), Paragraph(safra.cultura or "—", styles["BodyText2"])],
            [Paragraph("<b>Safra:</b>", styles["SmallBold"]), Paragraph(safra.ano_safra or "—", styles["BodyText2"])],
            [Paragraph("<b>Status:</b>", styles["SmallBold"]), Paragraph(safra.status or "—", styles["BodyText2"])],
        ]

        # Campos extras por modelo
        if modelo == "globalgap":
            # GlobalG.A.P.: número de registro, rastreabilidade de insumos, lote
            info_data.append([
                Paragraph("<b>Registro GlobalG.A.P.:</b>", styles["SmallBold"]),
                Paragraph(safra.id_externo or "N/I", styles["BodyText2"]),
            ])
            info_data.append([
                Paragraph("<b>Lote de Produto:</b>", styles["SmallBold"]),
                Paragraph(f"LOTE-{safra.id.hex[:8].upper()}", styles["BodyText2"]),
            ])
        elif modelo == "organico":
            # Orgânico: declaração de origem, período de conversão
            info_data.append([
                Paragraph("<b>Período de Conversão:</b>", styles["SmallBold"]),
                Paragraph(f"{safra.data_plantio or 'N/I'} até {safra.data_colheita or 'Em andamento'}", styles["BodyText2"]),
            ])
            info_data.append([
                Paragraph("<b>Declar. Origem:</b>", styles["SmallBold"]),
                Paragraph(f"Propriedade: {safra.cultura} — Safra {safra.ano_safra}", styles["BodyText2"]),
            ])
        elif modelo == "mapa":
            # MAPA: receituário agronômico
            if dados.assinado_por:
                info_data.append([
                    Paragraph("<b>Responsável Técnico:</b>", styles["SmallBold"]),
                    Paragraph(f"{dados.assinado_por} — CREA {dados.crea_rt or 'N/I'}", styles["BodyText2"]),
                ])

        if dados.assinado_por and modelo != "mapa":
            info_data.append([
                Paragraph("<b>Responsável:</b>", styles["SmallBold"]),
                Paragraph(f"{dados.assinado_por} — CREA {dados.crea_rt or 'N/I'}", styles["BodyText2"]),
            ])
        info_data.append([
            Paragraph("<b>Modo de Exportação:</b>", styles["SmallBold"]),
            Paragraph(modo_exportacao, styles["BodyText2"]),
        ])
        info_data.append([
            Paragraph("<b>Hash Documental:</b>", styles["SmallBold"]),
            Paragraph(snapshot_hash[:16] + "…", styles["BodyText2"]),
        ])
        info_data.append([
            Paragraph("<b>Protocolo:</b>", styles["SmallBold"]),
            Paragraph(protocolo_documental, styles["BodyText2"]),
        ])

        info_table = Table(info_data, colWidths=[4.5*cm, 10*cm])
        info_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("LINEBELOW", (0, 0), (-1, -1), 0.5, HexColor("#ddd")),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 12))

        # ═══════════════════════════════════════════════════════
        # GLOBALG.A.P. — Rastreabilidade de insumos
        # ═══════════════════════════════════════════════════════
        if modelo == "globalgap":
            story.append(Paragraph("Rastreabilidade de Insumos (GlobalG.A.P.)", styles["SectionHeader"]))
            story.append(HRFlowable(width="100%", thickness=0.5, color=HexColor("#ccc"), spaceAfter=6))

            # Coleta insumos das operações
            insumos_rows = []
            for e in entradas:
                if hasattr(e, 'operacao_id') and e.operacao_id:
                    op = operacoes_por_id.get(e.operacao_id)
                    if op and op.insumos:
                        for ins in op.insumos:
                            retificacao_info = _retificacao_texto(e)
                            invalidacao_info = _invalidacao_origem_texto(e)
                            talhao_label = getattr(ins, "produto_nome", None) or str(ins.produto_id)
                            extras = [texto for texto in [retificacao_info, invalidacao_info] if texto]
                            if extras:
                                talhao_label = f"{talhao_label}<br/>" + "<br/>".join(extras)
                            insumos_rows.append([
                                Paragraph(e.data_registro.strftime("%d/%m/%Y"), styles["TableCell"]),
                                Paragraph(talhao_label, styles["TableCell"]),
                                Paragraph(f"{ins.dose_por_ha or ''} {ins.unidade or ''}/ha", styles["TableCell"]),
                                Paragraph(str(getattr(ins, "registro_mapa", "N/A")), styles["TableCell"]),
                            ])

            if not insumos_rows:
                # Fallback: mostra entradas com dados básicos
                for e in entradas:
                    talhao_nome = talhoes_map.get(str(e.talhao_id), f"Talhão {str(e.talhao_id)[:8]}")
                    retificacao_info = _retificacao_texto(e)
                    invalidacao_info = _invalidacao_origem_texto(e)
                    extras = [texto for texto in [retificacao_info, invalidacao_info] if texto]
                    talhao_label = talhao_nome if not extras else f"{talhao_nome}<br/>" + "<br/>".join(extras)
                    insumos_rows.append([
                        Paragraph(e.data_registro.strftime("%d/%m/%Y") if hasattr(e.data_registro, 'strftime') else str(e.data_registro), styles["TableCell"]),
                        Paragraph(talhao_label, styles["TableCell"]),
                        Paragraph(e.tipo_evento or e.tipo, styles["TableCell"]),
                        Paragraph("—", styles["TableCell"]),
                    ])

            insumos_header = [
                Paragraph("<b>Data</b>", styles["TableHeader"]),
                Paragraph("<b>Insumo / Talhão</b>", styles["TableHeader"]),
                Paragraph("<b>Dose</b>", styles["TableHeader"]),
                Paragraph("<b>Registro MAPA</b>", styles["TableHeader"]),
            ]
            insumos_table = Table([insumos_header] + insumos_rows, colWidths=[3*cm, 4*cm, 3*cm, 3*cm])
            insumos_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), HexColor("#1a5e1a")),
                ("TEXTCOLOR", (0, 0), (-1, 0), white),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOX", (0, 0), (-1, -1), 0.5, HexColor("#ccc")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [HexColor("#f9f9f9"), white]),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
            ]))
            story.append(insumos_table)
            story.append(Spacer(1, 16))

        # ═══════════════════════════════════════════════════════
        # ORGÂNICO — Ausência de agroquímicos + declaração
        # ═══════════════════════════════════════════════════════
        if modelo == "organico":
            story.append(Paragraph("Declaração de Produção Orgânica", styles["SectionHeader"]))
            story.append(HRFlowable(width="100%", thickness=0.5, color=HexColor("#ccc"), spaceAfter=6))

            story.append(Paragraph(
                f"Declaramos para fins de certificação orgânica (USDA/IBD) que as operações registradas neste "
                f"caderno de campo referentes à safra {safra.ano_safra} de {safra.cultura} foram realizadas "
                f"sem a utilização de agroquímicos ou insumos sintéticos proibidos pela legislação orgânica vigente.",
                styles["BodyText2"],
            ))
            story.append(Spacer(1, 10))

            # Tabela de operações — destaca ausência de agroquímicos
            story.append(Paragraph("Registro de Operações — Produção Orgânica", styles["SectionHeader"]))
            story.append(HRFlowable(width="100%", thickness=0.5, color=HexColor("#ccc"), spaceAfter=6))

            organico_rows = []
            for e in entradas:
                talhao_nome = talhoes_map.get(str(e.talhao_id), f"Talhão {str(e.talhao_id)[:8]}")
                desc = (e.descricao or "")[:80]
                retificacao_info = _retificacao_texto(e)
                invalidacao_info = _invalidacao_origem_texto(e)
                extras = [texto for texto in [retificacao_info, invalidacao_info] if texto]
                if extras:
                    desc = f"{desc}<br/>" + "<br/>".join(extras)
                organico_rows.append([
                    Paragraph(e.data_registro.strftime("%d/%m/%Y") if hasattr(e.data_registro, 'strftime') else str(e.data_registro), styles["TableCell"]),
                    Paragraph(talhao_nome, styles["TableCell"]),
                    Paragraph(e.tipo_evento or e.tipo, styles["TableCell"]),
                    Paragraph(desc, styles["TableCell"]),
                    Paragraph("✓ Livre de agroquímicos", styles["TableCell"]),
                ])

            organico_header = [
                Paragraph("<b>Data</b>", styles["TableHeader"]),
                Paragraph("<b>Talhão</b>", styles["TableHeader"]),
                Paragraph("<b>Tipo</b>", styles["TableHeader"]),
                Paragraph("<b>Descrição</b>", styles["TableHeader"]),
                Paragraph("<b>Status</b>", styles["TableHeader"]),
            ]
            organico_table = Table([organico_header] + organico_rows, colWidths=[2.5*cm, 2.5*cm, 2.5*cm, 5.5*cm, 3*cm])
            organico_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), HexColor("#2e7d32")),
                ("TEXTCOLOR", (0, 0), (-1, 0), white),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOX", (0, 0), (-1, -1), 0.5, HexColor("#ccc")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [HexColor("#f0f7f0"), white]),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
            ]))
            story.append(organico_table)
            story.append(Spacer(1, 16))

        # ═══════════════════════════════════════════════════════
        # MAPA — Doses aplicadas, intervalo de segurança, receituário
        # ═══════════════════════════════════════════════════════
        if modelo == "mapa":
            story.append(Paragraph("Receituário Agronômico (MAPA — Lei 7.802/89)", styles["SectionHeader"]))
            story.append(HRFlowable(width="100%", thickness=0.5, color=HexColor("#ccc"), spaceAfter=6))

            if dados.assinado_por:
                story.append(Paragraph(
                    f"<b>Responsável Técnico:</b> {dados.assinado_por} | <b>CREA:</b> {dados.crea_rt or 'N/I'}",
                    styles["BodyText2"],
                ))
                story.append(Spacer(1, 8))

            # Tabela de operações com doses e intervalo de segurança
            mapa_rows = []
            for e in entradas:
                talhao_nome = talhoes_map.get(str(e.talhao_id), f"Talhão {str(e.talhao_id)[:8]}")
                receituario = e.numero_receituario if hasattr(e, 'numero_receituario') else None
                # Busca operação para dose
                dose_info = "—"
                intervalo = "—"
                retificacao_info = _retificacao_texto(e)
                invalidacao_info = _invalidacao_origem_texto(e)
                if hasattr(e, 'operacao_id') and e.operacao_id:
                    op = operacoes_por_id.get(e.operacao_id)
                    if op and op.insumos:
                        doses = []
                        for ins in op.insumos:
                            doses.append(f"{ins.dose_por_ha or ''} {ins.unidade or ''}/ha")
                        dose_info = "; ".join(doses) if doses else "—"
                        intervalo = f"{op.intervalo_seguranca or '—'} dias" if hasattr(op, 'intervalo_seguranca') else "—"

                mapa_rows.append([
                    Paragraph(e.data_registro.strftime("%d/%m/%Y") if hasattr(e.data_registro, 'strftime') else str(e.data_registro), styles["TableCell"]),
                    Paragraph(talhao_nome, styles["TableCell"]),
                    Paragraph(e.tipo_evento or e.tipo, styles["TableCell"]),
                    Paragraph(
                        "<br/>".join([texto for texto in [dose_info, retificacao_info, invalidacao_info] if texto]),
                        styles["TableCell"],
                    ),
                    Paragraph(intervalo, styles["TableCell"]),
                    Paragraph(receituario or "—", styles["TableCell"]),
                ])

            mapa_header = [
                Paragraph("<b>Data</b>", styles["TableHeader"]),
                Paragraph("<b>Talhão</b>", styles["TableHeader"]),
                Paragraph("<b>Tipo</b>", styles["TableHeader"]),
                Paragraph("<b>Dose Aplicada</b>", styles["TableHeader"]),
                Paragraph("<b>Intervalo Seg.</b>", styles["TableHeader"]),
                Paragraph("<b>Nº Receituário</b>", styles["TableHeader"]),
            ]
            mapa_table = Table([mapa_header] + mapa_rows, colWidths=[2.5*cm, 2*cm, 2*cm, 3*cm, 2.5*cm, 3*cm])
            mapa_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), HexColor("#1565c0")),
                ("TEXTCOLOR", (0, 0), (-1, 0), white),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOX", (0, 0), (-1, -1), 0.5, HexColor("#ccc")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [HexColor("#f0f4fa"), white]),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
            ]))
            story.append(mapa_table)
            story.append(Spacer(1, 16))

        # ═══════════════════════════════════════════════════════
        # LAYOUT PADRÃO — Timeline de entradas (todos os modelos)
        # ═══════════════════════════════════════════════════════
        if modelo == "padrao":
            from collections import defaultdict
            grouped: dict[str, list] = defaultdict(list)
            for e in entradas:
                key = e.data_registro.strftime("%d/%m/%Y") if hasattr(e.data_registro, "strftime") else str(e.data_registro)
                grouped[key].append(e)

            for data_str, items in sorted(grouped.items(), key=lambda x: x[0], reverse=True):
                story.append(Paragraph(f"📅 {data_str}", styles["SectionHeader"]))
                story.append(HRFlowable(width="100%", thickness=0.5, color=HexColor("#ccc"), spaceAfter=6))

                for item in items:
                    tipo_evento_item = (item.tipo_evento if hasattr(item, "tipo_evento") else item.get("tipo_evento", None)) or (
                        item.tipo if hasattr(item, "tipo") else item.get("tipo", "")
                    )
                    tipo_label = {
                        "MONITORAMENTO": "🔍 Monitoramento",
                        "VISITA_TECNICA": "👨‍🔬 Visita Técnica",
                        "EPI_ENTREGA": "🦺 Entrega EPI",
                        "OBSERVACAO": "📝 Observação",
                        "CLIMA": "🌤️ Clima",
                        "SOLO": "🌱 Solo",
                    }.get(tipo_evento_item, tipo_evento_item)

                    talhao_nome = talhoes_map.get(str(item.talhao_id), f"Talhão {str(item.talhao_id)[:8]}")
                    desc = item.descricao if hasattr(item, 'descricao') else item.get('descricao', '')
                    retificacao_info = _retificacao_texto(item) if hasattr(item, "retifica_evento_id") else ""
                    invalidacao_info = _invalidacao_origem_texto(item) if hasattr(item, "origem_invalidada") else ""
                    severidade = item.nivel_severidade if hasattr(item, 'nivel_severidade') else item.get('nivel_severidade')
                    status_evento = item.status_evento if hasattr(item, "status_evento") else item.get("status_evento")
                    status_hist = item.status_historico if hasattr(item, "status_historico") else item.get("status_historico", [])

                    row_data = [
                        Paragraph(f"<b>{tipo_label}</b>", styles["SmallBold"]),
                        Paragraph(talhao_nome, styles["BodyText2"]),
                        Paragraph(f"<b>Severidade:</b> {severidade}" if severidade else "—", styles["BodyText2"]),
                        Paragraph(f"<b>Status:</b> {status_evento or '—'}", styles["BodyText2"]),
                    ]

                    entry_table = Table([row_data], colWidths=[3*cm, 4*cm, 3.5*cm, 4*cm])
                    entry_table.setStyle(TableStyle([
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("BACKGROUND", (0, 0), (-1, 0), HexColor("#f5f5f5")),
                        ("BOX", (0, 0), (-1, -1), 0.5, HexColor("#ddd")),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                        ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ]))
                    story.append(entry_table)
                    story.append(Spacer(1, 2))
                    story.append(Paragraph(desc.replace("\n", "<br/>"), styles["BodyText2"]))
                    if retificacao_info:
                        story.append(Paragraph(f"<b>Retificação:</b> {retificacao_info}", styles["BodyText2"]))
                    if invalidacao_info:
                        story.append(Paragraph(f"<b>Origem:</b> {invalidacao_info}", styles["BodyText2"]))
                    if status_hist and modo_exportacao == "AUDITORIA":
                        hist_txt = "<br/>".join(
                            f"{(getattr(h, 'status_anterior', None) or '—')} → {getattr(h, 'status_novo', '—')} ({getattr(h, 'created_at', None).strftime('%d/%m/%Y %H:%M') if getattr(h, 'created_at', None) else '—'})"
                            for h in status_hist
                        )
                        story.append(Spacer(1, 2))
                        story.append(Paragraph(f"<b>Histórico:</b><br/>{hist_txt}", styles["BodyText2"]))
                    story.append(Spacer(1, 8))

        # ═══════════════════════════════════════════════════════
        # Visitas técnicas e EPI
        # ═══════════════════════════════════════════════════════
        if visitas:
            story.append(Paragraph("Visitas Técnicas", styles["SectionHeader"]))
            story.append(HRFlowable(width="100%", thickness=0.5, color=HexColor("#ccc"), spaceAfter=6))

            visitas_rows = []
            for v in visitas:
                visitas_rows.append([
                    Paragraph(v.data_visita.strftime("%d/%m/%Y"), styles["TableCell"]),
                    Paragraph(v.nome_rt, styles["TableCell"]),
                    Paragraph(v.crea, styles["TableCell"]),
                    Paragraph((v.observacoes or "—")[:80], styles["TableCell"]),
                    Paragraph("✓" if v.assinado else "—", styles["TableCell"]),
                ])

            visitas_header = [
                Paragraph("<b>Data</b>", styles["TableHeader"]),
                Paragraph("<b>Responsável</b>", styles["TableHeader"]),
                Paragraph("<b>CREA</b>", styles["TableHeader"]),
                Paragraph("<b>Observações</b>", styles["TableHeader"]),
                Paragraph("<b>Assinado</b>", styles["TableHeader"]),
            ]
            visitas_table = Table([visitas_header] + visitas_rows, colWidths=[2.5*cm, 3.5*cm, 2.5*cm, 5*cm, 2*cm])
            visitas_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), HexColor("#1a5e1a")),
                ("TEXTCOLOR", (0, 0), (-1, 0), white),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOX", (0, 0), (-1, -1), 0.5, HexColor("#ccc")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [HexColor("#f9f9f9"), white]),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
            ]))
            story.append(visitas_table)
            story.append(Spacer(1, 16))

        if epis:
            story.append(Paragraph("Entregas de EPI", styles["SectionHeader"]))
            story.append(HRFlowable(width="100%", thickness=0.5, color=HexColor("#ccc"), spaceAfter=6))
            epi_rows = []
            for e in epis:
                epi_rows.append([
                    Paragraph(e.data_entrega.strftime("%d/%m/%Y"), styles["TableCell"]),
                    Paragraph(e.nome_trabalhador, styles["TableCell"]),
                    Paragraph(e.epi_tipo, styles["TableCell"]),
                    Paragraph(str(e.quantidade), styles["TableCell"]),
                    Paragraph(e.assinatura_url or "—", styles["TableCell"]),
                ])
            epi_header = [
                Paragraph("<b>Data</b>", styles["TableHeader"]),
                Paragraph("<b>Trabalhador</b>", styles["TableHeader"]),
                Paragraph("<b>EPI</b>", styles["TableHeader"]),
                Paragraph("<b>Qtd</b>", styles["TableHeader"]),
                Paragraph("<b>Assinatura</b>", styles["TableHeader"]),
            ]
            epi_table = Table([epi_header] + epi_rows, colWidths=[2.5*cm, 4*cm, 4*cm, 1.5*cm, 4*cm])
            epi_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), HexColor("#1a5e1a")),
                ("TEXTCOLOR", (0, 0), (-1, 0), white),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOX", (0, 0), (-1, -1), 0.5, HexColor("#ccc")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [HexColor("#f9f9f9"), white]),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
            ]))
            story.append(epi_table)
            story.append(Spacer(1, 16))

        if modo_exportacao == "AUDITORIA" and historico_status:
            story.append(Paragraph("Histórico de Status", styles["SectionHeader"]))
            story.append(HRFlowable(width="100%", thickness=0.5, color=HexColor("#ccc"), spaceAfter=6))
            historico_rows = []
            for h in historico_status:
                historico_rows.append([
                    Paragraph(str(h.caderno_entrada_id)[:8], styles["TableCell"]),
                    Paragraph(h.status_anterior or "—", styles["TableCell"]),
                    Paragraph(h.status_novo, styles["TableCell"]),
                    Paragraph(h.justificativa or "—", styles["TableCell"]),
                    Paragraph(h.created_at.strftime("%d/%m/%Y %H:%M") if h.created_at else "—", styles["TableCell"]),
                ])
            historico_header = [
                Paragraph("<b>Entrada</b>", styles["TableHeader"]),
                Paragraph("<b>Anterior</b>", styles["TableHeader"]),
                Paragraph("<b>Novo</b>", styles["TableHeader"]),
                Paragraph("<b>Justificativa</b>", styles["TableHeader"]),
                Paragraph("<b>Data</b>", styles["TableHeader"]),
            ]
            historico_table = Table([historico_header] + historico_rows, colWidths=[2.5*cm, 2.5*cm, 2.5*cm, 5*cm, 3*cm])
            historico_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), HexColor("#37474f")),
                ("TEXTCOLOR", (0, 0), (-1, 0), white),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOX", (0, 0), (-1, -1), 0.5, HexColor("#ccc")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [HexColor("#f4f4f4"), white]),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
            ]))
            story.append(historico_table)
            story.append(Spacer(1, 16))

        # ── Rodapé com assinaturas ──
        story.append(PageBreak())
        story.append(Paragraph("Assinaturas", styles["SectionHeader"]))
        story.append(HRFlowable(width="100%", thickness=0.5, color=HexColor("#ccc"), spaceAfter=20))

        if modelo == "organico":
            story.append(Paragraph(
                "Declaro que as informações acima são verdadeiras e refletem as práticas de produção orgânica "
                "adotadas nesta propriedade, em conformidade com as normas USDA Organic e IBD Certificações.",
                styles["BodyText2"],
            ))
            story.append(Spacer(1, 30))

        story.append(HRFlowable(width="60%", thickness=1, color=black, spaceAfter=4))
        story.append(Paragraph(
            dados.assinado_por or "Responsável Técnico",
            ParagraphStyle("sigName", fontSize=9, alignment=TA_CENTER, fontName="Helvetica"),
        ))
        if dados.crea_rt:
            story.append(Paragraph(
                f"CREA: {dados.crea_rt}",
                ParagraphStyle("sigCrea", fontSize=8, alignment=TA_CENTER, textColor=HexColor("#666"), fontName="Helvetica"),
            ))

        # Data de geração
        story.append(Spacer(1, 10))
        story.append(Paragraph(
            f"Gerado em {datetime.now().strftime('%d/%m/%Y às %H:%M')}",
            ParagraphStyle("sigDate", fontSize=7, alignment=TA_CENTER, textColor=HexColor("#999"), fontName="Helvetica"),
        ))
        story.append(Paragraph(
            f"Protocolo documental: {protocolo_documental}",
            ParagraphStyle("sigHash", fontSize=7, alignment=TA_CENTER, textColor=HexColor("#999"), fontName="Helvetica"),
        ))

        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()

        filename = f"caderno_{modelo}_{dados.safra_id}_{_uuid.uuid4().hex[:8]}.pdf"
        storage_path = f"static/caderno_exports/{filename}"
        StorageService.save_blob(pdf_bytes, storage_path)
        url_pdf = StorageService.public_url(storage_path)

        exportacao = CadernoExportacao(
            tenant_id=self.tenant_id,
            safra_id=dados.safra_id,
            talhao_id=dados.talhao_id,
            url_pdf=url_pdf,
            snapshot_documental=snapshot,
            snapshot_hash=snapshot_hash,
            modo_exportacao=modo_exportacao,
            hash_documental=snapshot_hash,
            assinatura_hash=None,
            protocolo_documental=protocolo_documental,
            assinado_por=dados.assinado_por,
            crea_rt=dados.crea_rt,
            responsavel_tecnico_nome=dados.assinado_por,
            responsavel_tecnico_crea=dados.crea_rt,
            assinatura_origem="SYSTEM_GENERATED",
            modelo_certificacao=modelo,
        )
        self.session.add(exportacao)
        await self.session.flush()
        return exportacao

    async def listar_por_safra(self, safra_id: UUID) -> list[CadernoExportacao]:
        stmt = select(CadernoExportacao).where(
            CadernoExportacao.tenant_id == self.tenant_id,
            CadernoExportacao.safra_id == safra_id,
        ).order_by(CadernoExportacao.data_geracao.desc())
        return list((await self.session.execute(stmt)).scalars().all())

    async def listar_todas(self) -> list[CadernoExportacao]:
        stmt = select(CadernoExportacao).where(
            CadernoExportacao.tenant_id == self.tenant_id,
        ).order_by(CadernoExportacao.data_geracao.desc())
        return list((await self.session.execute(stmt)).scalars().all())
