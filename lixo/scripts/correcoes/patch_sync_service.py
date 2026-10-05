import re

with open("services/api/integracoes/sankhya/services/sync_service.py", "r") as f:
    content = f.read()

# Update criar_config def
content = content.replace(
    "        tenant_id: str,\n        sankhya_environment: str | None = None,",
    "        tenant_id: str,\n        auth_model: str | None = None,\n        sankhya_environment: str | None = None,"
)

# Pass auth_model to _normalize_config_values from criar_config
content = content.replace(
    "            sankhya_environment=sankhya_environment,\n            sankhya_api_base_url=sankhya_api_base_url,",
    "            auth_model=auth_model,\n            sankhya_environment=sankhya_environment,\n            sankhya_api_base_url=sankhya_api_base_url,"
)

# Update atualizar_config def
content = content.replace(
    "        config: SankhyaConfig,\n        *,\n        sankhya_environment: str | None = None,",
    "        config: SankhyaConfig,\n        *,\n        auth_model: str | None = None,\n        sankhya_environment: str | None = None,"
)

# Pass auth_model to _normalize_config_values from atualizar_config
content = content.replace(
    "        normalized = await self._normalize_config_values(\n            sankhya_environment=sankhya_environment,",
    "        normalized = await self._normalize_config_values(\n            auth_model=auth_model,\n            sankhya_environment=sankhya_environment,"
)

# Update _normalize_config_values def
content = content.replace(
    "    async def _normalize_config_values(\n        self,\n        *,\n        sankhya_environment: str | None,",
    "    async def _normalize_config_values(\n        self,\n        *,\n        auth_model: str | None = None,\n        sankhya_environment: str | None,"
)

# Update _normalize_config_values inference logic
old_logic = """        if explicit_legacy_login:
            auth_model = "gateway_legacy_login"
        elif explicit_gateway:
            auth_model = "gateway_oauth_client_credentials"
        elif current_model and current_model != "incomplete":
            auth_model = current_model
        elif explicit_legacy:
            auth_model = "legacy_ws_basic_auth"
        else:
            auth_model = "gateway_oauth_client_credentials\""""

new_logic = """        # Respeita o auth_model se for providenciado explicitamente, senão fallback
        if auth_model:
            if auth_model not in ("gateway_oauth_client_credentials", "gateway_legacy_login", "legacy_ws_basic_auth"):
                raise ValueError(f"auth_model inválido: {auth_model}")
        else:
            if explicit_legacy_login:
                auth_model = "gateway_legacy_login"
            elif explicit_gateway:
                auth_model = "gateway_oauth_client_credentials"
            elif current_model and current_model != "incomplete":
                auth_model = current_model
            elif explicit_legacy:
                auth_model = "legacy_ws_basic_auth"
            else:
                auth_model = "gateway_oauth_client_credentials\""""

content = content.replace(old_logic, new_logic)

with open("services/api/integracoes/sankhya/services/sync_service.py", "w") as f:
    f.write(content)
