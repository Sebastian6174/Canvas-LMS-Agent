from src.activities.rules import (
    normalize_activity_type,
    format_activity_display_name,
    infer_evaluation_type,
    ACTIVITY_TYPE_DEFAULT,
)


def test_normalize_activity_type_defaults_to_otros():
    assert normalize_activity_type("desconocido") == ACTIVITY_TYPE_DEFAULT
    assert normalize_activity_type("taller") == ACTIVITY_TYPE_DEFAULT
    assert normalize_activity_type(None) == ACTIVITY_TYPE_DEFAULT


def test_format_activity_display_name():
    assert (
        format_activity_display_name(2, "Foro", "Debate sobre el tema")
        == "Actividad 2. Foro: Debate sobre el tema"
    )
    prefixed = "Actividad 2. Foro: Debate sobre el tema"
    assert format_activity_display_name(2, "Foro", prefixed) == prefixed


def test_infer_evaluation_type_from_weight():
    assert infer_evaluation_type(0) == "Formativa"
    assert infer_evaluation_type(20) == "Evaluativa"
    assert infer_evaluation_type(0, "Evaluativa") == "Evaluativa"
