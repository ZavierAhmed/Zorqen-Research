"""Immutable strategy definition model."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from zorqen_research.domain.backtesting.enums import PositionDirection
from zorqen_research.domain.strategy_definitions.enums import DefinitionStatus
from zorqen_research.domain.strategy_definitions.errors import StrategyDefinitionValidationError
from zorqen_research.domain.strategy_definitions.identifiers import (
    MAX_DESCRIPTION_LENGTH,
    MAX_DISPLAY_NAME_LENGTH,
    MAX_WARMUP_BARS,
    SCHEMA_VERSION,
    require_canonical_identifier,
    require_definition_uuid,
    require_display_text,
    require_semantic_version,
    require_source_spec_sha256,
)
from zorqen_research.domain.strategy_definitions.parameters import (
    BooleanParameterDefinition,
    DecimalParameterDefinition,
    EnumParameterDefinition,
    IntegerParameterDefinition,
    StrategyParameterDefinition,
)
from zorqen_research.domain.strategy_definitions.timeframes import (
    TimeframeRequirement,
    require_canonical_context_requirements,
)
from zorqen_research.domain.strategy_families import require_seeded_family_pair
from zorqen_research.domain.timeframes import Timeframe


def _require_warmup(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        msg = "execution_warmup_bars must be a real int"
        raise StrategyDefinitionValidationError(msg)
    if value < 0:
        msg = "execution_warmup_bars must be greater than or equal to zero"
        raise StrategyDefinitionValidationError(msg)
    if value > MAX_WARMUP_BARS:
        msg = f"execution_warmup_bars exceeds maximum {MAX_WARMUP_BARS}"
        raise StrategyDefinitionValidationError(msg)
    return value


def require_canonical_directions(value: object) -> tuple[PositionDirection, ...]:
    if not isinstance(value, tuple):
        msg = "supported_directions must be an immutable tuple"
        raise StrategyDefinitionValidationError(msg)
    if not value:
        msg = "supported_directions must be non-empty"
        raise StrategyDefinitionValidationError(msg)
    for item in value:
        if not isinstance(item, PositionDirection):
            msg = "supported_directions must contain PositionDirection values"
            raise StrategyDefinitionValidationError(msg)
    if len(set(value)) != len(value):
        msg = "supported_directions must be unique"
        raise StrategyDefinitionValidationError(msg)
    expected = tuple(
        direction
        for direction in (PositionDirection.LONG, PositionDirection.SHORT)
        if direction in value
    )
    if value != expected:
        msg = "supported_directions must be in canonical order: long, then short"
        raise StrategyDefinitionValidationError(msg)
    return expected


def require_canonical_parameters(
    value: object,
) -> tuple[StrategyParameterDefinition, ...]:
    if not isinstance(value, tuple):
        msg = "parameters must be an immutable tuple"
        raise StrategyDefinitionValidationError(msg)
    keys: list[str] = []
    for item in value:
        if not isinstance(
            item,
            (
                DecimalParameterDefinition,
                IntegerParameterDefinition,
                BooleanParameterDefinition,
                EnumParameterDefinition,
            ),
        ):
            msg = "parameters must contain StrategyParameterDefinition values"
            raise StrategyDefinitionValidationError(msg)
        keys.append(item.key)
    if len(set(keys)) != len(keys):
        msg = "parameter keys must be unique"
        raise StrategyDefinitionValidationError(msg)
    expected_keys = tuple(sorted(keys))
    if tuple(keys) != expected_keys:
        msg = "parameters must be sorted lexicographically by key"
        raise StrategyDefinitionValidationError(msg)
    return value


@dataclass(frozen=True, slots=True)
class StrategyDefinition:
    schema_version: str
    definition_id: UUID
    family_id: UUID
    family_code: str
    definition_code: str
    display_name: str
    description: str
    version: str
    status: DefinitionStatus
    execution_timeframe: Timeframe
    execution_warmup_bars: int
    context_requirements: tuple[TimeframeRequirement, ...]
    supported_directions: tuple[PositionDirection, ...]
    parameters: tuple[StrategyParameterDefinition, ...]
    source_spec_sha256: str | None

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            msg = f"Unsupported schema_version: {self.schema_version!r}"
            raise StrategyDefinitionValidationError(msg)
        require_definition_uuid(self.definition_id)
        if not isinstance(self.family_id, UUID):
            msg = "family_id must be a UUID"
            raise StrategyDefinitionValidationError(msg)
        if self.family_id.int == 0:
            msg = "family_id must not be the nil UUID"
            raise StrategyDefinitionValidationError(msg)
        if not isinstance(self.family_code, str):
            msg = "family_code must be a string"
            raise StrategyDefinitionValidationError(msg)
        try:
            require_seeded_family_pair(family_id=self.family_id, family_code=self.family_code)
        except ValueError as exc:
            raise StrategyDefinitionValidationError(str(exc)) from exc
        require_canonical_identifier(self.definition_code, field="definition_code")
        require_display_text(
            self.display_name, field="display_name", max_length=MAX_DISPLAY_NAME_LENGTH
        )
        require_display_text(
            self.description, field="description", max_length=MAX_DESCRIPTION_LENGTH
        )
        require_semantic_version(self.version)
        if not isinstance(self.status, DefinitionStatus):
            msg = "status must be a DefinitionStatus"
            raise StrategyDefinitionValidationError(msg)
        if not isinstance(self.execution_timeframe, Timeframe):
            msg = "execution_timeframe must be a Timeframe"
            raise StrategyDefinitionValidationError(msg)
        _require_warmup(self.execution_warmup_bars)
        object.__setattr__(
            self,
            "context_requirements",
            require_canonical_context_requirements(
                self.context_requirements,
                execution_timeframe=self.execution_timeframe,
            ),
        )
        object.__setattr__(
            self,
            "supported_directions",
            require_canonical_directions(self.supported_directions),
        )
        object.__setattr__(self, "parameters", require_canonical_parameters(self.parameters))
        if self.status is DefinitionStatus.APPROVED:
            if self.source_spec_sha256 is None:
                msg = "approved definitions require source_spec_sha256"
                raise StrategyDefinitionValidationError(msg)
            require_source_spec_sha256(self.source_spec_sha256)
        elif self.source_spec_sha256 is not None:
            require_source_spec_sha256(self.source_spec_sha256)
