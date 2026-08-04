"""Adversarial provenance tests for indicator bundle and feed identity."""

from __future__ import annotations

from decimal import Decimal

import pytest

from tests.unit.indicator_helpers import indicator_input_from_specs
from zorqen_research.application.indicator_views.feed import IndicatorDecisionFeed
from zorqen_research.application.indicators.ema import ema_close
from zorqen_research.application.indicators.serialization import (
    hash_indicator_series,
    hash_indicator_series_payload,
)
from zorqen_research.application.indicators.volatility import true_range, wilder_atr
from zorqen_research.domain.indicator_views.bundles import IndicatorSeriesBundle
from zorqen_research.domain.indicator_views.errors import IndicatorViewValidationError
from zorqen_research.domain.indicator_views.keys import IndicatorSeriesKey
from zorqen_research.domain.indicators.enums import IndicatorCode
from zorqen_research.domain.indicators.inputs import IndicatorInput
from zorqen_research.domain.indicators.math_policy import (
    IndicatorMathPolicy,
    default_math_policy,
)
from zorqen_research.domain.indicators.results import IndicatorSeries
from zorqen_research.domain.symbols import Symbol
from zorqen_research.domain.timeframes import Timeframe


def _specs() -> tuple[tuple[str, str, str, str], ...]:
    return (
        ("10", "11", "9", "10"),
        ("11", "12", "10", "11"),
        ("12", "13", "11", "12"),
        ("13", "14", "12", "13"),
        ("14", "15", "13", "14"),
    )


def _forge_series(
    *,
    template: IndicatorSeries,
    values: tuple[Decimal | None, ...] | None = None,
    first_defined_index: int | None | object = ...,
    defined_value_count: int | object = ...,
    value_count: int | object = ...,
    parameters: tuple[tuple[str, int], ...] | object = ...,
    schema_version: str | object = ...,
    math_policy: IndicatorMathPolicy | object = ...,
    input_candle_sha256: str | object = ...,
    input_candle_count: int | object = ...,
    result_hash: str | None = None,
) -> IndicatorSeries:
    """Fully populate an exact IndicatorSeries via object.__new__."""
    use_values = template.values if values is None else values
    use_first = template.first_defined_index if first_defined_index is ... else first_defined_index
    use_defined = (
        template.defined_value_count if defined_value_count is ... else defined_value_count
    )
    use_count = template.value_count if value_count is ... else value_count
    use_params = template.parameters if parameters is ... else parameters
    use_schema = template.schema_version if schema_version is ... else schema_version
    use_policy = template.math_policy if math_policy is ... else math_policy
    use_candle_hash = (
        template.input_candle_sha256 if input_candle_sha256 is ... else input_candle_sha256
    )
    use_candle_count = (
        template.input_candle_count if input_candle_count is ... else input_candle_count
    )
    assert isinstance(use_params, tuple)
    assert isinstance(use_schema, str)
    assert isinstance(use_policy, IndicatorMathPolicy)
    assert isinstance(use_candle_hash, str)
    assert isinstance(use_candle_count, int)
    assert isinstance(use_count, int)
    assert isinstance(use_defined, int)
    digest = (
        result_hash
        if result_hash is not None
        else hash_indicator_series_payload(
            schema_version=use_schema,
            indicator_code=template.indicator_code,
            symbol=template.symbol,
            timeframe=template.timeframe,
            input_candle_sha256=use_candle_hash,
            input_candle_count=use_candle_count,
            parameters=use_params,
            first_defined_index=use_first,  # type: ignore[arg-type]
            defined_value_count=use_defined,
            math_policy=use_policy,
            values=use_values,
        )
    )
    forged = object.__new__(IndicatorSeries)
    object.__setattr__(forged, "schema_version", use_schema)
    object.__setattr__(forged, "indicator_code", template.indicator_code)
    object.__setattr__(forged, "symbol", template.symbol)
    object.__setattr__(forged, "timeframe", template.timeframe)
    object.__setattr__(forged, "input_candle_sha256", use_candle_hash)
    object.__setattr__(forged, "input_candle_count", use_candle_count)
    object.__setattr__(forged, "parameters", use_params)
    object.__setattr__(forged, "value_count", use_count)
    object.__setattr__(forged, "values", use_values)
    object.__setattr__(forged, "first_defined_index", use_first)
    object.__setattr__(forged, "defined_value_count", use_defined)
    object.__setattr__(forged, "math_policy", use_policy)
    object.__setattr__(forged, "result_hash", digest)
    assert hash_indicator_series(forged) == forged.result_hash
    return forged


def _forge_input_from(
    template: IndicatorInput,
    *,
    candle_count: int | None = None,
    candle_sha256: str | None = None,
    input_hash: str | None = None,
) -> IndicatorInput:
    forged = object.__new__(IndicatorInput)
    object.__setattr__(forged, "symbol", template.symbol)
    object.__setattr__(forged, "timeframe", template.timeframe)
    object.__setattr__(forged, "candles", template.candles)
    object.__setattr__(
        forged,
        "candle_count",
        template.candle_count if candle_count is None else candle_count,
    )
    object.__setattr__(forged, "minimum_open_time", template.minimum_open_time)
    object.__setattr__(forged, "maximum_open_time", template.maximum_open_time)
    object.__setattr__(
        forged,
        "candle_sha256",
        template.candle_sha256 if candle_sha256 is None else candle_sha256,
    )
    object.__setattr__(
        forged,
        "input_hash",
        template.input_hash if input_hash is None else input_hash,
    )
    return forged


def _clone_bundle(
    template: IndicatorSeriesBundle,
    *,
    bundle_hash: str | None = None,
    input_candle_count: int | None = None,
    input_hash: str | None = None,
    symbol: Symbol | None = None,
    timeframe: Timeframe | None = None,
    series_count: int | None = None,
    series: tuple[IndicatorSeries, ...] | None = None,
    series_keys: tuple[IndicatorSeriesKey, ...] | None = None,
    indicator_input: IndicatorInput | None = None,
) -> IndicatorSeriesBundle:
    forged = object.__new__(IndicatorSeriesBundle)
    object.__setattr__(forged, "schema_version", template.schema_version)
    object.__setattr__(forged, "symbol", template.symbol if symbol is None else symbol)
    object.__setattr__(
        forged,
        "timeframe",
        template.timeframe if timeframe is None else timeframe,
    )
    object.__setattr__(
        forged,
        "input_candle_count",
        template.input_candle_count if input_candle_count is None else input_candle_count,
    )
    object.__setattr__(forged, "input_candle_hash", template.input_candle_hash)
    object.__setattr__(
        forged,
        "input_hash",
        template.input_hash if input_hash is None else input_hash,
    )
    use_series = template.series if series is None else series
    use_keys = template.series_keys if series_keys is None else series_keys
    object.__setattr__(forged, "series", use_series)
    object.__setattr__(
        forged,
        "series_count",
        len(use_series) if series_count is None else series_count,
    )
    object.__setattr__(forged, "series_keys", use_keys)
    object.__setattr__(
        forged,
        "bundle_hash",
        template.bundle_hash if bundle_hash is None else bundle_hash,
    )
    object.__setattr__(
        forged,
        "indicator_input",
        template.indicator_input if indicator_input is None else indicator_input,
    )
    return forged


# --- Exact input ---


def test_provenance_input_subclass_rejected_before_override() -> None:
    class EvilInput(IndicatorInput):
        def __getattribute__(self, name: str) -> object:
            raise AssertionError(f"subclass attribute accessed: {name}")

    subclassed = object.__new__(EvilInput)
    with pytest.raises(IndicatorViewValidationError, match="exact IndicatorInput"):
        IndicatorSeriesBundle.from_verified(indicator_input=subclassed, series=())


def test_provenance_input_subclass_isinstance_not_enough() -> None:
    class SubInput(IndicatorInput):
        pass

    real = indicator_input_from_specs(_specs())
    # Populate a subclass instance with real fields — still rejected by exact type.
    subclassed = object.__new__(SubInput)
    for field in (
        "symbol",
        "timeframe",
        "candles",
        "candle_count",
        "minimum_open_time",
        "maximum_open_time",
        "candle_sha256",
        "input_hash",
    ):
        object.__setattr__(subclassed, field, getattr(real, field))
    assert isinstance(subclassed, IndicatorInput)
    assert type(subclassed) is not IndicatorInput
    with pytest.raises(IndicatorViewValidationError, match="exact IndicatorInput"):
        IndicatorSeriesBundle.from_verified(
            indicator_input=subclassed,
            series=(ema_close(real, 3),),
        )


def test_provenance_forged_input_false_count_hash_rejected() -> None:
    real = indicator_input_from_specs(_specs())
    series = (ema_close(real, 3),)
    with pytest.raises(IndicatorViewValidationError, match="candle_count"):
        IndicatorSeriesBundle.from_verified(
            indicator_input=_forge_input_from(real, candle_count=999),
            series=series,
        )
    with pytest.raises(IndicatorViewValidationError, match="candle_sha256"):
        IndicatorSeriesBundle.from_verified(
            indicator_input=_forge_input_from(real, candle_sha256="ab" * 32),
            series=series,
        )
    with pytest.raises(IndicatorViewValidationError, match="input_hash"):
        IndicatorSeriesBundle.from_verified(
            indicator_input=_forge_input_from(real, input_hash="cd" * 32),
            series=series,
        )


def test_provenance_valid_input_accepted() -> None:
    real = indicator_input_from_specs(_specs())
    bundle = IndicatorSeriesBundle.from_verified(
        indicator_input=real,
        series=(ema_close(real, 3),),
    )
    assert bundle.indicator_input is real or bundle.indicator_input.input_hash == real.input_hash
    assert bundle.input_candle_count == real.candle_count


# --- Forged series with matching self-hashes ---


def test_provenance_forged_ema_false_values_matching_hash_fails() -> None:
    real = indicator_input_from_specs(_specs())
    template = ema_close(real, 3)
    false_values = tuple(Decimal("999") if value is not None else None for value in template.values)
    forged = _forge_series(template=template, values=false_values)
    assert hash_indicator_series(forged) == forged.result_hash
    with pytest.raises(IndicatorViewValidationError, match="byte-identical|values"):
        IndicatorSeriesBundle.from_verified(indicator_input=real, series=(forged,))


def test_provenance_forged_ema_false_warmup_matching_hash_fails() -> None:
    real = indicator_input_from_specs(_specs())
    template = ema_close(real, 3)
    # Collapse warmup: put a defined value too early.
    false_values = (Decimal("10"), Decimal("11"), Decimal("12"), Decimal("13"), Decimal("14"))
    forged = _forge_series(
        template=template,
        values=false_values,
        first_defined_index=0,
        defined_value_count=5,
    )
    with pytest.raises(IndicatorViewValidationError):
        IndicatorSeriesBundle.from_verified(indicator_input=real, series=(forged,))


def test_provenance_forged_negative_atr_matching_hash_fails() -> None:
    real = indicator_input_from_specs(_specs())
    template = wilder_atr(real, 3)
    false_values = tuple(
        (Decimal("-1") if value is not None else None) for value in template.values
    )
    forged = _forge_series(template=template, values=false_values)
    with pytest.raises(IndicatorViewValidationError):
        IndicatorSeriesBundle.from_verified(indicator_input=real, series=(forged,))


def test_provenance_forged_true_range_false_values_matching_hash_fails() -> None:
    real = indicator_input_from_specs(_specs())
    template = true_range(real)
    false_values = tuple(Decimal("42") for _ in template.values)
    forged = _forge_series(template=template, values=false_values)
    with pytest.raises(IndicatorViewValidationError):
        IndicatorSeriesBundle.from_verified(indicator_input=real, series=(forged,))


def test_provenance_forged_metadata_fields_matching_hash_fail() -> None:
    real = indicator_input_from_specs(_specs())
    template = ema_close(real, 3)
    with pytest.raises(IndicatorViewValidationError):
        IndicatorSeriesBundle.from_verified(
            indicator_input=real,
            series=(_forge_series(template=template, first_defined_index=0),),
        )
    with pytest.raises(IndicatorViewValidationError):
        IndicatorSeriesBundle.from_verified(
            indicator_input=real,
            series=(_forge_series(template=template, defined_value_count=99),),
        )
    with pytest.raises(IndicatorViewValidationError):
        IndicatorSeriesBundle.from_verified(
            indicator_input=real,
            series=(_forge_series(template=template, value_count=99),),
        )
    with pytest.raises(IndicatorViewValidationError):
        IndicatorSeriesBundle.from_verified(
            indicator_input=real,
            series=(_forge_series(template=template, parameters=(("period", 9),)),),
        )
    with pytest.raises(IndicatorViewValidationError):
        IndicatorSeriesBundle.from_verified(
            indicator_input=real,
            series=(_forge_series(template=template, schema_version="999"),),
        )


def test_provenance_forged_alternate_math_policy_fails() -> None:
    real = indicator_input_from_specs(_specs())
    template = ema_close(real, 3)
    alt = object.__new__(IndicatorMathPolicy)
    object.__setattr__(alt, "schema_version", "1")
    object.__setattr__(alt, "decimal_precision", 50)
    object.__setattr__(alt, "rounding", "ROUND_HALF_EVEN")
    object.__setattr__(alt, "policy_id", "forged-policy")
    forged = _forge_series(template=template, math_policy=alt)
    with pytest.raises(IndicatorViewValidationError):
        IndicatorSeriesBundle.from_verified(indicator_input=real, series=(forged,))


def test_provenance_forged_unrelated_candle_identity_fails() -> None:
    left = indicator_input_from_specs(_specs())
    right = indicator_input_from_specs(
        (
            ("10", "11", "9", "10"),
            ("11", "12", "10", "11"),
            ("12", "13", "11", "12"),
            ("13", "14", "12", "13"),
            ("99", "100", "98", "99"),
        )
    )
    template = ema_close(right, 3)
    forged = _forge_series(
        template=template,
        input_candle_sha256=left.candle_sha256,
        input_candle_count=left.candle_count,
    )
    # Point forged identity at left while values remain from right calculation.
    with pytest.raises(IndicatorViewValidationError):
        IndicatorSeriesBundle.from_verified(indicator_input=left, series=(forged,))


def test_provenance_byte_identical_forged_replaced_by_trusted() -> None:
    real = indicator_input_from_specs(_specs())
    trusted = ema_close(real, 3)
    forged = _forge_series(template=trusted, values=trusted.values)
    assert forged is not trusted
    assert hash_indicator_series(forged) == forged.result_hash
    bundle = IndicatorSeriesBundle.from_verified(indicator_input=real, series=(forged,))
    assert bundle.series[0] is not forged
    assert bundle.series[0].values == trusted.values
    assert bundle.series[0].result_hash == trusted.result_hash
    # Default policy identity retained from calculator path.
    assert bundle.series[0].math_policy is default_math_policy()


# --- Forged complete bundles at feed boundary ---


def test_provenance_forged_bundle_fields_rejected_by_feed() -> None:
    real = indicator_input_from_specs(_specs())
    valid = IndicatorSeriesBundle.from_verified(
        indicator_input=real,
        series=(ema_close(real, 3), wilder_atr(real, 3)),
    )
    cases = [
        _clone_bundle(valid, bundle_hash="0" * 64),
        _clone_bundle(valid, input_candle_count=999),
        _clone_bundle(valid, input_hash="11" * 32),
        _clone_bundle(valid, symbol=Symbol(value="ETHUSDT")),
        _clone_bundle(valid, timeframe=Timeframe.M5),
        _clone_bundle(valid, series_count=99),
        _clone_bundle(valid, series_keys=tuple(reversed(valid.series_keys))),
        _clone_bundle(
            valid,
            series_keys=(valid.series_keys[0],),
            series=(valid.series[0],),
            series_count=1,
        ),
        _clone_bundle(
            valid,
            series=valid.series + (true_range(real),),
            series_keys=valid.series_keys
            + (
                IndicatorSeriesKey.from_verified(
                    indicator_code=IndicatorCode.TRUE_RANGE,
                    parameters={},
                ),
            ),
            series_count=3,
        ),
    ]
    for forged in cases:
        with pytest.raises(IndicatorViewValidationError):
            IndicatorDecisionFeed.from_bundle(forged)


def test_provenance_forged_bundle_key_series_mismatch_rejected() -> None:
    real = indicator_input_from_specs(_specs())
    valid = IndicatorSeriesBundle.from_verified(
        indicator_input=real,
        series=(ema_close(real, 3), wilder_atr(real, 3)),
    )
    swapped = _clone_bundle(
        valid,
        series=valid.series,
        series_keys=(valid.series_keys[1], valid.series_keys[0]),
    )
    with pytest.raises(IndicatorViewValidationError):
        IndicatorDecisionFeed.from_bundle(swapped)


def test_provenance_forged_bundle_with_semantic_series_rejected() -> None:
    real = indicator_input_from_specs(_specs())
    valid = IndicatorSeriesBundle.from_verified(
        indicator_input=real,
        series=(ema_close(real, 3),),
    )
    false_values = tuple(
        Decimal("7") if value is not None else None for value in valid.series[0].values
    )
    forged_series = _forge_series(template=valid.series[0], values=false_values)
    forged = _clone_bundle(valid, series=(forged_series,))
    with pytest.raises(IndicatorViewValidationError):
        IndicatorDecisionFeed.from_bundle(forged)


def test_provenance_valid_bundle_feed_deterministic_and_retains_trusted() -> None:
    real = indicator_input_from_specs(_specs())
    valid = IndicatorSeriesBundle.from_verified(
        indicator_input=real,
        series=(wilder_atr(real, 3), ema_close(real, 3)),
    )
    feed_a = IndicatorDecisionFeed.from_bundle(valid)
    feed_b = IndicatorDecisionFeed.from_bundle(valid)
    assert feed_a.bundle.bundle_hash == valid.bundle_hash
    assert feed_b.bundle.bundle_hash == valid.bundle_hash
    assert feed_a.view_at(4).decision_view_hash == feed_b.view_at(4).decision_view_hash
    # Feed retains rebuilt trusted bundle (may be a distinct object with identical identity).
    assert feed_a.bundle.bundle_hash == feed_b.bundle.bundle_hash
    assert feed_a.bundle.series_keys == valid.series_keys
