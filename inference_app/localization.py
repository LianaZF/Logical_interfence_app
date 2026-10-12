"""Единая локализация интерфейса программы логического вывода."""

from __future__ import annotations


ENGLISH_TEXTS = {
    "Программа использования нечетких правил второго типа для решения задач классификации": "Application of type-2 fuzzy rules to classification problems",
    "База правил": "Rule base",
    "Язык": "Language",
    "Русский": "Russian",
    "Загрузить базу правил": "Load rule base",
    "Режим логического вывода": "Inference mode",
    "Пакетный (ввод данных из файла)": "Batch (data from file)",
    "Интерактивный (ручной ввод данных)": "Interactive (manual input)",
    "Загрузка данных для логического вывода": "Inference data",
    "Входные данные": "Input data",
    "Обзор": "Browse",
    "Количество строк": "Rows",
    "Количество признаков": "Features",
    "Количество классов": "Classes",
    "Система правил 2-го типа": "Type-2 rule system",
    "Конфликтное множество правил": "Conflicting rule set",
    "Входные значения": "Input values",
    "Расчёт для выбранного правила": "Selected rule calculation",
    "Класс объекта": "Object class",
    "Интервал активации [Tmin; Tmax]": "Activation interval [Tmin; Tmax]",
    "Интервал достоверности [Cmin; Cmax]": "Confidence interval [Cmin; Cmax]",
    "Оценка достоверности решения (С)": "Decision confidence score (C)",
    "Функции принадлежности": "Membership functions",
    "Функции принадлежности выбранного правила": "Membership functions of the selected rule",
    "Оценить состояние объекта": "Evaluate object",
    "Показать сработавшее правило": "Show winning rule",
    "Лингвистическая интерпретация решения": "Linguistic interpretation",
    "База нечётких правил": "Fuzzy rule base",
    "Табличные данные": "Tabular data",
    "Все файлы": "All files",
    "Ошибка": "Error",
    "Сначала выполните логический вывод.": "Run inference first.",
    "Загрузите базу правил и входные данные.": "Load the rule base and input data.",
    "Загрузите данные или перейдите в интерактивный режим.": "Load data or switch to interactive mode.",
    "Класс": "Class",
    "Объект: ручной ввод": "Object: manual input",
    "Объект: —": "Object: —",
    "Объект: {current} из {total}": "Object: {current} of {total}",
    "Правило: —": "Rule: —",
    "Правило: {current} из {total}": "Rule: {current} of {total}",
    "Для объекта не сработало ни одно правило.": "No rule fired for the object.",
    "ЕСЛИ {conditions}, ТО класс объекта «{class_name}».": (
        "IF {conditions}, THEN the object's class is “{class_name}”."
    ),
    "Предыдущий признак": "Previous feature",
    "Следующий признак": "Next feature",
    "Верхняя ФП": "Upper MF",
    "Нижняя ФП": "Lower MF",
    "Входное значение": "Input value",
    "Значение входного признака": "Input feature value",
    "Терм": "Term",
    "Точка": "Point",
    "левая граница основания": "left support boundary",
    "левая граница ядра": "left core boundary",
    "правая граница ядра": "right core boundary",
    "правая граница основания": "right support boundary",
    "нижняя степень": "lower degree",
    "верхняя степень": "upper degree",
    "мин": "min",
    "макс": "max",
}


ERROR_REPLACEMENTS = (
    ("Сначала загрузите базу правил .nfrules.", "Load the .nfrules rule base first."),
    ("Нет объекта для логического вывода.", "There is no object for inference."),
    ("Не удалось прочитать базу правил:", "Failed to read the rule base:"),
    ("Выбранный файл не является базой правил .nfrules.", "The selected file is not an .nfrules rule base."),
    ("База правил не содержит входных признаков.", "The rule base contains no input features."),
    ("База правил не содержит правил второго типа.", "The rule base contains no type-2 rules."),
    ("В базе правил найдено повреждённое правило.", "A corrupted rule was found in the rule base."),
    ("Число условий правила не совпадает с числом признаков.", "The number of rule conditions does not match the number of features."),
    ("Границы CF должны находиться в диапазоне от 0 до 1.", "CF bounds must be between 0 and 1."),
    ("Файл должен содержать заголовок и хотя бы один объект.", "The file must contain a header and at least one object."),
    ("В файле отсутствуют признаки:", "The file is missing features:"),
    ("Число входных значений не совпадает с базой правил.", "The number of input values does not match the rule base."),
    ("Не удалось прочитать входные данные:", "Failed to read input data:"),
    ("Поддерживаются кодировки UTF-8, Windows-1251 и Windows-1252.", "Supported encodings are UTF-8, Windows-1251, and Windows-1252."),
    ("Не удалось определить разделитель входного файла.", "Could not detect the input file delimiter."),
    ("Строка", "Row"),
    ("неизвестное значение", "unknown value"),
    ("признака", "of feature"),
    ("не является числом для признака", "is not a number for feature"),
    ("должен быть конечным числом", "must be a finite number"),
    ("ожидалось", "expected"),
    ("значений, получено", "values, received"),
)


def translate(text: str, language_code: str = "ru", **values) -> str:
    """Переводит строку и подставляет динамические значения."""

    template = ENGLISH_TEXTS.get(text, text) if language_code == "en" else text
    return template.format(**values) if values else template


def translate_error(message: str | None, language_code: str = "ru") -> str:
    """Переводит сообщения слоя данных, не связывая его с интерфейсом."""

    result = message or ""
    if language_code != "en":
        return result
    for russian, english in ERROR_REPLACEMENTS:
        result = result.replace(russian, english)
    return result
