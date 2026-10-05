import re

with open("services/api/integracoes/sankhya/schemas/__init__.py", "r") as f:
    content = f.read()

# Add auth_model to SankhyaConfigCreate
auth_model_field = """    auth_model: str | None = Field(
        default=None,
        description="Modelo de autenticação: gateway_oauth_client_credentials ou gateway_legacy_login",
    )
    sankhya_environment: str"""

content = content.replace("    sankhya_environment: str", auth_model_field, 1)

with open("services/api/integracoes/sankhya/schemas/__init__.py", "w") as f:
    f.write(content)
