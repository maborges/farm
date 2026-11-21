import uuid
from datetime import date

from sqlalchemy import and_, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from core.base_service import BaseService
from core.exceptions import EntityNotFoundError
from financeiro.models.despesa import Despesa
from financeiro.models.plano_conta import PlanoConta
from financeiro.schemas.despesa_schema import DespesaCreate
from financeiro.services.despesa_service import DespesaService
from pecuaria.animal.models import Animal, EventoAnimal, LoteAnimal
from pecuaria.schemas.animal_schema import AnimalCreate, AnimalFilter, AnimalUpdate


class AnimalService(BaseService[Animal]):
    COMPRA_EXTRAS_FIELDS = {"fornecedor", "numero_nf", "serie_nf", "chave_nfe"}

    def __init__(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
        ip_address: str | None = None,
    ):
        super().__init__(Animal, session, tenant_id, user_id, ip_address)

    async def _validate_references(self, data: dict):
        # Validação do lote_id
        if data.get("lote_id"):
            lote_id = data["lote_id"]
            stmt = select(LoteAnimal).where(
                and_(LoteAnimal.id == lote_id, LoteAnimal.tenant_id == self.tenant_id)
            )
            result = await self.session.execute(stmt)
            if not result.scalar_one_or_none():
                raise EntityNotFoundError(f"Lote com ID {lote_id} não encontrado neste tenant.")

        # Validação de pai_id
        if data.get("pai_id"):
            pai_id = data["pai_id"]
            stmt = select(Animal).where(
                and_(Animal.id == pai_id, Animal.tenant_id == self.tenant_id)
            )
            result = await self.session.execute(stmt)
            if not result.scalar_one_or_none():
                raise EntityNotFoundError(
                    f"Animal Pai com ID {pai_id} não encontrado neste tenant."
                )

        # Validação de mae_id
        if data.get("mae_id"):
            mae_id = data["mae_id"]
            stmt = select(Animal).where(
                and_(Animal.id == mae_id, Animal.tenant_id == self.tenant_id)
            )
            result = await self.session.execute(stmt)
            if not result.scalar_one_or_none():
                raise EntityNotFoundError(
                    f"Animal Mãe com ID {mae_id} não encontrado neste tenant."
                )

    def _extrair_dados_compra(self, data: dict) -> dict:
        compra: dict[str, str] = {}
        for field in self.COMPRA_EXTRAS_FIELDS:
            if field not in data:
                continue
            value = data.pop(field)
            if value in (None, ""):
                continue
            compra[field] = value
        if not compra:
            return {}
        return compra

    def _mesclar_dados_extras(self, data: dict, compra: dict) -> dict | None:
        extras = data.get("dados_extras") or {}
        if not isinstance(extras, dict):
            extras = {}
        if compra:
            extras = {**extras, "compra": {**(extras.get("compra") or {}), **compra}}
        return extras or None

    async def _resolver_plano_conta_compra(self) -> uuid.UUID:
        stmt = (
            select(PlanoConta.id)
            .where(
                PlanoConta.tenant_id == self.tenant_id,
                PlanoConta.ativo,
                or_(
                    PlanoConta.codigo == "4.03",
                    PlanoConta.nome.ilike("%Aquisição de Animais%"),
                ),
            )
            .order_by(PlanoConta.codigo)
            .limit(1)
        )
        plano_id = (await self.session.execute(stmt)).scalar_one_or_none()
        if plano_id:
            return plano_id
        stmt = (
            select(PlanoConta.id)
            .where(
                PlanoConta.tenant_id == self.tenant_id,
                PlanoConta.ativo,
                PlanoConta.categoria_rfb == "INVESTIMENTO",
                PlanoConta.natureza == "ANALITICA",
            )
            .order_by(PlanoConta.codigo)
            .limit(1)
        )
        plano_id = (await self.session.execute(stmt)).scalar_one_or_none()
        if not plano_id:
            raise EntityNotFoundError(
                "Plano de contas para aquisição de animais não encontrado neste tenant."
            )
        return plano_id

    async def _obter_evento_compra_existente(self, animal_id: uuid.UUID) -> EventoAnimal | None:
        stmt = select(EventoAnimal).where(
            EventoAnimal.tenant_id == self.tenant_id,
            EventoAnimal.animal_id == animal_id,
            EventoAnimal.tipo == "COMPRA",
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def _obter_despesa_compra_existente(self, origem_id: uuid.UUID) -> Despesa | None:
        stmt = select(Despesa).where(
            Despesa.tenant_id == self.tenant_id,
            Despesa.origem_tipo == "COMPRA",
            Despesa.origem_id == origem_id,
            Despesa.ativo,
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def _materializar_lote(self, lote_id: uuid.UUID | None) -> None:
        if lote_id is None:
            return

        stmt = select(
            func.count(Animal.id),
            func.coalesce(func.sum(Animal.peso_atual_kg), 0),
            func.count(Animal.peso_atual_kg),
        ).where(
            Animal.tenant_id == self.tenant_id,
            Animal.lote_id == lote_id,
            Animal.status == "ATIVO",
        )
        total, peso_total, quantidade_com_peso = (await self.session.execute(stmt)).one()
        lote = await self.session.get(LoteAnimal, lote_id)
        if not lote or lote.tenant_id != self.tenant_id:
            return

        qtd_ativos = int(total or 0)
        lote.quantidade_cabecas = qtd_ativos
        lote.peso_medio_kg = (
            float(peso_total or 0) / int(quantidade_com_peso or 0) if quantidade_com_peso else 0.0
        )
        if qtd_ativos > 0 and lote.modo_gestao == "POR_LOTE":
            lote.modo_gestao = "INDIVIDUAL"
        self.session.add(lote)

    async def _registrar_compra_financeira(
        self, animal: Animal, compra: dict | None = None
    ) -> tuple[EventoAnimal | None, Despesa | None]:
        if animal.valor_aquisicao is None or animal.valor_aquisicao <= 0:
            return None, None

        evento = await self._obter_evento_compra_existente(animal.id)
        compra = (
            compra
            or (
                (animal.dados_extras or {}).get("compra")
                if isinstance(animal.dados_extras, dict)
                else {}
            )
            or {}
        )
        if evento is None:
            evento = EventoAnimal(
                tenant_id=self.tenant_id,
                animal_id=animal.id,
                tipo="COMPRA",
                data_evento=animal.data_entrada or date.today(),
                peso_kg=animal.peso_atual_kg,
                valor=float(animal.valor_aquisicao),
                lote_destino_id=animal.lote_id,
                observacoes=animal.observacoes,
                dados_extras={
                    "compra": compra or None,
                    "unidade_produtiva_id": str(animal.unidade_produtiva_id),
                    "animal_id": str(animal.id),
                    "lote_id": str(animal.lote_id) if animal.lote_id else None,
                },
            )
            self.session.add(evento)
            await self.session.flush()

        despesa = await self._obter_despesa_compra_existente(evento.id)
        if despesa is None:
            plano_conta_id = await self._resolver_plano_conta_compra()
            descricao_identificacao = (
                animal.numero_brinco
                or animal.numero_sisbov
                or animal.microchip
                or animal.nome
                or str(animal.id)
            )
            despesa_service = DespesaService(self.session, self.tenant_id)
            despesa_payload = DespesaCreate(
                unidade_produtiva_id=animal.unidade_produtiva_id,
                plano_conta_id=plano_conta_id,
                descricao=f"Compra de animal {descricao_identificacao}",
                valor_total=float(animal.valor_aquisicao),
                data_emissao=animal.data_entrada or date.today(),
                data_vencimento=animal.data_entrada or date.today(),
                competencia=animal.data_entrada or date.today(),
                status="A_PAGAR",
                pessoa_id=None,
                fornecedor=compra.get("fornecedor") if isinstance(compra, dict) else None,
                numero_nf=compra.get("numero_nf") if isinstance(compra, dict) else None,
                serie_nf=compra.get("serie_nf") if isinstance(compra, dict) else None,
                chave_nfe=compra.get("chave_nfe") if isinstance(compra, dict) else None,
                origem_id=evento.id,
                origem_tipo="COMPRA",
            )
            despesas = await despesa_service.create_with_rateio(despesa_payload)
            despesa = despesas[0] if despesas else None

        if isinstance(animal.dados_extras, dict):
            compra_atual = dict(animal.dados_extras.get("compra") or {})
            extras_base = dict(animal.dados_extras)
        else:
            compra_atual = {}
            extras_base = {}
        if isinstance(compra, dict):
            compra_atual.update(compra)
        compra_atual.update(
            {
                "evento_compra_id": str(evento.id) if evento else None,
                "despesa_compra_id": str(despesa.id) if despesa else None,
            }
        )
        extras_base["compra"] = compra_atual
        animal.dados_extras = extras_base
        if animal.valor_atual is None:
            animal.valor_atual = animal.valor_aquisicao
        self.session.add(animal)
        await self.session.flush()
        return evento, despesa

    async def create(self, obj_in: AnimalCreate | dict) -> Animal:
        data = obj_in.model_dump() if isinstance(obj_in, AnimalCreate) else obj_in
        compra = self._extrair_dados_compra(data)
        data["dados_extras"] = self._mesclar_dados_extras(data, compra)
        await self._validate_references(data)
        animal = await super().create(data)
        await self._registrar_compra_financeira(animal, compra)
        if animal.lote_id:
            await self._materializar_lote(animal.lote_id)
        return animal

    async def update(self, id: uuid.UUID, obj_in: AnimalUpdate | dict) -> Animal:
        data = obj_in.model_dump(exclude_unset=True) if isinstance(obj_in, AnimalUpdate) else obj_in
        compra = self._extrair_dados_compra(data)
        if compra or "dados_extras" in data:
            data["dados_extras"] = self._mesclar_dados_extras(data, compra)
        await self._validate_references(data)
        animal_anterior = await self.get_or_fail(id)
        lote_anterior_id = animal_anterior.lote_id
        animal = await super().update(id, data)
        await self._registrar_compra_financeira(animal, compra)
        if lote_anterior_id != animal.lote_id:
            await self._materializar_lote(lote_anterior_id)
        await self._materializar_lote(animal.lote_id)
        return animal

    async def hard_delete(self, id: uuid.UUID) -> None:
        animal = await self.get_or_fail(id)
        lote_id = animal.lote_id
        await super().hard_delete(id)
        await self._materializar_lote(lote_id)

    async def list_paginated(
        self, skip: int, limit: int, unidade_produtiva_id: uuid.UUID, filter_params: AnimalFilter
    ) -> tuple[list[Animal], int]:
        stmt = select(Animal).where(
            and_(
                Animal.tenant_id == self.tenant_id,
                Animal.unidade_produtiva_id == unidade_produtiva_id,
            )
        )

        if filter_params.q:
            q = f"%{filter_params.q}%"
            stmt = stmt.where(
                or_(
                    Animal.numero_brinco.ilike(q),
                    Animal.numero_sisbov.ilike(q),
                    Animal.nome.ilike(q),
                )
            )

        if filter_params.lote_id:
            stmt = stmt.where(Animal.lote_id == filter_params.lote_id)
        if filter_params.categoria:
            stmt = stmt.where(Animal.categoria == filter_params.categoria)
        if filter_params.status:
            stmt = stmt.where(Animal.status == filter_params.status)
        if filter_params.sexo:
            stmt = stmt.where(Animal.sexo == filter_params.sexo)
        if filter_params.especie:
            stmt = stmt.where(Animal.especie == filter_params.especie)

        # Contagem total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.session.execute(count_stmt)).scalar() or 0

        # Paginação e ordenação (mais recentes primeiro)
        stmt = stmt.order_by(Animal.created_at.desc()).offset(skip).limit(limit)
        result = await self.session.execute(stmt)

        return list(result.scalars().all()), total
