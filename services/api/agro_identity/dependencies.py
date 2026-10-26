"""Dependências FastAPI exclusivas para o módulo de identidade individual do Agro."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import AGRO_COOKIE_NAME
from .database import get_agro_db
from .models import AgroSessao, AgroUsuario
from .security import decode_agro_jwt, hash_token


def extract_agro_token(request: Request) -> str:
    """Extrai o token individual do header Bearer explícito ou do cookie HttpOnly seguro."""
    # 1. Header Authorization Bearer explícito
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:].strip()

    # 2. Cookie HttpOnly Agro
    token = request.cookies.get(AGRO_COOKIE_NAME)
    if token:
        return token

    # 3. Cookie HttpOnly Plataforma Central
    token_central = request.cookies.get("deepfarms_session")
    if token_central:
        return token_central

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Sessão individual não autenticada. Faça login para continuar.",
    )


async def get_current_agro_user(
    request: Request,
    db: AsyncSession = Depends(get_agro_db),
) -> AgroUsuario:
    """Valida o token individual e a sessão ativa (compatível com identidade central e segregada)."""
    token = extract_agro_token(request)

    # 1. Tenta decodificar via infraestrutura de identidade central
    try:
        from jose import jwt
        from core.config import settings
        claims_central = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            options={"verify_aud": False, "verify_iss": False},
        )
        sub_str = claims_central.get("sub")
        if sub_str:
            usuario_id = uuid.UUID(sub_str)
            return AgroUsuario(
                id=usuario_id,
                email=claims_central.get("email", ""),
                nome=claims_central.get("nome", "Usuário DeepFarms"),
                ativo=True,
                email_verificado=True,
            )
    except Exception:
        pass

    # 2. Fallback para tokens legados da identidade individual segregada
    claims = decode_agro_jwt(token)

    sub_str = claims.get("sub")
    if not sub_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token sem identificador de usuário válido.",
        )

    usuario_id = uuid.UUID(sub_str)
    token_hash_val = hash_token(token)
    now = datetime.now(timezone.utc)

    # Valida sessão no banco segregado
    stmt_sessao = select(AgroSessao).where(
        AgroSessao.token_hash == token_hash_val,
        AgroSessao.revogado == False,  # noqa: E712
        AgroSessao.expira_em > now,
    )
    sessao = (await db.execute(stmt_sessao)).scalar_one_or_none()
    if sessao is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sessão individual expirada ou revogada.",
        )

    # Recupera o usuário
    stmt_user = select(AgroUsuario).where(AgroUsuario.id == usuario_id)
    usuario = (await db.execute(stmt_user)).scalar_one_or_none()
    if usuario is None or not usuario.ativo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário individual inativo ou não encontrado.",
        )

    # Atualiza timestamp de último acesso (fire-and-forget leve no banco segregado)
    sessao.ultimo_acesso = now
    await db.commit()

    return usuario
