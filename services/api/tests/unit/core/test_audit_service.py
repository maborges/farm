import uuid
from datetime import datetime, timezone

from core.services.audit_service import _serialize
from notificacoes.models import Notificacao


def test_serialize_usa_atributo_orm_em_vez_do_nome_fisico_da_coluna():
    """Modelos com alias ORM/coluna devem serializar o atributo correto."""
    tenant_id = uuid.uuid4()
    notificacao_id = uuid.uuid4()

    notif = Notificacao()
    notif.id = notificacao_id
    notif.tenant_id = tenant_id
    notif.tipo = "PREVISAO_CHUVA"
    notif.titulo = "Teste"
    notif.mensagem = "Mensagem"
    notif.nivel = "INFO"
    notif.lida = False
    notif.meta = {"talhao": "A1", "mm": 20}
    notif.origem = None
    notif.origem_id = None
    notif.usuario_id = None
    notif.created_at = datetime.now(timezone.utc)
    notif.read_at = None

    payload = _serialize(notif)

    assert payload is not None
    assert payload["id"] == str(notificacao_id)
    assert payload["tenant_id"] == str(tenant_id)
    assert payload["meta"] == {"talhao": "A1", "mm": 20}
    assert "metadata" not in payload
    assert payload["created_at"] == notif.created_at.isoformat()
