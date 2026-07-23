import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from core.models.sequencial import SequencialContador
from core.models.tenant_config import ConfiguracaoTenant
from core.sequenciais_config import SEQUENCIAL_CONFIG

CATEGORIA_CONFIG = "sequenciais"


class SequencialService:
    """Gera códigos de referência legíveis (ex: PED-2026-000123).

    Cumprem, para comunicação humana, o mesmo papel que o `id` (UUID)
    cumpre como chave primária: identificam de forma única e definitiva
    um registro dentro do tenant. Ver core/sequenciais_config.py.

    O padrão (prefixo/dígitos/escopo) tem um default por entidade definido
    na aplicação, mas cada tenant pode personalizá-lo via
    ConfiguracaoTenant(categoria="sequenciais", chave=entidade) — ver
    ConfiguracoesService.get_sequencial_config/set_sequencial_config.
    """

    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        self.session = session
        self.tenant_id = tenant_id

    async def _resolver_config(self, entidade: str) -> dict:
        default = SEQUENCIAL_CONFIG[entidade]
        stmt = select(ConfiguracaoTenant).where(
            ConfiguracaoTenant.tenant_id == self.tenant_id,
            ConfiguracaoTenant.categoria == CATEGORIA_CONFIG,
            ConfiguracaoTenant.chave == entidade,
            ConfiguracaoTenant.ativo == True,
        )
        override = (await self.session.execute(stmt)).scalar_one_or_none()
        if override:
            return {**default, **override.valor}
        return default

    async def proximo_numero(self, entidade: str) -> str:
        cfg = await self._resolver_config(entidade)
        ano = date.today().year if cfg["escopo"] == "ANO" else None

        # Garante que a linha do contador exista (idempotente, não sobrescreve).
        stmt_insert = pg_insert(SequencialContador).values(
            id=uuid.uuid4(),
            tenant_id=self.tenant_id,
            entidade=entidade,
            ano=ano,
            ultimo_numero=0,
        ).on_conflict_do_nothing(
            index_elements=["tenant_id", "entidade", "ano"],
        )
        await self.session.execute(stmt_insert)

        # Trava a linha (FOR UPDATE) para serializar concorrência entre requisições.
        stmt_lock = (
            select(SequencialContador)
            .where(
                SequencialContador.tenant_id == self.tenant_id,
                SequencialContador.entidade == entidade,
                SequencialContador.ano == ano,
            )
            .with_for_update()
        )
        contador = (await self.session.execute(stmt_lock)).scalar_one()
        contador.ultimo_numero += 1
        await self.session.flush()

        numero_formatado = f"{contador.ultimo_numero:0{cfg['digitos']}d}"
        if ano:
            return f"{cfg['prefixo']}-{ano}-{numero_formatado}"
        return f"{cfg['prefixo']}-{numero_formatado}"

    async def resetar_contador(self, entidade: str, ultimo_numero: int) -> str:
        """Ajusta o último número emitido (ex: para continuar uma numeração legada).

        O próximo `proximo_numero()` chamado emitirá `ultimo_numero + 1`.
        Afeta apenas o escopo vigente (ano corrente, se escopo == "ANO").
        """
        cfg = await self._resolver_config(entidade)
        ano = date.today().year if cfg["escopo"] == "ANO" else None

        stmt_insert = pg_insert(SequencialContador).values(
            id=uuid.uuid4(),
            tenant_id=self.tenant_id,
            entidade=entidade,
            ano=ano,
            ultimo_numero=ultimo_numero,
        ).on_conflict_do_update(
            index_elements=["tenant_id", "entidade", "ano"],
            set_={"ultimo_numero": ultimo_numero},
        )
        await self.session.execute(stmt_insert)
        await self.session.flush()

        numero_formatado = f"{ultimo_numero:0{cfg['digitos']}d}"
        if ano:
            return f"{cfg['prefixo']}-{ano}-{numero_formatado}"
        return f"{cfg['prefixo']}-{numero_formatado}"
