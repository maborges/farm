"""
Service para gerenciamento de mudanças de plano (upgrade/downgrade).

Implementa toda a lógica de negócio para solicitação, aprovação e aplicação
de mudanças de plano com integração ao gateway de pagamento.
"""
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional
from uuid import UUID
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from core.models.plan_changes import MudancaPlano, HistoricoBloqueio
from core.models.billing import PlanoAssinatura, AssinaturaTenant, Fatura
from core.models.unidade_produtiva import UnidadeProdutiva
from core.models.tenant import Tenant
from core.models.auth import Usuario
from core.base_service import BaseService
from core.exceptions import BusinessRuleError, EntityNotFoundError
from core.services.plan_pricing_service import PlanoPricingService


class MudancaPlanoService(BaseService[MudancaPlano]):
    """Service para gerenciar mudanças de plano."""

    def __init__(self, session: AsyncSession, tenant_id: Optional[UUID] = None):
        super().__init__(MudancaPlano, session, tenant_id)
        self.pricing_service = PlanoPricingService(session)

    async def simular_mudanca(
        self,
        plano_destino_id: UUID,
        usuarios_destino: int,
        assinatura_id: Optional[UUID] = None,
        usuario_solicitante_id: Optional[UUID] = None,
        ciclo_destino: Optional[str] = None,
    ) -> dict:
        """
        Simula mudança de plano e/ou quantidade de acessos simultâneos sem criar registro.

        Compõe o valor atual (pacote + acessos extras) e o valor novo (novo pacote por
        tamanho de propriedade + novos acessos extras), apurando a diferença da mensalidade
        ou anuidade e o valor proporcional (pro-rata) do ciclo corrente.

        Args:
            plano_destino_id: Plano desejado
            usuarios_destino: Quantidade de acessos simultâneos desejada
            assinatura_id: ID da assinatura (se tenant tem múltiplas)
            usuario_solicitante_id: ID do usuário solicitante (para validação)
            ciclo_destino: Ciclo desejado (MENSAL ou ANUAL). Se omitido, usa o da assinatura.

        Returns:
            dict com simulação completa

        Raises:
            EntityNotFoundError: Se assinatura não existe
            BusinessRuleError: Se mudança não é permitida ou área atual excede o pacote destino
        """
        # Buscar assinatura atual
        assinatura = await self._obter_assinatura(assinatura_id)

        # Buscar planos
        plano_atual = await self._obter_plano(assinatura.plano_id)
        plano_novo = await self._obter_plano(plano_destino_id)

        # Validar se a área total das propriedades ativas cabe no limite_hectares do plano destino
        await self._validar_compatibilidade_hectares_destino(plano_novo)

        usuarios_origem = assinatura.usuarios_contratados or plano_atual.limite_usuarios_minimo or 1
        ciclo_efetivo = (ciclo_destino or assinatura.ciclo_pagamento or "MENSAL").upper()

        # Calcular valores compostos (Pacote Base + Faixas de Acessos Simultâneos Extras)
        calculo = await self.pricing_service.calcular_diferenca_planos(
            plano_origem_id=assinatura.plano_id,
            usuarios_origem=usuarios_origem,
            plano_destino_id=plano_destino_id,
            usuarios_destino=usuarios_destino,
            ciclo=ciclo_efetivo
        )

        diferenca_composta = Decimal(str(calculo["diferenca"]))

        # Determinar tipo de mudança considerando pacote, acessos e diferença financeira composta
        tipo_mudanca = self._determinar_tipo_mudanca(
            assinatura.plano_id,
            usuarios_origem,
            plano_destino_id,
            usuarios_destino,
            diferenca_composta
        )

        ja_pagou = await self._assinatura_ja_paga(assinatura)

        # Calcular proporcional (para upgrade) somente quando a assinatura já possui pagamento prévio
        dias_ciclo = 365 if ciclo_efetivo == "ANUAL" else 30
        dias_restantes = 0
        valor_proporcional = Decimal("0.00")

        if tipo_mudanca.startswith("UPGRADE") and diferenca_composta > 0 and ja_pagou:
            if assinatura.data_proxima_renovacao:
                dias_restantes = (assinatura.data_proxima_renovacao.date() - datetime.now(timezone.utc).date()).days

            if 0 < dias_restantes < dias_ciclo:
                valor_proporcional = ((diferenca_composta * Decimal(str(dias_restantes))) / Decimal(str(dias_ciclo))).quantize(Decimal("0.01"))
            else:
                dias_restantes = dias_ciclo
                valor_proporcional = diferenca_composta.quantize(Decimal("0.01"))

        requer_pagamento = bool(ja_pagou and tipo_mudanca.startswith("UPGRADE") and valor_proporcional > 0)

        # Mensagem explicativa
        mensagem = self._gerar_mensagem_simulacao(
            tipo_mudanca,
            plano_atual.nome,
            plano_novo.nome,
            usuarios_origem,
            usuarios_destino,
            valor_proporcional,
            dias_restantes,
            ja_pagou=ja_pagou,
            valor_novo_total=Decimal(str(calculo["valor_novo"])),
        )

        return {
            "tipo_mudanca": tipo_mudanca,
            "ciclo": ciclo_efetivo,
            "plano_atual": {
                "id": str(plano_atual.id),
                "nome": plano_atual.nome,
                "modulos": plano_atual.modulos_inclusos,
                "limite_hectares": float(plano_atual.limite_hectares) if plano_atual.limite_hectares is not None else None,
                "usuarios_inclusos": plano_atual.limite_usuarios_minimo or 1,
            },
            "plano_novo": {
                "id": str(plano_novo.id),
                "nome": plano_novo.nome,
                "modulos": plano_novo.modulos_inclusos,
                "limite_hectares": float(plano_novo.limite_hectares) if plano_novo.limite_hectares is not None else None,
                "usuarios_inclusos": plano_novo.limite_usuarios_minimo or 1,
            },
            "usuarios_atual": usuarios_origem,
            "usuarios_novo": usuarios_destino,
            "valor_atual_mensal": float(calculo["valor_atual"]),
            "valor_novo_mensal": float(calculo["valor_novo"]),
            "diferenca_mensal": float(diferenca_composta),
            "detalhes_atual": calculo.get("detalhes_atual", []),
            "detalhes_novo": calculo.get("detalhes_novo", []),
            "dias_restantes_ciclo": dias_restantes,
            "valor_proporcional": float(valor_proporcional),
            "data_proxima_cobranca": assinatura.data_proxima_renovacao or (datetime.now(timezone.utc) + timedelta(days=dias_ciclo)),
            "requer_pagamento": requer_pagamento,
            "mensagem": mensagem
        }

    async def solicitar_mudanca(
        self,
        plano_destino_id: UUID,
        usuarios_destino: int,
        usuario_solicitante_id: UUID,
        assinatura_id: Optional[UUID] = None,
        ciclo_destino: Optional[str] = None,
    ) -> MudancaPlano:
        """
        Cria solicitação de mudança de plano e/ou quantidade de acessos simultâneos.

        Se o assinante está em TRIAL ou sem pagamento prévio, cancela cobranças em aberto
        anteriores, gera nova fatura com o valor do novo plano e aplica a mudança na hora.
        Caso já tenha pago, cobra a diferença proporcional (upgrade) ou agenda (downgrade).

        Args:
            plano_destino_id: Plano desejado
            usuarios_destino: Quantidade de acessos simultâneos
            usuario_solicitante_id: Quem está solicitando
            assinatura_id: ID da assinatura
            ciclo_destino: Ciclo desejado (MENSAL ou ANUAL)

        Returns:
            MudancaPlano criada

        Raises:
            BusinessRuleError: Se mudança não permitida
        """
        assinatura = await self._obter_assinatura(assinatura_id)
        ja_pagou = await self._assinatura_ja_paga(assinatura)

        if ja_pagou:
            # Validar que não há mudança pendente apenas no ciclo pago
            await self._validar_mudanca_pendente(assinatura_id)

        # Simular para obter valores compostos
        simulacao = await self.simular_mudanca(
            plano_destino_id,
            usuarios_destino,
            assinatura_id,
            usuario_solicitante_id,
            ciclo_destino=ciclo_destino,
        )

        # Calcular valores
        dias_restantes = simulacao["dias_restantes_ciclo"]
        valor_proporcional = Decimal(str(simulacao["valor_proporcional"]))
        valor_diferenca = Decimal(str(simulacao["diferenca_mensal"]))
        valor_novo_total = Decimal(str(simulacao["valor_novo_mensal"]))

        # Criar registro de mudança
        mudanca = MudancaPlano(
            tenant_id=self.tenant_id,
            assinatura_id=assinatura.id,
            plano_origem_id=assinatura.plano_id,
            usuarios_origem=assinatura.usuarios_contratados or 1,
            plano_destino_id=plano_destino_id,
            usuarios_destino=usuarios_destino,
            tipo_mudanca=simulacao["tipo_mudanca"],
            valor_calculado=valor_diferenca,
            valor_proporcional=valor_proporcional,
            dias_restantes_ciclo=dias_restantes if dias_restantes > 0 else None,
            solicitado_por_usuario_id=usuario_solicitante_id,
            status="pendente_pagamento"
        )

        if not ja_pagou:
            # Assinante em TRIAL ou sem pagamento confirmado:
            # 1) Cancela mudanças pendentes anteriores para não bloquear nova troca
            mudancas_antigas = (
                await self.session.execute(
                    select(MudancaPlano).where(
                        MudancaPlano.assinatura_id == assinatura.id,
                        MudancaPlano.status.in_(["pendente_pagamento", "agendado"]),
                    )
                )
            ).scalars().all()
            for mudanca_antiga in mudancas_antigas:
                mudanca_antiga.status = "cancelado"
                mudanca_antiga.observacoes = "Substituída automaticamente por nova alteração antes do pagamento"

            # 2) Cancela cobrança anterior em aberto e gera nova fatura no valor do novo plano
            faturas_abertas = (
                await self.session.execute(
                    select(Fatura)
                    .where(
                        Fatura.assinatura_id == assinatura.id,
                        Fatura.status == "ABERTA",
                    )
                    .order_by(Fatura.data_vencimento.desc())
                )
            ).scalars().all()

            vencimento_novo = None
            for fatura_antiga in faturas_abertas:
                if vencimento_novo is None and fatura_antiga.data_vencimento is not None:
                    vencimento_novo = fatura_antiga.data_vencimento
                fatura_antiga.status = "CANCELADA"

            if vencimento_novo is None:
                vencimento_novo = assinatura.data_proxima_renovacao or (datetime.now(timezone.utc) + timedelta(days=3))

            if valor_novo_total > 0:
                nova_fatura = Fatura(
                    tenant_id=self.tenant_id,
                    assinatura_id=assinatura.id,
                    valor=valor_novo_total,
                    data_vencimento=vencimento_novo,
                    status="ABERTA",
                )
                self.session.add(nova_fatura)

            # 3) Aplica o novo pacote/acessos imediatamente sem exigir pagamento de diferença
            assinatura.plano_id = plano_destino_id
            assinatura.usuarios_contratados = usuarios_destino
            if simulacao.get("ciclo"):
                assinatura.ciclo_pagamento = simulacao["ciclo"]
            mudanca.valor_proporcional = Decimal("0.00")
            mudanca.dias_restantes_ciclo = None
            mudanca.status = "aplicado"
            mudanca.aplicado_em = datetime.now(timezone.utc)

        elif simulacao["tipo_mudanca"].startswith("DOWNGRADE"):
            mudanca.agendado_para = assinatura.data_proxima_renovacao
            mudanca.status = "agendado"
            logger.info(
                f"Downgrade agendado para {assinatura.data_proxima_renovacao} - "
                f"Tenant {self.tenant_id}"
            )
        else:
            # Assinatura já paga solicitando UPGRADE: gera fatura complementar com a diferença pro-rata
            valor_fatura_complementar = valor_proporcional if valor_proporcional > 0 else valor_diferenca
            if valor_fatura_complementar > 0:
                nova_fatura = Fatura(
                    tenant_id=self.tenant_id,
                    assinatura_id=assinatura.id,
                    valor=valor_fatura_complementar,
                    data_vencimento=datetime.now(timezone.utc) + timedelta(days=3),
                    status="ABERTA",
                )
                self.session.add(nova_fatura)

        self.session.add(mudanca)
        await self.session.commit()
        await self.session.refresh(mudanca)

        logger.info(
            f"Mudança de plano solicitada: {simulacao['tipo_mudanca']} - "
            f"Tenant {self.tenant_id}, Mudança ID {mudanca.id}"
        )

        return mudanca

    async def gerar_checkout_stripe(
        self,
        mudanca: MudancaPlano,
        email_responsavel: Optional[str] = None,
    ) -> Optional[str]:
        """Gera URL de Checkout Stripe para uma mudança de plano pendente de pagamento.

        Args:
            mudanca: Registro de MudancaPlano recém-criado ou pendente.
            email_responsavel: E-mail opcional para pré-preencher o checkout.

        Returns:
            URL do checkout Stripe ou None se não houver valor a cobrar.
        """
        from core.models.tenant import Tenant
        from core.services.stripe_service import StripeService

        assinatura = await self._obter_assinatura(mudanca.assinatura_id)
        plano_destino = await self._obter_plano(mudanca.plano_destino_id)
        tenant = await self.session.get(Tenant, assinatura.tenant_id)
        email = email_responsavel or (tenant.email_responsavel if tenant else None) or "financeiro@deepfarms.com.br"

        fatura_aberta = (
            await self.session.execute(
                select(Fatura)
                .where(Fatura.assinatura_id == assinatura.id, Fatura.status == "ABERTA")
                .order_by(Fatura.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

        stripe_svc = StripeService()
        if assinatura.stripe_subscription_id:
            valor_cobrar = fatura_aberta.valor if fatura_aberta else mudanca.valor_proporcional
            if Decimal(str(valor_cobrar or 0)) <= 0:
                return None
            url = await stripe_svc.criar_checkout_mudanca_prorata(
                tenant_id=str(assinatura.tenant_id),
                assinatura_id=str(assinatura.id),
                mudanca_plano_id=str(mudanca.id),
                plano_destino_id=str(plano_destino.id),
                nome_plano_destino=plano_destino.nome,
                valor_reais=float(valor_cobrar),
                email=email,
                fatura_id=str(fatura_aberta.id) if fatura_aberta else None,
            )
        else:
            ciclo = getattr(assinatura, "ciclo_pagamento", "MENSAL") or "MENSAL"
            _, detalhamento = await self.pricing_service.calcular_preco_total(
                plano_id=plano_destino.id,
                quantidade_usuarios=mudanca.usuarios_destino,
                ciclo=ciclo,
            )
            extensoes = list((tenant.branding or {}).get("extensoes_contratadas") or []) if tenant else []
            url = await stripe_svc.criar_checkout_assinatura(
                tenant_id=str(assinatura.tenant_id),
                assinatura_id=str(assinatura.id),
                email=email,
                plano_id=str(plano_destino.id),
                ciclo=ciclo,
                detalhamento_preco=detalhamento,
                nome_plano=plano_destino.nome,
                usuarios_contratados=mudanca.usuarios_destino,
                extensoes_contratadas=extensoes,
            )

        mudanca.url_pagamento = url
        await self.session.commit()
        await self.session.refresh(mudanca)
        return url

    async def aprovar_manualmente(
        self,
        mudanca_id: UUID,
        admin_id: UUID,
        motivo: str,
        dias_tolerancia: int = 5
    ) -> MudancaPlano:
        """
        Aprova mudança manualmente (backoffice).

        Libera acesso sem pagamento, mas define prazo para regularização.
        Após o prazo, tenant é bloqueado automaticamente.

        Args:
            mudanca_id: ID da mudança
            admin_id: ID do admin aprovando
            motivo: Justificativa da liberação
            dias_tolerancia: Dias para regularizar pagamento

        Returns:
            MudancaPlano atualizada
        """
        # Buscar mudança (sem filtro de tenant, é operação de backoffice)
        stmt = select(MudancaPlano).where(MudancaPlano.id == mudanca_id)
        result = await self.session.execute(stmt)
        mudanca = result.scalar_one_or_none()

        if not mudanca:
            raise EntityNotFoundError("Mudança de plano não encontrada.")

        if mudanca.status not in ["pendente_pagamento", "agendado"]:
            raise BusinessRuleError(
                f"Mudança está em status {mudanca.status}, não pode ser aprovada manualmente"
            )

        # Atualizar mudança
        mudanca.status = "liberado_manualmente"
        mudanca.liberado_manualmente = True
        mudanca.aprovado_por_admin_id = admin_id
        mudanca.motivo_liberacao_manual = motivo
        mudanca.data_limite_pagamento = datetime.now(timezone.utc) + timedelta(days=dias_tolerancia)

        await self.session.commit()
        await self.session.refresh(mudanca)

        # Aplicar mudança imediatamente
        await self._aplicar_mudanca(mudanca)

        logger.warning(
            f"Mudança {mudanca_id} aprovada manualmente por admin {admin_id}. "
            f"Prazo para pagamento: {mudanca.data_limite_pagamento}"
        )

        return mudanca

    async def aplicar_mudancas_agendadas(self) -> list[MudancaPlano]:
        """
        Aplica mudanças agendadas cuja data chegou.

        Chamado por job diário para aplicar downgrades agendados.

        Returns:
            Lista de mudanças aplicadas
        """
        # Buscar mudanças agendadas com data <= hoje
        stmt = (
            select(MudancaPlano)
            .where(MudancaPlano.status == "agendado")
            .where(MudancaPlano.agendado_para <= datetime.now(timezone.utc))
        )
        result = await self.session.execute(stmt)
        mudancas = result.scalars().all()

        aplicadas = []

        for mudanca in mudancas:
            try:
                await self._aplicar_mudanca(mudanca)
                aplicadas.append(mudanca)
                logger.info(f"Mudança agendada {mudanca.id} aplicada automaticamente")
            except Exception as e:
                logger.error(f"Erro ao aplicar mudança {mudanca.id}: {e}")

        await self.session.commit()

        return aplicadas

    async def verificar_inadimplencias(self) -> list[UUID]:
        """
        Verifica mudanças liberadas manualmente sem pagamento no prazo.

        Bloqueia tenants inadimplentes.

        Returns:
            Lista de tenant_ids bloqueados
        """
        # Buscar mudanças liberadas manualmente com prazo vencido
        stmt = (
            select(MudancaPlano)
            .where(MudancaPlano.status == "liberado_manualmente")
            .where(MudancaPlano.data_limite_pagamento < datetime.now(timezone.utc))
        )
        result = await self.session.execute(stmt)
        mudancas_vencidas = result.scalars().all()

        tenants_bloqueados = []

        for mudanca in mudancas_vencidas:
            try:
                await self._bloquear_por_inadimplencia(mudanca)
                tenants_bloqueados.append(mudanca.tenant_id)
                logger.warning(
                    f"Tenant {mudanca.tenant_id} bloqueado por inadimplência - "
                    f"Mudança {mudanca.id}"
                )
            except Exception as e:
                logger.error(f"Erro ao bloquear tenant {mudanca.tenant_id}: {e}")

        await self.session.commit()

        return tenants_bloqueados

    async def cancelar_mudanca(
        self,
        mudanca_id: UUID,
        usuario_id: UUID,
        motivo: Optional[str] = None
    ) -> MudancaPlano:
        """
        Cancela mudança pendente.

        Apenas mudanças em status pendente/agendado podem ser canceladas.
        """
        mudanca = await self.get_or_fail(mudanca_id)

        if mudanca.status not in ["pendente_pagamento", "agendado"]:
            raise BusinessRuleError(
                f"Mudança em status {mudanca.status} não pode ser cancelada"
            )

        mudanca.status = "cancelado"
        mudanca.observacoes = motivo or "Cancelado pelo usuário"

        await self.session.commit()
        await self.session.refresh(mudanca)

        logger.info(f"Mudança {mudanca_id} cancelada por usuário {usuario_id}")

        return mudanca

    # ========================================================================
    # Métodos privados
    # ========================================================================

    async def _aplicar_mudanca(self, mudanca: MudancaPlano) -> None:
        """Aplica mudança na assinatura."""
        # Buscar assinatura
        stmt = select(AssinaturaTenant).where(AssinaturaTenant.id == mudanca.assinatura_id)
        result = await self.session.execute(stmt)
        assinatura = result.scalar_one()

        # Atualizar assinatura
        assinatura.plano_id = mudanca.plano_destino_id
        assinatura.usuarios_contratados = mudanca.usuarios_destino

        # Atualizar mudança
        mudanca.status = "aplicado"
        mudanca.aplicado_em = datetime.now(timezone.utc)
        mudanca.aplicado_por_job = True

        # Se a assinatura já possui contrato recorrente no Stripe, sincronizar os novos acessos/plano
        if assinatura.stripe_subscription_id:
            try:
                from core.models.tenant import Tenant
                from core.services.stripe_service import StripeService

                plano_novo = await self._obter_plano(mudanca.plano_destino_id)
                ciclo = getattr(assinatura, "ciclo_pagamento", "MENSAL") or "MENSAL"
                _, detalhamento = await self.pricing_service.calcular_preco_total(
                    plano_id=plano_novo.id,
                    quantidade_usuarios=mudanca.usuarios_destino,
                    ciclo=ciclo,
                )
                tenant_obj = await self.session.get(Tenant, assinatura.tenant_id)
                extensoes = list((tenant_obj.branding or {}).get("extensoes_contratadas") or []) if tenant_obj else []
                StripeService().atualizar_assinatura_recorrente(
                    stripe_subscription_id=assinatura.stripe_subscription_id,
                    detalhamento_preco=detalhamento,
                    nome_plano=plano_novo.nome,
                    ciclo=ciclo,
                    usuarios_contratados=mudanca.usuarios_destino,
                    extensoes_contratadas=extensoes,
                    cobrar_prorata_no_stripe=False,
                )
            except Exception as exc:
                logger.warning(f"Falha ao atualizar contrato Stripe na mudança {mudanca.id}: {exc}")

        logger.info(
            f"Mudança {mudanca.id} aplicada: Plano {mudanca.plano_destino_id}, "
            f"{mudanca.usuarios_destino} usuários"
        )

    async def _bloquear_por_inadimplencia(self, mudanca: MudancaPlano) -> None:
        """Bloqueia tenant por inadimplência."""
        # Buscar assinatura
        stmt = select(AssinaturaTenant).where(AssinaturaTenant.id == mudanca.assinatura_id)
        result = await self.session.execute(stmt)
        assinatura = result.scalar_one()

        # Bloquear assinatura
        assinatura.status = "BLOQUEADA"
        assinatura.data_bloqueio = datetime.now(timezone.utc)

        # Atualizar mudança
        mudanca.status = "bloqueado"

        # Criar histórico de bloqueio
        bloqueio = HistoricoBloqueio(
            tenant_id=mudanca.tenant_id,
            mudanca_plano_id=mudanca.id,
            assinatura_id=assinatura.id,
            motivo="INADIMPLENCIA_MUDANCA_PLANO",
            descricao=f"Mudança {mudanca.id} liberada manualmente não foi paga no prazo ({mudanca.data_limite_pagamento})",
            data_bloqueio=datetime.now(timezone.utc),
            bloqueado_automaticamente=True
        )

        self.session.add(bloqueio)

    async def _validar_compatibilidade_hectares_destino(self, plano_destino: PlanoAssinatura) -> Decimal:
        """
        Verifica se a soma atual dos hectares das propriedades ativas do tenant
        cabe dentro do limite_hectares do pacote de destino.

        Args:
            plano_destino: Objeto PlanoAssinatura desejado.

        Returns:
            Decimal: Soma atual de hectares das propriedades ativas do tenant.

        Raises:
            BusinessRuleError: Se as propriedades ativas excederem o limite de hectares do plano destino.
        """
        area_expr = func.coalesce(
            UnidadeProdutiva.area_total_calculada_ha,
            UnidadeProdutiva.area_total_ha,
            0,
        )
        stmt_soma = select(func.coalesce(func.sum(area_expr), 0)).where(
            UnidadeProdutiva.tenant_id == self.tenant_id,
            UnidadeProdutiva.ativo == True,
        )
        area_atual = Decimal(str((await self.session.execute(stmt_soma)).scalar_one() or 0))

        if plano_destino.limite_hectares is not None and Decimal(str(plano_destino.limite_hectares)) > 0:
            limite_destino = Decimal(str(plano_destino.limite_hectares))
            if area_atual > limite_destino:
                raise BusinessRuleError(
                    f"Não é possível migrar para o pacote '{plano_destino.nome}' (limite de {limite_destino:.2f} ha) "
                    f"pois suas propriedades ativas somam {area_atual:.2f} ha. "
                    "Escolha um pacote compatível com o tamanho total das suas propriedades."
                )

        return area_atual

    async def _obter_assinatura(self, assinatura_id: Optional[UUID]) -> AssinaturaTenant:
        """Busca assinatura ativa/trial/pendente do tenant."""
        if assinatura_id:
            stmt = select(AssinaturaTenant).where(
                and_(
                    AssinaturaTenant.id == assinatura_id,
                    AssinaturaTenant.tenant_id == self.tenant_id
                )
            )
        else:
            stmt = (
                select(AssinaturaTenant)
                .where(
                    and_(
                        AssinaturaTenant.tenant_id == self.tenant_id,
                        AssinaturaTenant.tipo_assinatura.in_(["TENANT", "GRUPO", "PRINCIPAL"]),
                    )
                )
                .order_by(AssinaturaTenant.data_inicio.desc())
                .limit(1)
            )

        result = await self.session.execute(stmt)
        assinatura = result.scalar_one_or_none()

        if not assinatura:
            raise EntityNotFoundError("Assinatura do tenant não encontrada.")

        if assinatura.status == "BLOQUEADA":
            raise BusinessRuleError(
                "Assinatura está bloqueada. Entre em contato com o suporte."
            )

        return assinatura

    async def _obter_plano(self, plano_id: UUID) -> PlanoAssinatura:
        """Busca plano."""
        stmt = select(PlanoAssinatura).where(PlanoAssinatura.id == plano_id)
        result = await self.session.execute(stmt)
        plano = result.scalar_one_or_none()

        if not plano:
            raise EntityNotFoundError("Plano não encontrado.")

        if not plano.ativo:
            raise BusinessRuleError("Plano indisponível ou inativo.")

        return plano

    def _determinar_tipo_mudanca(
        self,
        plano_origem_id: UUID,
        usuarios_origem: int,
        plano_destino_id: UUID,
        usuarios_destino: int,
        diferenca_valor: Decimal = Decimal("0.00"),
    ) -> str:
        """Determina tipo de mudança com base no plano, acessos e diferença financeira composta."""
        mudou_plano = plano_origem_id != plano_destino_id
        mudou_usuarios = usuarios_origem != usuarios_destino

        if mudou_plano and mudou_usuarios:
            if diferenca_valor >= 0:
                return "UPGRADE_COMPLETO"
            return "DOWNGRADE_COMPLETO"
        elif mudou_plano:
            if diferenca_valor >= 0:
                return "UPGRADE_PLANO"
            return "DOWNGRADE_PLANO"
        elif mudou_usuarios:
            if usuarios_destino > usuarios_origem:
                return "UPGRADE_USUARIOS"
            return "DOWNGRADE_USUARIOS"
        else:
            raise BusinessRuleError("Nenhuma mudança de pacote ou quantidade de acessos simultâneos foi detectada.")

    def _gerar_mensagem_simulacao(
        self,
        tipo_mudanca: str,
        plano_atual: str,
        plano_novo: str,
        usuarios_atual: int,
        usuarios_novo: int,
        valor_proporcional: Decimal,
        dias_restantes: int,
        ja_pagou: bool = True,
        valor_novo_total: Decimal | None = None,
    ) -> str:
        """Gera mensagem explicativa para o usuário."""
        if not ja_pagou:
            valor_cheio = valor_novo_total if valor_novo_total is not None else Decimal("0.00")
            return (
                f"Como a assinatura ainda está em trial ou sem pagamento confirmado, a mudança para "
                f"{plano_novo} ({usuarios_novo} usuários) será aplicada imediatamente: a cobrança em aberto "
                f"anterior será cancelada e uma nova fatura de R$ {valor_cheio:.2f} será gerada com o valor do novo plano."
            )

        if tipo_mudanca.startswith("UPGRADE"):
            if valor_proporcional > 0:
                return (
                    f"Upgrade de {plano_atual} ({usuarios_atual} users) para "
                    f"{plano_novo} ({usuarios_novo} users). "
                    f"Você pagará R$ {valor_proporcional:.2f} proporcional aos "
                    f"{dias_restantes} dias restantes do ciclo atual. "
                    f"Após confirmação do pagamento, o upgrade será aplicado imediatamente."
                )
            else:
                return f"Upgrade para {plano_novo} com {usuarios_novo} usuários será aplicado no próximo ciclo."

        else:  # DOWNGRADE
            return (
                f"Downgrade de {plano_atual} ({usuarios_atual} users) para "
                f"{plano_novo} ({usuarios_novo} users) será agendado para o próximo "
                f"ciclo de cobrança. Você continuará com acesso ao plano atual até lá."
            )

    async def _assinatura_ja_paga(self, assinatura: AssinaturaTenant) -> bool:
        """Indica se a assinatura já teve pagamento prévio confirmado."""
        if getattr(assinatura, "status", None) in ("TRIAL", "PENDENTE_PAGAMENTO", "PENDENTE"):
            fatura_paga_stmt = (
                select(Fatura.id)
                .where(
                    Fatura.assinatura_id == assinatura.id,
                    Fatura.status == "PAGA",
                )
                .limit(1)
            )
            fatura_paga = (await self.session.execute(fatura_paga_stmt)).scalar_one_or_none()
            return fatura_paga is not None

        if getattr(assinatura, "stripe_subscription_id", None):
            return True

        fatura_paga_stmt = (
            select(Fatura.id)
            .where(
                Fatura.assinatura_id == assinatura.id,
                Fatura.status == "PAGA",
            )
            .limit(1)
        )
        fatura_paga = (await self.session.execute(fatura_paga_stmt)).scalar_one_or_none()
        return fatura_paga is not None or getattr(assinatura, "status", None) == "ATIVA"

    async def _validar_mudanca_pendente(self, assinatura_id: Optional[UUID]) -> None:
        """Valida que não há mudança pendente."""
        assinatura = await self._obter_assinatura(assinatura_id)

        stmt = (
            select(MudancaPlano)
            .where(MudancaPlano.assinatura_id == assinatura.id)
            .where(MudancaPlano.status.in_(["pendente_pagamento", "agendado", "liberado_manualmente"]))
        )
        result = await self.session.execute(stmt)
        mudanca_existente = result.scalar_one_or_none()

        if mudanca_existente:
            raise BusinessRuleError(
                f"Já existe uma mudança de plano pendente (status: {mudanca_existente.status}). "
                "Cancele ou aguarde conclusão antes de solicitar nova mudança."
            )
