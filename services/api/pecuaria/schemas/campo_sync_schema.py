from datetime import datetime
from typing import List, Optional
import uuid

from pydantic import BaseModel, ConfigDict


class ManejoSyncResult(BaseModel):
    status: str
    total_recebido: int
    total_processado: int
    total_ignorados: int
    erros: list[str]
    tarefa_campo_id: uuid.UUID

    model_config = ConfigDict(from_attributes=True)


class SyncStatusResponse(BaseModel):
    tarefa_campo_id: uuid.UUID
    type: str
    status_tarefa: str
    status_processamento: str
    total_processado: int
    total_erros: int
    mensagem_erro: Optional[str] = None
    operador_id: Optional[uuid.UUID] = None
    lote_id: Optional[uuid.UUID] = None
    data_execucao: Optional[datetime] = None
    data_processamento: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class SyncStatusPaginatedResponse(BaseModel):
    items: List[SyncStatusResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

    model_config = ConfigDict(from_attributes=True)
