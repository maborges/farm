import inspect

from ia import router as ia_router


def test_get_plano_acao_usa_tenant_id_como_dependencia() -> None:
    signature = inspect.signature(ia_router.get_plano_acao)
    tenant_param = signature.parameters["tenant_id"]

    assert tenant_param.default.dependency is ia_router.get_tenant_id
