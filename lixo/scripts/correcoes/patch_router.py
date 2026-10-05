import re

with open("services/api/integracoes/sankhya/routers/__init__.py", "r") as f:
    content = f.read()

# Pass auth_model to atualizar_config
content = content.replace(
    "                existing,\n                sankhya_environment=config.sankhya_environment,",
    "                existing,\n                auth_model=config.auth_model,\n                sankhya_environment=config.sankhya_environment,"
)

# Pass auth_model to criar_config
content = content.replace(
    "                tenant_id=tenant_scope,\n                sankhya_environment=config.sankhya_environment,",
    "                tenant_id=tenant_scope,\n                auth_model=config.auth_model,\n                sankhya_environment=config.sankhya_environment,"
)

with open("services/api/integracoes/sankhya/routers/__init__.py", "w") as f:
    f.write(content)
