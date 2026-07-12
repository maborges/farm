import re
with open("services/api/integracoes/sankhya/routers/__init__.py", "r") as f:
    content = f.read()

# I need to remove:
# _sanitize_external_payload
# _build_external_key
# _serialize_history_item
# _serialize_pending_item
# listar_associacoes_externas_pendentes
# listar_associacoes_externas
# resumo_associacoes_externas
# reconciliar_associacao_externa

pattern = r"def _sanitize_external_payload[\s\S]*?async def _serialize_pending_item[\s\S]*?return ExternalRecordAssociationPendingItemResponse\.model_validate\(payload\)\n\n\n"
content = re.sub(pattern, "", content)

pattern = r"@router\.get\(\n    \"/associacoes/pendentes\",[\s\S]*?async def listar_associacoes_externas_pendentes[\s\S]*?return \[\n        await _serialize_pending_item[\s\S]*?for association in associations\n    \]\n\n\n"
content = re.sub(pattern, "", content)

pattern = r"@router\.get\(\n    \"/associacoes\",[\s\S]*?async def listar_associacoes_externas[\s\S]*?return \[\n        await _serialize_pending_item[\s\S]*?for association in associations\n    \]\n\n\n"
content = re.sub(pattern, "", content)

pattern = r"@router\.get\(\n    \"/associacoes/resumo\",[\s\S]*?async def resumo_associacoes_externas[\s\S]*?return ExternalRecordAssociationSummaryResponse\(\*\*summary\)\n\n\n"
content = re.sub(pattern, "", content)

pattern = r"@router\.post\(\n    \"/associacoes/{association_id}/reconciliar\",[\s\S]*?async def reconciliar_associacao_externa[\s\S]*?return await _serialize_pending_item\([\s\S]*?feature_code_by_id=feature_code_by_id,\n    \)\n"
content = re.sub(pattern, "", content)

# Clean up imports
content = re.sub(r"from integracoes\.schemas import \([\s\S]*?ExternalRecordAssociationSummaryResponse,\n\)\nfrom integracoes\.services import ExternalRecordAssociationService, DuplicateAssociationError", "", content)
content = re.sub(r"def get_external_association_service\([\s\S]*?    return ExternalRecordAssociationService\(db\)\n", "", content)
content = content.replace("from integracoes.models import (\n    ExternalRecordAssociation,\n    ExternalRecordAssociationStatus,\n    IntegrationFeature,\n)", "")
content = content.replace("from integracoes.models import MarketplaceIntegracao, ExternalRecordAssociationStatus", "")

with open("services/api/integracoes/sankhya/routers/__init__.py", "w") as f:
    f.write(content)
