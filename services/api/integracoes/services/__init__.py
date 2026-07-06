"""Services transversais do dominio de Integracoes."""

from .external_record_association_service import (
    DuplicateAssociationError,
    ExternalRecordAssociationService,
)

__all__ = [
    "DuplicateAssociationError",
    "ExternalRecordAssociationService",
]
