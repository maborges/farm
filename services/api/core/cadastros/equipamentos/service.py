import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.base_service import BaseService
from core.exceptions import BusinessRuleError, EntityNotFoundError
from core.models.unidade_produtiva import UnidadeProdutiva
from .alocacao_service import criar_equipamento_alocacao
from .models import Equipamento, EquipamentoAlocacao, EquipamentoCalibracao
from .schemas import EquipamentoCreate, EquipamentoUpdate, EquipamentoCalibracaoCreate


class EquipamentoService(BaseService[Equipamento]):
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        super().__init__(Equipamento, session, tenant_id)

    async def _validar_unidade_produtiva(self, unidade_produtiva_id: uuid.UUID | None) -> None:
        if unidade_produtiva_id is None:
            return
        unidade = (
            await self.session.execute(
                select(UnidadeProdutiva.id).where(
                    UnidadeProdutiva.id == unidade_produtiva_id,
                    UnidadeProdutiva.tenant_id == self.tenant_id,
                    UnidadeProdutiva.ativo == True,
                )
            )
        ).scalar_one_or_none()
        if unidade is None:
            raise BusinessRuleError("Unidade produtiva do equipamento não localizada ou inacessível.")

    async def listar(
        self,
        tipo: Optional[str] = None,
        status: Optional[str] = None,
        unidade_produtiva_id: Optional[uuid.UUID] = None,
        q: Optional[str] = None,
        skip: int = 0,
        limit: int | None = None,
    ) -> list[Equipamento]:
        stmt = select(Equipamento).where(Equipamento.tenant_id == self.tenant_id)
        if tipo:
            stmt = stmt.where(Equipamento.tipo == tipo)
        if status:
            stmt = stmt.where(Equipamento.status == status)
        if q:
            stmt = stmt.where(Equipamento.nome.ilike(f"%{q}%"))
        if unidade_produtiva_id:
            agora = datetime.now(timezone.utc)
            allocated_ids = (
                select(EquipamentoAlocacao.equipamento_id)
                .where(
                    EquipamentoAlocacao.tenant_id == self.tenant_id,
                    EquipamentoAlocacao.unidade_produtiva_id == unidade_produtiva_id,
                    EquipamentoAlocacao.status == "ATIVA",
                    EquipamentoAlocacao.data_inicio <= agora,
                    (EquipamentoAlocacao.data_fim.is_(None) | (EquipamentoAlocacao.data_fim >= agora)),
                )
            )
            stmt = stmt.where((Equipamento.unidade_produtiva_id == unidade_produtiva_id) | (Equipamento.id.in_(allocated_ids)))
        stmt = stmt.order_by(Equipamento.nome.asc())
        if skip:
            stmt = stmt.offset(skip)
        if limit is not None:
            stmt = stmt.limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    async def criar(self, data: EquipamentoCreate) -> Equipamento:
        await self._validar_unidade_produtiva(data.unidade_produtiva_id)
        eq = Equipamento(tenant_id=self.tenant_id, **data.model_dump())
        self.session.add(eq)
        await self.session.flush()
        if eq.unidade_produtiva_id:
            await criar_equipamento_alocacao(
                self.session,
                tenant_id=self.tenant_id,
                equipamento_id=eq.id,
                unidade_produtiva_id=eq.unidade_produtiva_id,
                principal=True,
                observacao="Alocação inicial criada a partir do vínculo legado do equipamento.",
            )
        await self.session.refresh(eq)
        return eq

    async def obter(self, eq_id: uuid.UUID) -> Equipamento:
        stmt = select(Equipamento).where(Equipamento.id == eq_id, Equipamento.tenant_id == self.tenant_id)
        obj = (await self.session.execute(stmt)).scalar_one_or_none()
        if not obj:
            raise EntityNotFoundError("Equipamento não encontrado")
        return obj

    async def atualizar(self, eq_id: uuid.UUID, data: EquipamentoUpdate) -> Equipamento:
        obj = await self.obter(eq_id)
        updates = data.model_dump(exclude_none=True)
        if "unidade_produtiva_id" in updates:
            await self._validar_unidade_produtiva(updates["unidade_produtiva_id"])
        for k, v in updates.items():
            setattr(obj, k, v)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def desativar(self, eq_id: uuid.UUID) -> None:
        obj = await self.obter(eq_id)
        obj.status = "INATIVO"


class EquipamentoCalibracaoService(BaseService[EquipamentoCalibracao]):
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        super().__init__(EquipamentoCalibracao, session, tenant_id)

    async def criar_calibracao(self, data: EquipamentoCalibracaoCreate, criado_por_id: uuid.UUID | None = None) -> EquipamentoCalibracao:
        # Validate that equipment exists and belongs to the tenant
        eq = await self.session.get(Equipamento, data.equipamento_id)
        if not eq or eq.tenant_id != self.tenant_id:
            raise BusinessRuleError("Equipamento não localizado ou inacessível.")

        # Calculate hash_documental
        import hashlib
        payload_str = f"{self.tenant_id}:{data.equipamento_id}:{data.data_calibracao}:{data.metodo}:{data.vazao}:{data.pressao}:{criado_por_id}"
        hash_val = hashlib.sha256(payload_str.encode('utf-8')).hexdigest()

        calib = EquipamentoCalibracao(
            tenant_id=self.tenant_id,
            equipamento_id=data.equipamento_id,
            data_calibracao=data.data_calibracao,
            validade_ate=data.validade_ate,
            metodo=data.metodo,
            vazao=data.vazao,
            pressao=data.pressao,
            observacoes=data.observacoes,
            hash_documental=hash_val,
            criado_por=criado_por_id
        )
        self.session.add(calib)
        await self.session.flush()

        # Automate insertion of CadernoCampoEntrada event
        from agricola.safras.models import Safra
        from core.cadastros.propriedades.models import AreaRural
        from agricola.caderno.models import CadernoCampoEntrada

        safra_id, talhao_id, unidade_produtiva_id = await self._obter_contexto_safra_talhao_para_equipamento(data.equipamento_id)

        if safra_id and talhao_id:
            entrada = CadernoCampoEntrada(
                tenant_id=self.tenant_id,
                safra_id=safra_id,
                talhao_id=talhao_id,
                tipo="INSPECAO",
                tipo_evento="INSPECAO",
                descricao=f"Inspeção técnica e calibração do equipamento {eq.nome} (Vazão: {data.vazao} L/min, Pressão: {data.pressao} PSI, Método: {data.metodo}). Hash: {hash_val[:8].upper()}",
                data_registro=data.data_calibracao,
                usuario_id=criado_por_id or uuid.UUID("00000000-0000-0000-0000-000000000000"),
                origem_evento="CALIBRACAO_EQUIPAMENTO",
                origem_id=str(calib.id),
                origem_tecnica="CALIBRACAO",
                unidade_produtiva_id=unidade_produtiva_id,
                status_evento="CONSOLIDADO",
                payload_operacional={
                    "equipamento_id": str(data.equipamento_id),
                    "data_calibracao": data.data_calibracao.isoformat(),
                    "validade_ate": data.validade_ate.isoformat(),
                    "metodo": data.metodo,
                    "vazao": data.vazao,
                    "pressao": data.pressao,
                    "hash_documental": hash_val,
                }
            )
            self.session.add(entrada)
            await self.session.flush()

            # Register status history
            from agricola.caderno.service import CadernoCampoService
            caderno_svc = CadernoCampoService(self.session, self.tenant_id)
            await caderno_svc._registrar_historico_status(
                entrada,
                status_anterior=None,
                status_novo="CONSOLIDADO",
                justificativa="Registro automático de calibração de equipamento",
                usuario_id=criado_por_id,
            )

        await self.session.refresh(calib)
        return calib

    async def _obter_contexto_safra_talhao_para_equipamento(self, equipamento_id: uuid.UUID):
        from core.cadastros.equipamentos.models import EquipamentoAlocacao, Equipamento
        from core.cadastros.propriedades.models import AreaRural
        from agricola.safras.models import Safra

        alocacao = (await self.session.execute(
            select(EquipamentoAlocacao)
            .where(
                EquipamentoAlocacao.equipamento_id == equipamento_id,
                EquipamentoAlocacao.tenant_id == self.tenant_id,
                EquipamentoAlocacao.status == "ATIVA"
            )
            .order_by(EquipamentoAlocacao.data_inicio.desc())
        )).scalars().first()

        unidade_produtiva_id = None
        if alocacao:
            unidade_produtiva_id = alocacao.unidade_produtiva_id
        else:
            eq = await self.session.get(Equipamento, equipamento_id)
            if eq:
                unidade_produtiva_id = eq.unidade_produtiva_id

        talhao_id = None
        if unidade_produtiva_id:
            talhao_id = (await self.session.execute(
                select(AreaRural.id)
                .where(
                    AreaRural.unidade_produtiva_id == unidade_produtiva_id,
                    AreaRural.tenant_id == self.tenant_id
                )
                .limit(1)
            )).scalar()

        if not talhao_id:
            talhao_id = (await self.session.execute(
                select(AreaRural.id)
                .where(AreaRural.tenant_id == self.tenant_id)
                .limit(1)
            )).scalar()

        safra_id = (await self.session.execute(
            select(Safra.id)
            .where(
                Safra.tenant_id == self.tenant_id,
                Safra.status == "ATIVA"
            )
            .limit(1)
        )).scalar()

        if not safra_id:
            safra_id = (await self.session.execute(
                select(Safra.id)
                .where(Safra.tenant_id == self.tenant_id)
                .limit(1)
            )).scalar()

        return safra_id, talhao_id, unidade_produtiva_id
