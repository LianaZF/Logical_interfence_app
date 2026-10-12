"""Загрузка базы знаний, входных данных и математический логический вывод."""

from __future__ import annotations

import csv
import io
import json
import math
from pathlib import Path

from inference_app.domain import (
    FeatureEvaluation,
    FeatureSpec,
    FuzzyRule,
    InferenceResult,
    InputDataset,
    InputObject,
    IntervalMembership,
    KnowledgeBase,
    RuleEvaluation,
)


class InferenceDataError(ValueError):
    """Файл базы знаний или входных данных имеет неподдерживаемый формат."""


class KnowledgeBaseLoader:
    """Читает структурированный экспорт правил первой программы."""

    def load(self, path: str | Path) -> KnowledgeBase:
        source_path = Path(path)
        try:
            payload = json.loads(source_path.read_text(encoding="utf-8-sig"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise InferenceDataError(f"Не удалось прочитать базу правил: {error}") from error

        if payload.get("format") != "neuro-fuzzy-rules" or payload.get("version") != 1:
            raise InferenceDataError("Выбранный файл не является базой правил .nfrules.")

        feature_names = tuple(str(name) for name in payload.get("feature_names", ()))
        if not feature_names:
            raise InferenceDataError("База правил не содержит входных признаков.")
        encodings = payload.get("column_encodings", ())
        rules = tuple(self._parse_rule(item, feature_names) for item in payload.get("rules", ()))
        if not rules:
            raise InferenceDataError("База правил не содержит правил второго типа.")
        feature_ranges = payload.get("feature_ranges", ())
        features = tuple(
            self._feature_spec(feature_name, encodings, feature_ranges, rules)
            for feature_name in feature_names
        )
        class_labels = tuple(str(item) for item in payload.get("class_labels", ()))
        if not class_labels:
            class_labels = tuple(dict.fromkeys(rule.consequent for rule in rules))
        return KnowledgeBase(
            source_path=source_path.resolve(),
            features=features,
            target_name=str(payload.get("target_name", "Класс")),
            class_labels=class_labels,
            rules=rules,
        )

    @staticmethod
    def _feature_spec(feature_name: str, encodings, feature_ranges, rules) -> FeatureSpec:
        minimum, maximum = _feature_bounds(feature_name, feature_ranges, rules)
        for item in encodings:
            if feature_name in item.get("output_names", ()):
                return FeatureSpec(
                    name=feature_name,
                    kind=str(item.get("kind", "numeric")),
                    categories=tuple(str(value) for value in item.get("categories", ())),
                    minimum=minimum,
                    maximum=maximum,
                )
        return FeatureSpec(
            name=feature_name,
            minimum=minimum,
            maximum=maximum,
        )

    @staticmethod
    def _parse_rule(item, feature_names: tuple[str, ...]) -> FuzzyRule:
        try:
            memberships = tuple(
                IntervalMembership(
                    feature_name=str(value["feature_name"]),
                    term_name=str(value["term_name"]),
                    left_base=_pair(value["left_base"]),
                    left_core=_pair(value["left_core"]),
                    right_core=_pair(value["right_core"]),
                    right_base=_pair(value["right_base"]),
                )
                for value in item["memberships"]
            )
            cf_low, cf_high = _pair(item["cf"])
            terms = tuple(str(value) for value in item["terms"])
        except (KeyError, TypeError, ValueError) as error:
            raise InferenceDataError("В базе правил найдено повреждённое правило.") from error
        if len(terms) != len(feature_names) or len(memberships) != len(feature_names):
            raise InferenceDataError("Число условий правила не совпадает с числом признаков.")
        if not 0.0 <= cf_low <= cf_high <= 1.0:
            raise InferenceDataError("Границы CF должны находиться в диапазоне от 0 до 1.")
        return FuzzyRule(
            number=int(item.get("number", 0)),
            terms=terms,
            consequent=str(item["consequent"]),
            cf_low=cf_low,
            cf_high=cf_high,
            memberships=memberships,
        )


class InputDatasetLoader:
    """Загружает пакет объектов и кодирует качественные значения по базе знаний."""

    def load(self, path: str | Path, knowledge_base: KnowledgeBase) -> InputDataset:
        source_path = Path(path)
        content = _read_text(source_path)
        rows = _read_rows(content)
        if len(rows) < 2:
            raise InferenceDataError("Файл должен содержать заголовок и хотя бы один объект.")
        header = tuple(cell.strip() for cell in rows[0])
        positions = {name: index for index, name in enumerate(header)}
        missing = [feature.name for feature in knowledge_base.features if feature.name not in positions]
        if missing:
            raise InferenceDataError(
                "В файле отсутствуют признаки: " + ", ".join(missing)
            )
        target_position = positions.get(knowledge_base.target_name)
        objects = []
        for row_number, row in enumerate(rows[1:], start=2):
            if len(row) != len(header):
                raise InferenceDataError(
                    f"Строка {row_number}: ожидалось {len(header)} значений, получено {len(row)}."
                )
            values = tuple(
                parse_feature_value(row[positions[feature.name]], feature, row_number)
                for feature in knowledge_base.features
            )
            actual_class = None if target_position is None else row[target_position].strip() or None
            objects.append(InputObject(values=values, actual_class=actual_class))
        return InputDataset(source_path=source_path.resolve(), objects=tuple(objects))


class InferenceService:
    """Выполняет интервальную фаззификацию и выбор наиболее достоверного правила."""

    def infer(self, knowledge_base: KnowledgeBase, obj: InputObject) -> InferenceResult:
        if len(obj.values) != len(knowledge_base.features):
            raise InferenceDataError("Число входных значений не совпадает с базой правил.")
        evaluations = tuple(
            self.evaluate_rule(rule, obj.values)
            for rule in knowledge_base.rules
        )
        fired = tuple(
            sorted(
                (item for item in evaluations if item.fired),
                key=lambda item: (-item.point_score, item.rule.number),
            )
        )
        winner = fired[0] if fired else None
        return InferenceResult(
            predicted_class=None if winner is None else winner.rule.consequent,
            evaluations=evaluations,
            fired_rules=fired,
            winner=winner,
        )

    def evaluate_rule(
        self,
        rule: FuzzyRule,
        values: tuple[float | None, ...],
    ) -> RuleEvaluation:
        feature_results = tuple(
            _evaluate_feature(value, membership)
            for value, membership in zip(values, rule.memberships)
        )
        known = tuple(item for item in feature_results if item.input_value is not None)
        activation_low = min((item.membership_low for item in known), default=0.0)
        activation_high = min((item.membership_high for item in known), default=0.0)
        confidence_low = activation_low * rule.cf_low
        confidence_high = activation_high * rule.cf_high
        return RuleEvaluation(
            rule=rule,
            features=feature_results,
            activation_low=activation_low,
            activation_high=activation_high,
            confidence_low=confidence_low,
            confidence_high=confidence_high,
            point_score=nie_tan_score(confidence_low, confidence_high),
        )


def nie_tan_score(confidence_low: float, confidence_high: float) -> float:
    """Выполняет понижение типа интервала достоверности методом Ние-Тана."""

    return (confidence_low + confidence_high) / 2


def parse_feature_value(value: str, feature: FeatureSpec, row_number: int = 0) -> float | None:
    """Преобразует число или исходную категорию в значение модели."""

    text = value.strip()
    if not text:
        return None
    if feature.categories:
        try:
            return float(feature.categories.index(text))
        except ValueError as error:
            raise InferenceDataError(
                f"Строка {row_number}: неизвестное значение «{text}» признака «{feature.name}»."
            ) from error
    try:
        parsed = float(text.replace(",", "."))
    except ValueError as error:
        raise InferenceDataError(
            f"Строка {row_number}: «{text}» не является числом для признака «{feature.name}»."
        ) from error
    if not math.isfinite(parsed):
        raise InferenceDataError(f"Признак «{feature.name}» должен быть конечным числом.")
    return parsed


def _evaluate_feature(value: float | None, membership: IntervalMembership) -> FeatureEvaluation:
    if value is None:
        low = high = 1.0
    else:
        low = trapezoidal_value(
            value,
            (
                membership.left_base[1],
                membership.left_core[1],
                membership.right_core[0],
                membership.right_base[0],
            ),
        )
        high = trapezoidal_value(
            value,
            (
                membership.left_base[0],
                membership.left_core[0],
                membership.right_core[1],
                membership.right_base[1],
            ),
        )
    return FeatureEvaluation(
        feature_name=membership.feature_name,
        input_value=value,
        term_name=membership.term_name,
        membership_low=low,
        membership_high=high,
    )


def trapezoidal_value(value: float, points: tuple[float, float, float, float]) -> float:
    """Вычисляет значение трапецеидальной ФП, устойчивое к суженному ядру."""

    left_base, left_core, right_core, right_base = points
    if left_core > right_core:
        left_core = right_core = (left_core + right_core) / 2
    left_base = min(left_base, left_core)
    right_base = max(right_base, right_core)
    if value < left_base or value > right_base:
        return 0.0
    if left_core <= value <= right_core:
        return 1.0
    if value < left_core:
        return (value - left_base) / max(left_core - left_base, 1e-12)
    return (right_base - value) / max(right_base - right_core, 1e-12)


def _pair(values) -> tuple[float, float]:
    first, second = (float(value) for value in values)
    return min(first, second), max(first, second)


def _feature_bounds(feature_name: str, feature_ranges, rules) -> tuple[float | None, float | None]:
    """Читает исходный диапазон или восстанавливает его из опорных точек ФП."""

    for item in feature_ranges:
        if str(item.get("name", "")) != feature_name:
            continue
        try:
            minimum = float(item["minimum"])
            maximum = float(item["maximum"])
        except (KeyError, TypeError, ValueError):
            break
        if math.isfinite(minimum) and math.isfinite(maximum):
            return min(minimum, maximum), max(minimum, maximum)

    support_values = []
    for rule in rules:
        for membership in rule.memberships:
            if membership.feature_name != feature_name:
                continue
            support_values.extend(membership.left_base)
            support_values.extend(membership.right_base)
    if not support_values:
        return None, None
    return min(support_values), max(support_values)


def _read_text(path: Path) -> str:
    try:
        content = path.read_bytes()
    except OSError as error:
        raise InferenceDataError(f"Не удалось прочитать входные данные: {error}") from error
    for encoding in ("utf-8-sig", "cp1251", "cp1252"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise InferenceDataError("Поддерживаются кодировки UTF-8, Windows-1251 и Windows-1252.")


def _read_rows(content: str) -> list[tuple[str, ...]]:
    first_line = next((line for line in content.splitlines() if line.strip()), "")
    delimiter = max(("\t", ";", ","), key=first_line.count)
    if delimiter not in first_line:
        raise InferenceDataError("Не удалось определить разделитель входного файла.")
    return [
        tuple(cell.strip() for cell in row)
        for row in csv.reader(io.StringIO(content), delimiter=delimiter)
        if any(cell.strip() for cell in row)
    ]
