from __future__ import annotations

import uuid
from datetime import date, datetime, time, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.cadastros.propriedades.models import AreaRural, TipoArea
from core.cadastros.produtos.models import Produto, TipoProduto
from core.cadastros.pessoas.models import Pessoa
from core.exceptions import BusinessRuleError, EntityNotFoundError
from campo.models import TarefaCampo
from pecuaria.animal.models import Animal, LoteAnimal
from pecuaria.schemas.manejo_planejamento_schema import (
    ManejoPlanejamentoAnimalItem,
    ManejoPlanejamentoCreate,
    ManejoPlanejamentoFiltro,
    ManejoPlanejamentoListResponse,
    ManejoPlanejamentoLoteResumo,
    ManejoPlanejamentoOperadorResumo,
    ManejoPlanejamentoResponse,
)


class ManejoPlanejamentoService:
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id

    async def planejar(self, payload: ManejoPlanejamentoCreate, user_id: uuid.UUID) -> ManejoPlanejamentoResponse:
        lote = await self._get_lote(payload.lote_id)
        operador = await self._get_operador(payload.operador_id)
        animais = await self._resolver_animais(lote.id, payload.animais_ids)
        if payload.tipo == "VACINACAO":
            produto = await self._get_produto_vacina(payload.produto_id)
            tarefa = self._build_tarefa_vacinacao(payload, lote, operador, animais, produto, user_id)
        else:
            tarefa = self._build_tarefa_pesagem(payload, lote, operador, animais, user_id)
        self.db.add(tarefa)
        await self.db.flush()
        await self.db.refresh(tarefa)
        return self._to_response(tarefa, lote, operador, animais)

    async def planejar_pesagem(self, payload: ManejoPlanejamentoCreate, user_id: uuid.UUID) -> ManejoPlanejamentoResponse:
        return await self.planejar(payload, user_id)

    async def listar_planejados(self, filtro: ManejoPlanejamentoFiltro) -> ManejoPlanejamentoListResponse:
        stmt = self._base_query()
        stmt = self._aplicar_filtros(stmt, filtro)
        total = await self._count_query(stmt)
        tarefas = await self._page_query(stmt, filtro.page, filtro.page_size)
        lotes, operadores = await self._carregar_relacionados(tarefas)
        items = [self._to_response(t, lotes.get(t.lote_id), operadores.get(t.operador_id)) for t in tarefas]
        total_pages = (total + filtro.page_size - 1) // filtro.page_size if total else 0
        return ManejoPlanejamentoListResponse(items=items, total=total, page=filtro.page, page_size=filtro.page_size, total_pages=total_pages)

    def _base_query(self):
        return select(TarefaCampo).where(
            TarefaCampo.tenant_id == self.tenant_id,
            TarefaCampo.module == "pecuaria",
            TarefaCampo.origem == "PROGRAMADA",
        )

    def _aplicar_filtros(self, stmt, filtro: ManejoPlanejamentoFiltro):
        if filtro.tipo:
            stmt = stmt.where(TarefaCampo.type == filtro.tipo)
        if filtro.lote_id:
            stmt = stmt.where(TarefaCampo.lote_id == filtro.lote_id)
        if filtro.operador_id:
            stmt = stmt.where(TarefaCampo.operador_id == filtro.operador_id)
        if filtro.status:
            stmt = stmt.where(TarefaCampo.status_execucao == filtro.status)
        if filtro.data_inicio:
            stmt = stmt.where(TarefaCampo.data_programada >= filtro.data_inicio)
        if filtro.data_fim:
            stmt = stmt.where(TarefaCampo.data_programada <= filtro.data_fim)
        if filtro.unidade_produtiva_id:
            stmt = stmt.where(TarefaCampo.unidade_produtiva_id == filtro.unidade_produtiva_id)
        return stmt

    async def _count_query(self, stmt) -> int:
        res = await self.db.execute(select(func.count()).select_from(stmt.subquery()))
        return int(res.scalar() or 0)

    async def _page_query(self, stmt, page: int, page_size: int) -> list[TarefaCampo]:
        paged = stmt.order_by(TarefaCampo.data_programada.desc(), TarefaCampo.created_at.desc())
        paged = paged.offset((page - 1) * page_size).limit(page_size)
        res = await self.db.execute(paged)
        return list(res.scalars().all())

    async def _carregar_relacionados(self, tarefas: list[TarefaCampo]) -> tuple[dict[uuid.UUID, LoteAnimal], dict[uuid.UUID, Pessoa]]:
        lote_ids = [t.lote_id for t in tarefas if t.lote_id]
        operador_ids = [t.operador_id for t in tarefas if t.operador_id]
        lotes = await self._map_lotes(lote_ids)
        operadores = await self._map_operadores(operador_ids)
        return lotes, operadores

    async def _map_lotes(self, lote_ids: list[uuid.UUID]) -> dict[uuid.UUID, LoteAnimal]:
        if not lote_ids:
            return {}
        res = await self.db.execute(select(LoteAnimal).where(LoteAnimal.id.in_(lote_ids), LoteAnimal.tenant_id == self.tenant_id))
        return {l.id: l for l in res.scalars().all()}

    async def _map_operadores(self, operador_ids: list[uuid.UUID]) -> dict[uuid.UUID, Pessoa]:
        if not operador_ids:
            return {}
        res = await self.db.execute(select(Pessoa).where(Pessoa.id.in_(operador_ids), Pessoa.tenant_id == self.tenant_id))
        return {p.id: p for p in res.scalars().all()}

    async def _get_lote(self, lote_id: uuid.UUID) -> LoteAnimal:
        res = await self.db.execute(
            select(LoteAnimal).where(LoteAnimal.id == lote_id, LoteAnimal.tenant_id == self.tenant_id, LoteAnimal.ativo == True)
        )
        lote = res.scalars().first()
        if not lote:
            raise EntityNotFoundError(f"Lote {lote_id} não encontrado neste tenant.")
        await self._validar_area_lote(lote)
        return lote

    async def _validar_area_lote(self, lote: LoteAnimal) -> AreaRural | None:
        if not lote.area_id:
            return None

        res = await self.db.execute(
            select(AreaRural).where(
                AreaRural.id == lote.area_id,
                AreaRural.tenant_id == self.tenant_id,
                AreaRural.unidade_produtiva_id == lote.unidade_produtiva_id,
            )
        )
        area = res.scalars().first()
        if not area:
            raise EntityNotFoundError(f"Área {lote.area_id} vinculada ao lote não encontrada neste tenant.")
        if not area.ativo:
            raise BusinessRuleError("A área vinculada ao lote está inativa.")
        if area.tipo != TipoArea.PIQUETE.value:
            raise BusinessRuleError("A área vinculada ao lote deve ser do tipo PIQUETE.")
        return area

    async def _get_operador(self, operador_id: uuid.UUID | None) -> Pessoa | None:
        if not operador_id:
            return None
        res = await self.db.execute(
            select(Pessoa).where(Pessoa.id == operador_id, Pessoa.tenant_id == self.tenant_id, Pessoa.ativo == True)
        )
        operador = res.scalars().first()
        if not operador:
            raise EntityNotFoundError(f"Operador {operador_id} não encontrado neste tenant.")
        return operador

    async def _get_produto_vacina(self, produto_id: uuid.UUID | None) -> Produto:
        if not produto_id:
            raise BusinessRuleError("produto_id é obrigatório para planejamento de vacinação.")
        res = await self.db.execute(
            select(Produto).where(
                Produto.id == produto_id,
                or_(Produto.tenant_id.is_(None), Produto.tenant_id == self.tenant_id),
                Produto.ativo == True,
            )
        )
        produto = res.scalars().first()
        if not produto:
            raise EntityNotFoundError(f"Produto {produto_id} não encontrado neste tenant.")
        if produto.tipo != TipoProduto.VACINA.value:
            raise BusinessRuleError("O produto informado para vacinação deve ser do tipo VACINA.")
        return produto

    async def _resolver_animais(self, lote_id: uuid.UUID, animais_ids: list[uuid.UUID]) -> list[Animal]:
        ids = list(dict.fromkeys(animais_ids))
        if ids:
            return await self._validar_animais_especificos(lote_id, ids)
        return await self._buscar_animais_ativos(lote_id)

    async def _buscar_animais_ativos(self, lote_id: uuid.UUID) -> list[Animal]:
        res = await self.db.execute(
            select(Animal).where(
                Animal.tenant_id == self.tenant_id,
                Animal.lote_id == lote_id,
                Animal.status == "ATIVO",
            ).order_by(Animal.numero_brinco.asc().nulls_last(), Animal.created_at.asc())
        )
        animais = list(res.scalars().all())
        if not animais:
            raise BusinessRuleError("Não há animais ativos disponíveis neste lote para planejamento.")
        return animais

    async def _validar_animais_especificos(self, lote_id: uuid.UUID, animais_ids: list[uuid.UUID]) -> list[Animal]:
        res = await self.db.execute(
            select(Animal).where(Animal.tenant_id == self.tenant_id, Animal.id.in_(animais_ids))
        )
        encontrados = {animal.id: animal for animal in res.scalars().all()}
        faltantes = [str(animal_id) for animal_id in animais_ids if animal_id not in encontrados]
        if faltantes:
            raise EntityNotFoundError(f"Animais não encontrados neste tenant: {', '.join(faltantes)}")
        erros: list[str] = []
        selecionados: list[Animal] = []
        for animal_id in animais_ids:
            animal = encontrados[animal_id]
            if animal.lote_id != lote_id:
                erros.append(f"Animal {animal.id} não pertence ao lote {lote_id}.")
            if animal.status != "ATIVO":
                erros.append(f"Animal {animal.id} não está ativo.")
            selecionados.append(animal)
        if erros:
            raise BusinessRuleError(" ".join(erros))
        return selecionados

    def _build_tarefa_pesagem(
        self,
        payload: ManejoPlanejamentoCreate,
        lote: LoteAnimal,
        operador: Pessoa | None,
        animais: list[Animal],
        user_id: uuid.UUID,
    ) -> TarefaCampo:
        return self._build_tarefa_base(
            payload=payload,
            lote=lote,
            operador=operador,
            user_id=user_id,
            tipo="PESAGEM",
            titulo=f"Pesagem programada - {lote.identificacao}",
            dados=self._build_dados_pesagem(payload, lote, animais),
        )

    def _build_tarefa_vacinacao(
        self,
        payload: ManejoPlanejamentoCreate,
        lote: LoteAnimal,
        operador: Pessoa | None,
        animais: list[Animal],
        produto: Produto,
        user_id: uuid.UUID,
    ) -> TarefaCampo:
        return self._build_tarefa_base(
            payload=payload,
            lote=lote,
            operador=operador,
            user_id=user_id,
            tipo="VACINACAO",
            titulo=f"Vacinação programada - {lote.identificacao}",
            dados=self._build_dados_vacinacao(payload, lote, animais, produto),
        )

    def _build_tarefa_base(
        self,
        payload: ManejoPlanejamentoCreate,
        lote: LoteAnimal,
        operador: Pessoa | None,
        user_id: uuid.UUID,
        tipo: str,
        titulo: str,
        dados: dict,
    ) -> TarefaCampo:
        now = datetime.utcnow()
        return TarefaCampo(
            tenant_id=self.tenant_id,
            user_id=user_id,
            client_id=str(uuid.uuid4()),
            operador_id=operador.id if operador else None,
            origem="PROGRAMADA",
            status_execucao="PENDENTE",
            status="PENDENTE",
            titulo=titulo,
            data_programada=payload.data_programada,
            prioridade="NORMAL",
            type=tipo,
            module="pecuaria",
            unidade_produtiva_id=lote.unidade_produtiva_id,
            area_rural_id=lote.area_id,
            lote_id=lote.id,
            dados=dados,
            fotos=[],
            localizacao_status="INDISPONIVEL",
            client_created_at=now,
            client_updated_at=now,
        )

    def _build_dados_pesagem(self, payload: ManejoPlanejamentoCreate, lote: LoteAnimal, animais: list[Animal]) -> dict:
        dados = {
            "lote_id": str(payload.lote_id),
            "data_evento": datetime.combine(payload.data_programada, time.min, tzinfo=timezone.utc).isoformat().replace("+00:00", "Z"),
            "tipo": "PESAGEM",
            "observacoes": payload.observacoes,
            "area_id": str(lote.area_id) if lote.area_id else None,
            "animais": [
                {
                    "animal_id": str(animal.id),
                    "numero_brinco": animal.numero_brinco,
                    "peso_kg": None,
                    "observacao": None,
                }
                for animal in animais
            ],
        }
        return dados

    def _build_dados_vacinacao(
        self,
        payload: ManejoPlanejamentoCreate,
        lote: LoteAnimal,
        animais: list[Animal],
        produto: Produto,
    ) -> dict:
        return {
            "lote_id": str(payload.lote_id),
            "area_id": str(lote.area_id) if lote.area_id else None,
            "data_evento": datetime.combine(payload.data_programada, time.min, tzinfo=timezone.utc).isoformat().replace("+00:00", "Z"),
            "tipo": "VACINACAO",
            "produto_id": str(produto.id),
            "dose": payload.dose,
            "unidade_medida": payload.unidade_medida,
            "via_aplicacao": payload.via_aplicacao,
            "observacoes": payload.observacoes,
            "animais_ids": [str(animal.id) for animal in animais],
        }

    def _extrair_animais(self, tarefa: TarefaCampo) -> list[ManejoPlanejamentoAnimalItem]:
        dados = tarefa.dados or {}
        animais = dados.get("animais") or []
        if not animais and dados.get("animais_ids"):
            return [
                ManejoPlanejamentoAnimalItem(animal_id=item, numero_brinco=None, peso_kg=None, observacao=None)
                for item in dados.get("animais_ids") or []
            ]
        return [
            ManejoPlanejamentoAnimalItem(
                animal_id=item.get("animal_id"),
                numero_brinco=item.get("numero_brinco"),
                peso_kg=item.get("peso_kg"),
                observacao=item.get("observacao"),
            )
            for item in animais
        ]

    def _to_response(
        self,
        tarefa: TarefaCampo,
        lote: LoteAnimal | None,
        operador: Pessoa | None,
        animais: list[Animal] | None = None,
    ) -> ManejoPlanejamentoResponse:
        dados = tarefa.dados or {}
        animais_resumo = (
            [
                ManejoPlanejamentoAnimalItem(
                    animal_id=animal.id,
                    numero_brinco=animal.numero_brinco,
                    peso_kg=animal.peso_atual_kg if tarefa.type == "PESAGEM" else None,
                    observacao=None,
                )
                for animal in animais
            ]
            if animais is not None
            else self._extrair_animais(tarefa)
        )
        return ManejoPlanejamentoResponse(
            tarefa_campo_id=tarefa.id,
            tipo=tarefa.type,
            lote=ManejoPlanejamentoLoteResumo(id=lote.id, identificacao=lote.identificacao) if lote else ManejoPlanejamentoLoteResumo(id=tarefa.lote_id, identificacao="-"),
            area_id=tarefa.area_rural_id or (lote.area_id if lote else None),
            operador=ManejoPlanejamentoOperadorResumo(id=operador.id, nome_exibicao=operador.nome_exibicao) if operador else None,
            status=tarefa.status_execucao,
            origem=tarefa.origem,
            data_programada=tarefa.data_programada or _parse_planned_date(dados.get("data_programada")),
            quantidade_animais=len(animais) if animais is not None else self._quantidade_animais(dados),
            observacoes=dados.get("observacoes"),
            animais=animais_resumo,
        )

    def _quantidade_animais(self, dados: dict) -> int:
        animais = dados.get("animais") or []
        if animais:
            return len(animais)
        animais_ids = dados.get("animais_ids") or []
        return len(animais_ids)


def _parse_planned_date(value: object) -> date:
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value).date()
        except ValueError:
            return datetime.now(timezone.utc).date()
    return datetime.now(timezone.utc).date()
