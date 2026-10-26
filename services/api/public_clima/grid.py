"""Política de quantização e agrupamento geográfico para cache agrometeorológico."""

from __future__ import annotations


class GeoGridPolicy:
    """Define o agrupamento espacial de coordenadas em nós regulares de grid.

    Permite que múltiplos produtores em uma mesma microrregião ou microbacia
    compartilhem entradas de cache, reduzindo requisições externas desnecessárias.
    """

    def __init__(self, step_degrees: float = 0.05) -> None:
        """Inicializa a política de grid geográfico.

        Args:
            step_degrees: Passo angular do grid em graus (ex: 0.05 equivale a aprox. 5.5 km).

        Raises:
            ValueError: Se step_degrees for menor ou igual a zero.
        """
        if step_degrees <= 0:
            raise ValueError("O passo do grid geográfico deve ser maior que zero.")
        self.step_degrees = step_degrees

    def quantize(self, lat: float, lon: float) -> tuple[float, float]:
        """Quantiza latitude e longitude para o nó canônico mais próximo do grid.

        Args:
            lat: Latitude decimal dentro do intervalo [-90, 90].
            lon: Longitude decimal dentro do intervalo [-180, 180].

        Returns:
            Tupla contendo (latitude_grid, longitude_grid) arredondadas para 4 decimais.

        Raises:
            ValueError: Se as coordenadas estiverem fora dos limites do globo terrestre.
        """
        if not (-90.0 <= lat <= 90.0):
            raise ValueError(f"Latitude inválida ({lat}). Deve estar entre -90.0 e 90.0.")
        if not (-180.0 <= lon <= 180.0):
            raise ValueError(f"Longitude inválida ({lon}). Deve estar entre -180.0 e 180.0.")

        lat_grid = round(round(lat / self.step_degrees) * self.step_degrees, 4)
        lon_grid = round(round(lon / self.step_degrees) * self.step_degrees, 4)

        # Garante que os limites não sejam ultrapassados por arredondamento
        lat_grid = max(-90.0, min(90.0, lat_grid))
        lon_grid = max(-180.0, min(180.0, lon_grid))

        return lat_grid, lon_grid

    def cache_key(self, lat: float, lon: float) -> str:
        """Gera a chave normalizada de grid para identificação de cache.

        Args:
            lat: Latitude original.
            lon: Longitude original.

        Returns:
            String formatada no padrão 'lat:lon' do nó quantizado.
        """
        lat_grid, lon_grid = self.quantize(lat, lon)
        return f"{lat_grid:.4f}:{lon_grid:.4f}"
