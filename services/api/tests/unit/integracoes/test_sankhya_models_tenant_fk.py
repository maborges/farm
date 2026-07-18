from __future__ import annotations

import pytest

from core.models.tenant import Tenant
from integracoes.sankhya.models import (
    SankhyaConfig,
    SankhyaLancamentoFinanceiro,
    SankhyaNFe,
    SankhyaPessoa,
    SankhyaProduto,
    SankhyaSyncLog,
    SankhyaTabela,
)

MODELS_COM_TENANT_FK = (
    SankhyaConfig,
    SankhyaSyncLog,
    SankhyaPessoa,
    SankhyaProduto,
    SankhyaNFe,
    SankhyaLancamentoFinanceiro,
    SankhyaTabela,
)


@pytest.mark.parametrize("model", MODELS_COM_TENANT_FK, ids=lambda m: m.__name__)
def test_sankhya_tenant_fk_resolve_para_tenant_table_no_metadata_compartilhado(model) -> None:
    """Regressão de INTEGRATIONS-MODEL-FK-REPAIR-03: `ForeignKey("farms.tenants.id")`
    não resolvia contra o Base.metadata compartilhado, pois `Tenant` é registrado
    como "tenants" (sem schema). A FK deve resolver para o objeto `Tenant.__table__`
    real, não apenas comparar a string do target.
    """
    fk = next(iter(model.__table__.c.tenant_id.foreign_keys))
    assert fk.column.table is Tenant.__table__, (
        f"{model.__name__}.tenant_id não resolve para Tenant.__table__"
    )
    assert fk.ondelete == "NO ACTION"
