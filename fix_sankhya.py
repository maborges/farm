import re
with open("services/api/integracoes/sankhya/routers/__init__.py", "r") as f:
    content = f.read()

# Only remove the endpoints:
# @router.get("/associacoes/pendentes", ...
# @router.get("/associacoes", ...
# @router.get("/associacoes/resumo", ...
# @router.post("/associacoes/{association_id}/reconciliar", ...
content = re.sub(r"@router\.get\(\n    \"/associacoes/pendentes\",[\s\S]*?(?=@router\.get\(\n    \"/associacoes\",)", "", content)
content = re.sub(r"@router\.get\(\n    \"/associacoes\",[\s\S]*?(?=@router\.get\(\n    \"/associacoes/resumo\",)", "", content)
content = re.sub(r"@router\.get\(\n    \"/associacoes/resumo\",[\s\S]*?(?=@router\.post\(\n    \"/associacoes/{association_id}/reconciliar\",)", "", content)
content = re.sub(r"@router\.post\(\n    \"/associacoes/{association_id}/reconciliar\",[\s\S]*?(?=$)", "", content)

# Remove the helpers _sanitize_external_payload up to _serialize_pending_item
content = re.sub(r"def _sanitize_external_payload[\s\S]*?async def _serialize_pending_item[\s\S]*?return ExternalRecordAssociationPendingItemResponse\.model_validate\(payload\)\n", "", content)

# Clean up imports
content = re.sub(r"from integracoes\.schemas import \([\s\S]*?ExternalRecordAssociationSummaryResponse,\n\)\nfrom integracoes\.services import ExternalRecordAssociationService, DuplicateAssociationError", "", content)
content = re.sub(r"def get_external_association_service\([\s\S]*?    return ExternalRecordAssociationService\(db\)\n", "", content)
content = content.replace("from integracoes.models import (\n    ExternalRecordAssociation,\n    ExternalRecordAssociationStatus,\n    IntegrationFeature,\n)", "")

with open("services/api/integracoes/sankhya/routers/__init__.py", "w") as f:
    f.write(content)
