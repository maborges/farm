__all__ = [
    "OperationalCostAllocationService",
    "OperationalCostInput",
    "OperationalCostResult",
]


def __getattr__(name: str):
    if name in __all__:
        from .operational_cost_service import (
            OperationalCostAllocationService,
            OperationalCostInput,
            OperationalCostResult,
        )

        exports = {
            "OperationalCostAllocationService": OperationalCostAllocationService,
            "OperationalCostInput": OperationalCostInput,
            "OperationalCostResult": OperationalCostResult,
        }
        return exports[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
