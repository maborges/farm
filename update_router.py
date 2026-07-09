import re

with open('services/api/wizard/router.py', 'r') as f:
    content = f.read()

# 1. Update _get_implantacao_ativa definition
old_def = """async def _get_implantacao_ativa(
    service: ImplantacaoService,
    tenant_id: uuid.UUID,
    *,
    unidade_produtiva_id: uuid.UUID | None = None,
) -> ImplantacaoOperacional:
    return await service.retomar_implantacao(
        tenant_id,
        unidade_produtiva_id=unidade_produtiva_id,
    )"""

new_def = """async def _get_implantacao_ativa(
    service: ImplantacaoService,
    tenant_id: uuid.UUID,
    owner_usuario_id: uuid.UUID,
    *,
    unidade_produtiva_id: uuid.UUID | None = None,
) -> ImplantacaoOperacional:
    from core.exceptions import EntityNotFoundError
    try:
        return await service.retomar_implantacao(
            tenant_id,
            unidade_produtiva_id=unidade_produtiva_id,
        )
    except EntityNotFoundError:
        return await service.create_or_get_active(
            tenant_id=tenant_id,
            owner_usuario_id=owner_usuario_id,
            unidade_produtiva_id=unidade_produtiva_id,
        )"""
content = content.replace(old_def, new_def)

# 2. Update calls to _get_implantacao_ativa to include current_user.id
content = re.sub(
    r'_get_implantacao_ativa\(\s*service,\s*tenant_id,',
    r'_get_implantacao_ativa(\n        service,\n        tenant_id,\n        current_user.id,',
    content
)

# 3. Remove "del current_user" inside endpoints that use current_user.id now
# Actually, since it's used, we can just remove all "del current_user" 
# or just specifically inside those functions. Let's just remove "del current_user\n    service = ImplantacaoService(session)" and replace with "service = ImplantacaoService(session)"
content = re.sub(r'    del current_user\n    service = ImplantacaoService\(session\)', r'    service = ImplantacaoService(session)', content)

# 4. Remove del current_user in endpoints that use current_user.id but might not be matched above.
# ver_detalhes_item_checklist has:
# del current_user
#     service = ImplantacaoService(session)
content = content.replace("    del current_user\n    service = ImplantacaoService(session)", "    service = ImplantacaoService(session)")

# also handle pausar_wizard/retomar_wizard which don't have del current_user because they use it for actor_user_id.

with open('services/api/wizard/router.py', 'w') as f:
    f.write(content)

print("Done")
