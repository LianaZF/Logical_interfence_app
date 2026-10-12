"""ViewModel связывает независимые сервисы логического вывода с интерфейсом."""

from __future__ import annotations

from inference_app.domain import InferenceResult, InputDataset, InputObject, KnowledgeBase
from inference_app.services import (
    InferenceDataError,
    InferenceService,
    InputDatasetLoader,
    KnowledgeBaseLoader,
    parse_feature_value,
)


class InferenceViewModel:
    """Хранит выбранные файлы, текущий объект и результат без зависимости от Tkinter."""

    def __init__(self) -> None:
        self.knowledge_base: KnowledgeBase | None = None
        self.dataset: InputDataset | None = None
        self.object_index = 0
        self.result: InferenceResult | None = None
        self.error_message: str | None = None
        self._knowledge_loader = KnowledgeBaseLoader()
        self._dataset_loader = InputDatasetLoader()
        self._inference = InferenceService()

    def load_knowledge_base(self, path: str) -> bool:
        try:
            self.knowledge_base = self._knowledge_loader.load(path)
        except InferenceDataError as error:
            self.error_message = str(error)
            return False
        self.dataset = None
        self.object_index = 0
        self.result = None
        self.error_message = None
        return True

    def load_dataset(self, path: str) -> bool:
        if self.knowledge_base is None:
            self.error_message = "Сначала загрузите базу правил .nfrules."
            return False
        try:
            self.dataset = self._dataset_loader.load(path, self.knowledge_base)
        except InferenceDataError as error:
            self.error_message = str(error)
            return False
        self.object_index = 0
        self.result = None
        self.error_message = None
        return True

    def create_interactive_object(self, raw_values: tuple[str, ...]) -> bool:
        if self.knowledge_base is None:
            self.error_message = "Сначала загрузите базу правил .nfrules."
            return False
        try:
            values = tuple(
                parse_feature_value(value, feature)
                for value, feature in zip(raw_values, self.knowledge_base.features)
            )
        except InferenceDataError as error:
            self.error_message = str(error)
            return False
        self.dataset = InputDataset(
            source_path=None,
            objects=(InputObject(values=values),),
        )
        self.object_index = 0
        self.error_message = None
        return True

    @property
    def current_object(self) -> InputObject | None:
        if self.dataset is None or not self.dataset.objects:
            return None
        return self.dataset.objects[self.object_index]

    def move_object(self, offset: int) -> None:
        if self.dataset is None:
            return
        self.object_index = min(
            len(self.dataset.objects) - 1,
            max(0, self.object_index + offset),
        )
        self.result = None

    def infer_current(self) -> bool:
        if self.knowledge_base is None or self.current_object is None:
            self.error_message = "Нет объекта для логического вывода."
            return False
        self.result = self._inference.infer(self.knowledge_base, self.current_object)
        self.error_message = None
        return True

    def evaluation_by_rule_number(self, rule_number: int):
        if self.result is None:
            return None
        return next(
            (item for item in self.result.evaluations if item.rule.number == rule_number),
            None,
        )
