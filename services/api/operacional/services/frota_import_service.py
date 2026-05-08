import csv
import uuid
import io
from datetime import datetime, timezone
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.cadastros.equipamentos.models import Equipamento
from operacional.models.abastecimento import Abastecimento
from operacional.models.frota import RegistroManutencao
from core.exceptions import BusinessRuleError

class FrotaImportService:
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        self.session = session
        self.tenant_id = tenant_id

    async def importar_abastecimentos(self, csv_content: str) -> Dict[str, Any]:
        """
        Importa abastecimentos a partir de um CSV.
        Template: equipamento_nome, data, horimetro, litros, preco_litro
        """
        f = io.StringIO(csv_content)
        reader = csv.DictReader(f)
        
        count = 0
        errors = []
        
        # Cache de equipamentos para evitar queries repetidas
        equipamentos_cache = {}
        
        for row_idx, row in enumerate(reader):
            try:
                nome_maq = row.get("equipamento_nome")
                if not nome_maq:
                    raise ValueError("Nome do equipamento é obrigatório")
                
                if nome_maq not in equipamentos_cache:
                    stmt = select(Equipamento).where(
                        Equipamento.tenant_id == self.tenant_id,
                        Equipamento.nome == nome_maq
                    )
                    maq = (await self.session.execute(stmt)).scalar_one_or_none()
                    if not maq:
                        raise ValueError(f"Equipamento '{nome_maq}' não encontrado")
                    equipamentos_cache[nome_maq] = maq
                
                maq = equipamentos_cache[nome_maq]
                
                data_str = row.get("data")
                try:
                    data_dt = datetime.fromisoformat(data_str.replace("/", "-")) if data_str else datetime.now(timezone.utc)
                except Exception:
                    data_dt = datetime.now(timezone.utc)

                litros = float(row.get("litros", 0))
                preco = float(row.get("preco_litro", 0))
                horimetro = float(row.get("horimetro", 0).replace(",", "."))
                
                novo_abast = Abastecimento(
                    id=uuid.uuid4(),
                    tenant_id=self.tenant_id,
                    equipamento_id=maq.id,
                    data=data_dt,
                    litros=litros,
                    preco_litro=preco,
                    custo_total=litros * preco,
                    horimetro_na_data=horimetro,
                    tanque_cheio=True,
                    local="INTERNO"
                )
                
                # Atualiza horimetro da máquina se for maior
                if horimetro > maq.horimetro_atual:
                    maq.horimetro_atual = horimetro
                
                self.session.add(novo_abast)
                count += 1
                
            except Exception as e:
                errors.append({"row": row_idx + 1, "error": str(e)})
        
        await self.session.commit()
        return {"imported": count, "errors": errors}

    async def importar_manutencoes(self, csv_content: str) -> Dict[str, Any]:
        """
        Importa registros de manutenção a partir de um CSV.
        Template: equipamento_nome, data, tipo, descricao, custo_total
        """
        f = io.StringIO(csv_content)
        reader = csv.DictReader(f)
        
        count = 0
        errors = []
        equipamentos_cache = {}
        
        for row_idx, row in enumerate(reader):
            try:
                nome_maq = row.get("equipamento_nome")
                if not nome_maq:
                    raise ValueError("Nome do equipamento é obrigatório")
                
                if nome_maq not in equipamentos_cache:
                    stmt = select(Equipamento).where(
                        Equipamento.tenant_id == self.tenant_id,
                        Equipamento.nome == nome_maq
                    )
                    maq = (await self.session.execute(stmt)).scalar_one_or_none()
                    if not maq:
                        raise ValueError(f"Equipamento '{nome_maq}' não encontrado")
                    equipamentos_cache[nome_maq] = maq
                
                maq = equipamentos_cache[nome_maq]
                
                data_str = row.get("data")
                try:
                    data_dt = datetime.fromisoformat(data_str.replace("/", "-")) if data_str else datetime.now(timezone.utc)
                except Exception:
                    data_dt = datetime.now(timezone.utc)

                registro = RegistroManutencao(
                    id=uuid.uuid4(),
                    equipamento_id=maq.id,
                    tipo=row.get("tipo", "CORRETIVA"),
                    descricao=row.get("descricao", "Importado via CSV"),
                    custo_total=float(row.get("custo_total", 0).replace(",", ".")),
                    data_realizacao=data_dt,
                    horimetro_na_data=maq.horimetro_atual
                )
                
                self.session.add(registro)
                count += 1
                
            except Exception as e:
                errors.append({"row": row_idx + 1, "error": str(e)})
        
        await self.session.commit()
        return {"imported": count, "errors": errors}
