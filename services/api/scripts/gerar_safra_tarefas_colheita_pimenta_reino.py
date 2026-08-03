"""
1) Remove as PhaseTemplateTask genéricas do template de COLHEITA de pimenta-do-reino
   (id 81e7ba18-bc8c-446c-be52-4372e6302d1e) — as tarefas de colheita não fazem
   sentido consolidadas por safra, precisam ser por talhão.
2) Gera SafraTarefa reais (9 tarefas x 10 talhões) para a safra 2026/01.
Uso: PYTHONPATH=/opt/lampp/htdocs/farm/services/api python scripts/gerar_safra_tarefas_colheita_pimenta_reino.py
"""
import asyncio
import uuid
from sqlalchemy import select, delete, text
from core.database import async_session_maker
from agricola.models.templates import PhaseTemplateTask
from agricola.tarefas.models import SafraTarefa

# Registra todos os models no Base.metadata (evita NoReferencedTableError em FKs
# cruzadas), mesmo import usado por migrations/env.py.
from rh.models import ColaboradorRH, LancamentoDiaria, Empreitada  # noqa: F401
from agricola.safras.models import Safra, SafraTalhao, SafraFaseHistorico  # noqa: F401
from agricola.cultivos.models import Cultivo, CultivoArea  # noqa: F401
from agricola.production_units.models import ProductionUnit, StatusConsorcioArea  # noqa: F401
from agricola.operacoes.models import OperacaoAgricola, OperacaoExecucao, InsumoOperacao  # noqa: F401
from agricola.monitoramento.models import MonitoramentoPragas  # noqa: F401
from agricola.monitoramento.catalogo_model import MonitoramentoCatalogo  # noqa: F401
from agricola.analises_solo.models import AnaliseSolo, RegraAgronomica  # noqa: F401
from agricola.checklist.models import SafraChecklistItem  # noqa: F401
from agricola.fenologia.models import FenologiaEscala, SafraTalhaoGrupo, SafraTalhaoGrupoItem, SafraFenologiaRegistro  # noqa: F401
from agricola.romaneios.models import RomaneioColheita  # noqa: F401
from agricola.beneficiamento.models import LoteBeneficiamento  # noqa: F401
from agricola.previsoes.models import PrevisaoProdutividade  # noqa: F401
from agricola.ndvi.models import ImagemNDVI  # noqa: F401
from agricola.climatico.models import RegistroClima  # noqa: F401
from agricola.rastreabilidade.models import LoteRastreabilidade, CertificacaoPropriedade, CadernoLoteComercial  # noqa: F401
from agricola.agronomo.models import ConversaAgronomo, RelatorioTecnico  # noqa: F401
from agricola.cadastros.models import Cultura  # noqa: F401
from agricola.caderno.models import CadernoCampoEntrada, CadernoCampoFoto, CadernoEventoStatusHistorico, VisitaTecnica, EPIEntrega, CadernoExportacao  # noqa: F401
from agricola.colheita.models import ProdutoColhido  # noqa: F401
from agricola.a1_planejamento.models import ItemOrcamentoSafra  # noqa: F401
from agricola.custos.models import CostAllocation  # noqa: F401
from pecuaria.animal.models import LoteAnimal, Animal, EventoAnimal  # noqa: F401
from pecuaria.producao.models import ProducaoLeite  # noqa: F401
from pecuaria.models.manejo import ManejoLote  # noqa: F401
from core.cadastros.propriedades.models import AreaRural  # noqa: F401

TENANT_ID = uuid.UUID("7cff0925-417a-41f0-8aba-271b16052477")
TEMPLATE_ID = uuid.UUID("81e7ba18-bc8c-446c-be52-4372e6302d1e")
SAFRA_ID = uuid.UUID("37501fb5-63c2-4a87-8acc-d9c0eff7e548")

# (tipo, descricao, criticidade, ordem)
TASKS = [
    ("COLHEITA", "Colher cachos maduros por talhão", "CRITICA", 1),
    ("COLHEITA", "Transportar cachos colhidos até o terreiro/secador", "CRITICA", 2),
    ("COLHEITA", "Debulhar (separar grãos dos cachos)", "CRITICA", 3),
    ("COLHEITA", "Lavar/selecionar grãos (pimenta preta vs branca)", "NORMAL", 4),
    ("COLHEITA", "Secar grãos ao sol ou em secador até umidade adequada", "CRITICA", 5),
    ("COLHEITA", "Registrar produtividade colhida por talhão (kg/ha)", "NORMAL", 6),
    ("COLHEITA", "Armazenar grãos secos em local ventilado e protegido de umidade", "NORMAL", 7),
    ("COLHEITA", "Registrar custo de colheita e mão de obra utilizada", "OPCIONAL", 8),
    ("COLHEITA", "Emitir romaneio/nota de produção da safra", "OPCIONAL", 9),
]


async def main():
    async with async_session_maker() as session:
        # 1) remove PhaseTemplateTask genéricas
        result = await session.execute(
            delete(PhaseTemplateTask).where(PhaseTemplateTask.phase_template_id == TEMPLATE_ID)
        )
        removidas = result.rowcount

        # 2) busca talhões/cultivo_areas da safra
        talhoes = (await session.execute(text("""
            SELECT ca.id as cultivo_area_id, ar.id as talhao_id, ar.nome
            FROM farms.cultivo_areas ca
            JOIN farms.cultivos cu ON cu.id = ca.cultivo_id
            JOIN farms.cadastros_areas_rurais ar ON ar.id = ca.area_id
            WHERE cu.safra_id = :sid
        """), {"sid": SAFRA_ID})).fetchall()

        if not talhoes:
            print("Nenhum talhão encontrado para a safra.")
            return

        criadas = 0
        for cultivo_area_id, talhao_id, nome_talhao in talhoes:
            grupo_geracao_id = uuid.uuid4()
            for tipo, descricao, criticidade, ordem in TASKS:
                session.add(SafraTarefa(
                    tenant_id=TENANT_ID,
                    safra_id=SAFRA_ID,
                    talhao_id=talhao_id,
                    cultivo_area_id=cultivo_area_id,
                    grupo_geracao_id=grupo_geracao_id,
                    origem="TEMPLATE",
                    tipo=tipo,
                    fase="COLHEITA",
                    criticidade=criticidade,
                    descricao=f"{descricao} — {nome_talhao}",
                    prioridade="MEDIA",
                    status="PENDENTE_APROVACAO",
                ))
                criadas += 1

        await session.commit()
        print(f"PhaseTemplateTask removidas: {removidas}")
        print(f"SafraTarefa criadas: {criadas} ({len(talhoes)} talhões x {len(TASKS)} tarefas)")


if __name__ == "__main__":
    asyncio.run(main())
