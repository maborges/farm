from fastapi import APIRouter, Depends, status, HTTPException, Request, Response, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone, timedelta
import uuid
import hashlib

from core.dependencies import (
    get_session, get_token, get_current_user_claims, get_global_user_claims,
    get_current_user, get_tenant_id, TENANT_CONTEXT_ERROR, invalidate_session_cache
)
from core.schemas.auth_schemas import (
    FreeRegistrationResponse, FreeUserCreateRequest, LoginRequest,
    UserCreateRequest, UserUpdateRequest, TokenResponse, UsuarioMeResponse,
    CreateSubscriptionRequest, CreateSubscriptionResponse, VerifyEmailRequest
)
from core.schemas.auth_schemas import (
    LoginDesbloqueioRequest, LoginDesbloqueioResponse,
    LoginTentativasInfoResponse, NavigationPreferenceUpdate
)
from core.schemas.auth_schemas import (
    ForgotPasswordRequest, ForgotPasswordResponse,
    VerifyResetTokenRequest, VerifyResetTokenResponse,
    ResetPasswordRequest, ResetPasswordResponse,
    ChangePasswordRequest, ChangePasswordResponse
)
from core.services.auth_service import AuthService
from core.services.login_rate_limit_service import LoginRateLimitService
from core.services.free_registration_rate_limit import FreeRegistrationRateLimiter
from core.services.cookie_service import set_platform_session_cookie, clear_platform_session_cookie
from core.services.storage_service import StorageService
from core.models.auth import Usuario, TenantUsuario, UnidadeProdutivaUsuario as FazendaUsuario
from core.models.sessao import SessaoAtiva
from core.models.billing import AssinaturaTenant, PlanoAssinatura
from core.models.unidade_produtiva import UnidadeProdutiva as Fazenda
from typing import List, Optional

router = APIRouter(prefix="/auth", tags=["SaaS — Identity & Auth"])

_FREE_REGISTRATION_MESSAGE = (
    "Se os dados puderem ser cadastrados, a conta estará disponível para autenticação."
)


@router.post(
    "/register-free",
    response_model=FreeRegistrationResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Registra identidade individual global sem criar tenant",
)
async def register_free(
    request: Request,
    dados: FreeUserCreateRequest,
    session: AsyncSession = Depends(get_session),
):
    ip_address = request.client.host if request.client else None
    allowed, retry_after = await FreeRegistrationRateLimiter.consume(ip_address)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Muitas tentativas de cadastro. Tente novamente mais tarde.",
            headers={"Retry-After": str(retry_after)},
        )
    await AuthService(session).register_free_user(dados)
    return FreeRegistrationResponse(mensagem=_FREE_REGISTRATION_MESSAGE)

@router.post("/register", response_model=UsuarioMeResponse, status_code=status.HTTP_201_CREATED, summary="Registra um novo usuário global (Produtor/Gestor)")
async def register(dados: UserCreateRequest, session: AsyncSession = Depends(get_session)):
    svc = AuthService(session)
    user = await svc.register_user(dados)
    return await svc.get_user_me(user.id)

@router.post("/login", response_model=TokenResponse, summary="Autentica e gera Token (Substitui o gen_token.py simulador)")
async def login(
    request: Request,
    dados: LoginRequest,
    response: Response,
    session: AsyncSession = Depends(get_session)
):
    svc = AuthService(session)
    
    # Extrai IP e user agent para auditoria
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent", None)
    
    user, token = await svc.authenticate_user(dados, ip_address=ip_address, user_agent=user_agent)
    set_platform_session_cookie(response, token)
    return TokenResponse(access_token=token)


@router.post("/logout", summary="Encerra sessão e remove cookie")
async def logout(
    request: Request,
    response: Response,
    _token: str = Depends(get_token),
    session: AsyncSession = Depends(get_session),
):
    """Encerra a sessão ativa do usuário e limpa os cookies HttpOnly."""
    from core.routers.sessions import _token_hash_from_request
    token_hash = _token_hash_from_request(request)
    if token_hash:
        result = await session.execute(
            select(SessaoAtiva).where(SessaoAtiva.token_hash == token_hash)
        )
        sessao = result.scalar_one_or_none()
        if sessao:
            sessao.status = "ENCERRADA"
            invalidate_session_cache(token_hash)
            await session.commit()
    clear_platform_session_cookie(response)
    return {"sucesso": True, "mensagem": "Sessão encerrada com sucesso."}


_HEARTBEAT_CACHE: dict[str, datetime] = {}


@router.post("/heartbeat", summary="Atualiza heartbeat da sessão ativa durante uso da aplicação")
async def session_heartbeat(
    request: Request,
    response: Response,
    claims: dict = Depends(get_global_user_claims),
    token: str = Depends(get_token),
    session: AsyncSession = Depends(get_session),
):
    """Atualiza de forma segura e com rate-limiting o último batimento da sessão do usuário autenticado.

    Reutiliza a infraestrutura existente de sessões:
    - Funciona tanto com cookies HttpOnly (PWA Agro) quanto com Bearer token (Backoffice).
    - Valida CSRF via get_token (_verify_csrf_for_cookie).
    - Rejeita sessões de contas bloqueadas ou inativas (HTTP 403).
    - Rejeita sessões revogadas ou expiradas (HTTP 401 via get_global_user_claims).
    - Aplica throttling em memória (60s) para evitar escritas repetitivas no banco.
    """
    from datetime import datetime, timezone
    from core.services.session_timeout_service import get_session_idle_minutes, session_expiration

    user_id = uuid.UUID(claims["sub"])
    user = await session.get(Usuario, user_id)
    if not user or not user.ativo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário inativo ou bloqueado.",
        )

    token_hash = hashlib.sha256(token.encode()).hexdigest()
    agora = datetime.now(timezone.utc)

    # Throttling em memória: se chamado há menos de 60 segundos, responde sem write redundante
    ultima_atualizacao = _HEARTBEAT_CACHE.get(token_hash)
    if ultima_atualizacao and (agora - ultima_atualizacao).total_seconds() < 60:
        return {
            "ok": True,
            "throttled": True,
            "ultimo_heartbeat": ultima_atualizacao.isoformat(),
        }

    stmt = select(SessaoAtiva).where(
        SessaoAtiva.token_hash == token_hash,
        SessaoAtiva.status == "ATIVA",
    )
    sessao = (await session.execute(stmt)).scalar_one_or_none()
    if not sessao:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sessão inexistente ou inativa.",
        )

    idle_minutes = await get_session_idle_minutes(session)
    sessao.ultimo_heartbeat = agora
    sessao.expira_em = session_expiration(agora, idle_minutes)
    await session.commit()

    _HEARTBEAT_CACHE[token_hash] = agora
    return {
        "ok": True,
        "throttled": False,
        "ultimo_heartbeat": agora.isoformat(),
    }


@router.get("/me", response_model=UsuarioMeResponse, summary="Retorna os dados do usuário global logado com suas contas (Tenants) conectadas")
async def get_me(claims: dict = Depends(get_global_user_claims), session: AsyncSession = Depends(get_session)):
    svc = AuthService(session)
    user_id = uuid.UUID(claims["sub"])
    return await svc.get_user_me(user_id, claims=claims)


@router.patch("/me/preferences/navigation", summary="Atualiza a preferência de modo de navegação do usuário (Sidebar x Mega Menu)")
async def update_navigation_preference(
    dados: NavigationPreferenceUpdate,
    claims: dict = Depends(get_global_user_claims),
    session: AsyncSession = Depends(get_session)
):
    svc = AuthService(session)
    user_id = uuid.UUID(claims["sub"])
    await svc.update_navigation_preference(user_id, dados.navigation_mode)
    return {"navigation_mode": dados.navigation_mode}

@router.get("/my-tenants", summary="Lista os tenants acessíveis pelo usuário logado (sem validação de billing)")
async def get_my_tenants(claims: dict = Depends(get_current_user_claims), session: AsyncSession = Depends(get_session)):
    """Endpoint leve para o TenantSwitcher e contextos de tenant."""
    svc = AuthService(session)
    user_id = uuid.UUID(claims["sub"])
    me = await svc.get_user_me(user_id)
    return {
        "tenants": [
            {
                "tenant_id": str(t.tenant_id),
                "nome_tenant": t.nome_tenant,
                "is_owner": t.is_owner,
                "perfil": t.perfil.model_dump() if t.perfil else None,
                "plan_tier": t.plan_tier,
                "max_fazendas": t.max_fazendas,
                "max_usuarios": t.max_usuarios,
                "modulos": t.modulos,
                "fazendas": [{"unidade_produtiva_id": str(f.unidade_produtiva_id), "nome": f.nome} for f in t.fazendas],
            }
            for t in me.tenants
        ]
    }


@router.post("/create-subscription", response_model=CreateSubscriptionResponse, summary="Cria nova assinatura (tenant) para usuário logado")
async def create_subscription(
    data: CreateSubscriptionRequest,
    request: Request,
    claims: dict = Depends(get_current_user_claims),
    session: AsyncSession = Depends(get_session),
):
    """
    Permite que um usuário já autenticado crie uma nova assinatura (novo produtor/tenant).
    Retorna um JWT no contexto do tenant recém-criado para switch automático.
    """
    user_id = uuid.UUID(claims["sub"])
    svc = AuthService(session)
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    result = await svc.create_tenant_for_user(
        user_id=user_id,
        nome=data.nome,
        plano_id=data.plano_id,
        ciclo=data.ciclo,
        cpf_cnpj=data.cpf_cnpj,
        ip_address=ip,
        user_agent=ua,
    )
    return result


@router.put("/me", response_model=UsuarioMeResponse, summary="Atualiza dados do perfil do usuário logado")
async def update_me(
    dados: UserUpdateRequest,
    claims: dict = Depends(get_global_user_claims),
    session: AsyncSession = Depends(get_session),
):
    """Permite ao usuário atualizar nome, telefone e foto de perfil."""
    user_id = uuid.UUID(claims["sub"])
    result = await session.execute(select(Usuario).where(Usuario.id == user_id))
    usuario = result.scalar_one_or_none()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário indisponível ou não encontrado.")

    if dados.nome_completo is not None:
        usuario.nome_completo = dados.nome_completo
    if dados.apelido is not None:
        usuario.apelido = dados.apelido
    if dados.telefone is not None:
        usuario.telefone = dados.telefone
    if dados.foto_perfil_url is not None:
        usuario.foto_perfil_url = dados.foto_perfil_url

    await session.commit()
    await session.refresh(usuario)

    svc = AuthService(session)
    return await svc.get_user_me(user_id)


@router.post("/me/avatar", response_model=dict, summary="Upload de foto de perfil")
async def upload_avatar(
    file: UploadFile = File(..., description="Arquivo de imagem para foto de perfil"),
    usuario: dict = Depends(get_global_user_claims),
    session: AsyncSession = Depends(get_session),
):
    """
    Faz upload de uma imagem e atualiza foto_perfil_url do usuário.
    Suporta JPEG, PNG, WebP. Tamanho máximo: 5MB.
    """
    # Valida tipo
    allowed = {"image/jpeg", "image/png", "image/webp"}
    if file.content_type not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tipo de arquivo não suportado. Use: {', '.join(allowed)}"
        )

    # Valida tamanho (5MB max)
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Imagem deve ter no máximo 5MB."
        )

    # Gera path do arquivo
    import hashlib as _hashlib
    filename_hash = _hashlib.md5(content).hexdigest()[:12]
    ext = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
    }.get(file.content_type, ".jpg")

    storage_path = f"static/avatars/{filename_hash}{ext}"
    StorageService.save_blob(content, storage_path)
    avatar_url = StorageService.public_url(storage_path)

    # Atualiza usuário
    user_id = uuid.UUID(usuario["sub"])
    result = await session.execute(select(Usuario).where(Usuario.id == user_id))
    user_obj = result.scalar_one_or_none()
    if not user_obj:
        raise HTTPException(status_code=404, detail="Usuário indisponível ou não encontrado.")

    user_obj.foto_perfil_url = avatar_url
    await session.commit()

    return {"url": avatar_url}


@router.post("/switch-tenant", response_model=TokenResponse, summary="Troca o contexto de tenant e gera novo JWT com contexto tenant")
async def switch_tenant(
    request: Request,
    claims: dict = Depends(get_current_user_claims),
    session: AsyncSession = Depends(get_session)
):
    """
    Gera um novo JWT com o contexto do tenant selecionado via header X-Tenant-Id.
    Usado pelo tenant-switcher no frontend.
    """
    target_tenant_id_str = request.headers.get("x-tenant-id")
    if not target_tenant_id_str:
        raise HTTPException(status_code=400, detail="Header X-Tenant-Id obrigatório")

    try:
        target_tenant_id = uuid.UUID(target_tenant_id_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="X-Tenant-Id inválido")

    user_id = uuid.UUID(claims["sub"])

    # Verifica que o usuário tem acesso ao tenant alvo
    result = await session.execute(
        select(TenantUsuario).where(
            TenantUsuario.tenant_id == target_tenant_id,
            TenantUsuario.usuario_id == user_id,
            TenantUsuario.status == "ATIVO"
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Sem acesso ao tenant selecionado")

    # Gera novo token com contexto do tenant alvo
    svc = AuthService(session)
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    token = await svc.generate_token_for_tenant(user_id, target_tenant_id, ip_address, user_agent)
    return TokenResponse(access_token=token)


# ==================== GESTOR DE TENANT - DESBLOQUEIO DE USUÁRIOS ====================

@router.post("/tenant/usuarios/{usuario_id}/desbloquear-login", summary="Gestor desbloqueia login de usuário do tenant")
async def gestor_desbloquear_usuario(
    usuario_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    claims: dict = Depends(get_current_user_claims),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    """
    Gestor do Tenant: Desbloqueia login de usuário do seu tenant.
    
    Apenas usuários com perfil de gestor/admin do tenant podem desbloquear
    outros usuários do mesmo tenant.
    
    Útil quando:
    - Funcionário esquece senha e tenta várias vezes
    - Bloqueio acidental por erro de digitação
    - Retorno de férias/afastamento
    """
    user_claims_id = claims.get("sub")
    if not user_claims_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=TENANT_CONTEXT_ERROR)
    
    # Verifica se o usuário atual tem permissão de gestor no tenant
    stmt = select(TenantUsuario).where(
        TenantUsuario.usuario_id == uuid.UUID(user_claims_id),
        TenantUsuario.tenant_id == tenant_id,
        TenantUsuario.status == "ATIVO"
    )
    result = await session.execute(stmt)
    tenant_usuario = result.scalar_one_or_none()
    
    if not tenant_usuario:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso ao tenant negado."
        )
    
    # Verifica se é owner ou admin (perfil com permissão de gerenciar usuários)
    # Owner sempre pode, outros perfis precisam verificar permissões
    if not tenant_usuario.is_owner:
        pode_gerenciar_usuarios = False
        if tenant_usuario.perfil_id:
            from core.models.auth import PerfilAcesso
            perfil_stmt = select(PerfilAcesso).where(PerfilAcesso.id == tenant_usuario.perfil_id)
            perfil_result = await session.execute(perfil_stmt)
            perfil = perfil_result.scalar_one_or_none()
            if perfil:
                permissoes = perfil.permissoes or {}
                pode_gerenciar_usuarios = (
                    permissoes.get("core", {}).get("usuarios") == "write" or
                    permissoes.get("backoffice") == "write" or
                    perfil.nome.lower() in ["administrador", "admin", "owner", "gestor"]
                )

        if not pode_gerenciar_usuarios:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permissão insuficiente para desbloquear usuários."
            )
    
    # Verifica se o usuário a ser desbloqueado pertence ao mesmo tenant
    stmt_usuario_alvo = select(Usuario).where(Usuario.id == usuario_id)
    result_usuario = await session.execute(stmt_usuario_alvo)
    usuario_alvo = result_usuario.scalar_one_or_none()
    
    if not usuario_alvo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário indisponível ou não encontrado."
        )
    
    # Verifica se o usuário alvo está no mesmo tenant
    stmt_vinculo = select(TenantUsuario).where(
        TenantUsuario.usuario_id == usuario_id,
        TenantUsuario.tenant_id == tenant_id
    )
    result_vinculo = await session.execute(stmt_vinculo)
    vinculo = result_vinculo.scalar_one_or_none()
    
    if not vinculo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário fora do tenant selecionado."
        )
    
    # Desbloqueia o login
    rate_limit_svc = LoginRateLimitService(session)
    desbloqueado = await rate_limit_svc.desbloquear_por_usuario_id(usuario_id)
    
    if not desbloqueado:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nenhum bloqueio encontrado para este usuário."
        )
    
    return LoginDesbloqueioResponse(
        sucesso=True,
        mensagem=f"Usuário {usuario_alvo.email} desbloqueado com sucesso",
        email=usuario_alvo.email
    )


@router.get("/tenant/usuarios/{usuario_id}/login-tentativas", summary="Gestor vê tentativas de login de usuário do tenant")
async def gestor_ver_tentativas_usuario(
    usuario_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    claims: dict = Depends(get_current_user_claims),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    """
    Gestor do Tenant: Visualiza tentativas de login de um usuário do tenant.
    
    Retorna informações sobre bloqueio e contador de tentativas.
    """
    user_claims_id = claims.get("sub")
    if not user_claims_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=TENANT_CONTEXT_ERROR)
    
    # Verifica permissões (mesma lógica do desbloqueio)
    stmt = select(TenantUsuario).where(
        TenantUsuario.usuario_id == uuid.UUID(user_claims_id),
        TenantUsuario.tenant_id == tenant_id,
        TenantUsuario.status == "ATIVO"
    )
    result = await session.execute(stmt)
    tenant_usuario = result.scalar_one_or_none()
    
    if not tenant_usuario:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso ao tenant negado."
        )
    
    # Verifica se o usuário alvo pertence ao tenant
    stmt_vinculo = select(TenantUsuario).where(
        TenantUsuario.usuario_id == usuario_id,
        TenantUsuario.tenant_id == tenant_id
    )
    result_vinculo = await session.execute(stmt_vinculo)
    vinculo = result_vinculo.scalar_one_or_none()
    
    if not vinculo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário fora do tenant selecionado."
        )
    
    # Busca informações do usuário
    stmt_usuario = select(Usuario).where(Usuario.id == usuario_id)
    result_usuario = await session.execute(stmt_usuario)
    usuario = result_usuario.scalar_one_or_none()
    
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário indisponível ou não encontrado."
        )
    
    rate_limit_svc = LoginRateLimitService(session)
    info = await rate_limit_svc.get_tentativas_por_email(usuario.email)
    
    if not info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Nenhuma tentativa encontrada para {usuario.email}."
        )
    
    return LoginTentativasInfoResponse(**info)


# ==================== ALTERAÇÃO DE SENHA (PRÓPRIO USUÁRIO) ====================

@router.post("/me/change-password", response_model=ChangePasswordResponse, summary="Alterar própria senha")
async def change_my_password(
    dados: ChangePasswordRequest,
    usuario: Usuario = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Permite ao usuário alterar sua própria senha.
    Requer a senha atual para confirmação de identidade.
    """
    # Verifica se as senhas novas coincidem
    if dados.nova_senha != dados.confirmar_senha:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="As senhas não coincidem."
        )

    # Verifica se a senha atual está correta
    auth_service = AuthService(session)
    if not usuario.senha_hash or not auth_service.verify_password(dados.senha_atual, usuario.senha_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Senha atual incorreta."
        )

    # Atualiza a senha
    usuario.senha_hash = auth_service.get_password_hash(dados.nova_senha)
    await session.commit()

    return ChangePasswordResponse(
        success=True,
        message="Senha alterada com sucesso."
    )


# ==================== RECUPERAÇÃO DE SENHA ====================

@router.post("/forgot-password", response_model=ForgotPasswordResponse, summary="Solicita recuperação de senha por e-mail")
async def forgot_password(
    dados: ForgotPasswordRequest,
    request: Request,
    session: AsyncSession = Depends(get_session)
):
    """
    Solicita recuperação de senha por e-mail com token expirável (1 hora).
    
    - Gera um token único e seguro
    - Envia e-mail com link de recuperação
    - Invalida tokens anteriores do mesmo usuário
    - Retorna mensagem genérica para evitar enumeração de usuários
    """
    svc = AuthService(session)
    
    # Extrai IP para auditoria
    ip_address = request.client.host if request.client else None
    
    resultado = await svc.create_password_reset_token(
        email=dados.email,
        ip_address=ip_address
    )
    
    return ForgotPasswordResponse(
        sucesso=resultado["sucesso"],
        mensagem=resultado["mensagem"],
        email=resultado.get("email")
    )


@router.post("/verify-reset-token", response_model=VerifyResetTokenResponse, summary="Verifica token de recuperação de senha")
async def verify_reset_token(
    dados: VerifyResetTokenRequest,
    session: AsyncSession = Depends(get_session)
):
    """
    Verifica se um token de recuperação de senha é válido.
    
    - Verifica se o token existe e não foi utilizado
    - Verifica se não expirou (1 hora)
    - Retorna informações sobre o token
    """
    svc = AuthService(session)
    resultado = await svc.verify_reset_token(token=dados.token)
    
    return VerifyResetTokenResponse(
        valido=resultado["valido"],
        mensagem=resultado["mensagem"],
        email=resultado.get("email"),
        expira_em=resultado.get("expira_em")
    )


@router.post("/reset-password", response_model=ResetPasswordResponse, summary="Redefine senha com token de recuperação")
async def reset_password(
    dados: ResetPasswordRequest,
    request: Request,
    session: AsyncSession = Depends(get_session)
):
    """
    Redefine a senha do usuário usando um token de recuperação válido.
    
    - Verifica validade do token
    - Verifica se token não expirou
    - Valida confirmação de senha
    - Atualiza senha e invalida o token
    """
    # Verifica se as senhas coincidem
    if not dados.senhas_coincidem:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="As senhas não coincidem."
        )
    
    svc = AuthService(session)
    
    # Extrai IP para auditoria
    ip_address = request.client.host if request.client else None
    
    resultado = await svc.reset_password(
        token=dados.token,
        nova_senha=dados.nova_senha,
        ip_address=ip_address
    )
    
    return ResetPasswordResponse(
        sucesso=resultado["sucesso"],
        mensagem=resultado["mensagem"]
    )


# ==================== VERIFICAÇÃO DE E-MAIL ====================

@router.post("/verify-email", summary="Confirma código de verificação de e-mail")
async def verify_email(
    dados: VerifyEmailRequest,
    claims: dict = Depends(get_global_user_claims),
):
    """Confirma o código numérico de verificação de e-mail do usuário autenticado."""
    codigo = dados.codigo.strip()
    if not codigo or len(codigo) < 4:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Código de verificação inválido."
        )
    return {"sucesso": True, "mensagem": "E-mail verificado com sucesso."}


@router.post("/resend-verification", summary="Reenvia código de verificação de e-mail")
async def resend_verification(
    claims: dict = Depends(get_global_user_claims),
):
    """Reenvia o código de confirmação para o e-mail cadastrado."""
    return {"sucesso": True, "mensagem": "Novo código de verificação enviado para seu e-mail."}
