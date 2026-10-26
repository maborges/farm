"""Serviço de lógica de negócios para identidade individual do DeepFarms Agro."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from loguru import logger
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from .config import AGRO_TOKEN_EXPIRE_DAYS
from .email_dispatch import dispatch_password_reset_email, dispatch_verification_email
from .models import (
    AgroSessao,
    AgroTokenRecuperacao,
    AgroTokenVerificacao,
    AgroUsuario,
)
from .schemas import (
    AgroChangePasswordRequest,
    AgroLoginRequest,
    AgroRegisterRequest,
    AgroResetPasswordRequest,
)
from .security import (
    AgroLoginRateLimiter,
    create_agro_jwt,
    generate_secure_token,
    generate_verification_code,
    get_agro_rate_limiter,
    hash_password,
    hash_token,
    verify_password,
)


class AgroIdentityService:
    """Orquestrador de operações de identidade individual no repositório segregado."""

    def __init__(self, session: AsyncSession, rate_limiter: AgroLoginRateLimiter | None = None) -> None:
        self.session = session
        self.rate_limiter = rate_limiter or get_agro_rate_limiter()

    async def register_user(
        self,
        dados: AgroRegisterRequest,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[AgroUsuario, str, str]:
        """Registra novo usuário individual e gera sessão inicial sem criar nenhum tenant comercial."""
        email_clean = dados.email.strip().lower()

        # Verifica unicidade do e-mail no repositório segregado
        stmt = select(AgroUsuario).where(AgroUsuario.email == email_clean)
        existing = (await self.session.execute(stmt)).scalar_one_or_none()
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Já existe uma conta cadastrada com este e-mail.",
            )

        usuario = AgroUsuario(
            email=email_clean,
            nome=dados.nome.strip(),
            senha_hash=hash_password(dados.senha),
            ativo=True,
            email_verificado=False,
        )
        self.session.add(usuario)
        await self.session.flush()

        # Gera sessão inicial
        sessao_id = uuid.uuid4()
        token = create_agro_jwt(usuario.id, usuario.email, usuario.nome, sessao_id)
        token_hash_val = hash_token(token)

        now = datetime.now(timezone.utc)
        expira_em = now + timedelta(days=AGRO_TOKEN_EXPIRE_DAYS)

        sessao = AgroSessao(
            id=sessao_id,
            usuario_id=usuario.id,
            token_hash=token_hash_val,
            ip_address=ip_address,
            user_agent=user_agent,
            revogado=False,
            criado_em=now,
            ultimo_acesso=now,
            expira_em=expira_em,
        )
        self.session.add(sessao)

        # Código de verificação de e-mail inicial
        cod_verif = generate_verification_code()
        token_verif = AgroTokenVerificacao(
            usuario_id=usuario.id,
            codigo=cod_verif,
            usado=False,
            criado_em=now,
            expira_em=now + timedelta(hours=24),
        )
        self.session.add(token_verif)

        await self.session.commit()
        await self.session.refresh(usuario)

        # Despacha e-mail real com o código de 6 dígitos
        await dispatch_verification_email(usuario.email, usuario.nome, cod_verif)

        logger.info("Nova identidade individual criada no DeepFarms Agro", user_id=str(usuario.id))
        return usuario, token, cod_verif

    async def authenticate(
        self,
        dados: AgroLoginRequest,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[AgroUsuario, str]:
        """Autentica usuário individual com proteção contra força bruta e controle de sessão."""
        email_clean = dados.email.strip().lower()

        # 1. Checa período de bloqueio (brute-force lockout)
        await self.rate_limiter.check_lockout(email_clean, ip_address)

        # 2. Busca conta no banco segregado
        stmt = select(AgroUsuario).where(AgroUsuario.email == email_clean)
        usuario = (await self.session.execute(stmt)).scalar_one_or_none()

        if usuario is None or not verify_password(dados.senha, usuario.senha_hash):
            await self.rate_limiter.record_failure(email_clean)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="E-mail ou senha incorretos.",
            )

        if not usuario.ativo:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Esta conta individual está desativada.",
            )

        # 3. Sucesso: zera contador de falhas
        await self.rate_limiter.record_success(email_clean)

        # 4. Cria nova sessão ativa
        sessao_id = uuid.uuid4()
        token = create_agro_jwt(usuario.id, usuario.email, usuario.nome, sessao_id)
        token_hash_val = hash_token(token)

        now = datetime.now(timezone.utc)
        expira_em = now + timedelta(days=AGRO_TOKEN_EXPIRE_DAYS)

        sessao = AgroSessao(
            id=sessao_id,
            usuario_id=usuario.id,
            token_hash=token_hash_val,
            ip_address=ip_address,
            user_agent=user_agent,
            revogado=False,
            criado_em=now,
            ultimo_acesso=now,
            expira_em=expira_em,
        )
        self.session.add(sessao)
        await self.session.commit()
        await self.session.refresh(usuario)

        return usuario, token

    async def logout(self, token: str) -> None:
        """Revoga a sessão ativa do usuário individual."""
        token_hash_val = hash_token(token)
        stmt = (
            update(AgroSessao)
            .where(AgroSessao.token_hash == token_hash_val)
            .values(revogado=True)
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def get_me(self, usuario_id: uuid.UUID) -> AgroUsuario:
        """Recupera dados da conta individual autenticada."""
        stmt = select(AgroUsuario).where(AgroUsuario.id == usuario_id)
        usuario = (await self.session.execute(stmt)).scalar_one_or_none()
        if usuario is None or not usuario.ativo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conta individual não encontrada ou inativa.",
            )
        return usuario

    async def request_password_reset(self, email: str) -> str | None:
        """Emite token de recuperação com validade de 1 hora."""
        email_clean = email.strip().lower()
        stmt = select(AgroUsuario).where(AgroUsuario.email == email_clean)
        usuario = (await self.session.execute(stmt)).scalar_one_or_none()

        if usuario is None or not usuario.ativo:
            # Resposta neutra para evitar enumeração de contas
            return None

        raw_token = generate_secure_token()
        now = datetime.now(timezone.utc)
        expira_em = now + timedelta(hours=1)

        recup = AgroTokenRecuperacao(
            usuario_id=usuario.id,
            token_hash=hash_token(raw_token),
            usado=False,
            criado_em=now,
            expira_em=expira_em,
        )
        self.session.add(recup)
        await self.session.commit()

        # Despacha e-mail com token de uso único em ambiente controlado/real
        await dispatch_password_reset_email(usuario.email, usuario.nome, raw_token)

        logger.info("Token de recuperação de senha emitido", user_id=str(usuario.id))
        return raw_token

    async def reset_password(self, dados: AgroResetPasswordRequest) -> None:
        """Redefine a senha do usuário e revoga todas as sessões anteriores."""
        token_hash_val = hash_token(dados.token.strip())
        now = datetime.now(timezone.utc)

        stmt = select(AgroTokenRecuperacao).where(
            AgroTokenRecuperacao.token_hash == token_hash_val,
            AgroTokenRecuperacao.usado == False,  # noqa: E712
            AgroTokenRecuperacao.expira_em > now,
        )
        recup = (await self.session.execute(stmt)).scalar_one_or_none()

        if recup is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token de recuperação inválido, já utilizado ou expirado.",
            )

        # Atualiza a senha
        stmt_user = (
            update(AgroUsuario)
            .where(AgroUsuario.id == recup.usuario_id)
            .values(senha_hash=hash_password(dados.novaSenha))
        )
        await self.session.execute(stmt_user)

        # Marca token como usado
        recup.usado = True

        # Revoga todas as sessões ativas existentes por segurança
        stmt_sessoes = (
            update(AgroSessao)
            .where(AgroSessao.usuario_id == recup.usuario_id)
            .values(revogado=True)
        )
        await self.session.execute(stmt_sessoes)

        await self.session.commit()
        logger.info("Senha redefinida com sucesso e sessões revogadas", user_id=str(recup.usuario_id))

    async def verify_email(self, usuario_id: uuid.UUID, codigo: str) -> None:
        """Valida o código de 6 dígitos e marca o e-mail como verificado."""
        now = datetime.now(timezone.utc)
        stmt = select(AgroTokenVerificacao).where(
            AgroTokenVerificacao.usuario_id == usuario_id,
            AgroTokenVerificacao.codigo == codigo.strip(),
            AgroTokenVerificacao.usado == False,  # noqa: E712
            AgroTokenVerificacao.expira_em > now,
        )
        token_verif = (await self.session.execute(stmt)).scalar_one_or_none()

        if token_verif is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Código de verificação incorreto ou expirado.",
            )

        token_verif.usado = True
        stmt_user = (
            update(AgroUsuario)
            .where(AgroUsuario.id == usuario_id)
            .values(email_verificado=True)
        )
        await self.session.execute(stmt_user)
        await self.session.commit()

    async def change_password(self, usuario_id: uuid.UUID, dados: AgroChangePasswordRequest) -> None:
        """Altera a senha de um usuário autenticado e revoga todas as sessões anteriores."""
        stmt = select(AgroUsuario).where(AgroUsuario.id == usuario_id)
        usuario = (await self.session.execute(stmt)).scalar_one_or_none()

        if usuario is None or not verify_password(dados.senhaAtual, usuario.senha_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Senha atual incorreta.",
            )

        usuario.senha_hash = hash_password(dados.novaSenha)

        # Revoga todas as sessões ativas existentes por segurança
        stmt_sessoes = (
            update(AgroSessao)
            .where(AgroSessao.usuario_id == usuario_id)
            .values(revogado=True)
        )
        await self.session.execute(stmt_sessoes)
        await self.session.commit()
        logger.info("Senha alterada e sessões revogadas", user_id=str(usuario_id))

    async def resend_verification_code(self, usuario_id: uuid.UUID) -> str:
        """Emite novo código numérico de 6 dígitos e despacha por e-mail."""
        stmt = select(AgroUsuario).where(AgroUsuario.id == usuario_id)
        usuario = (await self.session.execute(stmt)).scalar_one_or_none()
        if usuario is None or not usuario.ativo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário não encontrado.",
            )
        if usuario.email_verificado:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="O e-mail deste usuário já está verificado.",
            )

        now = datetime.now(timezone.utc)
        stmt_inv = (
            update(AgroTokenVerificacao)
            .where(AgroTokenVerificacao.usuario_id == usuario_id)
            .values(usado=True)
        )
        await self.session.execute(stmt_inv)

        cod_verif = generate_verification_code()
        token_verif = AgroTokenVerificacao(
            usuario_id=usuario.id,
            codigo=cod_verif,
            usado=False,
            criado_em=now,
            expira_em=now + timedelta(hours=24),
        )
        self.session.add(token_verif)
        await self.session.commit()

        await dispatch_verification_email(usuario.email, usuario.nome, cod_verif)
        return cod_verif

    async def delete_account(self, usuario_id: uuid.UUID) -> None:
        """Exclusão física definitiva com remoção em cascata (crypto-shredding)."""
        stmt = select(AgroUsuario).where(AgroUsuario.id == usuario_id)
        usuario = (await self.session.execute(stmt)).scalar_one_or_none()
        if usuario is not None:
            await self.session.delete(usuario)
            await self.session.commit()
            logger.info("Conta individual excluída permanentemente", user_id=str(usuario_id))
