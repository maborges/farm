from __future__ import annotations
import uuid
import secrets
import string
from datetime import datetime, timedelta, timezone, date
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, update, or_
from jose import jwt
from loguru import logger

from core.config import settings
from core.exceptions import EntityNotFoundError, BusinessRuleError, TenantViolationError
from core.models.auth import Usuario

from campo.models import DispositivoCampo, TarefaCampo, SyncTombstone
from campo.schemas import (
    DeviceCreate,
    DeviceActivateRequest,
    SyncPushItem,
    SyncPushItemResult,
    TarefaProgramadaCreate,
    ExecucaoUpdate,
)

_ACTIVATION_CODE_CHARS = string.ascii_uppercase + string.digits
_ACTIVATION_TTL_MINUTES = 30


def _generate_activation_code(length: int = 8) -> str:
    return "".join(secrets.choice(_ACTIVATION_CODE_CHARS) for _ in range(length))


def _make_device_jwt(device: DispositivoCampo, user_name: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "type": "device",
        "device_id": str(device.id),
        "tenant_id": str(device.tenant_id),
        "sub": str(device.user_id),
        "user_name": user_name,
        "fazenda_ids": [str(fid) for fid in device.fazenda_ids],
        "modulos": device.modulos,
        "iat": int(now.timestamp()),
        "exp": int(device.expires_at.replace(tzinfo=timezone.utc).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


class DispositivoService:
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        self.session = session
        self.tenant_id = tenant_id

    async def criar(self, data: DeviceCreate) -> DispositivoCampo:
        expires_at = datetime.utcnow() + timedelta(days=data.expires_days)
        activation_code = _generate_activation_code()
        activation_expires = datetime.utcnow() + timedelta(minutes=_ACTIVATION_TTL_MINUTES)

        device = DispositivoCampo(
            tenant_id=self.tenant_id,
            user_id=data.user_id,
            nome=data.nome,
            fazenda_ids=data.fazenda_ids,
            modulos=data.modulos,
            status="PENDENTE",
            activation_code=activation_code,
            activation_code_expires_at=activation_expires,
            expires_at=expires_at,
        )
        self.session.add(device)
        await self.session.flush()
        return device

    async def ativar(self, req: DeviceActivateRequest) -> tuple[DispositivoCampo, str]:
        result = await self.session.execute(
            select(DispositivoCampo).where(
                and_(
                    DispositivoCampo.activation_code == req.activation_code,
                    DispositivoCampo.status == "PENDENTE",
                )
            )
        )
        device = result.scalar_one_or_none()
        if not device:
            raise EntityNotFoundError("Código de ativação inválido ou já utilizado.")

        if device.activation_code_expires_at < datetime.utcnow():
            raise BusinessRuleError("Código de ativação expirado. Solicite um novo código.")

        # Garante que o dispositivo pertence ao tenant correto
        if device.tenant_id != self.tenant_id:
            raise TenantViolationError("Código pertence a outro tenant.", tenant_id=self.tenant_id)

        # Marca fingerprint e ativa
        device.device_fingerprint = req.device_fingerprint
        device.status = "ATIVO"
        device.activation_code = None
        device.activation_code_expires_at = None
        await self.session.flush()

        # Busca nome do usuário para embed no token
        user_result = await self.session.execute(
            select(Usuario).where(Usuario.id == device.user_id)
        )
        user = user_result.scalar_one_or_none()
        user_name = user.nome if user else "Operador"

        token = _make_device_jwt(device, user_name)
        return device, token

    async def revogar(self, device_id: uuid.UUID, revoked_by: uuid.UUID) -> DispositivoCampo:
        result = await self.session.execute(
            select(DispositivoCampo).where(
                and_(
                    DispositivoCampo.id == device_id,
                    DispositivoCampo.tenant_id == self.tenant_id,
                )
            )
        )
        device = result.scalar_one_or_none()
        if not device:
            raise EntityNotFoundError(f"Dispositivo {device_id} não encontrado.")

        device.status = "REVOGADO"
        device.revoked_at = datetime.utcnow()
        device.revoked_by = revoked_by
        await self.session.flush()
        return device

    async def listar(self) -> list[DispositivoCampo]:
        result = await self.session.execute(
            select(DispositivoCampo).where(
                DispositivoCampo.tenant_id == self.tenant_id
            ).order_by(DispositivoCampo.created_at.desc())
        )
        return list(result.scalars().all())

    async def atualizar_last_seen(self, device_id: uuid.UUID) -> None:
        await self.session.execute(
            update(DispositivoCampo)
            .where(DispositivoCampo.id == device_id)
            .values(last_seen_at=datetime.utcnow())
        )

    async def atualizar_last_sync(self, device_id: uuid.UUID) -> None:
        await self.session.execute(
            update(DispositivoCampo)
            .where(DispositivoCampo.id == device_id)
            .values(last_sync_at=datetime.utcnow(), last_seen_at=datetime.utcnow())
        )


class SyncService:
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID, device: DispositivoCampo):
        self.session = session
        self.tenant_id = tenant_id
        self.device = device

    async def pull(self, last_sync_at: datetime | None) -> dict[str, Any]:
        from core.models.unidade_produtiva import UnidadeProdutiva
        from core.cadastros.propriedades.models import AreaRural
        from pecuaria.animal.models import LoteAnimal
        from core.cadastros.produtos.models import Produto

        fazenda_ids = self.device.fazenda_ids

        # Fazendas autorizadas para o dispositivo
        stmt_f = select(UnidadeProdutiva).where(
            and_(
                UnidadeProdutiva.tenant_id == self.tenant_id,
                UnidadeProdutiva.id.in_(fazenda_ids),
            )
        )
        fazendas_rows = (await self.session.execute(stmt_f)).scalars().all()

        # Talhões das fazendas autorizadas
        stmt_t = select(AreaRural).where(
            and_(
                AreaRural.tenant_id == self.tenant_id,
                AreaRural.unidade_produtiva_id.in_(fazenda_ids),
                AreaRural.tipo == "TALHAO",
            )
        )
        talhoes_rows = (await self.session.execute(stmt_t)).scalars().all()

        # Lotes das fazendas autorizadas
        stmt_l = select(LoteAnimal).where(
            and_(
                LoteAnimal.tenant_id == self.tenant_id,
                LoteAnimal.unidade_produtiva_id.in_(fazenda_ids),
            )
        )
        lotes_rows = (await self.session.execute(stmt_l)).scalars().all()

        # Insumos do tenant
        stmt_i = select(Produto).where(
            and_(
                Produto.tenant_id == self.tenant_id,
                Produto.ativo == True,
            )
        ).limit(500)
        insumos_rows = (await self.session.execute(stmt_i)).scalars().all()

        # Tarefas para este dispositivo:
        # 1. Manuais pendentes criadas pelo dispositivo
        # 2. Programadas para hoje/atrasadas nas fazendas autorizadas (status PENDENTE ou EM_EXECUCAO)
        hoje = date.today()
        stmt_task = select(TarefaCampo).where(
            and_(
                TarefaCampo.tenant_id == self.tenant_id,
                TarefaCampo.status_execucao.in_(["PENDENTE", "EM_EXECUCAO"]),
                or_(
                    # Tarefas manuais do dispositivo
                    and_(
                        TarefaCampo.origem == "MANUAL",
                        TarefaCampo.dispositivo_id == self.device.id,
                    ),
                    # Tarefas programadas para fazendas autorizadas (hoje e atrasadas)
                    and_(
                        TarefaCampo.origem == "PROGRAMADA",
                        TarefaCampo.unidade_produtiva_id.in_(fazenda_ids),
                        TarefaCampo.data_programada <= hoje,
                        or_(
                            TarefaCampo.dispositivo_id == None,
                            TarefaCampo.dispositivo_id == self.device.id,
                        ),
                    ),
                ),
            )
        )
        tarefas_rows = (await self.session.execute(stmt_task)).scalars().all()

        # Tombstones desde o último sync
        tombstones: dict[str, list[str]] = {"talhoes": [], "lotes": [], "tarefas": [], "insumos": []}
        if last_sync_at:
            stmt_tomb = select(SyncTombstone).where(
                and_(
                    SyncTombstone.tenant_id == self.tenant_id,
                    SyncTombstone.deleted_at > last_sync_at,
                )
            )
            for t in (await self.session.execute(stmt_tomb)).scalars().all():
                if t.entity_type in tombstones:
                    tombstones[t.entity_type].append(t.entity_id)

        return {
            "sync_at": datetime.utcnow(),
            "fazendas": [
                {"id": f.id, "nome": f.nome, "municipio": f.municipio, "uf": f.uf}
                for f in fazendas_rows
            ],
            "talhoes": [
                {
                    "id": t.id,
                    "nome": t.nome,
                    "unidade_produtiva_id": t.unidade_produtiva_id,
                    "area_ha": float(t.area_manual_ha) if t.area_manual_ha else None,
                    "tipo": t.tipo,
                }
                for t in talhoes_rows
            ],
            "lotes": [
                {
                    "id": l.id,
                    "identificacao": l.identificacao,
                    "especie": l.especie,
                    "quantidade_cabecas": l.quantidade_cabecas,
                    "unidade_produtiva_id": l.unidade_produtiva_id,
                }
                for l in lotes_rows
            ],
            "insumos": [
                {
                    "id": i.id,
                    "nome": i.nome,
                    "tipo": i.tipo if hasattr(i, "tipo") else "",
                    "unidade_medida": i.unidade_medida if hasattr(i, "unidade_medida") else None,
                }
                for i in insumos_rows
            ],
            "tarefas_pendentes": [
                {
                    "id": t.id,
                    "client_id": t.client_id,
                    "type": t.type,
                    "module": t.module,
                    "status": t.status,
                    "origem": t.origem,
                    "status_execucao": t.status_execucao,
                    "titulo": t.titulo,
                    "data_programada": t.data_programada,
                    "prioridade": t.prioridade,
                    "operador_id": t.operador_id,
                    "dados": t.dados,
                    "unidade_produtiva_id": t.unidade_produtiva_id,
                    "area_rural_id": t.area_rural_id,
                    "lote_id": t.lote_id,
                    "client_created_at": t.client_created_at,
                    "client_updated_at": t.client_updated_at,
                }
                for t in tarefas_rows
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
                logger.warning(f"[sync/push] Erro ao processar item {item.local_id}: {exc}")
                results.append(SyncPushItemResult(
                    local_id=item.local_id,
                    status="ERROR",
                    error_message=str(exc),
                ))

        return results

    async def _process_item(self, item: SyncPushItem) -> SyncPushItemResult:
        if item.entity_type == "task":
            return await self._process_task(item)

        return SyncPushItemResult(
            local_id=item.local_id,
            status="ERROR",
            error_message=f"Tipo de entidade não suportado: {item.entity_type}",
        )

    async def _process_task(self, item: SyncPushItem) -> SyncPushItemResult:
        payload = item.payload

        if item.operation == "CREATE":
            # Verificar duplicata por client_id
            existing = await self.session.execute(
                select(TarefaCampo).where(
                    and_(
                        TarefaCampo.tenant_id == self.tenant_id,
                        TarefaCampo.client_id == item.local_id,
                    )
                )
            )
            if existing.scalar_one_or_none():
                return SyncPushItemResult(
                    local_id=item.local_id,
                    status="CREATED",
                    server_id=item.local_id,
                )

            task = TarefaCampo(
                tenant_id=self.tenant_id,
                dispositivo_id=self.device.id,
                user_id=self.device.user_id,
                client_id=item.local_id,
                origem="MANUAL",
                status_execucao="CONCLUIDA",
                type=payload.get("type", ""),
                module=payload.get("module", "agricola"),
                status=payload.get("status", "PENDENTE"),
                dados=payload.get("dados", {}),
                fotos=payload.get("fotos", []),
                unidade_produtiva_id=_to_uuid(payload.get("fazenda_id")),
                area_rural_id=_to_uuid(payload.get("talhao_id")),
                lote_id=_to_uuid(payload.get("lote_id")),
                localizacao_status=payload.get("localizacao_status", "INDISPONIVEL"),
                latitude=payload.get("latitude"),
                longitude=payload.get("longitude"),
                client_created_at=_parse_dt(item.client_created_at),
                client_updated_at=_parse_dt(item.client_updated_at),
            )
            self.session.add(task)
            await self.session.flush()
            return SyncPushItemResult(local_id=item.local_id, status="CREATED", server_id=str(task.id))

        if item.operation == "UPDATE":
            if not item.server_id:
                return SyncPushItemResult(local_id=item.local_id, status="ERROR", error_message="server_id obrigatório para UPDATE")

            result = await self.session.execute(
                select(TarefaCampo).where(
                    and_(
                        TarefaCampo.id == uuid.UUID(item.server_id),
                        TarefaCampo.tenant_id == self.tenant_id,
                    )
                )
            )
            task = result.scalar_one_or_none()
            if not task:
                return SyncPushItemResult(local_id=item.local_id, status="ERROR", error_message="Tarefa não encontrada")

            # last-write-wins para tipo APLICACAO, server-wins para demais
            if task.type.startswith("APLICACAO") or item.client_updated_at >= task.updated_at:
                task.status = payload.get("status", task.status)
                task.dados = payload.get("dados", task.dados)
                task.client_updated_at = _parse_dt(item.client_updated_at)

                # Atualizar execução de tarefas programadas
                novo_status_exec = payload.get("status_execucao")
                if novo_status_exec:
                    _aplicar_status_execucao(task, novo_status_exec, payload)

                await self.session.flush()
                return SyncPushItemResult(local_id=item.local_id, status="UPDATED", server_id=str(task.id))
            else:
                # Conflito: servidor tem versão mais recente
                from campo.schemas import TarefaPendenteSync
                return SyncPushItemResult(
                    local_id=item.local_id,
                    status="CONFLICT",
                    server_id=str(task.id),
                    server_data={
                        "status": task.status,
                        "dados": task.dados,
                        "updated_at": task.updated_at.isoformat(),
                    },
                )

        if item.operation == "DELETE":
            if item.server_id:
                await self.session.execute(
                    select(TarefaCampo).where(
                        and_(
                            TarefaCampo.id == uuid.UUID(item.server_id),
                            TarefaCampo.tenant_id == self.tenant_id,
                        )
                    )
                )
                # Soft delete via status
                await self.session.execute(
                    update(TarefaCampo)
                    .where(
                        and_(
                            TarefaCampo.id == uuid.UUID(item.server_id),
                            TarefaCampo.tenant_id == self.tenant_id,
                        )
                    )
                    .values(status="CANCELADA")
                )
                await self.session.flush()

            return SyncPushItemResult(local_id=item.local_id, status="DELETED")

        return SyncPushItemResult(local_id=item.local_id, status="ERROR", error_message="Operação desconhecida")


def _aplicar_status_execucao(task: TarefaCampo, novo: str, payload: dict) -> None:
    """Aplica transição de status_execucao com regras de negócio."""
    if novo == "EM_EXECUCAO":
        task.status_execucao = "EM_EXECUCAO"
        if not task.iniciada_em:
            task.iniciada_em = datetime.utcnow()
    elif novo == "CONCLUIDA":
        if task.status_execucao != "EM_EXECUCAO":
            raise BusinessRuleError("Só é possível CONCLUIR uma tarefa que está EM_EXECUCAO")
        task.status_execucao = "CONCLUIDA"
        task.concluida_em = datetime.utcnow()
        if payload.get("obs"):
            task.dados = {**task.dados, "obs_execucao": payload["obs"]}
        if payload.get("fotos"):
            task.fotos = list(task.fotos) + payload["fotos"]
        if payload.get("localizacao_status"):
            task.localizacao_status = payload["localizacao_status"]
        if payload.get("latitude"):
            task.latitude = payload["latitude"]
        if payload.get("longitude"):
            task.longitude = payload["longitude"]
    elif novo == "CANCELADA":
        task.status_execucao = "CANCELADA"


class TarefaProgramadaService:
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID):
        self.session = session
        self.tenant_id = tenant_id
        self.user_id = user_id

    async def criar(self, data: TarefaProgramadaCreate) -> TarefaCampo:
        task = TarefaCampo(
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            origem="PROGRAMADA",
            status_execucao="PENDENTE",
            titulo=data.titulo,
            type=data.type,
            module=data.module,
            data_programada=data.data_programada,
            prioridade=data.prioridade,
            unidade_produtiva_id=data.unidade_produtiva_id,
            area_rural_id=data.area_rural_id,
            lote_id=data.lote_id,
            operador_id=data.operador_id,
            dispositivo_id=data.dispositivo_id,
            dados=data.dados,
            status="PENDENTE",
            fotos=[],
            localizacao_status="INDISPONIVEL",
            client_created_at=None,
            client_updated_at=None,
        )
        self.session.add(task)
        await self.session.flush()
        return task

    async def listar(
        self,
        fazenda_id: uuid.UUID | None = None,
        data_inicio: date | None = None,
        data_fim: date | None = None,
        status_execucao: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[TarefaCampo]:
        filters = [
            TarefaCampo.tenant_id == self.tenant_id,
            TarefaCampo.origem == "PROGRAMADA",
        ]
        if fazenda_id:
            filters.append(TarefaCampo.unidade_produtiva_id == fazenda_id)
        if data_inicio:
            filters.append(TarefaCampo.data_programada >= data_inicio)
        if data_fim:
            filters.append(TarefaCampo.data_programada <= data_fim)
        if status_execucao:
            filters.append(TarefaCampo.status_execucao == status_execucao)

        result = await self.session.execute(
            select(TarefaCampo)
            .where(and_(*filters))
            .order_by(TarefaCampo.data_programada, TarefaCampo.prioridade)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_or_fail(self, tarefa_id: uuid.UUID) -> TarefaCampo:
        result = await self.session.execute(
            select(TarefaCampo).where(
                and_(
                    TarefaCampo.id == tarefa_id,
                    TarefaCampo.tenant_id == self.tenant_id,
                )
            )
        )
        task = result.scalar_one_or_none()
        if not task:
            raise EntityNotFoundError(f"Tarefa {tarefa_id} não encontrada")
        return task

    async def atualizar_execucao(self, tarefa_id: uuid.UUID, data: ExecucaoUpdate) -> TarefaCampo:
        task = await self.get_or_fail(tarefa_id)
        _aplicar_status_execucao(task, data.status_execucao, {
            "obs": data.obs,
            "fotos": data.fotos,
            "localizacao_status": data.localizacao_status,
            "latitude": data.latitude,
            "longitude": data.longitude,
        })
        await self.session.flush()
        return task

    async def cancelar(self, tarefa_id: uuid.UUID) -> TarefaCampo:
        task = await self.get_or_fail(tarefa_id)
        task.status_execucao = "CANCELADA"
        await self.session.flush()
        return task


def _to_uuid(val: Any) -> uuid.UUID | None:
    if not val:
        return None
    try:
        return uuid.UUID(str(val))
    except (ValueError, AttributeError):
        return None


def _parse_dt(val: Any) -> datetime:
    if isinstance(val, datetime):
        return val.replace(tzinfo=None)
    try:
        return datetime.fromisoformat(str(val)).replace(tzinfo=None)
    except Exception:
        return datetime.utcnow()
