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
from agricola.operacoes.models import OperacaoAgricola
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
        descricao += f"\nÁrea: {operacao.area_aplicada_ha} ha"
    if operacao.custo_total:
        descricao += f"\nCusto: R$ {operacao.custo_total:.2f}"
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
        entrada = CadernoCampoEntrada(
            tenant_id=self.tenant_id,
            safra_id=operacao.safra_id,
            talhao_id=operacao.talhao_id,
            tipo=payload["tipo"],
            tipo_evento=payload["tipo_evento"],
            descricao=payload["descricao"],
            data_registro=payload["data_registro"],
            usuario_id=UUID("00000000-0000-0000-0000-000000000000"),
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

        for evento in eventos:
            try:
                if evento.device_id != str(device.id):
                    raise BusinessRuleError("device_id do evento não confere com o dispositivo autenticado.")
                if evento.tenant_id != self.tenant_id:
                    raise BusinessRuleError("tenant_id do evento não confere com o tenant autenticado.")

                if not evento.talhao_id:
                    raise BusinessRuleError("Evento offline exige talhão para sincronização inicial.")

                safra = (await self.session.execute(
                    select(Safra).where(Safra.id == evento.safra_id, Safra.tenant_id == self.tenant_id)
                )).scalar_one_or_none()
                if not safra:
                    raise BusinessRuleError("Safra inválida para sincronização offline.")

                talhao = (await self.session.execute(
                    select(AreaRural).where(
                        AreaRural.id == evento.talhao_id,
                        AreaRural.tenant_id == self.tenant_id,
                    )
                )).scalar_one_or_none()
                if not talhao:
                    raise BusinessRuleError("Talhão inválido para sincronização offline.")

                if talhao.unidade_produtiva_id not in device.fazenda_ids:
                    raise BusinessRuleError("Talhão fora do escopo do dispositivo autenticado.")

                existente = await self.obter_por_origem("PWA_OFFLINE", evento.local_id)
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

                entrada = CadernoCampoEntrada(
                    tenant_id=self.tenant_id,
                    safra_id=evento.safra_id,
                    talhao_id=evento.talhao_id,
                    tipo=evento.tipo_evento,
                    tipo_evento=evento.tipo_evento,
                    descricao=descricao,
                    data_registro=data_registro,
                    usuario_id=evento.usuario_id or device.user_id,
                    operacao_id=evento.operacao_id,
                    origem_evento="PWA_OFFLINE",
                    origem_id=evento.local_id,
                    origem_tecnica="SYNC_PWA",
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
        )
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
        for safra in safras:
            ultima_entrada_stmt = select(func.max(CadernoCampoEntrada.data_registro)).where(
                CadernoCampoEntrada.tenant_id == self.tenant_id,
                CadernoCampoEntrada.safra_id == safra.id,
                CadernoCampoEntrada.excluida == False,
            )
            ultima_data = (await self.session.execute(ultima_entrada_stmt)).scalar_one_or_none()
            ultima_op_stmt = select(func.max(OperacaoAgricola.data_realizada)).where(
                OperacaoAgricola.tenant_id == self.tenant_id,
                OperacaoAgricola.safra_id == safra.id,
                OperacaoAgricola.status == "REALIZADA",
            )
            ultima_op = (await self.session.execute(ultima_op_stmt)).scalar_one_or_none()
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


class VisitaTecnicaService(BaseService[VisitaTecnica]):
    def __init__(self, session: AsyncSession, tenant_id: UUID):
        super().__init__(VisitaTecnica, session, tenant_id)

    async def criar(self, dados: VisitaTecnicaCreate, usuario_id: UUID) -> VisitaTecnica:
        visita = VisitaTecnica(
            tenant_id=self.tenant_id,
            safra_id=dados.safra_id,
            talhao_id=dados.talhao_id,
            responsavel_tecnico_id=usuario_id,
            nome_rt=dados.nome_rt,
            crea=dados.crea,
            data_visita=dados.data_visita,
            observacoes=dados.observacoes,
            recomendacoes=dados.recomendacoes,
            constatacoes=dados.constatacoes,
        )
        self.session.add(visita)
        await self.session.flush()
        return visita

    async def assinar(self, visita_id: UUID, nome_rt: str, crea: str) -> VisitaTecnica:
        visita = await self.get_or_fail(visita_id)
        if visita.assinado:
            raise BusinessRuleError("Visita técnica já foi assinada.")
        visita.assinado = True
        visita.data_assinatura = datetime.utcnow()
        visita.nome_rt = nome_rt
        visita.crea = crea
        await self.session.flush()
        return visita

    async def listar_por_safra(self, safra_id: UUID, talhao_id: UUID | None = None) -> list[VisitaTecnica]:
        stmt = select(VisitaTecnica).where(
            VisitaTecnica.tenant_id == self.tenant_id,
            VisitaTecnica.safra_id == safra_id,
        ).order_by(VisitaTecnica.data_visita.desc())
        if talhao_id:
            stmt = stmt.where(VisitaTecnica.talhao_id == talhao_id)
        return list((await self.session.execute(stmt)).scalars().all())


class EPIEntregaService(BaseService[EPIEntrega]):
    def __init__(self, session: AsyncSession, tenant_id: UUID):
        super().__init__(EPIEntrega, session, tenant_id)

    async def criar(self, dados: EPIEntregaCreate) -> EPIEntrega:
        epi = EPIEntrega(
            tenant_id=self.tenant_id,
            trabalhador_id=dados.trabalhador_id,
            nome_trabalhador=dados.nome_trabalhador,
            epi_tipo=dados.epi_tipo,
            quantidade=dados.quantidade,
            data_entrega=dados.data_entrega,
            validade=dados.validade,
            operacao_id=dados.operacao_id,
        )
        self.session.add(epi)
        await self.session.flush()
        return epi

    async def listar(self, operacao_id: UUID | None = None) -> list[EPIEntrega]:
        stmt = select(EPIEntrega).where(
            EPIEntrega.tenant_id == self.tenant_id,
        ).order_by(EPIEntrega.data_entrega.desc())
        if operacao_id:
            stmt = stmt.where(EPIEntrega.operacao_id == operacao_id)
        return list((await self.session.execute(stmt)).scalars().all())


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
                    # Busca operação para detalhes de insumos
                    op_stmt = select(OperacaoAgricola).where(OperacaoAgricola.id == e.operacao_id)
                    op = (await self.session.execute(op_stmt)).scalar_one_or_none()
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
                    op_stmt = select(OperacaoAgricola).where(OperacaoAgricola.id == e.operacao_id)
                    op = (await self.session.execute(op_stmt)).scalar_one_or_none()
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
