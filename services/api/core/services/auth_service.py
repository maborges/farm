from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select, text, update
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status, Request
from passlib.context import CryptContext
from datetime import date, datetime, timedelta, timezone
from jose import jwt
from typing import Optional
import uuid
import secrets
import re
import unicodedata
from loguru import logger

from core.models.auth import Usuario, TenantUsuario, PerfilAcesso, UnidadeProdutivaUsuario as FazendaUsuario, TokenRecuperacaoSenha
from core.models.admin_user import AdminUser
from core.models.tenant import Tenant
from core.models.unidade_produtiva import UnidadeProdutiva as Fazenda
from core.models.billing import AssinaturaTenant, PlanoAssinatura, Fatura
from core.schemas.auth_schemas import FreeUserCreateRequest, LoginRequest, UserCreateRequest, TenantAcessoResponse, UnidadeProdutivaAcessoResponse as FazendaAcessoResponse, PerfilSimplesResponse, UsuarioMeResponse
from core.config import settings
from core.constants import normalize_tenant_role
from core.services.demo_access_service import is_demo_tenant, is_read_only_profile
from core.services.demo_config_service import get_demo_saas_config
from core.services.login_rate_limit_service import LoginRateLimitService
from core.services.session_timeout_service import get_session_idle_minutes, session_expiration
from core.services.email_service import email_service, SMTPPlatformConfigNotFoundError
from core.utils.cpf_cnpj import normalizar_documento_opcional, validar_cpf_ou_cnpj

import bcrypt

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def _slugify_tenant_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-")
    return slug or "tenant"


def _username_base(email: str) -> str:
    local = email.partition("@")[0]
    normalized = unicodedata.normalize("NFKD", local).encode("ascii", "ignore").decode("ascii")
    username = re.sub(r"[^a-z0-9_]+", "_", normalized.lower()).strip("_")
    return (username or "usuario")[:40]

class AuthService:
    def __init__(self, session: AsyncSession):
        self.session = session
        
    def verify_password(self, plain_password, hashed_password):
        try:
            return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
        except ValueError:
            return False

    def get_password_hash(self, password):
        return hash_password(password)

    async def _read_restricted_login_material(self, auth_session, email: str):
        """Read one pre-authentication record through the dedicated SQL function."""
        result = await auth_session.execute(
            text("SELECT * FROM farms.auth_login_material(:email)"),
            {"email": email},
        )
        rows = result.mappings().all()
        if len(rows) > 1:
            raise RuntimeError("Multiple users match the normalized login email")
        return rows[0] if rows else None

    @staticmethod
    def _user_from_login_material(material):
        """Build the minimal user value needed after bcrypt verification."""
        if material is None:
            return None
        return Usuario(
            id=material["usuario_id"],
            email=material["email"],
            username=material["username"],
            senha_hash=material["senha_hash"],
            is_superuser=material["is_superuser"],
            ativo=material["ativo"],
        )

    @staticmethod
    async def _tenant_login_rate_config(session, tenant_id) -> dict:
        """Read only the rate-limit keys after bcrypt and Tenant membership validation."""
        from core.models.tenant_config import ConfiguracaoTenant

        result = await session.execute(
            select(ConfiguracaoTenant.chave, ConfiguracaoTenant.valor).where(
                ConfiguracaoTenant.tenant_id == tenant_id,
                ConfiguracaoTenant.categoria == "seguranca",
                ConfiguracaoTenant.chave.in_(
                    ("rate_limiting_ativo", "max_tentativas", "tempo_bloqueio_minutos")
                ),
                ConfiguracaoTenant.ativo.is_(True),
            )
        )
        config = {row.chave: row.valor for row in result.all()}
        return {
            "rate_limiting_ativo": config.get("rate_limiting_ativo", True),
            "max_tentativas": config.get("max_tentativas", 5),
            "tempo_bloqueio_minutos": config.get("tempo_bloqueio_minutos", 15),
        }

    @staticmethod
    async def _register_login_failure(rate_service, email, reason, ip, user_agent):
        await rate_service.registrar_tentativa_falha(
            email=email,
            motivo=reason,
            ip_address=ip,
            user_agent=user_agent,
        )
        
    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None):
        to_encode = data.copy()
        tenant_id = to_encode.get("tenant_id")
        if not tenant_id:
            tenant_contexts = to_encode.get("tenant_contexts") or []
            if len(tenant_contexts) == 1:
                context_tenant_id = tenant_contexts[0].get("id")
                if context_tenant_id:
                    to_encode["tenant_id"] = str(context_tenant_id)

        now = datetime.now(timezone.utc)
        if expires_delta:
            expire = now + expires_delta
        else:
            expire = now + timedelta(minutes=settings.access_token_expire_minutes)

        tenant_id = to_encode.get("tenant_id")
        is_superuser = bool(to_encode.get("is_superuser"))
        account_type = to_encode.get("account_type")
        if not account_type:
            account_type = "PLATFORM_ADMIN" if is_superuser else (
                "COMMERCIAL" if tenant_id else "INDIVIDUAL_FREE"
            )
        product_scope = to_encode.get("product_scope")
        if not product_scope:
            if account_type == "PLATFORM_ADMIN":
                product_scope = ["backoffice", "saas", "agro:free"]
            elif account_type == "COMMERCIAL":
                product_scope = ["saas", "agro:free"]
            else:
                product_scope = ["agro:free"]

        to_encode.update({
            "exp": expire,
            "iat": now,
            "jti": str(uuid.uuid4()),
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
            "token_version": 2,
            "account_type": account_type,
            "product_scope": product_scope,
        })
        encoded_jwt = jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
        return encoded_jwt

    async def register_free_user(self, user_data: FreeUserCreateRequest) -> tuple[Usuario | None, bool]:
        """Cria identidade global sem tenant com resposta externa não enumerável."""
        email = str(user_data.email).strip().lower()
        # O custo do bcrypt ocorre também para contas existentes, reduzindo o
        # sinal temporal utilizável para enumeração.
        hashed_pw = self.get_password_hash(user_data.senha)
        existing = (await self.session.execute(
            select(Usuario.id).where(func.lower(Usuario.email) == email)
        )).scalar_one_or_none()
        if existing is not None:
            return None, False

        base = _username_base(email)
        for attempt in range(8):
            username = base if attempt == 0 else f"{base}_{secrets.token_hex(4)}"
            db_user = Usuario(
                email=email,
                username=username,
                nome_completo=user_data.nome,
                apelido=user_data.nome.split()[0][:20],
                senha_hash=hashed_pw,
            )
            try:
                async with self.session.begin_nested():
                    self.session.add(db_user)
                    await self.session.flush()
                await self.session.commit()
                logger.info("Identidade gratuita criada", user_id=str(db_user.id))
                return db_user, True
            except IntegrityError:
                duplicate_email = (await self.session.execute(
                    select(Usuario.id).where(func.lower(Usuario.email) == email)
                )).scalar_one_or_none()
                if duplicate_email is not None:
                    return None, False

        logger.error("Não foi possível reservar username único para cadastro gratuito")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cadastro temporariamente indisponível",
        )

    async def register_user(self, user_data: UserCreateRequest) -> Usuario:
        # Check if email or username exists
        stmt = select(Usuario).where((Usuario.email == user_data.email) | (Usuario.username == user_data.username))
        result = await self.session.execute(stmt)
        if result.scalars().first():
            raise HTTPException(status_code=400, detail="Email ou Username já cadastrado")
            
        hashed_pw = self.get_password_hash(user_data.senha)
        db_user = Usuario(
            email=user_data.email,
            username=user_data.username,
            nome_completo=user_data.nome_completo,
            apelido=user_data.apelido,
            senha_hash=hashed_pw
        )
        self.session.add(db_user)
        # Note: A real app usually creates a default Tenant here if the user is a new "Produtor"
        # For now, let's just create the user.
        await self.session.commit()
        return db_user

    async def authenticate_user(
        self,
        login_data: LoginRequest,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> tuple[Usuario, str]:
        """
        Autentica usuário com rate limiting configurável por tenant.

        Args:
            login_data: Dados de login (email, senha)
            ip_address: IP do cliente para auditoria
            user_agent: User agent do cliente para auditoria

        Returns:
            tuple[Usuario, str]: Usuário autenticado e token de acesso

        Raises:
            HTTPException 423: Conta bloqueada temporariamente
            HTTPException 401: Credenciais inválidas
            HTTPException 403: Usuário inativo
        """
        normalized_login_email = str(login_data.email).strip().lower()
        restricted_auth = (
            settings.require_restricted_runtime_role
            or settings.rls_dev_route_sessions_enabled
        )
        auth_session = self.session
        isolated_auth_session = False
        if restricted_auth:
            from core.database import authentication_async_session_maker

            if authentication_async_session_maker is None:
                raise RuntimeError("Isolated authentication database session is not configured")
            auth_session = authentication_async_session_maker()
            isolated_auth_session = True
        auth_session.info["login_email"] = normalized_login_email
        # Before credentials are verified, the auth identity sees only the
        # requested email's attempt counter and the dedicated credential
        # function. Tenant settings and memberships are deliberately absent.
        rate_limit_svc = LoginRateLimitService(auth_session)

        try:
            bloqueado, data_desbloqueio = await rate_limit_svc.verificar_bloqueio(
                normalized_login_email
            )
            if bloqueado:
                minutos = max(1, int((data_desbloqueio - datetime.now(timezone.utc)).total_seconds() / 60))
                raise HTTPException(
                    status_code=status.HTTP_423_LOCKED,
                    detail=f"Conta bloqueada por segurança. Tente novamente em {minutos} minuto(s).",
                    headers={"Retry-After": str(minutos * 60)},
                )

            if restricted_auth:
                material = await self._read_restricted_login_material(
                    auth_session, normalized_login_email
                )
                user = self._user_from_login_material(material)
            else:
                material = (await auth_session.execute(
                    select(
                        Usuario.id.label("usuario_id"),
                        Usuario.email,
                        Usuario.username,
                        Usuario.senha_hash,
                        Usuario.is_superuser,
                        Usuario.ativo,
                    ).where(func.lower(func.trim(Usuario.email)) == normalized_login_email)
                )).mappings().one_or_none()
                user = self._user_from_login_material(material)

            if not user:
                await self._register_login_failure(rate_limit_svc, normalized_login_email, "USUARIO_NAO_ENCONTRADO", ip_address, user_agent)
                raise HTTPException(status_code=401, detail="Email ou senha incorretos")
            if not user.senha_hash:
                await self._register_login_failure(rate_limit_svc, normalized_login_email, "USUARIO_SEM_HASH", ip_address, user_agent)
                raise HTTPException(status_code=401, detail="Login via senha não habilitado para este usuário")
            if not self.verify_password(login_data.senha, user.senha_hash):
                await self._register_login_failure(rate_limit_svc, normalized_login_email, "SENHA_INVALIDA", ip_address, user_agent)
                raise HTTPException(status_code=401, detail="Email ou senha incorretos")
            if not user.ativo:
                await self._register_login_failure(rate_limit_svc, normalized_login_email, "USUARIO_INATIVO", ip_address, user_agent)
                raise HTTPException(status_code=403, detail="Usuário inativo")

            user.senha_hash = None

            # bcrypt passed: now establish the authenticated user context and
            # resolve the first active Tenant through the restricted runtime.
            self.session.info["user_id"] = user.id
            tenant_usuario_stmt = select(TenantUsuario).where(
                TenantUsuario.usuario_id == user.id,
                TenantUsuario.status == "ATIVO",
            )
            tenant_usuarios = (await self.session.execute(tenant_usuario_stmt)).scalars().all()

            tenant_rate_config = None
            if not user.is_superuser and tenant_usuarios:
                first_tenant_id = tenant_usuarios[0].tenant_id
                self.session.info["tenant_id"] = first_tenant_id
                # The membership read opened a transaction with only user_id.
                # End that read transaction so the next one installs both
                # authenticated user and Tenant context before protected SQL.
                await self.session.commit()
                if restricted_auth:
                    tenant_rate_config = await self._tenant_login_rate_config(
                        self.session, first_tenant_id
                    )
                else:
                    from core.services.configuracoes_service import ConfiguracoesService
                    tenant_rate_config = await ConfiguracoesService(
                        self.session, first_tenant_id
                    ).get_seguranca_config()

            # Apply the Tenant's policy only after bcrypt. The generic
            # pre-authentication guard remains in force for unknown emails and
            # invalid passwords; see the activation report for this unavoidable
            # difference in when personalized thresholds can take effect.
            if tenant_rate_config is not None:
                tenant_rate_limit = LoginRateLimitService(
                    auth_session, seguranca_config=tenant_rate_config
                )
                bloqueado, data_desbloqueio = await tenant_rate_limit.verificar_bloqueio(
                    normalized_login_email
                )
                if bloqueado:
                    minutos = max(1, int((data_desbloqueio - datetime.now(timezone.utc)).total_seconds() / 60))
                    raise HTTPException(
                        status_code=status.HTTP_423_LOCKED,
                        detail=f"Conta bloqueada por segurança. Tente novamente em {minutos} minuto(s).",
                        headers={"Retry-After": str(minutos * 60)},
                    )
            await rate_limit_svc.registrar_tentativa_sucesso(normalized_login_email)
        finally:
            if isolated_auth_session:
                await auth_session.close()

        # Build the dynamic token claims based on the first tenant or default structure
        # A good SaaS token only holds current "active" tenant context, not ALL tenants.
        # But our old mock injected all. Let's find first active tenant to inject as default context.
        
        default_tenant_id = None
        modulos = ["CORE"]
        fazendas_auth = []
        tenant_contexts = []
        perfil = None

        is_read_only = False
        is_demo_visitor = False
        is_demo_expired = False

        # Superadministradores não entram vinculados a nenhum tenant por padrão.
        # Eles entram no contexto de Gestão Global.
        if not user.is_superuser and tenant_usuarios:
            first_tu = tenant_usuarios[0]
            default_tenant_id = str(first_tu.tenant_id)
            self.session.info["tenant_id"] = first_tu.tenant_id
            
            # Fetch profile and tenant to compute role & demo constraints
            perfil_stmt = select(PerfilAcesso).where(PerfilAcesso.id == first_tu.perfil_id)
            perfil = (await self.session.execute(perfil_stmt)).scalar_one_or_none()
            tenant_obj = await self.session.get(Tenant, first_tu.tenant_id)
            role_name = "owner" if first_tu.is_owner else (
                normalize_tenant_role(perfil.nome) if perfil else "operador"
            )
            is_read_only = (not first_tu.is_owner) and is_read_only_profile(perfil)
            is_demo_visitor = is_read_only and (
                is_demo_tenant(tenant_obj) or bool(perfil and getattr(perfil, "is_demo_profile", False))
            )
            is_demo_expired = bool(
                is_demo_visitor and first_tu.data_validade_acesso and first_tu.data_validade_acesso < date.today()
            )
            
            # Fetch allowed unidades produtivas
            fazenda_usu_stmt = select(FazendaUsuario).where(
                FazendaUsuario.usuario_id == user.id,
                FazendaUsuario.tenant_id == first_tu.tenant_id
            )
            f_usuarios = (await self.session.execute(fazenda_usu_stmt)).scalars().all()
            for fu in f_usuarios:
                fazendas_auth.append({"id": str(fu.unidade_produtiva_id), "role": role_name})

            # Fetch subscription info for the tenant
            assin_stmt = (
                select(PlanoAssinatura.modulos_inclusos, PlanoAssinatura.plan_tier,
                       PlanoAssinatura.max_fazendas, AssinaturaTenant.usuarios_contratados)
                .join(AssinaturaTenant, AssinaturaTenant.plano_id == PlanoAssinatura.id)
                .where(
                    AssinaturaTenant.tenant_id == first_tu.tenant_id,
                    AssinaturaTenant.status.in_(["ATIVA", "TRIAL"]),
                )
                .limit(1)
            )
            assin_row = (await self.session.execute(assin_stmt)).first()
            tenant_modules = (assin_row[0] if assin_row and assin_row[0] else ["CORE"])
            tenant_tier = (assin_row[1] if assin_row and assin_row[1] else "BASICO")
            tenant_max_fazendas = (assin_row[2] if assin_row and assin_row[2] else 1)
            tenant_max_usuarios = (assin_row[3] if assin_row and assin_row[3] else 2)

            # All unidades produtivas the user can access
            faz_stmt = select(Fazenda.id, Fazenda.nome).where(
                Fazenda.tenant_id == first_tu.tenant_id,
                Fazenda.ativo == True,
            )
            faz_rows = (await self.session.execute(faz_stmt)).all()
            all_fazendas = [{"id": str(r[0]), "nome": r[1]} for r in faz_rows]

            tenant_contexts = [{
                "id": str(first_tu.tenant_id),
                "nome": "default",
                "modules": tenant_modules,
                "plan_tier": tenant_tier,
                "max_fazendas": tenant_max_fazendas,
                "max_usuarios": tenant_max_usuarios,
                "fazendas": all_fazendas,
            }]
            modulos = list(set(modulos) | set(tenant_modules))
            for faz in all_fazendas:
                if not any(f["id"] == faz["id"] for f in fazendas_auth):
                    fazendas_auth.append({"id": faz["id"], "role": role_name})

        # plan_tier do tenant (ou BASICO)
        plan_tier = tenant_contexts[0]["plan_tier"] if tenant_contexts else "BASICO"

        # Role do tenant (owner/admin) para acesso implícito
        tenant_role = (
            "owner"
            if (not user.is_superuser and tenant_usuarios and tenant_usuarios[0].is_owner)
            else (normalize_tenant_role(perfil.nome) if (not user.is_superuser and perfil) else None)
        )

        # Generate token payload
        claims = {
            "sub": str(user.id),
            "tenant_id": default_tenant_id,
            "role": tenant_role,
            "modules": modulos,
            "fazendas_auth": fazendas_auth,
            "tenant_contexts": tenant_contexts,
            "is_superuser": user.is_superuser,
            "plan_tier": plan_tier,
            "session_required": True,
            "is_read_only": is_read_only,
            "is_demo_visitor": is_demo_visitor,
            "demo_expired": is_demo_expired,
        }
        
        access_token = self.create_access_token(data=claims)
        
        from core.models.sessao import SessaoAtiva
        import hashlib

        if default_tenant_id and not user.is_superuser:
            await self._verificar_disponibilidade_licenca_simultanea(
                tenant_id=uuid.UUID(default_tenant_id),
                usuario_id=user.id,
                is_demo_visitor=is_demo_visitor,
                is_demo_expired=is_demo_expired,
            )

        token_hash = hashlib.sha256(access_token.encode()).hexdigest()
        agora = datetime.now(timezone.utc)
        idle_minutes = await get_session_idle_minutes(self.session)
        if is_demo_visitor and not is_demo_expired:
            demo_cfg = await get_demo_saas_config(self.session)
            idle_minutes = min(idle_minutes, demo_cfg.timeout_inatividade_minutos)

        self.session.add(SessaoAtiva(
            tenant_id=uuid.UUID(default_tenant_id) if default_tenant_id else None,
            usuario_id=user.id,
            token_hash=token_hash,
            ip_address=ip_address,
            user_agent=user_agent,
            inicio=agora,
            ultimo_heartbeat=agora,
            expira_em=session_expiration(agora, idle_minutes),
            status="ATIVA",
        ))
        await self.session.commit()
        
        return user, access_token

    async def _verificar_disponibilidade_licenca_simultanea(
        self,
        tenant_id: uuid.UUID,
        usuario_id: uuid.UUID,
        escopo_produto: str = "web",
        is_demo_visitor: bool = False,
        is_demo_expired: bool = False,
    ) -> None:
        """
        Verifica se há licença de acesso simultâneo disponível para o tenant antes de criar
        uma nova sessão ativa. Limpa sessões expiradas e encerra sessões anteriores do mesmo
        usuário no mesmo tenant para permitir reconexão sem autotravamento.

        O acesso quando utilizado no aplicativo Campo (escopo_produto='campo') é isento
        e não é contabilizado para o acesso simultâneo. Em tenants de demonstração,
        contabiliza exclusivamente visitantes ativos com perfil Demonstração.

        Args:
            tenant_id: ID do tenant alvo do login/troca de contexto.
            usuario_id: ID do usuário autenticado.
            escopo_produto: Escopo do cliente ('web' ou 'campo').
            is_demo_visitor: Indica se o usuário logando usa o perfil de demonstração.
            is_demo_expired: Indica se o período de demonstração do visitante já venceu.

        Raises:
            HTTPException 403/429: Quando todas as licenças simultâneas estão em uso.
        """
        if str(escopo_produto).strip().lower() == "campo":
            return

        from core.models.sessao import SessaoAtiva
        from sqlalchemy import or_

        agora = datetime.now(timezone.utc)

        # 1. Expirar sessões vencidas do tenant
        await self.session.execute(
            update(SessaoAtiva)
            .where(
                SessaoAtiva.tenant_id == tenant_id,
                SessaoAtiva.status == "ATIVA",
                SessaoAtiva.expira_em <= agora,
            )
            .values(status="EXPIRADA")
        )

        # 2. Encerrar eventual sessão ativa anterior do próprio usuário no mesmo tenant
        await self.session.execute(
            update(SessaoAtiva)
            .where(
                SessaoAtiva.tenant_id == tenant_id,
                SessaoAtiva.usuario_id == usuario_id,
                SessaoAtiva.status == "ATIVA",
            )
            .values(status="ENCERRADA")
        )

        tenant_obj = await self.session.get(Tenant, tenant_id)
        if is_demo_tenant(tenant_obj):
            if not is_demo_visitor or is_demo_expired:
                return

            demo_cfg = await get_demo_saas_config(self.session)
            limite_demo = (
                getattr(tenant_obj, "demo_max_sessoes_simultaneas", None)
                or demo_cfg.max_sessoes_simultaneas
            )
            hoje = date.today()
            demo_count_stmt = (
                select(func.count(func.distinct(SessaoAtiva.id)))
                .join(
                    TenantUsuario,
                    (TenantUsuario.tenant_id == SessaoAtiva.tenant_id)
                    & (TenantUsuario.usuario_id == SessaoAtiva.usuario_id),
                )
                .outerjoin(PerfilAcesso, PerfilAcesso.id == TenantUsuario.perfil_id)
                .where(
                    SessaoAtiva.tenant_id == tenant_id,
                    SessaoAtiva.status == "ATIVA",
                    SessaoAtiva.expira_em > agora,
                    TenantUsuario.is_owner == False,
                    or_(
                        PerfilAcesso.is_read_only == True,
                        PerfilAcesso.is_demo_profile == True,
                    ),
                    or_(
                        TenantUsuario.data_validade_acesso.is_(None),
                        TenantUsuario.data_validade_acesso >= hoje,
                    ),
                )
            )
            sessoes_demo_ativas = (await self.session.execute(demo_count_stmt)).scalar_one() or 0
            if sessoes_demo_ativas >= limite_demo:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=demo_cfg.mensagem_limite_simultaneo,
                    headers={"X-Error-Code": "DEMO_CONCURRENCY_LIMIT"},
                )
            return

        # 3. Consultar limite de acessos simultâneos contratados na assinatura do tenant
        assin_stmt = (
            select(
                AssinaturaTenant.usuarios_contratados,
                PlanoAssinatura.limite_usuarios_maximo,
                PlanoAssinatura.limite_usuarios_minimo,
            )
            .join(PlanoAssinatura, AssinaturaTenant.plano_id == PlanoAssinatura.id)
            .where(
                AssinaturaTenant.tenant_id == tenant_id,
                AssinaturaTenant.status.in_(["ATIVA", "TRIAL", "PENDENTE_PAGAMENTO"]),
            )
            .limit(1)
        )
        assin_row = (await self.session.execute(assin_stmt)).first()
        if not assin_row:
            return

        limite_simultaneo = assin_row[0] or assin_row[1] or assin_row[2]
        if not limite_simultaneo or limite_simultaneo <= 0:
            return

        # 4. Contar sessões simultâneas ativas no tenant
        count_stmt = select(func.count(SessaoAtiva.id)).where(
            SessaoAtiva.tenant_id == tenant_id,
            SessaoAtiva.status == "ATIVA",
            SessaoAtiva.expira_em > agora,
        )
        sessoes_ativas = (await self.session.execute(count_stmt)).scalar_one() or 0

        if sessoes_ativas >= limite_simultaneo:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Não há licença de acesso simultâneo disponível no momento "
                    f"({sessoes_ativas}/{limite_simultaneo} acessos simultâneos em uso). "
                    "Aguarde a liberação de um acesso ou contrate mais acessos simultâneos para o seu pacote."
                ),
            )

    async def generate_token_for_tenant(
        self,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> str:
        """
        Gera um novo JWT com contexto do tenant selecionado.
        Usado pelo endpoint /auth/switch-tenant.
        """
        user = (await self.session.execute(select(Usuario).where(Usuario.id == user_id))).scalar_one_or_none()
        if not user or not user.ativo:
            raise HTTPException(status_code=403, detail="Usuário inativo")

        first_tu = (await self.session.execute(
            select(TenantUsuario).where(
                TenantUsuario.tenant_id == tenant_id,
                TenantUsuario.usuario_id == user_id,
                TenantUsuario.status == "ATIVO"
            )
        )).scalar_one_or_none()
        if not first_tu:
            raise HTTPException(status_code=403, detail="Sem acesso ao tenant")

        perfil = None
        if first_tu.perfil_id:
            perfil = (await self.session.execute(
                select(PerfilAcesso).where(PerfilAcesso.id == first_tu.perfil_id)
            )).scalar_one_or_none()
        tenant_obj = await self.session.get(Tenant, tenant_id)
        role_name = "owner" if first_tu.is_owner else (
            normalize_tenant_role(perfil.nome) if perfil else "operador"
        )
        is_read_only = (not first_tu.is_owner) and is_read_only_profile(perfil)
        is_demo_visitor = is_read_only and (
            is_demo_tenant(tenant_obj) or bool(perfil and getattr(perfil, "is_demo_profile", False))
        )
        is_demo_expired = bool(
            is_demo_visitor and first_tu.data_validade_acesso and first_tu.data_validade_acesso < date.today()
        )

        modulos: list[str] = ["CORE"]
        fazendas_auth: list[dict] = []
        tenant_contexts: list[dict] = []

        # Fetch subscription info for the tenant
        assin_row = (await self.session.execute(
            select(PlanoAssinatura.modulos_inclusos, PlanoAssinatura.plan_tier,
                   PlanoAssinatura.max_fazendas, AssinaturaTenant.usuarios_contratados)
            .join(AssinaturaTenant, AssinaturaTenant.plano_id == PlanoAssinatura.id)
            .where(
                AssinaturaTenant.tenant_id == tenant_id,
                AssinaturaTenant.status.in_(["ATIVA", "TRIAL"]),
            )
            .limit(1)
        )).first()

        tenant_modules = (assin_row[0] if assin_row and assin_row[0] else ["CORE"])
        tenant_tier = (assin_row[1] if assin_row and assin_row[1] else "BASICO")
        tenant_max_fazendas = (assin_row[2] if assin_row and assin_row[2] else 1)
        tenant_max_usuarios = (assin_row[3] if assin_row and assin_row[3] else 2)

        faz_rows = (await self.session.execute(
            select(Fazenda.id, Fazenda.nome).where(
                Fazenda.tenant_id == tenant_id,
                Fazenda.ativo == True,
            )
        )).all()
        all_fazendas = [{"id": str(r[0]), "nome": r[1]} for r in faz_rows]

        tenant_contexts = [{
            "id": str(tenant_id),
            "nome": "default",
            "modules": tenant_modules,
            "plan_tier": tenant_tier,
            "max_fazendas": tenant_max_fazendas,
            "max_usuarios": tenant_max_usuarios,
            "fazendas": all_fazendas,
        }]
        modulos = list(set(modulos) | set(tenant_modules))
        fazendas_auth = [{"id": faz["id"], "role": role_name} for faz in all_fazendas]

        plan_tier = tenant_tier

        claims = {
            "sub": str(user_id),
            "tenant_id": str(tenant_id),
            "role": role_name,
            "modules": modulos,
            "fazendas_auth": fazendas_auth,
            "tenant_contexts": tenant_contexts,
            "is_superuser": user.is_superuser,
            "plan_tier": plan_tier,
            "session_required": True,
            "is_read_only": is_read_only,
            "is_demo_visitor": is_demo_visitor,
            "demo_expired": is_demo_expired,
        }

        access_token = self.create_access_token(data=claims)

        if not user.is_superuser:
            await self._verificar_disponibilidade_licenca_simultanea(
                tenant_id=tenant_id,
                usuario_id=user_id,
                is_demo_visitor=is_demo_visitor,
                is_demo_expired=is_demo_expired,
            )

        # Registrar nova sessão
        from core.models.sessao import SessaoAtiva
        import hashlib
        token_hash = hashlib.sha256(access_token.encode()).hexdigest()
        agora = datetime.now(timezone.utc)
        idle_minutes = await get_session_idle_minutes(self.session)
        if is_demo_visitor and not is_demo_expired:
            demo_cfg = await get_demo_saas_config(self.session)
            idle_minutes = min(idle_minutes, demo_cfg.timeout_inatividade_minutos)
        self.session.add(SessaoAtiva(
            tenant_id=tenant_id,
            usuario_id=user_id,
            token_hash=token_hash,
            ip_address=ip_address,
            user_agent=user_agent,
            inicio=agora,
            ultimo_heartbeat=agora,
            expira_em=session_expiration(agora, idle_minutes),
            status="ATIVA",
        ))
        await self.session.commit()
        return access_token

    async def get_user_me(self, user_id: uuid.UUID, claims: dict | None = None) -> UsuarioMeResponse:
        claims = claims or {}
        if claims.get("impersonating"):
            impersonator_email = claims.get("impersonator_email")
            admin_obj = None

            # 1. Tenta localizar em AdminUser por ID
            admin_obj = (await self.session.execute(
                select(AdminUser).where(AdminUser.id == user_id)
            )).scalar_one_or_none()

            # 2. Se não encontrou por ID, tenta por email em AdminUser
            if not admin_obj and impersonator_email:
                admin_obj = (await self.session.execute(
                    select(AdminUser).where(func.lower(AdminUser.email) == str(impersonator_email).strip().lower())
                )).scalar_one_or_none()

            # 3. Se ainda não encontrou, busca na tabela Usuario (pois o admin pode ser um Usuario global)
            usuario_obj = None
            if not admin_obj:
                usuario_obj = (await self.session.execute(
                    select(Usuario).where(Usuario.id == user_id)
                )).scalar_one_or_none()
                if not usuario_obj and impersonator_email:
                    usuario_obj = (await self.session.execute(
                        select(Usuario).where(func.lower(Usuario.email) == str(impersonator_email).strip().lower())
                    )).scalar_one_or_none()

            # Identidade resolvida do operador (resiliente, nunca quebra com 404)
            op_id = admin_obj.id if admin_obj else (usuario_obj.id if usuario_obj else user_id)
            op_email = admin_obj.email if admin_obj else (usuario_obj.email if usuario_obj else (impersonator_email or "suporte@deepfarms.com"))
            op_nome = admin_obj.nome if admin_obj else (usuario_obj.nome_completo if (usuario_obj and usuario_obj.nome_completo) else (usuario_obj.username if usuario_obj else (claims.get("impersonator_nome") or op_email.split("@")[0])))
            op_avatar = admin_obj.avatar_url if admin_obj else (usuario_obj.foto_perfil_url if usuario_obj else None)
            op_role = admin_obj.role if admin_obj else (claims.get("backoffice_role") or "super_admin")
            op_ativo = admin_obj.ativo if admin_obj else (usuario_obj.ativo if usuario_obj else True)
            op_created_at = admin_obj.created_at if admin_obj else (usuario_obj.created_at if usuario_obj else datetime.now(timezone.utc))

            tenant_id_str = claims.get("tenant_id")
            tenants_response = []
            if tenant_id_str:
                tenant_id = uuid.UUID(tenant_id_str)
                # Ativa contexto do tenant para o Postgres RLS liberar a leitura
                from core.dependencies import _activate_session_tenant
                await _activate_session_tenant(self.session, tenant_id)

                t_stmt = select(Tenant).where(Tenant.id == tenant_id)
                tenant = (await self.session.execute(t_stmt)).scalar_one_or_none()
                if tenant:
                    f_stmt = select(Fazenda).where(Fazenda.tenant_id == tenant.id, Fazenda.ativo == True)
                    fazendas_list = (await self.session.execute(f_stmt)).scalars().all()
                    fazendas_resp = [
                        FazendaAcessoResponse(unidade_produtiva_id=f.id, nome=f.nome)
                        for f in fazendas_list
                    ]

                    plan_stmt = (
                        select(
                            PlanoAssinatura.plan_tier,
                            PlanoAssinatura.max_fazendas,
                            PlanoAssinatura.modulos_inclusos,
                            AssinaturaTenant.usuarios_contratados,
                        )
                        .join(AssinaturaTenant, AssinaturaTenant.plano_id == PlanoAssinatura.id)
                        .where(
                            AssinaturaTenant.tenant_id == tenant.id,
                            AssinaturaTenant.status.in_(["ATIVA", "PENDENTE_PAGAMENTO", "TRIAL"]),
                        )
                    )
                    plan_rows = (await self.session.execute(plan_stmt)).all()
                    if plan_rows:
                        t_plan_tier = plan_rows[0][0] or "BASICO"
                        t_max_fazendas = max((r[1] or 1) for r in plan_rows)
                        t_modulos = list({m for r in plan_rows if r[2] for m in r[2]})
                        t_max_usuarios = max((r[3] or 2) for r in plan_rows)
                    else:
                        t_plan_tier = claims.get("plan_tier") or "BASICO"
                        t_max_fazendas = 1
                        t_modulos = claims.get("modules") or ["CORE"]
                        t_max_usuarios = 2

                    tenants_response.append(TenantAcessoResponse(
                        tenant_id=tenant.id,
                        nome_tenant=tenant.nome,
                        is_owner=True,
                        ativo=tenant.ativo,
                        activation_pending=bool(tenant.activation_token),
                        perfil=PerfilSimplesResponse(id=uuid.uuid4(), nome="Owner (Suporte)", permissoes={}),
                        fazendas=fazendas_resp,
                        plan_tier=t_plan_tier,
                        max_fazendas=t_max_fazendas,
                        max_usuarios=t_max_usuarios,
                        modulos=t_modulos,
                    ))

            impersonation_info = {
                "active": True,
                "mode": claims.get("impersonation_mode", "READ_ONLY"),
                "impersonation_id": claims.get("impersonation_id"),
                "tenant_id": tenant_id_str,
                "tenant_nome": tenants_response[0].nome_tenant if tenants_response else "",
                "admin_email": op_email,
                "admin_nome": op_nome,
            }

            return UsuarioMeResponse(
                id=op_id,
                email=op_email,
                username=op_email.split("@")[0],
                nome_completo=op_nome,
                apelido=op_nome.split()[0] if op_nome else "Suporte",
                foto_perfil_url=op_avatar,
                is_superuser=True,
                navigation_mode="SIDEBAR",
                tenants=tenants_response,
                ativo=op_ativo,
                nome=op_nome,
                email_verificado=True,
                emailVerificado=True,
                created_at=op_created_at,
                createdAt=op_created_at,
                impersonation=impersonation_info,
                backoffice_role=op_role,
            )

        stmt = select(Usuario).where(Usuario.id == user_id)
        user = (await self.session.execute(stmt)).scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="Usuário não encontrado")
            
        # Get all tenants
        tu_stmt = select(TenantUsuario).where(TenantUsuario.usuario_id == user.id, TenantUsuario.status == "ATIVO")
        tenant_links = (await self.session.execute(tu_stmt)).scalars().all()
        
        tenants_response = []
        for tu in tenant_links:
            # get tenant
            t_stmt = select(Tenant).where(Tenant.id == tu.tenant_id)
            tenant = (await self.session.execute(t_stmt)).scalar_one()
            
            # get perfil
            perfil = None
            if tu.perfil_id:
                p_stmt = select(PerfilAcesso).where(PerfilAcesso.id == tu.perfil_id)
                perfil = (await self.session.execute(p_stmt)).scalar_one_or_none()
            
            # get fazendas
            fu_stmt = select(FazendaUsuario).where(FazendaUsuario.usuario_id == user.id, FazendaUsuario.tenant_id == tenant.id)
            f_links = (await self.session.execute(fu_stmt)).scalars().all()
            fazendas_resp = []
            for fl in f_links:
                f_stmt = select(Fazenda).where(Fazenda.id == fl.unidade_produtiva_id)
                fazenda_obj = (await self.session.execute(f_stmt)).scalar_one_or_none()
                if fazenda_obj:
                    fazendas_resp.append(FazendaAcessoResponse(unidade_produtiva_id=fazenda_obj.id, nome=fazenda_obj.nome))
                    
            # Query plan info — agrega todas as assinaturas ativas do tenant (union de módulos)
            plan_stmt = (
                select(
                    PlanoAssinatura.plan_tier,
                    PlanoAssinatura.max_fazendas,
                    PlanoAssinatura.modulos_inclusos,
                    AssinaturaTenant.usuarios_contratados,
                )
                .join(AssinaturaTenant, AssinaturaTenant.plano_id == PlanoAssinatura.id)
                .where(
                    AssinaturaTenant.tenant_id == tenant.id,
                    AssinaturaTenant.status.in_(["ATIVA", "PENDENTE_PAGAMENTO", "TRIAL"]),
                )
            )
            plan_rows = (await self.session.execute(plan_stmt)).all()
            if plan_rows:
                t_plan_tier = plan_rows[0][0] or "BASICO"
                t_max_fazendas = max((r[1] or 1) for r in plan_rows)
                t_modulos = list({m for r in plan_rows if r[2] for m in r[2]})
                t_max_usuarios = max((r[3] or 2) for r in plan_rows)
            else:
                t_plan_tier = "BASICO"
                t_max_fazendas = 1
                t_modulos = ["CORE"]
                t_max_usuarios = 2

            tu_validade = tu.data_validade_acesso
            tu_is_demo_tenant = is_demo_tenant(tenant)
            tu_is_demo_visitor = (not tu.is_owner) and (
                tu_is_demo_tenant or is_read_only_profile(perfil)
            )
            tu_demo_expired = bool(
                tu_is_demo_visitor and tu_validade and tu_validade < date.today()
            )
            tu_dias_restantes = (
                (tu_validade - date.today()).days
                if (tu_is_demo_visitor and tu_validade)
                else None
            )

            tenants_response.append(TenantAcessoResponse(
                tenant_id=tenant.id,
                nome_tenant=tenant.nome,
                is_owner=tu.is_owner,
                ativo=tenant.ativo,
                activation_pending=bool(tenant.activation_token),
                perfil=(
                    PerfilSimplesResponse(
                        id=perfil.id,
                        nome=perfil.nome,
                        permissoes=perfil.permissoes,
                        is_read_only=bool(getattr(perfil, "is_read_only", False)),
                        is_demo_profile=bool(getattr(perfil, "is_demo_profile", False)),
                    )
                    if perfil
                    else None
                ),
                fazendas=fazendas_resp,
                plan_tier=t_plan_tier,
                max_fazendas=t_max_fazendas,
                max_usuarios=t_max_usuarios,
                modulos=t_modulos,
                is_demo=tu_is_demo_tenant,
                data_validade_acesso=tu_validade,
                demo_expired=tu_demo_expired,
                demo_dias_restantes=tu_dias_restantes,
                demo_prorrogacoes_count=int(getattr(tu, "demo_prorrogacoes_count", 0) or 0),
            ))

        display_name = user.nome_completo or user.apelido or user.username
        response = UsuarioMeResponse(
            id=user.id,
            email=user.email,
            username=user.username,
            cpf=user.cpf,
            telefone=user.telefone,
            nome_completo=user.nome_completo,
            apelido=user.apelido,
            foto_perfil_url=user.foto_perfil_url,
            is_superuser=user.is_superuser,
            navigation_mode=user.navigation_mode,
            tenants=tenants_response,
            ativo=user.ativo,
            nome=display_name,
            email_verificado=True,
            emailVerificado=True,
            created_at=user.created_at,
            createdAt=user.created_at,
        )
        return response

    async def update_navigation_preference(self, user_id: uuid.UUID, navigation_mode: str) -> None:
        stmt = select(Usuario).where(Usuario.id == user_id)
        user = (await self.session.execute(stmt)).scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="Usuário não encontrado")

        user.navigation_mode = navigation_mode
        self.session.add(user)
        await self.session.commit()

    # ==================== CRIAÇÃO DE NOVA ASSINATURA ====================

    async def create_tenant_for_user(
        self,
        user_id: uuid.UUID,
        nome: str,
        plano_id: uuid.UUID,
        ciclo: str = "MENSAL",
        cpf_cnpj: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> dict:
        """
        Cria um novo tenant (assinatura/produtor) para um usuário já autenticado.
        Retorna um novo JWT no contexto do tenant recém-criado.
        """
        # Verificar plano
        plano = (await self.session.execute(
            select(PlanoAssinatura).where(PlanoAssinatura.id == plano_id, PlanoAssinatura.ativo == True)
        )).scalar_one_or_none()
        if not plano:
            raise HTTPException(status_code=404, detail="Plano não encontrado")

        documento_tenant = normalizar_documento_opcional(cpf_cnpj)
        if documento_tenant and not validar_cpf_ou_cnpj(documento_tenant):
            raise HTTPException(status_code=400, detail="CPF ou CNPJ inválido")

        agora = datetime.now(timezone.utc)
        is_trial = not plano.is_free and plano.tem_trial
        status_assin = "ATIVA" if plano.is_free else "TRIAL" if is_trial else "PENDENTE_PAGAMENTO"
        slug_base = _slugify_tenant_name(nome)
        slug = slug_base
        suffix = 2
        while (
            await self.session.execute(select(Tenant.id).where(Tenant.slug == slug))
        ).scalar_one_or_none():
            slug = f"{slug_base}-{suffix}"
            suffix += 1

        # 1. Criar Tenant
        tenant = Tenant(
            nome=nome,
            documento=documento_tenant,
            slug=slug,
            ativo=status_assin in ("ATIVA", "TRIAL"),
        )
        self.session.add(tenant)
        await self.session.flush()  # gera tenant.id

        # 2. Vincular usuário como owner
        tu = TenantUsuario(
            tenant_id=tenant.id,
            usuario_id=user_id,
            is_owner=True,
            status="ATIVO",
        )
        self.session.add(tu)

        # 3. Criar assinatura
        if plano.is_free:
            trial_expira_em = None
            primeiro_vencimento = None
        else:
            trial_expira_em = agora + timedelta(days=plano.dias_trial) if is_trial else None
            # Vencimento = dia seguinte ao fim do trial
            primeiro_vencimento = (trial_expira_em + timedelta(days=1)).date() if trial_expira_em else None

        assin = AssinaturaTenant(
            tenant_id=tenant.id,
            plano_id=plano.id,
            tipo_assinatura="TENANT",
            ciclo_pagamento=ciclo,
            status=status_assin,
            usuarios_contratados=plano.limite_usuarios_minimo or 1,
            data_inicio=agora,
            data_proxima_renovacao=trial_expira_em,
        )
        self.session.add(assin)
        await self.session.flush()  # gera assin.id

        # 6. Criar Fatura (APENAS se plano pago e tem trial)
        if not plano.is_free and is_trial and primeiro_vencimento:
            from decimal import Decimal
            valor_fatura = Decimal(str(plano.preco_anual)) if ciclo == "ANUAL" else Decimal(str(plano.preco_mensal))
            vencimento_datetime = datetime.combine(primeiro_vencimento, datetime.min.time(), tzinfo=timezone.utc)
            fatura = Fatura(
                tenant_id=tenant.id,
                assinatura_id=assin.id,
                valor=valor_fatura,
                data_vencimento=vencimento_datetime,
                status="ABERTA",
            )
            self.session.add(fatura)
            logger.info(f"Fatura criada para assinatura {assin.id}: R${valor_fatura} vence em {primeiro_vencimento}")

        await self.session.commit()

        # 7. Buscar usuário para email
        usuario = (await self.session.execute(select(Usuario).where(Usuario.id == user_id))).scalar_one_or_none()

        # 8. Enviar email com aviso de trial (background, sem bloquear)
        if usuario and not plano.is_free and is_trial:
            from core.services.email_service import email_service
            try:
                dias_trial = plano.dias_trial
                await email_service.send_trial_notice(
                    email=usuario.email,
                    nome=usuario.nome_completo or usuario.username,
                    nome_produtor=nome,
                    nome_plano=plano.nome,
                    dias_trial=dias_trial,
                    data_vencimento=primeiro_vencimento,
                    tenant_id=tenant.id,
                )
                logger.info(f"Email de trial enviado para {usuario.email}")
            except Exception as e:
                logger.error(f"Erro ao enviar email de trial: {e}")

        # 9. Gerar token no contexto do novo tenant
        token = await self.generate_token_for_tenant(user_id, tenant.id, ip_address, user_agent)

        return {
            "access_token": token,
            "tenant_id": tenant.id,
            "nome_tenant": nome,
            "is_trial": is_trial,
            "trial_expira_em": trial_expira_em,
            "data_primeiro_vencimento": primeiro_vencimento,
        }

    # ==================== RECUPERAÇÃO DE SENHA ====================

    async def create_password_reset_token(self, email: str, ip_address: Optional[str] = None) -> dict:
        """
        Cria um token de recuperação de senha e envia por e-mail.
        
        Args:
            email: E-mail do usuário
            ip_address: IP de origem da solicitação
            
        Returns:
            dict: Informações sobre o resultado da operação
        """
        from core.services.email_service import email_service

        # Busca usuário pelo email
        normalized_email = email.strip().lower()
        stmt = select(Usuario).where(func.lower(Usuario.email) == normalized_email)
        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()

        # Sempre retorna sucesso para evitar enumeração de usuários
        if not user:
            return {
                "sucesso": True,
                "mensagem": "Se o e-mail estiver cadastrado, você receberá as instruções para recuperação de senha.",
                "email": None
            }

        # Invalida tokens anteriores não utilizados deste usuário
        invalidate_stmt = select(TokenRecuperacaoSenha).where(
            TokenRecuperacaoSenha.usuario_id == user.id,
            TokenRecuperacaoSenha.utilizado == False
        )
        invalidate_result = await self.session.execute(invalidate_stmt)
        tokens_anteriores = invalidate_result.scalars().all()
        
        for token in tokens_anteriores:
            token.utilizado = True  # Marca como utilizado para invalidar

        # Gera token seguro
        token_value = secrets.token_urlsafe(48)  # 64 caracteres
        data_expiracao = datetime.now(timezone.utc) + timedelta(hours=1)

        # Cria registro do token
        token_record = TokenRecuperacaoSenha(
            usuario_id=user.id,
            token=token_value,
            data_expiracao=data_expiracao,
            ip_origem=ip_address
        )
        
        self.session.add(token_record)
        await self.session.commit()

        # Obtém tenant_id do usuário para configuração SMTP correta
        tenant_id = None
        tenant_usuario_stmt = select(TenantUsuario).where(
            TenantUsuario.usuario_id == user.id,
            TenantUsuario.status == "ATIVO"
        ).limit(1)
        tenant_usuario_result = await self.session.execute(tenant_usuario_stmt)
        tenant_usuario = tenant_usuario_result.scalar_one_or_none()
        
        if tenant_usuario:
            tenant_id = tenant_usuario.tenant_id

        # Envia e-mail de recuperação
        nome_usuario = user.nome_completo or user.username
        try:
            await email_service.send_password_recovery(
                email=user.email,
                nome_usuario=nome_usuario,
                token=token_value,
                tenant_id=tenant_id
            )
        except SMTPPlatformConfigNotFoundError as exc:
            logger.error(
                f"Configuração SMTP global não encontrada para recuperação de senha: {exc}"
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Configuração SMTP da plataforma não encontrada.",
            ) from exc
        except Exception as exc:
            logger.error(
                f"Falha no envio do e-mail de recuperação para {user.email}: {exc}"
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Falha ao enviar o e-mail de recuperação. Verifique a configuração SMTP."
            ) from exc

        return {
            "sucesso": True,
            "mensagem": "Se o e-mail estiver cadastrado, você receberá as instruções para recuperação de senha.",
            "email": None
        }

    async def verify_reset_token(self, token: str) -> dict:
        """
        Verifica se um token de recuperação é válido.
        
        Args:
            token: Token de recuperação
            
        Returns:
            dict: Informações sobre a validade do token
        """
        # Busca token não utilizado
        stmt = select(TokenRecuperacaoSenha).where(
            TokenRecuperacaoSenha.token == token,
            TokenRecuperacaoSenha.utilizado == False
        )
        result = await self.session.execute(stmt)
        token_record = result.scalar_one_or_none()
        if not token_record:
            return {
                "valido": False,
                "mensagem": "Token inválido ou já utilizado.",
                "email": None,
                "expira_em": None
            }

        # Verifica se expirou
        agora = datetime.now(timezone.utc)
        if agora > token_record.data_expiracao:
            return {
                "valido": False,
                "mensagem": "Token expirado. Solicite um novo link de recuperação.",
                "email": None,
                "expira_em": None
            }

        # Busca informações do usuário
        usuario = await self.session.get(Usuario, token_record.usuario_id)
        if not usuario:
            return {
                "valido": False,
                "mensagem": "Usuário não encontrado.",
                "email": None,
                "expira_em": None
            }

        minutos_restantes = int((token_record.data_expiracao - agora).total_seconds() / 60)
        
        return {
            "valido": True,
            "mensagem": "Token válido.",
            "email": usuario.email,
            "expira_em": f"{minutos_restantes} minutos"
        }

    async def reset_password(self, token: str, nova_senha: str, ip_address: Optional[str] = None) -> dict:
        """
        Redefine a senha do usuário usando um token válido.
        
        Args:
            token: Token de recuperação
            nova_senha: Nova senha
            ip_address: IP de origem da solicitação
            
        Returns:
            dict: Resultado da operação
        """
        # Busca token não utilizado
        stmt = select(TokenRecuperacaoSenha).where(
            TokenRecuperacaoSenha.token == token,
            TokenRecuperacaoSenha.utilizado == False
        )
        result = await self.session.execute(stmt)
        token_record = result.scalar_one_or_none()

        if not token_record:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token inválido ou já utilizado."
            )

        # Verifica se expirou
        agora = datetime.now(timezone.utc)
        if agora > token_record.data_expiracao:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token expirado. Solicite um novo link de recuperação."
            )

        # Busca usuário
        usuario = await self.session.get(Usuario, token_record.usuario_id)
        if not usuario:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário não encontrado."
            )

        # Verifica se a senha é diferente da atual
        if usuario.senha_hash and self.verify_password(nova_senha, usuario.senha_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A nova senha deve ser diferente da senha atual."
            )

        # Atualiza a senha
        usuario.senha_hash = self.get_password_hash(nova_senha)
        usuario.updated_at = datetime.now(timezone.utc)

        # Marca o token como utilizado
        token_record.utilizado = True
        token_record.data_utilizacao = agora
        token_record.ip_utilizacao = ip_address

        await self.session.commit()

        return {
            "sucesso": True,
            "mensagem": "Senha redefinida com sucesso. Você já pode fazer login com a nova senha."
        }
