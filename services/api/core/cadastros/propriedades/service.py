from decimal import Decimal
import uuid
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.base_service import BaseService
from core.exceptions import EntityNotFoundError, BusinessRuleError
from core.models.unidade_produtiva import UnidadeProdutiva
from core.models.billing import AssinaturaTenant, PlanoAssinatura
from .models import AreaRural, RegistroAmbiental, ValorPatrimonial, Infraestrutura, ArquivoGeo, StatusProcessamentoGeo, FILHOS_PERMITIDOS, TIPOS_AREA_PRODUTIVA, TIPOS_AREA_AMBIENTAL, TIPOS_INFRAESTRUTURA, TipoSolo, TipoIrrigacao


class AreaRuralService(BaseService[AreaRural]):
    """
    Serviço para cadastro de propriedades e áreas rurais.
    Herda tenant_id enforcement do BaseService.
    """

    async def listar(
        self,
        unidade_produtiva_id: uuid.UUID | None = None,
        tipo: str | None = None,
        parent_id: uuid.UUID | None = None,
        apenas_ativos: bool = True,
    ) -> list[AreaRural]:
        stmt = (
            select(AreaRural, TipoSolo.nome.label("tipo_solo_nome"), TipoIrrigacao.nome.label("tipo_irrigacao_nome"))
            .outerjoin(TipoSolo, AreaRural.tipo_solo_id == TipoSolo.id)
            .outerjoin(TipoIrrigacao, AreaRural.tipo_irrigacao_id == TipoIrrigacao.id)
            .where(AreaRural.tenant_id == self.tenant_id)
        )
        if apenas_ativos:
            stmt = stmt.where(AreaRural.ativo == True)
        if unidade_produtiva_id:
            stmt = stmt.where(AreaRural.unidade_produtiva_id == unidade_produtiva_id)
        if tipo:
            stmt = stmt.where(AreaRural.tipo == tipo)
        if parent_id is not None:
            stmt = stmt.where(AreaRural.parent_id == parent_id)

        stmt = stmt.order_by(func.lower(AreaRural.nome).asc(), AreaRural.created_at.asc())
        result = await self.session.execute(stmt)
        rows = result.all()

        areas = []
        for row in rows:
            area = row.AreaRural
            area.tipo_solo_nome = row.tipo_solo_nome
            area.tipo_irrigacao_nome = row.tipo_irrigacao_nome
            areas.append(area)
        return areas

    async def listar_raizes(self, unidade_produtiva_id: uuid.UUID | None = None) -> list[AreaRural]:
        """Retorna apenas áreas sem parent (raízes da hierarquia)."""
        stmt = (
            select(AreaRural, TipoSolo.nome.label("tipo_solo_nome"), TipoIrrigacao.nome.label("tipo_irrigacao_nome"))
            .outerjoin(TipoSolo, AreaRural.tipo_solo_id == TipoSolo.id)
            .outerjoin(TipoIrrigacao, AreaRural.tipo_irrigacao_id == TipoIrrigacao.id)
            .where(AreaRural.tenant_id == self.tenant_id, AreaRural.parent_id == None, AreaRural.ativo == True)
        )
        if unidade_produtiva_id:
            stmt = stmt.where(AreaRural.unidade_produtiva_id == unidade_produtiva_id)

        stmt = stmt.order_by(func.lower(AreaRural.nome).asc(), AreaRural.created_at.asc())
        result = await self.session.execute(stmt)
        rows = result.all()
        
        areas = []
        for row in rows:
            area = row.AreaRural
            area.tipo_solo_nome = row.tipo_solo_nome
            area.tipo_irrigacao_nome = row.tipo_irrigacao_nome
            areas.append(area)
        return areas

    async def obter_com_filhos(self, area_id: uuid.UUID) -> AreaRural:
        """Carrega a área com todos os filhos diretos."""
        stmt = (
            select(AreaRural)
            .where(AreaRural.id == area_id, AreaRural.tenant_id == self.tenant_id)
            .options(selectinload(AreaRural.filhos))
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        if not obj:
            raise EntityNotFoundError("Área rural não encontrada")
        return obj

    async def _validar_hierarquia(self, tipo: str, parent_id: uuid.UUID | None) -> None:
        """Valida que o tipo filho é permitido para o tipo pai."""
        if parent_id is None:
            tipos_raiz = FILHOS_PERMITIDOS.get(None, set())
            if tipo not in tipos_raiz:
                raise BusinessRuleError(
                    f"Tipo '{tipo}' não pode ser raiz. Tipos raiz válidos: {sorted(tipos_raiz)}"
                )
            return

        pai = await self.get_or_fail(parent_id)
        permitidos = FILHOS_PERMITIDOS.get(pai.tipo, set())
        if tipo not in permitidos:
            raise BusinessRuleError(
                f"Tipo '{tipo}' não é filho válido de '{pai.tipo}'. "
                f"Filhos permitidos: {sorted(permitidos) or 'nenhum (folha)'}"
            )

    async def criar_estrutura_base(self, unidade_produtiva_id: uuid.UUID) -> None:
        """Cria os nós raiz AREA_RURAL e INFRAESTRUTURA ao cadastrar nova UnidadeProdutiva."""
        from .models import TipoArea
        for tipo, nome in [
            (TipoArea.AREA_RURAL,     "Área Rural"),
            (TipoArea.INFRAESTRUTURA, "Infraestrutura"),
        ]:
            existe = await self.session.execute(
                select(AreaRural).where(
                    AreaRural.tenant_id == self.tenant_id,
                    AreaRural.unidade_produtiva_id == unidade_produtiva_id,
                    AreaRural.tipo == tipo,
                    AreaRural.parent_id == None,
                )
            )
            if not existe.scalar_one_or_none():
                self.session.add(AreaRural(
                    tenant_id=self.tenant_id,
                    unidade_produtiva_id=unidade_produtiva_id,
                    tipo=tipo,
                    nome=nome,
                    ativo=True,
                ))

    async def _validar_limite_hectares_area(
        self,
        unidade_produtiva_id: uuid.UUID,
        tipo: str,
        nova_area_ha: Decimal | float | None,
        excluir_area_id: uuid.UUID | None = None,
    ) -> None:
        """
        Valida se a soma dos hectares das áreas produtivas (ex.: TALHAO) não excede
        a área total da propriedade (UnidadeProdutiva) nem o limite_hectares do pacote contratado.

        Args:
            unidade_produtiva_id: ID da propriedade vinculada.
            tipo: Tipo da área rural sendo criada ou atualizada.
            nova_area_ha: Área em hectares da área rural.
            excluir_area_id: ID da área a excluir da soma em caso de atualização.

        Raises:
            BusinessRuleError: Se o somatório ultrapassar a área da propriedade ou o limite do pacote.
        """
        if tipo not in TIPOS_AREA_PRODUTIVA or not nova_area_ha or float(nova_area_ha) <= 0:
            return

        nova_area_dec = Decimal(str(nova_area_ha))

        # 1. Validar contra área total da propriedade (UnidadeProdutiva)
        up_stmt = select(
            UnidadeProdutiva.area_total_calculada_ha,
            UnidadeProdutiva.area_total_ha,
        ).where(
            UnidadeProdutiva.id == unidade_produtiva_id,
            UnidadeProdutiva.tenant_id == self.tenant_id,
        )
        up_row = (await self.session.execute(up_stmt)).first()
        if up_row:
            candidatos_area = [Decimal(str(v)) for v in up_row if v is not None and Decimal(str(v)) > 0]
            area_propriedade = max(candidatos_area) if candidatos_area else None
            if area_propriedade is not None and float(area_propriedade) > 0:
                soma_prop_stmt = select(
                    func.coalesce(
                        func.sum(
                            func.coalesce(
                                AreaRural.area_hectares_manual,
                                AreaRural.area_hectares,
                                0,
                            )
                        ),
                        0,
                    )
                ).where(
                    AreaRural.tenant_id == self.tenant_id,
                    AreaRural.unidade_produtiva_id == unidade_produtiva_id,
                    AreaRural.tipo == tipo,
                    AreaRural.ativo == True,
                )
                if excluir_area_id is not None:
                    soma_prop_stmt = soma_prop_stmt.where(AreaRural.id != excluir_area_id)

                soma_prop_atual = Decimal(str((await self.session.execute(soma_prop_stmt)).scalar_one() or 0))
                limite_prop_dec = Decimal(str(area_propriedade))
                if soma_prop_atual + nova_area_dec > limite_prop_dec:
                    disponivel_prop = max(Decimal("0"), limite_prop_dec - soma_prop_atual)
                    raise BusinessRuleError(
                        f"A soma das áreas de '{tipo}' ({soma_prop_atual + nova_area_dec:.2f} ha) "
                        f"ultrapassa a área total da propriedade ({limite_prop_dec:.2f} ha). "
                        f"Saldo disponível na propriedade: {disponivel_prop:.2f} ha."
                    )

        # 2. Validar contra limite_hectares do pacote contratado pelo tenant
        # Áreas de preservação ambiental (APP, RESERVA_LEGAL, AREA_AMBIENTAL) são isentas (fator 0.0x)
        # da franquia de hectares produtivos do pacote.
        if str(tipo).upper() in ("APP", "RESERVA_LEGAL", "AREA_AMBIENTAL"):
            return

        plano_stmt = (
            select(PlanoAssinatura.limite_hectares)
            .join(AssinaturaTenant, AssinaturaTenant.plano_id == PlanoAssinatura.id)
            .where(
                AssinaturaTenant.tenant_id == self.tenant_id,
                AssinaturaTenant.status.in_(["ATIVA", "TRIAL"]),
            )
            .limit(1)
        )
        limite_plano = (await self.session.execute(plano_stmt)).scalar_one_or_none()
        if limite_plano is not None and float(limite_plano) > 0:
            soma_tenant_stmt = select(
                func.coalesce(
                    func.sum(
                        func.coalesce(
                            AreaRural.area_hectares_manual,
                            AreaRural.area_hectares,
                            0,
                        )
                    ),
                    0,
                )
            ).where(
                AreaRural.tenant_id == self.tenant_id,
                AreaRural.tipo == tipo,
                AreaRural.ativo == True,
            )
            if excluir_area_id is not None:
                soma_tenant_stmt = soma_tenant_stmt.where(AreaRural.id != excluir_area_id)

            soma_tenant_atual = Decimal(str((await self.session.execute(soma_tenant_stmt)).scalar_one() or 0))
            limite_plano_dec = Decimal(str(limite_plano))
            if soma_tenant_atual + nova_area_dec > limite_plano_dec:
                disponivel_plano = max(Decimal("0"), limite_plano_dec - soma_tenant_atual)
                raise BusinessRuleError(
                    f"Limite de área do pacote atingido para '{tipo}' ({limite_plano_dec:.2f} ha). "
                    f"Área já utilizada: {soma_tenant_atual:.2f} ha. "
                    f"Disponível no pacote: {disponivel_plano:.2f} ha."
                )

    async def criar_area(self, data: dict) -> AreaRural:
        await self._validar_hierarquia(data["tipo"], data.get("parent_id"))
        area_efetiva = data.get("area_hectares_manual") or data.get("area_hectares")
        if data.get("unidade_produtiva_id") and area_efetiva:
            await self._validar_limite_hectares_area(
                unidade_produtiva_id=data["unidade_produtiva_id"],
                tipo=data["tipo"],
                nova_area_ha=area_efetiva,
            )
        area = AreaRural(tenant_id=self.tenant_id, **data)
        self.session.add(area)
        await self.session.commit()
        await self.session.refresh(area)
        return area

    async def sumario_areas(self, unidade_produtiva_id: uuid.UUID) -> dict:
        """Agrega hectares por categoria para a unidade produtiva."""
        stmt = select(AreaRural).where(
            AreaRural.tenant_id == self.tenant_id,
            AreaRural.unidade_produtiva_id == unidade_produtiva_id,
            AreaRural.ativo == True,
        )
        result = await self.session.execute(stmt)
        areas = result.scalars().all()

        def ha(area: AreaRural) -> float:
            v = area.area_hectares_manual or area.area_hectares
            return float(v) if v else 0.0

        total = sum(ha(a) for a in areas if a.parent_id is None or a.tipo in TIPOS_AREA_PRODUTIVA | TIPOS_AREA_AMBIENTAL | TIPOS_INFRAESTRUTURA)
        produtiva = sum(ha(a) for a in areas if a.tipo in TIPOS_AREA_PRODUTIVA)
        ambiental = sum(ha(a) for a in areas if a.tipo in TIPOS_AREA_AMBIENTAL)
        infraestrutura = sum(ha(a) for a in areas if a.tipo in TIPOS_INFRAESTRUTURA)

        return {
            "area_total_ha": total,
            "area_produtiva_ha": produtiva,
            "area_ambiental_ha": ambiental,
            "area_infraestrutura_ha": infraestrutura,
        }

    async def atualizar_area(self, area_id: uuid.UUID, data: dict) -> AreaRural:
        obj = await self.get_or_fail(area_id)
        novo_tipo = data.get("tipo", obj.tipo)
        nova_up_id = data.get("unidade_produtiva_id", obj.unidade_produtiva_id)
        nova_area_manual = data.get("area_hectares_manual", obj.area_hectares_manual)
        nova_area_calc = data.get("area_hectares", obj.area_hectares)
        area_efetiva = nova_area_manual if nova_area_manual is not None else nova_area_calc
        if (
            "area_hectares_manual" in data
            or "area_hectares" in data
            or "tipo" in data
            or "unidade_produtiva_id" in data
        ) and nova_up_id and area_efetiva:
            await self._validar_limite_hectares_area(
                unidade_produtiva_id=nova_up_id,
                tipo=novo_tipo,
                nova_area_ha=area_efetiva,
                excluir_area_id=area_id,
            )
        for k, v in data.items():
            setattr(obj, k, v)
        await self.session.commit()
        await self.session.refresh(obj)
        return obj

    async def soft_delete(self, area_id: uuid.UUID) -> None:
        obj = await self.get_or_fail(area_id)
        # Verifica se há filhos ativos
        stmt = select(AreaRural).where(
            AreaRural.parent_id == area_id, AreaRural.ativo == True
        )
        result = await self.session.execute(stmt)
        if result.scalar_one_or_none():
            raise BusinessRuleError("Não é possível inativar uma área que possui subáreas ativas")
        obj.ativo = False
        await self.session.commit()

    async def listar_tipos_solo(self, apenas_ativos: bool = True) -> list[TipoSolo]:
        stmt = select(TipoSolo)
        if apenas_ativos:
            stmt = stmt.where(TipoSolo.ativo == True)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def listar_tipos_irrigacao(self, apenas_ativos: bool = True) -> list[TipoIrrigacao]:
        stmt = select(TipoIrrigacao)
        if apenas_ativos:
            stmt = stmt.where(TipoIrrigacao.ativo == True)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class RegistroAmbientalService:
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        self.session = session
        self.tenant_id = tenant_id

    async def _verificar_area(self, area_id: uuid.UUID) -> AreaRural:
        result = await self.session.execute(
            select(AreaRural).where(AreaRural.id == area_id, AreaRural.tenant_id == self.tenant_id)
        )
        obj = result.scalar_one_or_none()
        if not obj:
            raise EntityNotFoundError("Área rural não encontrada")
        return obj

    async def listar(self, area_id: uuid.UUID) -> list[RegistroAmbiental]:
        await self._verificar_area(area_id)
        result = await self.session.execute(
            select(RegistroAmbiental).where(RegistroAmbiental.area_id == area_id, RegistroAmbiental.ativo == True)
        )
        return list(result.scalars().all())

    async def criar(self, data: dict) -> RegistroAmbiental:
        await self._verificar_area(data["area_id"])
        obj = RegistroAmbiental(**data)
        self.session.add(obj)
        await self.session.commit()
        await self.session.refresh(obj)
        return obj

    async def atualizar(self, registro_id: uuid.UUID, area_id: uuid.UUID, data: dict) -> RegistroAmbiental:
        await self._verificar_area(area_id)
        result = await self.session.execute(
            select(RegistroAmbiental).where(RegistroAmbiental.id == registro_id, RegistroAmbiental.area_id == area_id)
        )
        obj = result.scalar_one_or_none()
        if not obj:
            raise EntityNotFoundError("Registro ambiental não encontrado")
        for k, v in data.items():
            setattr(obj, k, v)
        await self.session.commit()
        await self.session.refresh(obj)
        return obj

    async def remover(self, registro_id: uuid.UUID, area_id: uuid.UUID) -> None:
        await self._verificar_area(area_id)
        result = await self.session.execute(
            select(RegistroAmbiental).where(RegistroAmbiental.id == registro_id, RegistroAmbiental.area_id == area_id)
        )
        obj = result.scalar_one_or_none()
        if not obj:
            raise EntityNotFoundError("Registro ambiental não encontrado")
        obj.ativo = False
        await self.session.commit()


class InfraestruturaService:
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        self.session = session
        self.tenant_id = tenant_id

    async def _verificar_area(self, area_id: uuid.UUID) -> AreaRural:
        result = await self.session.execute(
            select(AreaRural).where(AreaRural.id == area_id, AreaRural.tenant_id == self.tenant_id)
        )
        obj = result.scalar_one_or_none()
        if not obj:
            raise EntityNotFoundError("Área rural não encontrada")
        return obj

    async def listar(self, area_rural_id: uuid.UUID, apenas_ativos: bool = True) -> list[Infraestrutura]:
        await self._verificar_area(area_rural_id)
        stmt = select(Infraestrutura).where(Infraestrutura.area_rural_id == area_rural_id)
        if apenas_ativos:
            stmt = stmt.where(Infraestrutura.is_active == True)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def criar(self, data: dict) -> Infraestrutura:
        await self._verificar_area(data["area_rural_id"])
        obj = Infraestrutura(tenant_id=self.tenant_id, **data)
        self.session.add(obj)
        await self.session.commit()
        await self.session.refresh(obj)
        return obj

    async def atualizar(self, infra_id: uuid.UUID, area_rural_id: uuid.UUID, data: dict) -> Infraestrutura:
        await self._verificar_area(area_rural_id)
        result = await self.session.execute(
            select(Infraestrutura).where(
                Infraestrutura.id == infra_id,
                Infraestrutura.area_rural_id == area_rural_id,
                Infraestrutura.tenant_id == self.tenant_id,
            )
        )
        obj = result.scalar_one_or_none()
        if not obj:
            raise EntityNotFoundError("Infraestrutura não encontrada")
        for k, v in data.items():
            setattr(obj, k, v)
        await self.session.commit()
        await self.session.refresh(obj)
        return obj

    async def remover(self, infra_id: uuid.UUID, area_rural_id: uuid.UUID) -> None:
        await self._verificar_area(area_rural_id)
        result = await self.session.execute(
            select(Infraestrutura).where(
                Infraestrutura.id == infra_id,
                Infraestrutura.area_rural_id == area_rural_id,
                Infraestrutura.tenant_id == self.tenant_id,
            )
        )
        obj = result.scalar_one_or_none()
        if not obj:
            raise EntityNotFoundError("Infraestrutura não encontrada")
        obj.is_active = False
        await self.session.commit()


class ArquivoGeoService:
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        self.session = session
        self.tenant_id = tenant_id

    async def _verificar_area(self, area_id: uuid.UUID) -> AreaRural:
        result = await self.session.execute(
            select(AreaRural).where(AreaRural.id == area_id, AreaRural.tenant_id == self.tenant_id)
        )
        obj = result.scalar_one_or_none()
        if not obj:
            raise EntityNotFoundError("Área rural não encontrada")
        return obj

    async def listar(self, area_rural_id: uuid.UUID) -> list[ArquivoGeo]:
        await self._verificar_area(area_rural_id)
        result = await self.session.execute(
            select(ArquivoGeo)
            .where(ArquivoGeo.area_rural_id == area_rural_id, ArquivoGeo.tenant_id == self.tenant_id)
            .order_by(ArquivoGeo.created_at.desc())
        )
        return list(result.scalars().all())

    async def criar(self, data: dict) -> ArquivoGeo:
        obj = ArquivoGeo(tenant_id=self.tenant_id, **data)
        self.session.add(obj)
        await self.session.commit()
        await self.session.refresh(obj)
        return obj

    async def marcar_processado(
        self, arquivo_id: uuid.UUID, poligonos: int, area_ha: float
    ) -> ArquivoGeo:
        result = await self.session.execute(
            select(ArquivoGeo).where(
                ArquivoGeo.id == arquivo_id, ArquivoGeo.tenant_id == self.tenant_id
            )
        )
        obj = result.scalar_one_or_none()
        if not obj:
            raise EntityNotFoundError("Arquivo geo não encontrado")
        obj.status = StatusProcessamentoGeo.PROCESSADO
        obj.poligonos_extraidos = poligonos
        obj.area_ha_extraida = area_ha
        await self.session.commit()
        await self.session.refresh(obj)
        return obj

    async def marcar_erro(self, arquivo_id: uuid.UUID, erro: str) -> ArquivoGeo:
        result = await self.session.execute(
            select(ArquivoGeo).where(
                ArquivoGeo.id == arquivo_id, ArquivoGeo.tenant_id == self.tenant_id
            )
        )
        obj = result.scalar_one_or_none()
        if not obj:
            raise EntityNotFoundError("Arquivo geo não encontrado")
        obj.status = StatusProcessamentoGeo.ERRO
        obj.erro_msg = erro
        await self.session.commit()
        await self.session.refresh(obj)
        return obj


class ValorPatrimonialService:
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        self.session = session
        self.tenant_id = tenant_id

    async def _verificar_area(self, area_id: uuid.UUID) -> AreaRural:
        result = await self.session.execute(
            select(AreaRural).where(AreaRural.id == area_id, AreaRural.tenant_id == self.tenant_id)
        )
        obj = result.scalar_one_or_none()
        if not obj:
            raise EntityNotFoundError("Área rural não encontrada")
        return obj

    async def listar(self, area_id: uuid.UUID) -> list[ValorPatrimonial]:
        await self._verificar_area(area_id)
        result = await self.session.execute(
            select(ValorPatrimonial)
            .where(ValorPatrimonial.area_id == area_id)
            .order_by(ValorPatrimonial.data_avaliacao.desc())
        )
        return list(result.scalars().all())

    async def criar(self, data: dict) -> ValorPatrimonial:
        await self._verificar_area(data["area_id"])
        obj = ValorPatrimonial(**data)
        self.session.add(obj)
        await self.session.commit()
        await self.session.refresh(obj)
        return obj

    async def atualizar(self, valor_id: uuid.UUID, area_id: uuid.UUID, data: dict) -> ValorPatrimonial:
        await self._verificar_area(area_id)
        result = await self.session.execute(
            select(ValorPatrimonial).where(ValorPatrimonial.id == valor_id, ValorPatrimonial.area_id == area_id)
        )
        obj = result.scalar_one_or_none()
        if not obj:
            raise EntityNotFoundError("Avaliação patrimonial não encontrada")
        for k, v in data.items():
            setattr(obj, k, v)
        await self.session.commit()
        await self.session.refresh(obj)
        return obj

    async def remover(self, valor_id: uuid.UUID, area_id: uuid.UUID) -> None:
        await self._verificar_area(area_id)
        result = await self.session.execute(
            select(ValorPatrimonial).where(ValorPatrimonial.id == valor_id, ValorPatrimonial.area_id == area_id)
        )
        obj = result.scalar_one_or_none()
        if not obj:
            raise EntityNotFoundError("Avaliação patrimonial não encontrada")
        await self.session.delete(obj)
        await self.session.commit()
