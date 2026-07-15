"""Bootstrap do registry de providers ERP.

Único módulo que importa implementações concretas de provider para registrá-las.
Chamado durante a inicialização da aplicação.

Nenhum outro módulo genérico do pacote erp pode importar providers concretos.
"""

from __future__ import annotations

from integracoes.erp.provider_registry import erp_provider_registry
from integracoes.erp.providers.sankhya_runtime import SankhyaProviderRuntime


def bootstrap_erp_providers() -> None:
    """Registra todos os providers ERP disponíveis no registry.

    Chamado uma vez durante o startup da aplicação.
    Registros duplicados são ignorados silenciosamente quando o bootstrap
    é chamado mais de uma vez (idempotência).
    """
    if not erp_provider_registry.is_registered("sankhya"):
        erp_provider_registry.register("sankhya", SankhyaProviderRuntime)


# Auto-bootstrap ao importar o módulo.
bootstrap_erp_providers()

__all__ = ["bootstrap_erp_providers"]
