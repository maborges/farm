"""
Serviço de integração com Stripe.

Responsável por:
- Criar sessões de checkout para primeira cobrança
- Processar webhooks de pagamento (payment_intent.succeeded)

Configuração necessária em .env.local:
  STRIPE_SECRET_KEY=sk_live_...
  STRIPE_WEBHOOK_SECRET=whsec_...
  FRONTEND_URL=http://localhost:3000
"""
import stripe
from loguru import logger
from core.config import settings

stripe.api_key = settings.stripe_secret_key
FRONTEND_URL = settings.frontend_url
WEBHOOK_SECRET = settings.stripe_webhook_secret


class StripeService:

    @staticmethod
    def montar_line_items_compostos(
        detalhamento_preco: list[dict],
        nome_plano: str,
        ciclo: str,
        extensoes_contratadas: list[str] | None = None,
    ) -> list[dict]:
        """
        Monta os line_items do Stripe Checkout para cobrança composta:
        Item 1: Pacote Base (inclui todos os módulos nativos e franquia base de acessos Web).
        Itens 2+: Licenças adicionais de acesso simultâneo na Web por faixa progressiva.
        Itens finais: Extensões opcionais contratadas à parte (IoT e/ou ERP).

        Args:
            detalhamento_preco: Lista de faixas calculada pelo PlanoPricingService.
            nome_plano: Nome comercial do pacote (ex: Médio Produtor).
            ciclo: MENSAL ou ANUAL.
            extensoes_contratadas: Lista opcional de IDs de extensões (EXT_IOT, EXT_ERP).

        Returns:
            list[dict]: Lista de line_items com price_data em centavos (BRL).
        """
        from core.constants import TABELA_EXTENSOES_A_PARTE

        intervalo = "year" if ciclo == "ANUAL" else "month"
        line_items: list[dict] = []

        for item in detalhamento_preco:
            tipo = item.get("tipo", "PACOTE_BASE")
            qtd = max(1, int(item.get("usuarios_nesta_faixa") or 1))
            preco_unitario_reais = float(item.get("preco_unitario") or 0.0)
            unit_amount_centavos = int(round(preco_unitario_reais * 100))

            if tipo == "PACOTE_BASE":
                line_items.append({
                    "price_data": {
                        "currency": "brl",
                        "unit_amount": unit_amount_centavos,
                        "recurring": {"interval": intervalo},
                        "product_data": {
                            "name": f"Pacote {nome_plano} — Todos os Módulos ({ciclo.capitalize()})",
                            "description": f"Inclui {qtd} acesso(s) simultâneo(s) Web + App Campo ilimitado",
                        },
                    },
                    "quantity": 1,
                })
            else:
                faixa_ini = item.get("faixa_inicio", 1)
                faixa_fim = item.get("faixa_fim") or "∞"
                desconto_txt = " (20% OFF Anual)" if ciclo == "ANUAL" else ""
                line_items.append({
                    "price_data": {
                        "currency": "brl",
                        "unit_amount": unit_amount_centavos,
                        "recurring": {"interval": intervalo},
                        "product_data": {
                            "name": f"Licença Adicional de Acesso Simultâneo Web — {nome_plano}{desconto_txt}",
                            "description": f"Faixa adicional {faixa_ini} a {faixa_fim}",
                        },
                    },
                    "quantity": qtd,
                })

        if extensoes_contratadas:
            for ext_id in extensoes_contratadas:
                info_ext = TABELA_EXTENSOES_A_PARTE.get(ext_id)
                if not info_ext:
                    continue
                preco_ext = float(
                    info_ext["preco_anual"] if ciclo == "ANUAL" else info_ext["preco_mensal"]
                )
                desconto_txt = " (20% OFF Anual)" if ciclo == "ANUAL" else ""
                line_items.append({
                    "price_data": {
                        "currency": "brl",
                        "unit_amount": int(round(preco_ext * 100)),
                        "recurring": {"interval": intervalo},
                        "product_data": {
                            "name": f"Extensão {info_ext['nome']}{desconto_txt}",
                            "description": f"Extensão corporativa contratada à parte ({ext_id})",
                        },
                    },
                    "quantity": 1,
                })

        return line_items

    async def criar_checkout_assinatura(
        self,
        tenant_id: str,
        assinatura_id: str,
        email: str,
        plano_id: str,
        ciclo: str,
        detalhamento_preco: list[dict] | None = None,
        nome_plano: str | None = None,
        usuarios_contratados: int | None = None,
        extensoes_contratadas: list[str] | None = None,
    ) -> str:
        """
        Cria uma sessão de checkout Stripe para o primeiro pagamento.

        Retorna a URL de checkout para redirecionar o assinante.
        Quando detalhamento_preco é informado, compõe os line_items dinâmicos
        (pacote base + licenças adicionais de acesso simultâneo). Caso contrário,
        busca o preço via lookup_key no Stripe:
          - Formato: plano_{plano_id}_{MENSAL|ANUAL}

        Se STRIPE_SECRET_KEY não estiver configurada (desenvolvimento),
        retorna URL de simulação local.
        """
        if not stripe.api_key:
            logger.warning("STRIPE_SECRET_KEY não configurada — usando checkout simulado")
            return f"{FRONTEND_URL}/onboarding/pagamento-simulado?assinatura_id={assinatura_id}"

        try:
            metadata = {
                "tenant_id": tenant_id,
                "assinatura_id": assinatura_id,
                "plano_id": plano_id,
            }
            if usuarios_contratados is not None:
                metadata["usuarios_contratados"] = str(usuarios_contratados)
            if extensoes_contratadas:
                metadata["extensoes_contratadas"] = ",".join(extensoes_contratadas)

            if detalhamento_preco:
                line_items = self.montar_line_items_compostos(
                    detalhamento_preco=detalhamento_preco,
                    nome_plano=nome_plano or "DeepFarms",
                    ciclo=ciclo,
                    extensoes_contratadas=extensoes_contratadas,
                )
            else:
                # Buscar preço via lookup key (compatibilidade padrão)
                lookup_key = f"plano_{plano_id}_{ciclo}"
                prices = stripe.Price.list(lookup_keys=[lookup_key], limit=1)

                if not prices.data:
                    logger.error(f"Preço Stripe não encontrado para lookup_key={lookup_key}")
                    raise ValueError(f"Preço não configurado no Stripe para o plano/ciclo selecionado")

                price_id = prices.data[0].id
                line_items = [{"price": price_id, "quantity": 1}]

            session = stripe.checkout.Session.create(
                customer_email=email,
                line_items=line_items,
                mode="subscription",
                success_url=f"{FRONTEND_URL}/onboarding/sucesso?session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=f"{FRONTEND_URL}/onboarding/cancelado",
                metadata=metadata,
            )

            logger.info(f"Checkout Stripe criado: {session.id} para tenant {tenant_id}")
            return session.url

        except stripe.StripeError as e:
            logger.error(f"Erro Stripe ao criar checkout: {e}")
            raise ValueError(f"Erro ao criar sessão de pagamento: {e.user_message}")

    def stripe_configured(self) -> bool:
        return bool(stripe.api_key)

    async def criar_checkout_mudanca_prorata(
        self,
        tenant_id: str,
        assinatura_id: str,
        mudanca_plano_id: str,
        plano_destino_id: str,
        nome_plano_destino: str,
        valor_reais: float,
        email: str,
        fatura_id: str | None = None,
    ) -> str:
        """Cria sessão Stripe Checkout avulsa (mode='payment') para cobrança pro-rata de upgrade."""
        if not stripe.api_key:
            logger.warning("STRIPE_SECRET_KEY não configurada — usando checkout pro-rata simulado")
            return f"{FRONTEND_URL}/dashboard/settings/billing?mudanca_id={mudanca_plano_id}"

        unit_amount = max(50, int(round(float(valor_reais) * 100)))
        metadata = {
            "tipo": "mudanca_plano_prorata",
            "tenant_id": tenant_id,
            "assinatura_id": assinatura_id,
            "mudanca_plano_id": mudanca_plano_id,
            "plano_destino_id": plano_destino_id,
        }
        if fatura_id:
            metadata["fatura_id"] = fatura_id

        try:
            session = stripe.checkout.Session.create(
                customer_email=email,
                line_items=[
                    {
                        "price_data": {
                            "currency": "brl",
                            "unit_amount": unit_amount,
                            "product_data": {
                                "name": f"Upgrade de Plano (Pro-rata) — {nome_plano_destino}",
                                "description": "Diferença proporcional ao período restante do ciclo atual",
                            },
                        },
                        "quantity": 1,
                    }
                ],
                mode="payment",
                success_url=f"{FRONTEND_URL}/dashboard/settings/billing?upgrade=sucesso&session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=f"{FRONTEND_URL}/dashboard/settings/billing?upgrade=cancelado",
                metadata=metadata,
            )
            logger.info(f"Checkout pro-rata Stripe criado: {session.id} para mudança {mudanca_plano_id}")
            return session.url
        except stripe.StripeError as e:
            logger.error(f"Erro Stripe ao criar checkout pro-rata: {e}")
            raise ValueError(f"Erro ao criar sessão de pagamento: {e.user_message}")

    def atualizar_assinatura_recorrente(
        self,
        stripe_subscription_id: str,
        detalhamento_preco: list[dict],
        nome_plano: str,
        ciclo: str,
        usuarios_contratados: int,
        extensoes_contratadas: list[str] | None = None,
        cobrar_prorata_no_stripe: bool = False,
    ) -> bool:
        """
        Atualiza o contrato recorrente existente no Stripe (stripe.Subscription.modify)
        quando o assinante adiciona novos acessos simultâneos e/ou muda de pacote,
        garantindo que as próximas renovações já cobrem a nova quantidade de acessos.
        """
        if not stripe.api_key or not stripe_subscription_id:
            logger.info(
                f"Stripe não configurado ou sem subscription_id ({stripe_subscription_id}) — "
                "atualização recorrente registrada apenas localmente."
            )
            return False

        try:
            novos_items = self.montar_line_items_compostos(
                detalhamento_preco=detalhamento_preco,
                nome_plano=nome_plano,
                ciclo=ciclo,
                extensoes_contratadas=extensoes_contratadas,
            )
            sub_atual = stripe.Subscription.retrieve(stripe_subscription_id)
            items_existentes = (sub_atual.get("items") or {}).get("data") or []

            items_payload: list[dict] = [
                {"id": item["id"], "deleted": True} for item in items_existentes if item.get("id")
            ]
            items_payload.extend(novos_items)

            stripe.Subscription.modify(
                stripe_subscription_id,
                items=items_payload,
                proration_behavior="create_prorations" if cobrar_prorata_no_stripe else "none",
                metadata={
                    "usuarios_contratados": str(usuarios_contratados),
                    "extensoes_contratadas": ",".join(extensoes_contratadas or []),
                },
            )
            logger.info(
                f"Contrato Stripe {stripe_subscription_id} atualizado para "
                f"{usuarios_contratados} acessos simultâneos ({nome_plano})"
            )
            return True
        except Exception as exc:
            logger.warning(f"Não foi possível sincronizar aditivo no Stripe ({stripe_subscription_id}): {exc}")
            return False

    def verificar_webhook(self, payload: bytes, signature: str) -> stripe.Event:
        """Valida e parseia um evento de webhook Stripe."""
        if not WEBHOOK_SECRET:
            raise ValueError("STRIPE_WEBHOOK_SECRET não configurado")
        return stripe.Webhook.construct_event(payload, signature, WEBHOOK_SECRET)
