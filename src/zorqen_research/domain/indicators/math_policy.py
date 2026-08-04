"""Fixed deterministic Decimal math policy for indicators."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Context, localcontext

from zorqen_research.domain.indicators.errors import IndicatorValidationError

_MATH_SCHEMA = "1"
_DECIMAL_PRECISION = 50


@dataclass(frozen=True, slots=True, init=False)
class IndicatorMathPolicy:
    """
    Immutable, fixed indicator math policy.

    Callers cannot supply an alternate precision or rounding mode in Milestone 1.0.
    """

    schema_version: str
    decimal_precision: int
    rounding: str
    policy_id: str

    def __init__(self, *args: object, **kwargs: object) -> None:
        msg = "IndicatorMathPolicy must be obtained via default_math_policy()"
        raise IndicatorValidationError(msg)

    @classmethod
    def _create(cls) -> IndicatorMathPolicy:
        self = object.__new__(cls)
        object.__setattr__(self, "schema_version", _MATH_SCHEMA)
        object.__setattr__(self, "decimal_precision", _DECIMAL_PRECISION)
        object.__setattr__(self, "rounding", "ROUND_HALF_EVEN")
        object.__setattr__(
            self,
            "policy_id",
            f"indicator-math-v{_MATH_SCHEMA}-p{_DECIMAL_PRECISION}-half-even",
        )
        return self

    def decimal_context(self) -> Context:
        return Context(prec=self.decimal_precision, rounding=ROUND_HALF_EVEN)

    @contextmanager
    def local_decimal_context(self) -> Iterator[Context]:
        """Every division/recurrence must run inside this local context."""
        with localcontext(self.decimal_context()) as ctx:
            yield ctx


_DEFAULT_POLICY = IndicatorMathPolicy._create()


def default_math_policy() -> IndicatorMathPolicy:
    """Return the single fixed Milestone 1.0 math policy."""
    return _DEFAULT_POLICY


def require_period(period: object) -> int:
    """Validate a period/window argument."""
    if type(period) is not int or isinstance(period, bool):
        msg = "period must be a real int"
        raise IndicatorValidationError(msg)
    if period < 1:
        msg = "period must be >= 1"
        raise IndicatorValidationError(msg)
    if period > 1_000_000:
        msg = "period must be <= 1000000"
        raise IndicatorValidationError(msg)
    return period
