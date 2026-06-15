import os
from pathlib import Path

p = Path("/opt/lampp/htdocs/farm/services/api/tests/test_e2e_colheita_completa.py")
content = p.read_text()
content = content.replace("tenant_uuid = UUID(tenant_id)", "tenant_uuid = tenant_id if isinstance(tenant_id, UUID) else UUID(tenant_id)")
content = content.replace("fazenda_uuid = UUID(unidade_produtiva_id)", "fazenda_uuid = unidade_produtiva_id if isinstance(unidade_produtiva_id, UUID) else UUID(unidade_produtiva_id)")
content = content.replace("tenant_a = UUID(tenant_id)", "tenant_a = tenant_id if isinstance(tenant_id, UUID) else UUID(tenant_id)")
content = content.replace("tenant_b = UUID(outro_tenant_id)", "tenant_b = outro_tenant_id if isinstance(outro_tenant_id, UUID) else UUID(outro_tenant_id)")

p.write_text(content)
print("Fix applied to test_e2e_colheita_completa.py")
