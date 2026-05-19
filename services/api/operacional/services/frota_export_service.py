from __future__ import annotations

import csv
import uuid
import zipfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from io import BytesIO, StringIO
from typing import Any
from xml.sax.saxutils import escape

from operacional.services.frota_agricultura_service import FrotaAgriculturaService
from operacional.services.frota_custo_service import FrotaCustoService
from operacional.services.frota_dashboard_service import FrotaDashboardService
from operacional.services.frota_jornada_service import FrotaJornadaService
from operacional.models.frota import RegistroManutencao


CSV_MEDIA_TYPE = "text/csv; charset=utf-8"
XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@dataclass(slots=True)
class ExportArtifact:
    filename: str
    media_type: str
    content: bytes


class FrotaExportService(FrotaDashboardService):
    async def exportar_custos(
        self,
        *,
        periodo_dias: int | None = None,
        unidade_produtiva_id: uuid.UUID | None = None,
        tipo_equipamento: str | None = None,
        formato: str = "csv",
    ) -> ExportArtifact:
        resposta = await FrotaCustoService(
            self.session,
            self.tenant_id,
        ).obter_custos(
            periodo_dias=periodo_dias,
            unidade_produtiva_id=unidade_produtiva_id,
            tipo_equipamento=tipo_equipamento,
        )
        rows = [
            {
                "equipamento_nome": item.equipamento_nome,
                "equipamento_tipo": item.equipamento_tipo,
                "equipamento_status": item.equipamento_status,
                "unidade_produtiva_id": str(item.unidade_produtiva_id) if item.unidade_produtiva_id else "",
                "custo_combustivel": item.custo_combustivel,
                "custo_manutencao": item.custo_manutencao,
                "custo_pecas_itens": item.custo_pecas_itens,
                "custo_documental": item.custo_documental,
                "custo_total": item.custo_total,
                "custo_por_hora": item.custo_por_hora or "",
                "custo_por_km": item.custo_por_km or "",
                "participacao_percentual": item.participacao_percentual or "",
            }
            for item in resposta.equipamentos
        ]
        return self._build_export(
            rows=rows,
            headers=list(rows[0].keys()) if rows else [
                "equipamento_nome",
                "equipamento_tipo",
                "equipamento_status",
                "unidade_produtiva_id",
                "custo_combustivel",
                "custo_manutencao",
                "custo_pecas_itens",
                "custo_documental",
                "custo_total",
                "custo_por_hora",
                "custo_por_km",
                "participacao_percentual",
            ],
            base_name="custos",
            formato=formato,
        )

    async def exportar_jornadas(
        self,
        *,
        unidade_produtiva_id: uuid.UUID | None = None,
        periodo_dias: int | None = None,
        formato: str = "csv",
    ) -> ExportArtifact:
        resposta = await FrotaJornadaService(
            self.session,
            self.tenant_id,
        ).listar_jornadas(
            unidade_produtiva_id=unidade_produtiva_id,
            periodo_dias=periodo_dias,
        )
        rows = [
            {
                "equipamento_nome": item.equipamento_nome,
                "operador_nome": item.operador_nome or "",
                "unidade_produtiva_nome": item.unidade_produtiva_nome or "",
                "safra_nome": item.safra_nome or "",
                "talhao_nome": item.talhao_nome or "",
                "tipo_operacao": item.tipo_operacao,
                "status": item.status,
                "data_inicio": item.data_inicio.isoformat(),
                "data_fim": item.data_fim.isoformat() if item.data_fim else "",
                "horas_trabalhadas": item.horas_trabalhadas or "",
                "km_trabalhados": item.km_trabalhados or "",
                "custo_estimado": item.custo_estimado or "",
                "metrica_custo": item.metrica_custo,
                "aberta_por_nome": item.aberta_por_nome or "",
                "encerrada_por_nome": item.encerrada_por_nome or "",
            }
            for item in resposta.jornadas
        ]
        return self._build_export(
            rows=rows,
            headers=list(rows[0].keys()) if rows else [
                "equipamento_nome",
                "operador_nome",
                "unidade_produtiva_nome",
                "safra_nome",
                "talhao_nome",
                "tipo_operacao",
                "status",
                "data_inicio",
                "data_fim",
                "horas_trabalhadas",
                "km_trabalhados",
                "custo_estimado",
                "metrica_custo",
                "aberta_por_nome",
                "encerrada_por_nome",
            ],
            base_name="jornadas",
            formato=formato,
        )

    async def exportar_manutencoes(
        self,
        *,
        unidade_produtiva_id: uuid.UUID | None = None,
        periodo_dias: int | None = None,
        formato: str = "csv",
    ) -> ExportArtifact:
        equipamento_ids = [item.id for item in await self._listar_equipamentos(unidade_produtiva_id)]
        registros = await self._listar_registros_manutencao(equipamento_ids)
        if periodo_dias is not None:
            inicio = datetime.now(timezone.utc) - timedelta(days=periodo_dias)
            registros = [item for item in registros if item.data_realizacao >= inicio]
        equipamentos = {item.id: item for item in await self._listar_equipamentos(unidade_produtiva_id)}
        rows = [
            {
                "equipamento_nome": equipamentos.get(item.equipamento_id).nome if equipamentos.get(item.equipamento_id) else "",
                "tipo": item.tipo,
                "descricao": item.descricao,
                "data_realizacao": item.data_realizacao.isoformat(),
                "custo_total": float(item.custo_total or 0.0),
                "safra_id": str(item.safra_id) if item.safra_id else "",
                "talhao_id": str(item.talhao_id) if item.talhao_id else "",
                "executado_por_id": str(item.executado_por_id) if item.executado_por_id else "",
                "tecnico_responsavel": item.tecnico_responsavel or "",
            }
            for item in registros
        ]
        return self._build_export(
            rows=rows,
            headers=list(rows[0].keys()) if rows else [
                "equipamento_nome",
                "tipo",
                "descricao",
                "data_realizacao",
                "custo_total",
                "safra_id",
                "talhao_id",
                "executado_por_id",
                "tecnico_responsavel",
            ],
            base_name="manutencoes",
            formato=formato,
        )

    async def exportar_produtividade(
        self,
        *,
        unidade_produtiva_id: uuid.UUID | None = None,
        formato: str = "csv",
    ) -> ExportArtifact:
        registros = await FrotaAgriculturaService(
            self.session,
            self.tenant_id,
        )._montar_apontamentos_registros(unidade_produtiva_id=unidade_produtiva_id)
        rows = [
            {
                "equipamento_nome": item.equipamento_nome,
                "operador_nome": item.operador_nome or "",
                "safra_nome": item.safra_nome,
                "talhao_nome": item.talhao_nome,
                "operacao_nome": item.operacao_nome,
                "horas": item.horas,
                "hectares": item.hectares,
                "quantidade": item.quantidade,
                "custo_total": item.custo_total if item.custo_total is not None else "",
                "custo_por_ha": item.custo_por_ha if item.custo_por_ha is not None else "",
            }
            for item in registros
        ]
        return self._build_export(
            rows=rows,
            headers=list(rows[0].keys()) if rows else [
                "equipamento_nome",
                "operador_nome",
                "safra_nome",
                "talhao_nome",
                "operacao_nome",
                "horas",
                "hectares",
                "quantidade",
                "custo_total",
                "custo_por_ha",
            ],
            base_name="produtividade",
            formato=formato,
        )

    def _build_export(self, *, rows: list[dict[str, Any]], headers: list[str], base_name: str, formato: str) -> ExportArtifact:
        formato_normalizado = formato.lower().strip()
        if formato_normalizado == "xlsx":
            return ExportArtifact(
                filename=f"frota_{base_name}.xlsx",
                media_type=XLSX_MEDIA_TYPE,
                content=self._build_xlsx(headers, rows, sheet_name=base_name),
            )
        return ExportArtifact(
            filename=f"frota_{base_name}.csv",
            media_type=CSV_MEDIA_TYPE,
            content=self._build_csv(headers, rows).encode("utf-8"),
        )

    @staticmethod
    def _build_csv(headers: list[str], rows: list[dict[str, Any]]) -> str:
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=headers, extrasaction="ignore", delimiter=";")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: FrotaExportService._stringify_csv_value(row.get(key)) for key in headers})
        return output.getvalue()

    @staticmethod
    def _stringify_csv_value(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, datetime):
            return value.isoformat()
        return str(value)

    @staticmethod
    def _build_xlsx(headers: list[str], rows: list[dict[str, Any]], sheet_name: str) -> bytes:
        buffer = BytesIO()

        def _col_letter(index: int) -> str:
            letters = ""
            index += 1
            while index:
                index, remainder = divmod(index - 1, 26)
                letters = chr(65 + remainder) + letters
            return letters

        def _cell_xml(ref: str, value: Any) -> str:
            if value is None or value == "":
                return f'<c r="{ref}" t="inlineStr"><is><t></t></is></c>'
            if isinstance(value, bool):
                return f'<c r="{ref}" t="b"><v>{"1" if value else "0"}</v></c>'
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                return f'<c r="{ref}" t="n"><v>{value}</v></c>'
            text = escape(value.isoformat() if isinstance(value, datetime) else str(value))
            return f'<c r="{ref}" t="inlineStr"><is><t>{text}</t></is></c>'

        sheet_rows: list[str] = []
        all_rows = [dict(zip(headers, headers))]
        all_rows.extend(rows)
        for row_index, row in enumerate(all_rows, start=1):
            cells = []
            for col_index, header in enumerate(headers):
                value = row.get(header, header if row_index == 1 else "")
                cells.append(_cell_xml(f"{_col_letter(col_index)}{row_index}", value))
            sheet_rows.append(f'<row r="{row_index}">{"".join(cells)}</row>')

        worksheet = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            f'<sheetData>{"".join(sheet_rows)}</sheetData>'
            "</worksheet>"
        )
        workbook = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            f'<sheets><sheet name="{escape(sheet_name[:31])}" sheetId="1" r:id="rId1"/></sheets>'
            "</workbook>"
        )
        rels = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
            'Target="worksheets/sheet1.xml"/>'
            "</Relationships>"
        )
        root_rels = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
            'Target="xl/workbook.xml"/>'
            '<Relationship Id="rId2" '
            'Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" '
            'Target="docProps/core.xml"/>'
            '<Relationship Id="rId3" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" '
            'Target="docProps/app.xml"/>'
            "</Relationships>"
        )
        content_types = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            '<Override PartName="/docProps/core.xml" '
            'ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
            '<Override PartName="/docProps/app.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>'
            "</Types>"
        )
        core_props = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/" '
            'xmlns:dcterms="http://purl.org/dc/terms/" '
            'xmlns:dcmitype="http://purl.org/dc/dcmitype/" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
            "<dc:creator>AgroSaaS</dc:creator>"
            "<cp:lastModifiedBy>AgroSaaS</cp:lastModifiedBy>"
            "<dcterms:created xsi:type=\"dcterms:W3CDTF\">"
            f"{datetime.now(timezone.utc).isoformat()}"
            "</dcterms:created>"
            "</cp:coreProperties>"
        )
        app_props = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" '
            'xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">'
            "<Application>AgroSaaS</Application>"
            "</Properties>"
        )

        with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("[Content_Types].xml", content_types)
            zf.writestr("_rels/.rels", root_rels)
            zf.writestr("docProps/core.xml", core_props)
            zf.writestr("docProps/app.xml", app_props)
            zf.writestr("xl/workbook.xml", workbook)
            zf.writestr("xl/_rels/workbook.xml.rels", rels)
            zf.writestr("xl/worksheets/sheet1.xml", worksheet)

        return buffer.getvalue()
