"""Adiciona padrões zoossanitários climáticos para espécies pecuárias adicionais."""

from alembic import op
import sqlalchemy as sa

revision = "20260824_pecuaria_species_defaults"
down_revision = "20260823_clima_inteligencia_integrity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    modelos = [
        ("Suíno", 68, 74, 78, "UMN Extension: Heat stress in swine affects production", "https://extension.umn.edu/agriculture/animals-and-livestock/swine/heat-stress-swine-affects-production"),
        ("Aves de Corte", 76, 80, 83, "PMC: An acute, rather than progressive, increase of THI has severe effects in laying hens", "https://pmc.ncbi.nlm.nih.gov/articles/PMC7674306/"),
        ("Aves de Postura", 76, 80, 83, "PMC: An acute, rather than progressive, increase of THI has severe effects in laying hens", "https://pmc.ncbi.nlm.nih.gov/articles/PMC7674306/"),
        ("Bubalino", 75, 80, 85, "Acta Amazonica: bioclimatologia de búfalas Murrah", "https://acta.inpa.gov.br/fasciculos/41-3/BODY/v41n3a14.html"),
        ("Asinino", 72, 78, 83, "PubMed: rectal temperature responses of donkeys under heat and packing stress", "https://pubmed.ncbi.nlm.nih.gov/22869338/"),
    ]
    for especie, medio, alto, critico, fonte, url in modelos:
        op.execute(
            sa.text(
                """
            INSERT INTO modelos_zoosanitarios
                (id, tenant_id, especie, tipo_risco, regras_risco, is_global)
            SELECT gen_random_uuid(), NULL, :especie, 'Estresse Térmico',
                jsonb_build_object(
                    'nivel_medio', :medio, 'nivel_alto', :alto,
                    'nivel_critico', :critico, 'indice', 'ITH_CLÁSSICO',
                    'fonte_parametros', :fonte, 'fonte_url', :url,
                    'observacao', 'Referência ambiental preventiva; validar com responsável técnico e microclima local.'
                ), true
            WHERE NOT EXISTS (
                SELECT 1 FROM modelos_zoosanitarios
                WHERE tenant_id IS NULL AND especie = :especie AND tipo_risco = 'Estresse Térmico'
            )
                """
            ).bindparams(
                especie=especie,
                medio=medio,
                alto=alto,
                critico=critico,
                fonte=fonte,
                url=url,
            )
        )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM modelos_zoosanitarios
        WHERE tenant_id IS NULL AND is_global = true
          AND tipo_risco = 'Estresse Térmico'
          AND especie IN ('Suíno', 'Aves de Corte', 'Aves de Postura', 'Bubalino', 'Asinino')
        """
    )
