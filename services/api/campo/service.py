# ruff: noqa
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
from core.services.audit_service import _serialize, write_audit_log

from campo.models import DispositivoCampo, TarefaCampo, SyncTombstone
from campo.schemas import (
    DeviceCreate,
    DeviceActivateRequest,
    DeviceReactivateRequest,
    SyncPushItem,
    SyncPushItemResult,
    TarefaProgramadaCreate,
    TarefaProgramadaUpdate,
    ExecucaoUpdate,
)
from recommendations.enums import ACTIVE_RECOMMENDATION_STATUSES
from recommendations.models import RecommendationResult

_ACTIVATION_CODE_CHARS = string.ascii_uppercase + string.digits
_ACTIVATION_TTL_MINUTES = 30
_RECOMMENDATION_PRIORITY_RANK = {
    "URGENT": 4,
    "HIGH": 3,
    "NORMAL": 2,
    "LOW": 1,
}


def _generate_activation_code(length: int = 8) -> str:
    return "".join(secrets.choice(_ACTIVATION_CODE_CHARS) for _ in range(length))


def _priority_rank(priority: str) -> int:
    return _RECOMMENDATION_PRIORITY_RANK.get(priority, 0)


def _as_utc_naive(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def _as_utc_aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _montar_dados_contexto_safra(
    safra_id: uuid.UUID,
    ano_safra: str,
    cultura: str | None,
) -> dict[str, str]:
    """Monta o contexto agrícola mínimo consumido pelo PWA offline."""
    dados = {"safra_id": str(safra_id), "safra_nome": ano_safra}
    if cultura:
        dados["cultura"] = cultura
    return dados


def _enriquecer_dados_com_contexto_safra(
    dados: dict[str, Any] | None,
    contexto: dict[str, str] | None,
) -> dict[str, Any]:
    """Preserva os dados da tarefa e aplica o contexto agrícola canônico."""
    resultado = dict(dados or {})
    if contexto:
        resultado.update(contexto)
    return resultado


def _enriquecer_dados_com_nome_operador(
    dados: dict[str, Any], nome_operador: str | None
) -> dict[str, Any]:
    """Inclui o nome do operador para exibição offline quando disponível."""
    resultado = dict(dados)
    if nome_operador:
        resultado["operador_nome"] = nome_operador
    return resultado


async def _buscar_contexto_safra_tarefa(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    safra_tarefa_id: uuid.UUID,
) -> dict[str, str]:
    """Busca o contexto de safra de uma tarefa agrícola respeitando o tenant."""
    from agricola.safras.models import Safra
    from agricola.tarefas.models import SafraTarefa

    stmt = (
        select(SafraTarefa.safra_id, Safra.ano_safra, Safra.cultura)
        .join(Safra, Safra.id == SafraTarefa.safra_id)
        .where(
            SafraTarefa.id == safra_tarefa_id,
            SafraTarefa.tenant_id == tenant_id,
            Safra.tenant_id == tenant_id,
        )
    )
    contexto = (await session.execute(stmt)).one_or_none()
    if contexto is None:
        return {}
    return _montar_dados_contexto_safra(*contexto)


def _make_device_jwt(device: DispositivoCampo, user_name: str, user_avatar_url: str | None) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "type": "device",
        "device_id": str(device.id),
        "tenant_id": str(device.tenant_id),
        "sub": str(device.user_id),
        "user_name": user_name,
        "user_avatar_url": user_avatar_url,
        "fazenda_ids": [str(fid) for fid in device.fazenda_ids],
        "modulos": device.modulos,
        "iat": int(now.timestamp()),
        "exp": int(_to_naive_utc(device.expires_at).replace(tzinfo=timezone.utc).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


_TIPOS_TAREFA_AGRICOLA_MATERIALIZAVEIS = {
    "APLICACAO_DEFENSIVO",
    "APLICACAO_FERTILIZANTE",
    "COLHEITA_REGISTRO",
}


class DispositivoService:
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        self.session = session
        self.tenant_id = tenant_id

    async def criar(self, data: DeviceCreate) -> DispositivoCampo:
        if not data.fazenda_ids:
            raise BusinessRuleError("Selecione ao menos uma fazenda autorizada para o dispositivo.")

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

        if _to_naive_utc(device.activation_code_expires_at) < datetime.utcnow():
            raise BusinessRuleError("Código de ativação expirado. Solicite um novo código.")

        # Garante que o dispositivo pertence ao tenant correto
        if device.tenant_id != self.tenant_id:
            raise TenantViolationError("Código pertence a outro tenant.", tenant_id=self.tenant_id)
        if not device.fazenda_ids:
            raise BusinessRuleError(
                "Dispositivo sem fazendas autorizadas. Revise o cadastro e gere um novo código."
            )

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
        user_name = (user.apelido or user.nome_completo or user.username) if user else "Operador"
        user_avatar_url = user.foto_perfil_url if user else None

        token = _make_device_jwt(device, user_name, user_avatar_url)
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

    async def reativar(self, data: DeviceReactivateRequest) -> tuple[DispositivoCampo, str]:
        result = await self.session.execute(
            select(DispositivoCampo).where(
                and_(
                    DispositivoCampo.id == data.device_id,
                    DispositivoCampo.tenant_id == self.tenant_id,
                )
            )
        )
        device = result.scalar_one_or_none()
        if not device:
            raise EntityNotFoundError(f"Dispositivo {data.device_id} não encontrado.")

        if not device.fazenda_ids:
            raise BusinessRuleError(
                "Dispositivo sem fazendas autorizadas. Refaça o cadastro antes de reativar."
            )

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

    async def listar(self) -> list[DispositivoCampo]:
        result = await self.session.execute(
            select(DispositivoCampo)
            .where(DispositivoCampo.tenant_id == self.tenant_id)
            .order_by(DispositivoCampo.created_at.desc())
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


class CampoAgricolaSyncService:
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        self.session = session
        self.tenant_id = tenant_id

    async def processar_tarefa_campo(self, tarefa_id: uuid.UUID) -> dict[str, Any]:
        task = await self.session.get(TarefaCampo, tarefa_id)
        if not task or task.tenant_id != self.tenant_id:
            raise EntityNotFoundError("Tarefa de campo", tarefa_id)
        if task.module != "agricola":
            raise BusinessRuleError(
                "Somente tarefas agrícolas podem ser materializadas neste fluxo."
            )
        if task.status_execucao != "CONCLUIDA":
            raise BusinessRuleError(
                "A tarefa precisa estar concluída para gerar efeitos agrícolas."
            )

        if task.operacao_agricola_id:
            return await self._concluir_operacao_vinculada(task)
        if task.type in {"APLICACAO_DEFENSIVO", "APLICACAO_FERTILIZANTE"}:
            return await self._materializar_aplicacao(task)
        if task.type == "COLHEITA_REGISTRO":
            return await self._materializar_colheita(task)
        raise BusinessRuleError(f"Tipo de tarefa agrícola não suportado: {task.type}")

    async def _concluir_operacao_vinculada(self, task: TarefaCampo) -> dict[str, Any]:
        """Tarefa nasceu de uma OS já existente (agricola/tarefas): marca REALIZADA e
        reprocessa os insumos que o operador informou em `task.dados` durante a
        execução (mesma convenção usada por `_materializar_aplicacao`), para que
        baixa de estoque e custo/despesa aconteçam mesmo neste caminho."""
        from agricola.operacoes.models import OperacaoAgricola
        from agricola.operacoes.schemas import OperacaoAgricolaUpdate, InsumoOperacaoCreate
        from agricola.operacoes.service import OperacaoService

        operacao = await self.session.get(OperacaoAgricola, task.operacao_agricola_id)
        if not operacao or operacao.tenant_id != self.tenant_id:
            raise BusinessRuleError("Operação agrícola vinculada não localizada para esta tarefa.")

        if operacao.status != "REALIZADA":
            dados = dict(task.dados or {})
            area_aplicada_ha = float(operacao.area_aplicada_ha or 0.0)

            def _montar_insumo(item: dict) -> InsumoOperacaoCreate | None:
                produto_id = _to_uuid(item.get("produto_id") or item.get("insumo_id"))
                quantidade = float(item.get("quantidade") or item.get("dose_por_ha") or 0.0)
                if produto_id is None or quantidade <= 0:
                    return None
                return InsumoOperacaoCreate(
                    produto_id=produto_id,
                    dose_por_ha=quantidade,
                    unidade=str(item.get("unidade") or "UN"),
                    area_aplicada=area_aplicada_ha,
                )

            insumos_informados = dados.get("insumos")
            insumos_payload: list[InsumoOperacaoCreate] = []
            if isinstance(insumos_informados, list) and insumos_informados:
                for item in insumos_informados:
                    insumo = _montar_insumo(item)
                    if insumo:
                        insumos_payload.append(insumo)
            elif dados.get("insumo_id"):
                insumo = _montar_insumo(dados)
                if insumo:
                    insumos_payload.append(insumo)

            update_kwargs: dict[str, Any] = {
                "status": "REALIZADA",
                "data_realizada": self._data_referencia(task).date(),
            }
            custo_informado = dados.get("custo_total") or dados.get("custo_mao_obra")
            if custo_informado:
                update_kwargs["custo_total"] = float(custo_informado)
            if insumos_payload:
                update_kwargs["insumos"] = insumos_payload

            await OperacaoService(self.session, self.tenant_id).atualizar(
                operacao.id,
                OperacaoAgricolaUpdate.model_construct(**update_kwargs),
            )
        return await self._marcar_sync_agricola(
            task.id,
            {
                "status": "SYNCED",
                "tipo_materializacao": "OPERACAO_AGRICOLA_VINCULADA",
                "operacao_id": str(operacao.id),
                "data_processamento": datetime.utcnow().isoformat(),
            },
        )

    async def _materializar_aplicacao(self, task: TarefaCampo) -> dict[str, Any]:
        from agricola.operacoes.models import OperacaoAgricola
        from agricola.operacoes.schemas import InsumoOperacaoCreate, OperacaoAgricolaCreate
        from agricola.operacoes.service import OperacaoService
        from core.cadastros.propriedades.models import AreaRural

        stmt = (
            select(OperacaoAgricola)
            .where(
                OperacaoAgricola.tenant_id == self.tenant_id,
                OperacaoAgricola.tarefa_id == task.id,
            )
            .limit(1)
        )
        operacao_existente = (await self.session.execute(stmt)).scalars().first()
        if operacao_existente is not None:
            return await self._marcar_sync_agricola(
                task.id,
                {
                    "status": "SYNCED",
                    "tipo_materializacao": "OPERACAO_AGRICOLA",
                    "operacao_id": str(operacao_existente.id),
                    "data_processamento": datetime.utcnow().isoformat(),
                },
            )

        dados = dict(task.dados or {})
        safra_id = await self._resolver_safra_id(task, dados)
        produto_id = _to_uuid(dados.get("insumo_id"))
        quantidade = float(dados.get("quantidade") or 0.0)
        unidade = str(dados.get("unidade") or "UN")
        if produto_id is None:
            raise BusinessRuleError(
                "Aplicação sem insumo vinculado não pode gerar operação agrícola."
            )
        if quantidade <= 0:
            raise BusinessRuleError(
                "Aplicação sem quantidade válida não pode gerar operação agrícola."
            )
        if task.area_rural_id is None:
            raise BusinessRuleError("Aplicação sem talhão não pode gerar operação agrícola.")

        talhao = await self.session.get(AreaRural, task.area_rural_id)
        if not talhao or talhao.tenant_id != self.tenant_id:
            raise BusinessRuleError(
                "Talhão da tarefa não localizado para materializar a aplicação."
            )
        area_aplicada_ha = float(talhao.area_hectares or talhao.area_hectares_manual or 0.0)
        if area_aplicada_ha <= 0:
            raise BusinessRuleError("Talhão sem área cadastrada não pode gerar aplicação agrícola.")

        observacoes = _first_non_empty(
            dados.get("obs_execucao"),
            dados.get("obs"),
        )
        tipo_operacao = "PULVERIZAÇÃO" if task.type == "APLICACAO_DEFENSIVO" else "ADUBAÇÃO"
        operacao = await OperacaoService(self.session, self.tenant_id).criar(
            OperacaoAgricolaCreate(
                safra_id=safra_id,
                talhao_id=task.area_rural_id,
                tarefa_id=task.id,
                tipo=tipo_operacao,
                subtipo=task.type,
                descricao=f"{tipo_operacao} via Campo PWA",
                data_realizada=self._data_referencia(task).date(),
                area_aplicada_ha=area_aplicada_ha,
                operador_id=task.operador_id or task.user_id,
                latitude=float(task.latitude) if task.latitude is not None else None,
                longitude=float(task.longitude) if task.longitude is not None else None,
                custo_total=float(dados.get("custo_total") or dados.get("custo_mao_obra") or 0.0),
                status="REALIZADA",
                observacoes=observacoes,
                insumos=[
                    InsumoOperacaoCreate(
                        produto_id=produto_id,
                        dose_por_ha=quantidade,
                        unidade=unidade,
                        area_aplicada=area_aplicada_ha,
                    )
                ],
            )
        )
        return await self._marcar_sync_agricola(
            task.id,
            {
                "status": "SYNCED",
                "tipo_materializacao": "OPERACAO_AGRICOLA",
                "operacao_id": str(operacao.id),
                "safra_id": str(safra_id),
                "efeitos": [
                    "operacao_agricola",
                    "movimentacao_estoque",
                    "despesa_financeira",
                    "evento_caderno",
                ],
                "data_processamento": datetime.utcnow().isoformat(),
            },
        )

    async def _materializar_colheita(self, task: TarefaCampo) -> dict[str, Any]:
        from agricola.romaneios.models import RomaneioColheita
        from agricola.romaneios.schemas import RomaneioColheitaCreate
        from agricola.romaneios.service import RomaneioService

        dados = dict(task.dados or {})
        safra_id = await self._resolver_safra_id(task, dados)
        numero_romaneio = f"CAMPO-{str(task.id).split('-')[0].upper()}"
        stmt = (
            select(RomaneioColheita)
            .where(
                RomaneioColheita.tenant_id == self.tenant_id,
                RomaneioColheita.numero_romaneio == numero_romaneio,
                RomaneioColheita.talhao_id == task.area_rural_id,
            )
            .limit(1)
        )
        romaneio_existente = (await self.session.execute(stmt)).scalars().first()
        if romaneio_existente is not None:
            return await self._marcar_sync_agricola(
                task.id,
                {
                    "status": "SYNCED",
                    "tipo_materializacao": "ROMANEIO_COLHEITA",
                    "romaneio_id": str(romaneio_existente.id),
                    "data_processamento": datetime.utcnow().isoformat(),
                },
            )

        if task.area_rural_id is None:
            raise BusinessRuleError("Colheita sem talhão não pode gerar romaneio.")

        quantidade = float(dados.get("quantidade") or 0.0)
        unidade = str(dados.get("unidade") or "sc").lower()
        if quantidade <= 0:
            raise BusinessRuleError("Colheita sem quantidade válida não pode gerar romaneio.")

        peso_bruto_kg = self._converter_colheita_para_kg(quantidade, unidade)
        romaneio = await RomaneioService(self.session, self.tenant_id).criar(
            RomaneioColheitaCreate(
                safra_id=safra_id,
                talhao_id=task.area_rural_id,
                production_unit_id=await self._resolver_production_unit_id(
                    safra_id, task.area_rural_id
                ),
                numero_romaneio=numero_romaneio,
                data_colheita=self._data_referencia(task).date(),
                operador_id=task.operador_id or task.user_id,
                peso_bruto_kg=peso_bruto_kg,
                tara_kg=0,
                umidade_pct=float(dados.get("umidade_perc"))
                if dados.get("umidade_perc") not in (None, "")
                else None,
                destino=str(dados.get("destino") or "ARMAZEM"),
                preco_saca=float(dados.get("preco_saca"))
                if dados.get("preco_saca") not in (None, "")
                else None,
                observacoes=self._montar_observacao_colheita(task, quantidade, unidade),
            )
        )
        efeitos = ["romaneio_colheita", "produto_colhido", "produtividade_safra"]
        if romaneio.receita_total and float(romaneio.receita_total) > 0:
            efeitos.append("receita_financeira")
        return await self._marcar_sync_agricola(
            task.id,
            {
                "status": "SYNCED",
                "tipo_materializacao": "ROMANEIO_COLHEITA",
                "romaneio_id": str(romaneio.id),
                "safra_id": str(safra_id),
                "sacas_60kg": float(romaneio.sacas_60kg or 0.0),
                "receita_total": float(romaneio.receita_total or 0.0),
                "efeitos": efeitos,
                "data_processamento": datetime.utcnow().isoformat(),
            },
        )

    async def _resolver_safra_id(self, task: TarefaCampo, dados: dict[str, Any]) -> uuid.UUID:
        from agricola.safras.models import Safra, SafraTalhao

        safra_id = _to_uuid(dados.get("safra_id"))
        if safra_id is not None:
            safra = await self.session.get(Safra, safra_id)
            if safra and safra.tenant_id == self.tenant_id:
                return safra_id

        if task.area_rural_id is None:
            raise BusinessRuleError(
                "A tarefa não informa safra nem talhão para resolver o contexto agrícola."
            )

        stmt = (
            select(Safra.id)
            .join(SafraTalhao, SafraTalhao.safra_id == Safra.id)
            .where(
                Safra.tenant_id == self.tenant_id,
                SafraTalhao.tenant_id == self.tenant_id,
                SafraTalhao.area_id == task.area_rural_id,
                Safra.status.notin_(["ENCERRADA", "CANCELADA"]),
            )
            .order_by((Safra.status == "ATIVA").desc(), Safra.created_at.desc())
            .limit(1)
        )
        safra_id = (await self.session.execute(stmt)).scalar_one_or_none()
        if safra_id is None:
            raise BusinessRuleError(
                "Nenhuma safra ativa/enquadrada foi encontrada para o talhão da tarefa."
            )
        return safra_id

    async def _resolver_production_unit_id(
        self,
        safra_id: uuid.UUID,
        talhao_id: uuid.UUID,
    ) -> uuid.UUID | None:
        from agricola.production_units.models import ProductionUnit

        stmt = (
            select(ProductionUnit.id)
            .where(
                ProductionUnit.tenant_id == self.tenant_id,
                ProductionUnit.safra_id == safra_id,
                ProductionUnit.area_id == talhao_id,
            )
            .order_by((ProductionUnit.status == "ATIVA").desc(), ProductionUnit.created_at.desc())
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def _marcar_sync_agricola(
        self, tarefa_id: uuid.UUID, sync_meta: dict[str, Any]
    ) -> dict[str, Any]:
        task = await self.session.get(TarefaCampo, tarefa_id)
        if not task or task.tenant_id != self.tenant_id:
            raise EntityNotFoundError("Tarefa de campo", tarefa_id)
        dados = dict(task.dados or {})
        dados["sync_agricola"] = sync_meta
        task.dados = dados
        await self.session.commit()
        return sync_meta

    def _data_referencia(self, task: TarefaCampo) -> datetime:
        return (
            task.concluida_em
            or task.client_updated_at
            or task.client_created_at
            or task.updated_at
            or task.created_at
            or datetime.utcnow()
        )

    def _converter_colheita_para_kg(self, quantidade: float, unidade: str) -> float:
        if unidade == "kg":
            return quantidade
        if unidade == "t":
            return quantidade * 1000.0
        if unidade in {"sc", "saca", "sacas", "cx"}:
            return quantidade * 60.0
        raise BusinessRuleError(f"Unidade de colheita não suportada para romaneio: {unidade}")

    def _montar_observacao_colheita(
        self, task: TarefaCampo, quantidade: float, unidade: str
    ) -> str | None:
        dados = dict(task.dados or {})
        linhas = [f"Origem Campo PWA: {quantidade} {unidade}"]
        obs = _first_non_empty(dados.get("obs_execucao"), dados.get("obs"))
        if obs:
            linhas.append(obs)
        return "\n".join(linhas)


class SyncService:
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID, device: DispositivoCampo):
        self.session = session
        self.tenant_id = tenant_id
        self.device = device
        self.tarefas_pecuaria_sync: list[uuid.UUID] = []
        self.tarefas_agricola_sync: list[uuid.UUID] = []

    async def pull(self, last_sync_at: datetime | None) -> dict[str, Any]:
        from core.models.unidade_produtiva import UnidadeProdutiva
        from core.cadastros.propriedades.models import AreaRural
        from pecuaria.animal.models import Animal, LoteAnimal
        from core.cadastros.produtos.models import Produto
        from agricola.caderno.service import CadernoCampoService

        # Safra depende de Cultivo para configurar o mapper corretamente.
        # Importar o módulo aqui evita InvalidRequestError quando o pull é
        # executado antes de outros fluxos agrícolas que já carregariam o model.
        from agricola.cultivos.models import Cultivo  # noqa: F401
        from agricola.safras.models import Safra

        last_sync_at_naive = _as_utc_naive(last_sync_at)
        last_sync_at_aware = _as_utc_aware(last_sync_at)
        fazenda_ids = [uuid.UUID(str(fazenda_id)) for fazenda_id in self.device.fazenda_ids]

        # Safras ativas associadas ao tenant (base para o seletor de caderno no PWA)
        stmt_s = (
            select(Safra)
            .where(
                and_(
                    Safra.tenant_id == self.tenant_id,
                    Safra.status.notin_(["ENCERRADA", "CANCELADA"]),
                )
            )
            .order_by(Safra.created_at.desc())
        )
        safras_rows = (await self.session.execute(stmt_s)).scalars().all()

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

        stmt_a = select(Animal).where(
            and_(
                Animal.tenant_id == self.tenant_id,
                Animal.unidade_produtiva_id.in_(fazenda_ids),
            )
        )
        animais_rows = (await self.session.execute(stmt_a)).scalars().all()

        # Insumos do tenant
        stmt_i = (
            select(Produto)
            .where(
                and_(
                    Produto.tenant_id == self.tenant_id,
                    Produto.ativo == True,
                )
            )
            .limit(500)
        )
        insumos_rows = (await self.session.execute(stmt_i)).scalars().all()

        from core.cadastros.pessoas.models import Pessoa, PessoaDocumento, PessoaRelacionamento, TipoRelacionamento

        # Colaboradores ativos do tenant
        from rh.models import ColaboradorRH

        stmt_c = (
            select(
                ColaboradorRH,
                Pessoa.nome_exibicao.label("nome_exibicao"),
                PessoaDocumento.numero.label("cpf"),
            )
            .join(Pessoa, Pessoa.id == ColaboradorRH.pessoa_id)
            .outerjoin(
                PessoaDocumento,
                and_(
                    PessoaDocumento.pessoa_id == ColaboradorRH.pessoa_id,
                    PessoaDocumento.tipo == "CPF",
                ),
            )
            .where(
                and_(
                    ColaboradorRH.tenant_id == self.tenant_id,
                    ColaboradorRH.ativo == True,
                    Pessoa.tenant_id == self.tenant_id,
                    Pessoa.ativo == True,
                )
            )
        )
        colaboradores_rows = (await self.session.execute(stmt_c)).all()

        # Pessoas operacionais (Fase 2B)
        hoje_date = date.today()
        stmt_p = (
            select(
                Pessoa.id.label("pessoa_id"),
                Pessoa.nome_exibicao,
                PessoaRelacionamento.unidade_produtiva_id,
                TipoRelacionamento.codigo.label("tipo_codigo"),
            )
            .select_from(Pessoa)
            .join(PessoaRelacionamento, PessoaRelacionamento.pessoa_id == Pessoa.id)
            .join(TipoRelacionamento, TipoRelacionamento.id == PessoaRelacionamento.tipo_id)
            .where(
                and_(
                    Pessoa.tenant_id == self.tenant_id,
                    Pessoa.ativo == True,
                    PessoaRelacionamento.unidade_produtiva_id.in_(fazenda_ids),
                    or_(
                        PessoaRelacionamento.ativo_desde == None,
                        PessoaRelacionamento.ativo_desde <= hoje_date,
                    ),
                    or_(
                        PessoaRelacionamento.ativo_ate == None,
                        PessoaRelacionamento.ativo_ate >= hoje_date,
                    ),
                    TipoRelacionamento.ativo == True,
                )
            )
        )
        pessoas_rows = (await self.session.execute(stmt_p)).all()

        pessoas_dict = {}
        for row in pessoas_rows:
            key = (row.pessoa_id, row.unidade_produtiva_id)
            if key not in pessoas_dict:
                pessoas_dict[key] = {
                    "pessoa_id": str(row.pessoa_id),
                    "nome_exibicao": row.nome_exibicao,
                    "unidade_produtiva_id": str(row.unidade_produtiva_id),
                    "papeis": [],
                }
            if row.tipo_codigo not in pessoas_dict[key]["papeis"]:
                pessoas_dict[key]["papeis"].append(row.tipo_codigo)

        pessoas_operacionais = sorted(
            [{**v, "papeis": sorted(v["papeis"])} for v in pessoas_dict.values()],
            key=lambda x: (x["unidade_produtiva_id"], x["nome_exibicao"]),
        )

        # Tarefas para este dispositivo:
        # 1. Manuais pendentes criadas pelo dispositivo
        # 2. Programadas para hoje/atrasadas nas fazendas autorizadas (status PENDENTE ou EM_EXECUCAO)
        # 3. Programadas explicitamente atribuídas ao dispositivo, mesmo que futuras
        hoje = date.today()
        status_sincronizavel = TarefaCampo.status_execucao.in_(["PENDENTE", "EM_EXECUCAO"])
        if last_sync_at_naive:
            status_sincronizavel = or_(
                status_sincronizavel,
                and_(
                    TarefaCampo.status_execucao.in_(["CONCLUIDA", "CANCELADA", "INVALIDADA"]),
                    TarefaCampo.updated_at >= last_sync_at_naive,
                ),
            )
        stmt_task = select(TarefaCampo).where(
            and_(
                TarefaCampo.tenant_id == self.tenant_id,
                or_(
                    # Tarefas manuais do dispositivo
                    and_(
                        TarefaCampo.origem == "MANUAL",
                        TarefaCampo.dispositivo_id == self.device.id,
                        status_sincronizavel,
                    ),
                    # Tarefas programadas para fazendas autorizadas (hoje e atrasadas)
                    and_(
                        TarefaCampo.origem == "PROGRAMADA",
                        TarefaCampo.unidade_produtiva_id.in_(fazenda_ids),
                        TarefaCampo.data_programada <= hoje,
                        status_sincronizavel,
                        or_(
                            TarefaCampo.dispositivo_id == None,
                            TarefaCampo.dispositivo_id == self.device.id,
                        ),
                    ),
                    # Tarefa atribuída diretamente ao dispositivo
                    and_(
                        TarefaCampo.origem == "PROGRAMADA",
                        TarefaCampo.unidade_produtiva_id.in_(fazenda_ids),
                        TarefaCampo.dispositivo_id == self.device.id,
                        status_sincronizavel,
                    ),
                ),
            )
        )
        tarefas_rows = (await self.session.execute(stmt_task)).scalars().all()
        contextos_safra = await self._buscar_contextos_safra_tarefas(tarefas_rows)
        nomes_operadores = await self._buscar_nomes_operadores(tarefas_rows)

        caderno_svc = CadernoCampoService(self.session, self.tenant_id)
        eventos_caderno_oficiais = await caderno_svc.listar_eventos_oficiais_para_sync(
            unidade_produtiva_ids=list(fazenda_ids),
            updated_after=last_sync_at_naive,
        )

        # Tombstones desde o último sync
        tombstones: dict[str, list[str]] = {
            "talhoes": [],
            "lotes": [],
            "tarefas": [],
            "insumos": [],
        }
        if last_sync_at_naive:
            stmt_tomb = select(SyncTombstone).where(
                and_(
                    SyncTombstone.tenant_id == self.tenant_id,
                    SyncTombstone.deleted_at > last_sync_at_naive,
                )
            )
            for t in (await self.session.execute(stmt_tomb)).scalars().all():
                if t.entity_type in tombstones:
                    tombstones[t.entity_type].append(t.entity_id)

        recomendacoes_operacionais = await self._listar_recomendacoes_operacionais(
            fazenda_ids=fazenda_ids,
            last_sync_at=last_sync_at_aware,
        )
        recomendacoes_climaticas = self._build_recomendacoes_climaticas(recomendacoes_operacionais)

        return {
            "sync_at": datetime.utcnow(),
            "safras": [
                {
                    "id": s.id,
                    "ano_safra": s.ano_safra,
                    "cultura": s.cultura,
                    "status": s.status,
                }
                for s in safras_rows
            ],
            "fazendas": [
                {"id": f.id, "nome": f.nome, "municipio": f.municipio, "uf": f.uf}
                for f in fazendas_rows
            ],
            "talhoes": [
                {
                    "id": t.id,
                    "nome": t.nome,
                    "unidade_produtiva_id": t.unidade_produtiva_id,
                    "area_ha": float(t.area_hectares_manual or t.area_hectares)
                    if (t.area_hectares_manual or t.area_hectares)
                    else None,
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
            "animais": [
                {
                    "id": str(a.id),
                    "unidade_produtiva_id": str(a.unidade_produtiva_id),
                    "lote_id": str(a.lote_id) if a.lote_id else None,
                    "numero_brinco": a.numero_brinco,
                    "numero_sisbov": a.numero_sisbov,
                    "nome": a.nome,
                    "sexo": a.sexo,
                    "categoria": a.categoria,
                    "status": a.status,
                    "especie": a.especie,
                    "dados_extras": a.dados_extras,
                    "updated_at": a.updated_at,
                }
                for a in animais_rows
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
            "colaboradores": [
                {
                    "id": str(c.id),
                    "nome": nome_exibicao or "Colaborador",
                    "cpf": cpf,
                    "cargo": c.cargo,
                }
                for c, nome_exibicao, cpf in colaboradores_rows
            ],
            "pessoas_operacionais": pessoas_operacionais,
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
                    "dados": _enriquecer_dados_com_nome_operador(
                        _enriquecer_dados_com_contexto_safra(
                            t.dados,
                            contextos_safra.get(t.safra_tarefa_id),
                        ),
                        nomes_operadores.get(t.operador_id),
                    ),
                    "unidade_produtiva_id": t.unidade_produtiva_id,
                    "area_rural_id": t.area_rural_id,
                    "lote_id": t.lote_id,
                    "dispositivo_id": t.dispositivo_id,
                    "client_created_at": t.client_created_at,
                    "client_updated_at": t.client_updated_at,
                }
                for t in tarefas_rows
            ],
            "eventos_caderno_oficiais": [
                evento.model_dump(mode="json") for evento in eventos_caderno_oficiais
            ],
            "recomendacoes_operacionais": [
                self._serialize_recommendation(row) for row in recomendacoes_operacionais
            ],
            "recomendacoes_climaticas": recomendacoes_climaticas,
            "tombstones": tombstones,
        }

    async def _buscar_contextos_safra_tarefas(
        self, tarefas: list[TarefaCampo]
    ) -> dict[uuid.UUID, dict[str, str]]:
        """Retorna o contexto agrícola das tarefas espelhadas no lote do pull."""
        tarefa_ids = [t.safra_tarefa_id for t in tarefas if t.safra_tarefa_id]
        if not tarefa_ids:
            return {}

        from agricola.safras.models import Safra
        from agricola.tarefas.models import SafraTarefa

        stmt = (
            select(SafraTarefa.id, SafraTarefa.safra_id, Safra.ano_safra, Safra.cultura)
            .join(Safra, Safra.id == SafraTarefa.safra_id)
            .where(
                SafraTarefa.id.in_(tarefa_ids),
                SafraTarefa.tenant_id == self.tenant_id,
                Safra.tenant_id == self.tenant_id,
            )
        )
        rows = (await self.session.execute(stmt)).all()
        return {
            tarefa_id: _montar_dados_contexto_safra(safra_id, ano_safra, cultura)
            for tarefa_id, safra_id, ano_safra, cultura in rows
        }

    async def _buscar_nomes_operadores(
        self, tarefas: list[TarefaCampo]
    ) -> dict[uuid.UUID, str]:
        """Retorna os nomes dos operadores atribuídos às tarefas sincronizadas."""
        operador_ids = list({t.operador_id for t in tarefas if t.operador_id})
        if not operador_ids:
            return {}

        from core.cadastros.pessoas.models import Pessoa

        stmt = select(Pessoa.id, Pessoa.nome_exibicao).where(
            Pessoa.id.in_(operador_ids),
            Pessoa.tenant_id == self.tenant_id,
            Pessoa.ativo == True,
        )
        rows = (await self.session.execute(stmt)).all()
        return {pessoa_id: nome for pessoa_id, nome in rows}

    async def _listar_recomendacoes_operacionais(
        self,
        *,
        fazenda_ids: list[uuid.UUID],
        last_sync_at: datetime | None,
    ) -> list[RecommendationResult]:
        if not fazenda_ids:
            return []

        try:
            stmt = select(RecommendationResult).where(
                RecommendationResult.tenant_id == self.tenant_id,
                RecommendationResult.unidade_produtiva_id.in_(fazenda_ids),
                RecommendationResult.domain.in_(self._recommended_domains()),
                RecommendationResult.status.in_(ACTIVE_RECOMMENDATION_STATUSES),
            )
            if last_sync_at is not None:
                stmt = stmt.where(RecommendationResult.updated_at > last_sync_at)
            stmt = stmt.order_by(
                RecommendationResult.updated_at.desc(), RecommendationResult.created_at.desc()
            ).limit(30)
            rows = (await self.session.execute(stmt)).scalars().all()
            return sorted(rows, key=self._recommendation_sort_key, reverse=True)
        except Exception as exc:
            logger.warning(f"[sync/pull] Falha ao carregar recomendações persistidas: {exc}")
            return []

    @staticmethod
    def _recommended_domains() -> tuple[str, ...]:
        return ("FIELD", "AGRICULTURE", "LIVESTOCK", "OPERATIONS")

    @staticmethod
    def _recommendation_sort_key(row: RecommendationResult) -> tuple[int, datetime]:
        return (_priority_rank(getattr(row, "priority", "")), row.updated_at or row.created_at)

    def _serialize_recommendation(self, row: RecommendationResult) -> dict[str, Any]:
        return {
            "id": row.id,
            "tenant_id": row.tenant_id,
            "unidade_produtiva_id": row.unidade_produtiva_id,
            "domain": row.domain,
            "status": row.status,
            "priority": row.priority,
            "source_type": row.source_type,
            "action_type": row.action_type,
            "provider_name": row.provider_name,
            "rule_code": row.rule_code,
            "scope_type": row.scope_type,
            "scope_id": row.scope_id,
            "title": row.title,
            "summary": row.summary,
            "rationale": row.rationale,
            "dedupe_key": row.dedupe_key,
            "source_signal_ids": row.source_signal_ids or [],
            "confidence": float(row.confidence) if row.confidence is not None else None,
            "action_label": row.action_label,
            "action_target": row.action_target,
            "context": row.context,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
            "expires_at": row.expires_at,
            "viewed_at": row.viewed_at,
            "accepted_at": row.accepted_at,
            "dismissed_at": row.dismissed_at,
            "postponed_until": row.postponed_until,
            "executed_at": row.executed_at,
            "superseded_at": row.superseded_at,
            "superseded_by_id": row.superseded_by_id,
        }

    def _build_recomendacoes_climaticas(
        self, rows: list[RecommendationResult]
    ) -> list[dict[str, Any]]:
        if not rows:
            return []

        climate_rows = [row for row in rows if row.provider_name == "clima"]
        if not climate_rows:
            return []

        payload: list[dict[str, Any]] = []
        grouped_by_unit: dict[uuid.UUID, list[RecommendationResult]] = {}
        for row in climate_rows:
            if row.unidade_produtiva_id is None:
                continue
            grouped_by_unit.setdefault(row.unidade_produtiva_id, []).append(row)

        for unidade_produtiva_id, unit_rows in grouped_by_unit.items():
            specific_rows: dict[str, RecommendationResult] = {}
            for row in unit_rows:
                tipo_operacao = self._map_climate_tipo_operacao(row)
                current = specific_rows.get(tipo_operacao)
                if current is None or self._recommendation_sort_key(
                    row
                ) > self._recommendation_sort_key(current):
                    specific_rows[tipo_operacao] = row

            geral = self._best_climate_general(unit_rows)
            if geral is None:
                geral = max(unit_rows, key=self._recommendation_sort_key)

            for tipo_operacao in ("PULVERIZACAO", "COLHEITA", "ADUBACAO", "GERAL"):
                row = specific_rows.get(tipo_operacao) or geral
                payload.append(
                    self._serialize_climate_recommendation(unidade_produtiva_id, tipo_operacao, row)
                )
        return payload

    @staticmethod
    def _best_climate_general(rows: list[RecommendationResult]) -> RecommendationResult | None:
        general_rows = [
            row for row in rows if SyncService._map_climate_tipo_operacao(row) == "GERAL"
        ]
        if not general_rows:
            return None
        return sorted(general_rows, key=SyncService._recommendation_sort_key, reverse=True)[0]

    @staticmethod
    def _map_climate_tipo_operacao(row: RecommendationResult) -> str:
        rule_code = (row.rule_code or "").upper()
        title = (row.title or "").upper()
        summary = (row.summary or "").upper()
        reference = " ".join((rule_code, title, summary))
        if any(token in reference for token in ("PULVER", "VENTO", "JANELA")):
            return "PULVERIZACAO"
        if any(token in reference for token in ("COLHEITA", "CHUVA")):
            return "COLHEITA"
        if any(token in reference for token in ("ADUB", "FERT")):
            return "ADUBACAO"
        return "GERAL"

    def _serialize_climate_recommendation(
        self,
        unidade_produtiva_id: uuid.UUID,
        tipo_operacao: str,
        row: RecommendationResult,
    ) -> dict[str, Any]:
        status, severidade = self._legacy_climate_status(row.priority)
        return {
            "unidade_produtiva_id": unidade_produtiva_id,
            "tipo_operacao": tipo_operacao,
            "status": status,
            "severidade": severidade,
            "motivo": row.summary or row.rationale,
            "dados_utilizados": row.context or {},
            "data_referencia": row.updated_at or row.created_at,
            "fonte": row.provider_name,
            "validade_horas": self._climate_validity_hours(row),
        }

    @staticmethod
    def _legacy_climate_status(priority: str) -> tuple[str, str]:
        if priority == "URGENT":
            return "NAO_RECOMENDADO", "CRITICAL"
        if priority == "HIGH":
            return "ATENCAO", "WARNING"
        if priority == "NORMAL":
            return "RECOMENDADO", "NORMAL"
        return "RECOMENDADO", "NORMAL"

    @staticmethod
    def _climate_validity_hours(row: RecommendationResult) -> int:
        if not row.expires_at or not row.updated_at:
            return 12
        delta = row.expires_at - row.updated_at
        hours = int(delta.total_seconds() // 3600)
        return hours if hours > 0 else 12

    async def push(self, items: list[SyncPushItem]) -> list[SyncPushItemResult]:
        results: list[SyncPushItemResult] = []

        for item in items:
            try:
                result = await self._process_item(item)
                results.append(result)
            except Exception as exc:
                logger.warning(f"[sync/push] Erro ao processar item {item.local_id}: {exc}")
                results.append(
                    SyncPushItemResult(
                        local_id=item.local_id,
                        status="ERROR",
                        error_message=str(exc),
                    )
                )

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
        tipo_pecuario = _normalizar_tipo_pecuaria(payload.get("type"))

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
            existing_task = existing.scalar_one_or_none()
            if existing_task:
                return SyncPushItemResult(
                    local_id=item.local_id,
                    status="CREATED",
                    server_id=str(existing_task.id) if existing_task else None,
                )

            task = TarefaCampo(
                tenant_id=self.tenant_id,
                dispositivo_id=self.device.id,
                user_id=self.device.user_id,
                client_id=item.local_id,
                origem="MANUAL",
                status_execucao="CONCLUIDA",
                type=tipo_pecuario or str(payload.get("type", "")),
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

            if (
                task.module == "pecuaria"
                and task.type
                in {
                    "PESAGEM",
                    "VACINACAO",
                    "COBERTURA",
                    "INSEMINACAO",
                    "DIAGNOSTICO_PRENHEZ",
                    "PARTO",
                    "DESMAME",
                }
                and task.status_execucao == "CONCLUIDA"
            ):
                self.tarefas_pecuaria_sync.append(task.id)
            if (
                task.module == "agricola"
                and (
                    task.type in _TIPOS_TAREFA_AGRICOLA_MATERIALIZAVEIS
                    or task.operacao_agricola_id is not None
                )
                and task.status_execucao == "CONCLUIDA"
            ):
                self.tarefas_agricola_sync.append(task.id)

            return SyncPushItemResult(
                local_id=item.local_id, status="CREATED", server_id=str(task.id)
            )

        if item.operation == "UPDATE":
            if not item.server_id:
                return SyncPushItemResult(
                    local_id=item.local_id,
                    status="ERROR",
                    error_message="server_id obrigatório para UPDATE",
                )

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
                return SyncPushItemResult(
                    local_id=item.local_id, status="ERROR", error_message="Tarefa não encontrada"
                )

            tipo_existente = _normalizar_tipo_pecuaria(task.type)
            if tipo_existente and task.type != tipo_existente:
                task.type = tipo_existente

            # Para mutações vindas do PWA, a ordenação correta é pelo relógio do cliente
            # quando ele existe no servidor; `updated_at` inclui o tempo de processamento
            # do backend e pode rejeitar transições válidas em sequência rápida
            # (ex.: EM_EXECUCAO -> CONCLUIDA na mesma tarefa).
            server_clock = task.client_updated_at or task.updated_at
            if task.type.startswith("APLICACAO") or _to_naive_utc(
                item.client_updated_at
            ) >= _to_naive_utc(server_clock):
                task.status = payload.get("status", task.status)
                task.dados = payload.get("dados", task.dados)
                task.client_updated_at = _parse_dt(item.client_updated_at)

                # Atualizar execução de tarefas programadas
                novo_status_exec = payload.get("status_execucao")
                if novo_status_exec:
                    _aplicar_status_execucao(task, novo_status_exec, payload)

                await self.session.flush()

                if (
                    task.module == "pecuaria"
                    and task.type
                    in {
                        "PESAGEM",
                        "VACINACAO",
                        "COBERTURA",
                        "INSEMINACAO",
                        "DIAGNOSTICO_PRENHEZ",
                        "PARTO",
                        "DESMAME",
                    }
                    and task.status_execucao == "CONCLUIDA"
                ):
                    self.tarefas_pecuaria_sync.append(task.id)
                if (
                    task.module == "agricola"
                    and (
                        task.type in _TIPOS_TAREFA_AGRICOLA_MATERIALIZAVEIS
                        or task.operacao_agricola_id is not None
                    )
                    and task.status_execucao == "CONCLUIDA"
                ):
                    self.tarefas_agricola_sync.append(task.id)

                return SyncPushItemResult(
                    local_id=item.local_id, status="UPDATED", server_id=str(task.id)
                )
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

        return SyncPushItemResult(
            local_id=item.local_id, status="ERROR", error_message="Operação desconhecida"
        )


def _first_non_empty(*values: object) -> str | None:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _aplicar_status_execucao(task: TarefaCampo, novo: str, payload: dict) -> None:
    """Aplica transição de status_execucao com regras de negócio."""
    if novo == "EM_EXECUCAO":
        if task.status_execucao in {"CONCLUIDA", "CANCELADA", "INVALIDADA"}:
            raise BusinessRuleError("Esta tarefa já integra o histórico operacional.")
        task.status_execucao = "EM_EXECUCAO"
        if not task.iniciada_em:
            task.iniciada_em = datetime.utcnow()
    elif novo == "CONCLUIDA":
        if task.status_execucao not in {"PENDENTE", "EM_EXECUCAO"}:
            raise BusinessRuleError("Só é possível CONCLUIR uma tarefa pendente ou em execução")
        if task.status_execucao == "PENDENTE" and not task.iniciada_em:
            task.iniciada_em = datetime.utcnow()
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
        if task.status_execucao in {"CONCLUIDA", "INVALIDADA"}:
            raise BusinessRuleError("Esta tarefa já integra o histórico operacional.")
        if task.status_execucao == "CANCELADA":
            return
        if task.status_execucao not in {"PENDENTE", "EM_EXECUCAO"}:
            raise BusinessRuleError("Só é possível cancelar uma tarefa pendente ou em execução.")
        task.status_execucao = "CANCELADA"


def _normalizar_tipo_pecuaria(tipo: object) -> str | None:
    if not isinstance(tipo, str) or not tipo:
        return None
    if tipo == "PESAGEM_ANIMAL":
        return "PESAGEM"
    if tipo == "VACINACAO_LOTE":
        return "VACINACAO"
    if tipo == "PARTO_REGISTRO":
        return "PARTO"
    if tipo == "DESMAME_REGISTRO":
        return "DESMAME"
    return tipo


class TarefaProgramadaService:
    def __init__(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID | None,
        ip_address: str | None = None,
    ):
        self.session = session
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.ip_address = ip_address

    async def criar(self, data: TarefaProgramadaCreate) -> TarefaCampo:
        now = datetime.utcnow()
        task = TarefaCampo(
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            client_id=str(uuid.uuid4()),
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
            client_created_at=now,
            client_updated_at=now,
        )
        self.session.add(task)
        await self.session.flush()
        return task

    async def criar_vinculada_operacao(
        self,
        *,
        safra_tarefa_id: uuid.UUID,
        operacao_agricola_id: uuid.UUID,
        titulo: str,
        type: str,
        data_programada,
        unidade_produtiva_id: uuid.UUID | None,
        area_rural_id: uuid.UUID | None,
        operador_id: uuid.UUID | None,
        prioridade: str = "NORMAL",
    ) -> TarefaCampo:
        """Cria a TarefaCampo espelho de uma OS gerada em agricola/tarefas.

        Ao concluir esta tarefa, `processar_tarefa_campo` marca a OperacaoAgricola
        vinculada como REALIZADA em vez de tentar criar uma nova (ver
        `operacao_agricola_id`).
        """
        now = datetime.utcnow()
        dados = await _buscar_contexto_safra_tarefa(
            self.session,
            self.tenant_id,
            safra_tarefa_id,
        )
        task = TarefaCampo(
            tenant_id=self.tenant_id,
            user_id=self.user_id or uuid.uuid4(),
            client_id=str(uuid.uuid4()),
            origem="PROGRAMADA",
            status_execucao="PENDENTE",
            titulo=titulo,
            type=type,
            module="agricola",
            data_programada=data_programada,
            prioridade=prioridade,
            unidade_produtiva_id=unidade_produtiva_id,
            area_rural_id=area_rural_id,
            operador_id=operador_id,
            safra_tarefa_id=safra_tarefa_id,
            operacao_agricola_id=operacao_agricola_id,
            dados=dados,
            status="PENDENTE",
            fotos=[],
            localizacao_status="INDISPONIVEL",
            client_created_at=now,
            client_updated_at=now,
        )
        self.session.add(task)
        await self.session.flush()
        return task

    async def atualizar(self, tarefa_id: uuid.UUID, data: TarefaProgramadaUpdate) -> TarefaCampo:
        task = await self.get_or_fail(tarefa_id)
        if task.origem != "PROGRAMADA":
            raise BusinessRuleError("Apenas tarefas programadas podem ser editadas por este fluxo.")
        if task.status_execucao != "PENDENTE":
            raise BusinessRuleError("Só é possível editar tarefas ainda pendentes.")

        patch = data.model_dump(exclude_unset=True)
        for field in [
            "titulo",
            "type",
            "module",
            "data_programada",
            "prioridade",
            "unidade_produtiva_id",
            "area_rural_id",
            "lote_id",
            "operador_id",
            "dispositivo_id",
            "dados",
        ]:
            if field in patch:
                setattr(task, field, patch[field])

        task.client_updated_at = datetime.utcnow()
        await self.session.flush()
        return task

    async def listar(
        self,
        fazenda_id: uuid.UUID | None = None,
        safra_id: uuid.UUID | None = None,
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
        if safra_id:
            from agricola.cultivos.models import Cultivo, CultivoArea
            from agricola.tarefas.models import SafraTarefa

            talhoes_safra = (
                select(CultivoArea.area_id)
                .join(Cultivo, Cultivo.id == CultivoArea.cultivo_id)
                .where(Cultivo.safra_id == safra_id)
            )
            tarefas_safra = select(SafraTarefa.id).where(SafraTarefa.safra_id == safra_id)
            filters.append(
                or_(
                    TarefaCampo.area_rural_id.in_(talhoes_safra),
                    TarefaCampo.safra_tarefa_id.in_(tarefas_safra),
                )
            )
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
        _aplicar_status_execucao(
            task,
            data.status_execucao,
            {
                "obs": data.obs,
                "fotos": data.fotos,
                "localizacao_status": data.localizacao_status,
                "latitude": data.latitude,
                "longitude": data.longitude,
            },
        )
        await self.session.flush()
        return task

    async def cancelar(self, tarefa_id: uuid.UUID) -> TarefaCampo:
        task = await self.get_or_fail(tarefa_id)
        if task.status_execucao in {"CONCLUIDA", "INVALIDADA"}:
            raise BusinessRuleError("Esta tarefa já integra o histórico operacional.")
        if task.status_execucao not in {"PENDENTE", "EM_EXECUCAO"}:
            raise BusinessRuleError("Só é possível cancelar uma tarefa pendente ou em execução.")
        task.status_execucao = "CANCELADA"
        await self.session.flush()
        return task

    async def invalidar(self, tarefa_id: uuid.UUID, motivo: str) -> TarefaCampo:
        task = await self.get_or_fail(tarefa_id)
        motivo_limpo = (motivo or "").strip()
        if not motivo_limpo:
            raise BusinessRuleError("Motivo de invalidação é obrigatório.")
        if task.status_execucao != "CONCLUIDA":
            raise BusinessRuleError("Só é possível invalidar tarefas concluídas.")

        payload_before = _serialize(task)
        task.status_execucao = "INVALIDADA"
        task.invalidado_em = datetime.utcnow()
        task.invalidado_por = self.user_id
        task.motivo_invalidacao = motivo_limpo
        await self.session.flush()

        await write_audit_log(
            self.session,
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            action="invalidate",
            resource=TarefaCampo.__tablename__,
            resource_id=task.id,
            payload_before=payload_before,
            payload_after=_serialize(task),
            ip_address=self.ip_address,
        )

        from agricola.caderno.service import CadernoCampoService

        caderno_svc = CadernoCampoService(
            self.session, self.tenant_id, user_id=self.user_id, ip_address=self.ip_address
        )
        await caderno_svc.propagar_invalidacao_origem_operacional(
            tarefa_id=task.id,
            motivo=motivo_limpo,
            usuario_id=self.user_id,
            operacao_ids=[],
            ip_address=self.ip_address,
        )
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
        return _to_naive_utc(val)
    try:
        return _to_naive_utc(datetime.fromisoformat(str(val)))
    except Exception:
        return datetime.utcnow()


def _to_naive_utc(value: datetime | None) -> datetime:
    if value is None:
        return datetime.utcnow()
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)
