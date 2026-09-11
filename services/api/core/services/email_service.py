import aiosmtplib
from email.message import EmailMessage
from email.utils import make_msgid, formatdate
from jinja2 import Environment, FileSystemLoader
import os
import uuid
from loguru import logger
from core.config import settings

class SMTPPlatformConfigNotFoundError(RuntimeError):
    """A configuração SMTP global da plataforma não foi cadastrada."""


class EmailService:
    def __init__(self):
        template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
        self.env = Environment(loader=FileSystemLoader(template_dir))
        
    async def _get_smtp_config(self, tenant_id: uuid.UUID = None, allow_env_fallback: bool = True):
        """Busca configuração SMTP com hierarquia configurável."""
        from core.database import async_session_maker
        from core.models.tenant import Tenant
        from core.models.configuration import ConfiguracaoSaaS
        from sqlalchemy import select

        async with async_session_maker() as session:
            # 1. White-label Tenant specific
            if tenant_id:
                tenant = await session.get(Tenant, tenant_id)
                if tenant and tenant.smtp_config:
                    return tenant.smtp_config

            # 2. Global DB Config
            stmt = select(ConfiguracaoSaaS).where(ConfiguracaoSaaS.chave == "smtp_global", ConfiguracaoSaaS.ativo == True)
            res = await session.execute(stmt)
            config_db = res.scalar_one_or_none()
            if config_db:
                return config_db.valor

        if not allow_env_fallback:
            raise SMTPPlatformConfigNotFoundError(
                "Configuração SMTP global da plataforma não encontrada."
            )

        # 3. Fallback Env (mantido para os demais e-mails legados)
        return {
            "host": settings.smtp_host,
            "port": settings.smtp_port,
            "user": settings.smtp_user,
            "pass": settings.smtp_pass,
            "from": settings.mail_from
        }

    async def _send(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        tenant_id: uuid.UUID = None,
        allow_env_fallback: bool = True,
    ):
        """Método interno para envio via SMTP dinâmico."""
        config = await self._get_smtp_config(tenant_id, allow_env_fallback=allow_env_fallback)
        
        from_email = config.get("from") or (settings.mail_from if allow_env_fallback else "")

        if not from_email:
            raise SMTPPlatformConfigNotFoundError(
                "Remetente não encontrado na configuração SMTP global da plataforma."
            )

        message = EmailMessage()
        message["From"] = from_email
        message["To"] = to_email
        message["Subject"] = subject
        # Sem Date/Message-ID, provedores como Gmail costumam classificar a
        # mensagem como spam ou descartá-la silenciosamente — o SMTP aceita
        # o envio (sem erro), mas o destinatário nunca recebe.
        message["Date"] = formatdate(localtime=True)
        message["Message-ID"] = make_msgid(domain=from_email.split("@")[-1] if "@" in from_email else None)
        message.add_alternative(html_content, subtype="html")

        try:
            host = config.get("host")
            port = int(config.get("port", 587))
            user = config.get("user")
            pwd = config.get("pass")

            if not host:
                raise RuntimeError("SMTP host não configurado.")

            # Para portas autenticadas comuns, exigir credenciais explicitamente.
            if port in (465, 587) and (not user or not pwd):
                raise RuntimeError(
                    f"SMTP configurado em {host}:{port}, mas sem credenciais de autenticação."
                )

            if user and pwd:
                await aiosmtplib.send(
                    message,
                    hostname=host,
                    port=port,
                    username=user,
                    password=pwd,
                    use_tls=port == 465,
                    start_tls=port == 587
                )
            else:
                await aiosmtplib.send(message, hostname=host, port=port)
                
            logger.info(
                f"Email enviado ({'White-label' if tenant_id else 'SaaS'}) para {to_email} "
                f"via {host}:{port} como {from_email}"
            )
        except Exception as e:
            logger.exception(
                f"Falha ao enviar email para {to_email} "
                f"usando SMTP host={config.get('host')} port={config.get('port')} "
                f"user={'set' if config.get('user') else 'empty'} "
                f"from={config.get('from', settings.mail_from)}"
            )
            raise

    async def send_invoice_approved(self, email: str, nome: str, plano: str, valor: float, tenant_id: uuid.UUID = None):
        template = self.env.get_template("emails/invoice_approved.html")
        html = template.render(
            nome_cliente=nome,
            nome_plano=plano,
            valor=f"{valor:.2f}",
            referência="Mensalidade AgroSaaS",
            login_url=f"{settings.frontend_url}/login"
        )
        await self._send(email, "Pagamento Confirmado - AgroSaaS", html, tenant_id)

    async def send_invoice_rejected(self, email: str, nome: str, justificativa: str, tenant_id: uuid.UUID = None):
        template = self.env.get_template("emails/invoice_rejected.html")
        html = template.render(
            nome_cliente=nome,
            justificativa=justificativa,
            billing_url=f"{settings.frontend_url}/settings/account"
        )
        await self._send(email, "⚠️ Ação Necessária: Problema no Pagamento", html, tenant_id)

    async def send_welcome(self, email: str, nome: str, tenant_nome: str, username: str, tenant_id: uuid.UUID = None):
        template = self.env.get_template("emails/welcome.html")
        html = template.render(
            nome_cliente=nome,
            nome_tenant=tenant_nome,
            username=username,
            login_url=f"{settings.frontend_url}/login"
        )
        await self._send(email, "Bem-vindo ao AgroSaaS! 🚜", html, tenant_id)

    async def send_invite(self, email: str, remetente: str, tenant_nome: str, perfil_nome: str, token: str, tenant_id: uuid.UUID = None):
        template = self.env.get_template("emails/invite.html")
        html = template.render(
            remetente=remetente,
            nome_tenant=tenant_nome,
            perfil_nome=perfil_nome,
            invite_url=f"{settings.frontend_url}/convite/aceitar?token={token}"
        )
        await self._send(email, f"Convite: {tenant_nome} no AgroSaaS", html, tenant_id)

    async def send_activation_link(self, email: str, nome: str, tenant_nome: str, token: str, tenant_id: uuid.UUID = None):
        template = self.env.get_template("emails/activation_link.html")
        html = template.render(
            nome_usuario=nome,
            nome_tenant=tenant_nome,
            activation_url=f"{settings.frontend_url}/onboarding/ativar?token={token}",
        )
        await self._send(email, "Confirme sua ativacao no AgroSaaS", html, tenant_id)

    async def send_registration_confirmation(self, email: str, nome: str, tenant_nome: str, token: str, tenant_id: uuid.UUID = None):
        template = self.env.get_template("emails/registration_confirmation.html")
        html = template.render(
            nome_usuario=nome,
            nome_tenant=tenant_nome,
            confirmation_url=f"{settings.frontend_url}/onboarding/confirmar-cadastro?token={token}",
        )
        await self._send(email, "Confirme seu cadastro no AgroSaaS", html, tenant_id)

    async def send_password_recovery(self, email: str, nome_usuario: str, token: str, tenant_id: uuid.UUID = None):
        """Envia recuperação usando exclusivamente o SMTP da plataforma.

        O ``tenant_id`` é mantido na assinatura por compatibilidade com os
        chamadores existentes, mas recuperação de senha é uma comunicação
        transacional do AgroSaaS e não deve usar o SMTP white-label do tenant.
        """
        template = self.env.get_template("emails/password_reset.html")
        reset_url = f"{settings.frontend_url}/reset-password?token={token}"
        from datetime import datetime
        html = template.render(
            nome_usuario=nome_usuario,
            email_usuario=email,
            reset_url=reset_url,
            data_solicitacao=datetime.now().strftime("%d/%m/%Y às %H:%M")
        )
        await self._send(
            email,
            "Recuperação de Senha - AgroSaaS 🔑",
            html,
            tenant_id=None,
            allow_env_fallback=False,
        )

    async def send_pedido_compra_confirmacao(
        self,
        email: str,
        fornecedor_nome: str,
        tenant_nome: str,
        itens: list[dict],
        valor_total: str,
        condicoes_pagamento: str,
        endereco_entrega: str,
        prazo_entrega_dias: int | None,
        token: str,
        senha_confirmacao: str,
        dias_expiracao: int,
        tenant_id: uuid.UUID = None,
        numero_pedido: str | None = None,
    ):
        template = self.env.get_template("emails/pedido_compra_confirmacao.html")
        html = template.render(
            fornecedor_nome=fornecedor_nome,
            tenant_nome=tenant_nome,
            itens=itens,
            valor_total=valor_total,
            condicoes_pagamento=condicoes_pagamento,
            endereco_entrega=endereco_entrega,
            prazo_entrega_dias=prazo_entrega_dias,
            confirmacao_url=f"{settings.frontend_url}/pedido-compra/confirmar?token={token}",
            senha_confirmacao=senha_confirmacao,
            dias_expiracao=dias_expiracao,
            numero_pedido=numero_pedido,
        )
        assunto = f"Pedido de Compra {numero_pedido} — {tenant_nome} aguarda sua confirmação" if numero_pedido else f"Pedido de Compra — {tenant_nome} aguarda sua confirmação"
        await self._send(email, assunto, html, tenant_id)

    async def send_trial_notice(self, email: str, nome: str, nome_produtor: str, nome_plano: str, dias_trial: int, data_vencimento, tenant_id: uuid.UUID = None):
        """Envia e-mail com aviso de período de trial para nova assinatura."""
        template = self.env.get_template("emails/trial_notice.html")
        from datetime import datetime
        data_vencimento_str = data_vencimento.strftime("%d/%m/%Y") if hasattr(data_vencimento, 'strftime') else str(data_vencimento)

        html = template.render(
            nome_usuario=nome,
            nome_produtor=nome_produtor,
            nome_plano=nome_plano,
            dias_trial=dias_trial,
            data_vencimento=data_vencimento_str,
            dashboard_url=f"{settings.frontend_url}/dashboard"
        )
        await self._send(email, f"Período de Trial Iniciado - {dias_trial} dias grátis 🎉", html, tenant_id)

email_service = EmailService()
