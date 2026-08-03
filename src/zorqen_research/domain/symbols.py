"""Canonical trading-symbol value objects."""

from __future__ import annotations

from dataclasses import dataclass

ALLOWED_SYMBOLS: frozenset[str] = frozenset({"BTCUSDT", "ETHUSDT", "BNBUSDT"})


@dataclass(frozen=True, slots=True)
class Symbol:
    """Uppercase canonical symbol approved for this milestone."""

    value: str

    def __post_init__(self) -> None:
        if self.value != self.value.upper() or any(ch.isspace() for ch in self.value):
            msg = f"Symbol must be uppercase without whitespace: {self.value!r}"
            raise ValueError(msg)
        if self.value not in ALLOWED_SYMBOLS:
            msg = f"Unsupported symbol for this milestone: {self.value!r}"
            raise ValueError(msg)

    def __str__(self) -> str:
        return self.value


def parse_symbol(value: str) -> Symbol:
    """Parse a symbol into its canonical form."""
    if any(ch.isspace() for ch in value):
        msg = f"Symbol must not contain whitespace: {value!r}"
        raise ValueError(msg)
    return Symbol(value=value.strip().upper())
