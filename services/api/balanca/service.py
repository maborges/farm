from __future__ import annotations

import uuid
import secrets
import string
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from jose import jwt
from loguru import logger

from core.config import settings
from core.exceptions import EntityNotFoundError, BusinessRuleError, TenantViolationError

from balanca.models import DispositivoBalanca, OperadorBalanca, OrdemPesagem, Pesagem, SyncTombstoneBalanca
from balanca.schemas import (
    DeviceCreate,
    DeviceActivateRequest,
    DeviceReactivateRequest,
    OperadorCreate,
    OperadorLoginRequest,
    SolicitarPesagemRequest,
    ReatribuirOrdemRequest,
    SyncPushItem,
    SyncPushItemResult,
    ETAPAS_POR_TIPO_PESAGEM,
)

_ACTIVATION_CODE_CHARS = string.ascii_uppercase + string.digits
_ACTIVATION_TTL_MINUTES = 30


def _generate_activation_code(length: int = 8) -> str:
    return "".join(secrets.choice(_ACTIVATION_CODE_CHARS) for _ in range(length))


def _to_naive_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def _parse_dt(value: datetime | None) -> datetime | None:
    return _to_naive_utc(value)


def _to_decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _make_device_jwt(device: DispositivoBalanca) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "type": "device_balanca",
        "device_id": str(device.id),
        "tenant_id": str(device.tenant_id),
        "fazenda_ids": [str(fid) for fid in device.fazenda_ids],
        "iat": int(now.timestamp()),
        "exp": int(_to_naive_utc(device.expires_at).replace(tzinfo=timezone.utc).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def _gerar_numero_ticket() -> str:
    hoje = datetime.utcnow().strftime("%Y%m%d")
    sufixo = uuid.uuid4().hex[:6].upper()
    return f"BAL-{hoje}-{sufixo}"


class DispositivoService:
    """Gestão da estação de balança — dispositivo fixo, sem vínculo a um operador."""

    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        self.session = session
        self.tenant_id = tenant_id

    async def criar(self, data: DeviceCreate) -> DispositivoBalanca:
        if not data.fazenda_ids:
            raise BusinessRuleError("Selecione ao menos uma fazenda autorizada para a estação de balança.")

        expires_at = datetime.utcnow() + timedelta(days=data.expires_days)
        activation_code = _generate_activation_code()
        activation_expires = datetime.utcnow() + timedelta(minutes=_ACTIVATION_TTL_MINUTES)

        device = DispositivoBalanca(
            tenant_id=self.tenant_id,
            nome=data.nome,
            fazenda_ids=data.fazenda_ids,
            status="PENDENTE",
            activation_code=activation_code,
            activation_code_expires_at=activation_expires,
            expires_at=expires_at,
        )
        self.session.add(device)
        await self.session.flush()
        return device

    async def ativar(self, req: DeviceActivateRequest) -> tuple[DispositivoBalanca, str]:
        result = await self.session.execute(
            select(DispositivoBalanca).where(
                and_(
                    DispositivoBalanca.activation_code == req.activation_code,
                    DispositivoBalanca.status == "PENDENTE",
                )
            )
        )
        device = result.scalar_one_or_none()
        if not device:
            raise EntityNotFoundError("Código de ativação inválido ou já utilizado.")

        if _to_naive_utc(device.activation_code_expires_at) < datetime.utcnow():
            raise BusinessRuleError("Código de ativação expirado. Solicite um novo código.")

        if device.tenant_id != self.tenant_id:
            raise TenantViolationError("Código pertence a outro tenant.", tenant_id=self.tenant_id)

        device.device_fingerprint = req.device_fingerprint
        device.pin_hash = req.pin_hash
        device.status = "ATIVO"
        device.activation_code = None
        device.activation_code_expires_at = None
        await self.session.flush()

        token = _make_device_jwt(device)
        return device, token

    async def revogar(self, device_id: uuid.UUID, revoked_by: uuid.UUID | None) -> DispositivoBalanca:
        device = await self.session.get(DispositivoBalanca, device_id)
        if not device or device.tenant_id != self.tenant_id:
            raise EntityNotFoundError(f"Dispositivo {device_id} não encontrado.")

        device.status = "REVOGADO"
        device.revoked_at = datetime.utcnow()
        device.revoked_by = revoked_by
        await self.session.flush()
        return device

    async def reativar(self, data: DeviceReactivateRequest) -> tuple[DispositivoBalanca, str]:
        device = await self.session.get(DispositivoBalanca, data.device_id)
        if not device or device.tenant_id != self.tenant_id:
            raise EntityNotFoundError(f"Dispositivo {data.device_id} não encontrado.")
        if not device.fazenda_ids:
            raise BusinessRuleError("Estação sem fazendas autorizadas. Refaça o cadastro antes de reativar.")

        activation_code = _generate_activation_code()
        activation_expires = datetime.utcnow() + timedelta(minutes=_ACTIVATION_TTL_MINUTES)
        device.status = "PENDENTE"
        device.activation_code = activation_code
        device.activation_code_expires_at = activation_expires
        device.expires_at = datetime.utcnow() + timedelta(days=data.expires_days)
        device.revoked_at = None
        device.revoked_by = None
        device.device_fingerprint = None
        await self.session.flush()
        return device, activation_code

    async def listar(self, skip: int = 0, limit: int = 100) -> list[DispositivoBalanca]:
        result = await self.session.execute(
            select(DispositivoBalanca)
            .where(DispositivoBalanca.tenant_id == self.tenant_id)
            .order_by(DispositivoBalanca.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def atualizar_last_sync(self, device_id: uuid.UUID) -> None:
        device = await self.session.get(DispositivoBalanca, device_id)
        if device:
            device.last_sync_at = datetime.utcnow()
            device.last_seen_at = datetime.utcnow()


class OperadorService:
    """Cadastro de operadores habilitados a pesar (qualquer estação do tenant) e
    autenticação por PIN pessoal — distinto do PIN da estação (DispositivoBalanca)."""

    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        self.session = session
        self.tenant_id = tenant_id

    async def criar(self, data: OperadorCreate) -> OperadorBalanca:
        existente = (
            await self.session.execute(
                select(OperadorBalanca).where(
                    OperadorBalanca.tenant_id == self.tenant_id,
                    OperadorBalanca.pessoa_id == data.pessoa_id,
                )
            )
        ).scalar_one_or_none()
        if existente:
            raise BusinessRuleError("Esta pessoa já está cadastrada como operador de balança.")

        operador = OperadorBalanca(
            tenant_id=self.tenant_id,
            pessoa_id=data.pessoa_id,
            nome_exibicao=data.nome_exibicao,
            pin_hash=data.pin_hash,
            status="ATIVO",
        )
        self.session.add(operador)
        await self.session.flush()
        return operador

    async def revogar(self, operador_id: uuid.UUID, revoked_by: uuid.UUID | None) -> OperadorBalanca:
        operador = await self.session.get(OperadorBalanca, operador_id)
        if not operador or operador.tenant_id != self.tenant_id:
            raise EntityNotFoundError(f"Operador {operador_id} não encontrado.")
        operador.status = "REVOGADO"
        operador.revoked_at = datetime.utcnow()
        operador.revoked_by = revoked_by
        await self.session.flush()
        return operador

    async def listar(self, skip: int = 0, limit: int = 100) -> list[OperadorBalanca]:
        result = await self.session.execute(
            select(OperadorBalanca)
            .where(OperadorBalanca.tenant_id == self.tenant_id)
            .order_by(OperadorBalanca.nome_exibicao.asc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def listar_ativos(self) -> list[OperadorBalanca]:
        result = await self.session.execute(
            select(OperadorBalanca)
            .where(OperadorBalanca.tenant_id == self.tenant_id, OperadorBalanca.status == "ATIVO")
            .order_by(OperadorBalanca.nome_exibicao.asc())
        )
        return list(result.scalars().all())

    async def login(self, data: OperadorLoginRequest) -> OperadorBalanca:
        from core.services.auth_service import AuthService

        operador = await self.session.get(OperadorBalanca, data.operador_id)
        if not operador or operador.tenant_id != self.tenant_id:
            raise EntityNotFoundError(f"Operador {data.operador_id} não encontrado.")
        if operador.status != "ATIVO":
            raise BusinessRuleError("Operador revogado — não pode registrar pesagens.")
        if not AuthService(self.session).verify_password(data.pin, operador.pin_hash):
            raise BusinessRuleError("PIN inválido.")
        return operador


class PesagemService:
    """API interna de pesagem. Módulos clientes (romaneio/colheita, compras, vendas,
    pecuária, pessoas) chamam `solicitar_pesagem()` sem que a Balança precise conhecer
    a lógica interna desses módulos — vínculo apenas por origem_tipo/origem_id."""

    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        self.session = session
        self.tenant_id = tenant_id

    async def solicitar_pesagem(self, data: SolicitarPesagemRequest) -> OrdemPesagem:
        ordem = OrdemPesagem(
            tenant_id=self.tenant_id,
            origem_tipo=data.origem_tipo,
            origem_id=data.origem_id,
            subject_type=data.subject_type,
            tipo_pesagem=data.tipo_pesagem,
            status="PENDENTE",
            solicitado_por=data.solicitado_por,
            contexto=data.contexto,
            produto_id=data.produto_id,
            produto_tipo=data.produto_tipo,
            tipo_volume=data.tipo_volume,
            quantidade_volumes=data.quantidade_volumes,
            data_agendada=data.data_agendada,
            numero_documento_fiscal=data.numero_documento_fiscal,
        )
        self.session.add(ordem)
        await self.session.flush()
        return ordem

    async def cancelar_ordem(self, ordem_id: uuid.UUID, motivo: str) -> OrdemPesagem:
        ordem = await self.session.get(OrdemPesagem, ordem_id)
        if not ordem or ordem.tenant_id != self.tenant_id:
            raise EntityNotFoundError(f"Ordem de pesagem {ordem_id} não encontrada.")
        if ordem.status == "CONCLUIDA":
            raise BusinessRuleError("Ordem já concluída não pode ser cancelada.")

        ordem.status = "CANCELADA"
        ordem.cancelada_em = datetime.utcnow()
        ordem.motivo_cancelamento = motivo
        await self.session.flush()
        return ordem

    async def obter_ordem(self, ordem_id: uuid.UUID) -> OrdemPesagem:
        ordem = await self.session.get(OrdemPesagem, ordem_id)
        if not ordem or ordem.tenant_id != self.tenant_id:
            raise EntityNotFoundError(f"Ordem de pesagem {ordem_id} não encontrada.")
        return ordem

    async def listar_ordens(
        self, status_filtro: str | None = None, skip: int = 0, limit: int = 100
    ) -> list[OrdemPesagem]:
        stmt = select(OrdemPesagem).where(OrdemPesagem.tenant_id == self.tenant_id)
        if status_filtro:
            stmt = stmt.where(OrdemPesagem.status == status_filtro)
        stmt = stmt.order_by(OrdemPesagem.created_at.desc()).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def listar_pesagens_por_ordem(self, ordem_id: uuid.UUID) -> list[Pesagem]:
        result = await self.session.execute(
            select(Pesagem)
            .where(Pesagem.tenant_id == self.tenant_id, Pesagem.ordem_id == ordem_id)
            .order_by(Pesagem.created_at.asc())
        )
        return list(result.scalars().all())

    async def listar_pendentes_reconciliacao(self, skip: int = 0, limit: int = 100) -> list[OrdemPesagem]:
        """Pesagens avulsas (sem processo de origem definido no momento da pesagem) —
        criadas automaticamente pela estação quando não há OrdemPesagem prévia."""
        stmt = (
            select(OrdemPesagem)
            .where(
                OrdemPesagem.tenant_id == self.tenant_id,
                OrdemPesagem.origem_tipo == "OUTRO",
                OrdemPesagem.origem_id.is_(None),
            )
            .order_by(OrdemPesagem.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def reatribuir_ordem(self, ordem_id: uuid.UUID, data: ReatribuirOrdemRequest) -> OrdemPesagem:
        """Reconciliação: associa uma pesagem avulsa ao processo real de outro módulo."""
        ordem = await self.session.get(OrdemPesagem, ordem_id)
        if not ordem or ordem.tenant_id != self.tenant_id:
            raise EntityNotFoundError(f"Ordem de pesagem {ordem_id} não encontrada.")

        ordem.origem_tipo = data.origem_tipo
        ordem.origem_id = data.origem_id
        if data.contexto:
            ordem.contexto = {**ordem.contexto, **data.contexto}
        await self.session.flush()
        return ordem


class SyncService:
    """Push/pull offline-first, mesmo padrão de campo/service.py: idempotência por
    client_id, resolução de conflito 'servidor vence' e tombstones para deleções."""

    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID, device: DispositivoBalanca):
        self.session = session
        self.tenant_id = tenant_id
        self.device = device

    async def pull(self, last_sync_at: datetime | None) -> dict[str, Any]:
        fazenda_ids = [uuid.UUID(str(fid)) for fid in self.device.fazenda_ids]

        stmt = select(OrdemPesagem).where(
            and_(
                OrdemPesagem.tenant_id == self.tenant_id,
                OrdemPesagem.status.in_(["PENDENTE", "EM_PESAGEM"]),
            )
        )
        ordens_rows = (await self.session.execute(stmt)).scalars().all()

        etapas_por_ordem: dict[uuid.UUID, list[str]] = {}
        if ordens_rows:
            stmt_etapas = select(Pesagem.ordem_id, Pesagem.etapa).where(
                Pesagem.tenant_id == self.tenant_id,
                Pesagem.ordem_id.in_([o.id for o in ordens_rows]),
            )
            for ordem_id, etapa in (await self.session.execute(stmt_etapas)).all():
                etapas_por_ordem.setdefault(ordem_id, []).append(etapa)

        last_sync_at_naive = _to_naive_utc(last_sync_at)
        tombstones: dict[str, list[str]] = {"ordens": []}
        if last_sync_at_naive:
            stmt_tomb = select(SyncTombstoneBalanca).where(
                and_(
                    SyncTombstoneBalanca.tenant_id == self.tenant_id,
                    SyncTombstoneBalanca.deleted_at > last_sync_at_naive,
                )
            )
            for t in (await self.session.execute(stmt_tomb)).scalars().all():
                if t.entity_type in tombstones:
                    tombstones[t.entity_type].append(t.entity_id)

        return {
            "sync_at": datetime.utcnow(),
            "ordens_pendentes": [
                {
                    "id": o.id,
                    "origem_tipo": o.origem_tipo,
                    "origem_id": o.origem_id,
                    "subject_type": o.subject_type,
                    "tipo_pesagem": o.tipo_pesagem,
                    "status": o.status,
                    "contexto": o.contexto,
                    "produto_id": o.produto_id,
                    "produto_tipo": o.produto_tipo,
                    "tipo_volume": o.tipo_volume,
                    "quantidade_volumes": o.quantidade_volumes,
                    "data_agendada": o.data_agendada,
                    "numero_documento_fiscal": o.numero_documento_fiscal,
                    "etapas_realizadas": etapas_por_ordem.get(o.id, []),
                    "created_at": o.created_at,
                }
                for o in ordens_rows
            ],
            "tombstones": tombstones,
        }

    async def push(self, items: list[SyncPushItem]) -> list[SyncPushItemResult]:
        results: list[SyncPushItemResult] = []
        for item in items:
            try:
                result = await self._process_item(item)
                results.append(result)
            except Exception as exc:
                logger.warning(f"[balanca/sync/push] Erro ao processar item {item.local_id}: {exc}")
                results.append(
                    SyncPushItemResult(local_id=item.local_id, status="ERROR", error_message=str(exc))
                )
        return results

    async def _process_item(self, item: SyncPushItem) -> SyncPushItemResult:
        if item.entity_type != "pesagem":
            return SyncPushItemResult(
                local_id=item.local_id,
                status="ERROR",
                error_message=f"Tipo de entidade não suportado: {item.entity_type}",
            )
        return await self._process_pesagem(item)

    async def _process_pesagem(self, item: SyncPushItem) -> SyncPushItemResult:
        payload = item.payload

        existing = (
            await self.session.execute(
                select(Pesagem).where(
                    and_(Pesagem.tenant_id == self.tenant_id, Pesagem.client_id == item.local_id)
                )
            )
        ).scalar_one_or_none()
        if existing:
            return SyncPushItemResult(local_id=item.local_id, status="CREATED", server_id=str(existing.id))

        if item.operation != "CREATE":
            # Cada pesagem é um evento físico imutável (uma etapa) — corrigir um
            # valor já registrado é fluxo de controle de qualidade (fase futura,
            # não sobrescreve o original), não um UPDATE do sync.
            return SyncPushItemResult(
                local_id=item.local_id,
                status="ERROR",
                error_message="Pesagem não suporta UPDATE — cada etapa é um evento novo.",
            )

        ordem_id = payload.get("ordem_id")
        if ordem_id:
            ordem = await self.session.get(OrdemPesagem, uuid.UUID(str(ordem_id)))
            if not ordem or ordem.tenant_id != self.tenant_id:
                return SyncPushItemResult(local_id=item.local_id, status="ERROR", error_message="Ordem de pesagem não encontrada")
            if ordem.status == "CANCELADA":
                return SyncPushItemResult(local_id=item.local_id, status="ERROR", error_message="Ordem cancelada não aceita pesagem")
        else:
            # Pesagem avulsa (sem ordem prévia do módulo cliente): a estação cria
            # uma ordem "sombra" (origem_tipo=OUTRO) que fica pendente de
            # reconciliação — ver PesagemService.reatribuir_ordem().
            subject_type = payload.get("subject_type")
            tipo_pesagem = payload.get("tipo_pesagem")
            if not subject_type or not tipo_pesagem:
                return SyncPushItemResult(
                    local_id=item.local_id,
                    status="ERROR",
                    error_message="Pesagem avulsa exige subject_type e tipo_pesagem.",
                )
            ordem = OrdemPesagem(
                tenant_id=self.tenant_id,
                origem_tipo="OUTRO",
                origem_id=None,
                subject_type=subject_type,
                tipo_pesagem=tipo_pesagem,
                status="PENDENTE",
                dispositivo_id=self.device.id,
                contexto={"origem": "pesagem_avulsa"},
            )
            self.session.add(ordem)
            await self.session.flush()

        etapas_esperadas = ETAPAS_POR_TIPO_PESAGEM.get(ordem.tipo_pesagem, ("UNICA",))
        etapa = payload.get("etapa") or (etapas_esperadas[0] if len(etapas_esperadas) else "UNICA")
        if etapa not in etapas_esperadas:
            return SyncPushItemResult(
                local_id=item.local_id,
                status="ERROR",
                error_message=f"Etapa {etapa!r} não é válida para tipo_pesagem={ordem.tipo_pesagem!r} (esperado: {etapas_esperadas}).",
            )

        etapa_ja_existe = (
            await self.session.execute(
                select(Pesagem.id).where(Pesagem.ordem_id == ordem.id, Pesagem.etapa == etapa)
            )
        ).scalar_one_or_none()
        if etapa_ja_existe:
            return SyncPushItemResult(
                local_id=item.local_id, status="ERROR", error_message=f"Etapa {etapa!r} já registrada para esta ordem."
            )

        pesagem = Pesagem(
            tenant_id=self.tenant_id,
            ordem_id=ordem.id,
            dispositivo_id=self.device.id,
            numero_ticket=payload.get("numero_ticket") or _gerar_numero_ticket(),
            client_id=item.local_id,
            etapa=etapa,
            peso_informado_kg=_to_decimal(payload.get("peso_informado_kg")),
            peso_aferido_kg=_to_decimal(payload.get("peso_aferido_kg")),
            peso_tara_kg=_to_decimal(payload.get("peso_tara_kg")),
            captured_via=payload.get("captured_via", "MANUAL"),
            leitura_bruta=payload.get("leitura_bruta"),
            placa=payload.get("placa"),
            motorista=payload.get("motorista"),
            animal_id=_to_uuid(payload.get("animal_id")),
            pessoa_id=_to_uuid(payload.get("pessoa_id")),
            operador_pessoa_id=_to_uuid(payload.get("operador_pessoa_id")),
            data_pesagem=_parse_dt_str(payload.get("data_pesagem")) or datetime.utcnow(),
            client_created_at=_parse_dt(item.client_created_at),
            client_updated_at=_parse_dt(item.client_updated_at),
        )
        self.session.add(pesagem)
        await self.session.flush()

        ordem.dispositivo_id = self.device.id
        await self._avaliar_conclusao_ordem(ordem, etapas_esperadas)
        await self.session.flush()

        return SyncPushItemResult(local_id=item.local_id, status="CREATED", server_id=str(pesagem.id))

    async def _avaliar_conclusao_ordem(self, ordem: OrdemPesagem, etapas_esperadas: tuple[str, ...]) -> None:
        """Calcula o peso líquido da ordem quando todas as etapas esperadas
        estiverem registradas, e marca a ordem como CONCLUIDA."""
        pesagens = (
            await self.session.execute(select(Pesagem).where(Pesagem.ordem_id == ordem.id))
        ).scalars().all()
        pesos_por_etapa = {p.etapa: p for p in pesagens}

        if not all(e in pesos_por_etapa for e in etapas_esperadas):
            ordem.status = "EM_PESAGEM"
            return

        if len(etapas_esperadas) == 1:
            pesagem_unica = pesos_por_etapa[etapas_esperadas[0]]
            aferido = pesagem_unica.peso_aferido_kg or Decimal("0")
            tara = pesagem_unica.peso_tara_kg or Decimal("0")
            peso_bruto, peso_tara = aferido, tara
        else:
            primeira = pesos_por_etapa[etapas_esperadas[0]].peso_aferido_kg or Decimal("0")
            segunda = pesos_por_etapa[etapas_esperadas[1]].peso_aferido_kg or Decimal("0")
            peso_bruto, peso_tara = max(primeira, segunda), min(primeira, segunda)

        ordem.peso_liquido_kg = peso_bruto - peso_tara
        ordem.status = "CONCLUIDA"
        ordem.concluida_em = datetime.utcnow()

        await self._notificar_pesagem_concluida(ordem, peso_bruto, peso_tara)

    async def _notificar_pesagem_concluida(
        self, ordem: OrdemPesagem, peso_bruto: Decimal, peso_tara: Decimal
    ) -> None:
        """Publica evento de domínio (outbox) para módulos clientes desacoplados
        reagirem — a Balança não conhece romaneio/compra/venda/pecuária, só
        avisa 'esta pesagem concluiu' via origem_tipo/origem_id."""
        from events.base import DomainEvent
        from events.helpers import publish_domain_event_safe
        from alert_engine.models import Domain

        event = DomainEvent(
            tenant_id=ordem.tenant_id,
            domain=Domain.OPERATIONS,
            event_type="balanca.pesagem.concluida",
            source_type="BALANCA_PESAGEM_CONCLUIDA",
            entity_type="ordem_pesagem",
            entity_id=ordem.id,
            metadata={
                "origem_tipo": ordem.origem_tipo,
                "origem_id": str(ordem.origem_id) if ordem.origem_id else None,
                "subject_type": ordem.subject_type,
                "tipo_pesagem": ordem.tipo_pesagem,
                "peso_bruto_kg": str(peso_bruto),
                "peso_tara_kg": str(peso_tara),
                "peso_liquido_kg": str(ordem.peso_liquido_kg),
            },
        )
        await publish_domain_event_safe(
            event,
            session=self.session,
            commit=False,
            logger_context={"component": "balanca_sync_service"},
        )


def _to_uuid(value: Any) -> uuid.UUID | None:
    if not value:
        return None
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError):
        return None


def _parse_dt_str(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return _to_naive_utc(value)
    try:
        return _to_naive_utc(datetime.fromisoformat(str(value)))
    except ValueError:
        return None
