from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from core.base_service import BaseService

from agricola.ndvi.models import ImagemNDVI
from agricola.ndvi.schemas import NDVICreate

class NDVIService(BaseService[ImagemNDVI]):
    def __init__(self, session: AsyncSession, tenant_id: UUID):
        super().__init__(ImagemNDVI, session, tenant_id)

    async def sync_sentinel2_data(self, talhao_id: UUID) -> str:
        # 1. Busca poligono do talhao
        # 2. Faz req Copernicus Data Space API (Sentinel-2) com base na bbox do poligono
        # 3. Filtra nuvens < 20%
        # 4. Baixa banda B04 e B08, calcula NDVI
        # 5. Salva color map no MinIO/S3 e registra no BD
        
        # Mock logic
        return "Sincronização agendada com sucesso"

    async def get_serie_temporal(self, talhao_id: UUID) -> dict:
        """OPERATIONS-GAP-01 §21.32: formato alinhado ao que o frontend real
        (`ndvi-talhao.tsx`) já espera (total_imagens/indice_atual/tendencia/dados)
        — antes retornava uma lista simples {data, ndvi}, incompatível com o
        componente, que sempre caía no estado vazio independentemente de haver
        dado real ou não."""
        imagens = sorted(await self.list_all(talhao_id=talhao_id), key=lambda img: img.data_captura)
        dados = [
            {
                "data": img.data_captura.isoformat(),
                "indice_medio": float(img.indice_medio) if img.indice_medio is not None else None,
                "cobertura_nuvens_pct": float(img.cobertura_nuvens_pct) if img.cobertura_nuvens_pct is not None else None,
            }
            for img in imagens
        ]

        indice_atual = dados[-1]["indice_medio"] if dados else None
        tendencia = None
        if len(dados) >= 2 and dados[-1]["indice_medio"] is not None and dados[-2]["indice_medio"] is not None:
            delta = dados[-1]["indice_medio"] - dados[-2]["indice_medio"]
            tendencia = "SUBINDO" if delta > 0.02 else "CAINDO" if delta < -0.02 else "ESTAVEL"

        return {
            "talhao_id": str(talhao_id),
            "total_imagens": len(dados),
            "indice_atual": indice_atual,
            "tendencia": tendencia,
            "dados": dados,
        }
