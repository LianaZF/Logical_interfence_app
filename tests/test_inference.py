import json
import tempfile
import unittest
from types import SimpleNamespace
from pathlib import Path

from inference_app.app import InferenceApp, _feature_input_caption
from inference_app.domain import InputObject
from inference_app.localization import translate, translate_error
from inference_app.membership_view import membership_boundaries
from inference_app.services import InferenceService, InputDatasetLoader, KnowledgeBaseLoader, nie_tan_score


class LogicalInferenceTests(unittest.TestCase):
    def test_row_count_is_blank_without_input_data(self) -> None:
        class Value:
            def set(self, value):
                self.value = value

        app = SimpleNamespace(
            view_model=SimpleNamespace(knowledge_base=None, dataset=None),
            rows_var=Value(), features_var=Value(), classes_var=Value(),
        )
        for name in ("_populate_system_rules", "_populate_conflict_rules",
                     "_rebuild_feature_inputs", "_refresh_navigation", "_refresh_rule_details"):
            setattr(app, name, lambda: None)
        InferenceApp._refresh_all(app)
        self.assertEqual(app.rows_var.value, "")
        app.view_model.knowledge_base = SimpleNamespace(features=(1,), class_labels=(1, 2))
        InferenceApp._refresh_all(app)
        self.assertEqual(app.rows_var.value, "")
        app.view_model.dataset = SimpleNamespace(objects=(1, 2, 3))
        InferenceApp._refresh_all(app)
        self.assertEqual(app.rows_var.value, "3")
        app.view_model.dataset = None
        InferenceApp._refresh_all(app)
        self.assertEqual(app.rows_var.value, "")

    def test_updated_interface_translations(self) -> None:
        self.assertEqual(
            translate("Оценка достоверности решения (С)", "en"),
            "Decision confidence score (C)",
        )
        title = "Программа использования нечетких правил второго типа для решения задач классификации"
        self.assertEqual(translate(title, "ru"), title)
        self.assertEqual(translate(title, "en"),
                         "Application of type-2 fuzzy rules to classification problems")

    def test_navigation_uses_conflict_set_positions(self) -> None:
        class Control:
            def set(self, value):
                self.value = value

            def configure(self, **options):
                self.state = options["state"]

        app = SimpleNamespace(
            view_model=SimpleNamespace(dataset=None, result=None),
            mode_var=SimpleNamespace(get=lambda: "batch"),
            object_var=Control(), object_prev=Control(), object_next=Control(),
            rule_var=Control(), rule_prev=Control(), rule_next=Control(),
            selected_rule_number=41,
            _t=lambda text, **values: text.format(**values),
            _select_rule_in_trees=lambda: None, _refresh_rule_details=lambda: None,
            _show_rule_tab=lambda name: setattr(app, "active_tab", name),
        )
        app._refresh_navigation = lambda: InferenceApp._refresh_navigation(app)
        def fired(number):
            return SimpleNamespace(rule=SimpleNamespace(number=number))
        app.view_model.result = SimpleNamespace(fired_rules=(fired(41),))
        app._refresh_navigation()
        self.assertEqual(app.rule_var.value, "Правило: 1 из 1")
        self.assertEqual(app.rule_prev.state, "disabled")
        self.assertEqual(app.rule_next.state, "disabled")
        app.view_model.result = SimpleNamespace(fired_rules=(fired(41), fired(7)))
        InferenceApp._move_rule(app, 1)
        self.assertEqual(app.selected_rule_number, 7)
        self.assertEqual(app.active_tab, "conflict")
        self.assertEqual(app.rule_var.value, "Правило: 2 из 2")
        app.view_model.result = None
        app._refresh_navigation()
        self.assertIsNone(app.selected_rule_number)
        self.assertEqual(app.rule_var.value, "Правило: —")

    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)
        self.rules_path = self.directory / "rules.nfrules"
        self.rules_path.write_text(json.dumps(_rules_payload(), ensure_ascii=False), encoding="utf-8")
        self.knowledge_base = KnowledgeBaseLoader().load(self.rules_path)

    def test_selects_rule_with_highest_interval_score(self) -> None:
        result = InferenceService().infer(
            self.knowledge_base,
            InputObject(values=(2.5, 1.0)),
        )

        self.assertEqual(result.predicted_class, "B")
        self.assertEqual(result.winner.rule.number, 2)
        self.assertAlmostEqual(result.winner.activation_low, 0.5)
        self.assertAlmostEqual(result.winner.activation_high, 0.5)
        self.assertAlmostEqual(result.winner.point_score, 0.475)

    def test_nie_tan_score_is_interval_midpoint(self) -> None:
        self.assertAlmostEqual(nie_tan_score(0.4, 0.7), 0.55)

    def test_missing_value_does_not_limit_known_conditions(self) -> None:
        result = InferenceService().infer(
            self.knowledge_base,
            InputObject(values=(None, 0.0)),
        )

        first_rule = result.evaluations[0]
        self.assertEqual(first_rule.activation_low, 1.0)
        self.assertEqual(first_rule.activation_high, 1.0)

    def test_batch_loader_encodes_categories_and_reads_actual_class(self) -> None:
        data_path = self.directory / "objects.csv"
        data_path.write_text(
            "X1;Level;Class\n2,5;high;B\n1,5;low;A\n",
            encoding="utf-8",
        )

        dataset = InputDatasetLoader().load(data_path, self.knowledge_base)

        self.assertEqual(dataset.objects[0].values, (2.5, 1.0))
        self.assertEqual(dataset.objects[0].actual_class, "B")

    def test_membership_visualizer_uses_interval_boundaries(self) -> None:
        membership = self.knowledge_base.rules[0].memberships[0]

        upper, lower = membership_boundaries(membership)

        self.assertEqual(upper, (0, 1, 2, 3))
        self.assertEqual(lower, (0, 1, 2, 3))

    def test_english_translation_covers_membership_window(self) -> None:
        self.assertEqual(translate("База правил", "en"), "Rule base")
        self.assertEqual(translate("Функции принадлежности выбранного правила", "en"), "Membership functions of the selected rule")
        self.assertEqual(translate("Предыдущий признак", "en"), "Previous feature")
        self.assertEqual(translate("Верхняя ФП", "en"), "Upper MF")
        self.assertEqual(translate("Значение входного признака", "en"), "Input feature value")
        self.assertEqual(translate("левая граница основания", "en"), "left support boundary")

    def test_data_errors_are_translated_for_english_interface(self) -> None:
        self.assertEqual(
            translate_error("Сначала загрузите базу правил .nfrules.", "en"),
            "Load the .nfrules rule base first.",
        )

    def test_feature_bounds_are_shown_beside_input_name(self) -> None:
        numeric = self.knowledge_base.features[0]
        ordinal = self.knowledge_base.features[1]

        self.assertEqual(numeric.minimum, 0.0)
        self.assertEqual(numeric.maximum, 5.0)
        self.assertEqual(
            _feature_input_caption(numeric, lambda text: translate(text, "ru")),
            "X1 (мин: 0; макс: 5)",
        )
        self.assertEqual(
            _feature_input_caption(ordinal, lambda text: translate(text, "en")),
            "Level (min: low; max: high)",
        )


def _rules_payload():
    return {
        "format": "neuro-fuzzy-rules",
        "version": 1,
        "feature_names": ["X1", "Level"],
        "target_name": "Class",
        "class_labels": ["A", "B"],
        "column_encodings": [
            {"source_name": "X1", "kind": "numeric", "output_names": ["X1"], "categories": []},
            {
                "source_name": "Level",
                "kind": "ordinal",
                "output_names": ["Level"],
                "categories": ["low", "high"],
            },
        ],
        "rules": [
            _rule(1, ("small", "low"), "A", (0.8, 0.9), ((0, 1, 2, 3), (-0.4, -0.2, 0.2, 0.4))),
            _rule(2, ("large", "high"), "B", (0.9, 1.0), ((2, 3, 4, 5), (0.6, 0.8, 1.2, 1.4))),
        ],
    }


def _rule(number, terms, consequent, cf, points):
    memberships = []
    for feature_name, term_name, values in zip(("X1", "Level"), terms, points):
        memberships.append(
            {
                "feature_name": feature_name,
                "term_name": term_name,
                "left_base": [values[0], values[0]],
                "left_core": [values[1], values[1]],
                "right_core": [values[2], values[2]],
                "right_base": [values[3], values[3]],
            }
        )
    return {
        "number": number,
        "terms": list(terms),
        "consequent": consequent,
        "cf": list(cf),
        "memberships": memberships,
    }


if __name__ == "__main__":
    unittest.main()
