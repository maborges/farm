"""Roteador de endpoints HTTP para identidade individual do DeepFarms Agro."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from .database import get_agro_db
from .dependencies import extract_agro_token, get_current_agro_user
from .models import AgroUsuario
from .schemas import (
    AgroAuthResponse,
    AgroChangePasswordRequest,
    AgroForgotPasswordRequest,
    AgroForgotPasswordResponse,
    AgroLoginRequest,
    AgroMessageResponse,
    AgroRegisterRequest,
    AgroResetPasswordRequest,
    AgroUsuarioResponse,
    AgroVerifyEmailRequest,
)
from .security import (
    clear_agro_session_cookie,
    set_agro_session_cookie,
    verify_agro_csrf,
)
from .service import AgroIdentityService

router = APIRouter(
    prefix="/agro/auth",
    tags=["DeepFarms Agro — Identidade Individual (Legado Descontinuado)"],
    deprecated=True,
)


def _to_usuario_response(usuario: AgroUsuario) -> AgroUsuarioResponse:
    return AgroUsuarioResponse(
        id=usuario.id,
        email=usuario.email,
        nome=usuario.nome,
        ativo=usuario.ativo,
        emailVerificado=usuario.email_verificado,
        createdAt=usuario.created_at,
    )


@router.post("/register", response_model=AgroAuthResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: Request,
    response: Response,
    dados: AgroRegisterRequest,
    db: AsyncSession = Depends(get_agro_db),
) -> AgroAuthResponse:
    """Cria uma nova conta individual gratuita no DeepFarms Agro e emite sessão segura."""
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")

    service = AgroIdentityService(db)
    usuario, token, _ = await service.register_user(dados, ip_address=ip, user_agent=ua)

    # Injeta cookie HttpOnly na resposta
    set_agro_session_cookie(response, token)

    return AgroAuthResponse(
        sucesso=True,
        mensagem="Conta individual criada com sucesso.",
        usuario=_to_usuario_response(usuario),
    )


@router.post("/login", response_model=AgroAuthResponse)
async def login(
    request: Request,
    response: Response,
    dados: AgroLoginRequest,
    db: AsyncSession = Depends(get_agro_db),
) -> AgroAuthResponse:
    """Autentica o usuário individual com proteção contra força bruta."""
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")

    service = AgroIdentityService(db)
    usuario, token = await service.authenticate(dados, ip_address=ip, user_agent=ua)

    set_agro_session_cookie(response, token)

    return AgroAuthResponse(
        sucesso=True,
        mensagem="Autenticado com sucesso.",
        usuario=_to_usuario_response(usuario),
    )


@router.post("/logout", response_model=AgroMessageResponse)
async def logout(
    request: Request,
    response: Response,
    _: None = Depends(verify_agro_csrf),
    db: AsyncSession = Depends(get_agro_db),
) -> AgroMessageResponse:
    """Encerra a sessão ativa e limpa o cookie HttpOnly."""
    try:
        token = extract_agro_token(request)
        service = AgroIdentityService(db)
        await service.logout(token)
    except Exception:
        pass  # Logout idempotente

    clear_agro_session_cookie(response)
    return AgroMessageResponse(sucesso=True, mensagem="Sessão encerrada com sucesso.")


@router.get("/me", response_model=AgroUsuarioResponse)
async def get_me(
    usuario: AgroUsuario = Depends(get_current_agro_user),
) -> AgroUsuarioResponse:
    """Retorna os dados do perfil do usuário individual logado."""
    return _to_usuario_response(usuario)


@router.post("/forgot-password", response_model=AgroForgotPasswordResponse)
async def forgot_password(
    dados: AgroForgotPasswordRequest,
    db: AsyncSession = Depends(get_agro_db),
) -> AgroForgotPasswordResponse:
    """Solicita redefinição de senha com validade de 1 hora."""
    service = AgroIdentityService(db)
    await service.request_password_reset(dados.email)

    return AgroForgotPasswordResponse(
        sucesso=True,
        mensagem="Se o e-mail informado estiver cadastrado, as instruções de recuperação foram enviadas.",
    )


@router.post("/reset-password", response_model=AgroMessageResponse)
async def reset_password(
    dados: AgroResetPasswordRequest,
    db: AsyncSession = Depends(get_agro_db),
) -> AgroMessageResponse:
    """Aplica a nova senha e revoga todas as sessões anteriores."""
    service = AgroIdentityService(db)
    await service.reset_password(dados)
    return AgroMessageResponse(sucesso=True, mensagem="Senha redefinida com sucesso. Faça login com a nova senha.")


@router.post("/verify-email", response_model=AgroMessageResponse)
async def verify_email(
    dados: AgroVerifyEmailRequest,
    usuario: AgroUsuario = Depends(get_current_agro_user),
    _: None = Depends(verify_agro_csrf),
    db: AsyncSession = Depends(get_agro_db),
) -> AgroMessageResponse:
    """Confirma o código de verificação de e-mail de 6 dígitos."""
    service = AgroIdentityService(db)
    await service.verify_email(usuario.id, dados.codigo)
    return AgroMessageResponse(sucesso=True, mensagem="E-mail verificado com sucesso.")


@router.post("/resend-verification", response_model=AgroMessageResponse)
async def resend_verification(
    usuario: AgroUsuario = Depends(get_current_agro_user),
    _: None = Depends(verify_agro_csrf),
    db: AsyncSession = Depends(get_agro_db),
) -> AgroMessageResponse:
    """Reenvia o código numérico de 6 dígitos para o e-mail cadastrado."""
    service = AgroIdentityService(db)
    await service.resend_verification_code(usuario.id)
    return AgroMessageResponse(sucesso=True, mensagem="Novo código de verificação enviado para seu e-mail.")


@router.post("/change-password", response_model=AgroMessageResponse)
async def change_password(
    dados: AgroChangePasswordRequest,
    usuario: AgroUsuario = Depends(get_current_agro_user),
    _: None = Depends(verify_agro_csrf),
    db: AsyncSession = Depends(get_agro_db),
) -> AgroMessageResponse:
    """Altera a senha do usuário autenticado."""
    service = AgroIdentityService(db)
    await service.change_password(usuario.id, dados)
    return AgroMessageResponse(sucesso=True, mensagem="Senha alterada com sucesso.")


@router.delete("/me", response_model=AgroMessageResponse)
async def delete_account(
    response: Response,
    usuario: AgroUsuario = Depends(get_current_agro_user),
    _: None = Depends(verify_agro_csrf),
    db: AsyncSession = Depends(get_agro_db),
) -> AgroMessageResponse:
    """Exclui permanentemente a conta individual e todos os seus dados associados."""
    service = AgroIdentityService(db)
    await service.delete_account(usuario.id)
    clear_agro_session_cookie(response)
    return AgroMessageResponse(sucesso=True, mensagem="Conta individual excluída permanentemente.")
