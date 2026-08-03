"""Immutable strategy parameter definitions and value validation."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from zorqen_research.domain.strategy_definitions.enums import ParameterKind
from zorqen_research.domain.strategy_definitions.errors import StrategyDefinitionValidationError
from zorqen_research.domain.strategy_definitions.identifiers import (
    MAX_DESCRIPTION_LENGTH,
    MAX_DISPLAY_NAME_LENGTH,
    MAX_ENUM_CHOICE_LENGTH,
    require_canonical_identifier,
    require_display_text,
)


def _require_real_bool(value: object, *, field: str) -> bool:
    if not isinstance(value, bool):
        msg = f"{field} must be a real bool"
        raise StrategyDefinitionValidationError(msg)
    return value


def _require_finite_decimal(value: object, *, field: str) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, Decimal):
        msg = f"{field} must be a Decimal"
        raise StrategyDefinitionValidationError(msg)
    if not value.is_finite():
        msg = f"{field} must be a finite Decimal"
        raise StrategyDefinitionValidationError(msg)
    return value


def _require_real_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        msg = f"{field} must be a real int"
        raise StrategyDefinitionValidationError(msg)
    return value


def _decimal_aligned(value: Decimal, *, minimum: Decimal | None, step: Decimal) -> bool:
    base = minimum if minimum is not None else Decimal("0")
    try:
        return (value - base) % step == Decimal("0")
    except InvalidOperation as exc:
        msg = "decimal step alignment failed"
        raise StrategyDefinitionValidationError(msg) from exc


def _int_aligned(value: int, *, minimum: int | None, step: int) -> bool:
    base = minimum if minimum is not None else 0
    return (value - base) % step == 0


@dataclass(frozen=True, slots=True)
class DecimalParameterDefinition:
    key: str
    display_name: str
    description: str
    researchable: bool
    default_value: Decimal
    minimum: Decimal | None = None
    maximum: Decimal | None = None
    step: Decimal | None = None

    def __post_init__(self) -> None:
        require_canonical_identifier(self.key, field="parameter.key")
        require_display_text(
            self.display_name, field="parameter.display_name", max_length=MAX_DISPLAY_NAME_LENGTH
        )
        require_display_text(
            self.description, field="parameter.description", max_length=MAX_DESCRIPTION_LENGTH
        )
        _require_real_bool(self.researchable, field="parameter.researchable")
        default = _require_finite_decimal(self.default_value, field="parameter.default_value")
        minimum = (
            None
            if self.minimum is None
            else _require_finite_decimal(self.minimum, field="parameter.minimum")
        )
        maximum = (
            None
            if self.maximum is None
            else _require_finite_decimal(self.maximum, field="parameter.maximum")
        )
        if minimum is not None and maximum is not None and minimum > maximum:
            msg = "parameter.minimum cannot exceed parameter.maximum"
            raise StrategyDefinitionValidationError(msg)
        if minimum is not None and default < minimum:
            msg = "parameter.default_value is below minimum"
            raise StrategyDefinitionValidationError(msg)
        if maximum is not None and default > maximum:
            msg = "parameter.default_value is above maximum"
            raise StrategyDefinitionValidationError(msg)
        if self.step is not None:
            step = _require_finite_decimal(self.step, field="parameter.step")
            if step <= 0:
                msg = "parameter.step must be strictly positive"
                raise StrategyDefinitionValidationError(msg)
            if not _decimal_aligned(default, minimum=minimum, step=step):
                msg = "parameter.default_value must align exactly to step"
                raise StrategyDefinitionValidationError(msg)

    @property
    def kind(self) -> ParameterKind:
        return ParameterKind.DECIMAL

    def validate_value(self, value: object) -> Decimal:
        parsed = _require_finite_decimal(value, field=f"parameters.{self.key}")
        if self.minimum is not None and parsed < self.minimum:
            msg = f"parameters.{self.key} is below minimum"
            raise StrategyDefinitionValidationError(msg)
        if self.maximum is not None and parsed > self.maximum:
            msg = f"parameters.{self.key} is above maximum"
            raise StrategyDefinitionValidationError(msg)
        if self.step is not None and not _decimal_aligned(
            parsed, minimum=self.minimum, step=self.step
        ):
            msg = f"parameters.{self.key} must align exactly to step"
            raise StrategyDefinitionValidationError(msg)
        return parsed


@dataclass(frozen=True, slots=True)
class IntegerParameterDefinition:
    key: str
    display_name: str
    description: str
    researchable: bool
    default_value: int
    minimum: int | None = None
    maximum: int | None = None
    step: int | None = None

    def __post_init__(self) -> None:
        require_canonical_identifier(self.key, field="parameter.key")
        require_display_text(
            self.display_name, field="parameter.display_name", max_length=MAX_DISPLAY_NAME_LENGTH
        )
        require_display_text(
            self.description, field="parameter.description", max_length=MAX_DESCRIPTION_LENGTH
        )
        _require_real_bool(self.researchable, field="parameter.researchable")
        default = _require_real_int(self.default_value, field="parameter.default_value")
        minimum = (
            None
            if self.minimum is None
            else _require_real_int(self.minimum, field="parameter.minimum")
        )
        maximum = (
            None
            if self.maximum is None
            else _require_real_int(self.maximum, field="parameter.maximum")
        )
        if minimum is not None and maximum is not None and minimum > maximum:
            msg = "parameter.minimum cannot exceed parameter.maximum"
            raise StrategyDefinitionValidationError(msg)
        if minimum is not None and default < minimum:
            msg = "parameter.default_value is below minimum"
            raise StrategyDefinitionValidationError(msg)
        if maximum is not None and default > maximum:
            msg = "parameter.default_value is above maximum"
            raise StrategyDefinitionValidationError(msg)
        if self.step is not None:
            step = _require_real_int(self.step, field="parameter.step")
            if step <= 0:
                msg = "parameter.step must be an integer greater than zero"
                raise StrategyDefinitionValidationError(msg)
            if not _int_aligned(default, minimum=minimum, step=step):
                msg = "parameter.default_value must align exactly to step"
                raise StrategyDefinitionValidationError(msg)

    @property
    def kind(self) -> ParameterKind:
        return ParameterKind.INTEGER

    def validate_value(self, value: object) -> int:
        parsed = _require_real_int(value, field=f"parameters.{self.key}")
        if self.minimum is not None and parsed < self.minimum:
            msg = f"parameters.{self.key} is below minimum"
            raise StrategyDefinitionValidationError(msg)
        if self.maximum is not None and parsed > self.maximum:
            msg = f"parameters.{self.key} is above maximum"
            raise StrategyDefinitionValidationError(msg)
        if self.step is not None and not _int_aligned(parsed, minimum=self.minimum, step=self.step):
            msg = f"parameters.{self.key} must align exactly to step"
            raise StrategyDefinitionValidationError(msg)
        return parsed


@dataclass(frozen=True, slots=True)
class BooleanParameterDefinition:
    key: str
    display_name: str
    description: str
    researchable: bool
    default_value: bool

    def __post_init__(self) -> None:
        require_canonical_identifier(self.key, field="parameter.key")
        require_display_text(
            self.display_name, field="parameter.display_name", max_length=MAX_DISPLAY_NAME_LENGTH
        )
        require_display_text(
            self.description, field="parameter.description", max_length=MAX_DESCRIPTION_LENGTH
        )
        _require_real_bool(self.researchable, field="parameter.researchable")
        _require_real_bool(self.default_value, field="parameter.default_value")

    @property
    def kind(self) -> ParameterKind:
        return ParameterKind.BOOLEAN

    def validate_value(self, value: object) -> bool:
        return _require_real_bool(value, field=f"parameters.{self.key}")


@dataclass(frozen=True, slots=True)
class EnumParameterDefinition:
    key: str
    display_name: str
    description: str
    researchable: bool
    default_value: str
    choices: tuple[str, ...]

    def __post_init__(self) -> None:
        require_canonical_identifier(self.key, field="parameter.key")
        require_display_text(
            self.display_name, field="parameter.display_name", max_length=MAX_DISPLAY_NAME_LENGTH
        )
        require_display_text(
            self.description, field="parameter.description", max_length=MAX_DESCRIPTION_LENGTH
        )
        _require_real_bool(self.researchable, field="parameter.researchable")
        if not isinstance(self.choices, tuple):
            msg = "parameter.choices must be an immutable tuple"
            raise StrategyDefinitionValidationError(msg)
        if len(self.choices) < 2:
            msg = "parameter.choices must contain at least two values"
            raise StrategyDefinitionValidationError(msg)
        cleaned: list[str] = []
        seen: set[str] = set()
        for choice in self.choices:
            if not isinstance(choice, str):
                msg = "parameter.choices must be strings"
                raise StrategyDefinitionValidationError(msg)
            if not choice or choice != choice.strip():
                msg = "parameter.choices must be trimmed non-empty strings"
                raise StrategyDefinitionValidationError(msg)
            if "\x00" in choice:
                msg = "parameter.choices must not contain NUL characters"
                raise StrategyDefinitionValidationError(msg)
            if len(choice) > MAX_ENUM_CHOICE_LENGTH:
                msg = f"parameter.choices exceed maximum length {MAX_ENUM_CHOICE_LENGTH}"
                raise StrategyDefinitionValidationError(msg)
            if choice in seen:
                msg = f"duplicate parameter choice: {choice!r}"
                raise StrategyDefinitionValidationError(msg)
            seen.add(choice)
            cleaned.append(choice)
        if self.default_value not in cleaned:
            msg = "parameter.default_value must exactly equal one choice"
            raise StrategyDefinitionValidationError(msg)

    @property
    def kind(self) -> ParameterKind:
        return ParameterKind.ENUM

    def validate_value(self, value: object) -> str:
        if not isinstance(value, str):
            msg = f"parameters.{self.key} must be a string"
            raise StrategyDefinitionValidationError(msg)
        if value not in self.choices:
            msg = f"parameters.{self.key} must equal one of the defined choices"
            raise StrategyDefinitionValidationError(msg)
        return value


type StrategyParameterDefinition = (
    DecimalParameterDefinition
    | IntegerParameterDefinition
    | BooleanParameterDefinition
    | EnumParameterDefinition
)
