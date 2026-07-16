from typing import Optional, List, Dict
from pydantic import BaseModel, ConfigDict
import uuid
from decimal import Decimal
from datetime import datetime

class TerritoryReadView(BaseModel):
    unidade_produtiva_id: uuid.UUID
    exploracoes_rurais: List[Dict] = []
    propriedades: List[Dict] = []
    
    imovel_principal: Optional[Dict] = None
    imoveis_secundarios: List[Dict] = []
    associacoes: List[Dict] = []
    
    fonte_da_leitura: str
    estado_de_convergencia: str
    avisos: List[str] = []

    model_config = ConfigDict(from_attributes=True)
