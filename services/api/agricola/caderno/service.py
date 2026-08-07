import uuid
import hashlib
import json
from uuid import UUID
from datetime import date, datetime, timedelta, timezone
from typing import Any, Literal
import unicodedata
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, or_, func
from sqlalchemy.orm import selectinload

from core.base_service import BaseService
from core.exceptions import BusinessRuleError
from agricola.caderno.models import (
    CadernoCampoEntrada,
    CadernoCampoFoto,
    CadernoEventoStatusHistorico,
    VisitaTecnica,
    EPIEntrega,
    CadernoExportacao,
)
from core.cadastros.pessoas.models import Pessoa
from core.models.auth import Usuario
from agricola.caderno.schemas import (
    EntradaCreate,
    EntradaUpdate,
    ReprocessarEntradaRequest,
    VisitaTecnicaCreate,
    EPIEntregaCreate,
    ExportacaoCreate,
    TimelineItem,
    TipoEventoCaderno,
    OrigemEventoCaderno,
    OrigemTecnicaCaderno,
    StatusEventoCaderno,
    StatusEventoUpdateRequest,
    EventoCadernoOfflinePayload,
    EventoCadernoOfflineSyncResult,
    EventoCadernoOficialSync,
)
from agricola.operacoes.models import OperacaoAgricola, OperacaoExecucao
from campo.models import DispositivoCampo
from core.services.storage_service import StorageService
from core.services.audit_service import _serialize, write_audit_log

# Janela de edição livre sem aprovação do RT (configurável futuramente por tenant)
JANELA_EDICAO_HORAS = 72
ORIGEM_EVENTO_MANUAL = "WEB_MANUAL"
ORIGEM_TECNICA_MANUAL = "MANUAL_DIGITAL"
ORIGEM_EVENTO_OPERACAO = "OPERACAO_AGRICOLA"
ORIGEM_TECNICA_OPERACAO = "OPERACAO_AUTO"
STATUS_EVENTO_PADRAO: StatusEventoCaderno = "CONSOLIDADO"
STATUS_EVENTO_VALIDOS: set[str] = {
    "RASCUNHO",
    "PENDENTE_SINCRONIZACAO",
    "SINCRONIZADO",
    "PENDENTE_APROVACAO",
    "APROVADO",
    "REJEITADO",
    "CONSOLIDADO",
    "CANCELADO",
}
ORIGEM_EVENTO_VALIDAS: set[str] = {
    "OPERACAO_AGRICOLA",
    "WEB_MANUAL",
    "PWA_OFFLINE",
    "IMPORTACAO",
    "SISTEMA",
}
ORIGEM_TECNICA_VALIDAS: set[str] = {
    "OPERACAO_AUTO",
    "MANUAL_DIGITAL",
    "SYNC_PWA",
    "IMPORTACAO",
    "SISTEMA",
}

TIPOS_EVENTO_VALIDOS: set[str] = {
    "PLANTIO",
    "PULVERIZACAO",
    "APLICACAO",
    "IRRIGACAO",
    "COLHEITA",
    "INSPECAO",
    "OCORRENCIA",
    "MANUTENCAO",
    "ABASTECIMENTO",
    "EXECUCAO_OPERACIONAL",
    "MONITORAMENTO",
    "VISITA_TECNICA",
    "EPI_ENTREGA",
    "OBSERVACAO",
    "CLIMA",
    "SOLO",
}

TIPOS_LEGACY_PARA_EVENTO: dict[str, str] = {
    "PLANTIO_REGISTRO": "PLANTIO",
    "PLANTIO": "PLANTIO",
    "PULVERIZACAO": "PULVERIZACAO",
    "PULVERIZAÇÃO": "PULVERIZACAO",
    "APLICACAO": "APLICACAO",
    "APLICAÇÃO": "APLICACAO",
    "APLICACAO_DEFENSIVO": "PULVERIZACAO",
    "APLICACAO_FERTILIZANTE": "APLICACAO",
    "IRRIGACAO": "IRRIGACAO",
    "IRRIGAÇÃO": "IRRIGACAO",
    "IRRIGACAO_EVENTO": "IRRIGACAO",
    "COLHEITA_REGISTRO": "COLHEITA",
    "COLHEITA": "COLHEITA",
    "MONITORAMENTO_PRAGA": "MONITORAMENTO",
    "MONITORAMENTO": "MONITORAMENTO",
    "AMOSTRAGEM_SOLO": "SOLO",
    "PREPARO_SOLO": "SOLO",
    "SOLO": "SOLO",
    "INSPECAO_EQUIPAMENTO": "INSPECAO",
    "INSPECAO": "INSPECAO",
    "OCORRENCIA": "OCORRENCIA",
    "MANUTENCAO_OCORRENCIA": "MANUTENCAO",
    "MANUTENCAO": "MANUTENCAO",
    "ABASTECIMENTO_MAQUINA": "ABASTECIMENTO",
    "ABASTECIMENTO": "ABASTECIMENTO",
    "VISITA_TECNICA": "VISITA_TECNICA",
    "EPI_ENTREGA": "EPI_ENTREGA",
    "OBSERVACAO": "OBSERVACAO",
    "CLIMA": "CLIMA",
    "EXECUCAO_OPERACIONAL": "EXECUCAO_OPERACIONAL",
}

TIPOS_EVENTO_QUE_EXIGEM_APROVACAO: set[str] = {
    "APLICACAO",
    "PULVERIZACAO",
    "OCORRENCIA",
    "VISITA_TECNICA",
    "EPI_ENTREGA",
}

ORIGENS_EVENTO_QUE_EXIGEM_APROVACAO: set[str] = {
    "PWA_OFFLINE",
}

STATUS_TRANSICOES_PERMITIDAS: dict[str, set[str]] = {
    "RASCUNHO": {"PENDENTE_APROVACAO"},
    "PENDENTE_SINCRONIZACAO": {"SINCRONIZADO", "PENDENTE_APROVACAO"},
    "SINCRONIZADO": {"PENDENTE_APROVACAO", "CANCELADO"},
    "PENDENTE_APROVACAO": {"APROVADO", "REJEITADO", "CANCELADO"},
    "APROVADO": {"CONSOLIDADO", "CANCELADO"},
    "REJEITADO": {"CANCELADO"},
    "CONSOLIDADO": {"CANCELADO"},
    "CANCELADO": set(),
}

STATUS_EVENTO_FINAIS: set[str] = {"REJEITADO", "CONSOLIDADO", "CANCELADO"}
STATUS_EVENTO_GOVERNADOS: set[str] = set(STATUS_EVENTO_VALIDOS)
DOCUMENTAL_STATUS_VIGENTE = "VIGENTE"
DOCUMENTAL_STATUS_ORIGEM_INVALIDADA = "ORIGEM_INVALIDADA"
CAMPOS_CORRIGIVEIS_CADERNO: set[str] = {
    "descricao",
    "tipo_evento",
    "nivel_severidade",
    "recomendacao",
    "numero_receituario",
    "data_registro",
    "status_evento",
}


def _normalizar_chave(valor: str | None) -> str:
    if not valor:
        return ""
    texto = unicodedata.normalize("NFKD", valor)
    texto = texto.encode("ascii", "ignore").decode("ascii")
    texto = texto.strip().upper().replace("-", "_").replace(" ", "_")
    while "__" in texto:
        texto = texto.replace("__", "_")
    return texto


def _validar_tipo_evento(tipo_evento: str) -> str:
    tipo_normalizado = _normalizar_chave(tipo_evento)
    if tipo_normalizado not in TIPOS_EVENTO_VALIDOS:
        raise BusinessRuleError(f"Tipo de evento inválido: {tipo_evento}")
    return tipo_normalizado


def _validar_domino(valor: str | None, validos: set[str], nome_campo: str, default: str | None = None) -> str:
    if valor is None:
        if default is None:
            raise BusinessRuleError(f"Campo obrigatório ausente: {nome_campo}")
        return default
    valor_normalizado = _normalizar_chave(valor)
    if valor_normalizado not in validos:
        raise BusinessRuleError(f"{nome_campo} inválido: {valor}")
    return valor_normalizado


def _status_flags(status_evento: str | None) -> dict[str, bool]:
    status = _normalizar_chave(status_evento)
    return {
        "pendente_aprovacao": status in {"RASCUNHO", "PENDENTE_SINCRONIZACAO", "SINCRONIZADO", "PENDENTE_APROVACAO"},
        "aprovado": status == "APROVADO",
        "consolidado": status == "CONSOLIDADO",
        "rejeitado": status == "REJEITADO",
    }


def _to_naive_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def _exige_aprovacao_por_contexto(
    *,
    tipo_evento: str,
    origem_evento: str,
    digitalizacao_retroativa: bool = False,
) -> bool:
    return (
        origem_evento in ORIGENS_EVENTO_QUE_EXIGEM_APROVACAO
        or tipo_evento in TIPOS_EVENTO_QUE_EXIGEM_APROVACAO
        or digitalizacao_retroativa
    )


def validar_transicao_status_evento(
    status_atual: str | None,
    novo_status: str,
    contexto: dict[str, Any],
) -> str:
    status_novo = _normalizar_chave(novo_status)
    if status_novo not in STATUS_EVENTO_GOVERNADOS:
        raise BusinessRuleError(f"Status de evento inválido: {novo_status}")

    status_anterior = _normalizar_chave(status_atual) if status_atual else None
    origem_evento = _normalizar_chave(contexto.get("origem_evento"))
    tipo_evento = _normalizar_chave(contexto.get("tipo_evento"))
    usuario_role = _normalizar_chave(contexto.get("usuario_role"))
    justificativa = (contexto.get("justificativa") or "").strip()
    digitalizacao_retroativa = bool(contexto.get("digitalizacao_retroativa"))
    tem_evidencias = bool(contexto.get("tem_evidencias"))
    is_system = bool(contexto.get("is_system"))

    if status_novo in {"PENDENTE_SINCRONIZACAO", "SINCRONIZADO"} and origem_evento != "PWA_OFFLINE":
        raise BusinessRuleError("Estados de sincronização são exclusivos do fluxo offline do PWA.")

    if status_anterior is None:
        if origem_evento == ORIGEM_EVENTO_OPERACAO:
            if status_novo not in {"APROVADO", "CONSOLIDADO"}:
                raise BusinessRuleError("Eventos automáticos de operação devem nascer aprovados ou consolidados.")
            return status_novo

        if origem_evento == "PWA_OFFLINE":
            if status_novo not in {"RASCUNHO", "PENDENTE_SINCRONIZACAO", "SINCRONIZADO", "PENDENTE_APROVACAO"}:
                raise BusinessRuleError("Eventos do PWA offline devem iniciar em estado de sincronização ou aprovação.")
            return status_novo

        if _exige_aprovacao_por_contexto(
            tipo_evento=tipo_evento,
            origem_evento=origem_evento,
            digitalizacao_retroativa=digitalizacao_retroativa,
        ):
            if status_novo not in {"RASCUNHO", "PENDENTE_APROVACAO"}:
                raise BusinessRuleError("Eventos que exigem validação devem iniciar como rascunho ou pendentes de aprovação.")
        return status_novo

    if status_anterior == status_novo:
        return status_novo

    permitidos = STATUS_TRANSICOES_PERMITIDAS.get(status_anterior, set())
    if status_novo not in permitidos:
        raise BusinessRuleError(f"Transição de status não permitida: {status_anterior} → {status_novo}")

    exige_aprovacao = _exige_aprovacao_por_contexto(
        tipo_evento=tipo_evento,
        origem_evento=origem_evento,
        digitalizacao_retroativa=digitalizacao_retroativa,
    )
    precisa_permissao = status_novo in {"APROVADO", "REJEITADO", "CONSOLIDADO", "CANCELADO"}
    if precisa_permissao and not is_system and usuario_role not in {"ADMIN", "AGRONOMO", "GERENTE", "OWNER"}:
        raise BusinessRuleError("Usuário não possui permissão para esta transição de status.")

    if status_novo == "CANCELADO":
        if not justificativa:
            raise BusinessRuleError("Cancelamento exige justificativa.")
        return status_novo

    if status_novo in {"APROVADO", "CONSOLIDADO"}:
        if exige_aprovacao and not tem_evidencias and origem_evento != ORIGEM_EVENTO_OPERACAO:
            raise BusinessRuleError("Eventos que exigem evidência não podem ser consolidados sem evidências anexadas.")

    if origem_evento == "PWA_OFFLINE" and status_novo == "CONSOLIDADO":
        raise BusinessRuleError("Eventos do PWA offline precisam ser aprovados antes da consolidação.")

    if status_novo == "REJEITADO" and not justificativa:
        raise BusinessRuleError("Rejeição exige justificativa.")

    return status_novo


def _mapear_tipo_evento_legado(tipo: str, subtipo: str | None = None) -> str:
    tipo_norm = _normalizar_chave(tipo)
    subtipo_norm = _normalizar_chave(subtipo)
    if tipo_norm == "OPERACAO_AUTO":
        return "EXECUCAO_OPERACIONAL"
    if tipo_norm == "APLICACAO" and "FERTIL" in subtipo_norm:
        return "APLICACAO"
    if tipo_norm == "APLICACAO" and "DEFENS" in subtipo_norm:
        return "PULVERIZACAO"
    if tipo_norm == "MONITORAMENTO" and "SOLO" in subtipo_norm:
        return "SOLO"
    return TIPOS_LEGACY_PARA_EVENTO.get(tipo_norm, tipo_norm if tipo_norm in TIPOS_EVENTO_VALIDOS else "EXECUCAO_OPERACIONAL")


def mapear_operacao_para_evento_caderno(operacao: OperacaoAgricola) -> dict:
    tipo_norm = _normalizar_chave(operacao.tipo)
    subtipo_norm = _normalizar_chave(operacao.subtipo)
    descricao_norm = _normalizar_chave(operacao.descricao)

    if tipo_norm in {"PLANTIO", "PLANTIO_REGISTRO"}:
        tipo_evento = "PLANTIO"
    elif tipo_norm in {"COLHEITA", "COLHEITA_REGISTRO"}:
        tipo_evento = "COLHEITA"
    elif tipo_norm in {"IRRIGACAO", "IRRIGACAO_EVENTO"}:
        tipo_evento = "IRRIGACAO"
    elif tipo_norm in {"APLICACAO_FERTILIZANTE"}:
        tipo_evento = "APLICACAO"
    elif tipo_norm in {"APLICACAO_DEFENSIVO", "PULVERIZACAO"}:
        tipo_evento = "PULVERIZACAO"
    elif tipo_norm == "APLICACAO":
        if "DEFENS" in subtipo_norm or "DEFENS" in descricao_norm:
            tipo_evento = "PULVERIZACAO"
        else:
            tipo_evento = "APLICACAO"
    elif tipo_norm in {"MONITORAMENTO", "MONITORAMENTO_PRAGA"}:
        tipo_evento = "MONITORAMENTO"
    elif tipo_norm in {"AMOSTRAGEM_SOLO", "PREPARO_SOLO", "SOLO"}:
        tipo_evento = "SOLO"
    elif tipo_norm in {"INSPECAO", "INSPECAO_EQUIPAMENTO"}:
        tipo_evento = "INSPECAO"
    elif tipo_norm in {"ABASTECIMENTO", "ABASTECIMENTO_MAQUINA"}:
        tipo_evento = "ABASTECIMENTO"
    elif tipo_norm in {"MANUTENCAO", "MANUTENCAO_OCORRENCIA"}:
        tipo_evento = "MANUTENCAO"
    else:
        tipo_evento = "EXECUCAO_OPERACIONAL"

    return {
        "tipo": tipo_evento,
        "tipo_evento": tipo_evento,
        "descricao": mapear_descricao_operacao_para_caderno(operacao),
        "data_registro": operacao.data_realizada,
        "origem_evento": ORIGEM_EVENTO_OPERACAO,
        "origem_id": str(operacao.id),
        "origem_tecnica": ORIGEM_TECNICA_OPERACAO,
        "status_evento": STATUS_EVENTO_PADRAO,
        "nivel_severidade": None,
        "recomendacao": None,
        "numero_receituario": None,
        "operacao_id": operacao.id,
    }


def mapear_descricao_operacao_para_caderno(operacao: OperacaoAgricola) -> str:
    descricao = operacao.tipo
    if operacao.subtipo:
        descricao += f" / {operacao.subtipo}"
    if operacao.area_aplicada_ha:
        area_val = float(operacao.area_aplicada_ha)
        area_str = f"{area_val:,.4f}".rstrip("0").rstrip(".") if "." in f"{area_val:,.4f}" else f"{area_val:,.0f}"
        area_pt = area_str.replace(",", "X").replace(".", ",").replace("X", ".")
        descricao += f"\nÁrea: {area_pt} ha"
    if operacao.custo_total:
        custo_val = float(operacao.custo_total)
        custo_str = f"{custo_val:,.2f}"
        custo_pt = custo_str.replace(",", "X").replace(".", ",").replace("X", ".")
        descricao += f"\nCusto: R$ {custo_pt}"
    return descricao


class CadernoCampoService(BaseService[CadernoCampoEntrada]):
    def __init__(self, session: AsyncSession, tenant_id: UUID, user_id: UUID | None = None, ip_address: str | None = None):
        super().__init__(CadernoCampoEntrada, session, tenant_id, user_id=user_id, ip_address=ip_address)

    async def obter_por_origem(self, origem_evento: str, origem_id: str) -> CadernoCampoEntrada | None:
        stmt = select(CadernoCampoEntrada).where(
            CadernoCampoEntrada.tenant_id == self.tenant_id,
            CadernoCampoEntrada.origem_evento == origem_evento,
            CadernoCampoEntrada.origem_id == origem_id,
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def _registrar_historico_status(
        self,
        entrada: CadernoCampoEntrada,
        status_anterior: str | None,
        status_novo: str,
        justificativa: str | None = None,
        usuario_id: UUID | None = None,
    ) -> CadernoEventoStatusHistorico:
        historico = CadernoEventoStatusHistorico(
            tenant_id=self.tenant_id,
            caderno_entrada_id=entrada.id,
            status_anterior=status_anterior,
            status_novo=status_novo,
            usuario_id=usuario_id or self.user_id,
            justificativa=justificativa,
            created_at=datetime.utcnow(),
        )
        self.session.add(historico)
        await self.session.flush()
        return historico

    @staticmethod
    def _documental_status(entrada: CadernoCampoEntrada) -> str:
        return (
            DOCUMENTAL_STATUS_ORIGEM_INVALIDADA
            if entrada.origem_invalidada
            else DOCUMENTAL_STATUS_VIGENTE
        )

    @staticmethod
    def _aplicar_metadados_invalidacao_documental(
        *,
        payload: dict[str, Any] | None,
        motivo: str,
        usuario_id: UUID | None,
        invalidado_em: datetime,
    ) -> dict[str, Any]:
        novo_payload = dict(payload or {})
        novo_payload["origem_invalidada"] = True
        novo_payload["origem_invalidada_em"] = invalidado_em.isoformat()
        novo_payload["origem_invalidada_por"] = str(usuario_id) if usuario_id else None
        novo_payload["motivo_invalidacao_origem"] = motivo
        novo_payload["documental_status"] = DOCUMENTAL_STATUS_ORIGEM_INVALIDADA
        return novo_payload

    async def _marcar_invalidacao_documental_operacao(
        self,
        operacao: OperacaoAgricola,
        *,
        motivo: str,
        usuario_id: UUID | None,
        invalidado_em: datetime,
        ip_address: str | None = None,
    ) -> OperacaoAgricola | None:
        if operacao.origem_invalidada:
            return None

        payload_before = _serialize(operacao)
        operacao.origem_invalidada = True
        operacao.origem_invalidada_em = invalidado_em
        operacao.origem_invalidada_por = usuario_id
        operacao.motivo_invalidacao_origem = motivo
        self.session.add(operacao)
        await self.session.flush()

        await write_audit_log(
            self.session,
            tenant_id=self.tenant_id,
            user_id=usuario_id,
            action="invalidate_origin",
            resource="operacoes_agricolas",
            resource_id=operacao.id,
            payload_before=payload_before,
            payload_after=_serialize(operacao),
            ip_address=ip_address,
        )
        return operacao

    async def _marcar_invalidacao_documental_entrada(
        self,
        entrada: CadernoCampoEntrada,
        *,
        motivo: str,
        usuario_id: UUID | None,
        invalidado_em: datetime,
        ip_address: str | None = None,
    ) -> CadernoCampoEntrada | None:
        if entrada.origem_invalidada:
            return None

        payload_before = _serialize(entrada)
        entrada.origem_invalidada = True
        entrada.origem_invalidada_em = invalidado_em
        entrada.origem_invalidada_por = usuario_id
        entrada.motivo_invalidacao_origem = motivo
        entrada.payload_operacional = self._aplicar_metadados_invalidacao_documental(
            payload=entrada.payload_operacional,
            motivo=motivo,
            usuario_id=usuario_id,
            invalidado_em=invalidado_em,
        )
        self.session.add(entrada)
        await self.session.flush()

        await write_audit_log(
            self.session,
            tenant_id=self.tenant_id,
            user_id=usuario_id,
            action="invalidate_origin",
            resource="caderno_campo_entradas",
            resource_id=entrada.id,
            payload_before=payload_before,
            payload_after=_serialize(entrada),
            ip_address=ip_address,
        )
        return entrada

    async def propagar_invalidacao_origem_operacional(
        self,
        *,
        tarefa_id: UUID,
        motivo: str,
        usuario_id: UUID | None,
        operacao_ids: list[UUID] | None = None,
        ip_address: str | None = None,
    ) -> dict[str, list[UUID]]:
        invalidado_em = datetime.utcnow()
        operacao_ids_unicos = list(dict.fromkeys(operacao_ids or []))
        ids_entrada: list[UUID] = []
        ids_operacao: list[UUID] = []

        if operacao_ids_unicos:
            stmt_operacao = select(OperacaoAgricola).where(
                OperacaoAgricola.tenant_id == self.tenant_id,
                OperacaoAgricola.id.in_(operacao_ids_unicos),
            )
            operacoes = list((await self.session.execute(stmt_operacao)).scalars().all())
            for operacao in operacoes:
                if await self._marcar_invalidacao_documental_operacao(
                    operacao,
                    motivo=motivo,
                    usuario_id=usuario_id,
                    invalidado_em=invalidado_em,
                    ip_address=ip_address,
                ):
                    ids_operacao.append(operacao.id)

        clauses = [
            CadernoCampoEntrada.payload_operacional["task_id"].as_string() == str(tarefa_id),
        ]
        if operacao_ids_unicos:
            clauses.append(CadernoCampoEntrada.operacao_id.in_(operacao_ids_unicos))
            clauses.append(
                CadernoCampoEntrada.payload_operacional["operacao_id"].as_string().in_(
                    [str(op_id) for op_id in operacao_ids_unicos]
                )
            )

        entrada_stmt = select(CadernoCampoEntrada).where(
            CadernoCampoEntrada.tenant_id == self.tenant_id,
            or_(*clauses),
        )
        entradas = list((await self.session.execute(entrada_stmt)).scalars().all())
        for entrada in entradas:
            if await self._marcar_invalidacao_documental_entrada(
                entrada,
                motivo=motivo,
                usuario_id=usuario_id,
                invalidado_em=invalidado_em,
                ip_address=ip_address,
            ):
                ids_entrada.append(entrada.id)

        return {
            "operacao_ids": ids_operacao,
            "entrada_ids": ids_entrada,
        }

    @staticmethod
    def _entrada_foi_retificada(entrada: CadernoCampoEntrada) -> bool:
        return bool(entrada.retificado_por_evento_id)

    @staticmethod
    def _entrada_eh_retificadora(entrada: CadernoCampoEntrada) -> bool:
        return bool(entrada.retifica_evento_id)

    @staticmethod
    def _entrada_eh_vigente(entrada: CadernoCampoEntrada) -> bool:
        return (
            not entrada.excluida
            and not entrada.retificado_por_evento_id
            and not entrada.origem_invalidada
            and _normalizar_chave(entrada.status_evento) in {"APROVADO", "CONSOLIDADO"}
        )

    def _aplicar_dados_corrigidos(
        self,
        origem: CadernoCampoEntrada,
        dados_corrigidos: dict[str, Any],
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "safra_id": origem.safra_id,
            "talhao_id": origem.talhao_id,
            "tipo": origem.tipo,
            "tipo_evento": origem.tipo_evento,
            "descricao": origem.descricao,
            "data_registro": origem.data_registro,
            "origem_evento": ORIGEM_EVENTO_MANUAL if origem.origem_evento != ORIGEM_EVENTO_OPERACAO else origem.origem_evento,
            "origem_id": str(uuid.uuid4()),
            "origem_tecnica": ORIGEM_TECNICA_MANUAL if origem.origem_evento != ORIGEM_EVENTO_OPERACAO else origem.origem_tecnica,
            "status_evento": "PENDENTE_APROVACAO",
            "nivel_severidade": origem.nivel_severidade,
            "recomendacao": origem.recomendacao,
            "numero_receituario": origem.numero_receituario,
            "executado_por_pessoa_id": origem.executado_por_pessoa_id,
            "digitalizacao_retroativa": origem.digitalizacao_retroativa,
            "justificativa_retroativa": origem.justificativa_retroativa,
        }

        for campo, valor in dados_corrigidos.items():
            campo_norm = _normalizar_chave(campo).lower()
            if campo_norm not in CAMPOS_CORRIGIVEIS_CADERNO:
                continue
            if campo_norm == "tipo_evento" and valor is not None:
                valor = _validar_tipo_evento(str(valor))
            elif campo_norm == "status_evento" and valor is not None:
                valor = _validar_domino(str(valor), STATUS_EVENTO_VALIDOS, "status_evento", "PENDENTE_APROVACAO")
            elif campo_norm == "data_registro" and valor is not None and isinstance(valor, str):
                valor = date.fromisoformat(valor)
            elif campo_norm == "executado_por_pessoa_id" and valor is not None:
                valor = UUID(str(valor))
            payload[campo_norm] = valor

        if payload["tipo_evento"] is None:
            payload["tipo_evento"] = origem.tipo_evento or _mapear_tipo_evento_legado(origem.tipo)
        payload["tipo"] = payload["tipo_evento"]
        if not payload.get("descricao"):
            payload["descricao"] = origem.descricao
        if payload.get("status_evento") not in {"PENDENTE_APROVACAO", "RASCUNHO", "PENDENTE_SINCRONIZACAO", "SINCRONIZADO"}:
            payload["status_evento"] = "PENDENTE_APROVACAO"
        return payload

    def _status_inicial_padrao(self, tipo_evento: str, origem_evento: str, digitalizacao_retroativa: bool) -> str:
        if origem_evento == ORIGEM_EVENTO_OPERACAO:
            return "CONSOLIDADO"
        if origem_evento == "PWA_OFFLINE":
            return "PENDENTE_SINCRONIZACAO"
        if _exige_aprovacao_por_contexto(
            tipo_evento=tipo_evento,
            origem_evento=origem_evento,
            digitalizacao_retroativa=digitalizacao_retroativa,
        ):
            return "PENDENTE_APROVACAO"
        return STATUS_EVENTO_PADRAO

    def _validar_edicao_retroativa(self, data_registro: date, justificativa: str | None) -> None:
        limite = datetime.utcnow() - timedelta(hours=JANELA_EDICAO_HORAS)
        if datetime.combine(data_registro, datetime.min.time()) < limite:
            if not justificativa:
                raise BusinessRuleError(
                    f"Registros com mais de {JANELA_EDICAO_HORAS}h exigem justificativa de digitalização retroativa."
                )

    def _resolver_tipo_evento(self, dados: EntradaCreate) -> str:
        if dados.tipo_evento:
            return _validar_tipo_evento(dados.tipo_evento)
        tipo_normalizado = _normalizar_chave(dados.tipo)
        if tipo_normalizado in TIPOS_EVENTO_VALIDOS:
            return tipo_normalizado
        if tipo_normalizado in TIPOS_LEGACY_PARA_EVENTO:
            return TIPOS_LEGACY_PARA_EVENTO[tipo_normalizado]
        raise BusinessRuleError(f"Tipo de evento inválido: {dados.tipo}")

    def _resolver_origem_evento(self, dados: EntradaCreate) -> str:
        return _validar_domino(dados.origem_evento, ORIGEM_EVENTO_VALIDAS, "origem_evento", ORIGEM_EVENTO_MANUAL)

    def _resolver_origem_tecnica(self, dados: EntradaCreate) -> str:
        if dados.origem_tecnica:
            return _validar_domino(dados.origem_tecnica, ORIGEM_TECNICA_VALIDAS, "origem_tecnica")
        if self._resolver_origem_evento(dados) == ORIGEM_EVENTO_OPERACAO:
            return ORIGEM_TECNICA_OPERACAO
        return ORIGEM_TECNICA_MANUAL

    async def garantir_evento_operacao(self, operacao: OperacaoAgricola) -> CadernoCampoEntrada:
        existente = await self.obter_por_origem(ORIGEM_EVENTO_OPERACAO, str(operacao.id))
        if existente:
            return existente

        payload = mapear_operacao_para_evento_caderno(operacao)
        executor_herdado = operacao.operador_id
        # Consulta explícita em vez de `operacao.execucoes` (lazy="selectin"):
        # um objeto apenas criado/flushado nesta mesma unit-of-work não passou
        # por uma query com eager loading, então o acesso lazy implícito
        # dispara I/O fora do contexto de greenlet do SQLAlchemy async.
        execucoes_stmt = (
            select(OperacaoExecucao)
            .where(
                OperacaoExecucao.tenant_id == self.tenant_id,
                OperacaoExecucao.operacao_id == operacao.id,
            )
            .order_by(OperacaoExecucao.data_execucao)
        )
        execucoes = (await self.session.execute(execucoes_stmt)).scalars().all()
        # Tenta encontrar o executor efetivo nas execuções
        for execucao in execucoes:
            if getattr(execucao, "operador_id", None):
                executor_herdado = execucao.operador_id
                break

        entrada = CadernoCampoEntrada(
            tenant_id=self.tenant_id,
            safra_id=operacao.safra_id,
            talhao_id=operacao.talhao_id,
            tipo=payload["tipo"],
            tipo_evento=payload["tipo_evento"],
            descricao=payload["descricao"],
            data_registro=payload["data_registro"],
            usuario_id=UUID("00000000-0000-0000-0000-000000000000"),
            executado_por_pessoa_id=executor_herdado,
            operacao_id=operacao.id,
            origem_evento=payload["origem_evento"],
            origem_id=payload["origem_id"],
            origem_tecnica=payload["origem_tecnica"],
            status_evento=payload["status_evento"],
        )
        if operacao.origem_invalidada:
            entrada.origem_invalidada = True
            entrada.origem_invalidada_em = operacao.origem_invalidada_em
            entrada.origem_invalidada_por = operacao.origem_invalidada_por
            entrada.motivo_invalidacao_origem = operacao.motivo_invalidacao_origem
        self.session.add(entrada)
        await self.session.flush()
        await self._registrar_historico_status(
            entrada,
            status_anterior=None,
            status_novo=entrada.status_evento,
            usuario_id=operacao.operador_id,
        )
        return entrada

    async def sincronizar_eventos_offline(
        self,
        eventos: list[EventoCadernoOfflinePayload],
        *,
        device: DispositivoCampo,
        ip: str | None = None,
    ) -> list[EventoCadernoOfflineSyncResult]:
        from core.cadastros.propriedades.models import AreaRural
        from agricola.safras.models import Safra

        resultados: list[EventoCadernoOfflineSyncResult] = []

        if not eventos:
            return resultados

        safra_ids = list({evento.safra_id for evento in eventos})
        talhao_ids = list({evento.talhao_id for evento in eventos if evento.talhao_id})
        local_ids = list({evento.local_id for evento in eventos if evento.local_id})

        safras_por_id: dict[UUID, Safra] = {}
        if safra_ids:
            safra_rows = (await self.session.execute(
                select(Safra).where(
                    Safra.id.in_(safra_ids),
                    Safra.tenant_id == self.tenant_id,
                )
            )).scalars().all()
            safras_por_id = {safra.id: safra for safra in safra_rows}

        talhoes_por_id: dict[UUID, AreaRural] = {}
        if talhao_ids:
            talhao_rows = (await self.session.execute(
                select(AreaRural).where(
                    AreaRural.id.in_(talhao_ids),
                    AreaRural.tenant_id == self.tenant_id,
                )
            )).scalars().all()
            talhoes_por_id = {talhao.id: talhao for talhao in talhao_rows}

        existentes_por_chave: dict[tuple[str, str], CadernoCampoEntrada] = {}
        if local_ids:
            existentes = (await self.session.execute(
                select(CadernoCampoEntrada).where(
                    CadernoCampoEntrada.tenant_id == self.tenant_id,
                    CadernoCampoEntrada.origem_evento.in_(["PWA_OFFLINE", "CALIBRACAO_EQUIPAMENTO", "CHECKLIST_SANITARIO", "EPI_ENTREGA"]),
                    CadernoCampoEntrada.origem_id.in_(local_ids),
                )
            )).scalars().all()
            for existente in existentes:
                if existente.origem_evento and existente.origem_id:
                    existentes_por_chave[(existente.origem_evento, existente.origem_id)] = existente

        for evento in eventos:
            try:
                if evento.device_id != str(device.id):
                    raise BusinessRuleError("device_id do evento não confere com o dispositivo autenticado.")
                if evento.tenant_id != self.tenant_id:
                    raise BusinessRuleError("tenant_id do evento não confere com o tenant autenticado.")

                if not evento.talhao_id:
                    raise BusinessRuleError("Evento offline exige talhão para sincronização inicial.")

                safra = safras_por_id.get(evento.safra_id)
                if not safra:
                    raise BusinessRuleError("Safra inválida para sincronização offline.")

                talhao = talhoes_por_id.get(evento.talhao_id)
                if not talhao:
                    raise BusinessRuleError("Talhão inválido para sincronização offline.")

                if talhao.unidade_produtiva_id not in device.fazenda_ids:
                    raise BusinessRuleError("Talhão fora do escopo do dispositivo autenticado.")

                existente = (
                    existentes_por_chave.get(("PWA_OFFLINE", evento.local_id))
                    or existentes_por_chave.get(("CALIBRACAO_EQUIPAMENTO", evento.local_id))
                    or existentes_por_chave.get(("CHECKLIST_SANITARIO", evento.local_id))
                    or existentes_por_chave.get(("EPI_ENTREGA", evento.local_id))
                )
                if existente:
                    resultados.append(
                        EventoCadernoOfflineSyncResult(
                            local_id=evento.local_id,
                            server_id=existente.id,
                            status="SYNCED",
                            status_evento=existente.status_evento,
                            erro=None,
                        )
                    )
                    continue

                descricao = (
                    str(evento.payload_operacional.get("descricao"))
                    if evento.payload_operacional.get("descricao") is not None
                    else evento.tipo_evento.replace("_", " ").title()
                )
                data_registro = evento.payload_operacional.get("data_registro")
                if isinstance(data_registro, str):
                    data_registro = date.fromisoformat(data_registro)
                if not isinstance(data_registro, date):
                    data_registro = evento.client_created_at.date()

                status_evento = "PENDENTE_APROVACAO" if _exige_aprovacao_por_contexto(
                    tipo_evento=evento.tipo_evento,
                    origem_evento=evento.origem_evento,
                    digitalizacao_retroativa=bool(evento.payload_operacional.get("digitalizacao_retroativa")),
                ) else "SINCRONIZADO"

                origem_evento = "PWA_OFFLINE"
                origem_id = evento.local_id
                origem_tecnica = "SYNC_PWA"

                p_calib = evento.payload_operacional.get("calibracao")
                p_checklist = evento.payload_operacional.get("checklist")

                if p_calib and isinstance(p_calib, dict):
                    from core.cadastros.equipamentos.models import EquipamentoCalibracao
                    import hashlib
                    c_user = evento.usuario_id or device.user_id
                    data_calib = date.fromisoformat(p_calib["data_calibracao"]) if isinstance(p_calib.get("data_calibracao"), str) else data_registro
                    val_ate = date.fromisoformat(p_calib["validade_ate"]) if isinstance(p_calib.get("validade_ate"), str) else data_registro

                    payload_str = f"{self.tenant_id}:{p_calib['equipamento_id']}:{data_calib}:{p_calib.get('metodo')}:{p_calib.get('vazao')}:{p_calib.get('pressao')}:{c_user}"
                    hash_val = hashlib.sha256(payload_str.encode('utf-8')).hexdigest()

                    calib_obj = EquipamentoCalibracao(
                        id=UUID(evento.local_id),
                        tenant_id=self.tenant_id,
                        equipamento_id=UUID(p_calib["equipamento_id"]),
                        data_calibracao=data_calib,
                        validade_ate=val_ate,
                        metodo=p_calib.get("metodo", "Manual"),
                        vazao=float(p_calib.get("vazao", 0.0)),
                        pressao=float(p_calib.get("pressao", 0.0)),
                        observacoes=p_calib.get("observacoes"),
                        hash_documental=hash_val,
                        criado_por=c_user
                    )
                    self.session.add(calib_obj)
                    await self.session.flush()

                    origem_evento = "CALIBRACAO_EQUIPAMENTO"
                    origem_id = str(calib_obj.id)
                    origem_tecnica = "CALIBRACAO"

                elif p_checklist and isinstance(p_checklist, dict):
                    from operacional.models.checklist import ChecklistRealizado
                    chk_lib = bool(p_checklist.get("liberado_para_uso", True))
                    chk_respostas = p_checklist.get("respostas", [])

                    chk_obj = ChecklistRealizado(
                        id=UUID(evento.local_id),
                        tenant_id=self.tenant_id,
                        equipamento_id=UUID(p_checklist["equipamento_id"]),
                        modelo_id=UUID(p_checklist["modelo_id"]),
                        operador_id=evento.usuario_id or device.user_id,
                        data_hora=evento.client_created_at,
                        respostas=chk_respostas,
                        liberado_para_uso=chk_lib,
                        observacoes_gerais=p_checklist.get("observacoes_gerais")
                    )
                    self.session.add(chk_obj)
                    await self.session.flush()

                    origem_evento = "CHECKLIST_SANITARIO"
                    origem_id = str(chk_obj.id)
                    origem_tecnica = "CHECKLIST"

                elif evento.tipo_evento == "EPI_ENTREGA":
                    p_trabalhador_id = UUID(str(evento.payload_operacional.get("trabalhador_id"))) if evento.payload_operacional.get("trabalhador_id") else None
                    p_nome_trabalhador = str(evento.payload_operacional.get("nome_trabalhador", ""))
                    p_epi_tipo = str(evento.payload_operacional.get("epi_tipo", ""))
                    p_quantidade = int(evento.payload_operacional.get("quantidade", 1))

                    p_data_entrega = evento.payload_operacional.get("data_entrega")
                    if isinstance(p_data_entrega, str):
                        p_data_entrega = date.fromisoformat(p_data_entrega)
                    if not isinstance(p_data_entrega, date):
                        p_data_entrega = data_registro

                    p_validade = evento.payload_operacional.get("validade")
                    if isinstance(p_validade, str):
                        p_validade = date.fromisoformat(p_validade)
                    elif not isinstance(p_validade, date):
                        p_validade = None

                    p_operacao_id = UUID(str(evento.payload_operacional.get("operacao_id"))) if evento.payload_operacional.get("operacao_id") else None

                    epi_obj = EPIEntrega(
                        id=UUID(evento.local_id),
                        tenant_id=self.tenant_id,
                        trabalhador_id=p_trabalhador_id,
                        nome_trabalhador=p_nome_trabalhador,
                        epi_tipo=p_epi_tipo,
                        quantidade=p_quantidade,
                        data_entrega=p_data_entrega,
                        validade=p_validade,
                        operacao_id=p_operacao_id,
                        assinatura_url=None,
                    )
                    self.session.add(epi_obj)
                    await self.session.flush()

                    origem_evento = "EPI_ENTREGA"
                    origem_id = str(epi_obj.id)
                    origem_tecnica = "SYNC_PWA"

                entrada = CadernoCampoEntrada(
                    tenant_id=self.tenant_id,
                    safra_id=evento.safra_id,
                    talhao_id=evento.talhao_id,
                    tipo=evento.tipo_evento,
                    tipo_evento=evento.tipo_evento,
                    descricao=descricao,
                    data_registro=data_registro,
                    usuario_id=evento.usuario_id or device.user_id,
                    executado_por_pessoa_id=evento.executado_por_pessoa_id,
                    operacao_id=evento.operacao_id,
                    origem_evento=origem_evento,
                    origem_id=origem_id,
                    origem_tecnica=origem_tecnica,
                    device_id=device.id,
                    unidade_produtiva_id=talhao.unidade_produtiva_id,
                    client_created_at=_to_naive_utc(evento.client_created_at),
                    client_updated_at=_to_naive_utc(evento.client_updated_at),
                    payload_operacional={
                        **evento.payload_operacional,
                        "evidencias": [e.model_dump(mode="json") for e in evento.evidencias],
                        "device_id": evento.device_id,
                        "local_id": evento.local_id,
                    },
                    status_evento=status_evento,
                    nivel_severidade=evento.payload_operacional.get("nivel_severidade"),
                    recomendacao=evento.payload_operacional.get("recomendacao"),
                    numero_receituario=evento.payload_operacional.get("numero_receituario"),
                )
                self.session.add(entrada)
                await self.session.flush()
                await self._registrar_historico_status(
                    entrada,
                    status_anterior=None,
                    status_novo=entrada.status_evento,
                    justificativa=evento.payload_operacional.get("justificativa"),
                    usuario_id=evento.usuario_id or device.user_id,
                )

                resultados.append(
                    EventoCadernoOfflineSyncResult(
                        local_id=evento.local_id,
                        server_id=entrada.id,
                        status="SYNCED",
                        status_evento=entrada.status_evento,
                        erro=None,
                    )
                )
            except Exception as exc:
                resultados.append(
                    EventoCadernoOfflineSyncResult(
                        local_id=evento.local_id,
                        server_id=None,
                        status="ERROR",
                        status_evento=None,
                        erro=str(exc),
                    )
                )

        return resultados

    async def upload_evidencia_offline(
        self,
        *,
        entrada_id: UUID,
        device: "DispositivoCampo",
        local_evidence_id: str,
        file_content: bytes,
        filename: str,
        mime_type: str | None,
        size_bytes: int | None,
        captured_at: datetime | None,
        latitude: float | None,
        longitude: float | None,
    ) -> "CadernoCampoFoto":
        """Faz upload de evidência offline para uma entrada do caderno.

        Args:
            entrada_id: ID da entrada canônica do caderno.
            device: Dispositivo de campo autenticado.
            local_evidence_id: ID local da evidência (para idempotência).
            file_content: Bytes do arquivo de imagem.
            filename: Nome do arquivo.
            mime_type: Tipo MIME do arquivo.
            size_bytes: Tamanho em bytes.
            captured_at: Timestamp de captura no campo.
            latitude: Latitude do GPS no momento da captura.
            longitude: Longitude do GPS no momento da captura.

        Returns:
            CadernoCampoFoto criada ou existente (idempotente).

        Raises:
            BusinessRuleError: Se entrada não pertencer ao tenant ou ao escopo do device.
        """
        from pathlib import Path as _Path
        import uuid as _uuid_mod

        # Verifica se entrada pertence ao tenant
        entrada = await self.get_or_fail(entrada_id)

        # Verifica se entrada pertence ao escopo do device
        if entrada.unidade_produtiva_id and entrada.unidade_produtiva_id not in device.fazenda_ids:
            raise BusinessRuleError("Entrada fora do escopo do dispositivo autenticado.")

        # Idempotência: verifica se já existe foto com este local_evidence_id para esta entrada
        stmt_existente = select(CadernoCampoFoto).where(
            CadernoCampoFoto.entrada_id == entrada_id,
            CadernoCampoFoto.device_local_id == local_evidence_id,
        )
        foto_existente = (await self.session.execute(stmt_existente)).scalar_one_or_none()
        if foto_existente:
            return foto_existente

        # Gera path no storage usando convenção padrão do StorageService
        ext = _Path(filename).suffix or ".jpg"
        unique = _uuid_mod.uuid4().hex[:8]
        storage_path = f"static/fotos_caderno/{entrada.tenant_id}/{unique}_{_uuid_mod.uuid4().hex[:8]}{ext}"

        StorageService.save_blob(file_content, storage_path)
        url = StorageService.public_url(storage_path)

        from core.services.storage_service import increment_storage
        await increment_storage(self.session, self.tenant_id, len(file_content))

        foto = CadernoCampoFoto(
            entrada_id=entrada_id,
            url=url,
            storage_path=storage_path,
            device_local_id=local_evidence_id,
            device_id=device.id,
            mime_type=mime_type,
            size_bytes=size_bytes,
            latitude=latitude,
            longitude=longitude,
            data_captura=_to_naive_utc(captured_at),
        )
        self.session.add(foto)
        await self.session.flush()

        # Se for EPI_ENTREGA, atualiza o assinatura_url em EPIEntrega
        if entrada.tipo == "EPI_ENTREGA":
            if entrada.origem_id:
                try:
                    epi_id = UUID(entrada.origem_id)
                    stmt_epi = select(EPIEntrega).where(
                        and_(
                            EPIEntrega.id == epi_id,
                            EPIEntrega.tenant_id == entrada.tenant_id
                        )
                    )
                    res = await self.session.execute(stmt_epi)
                    epi_obj = res.scalar_one_or_none()
                    if epi_obj:
                        epi_obj.assinatura_url = url
                except ValueError:
                    pass

        await self.session.flush()
        return foto

    async def criar_entrada(self, dados: EntradaCreate, usuario_id: UUID, ip: str | None = None) -> CadernoCampoEntrada:
        if dados.digitalizacao_retroativa:
            self._validar_edicao_retroativa(dados.data_registro, dados.justificativa_retroativa)

        tipo_evento = self._resolver_tipo_evento(dados)
        origem_evento = self._resolver_origem_evento(dados)
        origem_tecnica = self._resolver_origem_tecnica(dados)
        origem_id = dados.origem_id or str(uuid.uuid4())
        status_evento = _validar_domino(dados.status_evento, STATUS_EVENTO_VALIDOS, "status_evento", self._status_inicial_padrao(
            tipo_evento,
            origem_evento,
            dados.digitalizacao_retroativa,
        ))
        status_evento = validar_transicao_status_evento(
            None,
            status_evento,
            {
                "tipo_evento": tipo_evento,
                "origem_evento": origem_evento,
                "digitalizacao_retroativa": dados.digitalizacao_retroativa,
                "tem_evidencias": False,
                "usuario_role": "SYSTEM",
                "is_system": True,
            },
        )

        if dados.executado_por_pessoa_id:
            stmt = select(Pessoa).where(
                Pessoa.id == dados.executado_por_pessoa_id,
                Pessoa.tenant_id == self.tenant_id
            )
            pessoa = (await self.session.execute(stmt)).scalar_one_or_none()
            if not pessoa:
                raise BusinessRuleError("Pessoa não encontrada neste tenant.")

            from core.cadastros.propriedades.models import AreaRural
            from core.cadastros.pessoas.models import PessoaRelacionamento
            from sqlalchemy import exists, and_, or_

            talhao = (await self.session.execute(select(AreaRural).where(AreaRural.id == dados.talhao_id))).scalar_one_or_none()
            if not talhao:
                raise BusinessRuleError("Talhão não encontrado.")

            stmt_rel = select(exists().where(
                and_(
                    PessoaRelacionamento.pessoa_id == dados.executado_por_pessoa_id,
                    PessoaRelacionamento.unidade_produtiva_id == talhao.unidade_produtiva_id,
                    or_(
                        PessoaRelacionamento.ativo_desde.is_(None),
                        PessoaRelacionamento.ativo_desde <= dados.data_registro
                    ),
                    or_(
                        PessoaRelacionamento.ativo_ate.is_(None),
                        PessoaRelacionamento.ativo_ate >= dados.data_registro
                    )
                )
            ))
            tem_relacionamento = (await self.session.execute(stmt_rel)).scalar()
            if not tem_relacionamento:
                raise BusinessRuleError("Pessoa selecionada não possui relacionamento válido com a Unidade Produtiva neste período.")

        if dados.origem_evento and dados.origem_id:
            existente = await self.obter_por_origem(origem_evento, origem_id)
            if existente:
                return existente

        entrada = CadernoCampoEntrada(
            tenant_id=self.tenant_id,
            safra_id=dados.safra_id,
            talhao_id=dados.talhao_id,
            tipo=tipo_evento,
            tipo_evento=tipo_evento,
            descricao=dados.descricao,
            data_registro=dados.data_registro,
            usuario_id=usuario_id,
            executado_por_pessoa_id=dados.executado_por_pessoa_id,
            origem_evento=origem_evento,
            origem_id=origem_id,
            origem_tecnica=origem_tecnica,
            status_evento=status_evento,
            nivel_severidade=dados.nivel_severidade,
            recomendacao=dados.recomendacao,
            numero_receituario=dados.numero_receituario,
            digitalizacao_retroativa=dados.digitalizacao_retroativa,
            justificativa_retroativa=dados.justificativa_retroativa,
            ip_dispositivo=ip,
        )
        self.session.add(entrada)
        await self.session.flush()
        await self._registrar_historico_status(
            entrada,
            status_anterior=None,
            status_novo=entrada.status_evento,
            justificativa=dados.justificativa_retroativa,
            usuario_id=usuario_id,
        )
        return entrada

    async def reprocessar_entrada(
        self,
        entrada_id: UUID,
        *,
        motivo: str,
        dados_corrigidos: dict[str, Any],
        usuario_id: UUID,
        usuario_role: str | None = None,
        ip: str | None = None,
    ) -> CadernoCampoEntrada:
        origem = await self.get_or_fail(entrada_id)
        usuario_role_norm = _normalizar_chave(usuario_role)
        if origem.retificado_por_evento_id:
            raise BusinessRuleError("Este evento já foi retificado. Use a versão vigente para nova correção.")

        if _normalizar_chave(origem.status_evento) == "CONSOLIDADO" and usuario_role_norm not in {"ADMIN", "AGRONOMO", "GERENTE", "OWNER"}:
            raise BusinessRuleError("Evento consolidado exige permissão superior para retificação.")

        payload = self._aplicar_dados_corrigidos(origem, dados_corrigidos)

        if payload.get("executado_por_pessoa_id"):
            stmt = select(Pessoa).where(
                Pessoa.id == payload["executado_por_pessoa_id"],
                Pessoa.tenant_id == self.tenant_id
            )
            pessoa = (await self.session.execute(stmt)).scalar_one_or_none()
            if not pessoa:
                raise BusinessRuleError("Pessoa não encontrada neste tenant.")

            from core.cadastros.propriedades.models import AreaRural
            from core.cadastros.pessoas.models import PessoaRelacionamento
            from sqlalchemy import exists, and_, or_

            talhao = (await self.session.execute(select(AreaRural).where(AreaRural.id == payload["talhao_id"]))).scalar_one_or_none()
            if not talhao:
                raise BusinessRuleError("Talhão não encontrado.")

            stmt_rel = select(exists().where(
                and_(
                    PessoaRelacionamento.pessoa_id == payload["executado_por_pessoa_id"],
                    PessoaRelacionamento.unidade_produtiva_id == talhao.unidade_produtiva_id,
                    or_(
                        PessoaRelacionamento.ativo_desde.is_(None),
                        PessoaRelacionamento.ativo_desde <= payload["data_registro"]
                    ),
                    or_(
                        PessoaRelacionamento.ativo_ate.is_(None),
                        PessoaRelacionamento.ativo_ate >= payload["data_registro"]
                    )
                )
            ))
            tem_relacionamento = (await self.session.execute(stmt_rel)).scalar()
            if not tem_relacionamento:
                raise BusinessRuleError("Pessoa selecionada não possui relacionamento válido com a Unidade Produtiva neste período.")

        if origem.tipo_evento in TIPOS_EVENTO_QUE_EXIGEM_APROVACAO or origem.origem_evento == "PWA_OFFLINE":
            payload["status_evento"] = "PENDENTE_APROVACAO"
        elif _normalizar_chave(origem.status_evento) in {"REJEITADO", "CANCELADO"}:
            payload["status_evento"] = "PENDENTE_APROVACAO"

        if payload["status_evento"] not in STATUS_EVENTO_VALIDOS:
            payload["status_evento"] = "PENDENTE_APROVACAO"

        nova_entrada = CadernoCampoEntrada(
            tenant_id=self.tenant_id,
            safra_id=payload["safra_id"],
            talhao_id=payload["talhao_id"],
            tipo=payload["tipo"],
            tipo_evento=payload["tipo_evento"],
            descricao=payload["descricao"],
            data_registro=payload["data_registro"],
            usuario_id=usuario_id,
            executado_por_pessoa_id=payload.get("executado_por_pessoa_id"),
            operacao_id=origem.operacao_id,
            origem_evento=payload["origem_evento"],
            origem_id=payload["origem_id"],
            origem_tecnica=payload["origem_tecnica"],
            status_evento=payload["status_evento"],
            nivel_severidade=payload["nivel_severidade"],
            recomendacao=payload["recomendacao"],
            numero_receituario=payload["numero_receituario"],
            digitalizacao_retroativa=payload["digitalizacao_retroativa"],
            justificativa_retroativa=payload["justificativa_retroativa"],
            ip_dispositivo=ip,
            retifica_evento_id=origem.id,
            motivo_retificacao=motivo,
        )
        self.session.add(nova_entrada)
        await self.session.flush()

        payload_before = _serialize(origem)
        origem.retificado_por_evento_id = nova_entrada.id
        origem.retificado_em = datetime.utcnow()
        origem.retificado_por_usuario_id = usuario_id
        origem.motivo_retificacao = motivo
        self.session.add(origem)
        await self.session.flush()

        await write_audit_log(
            self.session,
            tenant_id=self.tenant_id,
            user_id=usuario_id,
            action="retify",
            resource="caderno_campo_entradas",
            resource_id=origem.id,
            payload_before=payload_before,
            payload_after=_serialize(origem),
            ip_address=ip,
        )

        await self._registrar_historico_status(
            nova_entrada,
            status_anterior=None,
            status_novo=nova_entrada.status_evento,
            justificativa=motivo,
            usuario_id=usuario_id,
        )

        await write_audit_log(
            self.session,
            tenant_id=self.tenant_id,
            user_id=usuario_id,
            action="reprocess",
            resource="caderno_campo_entradas",
            resource_id=nova_entrada.id,
            payload_before=payload_before,
            payload_after=_serialize(nova_entrada),
            ip_address=ip,
        )
        return nova_entrada

    async def update(self, id: Any, obj_in: Any) -> CadernoCampoEntrada:
        entrada = await self.get_or_fail(id)
        if _normalizar_chave(entrada.status_evento) == "CONSOLIDADO" or entrada.retificado_por_evento_id:
            raise BusinessRuleError("Eventos consolidados ou já retificados devem ser corrigidos via reprocessamento.")
        return await super().update(id, obj_in)

    async def soft_delete(self, entrada_id: UUID, motivo: str) -> CadernoCampoEntrada:
        entrada = await self.get_or_fail(entrada_id)
        status_anterior = entrada.status_evento
        entrada.excluida = True
        entrada.motivo_exclusao = motivo
        if entrada.status_evento not in {"CANCELADO", "REJEITADO"}:
            entrada.status_evento = "CANCELADO"
        await self.session.flush()
        if entrada.status_evento != status_anterior:
            await self._registrar_historico_status(
                entrada,
                status_anterior=status_anterior,
                status_novo=entrada.status_evento,
                justificativa=motivo,
            )
        return entrada

    async def alterar_status_evento(
        self,
        entrada_id: UUID,
        *,
        novo_status: StatusEventoCaderno,
        justificativa: str | None,
        usuario_id: UUID,
        usuario_role: str | None = None,
        ip: str | None = None,
    ) -> CadernoCampoEntrada:
        entrada = await self.get_or_fail(entrada_id)
        status_anterior = entrada.status_evento
        status_normalizado = validar_transicao_status_evento(
            status_anterior,
            novo_status,
            {
                "tipo_evento": entrada.tipo_evento or entrada.tipo,
                "origem_evento": entrada.origem_evento or ORIGEM_EVENTO_MANUAL,
                "digitalizacao_retroativa": entrada.digitalizacao_retroativa,
                "tem_evidencias": bool(entrada.fotos),
                "usuario_role": usuario_role,
                "justificativa": justificativa,
                "is_system": False,
            },
        )
        if status_normalizado == status_anterior:
            return entrada

        payload_before = _serialize(entrada)
        entrada.status_evento = status_normalizado
        self.session.add(entrada)
        await self.session.flush()

        await self._registrar_historico_status(
            entrada,
            status_anterior=status_anterior,
            status_novo=status_normalizado,
            justificativa=justificativa,
            usuario_id=usuario_id,
        )

        await write_audit_log(
            self.session,
            tenant_id=self.tenant_id,
            user_id=usuario_id,
            action="update_status",
            resource="caderno_campo_entradas",
            resource_id=entrada.id,
            payload_before=payload_before,
            payload_after=_serialize(entrada),
            ip_address=ip,
        )
        return entrada

    async def adicionar_foto(
        self,
        entrada_id: UUID,
        url: str,
        latitude: float | None = None,
        longitude: float | None = None,
        data_captura: datetime | None = None,
    ) -> CadernoCampoFoto:
        foto = CadernoCampoFoto(
            entrada_id=entrada_id,
            url=url,
            latitude=latitude,
            longitude=longitude,
            data_captura=data_captura,
        )
        self.session.add(foto)
        await self.session.flush()
        return foto

    async def timeline(
        self,
        safra_id: UUID,
        talhao_id: UUID | None = None,
        tipo: str | None = None,
        data_inicio: date | None = None,
        data_fim: date | None = None,
        incluir_excluidas: bool = False,
    ) -> list[TimelineItem]:
        """Agrega entradas manuais + operações automáticas numa timeline cronológica."""
        # 1. Entradas manuais do caderno
        stmt = select(CadernoCampoEntrada).where(
            CadernoCampoEntrada.tenant_id == self.tenant_id,
            CadernoCampoEntrada.safra_id == safra_id,
        )
        if not incluir_excluidas:
            stmt = stmt.where(CadernoCampoEntrada.excluida == False)
        if talhao_id:
            stmt = stmt.where(CadernoCampoEntrada.talhao_id == talhao_id)
        if tipo:
            tipo_evento = _mapear_tipo_evento_legado(tipo)
            stmt = stmt.where(
                (CadernoCampoEntrada.tipo == tipo_evento) | (CadernoCampoEntrada.tipo_evento == tipo_evento)
            )
        if data_inicio:
            stmt = stmt.where(CadernoCampoEntrada.data_registro >= data_inicio)
        if data_fim:
            stmt = stmt.where(CadernoCampoEntrada.data_registro <= data_fim)
        stmt = stmt.order_by(CadernoCampoEntrada.data_registro.desc())

        entradas = list((await self.session.execute(stmt)).scalars().all())

        # 2. Operações automáticas NÃO vinculadas a entradas do caderno
        # (fallback: se o trigger não foi executado ou entrada foi excluída)
        op_stmt = select(OperacaoAgricola).where(
            OperacaoAgricola.tenant_id == self.tenant_id,
            OperacaoAgricola.safra_id == safra_id,
            OperacaoAgricola.status == "REALIZADA",
        ).options(selectinload(OperacaoAgricola.insumos))
        if talhao_id:
            op_stmt = op_stmt.where(OperacaoAgricola.talhao_id == talhao_id)
        if data_inicio:
            op_stmt = op_stmt.where(OperacaoAgricola.data_realizada >= data_inicio)
        if data_fim:
            op_stmt = op_stmt.where(OperacaoAgricola.data_realizada <= data_fim)
        op_stmt = op_stmt.order_by(OperacaoAgricola.data_realizada.desc())

        operacoes = list((await self.session.execute(op_stmt)).scalars().all())

        # IDs de operações já vinculadas a entradas para evitar duplicidade
        op_ids_vinculados = {e.operacao_id for e in entradas if e.operacao_id}

        items: list[TimelineItem] = []

        for e in entradas:
            tipo_evento = e.tipo_evento or _mapear_tipo_evento_legado(e.tipo)
            status_flags = _status_flags(e.status_evento)
            versao_vigente = self._entrada_eh_vigente(e)
            items.append(TimelineItem(
                id=e.id,
                tipo=tipo_evento,
                tipo_evento=tipo_evento,
                subtipo=e.tipo if e.tipo != tipo_evento else None,
                descricao=e.descricao,
                data_registro=e.data_registro,
                talhao_id=e.talhao_id,
                status_evento=e.status_evento,
                status_evento_atualizado_em=e.updated_at,
                pendente_aprovacao=status_flags["pendente_aprovacao"],
                aprovado=status_flags["aprovado"],
                consolidado=status_flags["consolidado"],
                rejeitado=status_flags["rejeitado"],
                nivel_severidade=e.nivel_severidade,
                fotos_count=len(e.fotos),
                excluida=e.excluida,
                origem="caderno",
                origem_evento=e.origem_evento,
                origem_id=e.origem_id,
                origem_tecnica=e.origem_tecnica,
                device_id=e.device_id,
                client_created_at=e.client_created_at,
                client_updated_at=e.client_updated_at,
                retifica_evento_id=e.retifica_evento_id,
                retificado_por_evento_id=e.retificado_por_evento_id,
                motivo_retificacao=e.motivo_retificacao,
                retificado_em=e.retificado_em,
                retificado_por_usuario_id=e.retificado_por_usuario_id,
                origem_invalidada=e.origem_invalidada,
                origem_invalidada_em=e.origem_invalidada_em,
                origem_invalidada_por=e.origem_invalidada_por,
                motivo_invalidacao_origem=e.motivo_invalidacao_origem,
                documental_status=self._documental_status(e),
                versao_vigente=versao_vigente,
                retificado=self._entrada_foi_retificada(e),
                retificador=self._entrada_eh_retificadora(e),
            ))

        for op in operacoes:
            if op.id in op_ids_vinculados:
                continue
            tipo_evento_op = mapear_operacao_para_evento_caderno(op)["tipo_evento"]
            if tipo and _mapear_tipo_evento_legado(tipo) != tipo_evento_op:
                continue
            status_flags = _status_flags(STATUS_EVENTO_PADRAO)
            items.append(TimelineItem(
                id=op.id,
                tipo=tipo_evento_op,
                tipo_evento=tipo_evento_op,
                subtipo=op.tipo,
                descricao=op.descricao,
                data_registro=op.data_realizada,
                talhao_id=op.talhao_id,
                status_evento=STATUS_EVENTO_PADRAO,
                status_evento_atualizado_em=op.updated_at,
                pendente_aprovacao=status_flags["pendente_aprovacao"],
                aprovado=status_flags["aprovado"],
                consolidado=status_flags["consolidado"],
                rejeitado=status_flags["rejeitado"],
                fotos_count=len(op.fotos) if op.fotos else 0,
                excluida=False,
                origem="operacao",
                origem_evento=ORIGEM_EVENTO_OPERACAO,
                origem_id=str(op.id),
                origem_tecnica=ORIGEM_TECNICA_OPERACAO,
                origem_invalidada=op.origem_invalidada,
                origem_invalidada_em=op.origem_invalidada_em,
                origem_invalidada_por=op.origem_invalidada_por,
                motivo_invalidacao_origem=op.motivo_invalidacao_origem,
                documental_status=DOCUMENTAL_STATUS_ORIGEM_INVALIDADA if op.origem_invalidada else DOCUMENTAL_STATUS_VIGENTE,
                versao_vigente=not op.origem_invalidada,
            ))

        # Ordena tudo por data desc
        items.sort(key=lambda x: x.data_registro, reverse=True)
        return items

    async def listar_eventos_oficiais_para_sync(
        self,
        *,
        unidade_produtiva_ids: list[UUID],
        updated_after: datetime | None = None,
    ) -> list[EventoCadernoOficialSync]:
        from core.cadastros.propriedades.models import AreaRural

        if not unidade_produtiva_ids:
            return []
        unidade_produtiva_ids_norm = {str(unidade_produtiva_id) for unidade_produtiva_id in unidade_produtiva_ids}

        stmt = (
            select(CadernoCampoEntrada)
            .where(
                CadernoCampoEntrada.tenant_id == self.tenant_id,
            )
            .order_by(CadernoCampoEntrada.data_registro.desc(), CadernoCampoEntrada.updated_at.desc())
        )
        if updated_after is not None:
            stmt = stmt.where(
                or_(
                    CadernoCampoEntrada.updated_at >= updated_after,
                    CadernoCampoEntrada.created_at >= updated_after,
                    CadernoCampoEntrada.retificado_em >= updated_after,
                    CadernoCampoEntrada.origem_invalidada_em >= updated_after,
                )
            )

        entradas = list((await self.session.execute(stmt)).scalars().all())
        if not entradas:
            return []

        talhao_ids = list({entrada.talhao_id for entrada in entradas})
        area_stmt = select(AreaRural.id, AreaRural.unidade_produtiva_id).where(
            AreaRural.tenant_id == self.tenant_id,
            AreaRural.id.in_(talhao_ids),
        )
        areas = (await self.session.execute(area_stmt)).all()
        area_por_talhao = {str(area_id): str(unidade_produtiva_id) for area_id, unidade_produtiva_id in areas}
        historico_stmt = (
            select(CadernoEventoStatusHistorico)
            .where(
                CadernoEventoStatusHistorico.tenant_id == self.tenant_id,
                CadernoEventoStatusHistorico.caderno_entrada_id.in_([entrada.id for entrada in entradas]),
            )
            .order_by(
                CadernoEventoStatusHistorico.caderno_entrada_id.asc(),
                CadernoEventoStatusHistorico.created_at.desc(),
            )
        )
        historicos = list((await self.session.execute(historico_stmt)).scalars().all())
        ultimo_historico_por_entrada: dict[UUID, CadernoEventoStatusHistorico] = {}
        for historico in historicos:
            ultimo_historico_por_entrada.setdefault(historico.caderno_entrada_id, historico)

        eventos: list[EventoCadernoOficialSync] = []
        for entrada in entradas:
            unidade_produtiva_id = (
                str(entrada.unidade_produtiva_id) if entrada.unidade_produtiva_id is not None else area_por_talhao.get(str(entrada.talhao_id))
            )
            if unidade_produtiva_id not in unidade_produtiva_ids_norm:
                continue
            local_id = entrada.origem_id if entrada.origem_evento == "PWA_OFFLINE" else None
            historico = ultimo_historico_por_entrada.get(entrada.id)
            eventos.append(
                EventoCadernoOficialSync(
                    server_id=entrada.id,
                    local_id=local_id,
                    device_id=str(entrada.device_id) if entrada.device_id is not None else None,
                    safra_id=entrada.safra_id,
                    talhao_id=entrada.talhao_id,
                    tipo=entrada.tipo,
                    tipo_evento=entrada.tipo_evento,
                    descricao=entrada.descricao,
                    data_registro=entrada.data_registro,
                    status_evento=entrada.status_evento,
                    documental_status=self._documental_status(entrada),
                    versao_vigente=self._entrada_eh_vigente(entrada),
                    retificado=self._entrada_foi_retificada(entrada),
                    retificador=self._entrada_eh_retificadora(entrada),
                    invalidado=bool(entrada.origem_invalidada),
                    origem_invalidada=bool(entrada.origem_invalidada),
                    motivo_invalidacao_origem=entrada.motivo_invalidacao_origem,
                    motivo_retificacao=entrada.motivo_retificacao,
                    retifica_evento_id=entrada.retifica_evento_id,
                    retificado_por_evento_id=entrada.retificado_por_evento_id,
                    justificativa=historico.justificativa if historico is not None else None,
                    updated_at=entrada.updated_at,
                    created_at=entrada.created_at,
                )
            )
        return eventos

    async def listar_safras_ativas(self, safra_id: UUID | None = None):
        from agricola.safras.models import Safra
        if safra_id:
            stmt = select(Safra).where(Safra.id == safra_id, Safra.tenant_id == self.tenant_id)
        else:
            stmt = select(Safra).where(
                Safra.tenant_id == self.tenant_id,
                Safra.status.notin_(["ENCERRADA", "CANCELADA"]),
            )
        return list((await self.session.execute(stmt)).scalars().all())

    async def listar_alertas(self, safra_id: UUID | None = None, dias_sem_registro: int = 7) -> list[dict]:
        from datetime import date, timedelta
        from agricola.operacoes.models import OperacaoAgricola
        safras = await self.listar_safras_ativas(safra_id)
        alertas = []
        limite = date.today() - timedelta(days=dias_sem_registro)
        safra_ids = [safra.id for safra in safras]
        ultima_entrada_por_safra: dict[UUID, date | None] = {}
        ultima_op_por_safra: dict[UUID, date | None] = {}

        if safra_ids:
            ultima_entrada_stmt = (
                select(
                    CadernoCampoEntrada.safra_id,
                    func.max(CadernoCampoEntrada.data_registro).label("ultima_data"),
                )
                .where(
                    CadernoCampoEntrada.tenant_id == self.tenant_id,
                    CadernoCampoEntrada.safra_id.in_(safra_ids),
                    CadernoCampoEntrada.excluida == False,
                )
                .group_by(CadernoCampoEntrada.safra_id)
            )
            for safra_id_row, ultima_data in (await self.session.execute(ultima_entrada_stmt)).all():
                ultima_entrada_por_safra[safra_id_row] = ultima_data

            ultima_op_stmt = (
                select(
                    OperacaoAgricola.safra_id,
                    func.max(OperacaoAgricola.data_realizada).label("ultima_data"),
                )
                .where(
                    OperacaoAgricola.tenant_id == self.tenant_id,
                    OperacaoAgricola.safra_id.in_(safra_ids),
                    OperacaoAgricola.status == "REALIZADA",
                )
                .group_by(OperacaoAgricola.safra_id)
            )
            for safra_id_row, ultima_op in (await self.session.execute(ultima_op_stmt)).all():
                ultima_op_por_safra[safra_id_row] = ultima_op

        for safra in safras:
            ultima_data = ultima_entrada_por_safra.get(safra.id)
            ultima_op = ultima_op_por_safra.get(safra.id)
            if ultima_data and ultima_op:
                ultima_registro = max(ultima_data, ultima_op) if isinstance(ultima_data, date) and isinstance(ultima_op, date) else (ultima_data or ultima_op)
            else:
                ultima_registro = ultima_data or ultima_op
            if ultima_registro and isinstance(ultima_registro, date):
                if ultima_registro < limite:
                    dias_desatualizada = (date.today() - ultima_registro).days
                    alertas.append({"safra_id": str(safra.id), "safra_nome": f"{safra.cultura} {safra.ano_safra}", "ultima_registro": ultima_registro.isoformat(), "dias_desatualizada": dias_desatualizada, "mensagem": f"Sem registros há {dias_desatualizada} dias (último: {ultima_registro.strftime('%d/%m/%Y')})."})
            elif not ultima_registro:
                alertas.append({"safra_id": str(safra.id), "safra_nome": f"{safra.cultura} {safra.ano_safra}", "ultima_registro": None, "dias_desatualizada": None, "mensagem": "Nenhum registro encontrado para esta safra."})
        return alertas



# Re-exportados para compatibilidade retroativa (classes extraídas para arquivos próprios
# por tamanho/responsabilidade — ver agricola/caderno/service_visita_epi.py e
# agricola/caderno/service_exportacao.py).
from agricola.caderno.service_visita_epi import VisitaTecnicaService, EPIEntregaService  # noqa: E402,F401
from agricola.caderno.service_exportacao import CadernoExportacaoService  # noqa: E402,F401
