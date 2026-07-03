from pathlib import Path

import yaml

DISPATCH_PATH = Path(__file__).resolve().parent.parent.parent / "schemas" / "dispatch.yaml"


class DispatchError(Exception):
    pass


def load_dispatch_table(path: Path | None = None) -> dict:
    """AD-12: the static, human-maintained operation-class -> tier table.
    Never learned or dynamically adjusted (out of scope until multi-run
    cost data exists)."""
    data = yaml.safe_load((path or DISPATCH_PATH).read_text())
    return data


def resolve_model(operation_class: str, config: dict, dispatch_table: dict | None = None) -> dict:
    """AD-12: launch-time model resolution. No call site names a concrete
    model — the operation class maps to a tier via `dispatch.yaml`, and the
    tier maps to a concrete model via the researcher's own `config.yaml`
    (`model_tiers`). A tier with no configured model is a refusal, not a
    silently-substituted default, since that would be a call site guessing
    on the researcher's behalf.
    """
    dispatch_table = dispatch_table or load_dispatch_table()
    operations = dispatch_table.get("operations", {})
    tier = operations.get(operation_class)
    if tier is None:
        raise DispatchError(
            f"'{operation_class}' is not a recognized operation class in dispatch.yaml"
        )

    if tier == "deterministic":
        return {"ok": True, "operation_class": operation_class, "tier": tier, "model": None}

    model_tiers = (config or {}).get("model_tiers", {})
    model = model_tiers.get(tier.replace("-", "_"))
    if not model:
        raise DispatchError(
            f"operation class '{operation_class}' resolves to tier '{tier}', but "
            f"config.yaml's model_tiers has no model configured for it"
        )
    return {"ok": True, "operation_class": operation_class, "tier": tier, "model": model}
