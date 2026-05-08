
import time
import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from loguru import logger
from datetime import datetime, timezone

class ObservabilityMiddleware(BaseHTTPMiddleware):
    """
    Middleware para logging estruturado (JSON) e monitoramento de performance.
    Captura tempo de resposta, status e tenant_id.
    Emite alertas para erros 500 e requisições lentas (> 1s).
    """

    async def dispatch(self, request, call_next):
        start_time = time.perf_counter()
        
        # Identificador único da requisição (Traceability)
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        
        # Contexto compartilhado para todos os logs da requisição
        with logger.contextualize(request_id=request_id):
            response = await call_next(request)
            
            process_time = time.perf_counter() - start_time
            status_code = response.status_code
            
            # Extrai tenant_id se disponível
            tenant_id = getattr(request.state, "rls_tenant_id", None)
            
            # Log estruturado (JSON quando serialize=True no logger)
            logger.info(
                "API_REQUEST",
                method=request.method,
                path=request.url.path,
                status=status_code,
                duration=round(process_time, 4),
                tenant_id=str(tenant_id) if tenant_id else None,
                user_agent=request.headers.get("user-agent"),
                ip=request.client.host if request.client else None
            )

            # Alertas Críticos
            if status_code >= 500:
                logger.error(f"ALERT: SERVER_ERROR | {request.method} {request.url.path}")
                
            if process_time > 1.0:
                logger.warning(f"ALERT: SLOW_REQUEST | {request.method} {request.url.path} | {process_time:.4f}s")

            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = f"{process_time:.4f}s"
            
            return response

async def check_db_health():
    """Verifica se a conexão com o banco de dados está ativa."""
    from core.database import engine
    from sqlalchemy import text
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            return True
    except Exception as e:
        logger.error(f"Healthcheck DB Failure: {e}")
        return False
