import re

with open("services/api/integracoes/sankhya/routers/__init__.py", "r") as f:
    content = f.read()

content = content.replace(
    "        created = await sync_service.criar_config(\n            tenant_id=tenant_scope,\n            sankhya_environment=config.sankhya_environment,",
    "        created = await sync_service.criar_config(\n            tenant_id=tenant_scope,\n            auth_model=config.auth_model,\n            sankhya_environment=config.sankhya_environment,"
)

content = content.replace(
    "                existing,\n                sankhya_environment=config.sankhya_environment,",
    "                existing,\n                auth_model=config.auth_model,\n                sankhya_environment=config.sankhya_environment,"
)

with open("services/api/integracoes/sankhya/routers/__init__.py", "w") as f:
    f.write(content)
