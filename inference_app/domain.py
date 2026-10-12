"""Предметные сущности программы логического вывода."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FeatureSpec:
    """Описание одного признака и способа ввода его значений."""

    name: str
    kind: str = "numeric"
    categories: tuple[str, ...] = ()
    minimum: float | None = None
    maximum: float | None = None


@dataclass(frozen=True)
class IntervalMembership:
    """Интервальная трапецеидальная функция принадлежности."""

    feature_name: str
    term_name: str
    left_base: tuple[float, float]
    left_core: tuple[float, float]
    right_core: tuple[float, float]
    right_base: tuple[float, float]


@dataclass(frozen=True)
class FuzzyRule:
    """Правило классификации второго типа."""

    number: int
    terms: tuple[str, ...]
    consequent: str
    cf_low: float
    cf_high: float
    memberships: tuple[IntervalMembership, ...]


@dataclass(frozen=True)
class KnowledgeBase:
    """Переносимая база знаний, сформированная первой программой."""

    source_path: Path
    features: tuple[FeatureSpec, ...]
    target_name: str
    class_labels: tuple[str, ...]
    rules: tuple[FuzzyRule, ...]


@dataclass(frozen=True)
class InputObject:
    """Один объект для классификации; None обозначает пропущенное значение."""

    values: tuple[float | None, ...]
    actual_class: str | None = None


@dataclass(frozen=True)
class InputDataset:
    """Пакет объектов, загруженный для логического вывода."""

    source_path: Path | None
    objects: tuple[InputObject, ...]


@dataclass(frozen=True)
class FeatureEvaluation:
    """Фаззификация одного входного значения условием правила."""

    feature_name: str
    input_value: float | None
    term_name: str
    membership_low: float
    membership_high: float


@dataclass(frozen=True)
class RuleEvaluation:
    """Полный расчёт активации и достоверности одного правила."""

    rule: FuzzyRule
    features: tuple[FeatureEvaluation, ...]
    activation_low: float
    activation_high: float
    confidence_low: float
    confidence_high: float
    point_score: float

    @property
    def fired(self) -> bool:
        return self.activation_high > 0.0 and self.confidence_high > 0.0


@dataclass(frozen=True)
class InferenceResult:
    """Результат классификации объекта и ранжированное множество правил."""

    predicted_class: str | None
    evaluations: tuple[RuleEvaluation, ...]
    fired_rules: tuple[RuleEvaluation, ...]
    winner: RuleEvaluation | None
