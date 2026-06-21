from __future__ import annotations

from datetime import date, datetime, timezone
import uuid

from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.cadastros.propriedades.propriedade_models import Propriedade
from core.exceptions import BusinessRuleError, EntityNotFoundError
from imoveis.models.imovel import ImovelRural

from .models import PropriedadeImovel, TipoVinculoPropriedadeImovel
from .schemas import PropriedadeImovelCreate, PropriedadeImovelUpdate


class PropriedadeImovelService:
    """Regras de negócio do vínculo canônico entre Propriedades e Imóveis Rurais."""

    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        self.session = session
        self.tenant_id = tenant_id

    async def listar(
        self,
        propriedade_id: uuid.UUID | None = None,
        imovel_rural_id: uuid.UUID | None = None,
        tipo_vinculo: TipoVinculoPropriedadeImovel | None = None,
        ativo: bool | None = None,
        vinculo_principal: bool | None = None,
    ) -> list[PropriedadeImovel]:
        """Lista vínculos do tenant com filtros opcionais."""
        stmt = (
            select(PropriedadeImovel)
            .where(PropriedadeImovel.tenant_id == self.tenant_id)
            .options(
                selectinload(PropriedadeImovel.propriedade),
                selectinload(PropriedadeImovel.imovel_rural),
            )
            .order_by(
                desc(PropriedadeImovel.vinculo_principal),
                desc(PropriedadeImovel.ativo),
                desc(PropriedadeImovel.data_inicio),
                desc(PropriedadeImovel.created_at),
            )
        )
        if propriedade_id:
            stmt = stmt.where(PropriedadeImovel.propriedade_id == propriedade_id)
        if imovel_rural_id:
            stmt = stmt.where(PropriedadeImovel.imovel_rural_id == imovel_rural_id)
        if tipo_vinculo:
            stmt = stmt.where(PropriedadeImovel.tipo_vinculo == tipo_vinculo.value)
        if ativo is not None:
            stmt = stmt.where(PropriedadeImovel.ativo == ativo)
        if vinculo_principal is not None:
            stmt = stmt.where(PropriedadeImovel.vinculo_principal == vinculo_principal)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def obter(self, vinculo_id: uuid.UUID) -> PropriedadeImovel:
        """Obtém vínculo por ID dentro do tenant atual."""
        stmt = (
            select(PropriedadeImovel)
            .where(
                PropriedadeImovel.id == vinculo_id,
                PropriedadeImovel.tenant_id == self.tenant_id,
            )
            .options(
                selectinload(PropriedadeImovel.propriedade),
                selectinload(PropriedadeImovel.imovel_rural),
            )
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        if not obj:
            raise EntityNotFoundError("Vínculo propriedade-imóvel não encontrado.")
        return obj

    async def criar(
        self,
        data: PropriedadeImovelCreate,
        usuario_id: uuid.UUID | None = None,
    ) -> PropriedadeImovel:
        """Cria vínculo canônico respeitando tenant, vigência e principalidade."""
        payload = data.model_dump()
        await self._validar_referencias(payload["propriedade_id"], payload["imovel_rural_id"])
        self._validar_origem_documental(payload["origem_documental"])
        self._validar_campos_numericos(payload)
        self._validar_vigencia(payload["data_inicio"], payload.get("data_fim"))
        await self._validar_principalidade(
            propriedade_id=payload["propriedade_id"],
            data_inicio=payload["data_inicio"],
            data_fim=payload.get("data_fim"),
            vinculo_principal=payload["vinculo_principal"],
            ativo=payload["ativo"],
        )

        vinculo = PropriedadeImovel(
            tenant_id=self.tenant_id,
            created_by=usuario_id,
            updated_by=usuario_id,
            **payload,
        )
        self.session.add(vinculo)
        await self.session.commit()
        await self.session.refresh(vinculo)
        return vinculo

    async def atualizar(
        self,
        vinculo_id: uuid.UUID,
        data: PropriedadeImovelUpdate,
        usuario_id: uuid.UUID | None = None,
    ) -> PropriedadeImovel:
        """Atualiza vínculo sem permitir troca de tenant."""
        vinculo = await self.obter(vinculo_id)
        payload = data.model_dump(exclude_unset=True)
        if not payload:
            raise BusinessRuleError("Nenhum campo foi informado para atualização.")

        propriedade_id = payload.get("propriedade_id", vinculo.propriedade_id)
        imovel_rural_id = payload.get("imovel_rural_id", vinculo.imovel_rural_id)
        await self._validar_referencias(propriedade_id, imovel_rural_id)
        if "origem_documental" in payload:
            self._validar_origem_documental(payload["origem_documental"])

        data_inicio = payload.get("data_inicio", vinculo.data_inicio)
        data_fim = payload.get("data_fim", vinculo.data_fim)
        self._validar_campos_numericos(payload)
        self._validar_vigencia(data_inicio, data_fim)

        vinculo_principal = payload.get("vinculo_principal", vinculo.vinculo_principal)
        await self._validar_principalidade(
            propriedade_id=propriedade_id,
            data_inicio=data_inicio,
            data_fim=data_fim,
            vinculo_principal=vinculo_principal,
            ativo=payload.get("ativo", vinculo.ativo),
            exclude_id=vinculo.id,
        )

        for campo, valor in payload.items():
            setattr(vinculo, campo, valor)
        vinculo.updated_by = usuario_id
        vinculo.updated_at = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(vinculo)
        return vinculo

    async def inativar(self, vinculo_id: uuid.UUID, usuario_id: uuid.UUID | None = None) -> None:
        """Inativa o vínculo preservando histórico."""
        vinculo = await self.obter(vinculo_id)
        vinculo.ativo = False
        if vinculo.data_fim is None:
            vinculo.data_fim = date.today()
        vinculo.updated_by = usuario_id
        vinculo.updated_at = datetime.now(timezone.utc)
        await self.session.commit()

    async def _validar_referencias(self, propriedade_id: uuid.UUID, imovel_rural_id: uuid.UUID) -> None:
        """Garante que propriedade e imóvel existem no tenant atual."""
        propriedade = await self._buscar_propriedade(propriedade_id)
        if not propriedade:
            raise EntityNotFoundError("Propriedade não encontrada no tenant atual.")

        imovel = await self._buscar_imovel(imovel_rural_id)
        if not imovel:
            raise EntityNotFoundError("Imóvel rural não encontrado no tenant atual.")

    async def _buscar_propriedade(self, propriedade_id: uuid.UUID) -> Propriedade | None:
        stmt = select(Propriedade).where(
            Propriedade.id == propriedade_id,
            Propriedade.tenant_id == self.tenant_id,
            Propriedade.ativo.is_(True),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def _buscar_imovel(self, imovel_rural_id: uuid.UUID) -> ImovelRural | None:
        stmt = select(ImovelRural).where(
            ImovelRural.id == imovel_rural_id,
            ImovelRural.tenant_id == self.tenant_id,
            ImovelRural.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    def _validar_campos_numericos(self, payload: dict) -> None:
        """Valida área e percentual do vínculo."""
        percentual = payload.get("percentual_vinculado")
        if percentual is not None and (percentual < 0 or percentual > 100):
            raise BusinessRuleError("percentual_vinculado deve estar entre 0 e 100.")

        area = payload.get("area_vinculada")
        if area is not None and area < 0:
            raise BusinessRuleError("area_vinculada não pode ser negativa.")

    def _validar_vigencia(self, data_inicio: date, data_fim: date | None) -> None:
        """Garante vigência cronológica coerente."""
        if data_fim is not None and data_fim < data_inicio:
            raise BusinessRuleError("data_fim deve ser maior ou igual a data_inicio.")

    def _validar_origem_documental(self, origem_documental: str) -> None:
        """Garante que a origem documental não esteja vazia."""
        if not origem_documental or not origem_documental.strip():
            raise BusinessRuleError("origem_documental é obrigatória.")

    async def _validar_principalidade(
        self,
        propriedade_id: uuid.UUID,
        data_inicio: date,
        data_fim: date | None,
        vinculo_principal: bool,
        ativo: bool,
        exclude_id: uuid.UUID | None = None,
    ) -> None:
        """Impede dois vínculos principais ativos sobrepostos na mesma propriedade."""
        if not vinculo_principal or not ativo:
            return

        stmt = select(PropriedadeImovel).where(
            PropriedadeImovel.tenant_id == self.tenant_id,
            PropriedadeImovel.propriedade_id == propriedade_id,
            PropriedadeImovel.ativo.is_(True),
            PropriedadeImovel.vinculo_principal.is_(True),
        )
        if exclude_id:
            stmt = stmt.where(PropriedadeImovel.id != exclude_id)

        result = await self.session.execute(stmt)
        for existente in result.scalars().all():
            if self._periodos_sobrepostos(existente.data_inicio, existente.data_fim, data_inicio, data_fim):
                raise BusinessRuleError("Já existe vínculo principal ativo sobreposto para esta propriedade.")

    @staticmethod
    def _periodos_sobrepostos(inicio_a: date, fim_a: date | None, inicio_b: date, fim_b: date | None) -> bool:
        """Determina sobreposição temporal entre dois vínculos."""
        fim_a_real = fim_a or date.max
        fim_b_real = fim_b or date.max
        return inicio_a <= fim_b_real and inicio_b <= fim_a_real
