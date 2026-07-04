import pytest

from kagami.kernel.dispatch import DispatchError, load_dispatch_table, resolve_model


def test_dispatch_table_loads_and_lists_the_four_tiers():
    table = load_dispatch_table()
    assert set(table["tiers"]) == {
        "deterministic",
        "deterministic-ml",
        "cheap-model",
        "frontier-model",
    }


def test_a_deterministic_operation_resolves_with_no_model_needed():
    result = resolve_model("staleness_propagation", config={})
    assert result["ok"] is True
    assert result["tier"] == "deterministic"
    assert result["model"] is None


def test_a_cheap_model_operation_resolves_to_the_configured_model():
    config = {"model_tiers": {"cheap_model": "claude-haiku-4-5"}}
    result = resolve_model("paper_card_extraction", config=config)
    assert result["ok"] is True
    assert result["tier"] == "cheap-model"
    assert result["model"] == "claude-haiku-4-5"


def test_a_frontier_model_operation_resolves_to_the_configured_model():
    config = {"model_tiers": {"frontier_model": "claude-fable-5"}}
    result = resolve_model("dossier_drafting", config=config)
    assert result["tier"] == "frontier-model"
    assert result["model"] == "claude-fable-5"


def test_no_call_site_may_name_a_concrete_model_directly():
    # AD-12: resolve_model's signature takes only an operation_class and
    # config — there is no parameter through which a caller could pass a
    # model name directly, which is the point being tested here.
    import inspect

    params = inspect.signature(resolve_model).parameters
    assert "model" not in params
    assert set(params) == {"operation_class", "config", "dispatch_table"}


def test_an_unconfigured_tier_is_refused_not_silently_defaulted():
    with pytest.raises(DispatchError):
        resolve_model("paper_card_extraction", config={})


def test_an_unrecognized_operation_class_is_refused():
    with pytest.raises(DispatchError):
        resolve_model("not-a-real-operation", config={"model_tiers": {"cheap_model": "x"}})
