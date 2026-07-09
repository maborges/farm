from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, text
import uuid
from decimal import Decimal
from typing import Optional

from core.base_service import BaseService
from core.models.unidade_produtiva import UnidadeProdutiva
from core.models.billing import AssinaturaTenant, PlanoAssinatura
from core.schemas.unidade_produtiva_input import UnidadeProdutivaCreate, UnidadeProdutivaUpdate
from core.exceptions import BusinessRuleError


class UnidadeProdutivaService(BaseService[UnidadeProdutiva]):
    """
    Serviço que gerencia o ciclo de vida das unidades produtivas do AgroSaaS.
    Herda do BaseService que assegura blindagem por tenant_id de forma automática.

    Responsabilidades extras (EXEC-37):
      - Auto-criação/localização de ImovelRural ao receber dados fundiários.
      - Auto-criação do vínculo canônico PropriedadeImovel.
      - Overlay de leitura: campos fundiários retornados sempre refletem a
        fonte oficial (ImovelRural) quando há vínculo ativo.
    """
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID | None = None):
        super().__init__(UnidadeProdutiva, session, tenant_id, user_id=user_id)

    # ------------------------------------------------------------------
    # Billing / limites
    # ------------------------------------------------------------------

    async def _check_limite_unidades(self) -> None:
        """Verifica se o tenant atingiu o limite de unidades produtivas do plano contratado.

        Raises:
            BusinessRuleError: quando o limite do plano for atingido.
        """
        stmt_plano = (
            select(PlanoAssinatura.max_fazendas)
            .join(AssinaturaTenant, AssinaturaTenant.plano_id == PlanoAssinatura.id)
            .where(
                AssinaturaTenant.tenant_id == self.tenant_id,
                AssinaturaTenant.status == "ATIVA",
            )
            .limit(1)
        )
        result = await self.session.execute(stmt_plano)
        max_unidades = result.scalar_one_or_none()

        if max_unidades is None or max_unidades == -1:
            return  # Sem plano ativo ou ilimitado

        stmt_count = select(func.count(UnidadeProdutiva.id)).where(
            UnidadeProdutiva.tenant_id == self.tenant_id,
            UnidadeProdutiva.ativo == True,
        )
        result_count = await self.session.execute(stmt_count)
        total = result_count.scalar_one()

        if total >= max_unidades:
            raise BusinessRuleError(
                f"Seu plano atingiu o limite de propriedades. Você tem {total} de {max_unidades} propriedade(s) ativas. "
                "Faça upgrade do plano para continuar."
            )

    # ------------------------------------------------------------------
    # CRUD principal
    # ------------------------------------------------------------------

    async def create_unidade_produtiva(self, dados: UnidadeProdutivaCreate) -> UnidadeProdutiva:
        """Cria uma nova Unidade Produtiva disparando sincronização fundiária.

        Args:
            dados: Schema validado de criação.

        Returns:
            UnidadeProdutiva: objeto criado e registrado na sessão.
        """
        await self._check_limite_unidades()
        unidade = await super().create(dados)
        await self._sincronizar_vinculo_fundiario(unidade, dados)
        return unidade

    async def update(self, id: uuid.UUID, dados: UnidadeProdutivaUpdate) -> UnidadeProdutiva:
        """Atualiza Unidade Produtiva disparando sincronização fundiária.

        Args:
            id: UUID da unidade.
            dados: Schema validado de atualização.

        Returns:
            UnidadeProdutiva: objeto atualizado.
        """
        unidade = await super().update(id, dados)
        await self._sincronizar_vinculo_fundiario(unidade, dados)
        return unidade

    async def hard_delete(self, id: uuid.UUID) -> None:
        """Deleta a Unidade Produtiva limpando dependências com RESTRICT.

        Como ImovelRural e PropriedadeImovel possuem constraints ondelete="RESTRICT",
        eles precisam ser removidos explicitamente antes da exclusão da unidade.
        """
        from imoveis.models.imovel import ImovelRural
        from core.cadastros.propriedade_imovel.models import PropriedadeImovel

        # Busca imóveis rurais atrelados a esta unidade produtiva
        stmt_imoveis = select(ImovelRural).where(ImovelRural.unidade_produtiva_id == id)
        imoveis = (await self.session.execute(stmt_imoveis)).scalars().all()

        for imovel in imoveis:
            # Remove vínculos de PropriedadeImovel
            stmt_vinculos = select(PropriedadeImovel).where(PropriedadeImovel.imovel_rural_id == imovel.id)
            vinculos = (await self.session.execute(stmt_vinculos)).scalars().all()
            for v in vinculos:
                await self.session.delete(v)

            # Remove o imóvel rural
            await self.session.delete(imovel)

        # Agora pode prosseguir com o hard_delete da classe base
        await super().hard_delete(id)

    async def get(self, id: uuid.UUID) -> Optional[UnidadeProdutiva]:
        """Retorna Unidade Produtiva aplicando overlay da fonte oficial fundiária.

        Quando há um ImovelRural vinculado via PropriedadeImovel, os campos
        CAR, NIRF, CCIR, SIGEF e Matrícula são sobrescritos com os dados da
        fonte oficial sem alterar o banco — apenas no objeto em memória.

        Args:
            id: UUID da unidade.

        Returns:
            UnidadeProdutiva ou None.
        """
        unidade = await super().get(id)
        if unidade is not None:
            await self._aplicar_overlay_territorial(unidade)
        return unidade

    # ------------------------------------------------------------------
    # Visão Territorial — Overlay de leitura (EXEC-37 § 8)
    # ------------------------------------------------------------------

    async def _aplicar_overlay_territorial(self, unidade: UnidadeProdutiva) -> None:
        """Sobrepõe campos fundiários com dados da fonte oficial (ImovelRural).

        Realiza o overlay sem escrever no banco: apenas substitui os atributos
        em memória do objeto para que a resposta reflita a fonte canônica.

        Args:
            unidade: Objeto UnidadeProdutiva já carregado da sessão.
        """
        from imoveis.models.imovel import ImovelRural
        from core.cadastros.propriedade_imovel.models import PropriedadeImovel
        from core.cadastros.propriedades.propriedade_models import ExploracaoRural

        # Resolve propriedade_id via ExploracaoRural
        stmt_expl = (
            select(ExploracaoRural.propriedade_id)
            .where(
                ExploracaoRural.unidade_produtiva_id == unidade.id,
                ExploracaoRural.tenant_id == self.tenant_id,
            )
            .order_by(ExploracaoRural.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt_expl)
        propriedade_id = result.scalar_one_or_none()

        if not propriedade_id:
            return

        # Busca imóvel rural vinculado ativamente
        stmt_imovel = (
            select(ImovelRural)
            .join(
                PropriedadeImovel,
                PropriedadeImovel.imovel_rural_id == ImovelRural.id,
            )
            .where(
                PropriedadeImovel.tenant_id == self.tenant_id,
                PropriedadeImovel.propriedade_id == propriedade_id,
                PropriedadeImovel.ativo.is_(True),
                PropriedadeImovel.vinculo_principal.is_(True),
                ImovelRural.deleted_at.is_(None),
            )
            .limit(1)
        )
        result_imovel = await self.session.execute(stmt_imovel)
        imovel: Optional[ImovelRural] = result_imovel.scalar_one_or_none()

        if not imovel:
            return

        # Aplica overlay em memória — fonte oficial prevalece
        if imovel.car_numero:
            unidade.codigo_car = imovel.car_numero
        if imovel.nirf:
            unidade.nirf = imovel.nirf
        if imovel.ccir_numero:
            unidade.ccir = imovel.ccir_numero
        if imovel.sigef_codigo:
            unidade.sigef_codigo = imovel.sigef_codigo
        if imovel.numero_matricula:
            unidade.numero_matricula = imovel.numero_matricula

    # ------------------------------------------------------------------
    # Sincronização Fundiária — Auto-criação (EXEC-37 § 3, 4, 5)
    # ------------------------------------------------------------------

    async def _sincronizar_vinculo_fundiario(self, unidade: UnidadeProdutiva, dados) -> None:
        """Orquestra a criação/localização do ImovelRural e do PropriedadeImovel.

        Fluxo:
          1. Coleta identificadores fundiários do payload e do objeto persistido.
          2. Se nenhum identificador presente, encerra sem ação.
          3. Busca ImovelRural existente pelos identificadores (OR logic).
          4. Se não encontrar, cria ImovelRural via `criar_imovel_sem_validacao` (sem
             validações de formato/área que poderiam silenciar a criação).
          5. Busca ExploracaoRural para obter propriedade_id.
          6. Se existir, garante (idempotente) o PropriedadeImovel canônico.

        Args:
            unidade: Objeto UnidadeProdutiva já persistido na sessão.
            dados: Schema de criação ou atualização com os campos do payload.
        """
        from imoveis.models.imovel import ImovelRural, TipoImovel
        from imoveis.services.imovel_service import ImovelService
        from core.cadastros.propriedade_imovel.models import TipoVinculoPropriedadeImovel, PropriedadeImovel
        from core.cadastros.propriedades.propriedade_models import ExploracaoRural
        from sqlalchemy.exc import IntegrityError
        from datetime import date
        from loguru import logger

        # Garante contexto RLS para queries cross-module
        await self.session.execute(text(f"SET app.current_tenant_id = '{self.tenant_id}';"))

        # Coleta identificadores — payload prevalece, fallback no objeto
        car = getattr(dados, 'codigo_car', None) or getattr(unidade, 'codigo_car', None)
        nirf = getattr(dados, 'nirf', None) or getattr(unidade, 'nirf', None)
        ccir = getattr(dados, 'ccir', None) or getattr(unidade, 'ccir', None)
        sigef = getattr(dados, 'sigef_codigo', None) or getattr(unidade, 'sigef_codigo', None)
        matricula = getattr(dados, 'numero_matricula', None) or getattr(unidade, 'numero_matricula', None)

        if not any([car, nirf, ccir, sigef, matricula]):
            return

        if nirf:
            stmt_nirf = select(ImovelRural.id).where(
                ImovelRural.nirf == nirf,
                ImovelRural.deleted_at.is_(None),
            ).limit(1)
            nirf_existente = await self.session.execute(stmt_nirf)
            if nirf_existente.scalar_one_or_none():
                logger.warning(
                    "[AutoVinculo] NIRF já existente em ImovelRural; criação ignorada para unidade={}",
                    unidade.id,
                )
                return

        # ── Passo 1: Localizar ImovelRural existente ─────────────────────
        imovel: Optional[ImovelRural] = None
        condicoes = []
        if car:
            condicoes.append(ImovelRural.car_numero == car)
        if nirf:
            condicoes.append(ImovelRural.nirf == nirf)
        if ccir:
            condicoes.append(ImovelRural.ccir_numero == ccir)
        if sigef:
            condicoes.append(ImovelRural.sigef_codigo == sigef)
        if matricula:
            condicoes.append(ImovelRural.numero_matricula == matricula)

        if condicoes:
            stmt = select(ImovelRural).where(
                ImovelRural.tenant_id == self.tenant_id,
                ImovelRural.deleted_at.is_(None),
                or_(*condicoes),
            )
            result = await self.session.execute(stmt)
            imovel = result.scalar_one_or_none()

        # ── Passo 2: Criar ImovelRural se não encontrou ───────────────────
        # Usa criar_imovel_sem_validacao para evitar que validações de formato
        # de NIRF/CAR ou consistência de área silenciem a criação.
        if not imovel:
            imovel_svc = ImovelService(self.session)
            try:
                imovel = await imovel_svc.criar_imovel_sem_validacao(
                    tenant_id=self.tenant_id,
                    unidade_produtiva_id=unidade.id,
                    nome=unidade.nome,
                    municipio=unidade.municipio or "Não informado",
                    uf=unidade.uf or "NI",
                    nirf=nirf,
                    car_numero=car,
                    ccir_numero=ccir,
                    sigef_codigo=sigef,
                    numero_matricula=matricula,
                    created_by=self.user_id,
                )
                logger.info(
                    "[AutoVinculo] ImovelRural criado: id={} unidade={}",
                    imovel.id,
                    unidade.id,
                )
            except Exception as exc:
                logger.warning("[AutoVinculo] Falha ao criar ImovelRural: {} — continuando sem imóvel", exc)
                return

        # ── Passo 3: Garantir vínculo canônico PropriedadeImovel ──────────
        stmt_expl = (
            select(ExploracaoRural)
            .where(
                ExploracaoRural.unidade_produtiva_id == unidade.id,
                ExploracaoRural.tenant_id == self.tenant_id,
            )
            .order_by(ExploracaoRural.created_at.desc())
        )
        exploracao = (await self.session.execute(stmt_expl)).scalars().first()

        if not exploracao:
            # Sem vínculo com Propriedade Econômica — PropriedadeImovel não pode ser criado
            return

        propriedade_id = exploracao.propriedade_id

        # Idempotência: verifica vínculo ativo já existente
        stmt_vinculo = select(PropriedadeImovel).where(
            PropriedadeImovel.tenant_id == self.tenant_id,
            PropriedadeImovel.propriedade_id == propriedade_id,
            PropriedadeImovel.imovel_rural_id == imovel.id,
            PropriedadeImovel.ativo.is_(True),
        )
        vinculo_existente = (await self.session.execute(stmt_vinculo)).scalar_one_or_none()

        if vinculo_existente is not None:
            return  # Já existe — não duplicar

        # Verifica se já existe QUALQUER vínculo principal ativo para esta propriedade
        # (constraint uq_propriedade_imovel_principal_ativo impediria o INSERT)
        stmt_principal = select(PropriedadeImovel).where(
            PropriedadeImovel.tenant_id == self.tenant_id,
            PropriedadeImovel.propriedade_id == propriedade_id,
            PropriedadeImovel.vinculo_principal.is_(True),
            PropriedadeImovel.ativo.is_(True),
            PropriedadeImovel.data_fim.is_(None),
        )
        principal_existente = (await self.session.execute(stmt_principal)).scalar_one_or_none()
        usar_principal = principal_existente is None

        try:
            vinculo = PropriedadeImovel(
                tenant_id=self.tenant_id,
                propriedade_id=propriedade_id,
                imovel_rural_id=imovel.id,
                tipo_vinculo=TipoVinculoPropriedadeImovel.PROPRIEDADE_PRINCIPAL.value,
                origem_documental="Cadastro Automático (Unidade Produtiva)",
                data_inicio=date.today(),
                percentual_vinculado=Decimal('100.00'),
                vinculo_principal=usar_principal,
                ativo=True,
                created_by=self.user_id,
            )
            self.session.add(vinculo)
            await self.session.flush()
            logger.info(
                "[AutoVinculo] PropriedadeImovel criado: prop={} imovel={} principal={}",
                propriedade_id,
                imovel.id,
                usar_principal,
            )
        except IntegrityError as exc:
            # Constraint uq_propriedade_imovel_principal_ativo disparou
            # NÃO fazer rollback — o ImovelRural já está válido na sessão
            logger.warning(
                "[AutoVinculo] PropriedadeImovel não criado (constraint): {} — ImovelRural preservado",
                exc,
            )
            await self.session.rollback()
        except Exception as exc:
            logger.warning(
                "[AutoVinculo] Falha ao criar PropriedadeImovel: {} — ImovelRural preservado",
                exc,
            )
            await self.session.rollback()

    # ------------------------------------------------------------------
    # Backward compat aliases
    # ------------------------------------------------------------------

    async def create_fazenda(self, dados: UnidadeProdutivaCreate) -> UnidadeProdutiva:
        """Alias de compatibilidade para create_unidade_produtiva."""
        return await self.create_unidade_produtiva(dados)


# Backward compatibility alias
FazendaService = UnidadeProdutivaService
