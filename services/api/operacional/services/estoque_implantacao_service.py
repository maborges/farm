from __future__ import annotations

import csv
import hashlib
import io
import re
import unicodedata
from datetime import date, datetime, timezone
from difflib import get_close_matches
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.cadastros.models import ProdutoCatalogo
from core.exceptions import BusinessRuleError, EntityNotFoundError
from core.models.unidade_produtiva import UnidadeProdutiva
from core.services.audit_service import _serialize, write_audit_log
from operacional.models.estoque import Deposito, EstoqueMovimento
from operacional.models.estoque_implantacao import EstoqueImplantacaoItem, EstoqueImplantacaoSessao
from operacional.schemas.estoque_implantacao import (
    EstoqueImplantacaoAptidaoConfirmacaoResponse,
    EstoqueImplantacaoConfirmacaoRequest,
    EstoqueImplantacaoItemCorrecaoRequest,
    EstoqueImplantacaoItemListResponse,
    EstoqueImplantacaoItemResponse,
    EstoqueImplantacaoPreviewItem,
    EstoqueImplantacaoPreviewMessage,
    EstoqueImplantacaoPreviewResponse,
    EstoqueImplantacaoSessaoListResponse,
    EstoqueImplantacaoSessaoResponse,
)
from operacional.services.estoque_service import EstoqueService


TEMPLATE_HEADERS = [
    "produto_codigo",
    "produto_nome",
    "deposito_nome",
    "quantidade",
    "unidade",
    "custo_unitario",
    "lote",
    "validade",
    "observacoes",
]

ALLOWED_DESTINATIONS = set(TEMPLATE_HEADERS)
REQUIRED_DESTINATIONS = {"deposito_nome", "quantidade"}
PRODUCT_DESTINATIONS = {"produto_codigo", "produto_nome"}
SUPPORTED_ENCODINGS = ("utf-8-sig", "utf-8", "latin-1")
EDITABLE_SESSION_STATUSES = {"RASCUNHO", "PREVIEW_GERADO", "VALIDADO_COM_ERROS", "PRONTO_PARA_CORRECAO", "PRONTO_PARA_CONFIRMAR"}

ALIASES: dict[str, list[str]] = {
    "produto_nome": ["produto", "item", "descricao", "descrição", "nome_produto", "produto_nome"],
    "produto_codigo": ["codigo", "código", "cod_produto", "sku", "item_codigo", "produto_codigo"],
    "deposito_nome": ["deposito", "depósito", "almoxarifado", "local", "armazem", "armazém", "deposito_nome"],
    "quantidade": ["quantidade", "qtde", "qtd", "saldo", "saldo_atual"],
    "unidade": ["unidade", "un", "und", "medida"],
    "custo_unitario": ["custo", "custo_unitario", "valor", "valor_unitario", "preço", "preco"],
    "lote": ["lote", "numero_lote", "nº lote"],
    "validade": ["validade", "data_validade", "vencimento"],
    "observacoes": ["observacao", "observação", "obs", "comentarios"],
}

ALIAS_TO_DESTINATION = {
    alias_key: destination
    for destination, aliases in ALIASES.items()
    for alias_key in [*aliases, destination]
}


class EstoqueImplantacaoService:
    def __init__(
        self,
        session: AsyncSession,
        tenant_id: UUID,
        *,
        user_id: UUID | None = None,
        ip_address: str | None = None,
    ):
        self.session = session
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.ip_address = ip_address

    async def gerar_template_csv(self) -> str:
        output = io.StringIO()
        writer = csv.writer(output, delimiter=",", lineterminator="\n")
        writer.writerow(TEMPLATE_HEADERS)
        return output.getvalue()

    async def gerar_preview_csv(
        self,
        *,
        filename: str,
        content: bytes,
        mapping: dict[str, str] | None = None,
    ) -> EstoqueImplantacaoPreviewResponse:
        extensao = self._extrair_extensao(filename)
        if extensao != "csv":
            return self._response_com_erro_arquivo(
                filename=filename,
                extensao=extensao,
                codigo="extensao_invalida",
                mensagem="Arquivo invalido. Apenas CSV e aceito nesta etapa.",
            )

        if not content or not content.strip():
            return self._response_com_erro_arquivo(
                filename=filename,
                extensao=extensao,
                codigo="arquivo_vazio",
                mensagem="Arquivo vazio.",
            )

        decoded = self._decode_content(content)
        if decoded is None:
            return self._response_com_erro_arquivo(
                filename=filename,
                extensao=extensao,
                codigo="encoding_invalido",
                mensagem="Nao foi possivel ler o arquivo CSV com os encodings suportados.",
            )

        text, encoding = decoded
        if not text.strip():
            return self._response_com_erro_arquivo(
                filename=filename,
                extensao=extensao,
                codigo="arquivo_vazio",
                mensagem="Arquivo vazio.",
            )

        delimiter = self._detect_delimiter(text)
        reader = csv.reader(io.StringIO(text), delimiter=delimiter)

        try:
            raw_header = next(reader)
        except StopIteration:
            return self._response_com_erro_arquivo(
                filename=filename,
                extensao=extensao,
                codigo="cabecalho_ausente",
                mensagem="Cabecalho ausente.",
                encoding=encoding,
                delimiter=delimiter,
            )

        raw_headers = [self._sanitize_header(col) for col in raw_header if self._sanitize_header(col)]
        if not raw_headers:
            return self._response_com_erro_arquivo(
                filename=filename,
                extensao=extensao,
                codigo="cabecalho_ausente",
                mensagem="Cabecalho ausente.",
                encoding=encoding,
                delimiter=delimiter,
            )

        file_errors, mapping_used = self._build_mapping(raw_headers=raw_headers, explicit_mapping=mapping or {})
        structure_valid = self._is_minimum_structure_valid(mapping_used)
        if not structure_valid:
            missing = self._missing_minimum_destinations(mapping_used)
            if missing:
                file_errors.append(
                    EstoqueImplantacaoPreviewMessage(
                        campo="cabecalho",
                        codigo="colunas_obrigatorias_ausentes",
                        mensagem=f"Campos obrigatorios nao mapeados: {', '.join(missing)}.",
                    )
                )

        rows_reader = csv.DictReader(io.StringIO(text), fieldnames=raw_headers, delimiter=delimiter)
        next(rows_reader, None)

        produtos = self._filter_produtos_visiveis(await self._listar_produtos_tenant())
        depositos = self._filter_depositos_visiveis(await self._listar_depositos_tenant())

        itens: list[EstoqueImplantacaoPreviewItem] = []
        linhas_validas = 0
        linhas_com_erro = 0
        linhas_com_aviso = 0
        total_linhas = 0
        produtos_nao_encontrados: set[str] = set()
        depositos_nao_encontrados: set[str] = set()
        valor_total_estimado = 0.0

        for line_number, raw_row in enumerate(rows_reader, start=2):
            if self._row_is_empty(raw_row):
                continue

            total_linhas += 1
            item = self._build_preview_item(
                line_number=line_number,
                raw_row=raw_row,
                mapping_used=mapping_used,
                produtos=produtos,
                depositos=depositos,
            )
            itens.append(item)

            if item.status == "ERRO":
                linhas_com_erro += 1
            elif item.status == "AVISO":
                linhas_com_aviso += 1
            else:
                linhas_validas += 1

            produto_nao_encontrado = item.dados_normalizados.get("produto_nome_original") or item.dados_normalizados.get("produto_codigo_original")
            deposito_nao_encontrado = item.dados_normalizados.get("deposito_nome")

            if any(error.codigo == "produto_nao_encontrado" for error in item.erros) and produto_nao_encontrado:
                produtos_nao_encontrados.add(str(produto_nao_encontrado))
            if any(error.codigo == "deposito_nao_encontrado" for error in item.erros) and deposito_nao_encontrado:
                depositos_nao_encontrados.add(str(deposito_nao_encontrado))

            quantidade = item.dados_normalizados.get("quantidade")
            custo_unitario = item.dados_normalizados.get("custo_unitario")
            if isinstance(quantidade, (float, int)) and isinstance(custo_unitario, (float, int)):
                valor_total_estimado += float(quantidade) * float(custo_unitario)

        return EstoqueImplantacaoPreviewResponse(
            arquivo_nome=filename,
            extensao=extensao,
            encoding=encoding,
            delimitador=delimiter,
            estrutura_minima_valida=structure_valid and not any(error.codigo.startswith("mapeamento_") for error in file_errors),
            colunas_detectadas=raw_headers,
            mapeamento_utilizado=mapping_used,
            total_linhas=total_linhas,
            linhas_validas=linhas_validas,
            linhas_com_erro=linhas_com_erro,
            linhas_com_aviso=linhas_com_aviso,
            produtos_nao_encontrados=sorted(produtos_nao_encontrados),
            depositos_nao_encontrados=sorted(depositos_nao_encontrados),
            valor_total_estimado=round(valor_total_estimado, 2),
            itens=itens,
            erros_arquivo=file_errors,
        )

    async def criar_sessao_from_csv(
        self,
        *,
        filename: str,
        content: bytes,
        mapping: dict[str, str] | None,
        criado_por: UUID | None,
        unidade_produtiva_id: UUID | None = None,
    ) -> EstoqueImplantacaoSessaoResponse:
        if unidade_produtiva_id is not None:
            await self._validar_unidade_produtiva(unidade_produtiva_id)

        preview = await self.gerar_preview_csv(filename=filename, content=content, mapping=mapping)
        arquivo_hash = hashlib.sha256(content).hexdigest()
        sessao_existente = await self._buscar_sessao_duplicada_por_hash(arquivo_hash, unidade_produtiva_id)
        if sessao_existente is not None:
            raise BusinessRuleError(
                f"Ja existe uma sessao com o mesmo CSV para este tenant (sessao {sessao_existente.id}, status {sessao_existente.status})."
            )

        sessao = EstoqueImplantacaoSessao(
            tenant_id=self.tenant_id,
            unidade_produtiva_id=unidade_produtiva_id,
            arquivo_nome=filename,
            arquivo_hash=arquivo_hash,
            status="PREVIEW_GERADO",
            mapeamento_colunas=preview.mapeamento_utilizado,
            colunas_detectadas=preview.colunas_detectadas,
            total_linhas=preview.total_linhas,
            linhas_validas=preview.linhas_validas,
            linhas_com_erro=preview.linhas_com_erro,
            linhas_com_aviso=preview.linhas_com_aviso,
            valor_total_estimado=preview.valor_total_estimado,
            criado_por=criado_por,
        )
        await self._persist_session_record(sessao)

        itens = [
            EstoqueImplantacaoItem(
                sessao_id=sessao.id,
                tenant_id=self.tenant_id,
                numero_linha=item.numero_linha,
                payload_original=item.payload_original,
                dados_normalizados=item.dados_normalizados,
                produto_id_resolvido=self._parse_uuid(item.dados_normalizados.get("produto_id")),
                deposito_id_resolvido=self._parse_uuid(item.dados_normalizados.get("deposito_id")),
                status=item.status,
                erros=[err.model_dump() for err in item.erros],
                avisos=[warning.model_dump() for warning in item.avisos],
                sugestoes=item.sugestoes,
                ignorado=False,
            )
            for item in preview.itens
        ]
        await self._persist_item_records(itens)
        await self._recalcular_resumo_sessao(sessao)
        await self._write_session_audit(
            action="create_session",
            sessao=sessao,
            payload_before=None,
            payload_after={
                "sessao": _serialize(sessao),
                "resumo": self._build_session_summary(sessao),
                "total_itens": len(itens),
            },
        )
        return await self.obter_sessao(sessao.id)

    async def listar_sessoes(
        self,
        *,
        status: str | None = None,
        arquivo_nome: str | None = None,
        criado_em_inicio: datetime | None = None,
        criado_em_fim: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> EstoqueImplantacaoSessaoListResponse:
        sessoes = await self._list_sessions(
            status=status,
            arquivo_nome=arquivo_nome,
            criado_em_inicio=criado_em_inicio,
            criado_em_fim=criado_em_fim,
            limit=limit,
            offset=offset,
        )
        total = await self._count_sessions(
            status=status,
            arquivo_nome=arquivo_nome,
            criado_em_inicio=criado_em_inicio,
            criado_em_fim=criado_em_fim,
        )
        serialized = []
        for sessao in sessoes:
            serialized.append(self._serialize_session(sessao, itens=[], total_itens=await self._count_session_items(sessao.id), limit=0, offset=0))
        return EstoqueImplantacaoSessaoListResponse(itens=serialized, total=total, limit=limit, offset=offset)

    async def obter_sessao(
        self,
        sessao_id: UUID,
        *,
        status: str | None = None,
        somente_erros: bool = False,
        somente_avisos: bool = False,
        ignorado: bool | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> EstoqueImplantacaoSessaoResponse:
        sessao = await self._get_session_or_fail(sessao_id)
        itens = await self._list_session_items(
            sessao_id,
            status=status,
            somente_erros=somente_erros,
            somente_avisos=somente_avisos,
            ignorado=ignorado,
            limit=limit,
            offset=offset,
        )
        total_itens = await self._count_session_items(
            sessao_id,
            status=status,
            somente_erros=somente_erros,
            somente_avisos=somente_avisos,
            ignorado=ignorado,
        )
        return self._serialize_session(sessao, itens=itens, total_itens=total_itens, limit=limit, offset=offset)

    async def listar_itens_sessao(
        self,
        sessao_id: UUID,
        *,
        status: str | None = None,
        somente_erros: bool = False,
        somente_avisos: bool = False,
        ignorado: bool | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> EstoqueImplantacaoItemListResponse:
        await self._get_session_or_fail(sessao_id)
        itens = await self._list_session_items(
            sessao_id,
            status=status,
            somente_erros=somente_erros,
            somente_avisos=somente_avisos,
            ignorado=ignorado,
            limit=limit,
            offset=offset,
        )
        total = await self._count_session_items(
            sessao_id,
            status=status,
            somente_erros=somente_erros,
            somente_avisos=somente_avisos,
            ignorado=ignorado,
        )
        return EstoqueImplantacaoItemListResponse(
            itens=[self._serialize_item(item) for item in itens],
            total=total,
            limit=limit,
            offset=offset,
        )

    async def corrigir_item(
        self,
        sessao_id: UUID,
        item_id: UUID,
        data: EstoqueImplantacaoItemCorrecaoRequest,
    ) -> EstoqueImplantacaoSessaoResponse:
        sessao = await self._get_session_or_fail(sessao_id)
        self._ensure_session_editable(sessao)
        item = await self._get_item_or_fail(sessao_id, item_id)
        payload_before = self._serialize_item(item).model_dump(mode="json")

        changes = data.model_dump(exclude_unset=True)
        normalized = dict(item.dados_normalizados or {})

        if "produto_id_resolvido" in changes:
            produto_id = changes["produto_id_resolvido"]
            if produto_id is None:
                item.produto_id_resolvido = None
                normalized.pop("produto_id", None)
                normalized.pop("produto_nome_resolvido", None)
                normalized.pop("produto_codigo_resolvido", None)
            else:
                produto = await self._validar_produto_resolvido(produto_id)
                item.produto_id_resolvido = produto.id
                normalized["produto_id"] = str(produto.id)
                normalized["produto_nome_resolvido"] = produto.nome
                normalized["produto_codigo_resolvido"] = produto.codigo_interno or produto.sku

        if "deposito_id_resolvido" in changes:
            deposito_id = changes["deposito_id_resolvido"]
            if deposito_id is None:
                item.deposito_id_resolvido = None
                normalized.pop("deposito_id", None)
                normalized.pop("deposito_nome_resolvido", None)
                normalized.pop("unidade_produtiva_id", None)
            else:
                deposito = await self._validar_deposito_resolvido(deposito_id, sessao.unidade_produtiva_id)
                item.deposito_id_resolvido = deposito.id
                normalized["deposito_id"] = str(deposito.id)
                normalized["deposito_nome_resolvido"] = deposito.nome
                if getattr(deposito, "unidade_produtiva_id", None):
                    normalized["unidade_produtiva_id"] = str(deposito.unidade_produtiva_id)

        if "quantidade" in changes:
            normalized["quantidade"] = changes["quantidade"]
        if "custo_unitario" in changes:
            normalized["custo_unitario"] = changes["custo_unitario"]
        if "lote" in changes:
            normalized["lote"] = changes["lote"]
        if "validade" in changes:
            normalized["validade"] = changes["validade"].isoformat() if changes["validade"] else None
        if "observacoes" in changes:
            normalized["observacoes"] = changes["observacoes"]
        if "ignorado" in changes:
            item.ignorado = bool(changes["ignorado"])

        item.dados_normalizados = normalized
        await self._revalidar_item_persistido(item, mark_corrected=True)
        await self._recalcular_resumo_sessao(sessao)
        audit_action = "ignore_item" if item.ignorado else "correct_item"
        await self._write_item_audit(
            action=audit_action,
            item=item,
            payload_before=payload_before,
            payload_after=self._serialize_item(item).model_dump(mode="json"),
        )
        return await self.obter_sessao(sessao.id)

    async def cancelar_sessao(self, sessao_id: UUID) -> EstoqueImplantacaoSessaoResponse:
        sessao = await self._get_session_or_fail(sessao_id)
        if sessao.status == "CONFIRMADO":
            raise BusinessRuleError("Sessao confirmada nao pode ser cancelada.")
        if sessao.status == "CANCELADO":
            return await self.obter_sessao(sessao.id)
        payload_before = _serialize(sessao)
        sessao.status = "CANCELADO"
        sessao.cancelado_em = datetime.now(timezone.utc)
        await self.session.flush()
        await self._write_session_audit(
            action="cancel_session",
            sessao=sessao,
            payload_before=payload_before,
            payload_after=_serialize(sessao),
        )
        return await self.obter_sessao(sessao.id)

    async def revalidar_sessao(self, sessao_id: UUID) -> EstoqueImplantacaoSessaoResponse:
        sessao = await self._get_session_or_fail(sessao_id)
        self._ensure_session_editable(sessao)
        payload_before = {
            "sessao": _serialize(sessao),
            "resumo": self._build_session_summary(sessao),
        }
        itens = await self._list_all_session_items(sessao.id)
        for item in itens:
            await self._revalidar_item_persistido(item, mark_corrected=item.status in {"CORRIGIDO", "IGNORADO"})
        await self._recalcular_resumo_sessao(sessao)
        await self._write_session_audit(
            action="revalidate_session",
            sessao=sessao,
            payload_before=payload_before,
            payload_after={
                "sessao": _serialize(sessao),
                "resumo": self._build_session_summary(sessao),
            },
        )
        return await self.obter_sessao(sessao.id)

    async def validar_sessao_apta_para_confirmacao(
        self,
        sessao_id: UUID,
        tenant_id: UUID | None = None,
    ) -> EstoqueImplantacaoAptidaoConfirmacaoResponse:
        if tenant_id is not None and tenant_id != self.tenant_id:
            raise EntityNotFoundError("Sessao de implantacao nao encontrada.")
        sessao = await self._get_session_or_fail(sessao_id)
        itens = await self._list_all_session_items(sessao.id)

        erros_bloqueantes: list[str] = []
        avisos: list[str] = []
        total_itens_confirmaveis = 0
        valor_total_confirmavel = 0.0
        combos_confirmaveis: dict[tuple[UUID, UUID], int] = {}

        if sessao.status == "CANCELADO":
            erros_bloqueantes.append("Sessao cancelada nao pode ser confirmada.")
        if sessao.status == "CONFIRMADO":
            erros_bloqueantes.append("Sessao confirmada nao pode ser confirmada novamente.")

        for item in itens:
            if item.ignorado or item.status == "IGNORADO":
                continue
            dados = item.dados_normalizados or {}
            item_errors = item.erros or []
            item_warnings = item.avisos or []

            if any(error.get("codigo") for error in item_errors):
                erros_bloqueantes.append(f"Linha {item.numero_linha} possui erros pendentes.")
                continue
            if item.produto_id_resolvido is None:
                erros_bloqueantes.append(f"Linha {item.numero_linha} sem produto resolvido.")
                continue
            if item.deposito_id_resolvido is None:
                erros_bloqueantes.append(f"Linha {item.numero_linha} sem deposito resolvido.")
                continue
            quantidade = dados.get("quantidade")
            if not isinstance(quantidade, (int, float)) or float(quantidade) <= 0:
                erros_bloqueantes.append(f"Linha {item.numero_linha} sem quantidade valida.")
                continue

            if await self._existe_saldo_inicial_para_item(item):
                erros_bloqueantes.append(
                    f"Linha {item.numero_linha} conflita com SALDO_INICIAL existente para o mesmo produto e deposito."
                )
                continue

            combo = (item.produto_id_resolvido, item.deposito_id_resolvido)
            if combo in combos_confirmaveis:
                erros_bloqueantes.append(
                    f"Linha {item.numero_linha} duplica o produto/deposito da linha {combos_confirmaveis[combo]}."
                )
                continue
            combos_confirmaveis[combo] = item.numero_linha

            total_itens_confirmaveis += 1
            custo = dados.get("custo_unitario")
            if isinstance(custo, (int, float)):
                valor_total_confirmavel += float(quantidade) * float(custo)
            for warning in item_warnings:
                mensagem = warning.get("mensagem")
                if mensagem:
                    avisos.append(f"Linha {item.numero_linha}: {mensagem}")

        if total_itens_confirmaveis < 1:
            erros_bloqueantes.append("Sessao nao possui itens confirmaveis.")

        return EstoqueImplantacaoAptidaoConfirmacaoResponse(
            apta=not erros_bloqueantes,
            erros_bloqueantes=self._dedupe_strings(erros_bloqueantes),
            avisos=self._dedupe_strings(avisos),
            total_itens_confirmaveis=total_itens_confirmaveis,
            valor_total_confirmavel=round(valor_total_confirmavel, 2),
        )

    async def confirmar_sessao(
        self,
        sessao_id: UUID,
        data: EstoqueImplantacaoConfirmacaoRequest,
    ) -> EstoqueImplantacaoSessaoResponse:
        sessao = await self._get_session_or_fail(sessao_id, for_update=True)
        if sessao.status == "CANCELADO":
            raise BusinessRuleError("Sessao cancelada nao pode ser confirmada.")
        if sessao.status == "CONFIRMADO":
            raise BusinessRuleError("Sessao ja confirmada.")

        aptidao = await self.validar_sessao_apta_para_confirmacao(sessao.id, self.tenant_id)
        if aptidao.erros_bloqueantes:
            raise BusinessRuleError("Sessao possui bloqueios para confirmacao.")
        if aptidao.avisos and not data.confirmar_avisos:
            raise BusinessRuleError("Sessao possui avisos pendentes. Informe confirmar_avisos=true para prosseguir.")

        itens = await self._list_all_session_items(sessao.id)
        itens_confirmaveis = [item for item in itens if self._item_confirmavel(item)]
        if not itens_confirmaveis:
            raise BusinessRuleError("Sessao nao possui itens confirmaveis.")

        payload_before = {
            "sessao": _serialize(sessao),
            "resumo": self._build_session_summary(sessao),
        }

        estoque_service = self._build_estoque_service()
        movimentos_gerados = []
        total_ignorados = sum(1 for item in itens if item.ignorado or item.status == "IGNORADO")
        for item in itens_confirmaveis:
            dados = item.dados_normalizados or {}
            movimento = await estoque_service.registrar_saldo_inicial_implantacao(
                produto_id=item.produto_id_resolvido,
                deposito_id=item.deposito_id_resolvido,
                quantidade=float(dados.get("quantidade") or 0),
                custo_unitario=self._coerce_optional_numeric(dados.get("custo_unitario")),
                numero_lote_legado=self._coerce_optional_str(dados.get("lote")),
                validade_legado=self._coerce_optional_date(dados.get("validade")),
                unidade_produtiva_id=sessao.unidade_produtiva_id,
                origem_id=item.id,
                observacao=self._build_confirmacao_observacao(sessao_id=sessao.id, item=item, observacao=data.observacao),
            )
            movimentos_gerados.append(movimento)

        sessao.status = "CONFIRMADO"
        sessao.confirmado_em = datetime.now(timezone.utc)
        sessao.confirmado_por = self.user_id
        await self.session.flush()
        await self._write_session_audit(
            action="confirm_session",
            sessao=sessao,
            payload_before=payload_before,
            payload_after={
                "sessao": _serialize(sessao),
                "resumo": self._build_session_summary(sessao),
                "total_itens_confirmados": len(itens_confirmaveis),
                "total_ignorados": total_ignorados,
                "valor_total_implantado": aptidao.valor_total_confirmavel,
                "observacao": data.observacao,
                "movimentos_ids": [str(mov.id) for mov in movimentos_gerados],
            },
        )
        return await self.obter_sessao(sessao.id)

    def _build_preview_item(
        self,
        *,
        line_number: int,
        raw_row: dict[str, str | None],
        mapping_used: dict[str, str],
        produtos: list[ProdutoCatalogo],
        depositos: list[Deposito],
    ) -> EstoqueImplantacaoPreviewItem:
        payload_original = {key: (value or "").strip() for key, value in raw_row.items()}
        normalized_data = self._extract_normalized_data(raw_row=raw_row, mapping_used=mapping_used)
        errors: list[EstoqueImplantacaoPreviewMessage] = []
        warnings: list[EstoqueImplantacaoPreviewMessage] = []
        suggestions: dict[str, list[str]] = {}

        produto_codigo = (normalized_data.get("produto_codigo") or "").strip()
        produto_nome = (normalized_data.get("produto_nome") or "").strip()
        deposito_nome = (normalized_data.get("deposito_nome") or "").strip()
        quantidade_raw = (normalized_data.get("quantidade") or "").strip()
        custo_raw = (normalized_data.get("custo_unitario") or "").strip()

        normalized_data["produto_codigo_original"] = produto_codigo or None
        normalized_data["produto_nome_original"] = produto_nome or None

        if not produto_codigo and not produto_nome:
            errors.append(self._message(line_number=line_number, field="produto_nome", code="produto_ausente", message="Linha sem produto_nome e sem produto_codigo."))

        produto = None
        if produto_codigo:
            produto = self._find_product_by_code(produtos, produto_codigo)
            if produto is None:
                errors.append(self._message(line_number=line_number, field="produto_codigo", code="produto_nao_encontrado", message=f"Produto nao encontrado para o codigo '{produto_codigo}'."))  # noqa: E501
                suggestions["produto_codigo"] = self._suggest_product_codes(produtos, produto_codigo)
        elif produto_nome:
            produto = self._find_product_by_name(produtos, produto_nome)
            if produto is None:
                errors.append(self._message(line_number=line_number, field="produto_nome", code="produto_nao_encontrado", message=f"Produto nao encontrado para o nome '{produto_nome}'."))  # noqa: E501
                suggestions["produto_nome"] = self._suggest_product_names(produtos, produto_nome)

        if produto is not None:
            normalized_data["produto_id"] = str(produto.id)
            normalized_data["produto_nome_resolvido"] = produto.nome
            normalized_data["produto_codigo_resolvido"] = produto.codigo_interno or produto.sku

        if not deposito_nome:
            errors.append(self._message(line_number=line_number, field="deposito_nome", code="deposito_ausente", message="Linha sem deposito_nome."))
        else:
            deposito = self._find_deposito_by_name(depositos, deposito_nome)
            if deposito is None:
                errors.append(self._message(line_number=line_number, field="deposito_nome", code="deposito_nao_encontrado", message=f"Deposito nao encontrado para o nome '{deposito_nome}'."))  # noqa: E501
                suggestions["deposito_nome"] = self._suggest_deposito_names(depositos, deposito_nome)
            else:
                normalized_data["deposito_id"] = str(deposito.id)
                normalized_data["deposito_nome_resolvido"] = deposito.nome
                if getattr(deposito, "unidade_produtiva_id", None):
                    normalized_data["unidade_produtiva_id"] = str(deposito.unidade_produtiva_id)

        self._append_quantity_validation(errors=errors, normalized_data=normalized_data, raw_value=quantidade_raw, line_number=line_number)
        self._append_cost_validation(errors=errors, warnings=warnings, normalized_data=normalized_data, raw_value=custo_raw, line_number=line_number)

        status = "ERRO" if errors else ("AVISO" if warnings else "VALIDA")
        return EstoqueImplantacaoPreviewItem(
            numero_linha=line_number,
            status=status,
            payload_original=payload_original,
            dados_normalizados=normalized_data,
            erros=errors,
            avisos=warnings,
            sugestoes={key: value for key, value in suggestions.items() if value},
        )

    async def _revalidar_item_persistido(self, item: EstoqueImplantacaoItem, *, mark_corrected: bool) -> None:
        produtos = self._filter_produtos_visiveis(await self._listar_produtos_tenant())
        depositos = self._filter_depositos_visiveis(await self._listar_depositos_tenant())
        normalized = dict(item.dados_normalizados or {})

        errors: list[dict[str, Any]] = []
        warnings: list[dict[str, Any]] = []
        suggestions: dict[str, list[str]] = {}

        produto_codigo = (normalized.get("produto_codigo_original") or normalized.get("produto_codigo") or "").strip()
        produto_nome = (normalized.get("produto_nome_original") or normalized.get("produto_nome") or "").strip()
        deposito_nome = (normalized.get("deposito_nome") or "").strip()
        quantidade_raw = normalized.get("quantidade")
        custo_raw = normalized.get("custo_unitario")

        produto = None
        if item.produto_id_resolvido is not None:
            try:
                produto = await self._validar_produto_resolvido(item.produto_id_resolvido)
            except BusinessRuleError:
                item.produto_id_resolvido = None
                normalized.pop("produto_id", None)
                normalized.pop("produto_nome_resolvido", None)
                normalized.pop("produto_codigo_resolvido", None)
                errors.append(self._message(line_number=item.numero_linha, field="produto_id_resolvido", code="produto_resolvido_invalido", message="Produto resolvido nao pertence mais ao tenant ou esta inativo.").model_dump())
        elif produto_codigo:
            produto = self._find_product_by_code(produtos, produto_codigo)
            if produto is None:
                errors.append(self._message(line_number=item.numero_linha, field="produto_codigo", code="produto_nao_encontrado", message=f"Produto nao encontrado para o codigo '{produto_codigo}'." ).model_dump())  # noqa: E501
                suggestions["produto_codigo"] = self._suggest_product_codes(produtos, produto_codigo)
        elif produto_nome:
            produto = self._find_product_by_name(produtos, produto_nome)
            if produto is None:
                errors.append(self._message(line_number=item.numero_linha, field="produto_nome", code="produto_nao_encontrado", message=f"Produto nao encontrado para o nome '{produto_nome}'." ).model_dump())  # noqa: E501
                suggestions["produto_nome"] = self._suggest_product_names(produtos, produto_nome)
        else:
            errors.append(self._message(line_number=item.numero_linha, field="produto_nome", code="produto_ausente", message="Linha sem produto_nome e sem produto_codigo.").model_dump())

        if produto is not None:
            item.produto_id_resolvido = produto.id
            normalized["produto_id"] = str(produto.id)
            normalized["produto_nome_resolvido"] = produto.nome
            normalized["produto_codigo_resolvido"] = produto.codigo_interno or produto.sku

        deposito = None
        if item.deposito_id_resolvido is not None:
            try:
                deposito = await self._validar_deposito_resolvido(item.deposito_id_resolvido)
            except BusinessRuleError:
                item.deposito_id_resolvido = None
                normalized.pop("deposito_id", None)
                normalized.pop("deposito_nome_resolvido", None)
                normalized.pop("unidade_produtiva_id", None)
                errors.append(self._message(line_number=item.numero_linha, field="deposito_id_resolvido", code="deposito_resolvido_invalido", message="Deposito resolvido nao pertence mais ao tenant ou esta inativo.").model_dump())
        elif deposito_nome:
            deposito = self._find_deposito_by_name(depositos, deposito_nome)
            if deposito is None:
                errors.append(self._message(line_number=item.numero_linha, field="deposito_nome", code="deposito_nao_encontrado", message=f"Deposito nao encontrado para o nome '{deposito_nome}'." ).model_dump())  # noqa: E501
                suggestions["deposito_nome"] = self._suggest_deposito_names(depositos, deposito_nome)
        else:
            errors.append(self._message(line_number=item.numero_linha, field="deposito_nome", code="deposito_ausente", message="Linha sem deposito_nome.").model_dump())

        if deposito is not None:
            item.deposito_id_resolvido = deposito.id
            normalized["deposito_id"] = str(deposito.id)
            normalized["deposito_nome_resolvido"] = deposito.nome
            if getattr(deposito, "unidade_produtiva_id", None):
                normalized["unidade_produtiva_id"] = str(deposito.unidade_produtiva_id)

        try:
            quantidade_val = self._coerce_numeric_value(quantidade_raw)
            if quantidade_val <= 0:
                raise ValueError
            normalized["quantidade"] = quantidade_val
        except ValueError:
            errors.append(self._message(line_number=item.numero_linha, field="quantidade", code="quantidade_invalida", message="Quantidade invalida. Informe valor numerico maior que zero.").model_dump())
            normalized["quantidade"] = None

        if custo_raw in (None, ""):
            warnings.append(self._message(line_number=item.numero_linha, field="custo_unitario", code="custo_unitario_ausente", message="Custo unitario ausente. A linha pode seguir para correcao futura.").model_dump())
            normalized["custo_unitario"] = None
        else:
            try:
                custo_val = self._coerce_numeric_value(custo_raw)
                if custo_val < 0:
                    raise ValueError
                normalized["custo_unitario"] = custo_val
            except ValueError:
                errors.append(self._message(line_number=item.numero_linha, field="custo_unitario", code="custo_unitario_invalido", message="Custo unitario invalido. Informe valor numerico maior ou igual a zero.").model_dump())
                normalized["custo_unitario"] = None

        item.dados_normalizados = normalized
        item.erros = errors
        item.avisos = warnings
        item.sugestoes = suggestions

        if item.ignorado:
            item.status = "IGNORADO"
        elif errors:
            item.status = "ERRO"
        elif warnings:
            item.status = "AVISO"
        else:
            item.status = "CORRIGIDO" if mark_corrected else "VALIDA"

    async def _recalcular_resumo_sessao(self, sessao: EstoqueImplantacaoSessao) -> None:
        itens = await self._list_all_session_items(sessao.id)
        sessao.total_linhas = len(itens)
        sessao.linhas_validas = sum(1 for item in itens if item.status in {"VALIDA", "CORRIGIDO"})
        sessao.linhas_com_erro = sum(1 for item in itens if item.status == "ERRO")
        sessao.linhas_com_aviso = sum(1 for item in itens if item.status == "AVISO")
        sessao.valor_total_estimado = round(
            sum(
                float(item.dados_normalizados.get("quantidade") or 0) * float(item.dados_normalizados.get("custo_unitario") or 0)
                for item in itens
                if item.status in {"VALIDA", "CORRIGIDO", "AVISO"}
            ),
            2,
        )
        if sessao.status not in {"CANCELADO", "CONFIRMADO"}:
            if sessao.linhas_com_erro > 0:
                sessao.status = "VALIDADO_COM_ERROS"
            elif sessao.linhas_com_aviso > 0:
                sessao.status = "PRONTO_PARA_CORRECAO"
            else:
                sessao.status = "PRONTO_PARA_CONFIRMAR"
        await self.session.flush()

    def _serialize_session(
        self,
        sessao: EstoqueImplantacaoSessao,
        *,
        itens: list[EstoqueImplantacaoItem],
        total_itens: int,
        limit: int,
        offset: int,
    ) -> EstoqueImplantacaoSessaoResponse:
        return EstoqueImplantacaoSessaoResponse(
            id=sessao.id,
            tenant_id=sessao.tenant_id,
            unidade_produtiva_id=sessao.unidade_produtiva_id,
            arquivo_nome=sessao.arquivo_nome,
            arquivo_hash=sessao.arquivo_hash,
            status=sessao.status,
            mapeamento_colunas=sessao.mapeamento_colunas or {},
            colunas_detectadas=sessao.colunas_detectadas or [],
            total_linhas=sessao.total_linhas,
            linhas_validas=sessao.linhas_validas,
            linhas_com_erro=sessao.linhas_com_erro,
            linhas_com_aviso=sessao.linhas_com_aviso,
            valor_total_estimado=float(sessao.valor_total_estimado or 0),
            criado_por=sessao.criado_por,
            criado_em=sessao.criado_em,
            atualizado_em=sessao.atualizado_em,
            cancelado_em=sessao.cancelado_em,
            confirmado_em=sessao.confirmado_em,
            confirmado_por=sessao.confirmado_por,
            total_itens=total_itens,
            limit=limit,
            offset=offset,
            itens=[self._serialize_item(item) for item in itens],
        )

    def _serialize_item(self, item: EstoqueImplantacaoItem) -> EstoqueImplantacaoItemResponse:
        return EstoqueImplantacaoItemResponse(
            id=item.id,
            numero_linha=item.numero_linha,
            status=item.status,
            ignorado=item.ignorado,
            payload_original=item.payload_original or {},
            dados_normalizados=item.dados_normalizados or {},
            produto_id_resolvido=item.produto_id_resolvido,
            deposito_id_resolvido=item.deposito_id_resolvido,
            erros=item.erros or [],
            avisos=item.avisos or [],
            sugestoes=item.sugestoes or {},
            criado_em=item.criado_em,
            atualizado_em=item.atualizado_em,
        )

    def _build_session_summary(self, sessao: EstoqueImplantacaoSessao) -> dict[str, Any]:
        return {
            "status": sessao.status,
            "total_linhas": sessao.total_linhas,
            "linhas_validas": sessao.linhas_validas,
            "linhas_com_erro": sessao.linhas_com_erro,
            "linhas_com_aviso": sessao.linhas_com_aviso,
            "valor_total_estimado": float(sessao.valor_total_estimado or 0),
        }

    async def _persist_session_record(self, sessao: EstoqueImplantacaoSessao) -> None:
        self.session.add(sessao)
        await self.session.flush()
        await self.session.refresh(sessao)

    async def _persist_item_records(self, itens: list[EstoqueImplantacaoItem]) -> None:
        for item in itens:
            self.session.add(item)
        await self.session.flush()

    async def _get_session_or_fail(self, sessao_id: UUID, *, for_update: bool = False) -> EstoqueImplantacaoSessao:
        stmt = select(EstoqueImplantacaoSessao).where(
            EstoqueImplantacaoSessao.id == sessao_id,
            EstoqueImplantacaoSessao.tenant_id == self.tenant_id,
        )
        if for_update:
            stmt = stmt.with_for_update()
        sessao = (await self.session.execute(stmt)).scalars().first()
        if not sessao:
            raise EntityNotFoundError("Sessao de implantacao nao encontrada.")
        return sessao

    async def _get_item_or_fail(self, sessao_id: UUID, item_id: UUID) -> EstoqueImplantacaoItem:
        stmt = select(EstoqueImplantacaoItem).where(
            EstoqueImplantacaoItem.id == item_id,
            EstoqueImplantacaoItem.sessao_id == sessao_id,
            EstoqueImplantacaoItem.tenant_id == self.tenant_id,
        )
        item = (await self.session.execute(stmt)).scalars().first()
        if not item:
            raise EntityNotFoundError("Item de implantacao nao encontrado.")
        return item

    async def _list_sessions(
        self,
        *,
        status: str | None,
        arquivo_nome: str | None,
        criado_em_inicio: datetime | None,
        criado_em_fim: datetime | None,
        limit: int,
        offset: int,
    ) -> list[EstoqueImplantacaoSessao]:
        stmt = self._build_sessions_query(
            status=status,
            arquivo_nome=arquivo_nome,
            criado_em_inicio=criado_em_inicio,
            criado_em_fim=criado_em_fim,
        ).order_by(EstoqueImplantacaoSessao.criado_em.desc()).offset(offset).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    async def _count_sessions(
        self,
        *,
        status: str | None,
        arquivo_nome: str | None,
        criado_em_inicio: datetime | None,
        criado_em_fim: datetime | None,
    ) -> int:
        stmt = select(func.count()).select_from(
            self._build_sessions_query(
                status=status,
                arquivo_nome=arquivo_nome,
                criado_em_inicio=criado_em_inicio,
                criado_em_fim=criado_em_fim,
            ).subquery()
        )
        return int((await self.session.execute(stmt)).scalar_one())

    def _build_sessions_query(
        self,
        *,
        status: str | None,
        arquivo_nome: str | None,
        criado_em_inicio: datetime | None,
        criado_em_fim: datetime | None,
    ):
        stmt = select(EstoqueImplantacaoSessao).where(EstoqueImplantacaoSessao.tenant_id == self.tenant_id)
        if status:
            stmt = stmt.where(EstoqueImplantacaoSessao.status == status)
        if arquivo_nome:
            stmt = stmt.where(EstoqueImplantacaoSessao.arquivo_nome.ilike(f"%{arquivo_nome.strip()}%"))
        if criado_em_inicio:
            stmt = stmt.where(EstoqueImplantacaoSessao.criado_em >= criado_em_inicio)
        if criado_em_fim:
            stmt = stmt.where(EstoqueImplantacaoSessao.criado_em <= criado_em_fim)
        return stmt

    async def _list_session_items(
        self,
        sessao_id: UUID,
        *,
        status: str | None = None,
        somente_erros: bool = False,
        somente_avisos: bool = False,
        ignorado: bool | None = None,
        limit: int,
        offset: int,
    ) -> list[EstoqueImplantacaoItem]:
        stmt = self._build_session_items_query(
            sessao_id,
            status=status,
            somente_erros=somente_erros,
            somente_avisos=somente_avisos,
            ignorado=ignorado,
        ).order_by(EstoqueImplantacaoItem.numero_linha.asc()).offset(offset).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    async def _list_all_session_items(self, sessao_id: UUID) -> list[EstoqueImplantacaoItem]:
        stmt = (
            select(EstoqueImplantacaoItem)
            .where(
                EstoqueImplantacaoItem.sessao_id == sessao_id,
                EstoqueImplantacaoItem.tenant_id == self.tenant_id,
            )
            .order_by(EstoqueImplantacaoItem.numero_linha.asc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    def _build_session_items_query(
        self,
        sessao_id: UUID,
        *,
        status: str | None = None,
        somente_erros: bool = False,
        somente_avisos: bool = False,
        ignorado: bool | None = None,
    ):
        stmt = select(EstoqueImplantacaoItem).where(
            EstoqueImplantacaoItem.sessao_id == sessao_id,
            EstoqueImplantacaoItem.tenant_id == self.tenant_id,
        )
        if status:
            stmt = stmt.where(EstoqueImplantacaoItem.status == status)
        if somente_erros:
            stmt = stmt.where(EstoqueImplantacaoItem.status == "ERRO")
        if somente_avisos:
            stmt = stmt.where(EstoqueImplantacaoItem.status == "AVISO")
        if ignorado is not None:
            stmt = stmt.where(EstoqueImplantacaoItem.ignorado == ignorado)
        return stmt

    async def _count_session_items(
        self,
        sessao_id: UUID,
        *,
        status: str | None = None,
        somente_erros: bool = False,
        somente_avisos: bool = False,
        ignorado: bool | None = None,
    ) -> int:
        stmt = select(func.count()).select_from(
            self._build_session_items_query(
                sessao_id,
                status=status,
                somente_erros=somente_erros,
                somente_avisos=somente_avisos,
                ignorado=ignorado,
            ).subquery()
        )
        return int((await self.session.execute(stmt)).scalar_one())

    async def _write_session_audit(
        self,
        *,
        action: str,
        sessao: EstoqueImplantacaoSessao,
        payload_before: dict[str, Any] | None,
        payload_after: dict[str, Any] | None,
    ) -> None:
        await write_audit_log(
            self.session,
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            action=action,
            resource=EstoqueImplantacaoSessao.__tablename__,
            resource_id=sessao.id,
            payload_before=payload_before,
            payload_after=payload_after,
            ip_address=self.ip_address,
        )

    async def _write_item_audit(
        self,
        *,
        action: str,
        item: EstoqueImplantacaoItem,
        payload_before: dict[str, Any] | None,
        payload_after: dict[str, Any] | None,
    ) -> None:
        await write_audit_log(
            self.session,
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            action=action,
            resource=EstoqueImplantacaoItem.__tablename__,
            resource_id=item.id,
            payload_before=payload_before,
            payload_after=payload_after,
            ip_address=self.ip_address,
        )

    def _build_estoque_service(self) -> EstoqueService:
        return EstoqueService(self.session, self.tenant_id)

    async def _existe_saldo_inicial_para_item(self, item: EstoqueImplantacaoItem) -> bool:
        if item.produto_id_resolvido is None or item.deposito_id_resolvido is None:
            return False
        stmt = select(EstoqueMovimento.id).where(
            EstoqueMovimento.tenant_id == self.tenant_id,
            EstoqueMovimento.produto_id == item.produto_id_resolvido,
            EstoqueMovimento.deposito_id == item.deposito_id_resolvido,
            EstoqueMovimento.tipo_movimento == "SALDO_INICIAL",
        ).limit(1)
        return (await self.session.execute(stmt)).scalar_one_or_none() is not None

    @staticmethod
    def _item_confirmavel(item: EstoqueImplantacaoItem) -> bool:
        if item.ignorado or item.status == "IGNORADO":
            return False
        if item.produto_id_resolvido is None or item.deposito_id_resolvido is None:
            return False
        if item.erros:
            return False
        quantidade = (item.dados_normalizados or {}).get("quantidade")
        return isinstance(quantidade, (int, float)) and float(quantidade) > 0

    @staticmethod
    def _coerce_optional_numeric(value: Any) -> float | None:
        if value in (None, "", "None"):
            return None
        return float(value)

    @staticmethod
    def _coerce_optional_str(value: Any) -> str | None:
        normalized = (str(value).strip() if value is not None else "")
        return normalized or None

    @staticmethod
    def _coerce_optional_date(value: Any) -> date | None:
        if value in (None, "", "None"):
            return None
        if isinstance(value, date):
            return value
        return date.fromisoformat(str(value))

    def _build_confirmacao_observacao(
        self,
        *,
        sessao_id: UUID,
        item: EstoqueImplantacaoItem,
        observacao: str | None,
    ) -> str:
        partes = [
            f"Implantacao assistida sessao {sessao_id}",
            f"linha {item.numero_linha}",
        ]
        if observacao:
            partes.append(observacao.strip())
        return " | ".join(partes)

    async def _validar_produto_resolvido(self, produto_id: UUID) -> ProdutoCatalogo:
        stmt = select(ProdutoCatalogo).where(
            ProdutoCatalogo.id == produto_id,
            ProdutoCatalogo.tenant_id == self.tenant_id,
            ProdutoCatalogo.ativo == True,
        )
        produto = (await self.session.execute(stmt)).scalars().first()
        if not produto:
            raise BusinessRuleError("Produto informado nao pertence ao tenant ou esta inativo.")
        return produto

    async def _validar_deposito_resolvido(
        self,
        deposito_id: UUID,
        unidade_produtiva_id: UUID | None = None,
    ) -> Deposito:
        stmt = select(Deposito).where(
            Deposito.id == deposito_id,
            Deposito.tenant_id == self.tenant_id,
            Deposito.ativo == True,
        )
        deposito = (await self.session.execute(stmt)).scalars().first()
        if not deposito:
            raise BusinessRuleError("Deposito informado nao pertence ao tenant ou esta inativo.")
        if (
            getattr(deposito, "unidade_produtiva_id", None) is not None
            and unidade_produtiva_id is not None
            and deposito.unidade_produtiva_id != unidade_produtiva_id
        ):
            raise BusinessRuleError("Deposito informado pertence a outra unidade produtiva da sessao.")
        return deposito

    async def _validar_unidade_produtiva(self, unidade_produtiva_id: UUID) -> UnidadeProdutiva:
        stmt = select(UnidadeProdutiva).where(
            UnidadeProdutiva.id == unidade_produtiva_id,
            UnidadeProdutiva.tenant_id == self.tenant_id,
            UnidadeProdutiva.ativo == True,
        )
        unidade = (await self.session.execute(stmt)).scalars().first()
        if not unidade:
            raise BusinessRuleError("Unidade produtiva nao localizada para o tenant.")
        return unidade

    def _ensure_session_editable(self, sessao: EstoqueImplantacaoSessao) -> None:
        if sessao.status not in EDITABLE_SESSION_STATUSES:
            raise BusinessRuleError("Sessao nao pode mais ser alterada.")

    def _extract_normalized_data(self, *, raw_row: dict[str, str | None], mapping_used: dict[str, str]) -> dict[str, Any]:
        normalized_data: dict[str, Any] = {destination: None for destination in TEMPLATE_HEADERS}
        for source, destination in mapping_used.items():
            normalized_data[destination] = (raw_row.get(source) or "").strip()
        return normalized_data

    async def _buscar_sessao_duplicada_por_hash(
        self,
        arquivo_hash: str,
        unidade_produtiva_id: UUID | None,
    ) -> EstoqueImplantacaoSessao | None:
        stmt = select(EstoqueImplantacaoSessao).where(
            EstoqueImplantacaoSessao.tenant_id == self.tenant_id,
            EstoqueImplantacaoSessao.arquivo_hash == arquivo_hash,
            EstoqueImplantacaoSessao.status != "CANCELADO",
        )
        if unidade_produtiva_id is None:
            stmt = stmt.where(EstoqueImplantacaoSessao.unidade_produtiva_id.is_(None))
        else:
            stmt = stmt.where(EstoqueImplantacaoSessao.unidade_produtiva_id == unidade_produtiva_id)
        stmt = stmt.order_by(EstoqueImplantacaoSessao.criado_em.desc()).limit(1)
        return (await self.session.execute(stmt)).scalars().first()


    def _build_mapping(
        self,
        *,
        raw_headers: list[str],
        explicit_mapping: dict[str, str],
    ) -> tuple[list[EstoqueImplantacaoPreviewMessage], dict[str, str]]:
        errors: list[EstoqueImplantacaoPreviewMessage] = []
        mapping_used: dict[str, str] = {}
        used_destinations: set[str] = set()
        normalized_headers = {self._normalize_alias_key(header): header for header in raw_headers}

        for raw_source, raw_destination in explicit_mapping.items():
            source = self._sanitize_header(raw_source)
            destination = self._sanitize_header(raw_destination)
            if not source or source not in raw_headers:
                errors.append(EstoqueImplantacaoPreviewMessage(campo="mapeamento", codigo="mapeamento_origem_ausente", mensagem=f"Coluna de origem '{raw_source}' nao encontrada no arquivo."))
                continue
            if destination not in ALLOWED_DESTINATIONS:
                errors.append(EstoqueImplantacaoPreviewMessage(campo="mapeamento", codigo="mapeamento_destino_invalido", mensagem=f"Destino '{raw_destination}' nao e suportado."))
                continue
            if destination in used_destinations:
                errors.append(EstoqueImplantacaoPreviewMessage(campo="mapeamento", codigo="mapeamento_destino_duplicado", mensagem=f"Destino '{destination}' foi informado mais de uma vez."))
                continue
            mapping_used[source] = destination
            used_destinations.add(destination)

        for alias_key, original_header in normalized_headers.items():
            if original_header in mapping_used:
                continue
            destination = ALIAS_TO_DESTINATION.get(alias_key)
            if destination is None or destination in used_destinations:
                continue
            mapping_used[original_header] = destination
            used_destinations.add(destination)

        return errors, mapping_used

    def _is_minimum_structure_valid(self, mapping_used: dict[str, str]) -> bool:
        destinations = set(mapping_used.values())
        return REQUIRED_DESTINATIONS.issubset(destinations) and bool(PRODUCT_DESTINATIONS.intersection(destinations))

    def _missing_minimum_destinations(self, mapping_used: dict[str, str]) -> list[str]:
        destinations = set(mapping_used.values())
        missing = sorted(REQUIRED_DESTINATIONS.difference(destinations))
        if not PRODUCT_DESTINATIONS.intersection(destinations):
            missing.append("produto_nome ou produto_codigo")
        return missing

    async def _listar_produtos_tenant(self) -> list[ProdutoCatalogo]:
        stmt = select(ProdutoCatalogo).where(
            ProdutoCatalogo.tenant_id == self.tenant_id,
            ProdutoCatalogo.ativo == True,
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def _listar_depositos_tenant(self) -> list[Deposito]:
        stmt = select(Deposito).where(
            Deposito.tenant_id == self.tenant_id,
            Deposito.ativo == True,
        )
        return list((await self.session.execute(stmt)).scalars().all())

    def _filter_produtos_visiveis(self, produtos: list[ProdutoCatalogo]) -> list[ProdutoCatalogo]:
        return [produto for produto in produtos if getattr(produto, "tenant_id", None) == self.tenant_id and getattr(produto, "ativo", True)]

    def _filter_depositos_visiveis(self, depositos: list[Deposito]) -> list[Deposito]:
        return [deposito for deposito in depositos if getattr(deposito, "tenant_id", None) == self.tenant_id and getattr(deposito, "ativo", True)]

    def _find_product_by_code(self, produtos: list[ProdutoCatalogo], value: str) -> ProdutoCatalogo | None:
        target = self._normalize_value(value)
        for produto in produtos:
            codigo_interno = self._normalize_value(getattr(produto, "codigo_interno", None))
            sku = self._normalize_value(getattr(produto, "sku", None))
            if target and target in {codigo_interno, sku}:
                return produto
        return None

    def _find_product_by_name(self, produtos: list[ProdutoCatalogo], value: str) -> ProdutoCatalogo | None:
        target = self._normalize_value(value)
        for produto in produtos:
            if target and self._normalize_value(produto.nome) == target:
                return produto
        return None

    def _find_deposito_by_name(self, depositos: list[Deposito], value: str) -> Deposito | None:
        target = self._normalize_value(value)
        for deposito in depositos:
            if target and self._normalize_value(deposito.nome) == target:
                return deposito
        return None

    def _suggest_product_codes(self, produtos: list[ProdutoCatalogo], value: str) -> list[str]:
        universe = sorted({candidate for produto in produtos for candidate in [getattr(produto, "codigo_interno", None), getattr(produto, "sku", None)] if candidate})
        return self._suggest_matches(universe, value)

    def _suggest_product_names(self, produtos: list[ProdutoCatalogo], value: str) -> list[str]:
        universe = sorted({produto.nome for produto in produtos if produto.nome})
        return self._suggest_matches(universe, value)

    def _suggest_deposito_names(self, depositos: list[Deposito], value: str) -> list[str]:
        universe = sorted({deposito.nome for deposito in depositos if deposito.nome})
        return self._suggest_matches(universe, value)

    def _suggest_matches(self, universe: list[str], value: str) -> list[str]:
        normalized_lookup = {self._normalize_value(item): item for item in universe}
        matches = get_close_matches(self._normalize_value(value), list(normalized_lookup.keys()), n=3, cutoff=0.5)
        return [normalized_lookup[match] for match in matches]

    def _append_quantity_validation(
        self,
        *,
        errors: list[EstoqueImplantacaoPreviewMessage],
        normalized_data: dict[str, Any],
        raw_value: str,
        line_number: int,
    ) -> None:
        try:
            quantidade = self._parse_decimal(raw_value)
            if quantidade <= 0:
                raise ValueError
            normalized_data["quantidade"] = quantidade
        except ValueError:
            errors.append(self._message(line_number=line_number, field="quantidade", code="quantidade_invalida", message="Quantidade invalida. Informe valor numerico maior que zero."))
            normalized_data["quantidade"] = None

    def _append_cost_validation(
        self,
        *,
        errors: list[EstoqueImplantacaoPreviewMessage],
        warnings: list[EstoqueImplantacaoPreviewMessage],
        normalized_data: dict[str, Any],
        raw_value: str,
        line_number: int,
    ) -> None:
        if not raw_value:
            warnings.append(self._message(line_number=line_number, field="custo_unitario", code="custo_unitario_ausente", message="Custo unitario ausente. A linha pode seguir para correcao futura."))
            normalized_data["custo_unitario"] = None
            return
        try:
            custo = self._parse_decimal(raw_value)
            if custo < 0:
                raise ValueError
            normalized_data["custo_unitario"] = custo
        except ValueError:
            errors.append(self._message(line_number=line_number, field="custo_unitario", code="custo_unitario_invalido", message="Custo unitario invalido. Informe valor numerico maior ou igual a zero."))
            normalized_data["custo_unitario"] = None

    @staticmethod
    def _message(*, line_number: int, field: str, code: str, message: str) -> EstoqueImplantacaoPreviewMessage:
        return EstoqueImplantacaoPreviewMessage(linha=line_number, campo=field, codigo=code, mensagem=message)

    @staticmethod
    def _parse_decimal(value: str) -> float:
        normalized = value.strip()
        if not normalized:
            raise ValueError
        if "," in normalized and "." in normalized:
            normalized = normalized.replace(".", "").replace(",", ".")
        elif "," in normalized:
            normalized = normalized.replace(",", ".")
        return float(normalized)

    def _coerce_numeric_value(self, value: Any) -> float:
        if isinstance(value, (int, float)):
            return float(value)
        return self._parse_decimal(str(value))

    @staticmethod
    def _parse_uuid(value: Any) -> UUID | None:
        if value in (None, "", "None"):
            return None
        try:
            return UUID(str(value))
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _row_is_empty(row: dict[str, str | None]) -> bool:
        return all(not (value or "").strip() for value in row.values())

    @staticmethod
    def _extract_extension_value(filename: str) -> str:
        return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    def _extrair_extensao(self, filename: str) -> str:
        return self._extract_extension_value(filename or "")

    @staticmethod
    def _sanitize_header(value: str | None) -> str:
        return (value or "").strip()

    @staticmethod
    def _normalize_alias_key(value: str | None) -> str:
        ascii_value = unicodedata.normalize("NFKD", (value or "").strip().lower()).encode("ascii", "ignore").decode("ascii")
        collapsed = re.sub(r"[^a-z0-9]+", "_", ascii_value)
        return collapsed.strip("_")

    @classmethod
    def _normalize_value(cls, value: str | None) -> str:
        return cls._normalize_alias_key(value)

    @staticmethod
    def _dedupe_strings(values: list[str]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for value in values:
            if value not in seen:
                seen.add(value)
                result.append(value)
        return result

    @staticmethod
    def _detect_delimiter(text: str) -> str:
        sample = text[:2048]
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;")
            return dialect.delimiter
        except csv.Error:
            return ","

    @staticmethod
    def _decode_content(content: bytes) -> tuple[str, str] | None:
        for encoding in SUPPORTED_ENCODINGS:
            try:
                return content.decode(encoding), encoding
            except UnicodeDecodeError:
                continue
        return None

    @staticmethod
    def _response_com_erro_arquivo(
        *,
        filename: str,
        extensao: str,
        codigo: str,
        mensagem: str,
        encoding: str | None = None,
        delimiter: str | None = None,
    ) -> EstoqueImplantacaoPreviewResponse:
        return EstoqueImplantacaoPreviewResponse(
            arquivo_nome=filename,
            extensao=extensao,
            encoding=encoding,
            delimitador=delimiter,
            estrutura_minima_valida=False,
            colunas_detectadas=[],
            mapeamento_utilizado={},
            total_linhas=0,
            linhas_validas=0,
            linhas_com_erro=0,
            linhas_com_aviso=0,
            produtos_nao_encontrados=[],
            depositos_nao_encontrados=[],
            valor_total_estimado=0.0,
            itens=[],
            erros_arquivo=[EstoqueImplantacaoPreviewMessage(codigo=codigo, mensagem=mensagem)],
        )
