"""Tkinter-интерфейс программы логического вывода."""

from __future__ import annotations

import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from inference_app.localization import translate, translate_error
from inference_app.membership_view import MembershipWindow
from inference_app.ui import BACKGROUND, FONT, make_button, readonly_value, setup_styles
from inference_app.viewmodel import InferenceViewModel

def resource_path(relative_path: str) -> Path:
    """Возвращает путь к ресурсу при запуске из исходников и PyInstaller."""

    if hasattr(sys, "_MEIPASS"):
        candidate = Path(sys._MEIPASS) / relative_path
        if candidate.exists():
            return candidate
    return Path(__file__).resolve().parent.parent / relative_path


class InferenceApp(tk.Tk):
    """Главное окно второй программы."""

    def __init__(self) -> None:
        super().__init__()
        self.view_model = InferenceViewModel()
        self.language_code = "ru"
        self.mode_var = tk.StringVar(value="batch")
        self.knowledge_path_var = tk.StringVar()
        self.data_path_var = tk.StringVar()
        self.rows_var = tk.StringVar(value="")
        self.features_var = tk.StringVar(value="—")
        self.classes_var = tk.StringVar(value="—")
        self.object_var = tk.StringVar(value="Объект: —")
        self.rule_var = tk.StringVar(value="Правило: —")
        self.actual_class_var = tk.StringVar(value="—")
        self.activation_var = tk.StringVar(value="—")
        self.cf_var = tk.StringVar(value="—")
        self.confidence_var = tk.StringVar(value="—")
        self.score_var = tk.StringVar(value="—")
        self.interpretation_var = tk.StringVar(value="Загрузите базу правил и входные данные.")
        self.selected_rule_number: int | None = None
        self.feature_vars: list[tk.StringVar] = []
        self.title(self._t("Программа использования нечетких правил второго типа для решения задач классификации"))
        self.geometry("1180x830")
        self.minsize(980, 710)
        self._load_theme()
        self._setup_styles()
        self._build_menu()
        self._build_content()

    def _t(self, text: str, **values) -> str:
        return translate(text, self.language_code, **values)

    def _show_error(self) -> None:
        """Показывает ошибку ViewModel на выбранном языке."""

        messagebox.showerror(
            self._t("Ошибка"),
            translate_error(self.view_model.error_message, self.language_code),
            parent=self,
        )

    def _setup_styles(self) -> None:
        self.configure(background=BACKGROUND)
        setup_styles(self)

    def _load_theme(self) -> None:
        """Подключает ту же тему forest-light, что и основная программа."""

        style = ttk.Style(self)
        theme_path = resource_path("themes/forest-light.tcl")
        if "forest-light" not in style.theme_names():
            self.tk.call("source", str(theme_path))
        style.theme_use("forest-light")
        self.style = style

    def _build_menu(self) -> None:
        self.option_add("*Menu.tearOff", False)
        self.option_add("*Menu.font", ("Times New Roman", 12))
        menu = tk.Menu(self)
        file_menu = tk.Menu(menu)
        file_menu.add_command(label=self._t("Загрузить базу правил"), command=self._choose_knowledge_base)
        menu.add_cascade(label=self._t("База правил"), menu=file_menu)
        language_menu = tk.Menu(menu)
        language_menu.add_command(label=self._t("Русский"), command=lambda: self._set_language("ru"))
        language_menu.add_command(label="English", command=lambda: self._set_language("en"))
        menu.add_cascade(label=self._t("Язык"), menu=language_menu)
        self.config(menu=menu)

    def _build_content(self) -> None:
        old_body = getattr(self, "body", None)
        if old_body is not None:
            old_body.destroy()
        self.body = ttk.Frame(self, padding=6)
        self.body.pack(fill="both", expand=True)
        self.body.columnconfigure(0, weight=1)
        self.body.rowconfigure(1, weight=2, minsize=220)
        self.body.rowconfigure(2, weight=0)
        self.body.rowconfigure(3, weight=1, minsize=100)
        self._build_top_area()
        self._build_rule_tables()
        self._build_work_area()
        self._build_interpretation()
        self._refresh_all()

    def _build_top_area(self) -> None:
        top = ttk.Frame(self.body)
        top.grid(row=0, column=0, sticky="ew", pady=(0, 7))
        top.columnconfigure(1, weight=1)
        mode = ttk.LabelFrame(top, text=self._t("Режим логического вывода"), padding=7)
        mode.grid(row=0, column=0, sticky="nsw", padx=(0, 7))
        ttk.Radiobutton(
            mode,
            text=self._t("Пакетный (ввод данных из файла)"),
            variable=self.mode_var,
            value="batch",
            command=self._mode_changed,
        ).grid(row=0, column=0, sticky="w")
        ttk.Radiobutton(
            mode,
            text=self._t("Интерактивный (ручной ввод данных)"),
            variable=self.mode_var,
            value="interactive",
            command=self._mode_changed,
        ).grid(row=1, column=0, sticky="w", pady=(3, 0))

        data = ttk.LabelFrame(
            top,
            text=self._t("Загрузка данных для логического вывода"),
            padding=7,
        )
        data.grid(row=0, column=1, sticky="nsew")
        data.columnconfigure(1, weight=1)
        ttk.Label(data, text=self._t("Входные данные")).grid(row=0, column=0, sticky="w", padx=(0, 6))
        self.data_entry = ttk.Entry(data, textvariable=self.data_path_var, state="readonly")
        self.data_entry.grid(row=0, column=1, sticky="ew")
        self.data_button = make_button(data, self._t("Обзор"), self._choose_dataset, width=10)
        self.data_button.grid(row=0, column=2, padx=(6, 0))
        stats = ttk.Frame(data)
        stats.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(6, 0))
        for column in range(6):
            stats.columnconfigure(column, weight=1 if column % 2 else 0)
        labels = (
            ("Количество строк", self.rows_var),
            ("Количество признаков", self.features_var),
            ("Количество классов", self.classes_var),
        )
        for index, (label, variable) in enumerate(labels):
            ttk.Label(stats, text=self._t(label)).grid(row=0, column=index * 2, padx=(0, 4))
            readonly_value(stats, variable, width=7).grid(
                row=0, column=index * 2 + 1, sticky="ew", padx=(0, 12 if index < 2 else 0)
            )

    def _build_rule_tables(self) -> None:
        container = ttk.Frame(self.body)
        container.grid(row=1, column=0, sticky="nsew")
        container.columnconfigure(0, weight=1)
        container.rowconfigure(1, weight=1)
        tabs = ttk.Frame(container)
        tabs.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        tabs.columnconfigure((0, 1), weight=1, uniform="rule-tabs")
        self.system_tab_button = make_button(
            tabs,
            self._t("Система правил 2-го типа"),
            lambda: self._show_rule_tab("system"),
            style="TopPlainActive.TButton",
        )
        self.system_tab_button.grid(row=0, column=0, sticky="ew", padx=(0, 4), ipady=5)
        self.conflict_tab_button = make_button(
            tabs,
            self._t("Конфликтное множество правил"),
            lambda: self._show_rule_tab("conflict"),
            style="TopPlain.TButton",
        )
        self.conflict_tab_button.grid(row=0, column=1, sticky="ew", padx=(4, 0), ipady=5)
        self.conflict_tab_button.configure(state="disabled")
        table_area = ttk.Frame(container)
        table_area.grid(row=1, column=0, sticky="nsew")
        table_area.columnconfigure(0, weight=1)
        table_area.rowconfigure(0, weight=1)
        self.rules_tab = ttk.Frame(table_area)
        self.conflict_tab = ttk.Frame(table_area)
        for frame in (self.rules_tab, self.conflict_tab):
            frame.grid(row=0, column=0, sticky="nsew")
        self.rules_tree = self._create_tree(self.rules_tab)
        self.conflict_tree = self._create_tree(self.conflict_tab)
        self.rules_tree.bind("<<TreeviewSelect>>", self._rule_selected)
        self.conflict_tree.bind("<<TreeviewSelect>>", self._rule_selected)
        self._show_rule_tab("system")

    def _show_rule_tab(self, name: str) -> None:
        """Переключает таблицы кнопками в стиле верхней панели первой программы."""

        if name == "conflict" and self.view_model.result is None:
            name = "system"
        is_system = name == "system"
        (self.rules_tab if is_system else self.conflict_tab).tkraise()
        self.system_tab_button.configure(
            style="TopPlainActive.TButton" if is_system else "TopPlain.TButton"
        )
        self.conflict_tab_button.configure(
            style="TopPlain.TButton" if is_system else "TopPlainActive.TButton"
        )

    def _create_tree(self, parent) -> ttk.Treeview:
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)
        outer = ttk.Frame(parent, borderwidth=1, relief="solid")
        outer.grid(row=0, column=0, sticky="nsew")
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(0, weight=1)
        tree = ttk.Treeview(
            outer,
            show="headings",
            selectmode="browse",
            style="Rules.Treeview",
        )
        y_scroll = ttk.Scrollbar(outer, orient="vertical", command=tree.yview)
        x_scroll = ttk.Scrollbar(outer, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
        tree.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")
        return tree

    def _build_work_area(self) -> None:
        work = ttk.Frame(self.body)
        work.grid(row=2, column=0, sticky="nsew", pady=(7, 0))
        work.columnconfigure(0, weight=1)
        work.columnconfigure(1, weight=1)
        work.rowconfigure(0, weight=1)
        inputs = ttk.LabelFrame(work, text=self._t("Входные значения"), padding=7)
        inputs.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        inputs.columnconfigure(0, weight=1)
        inputs.rowconfigure(1, weight=1)
        nav = ttk.Frame(inputs)
        nav.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        nav.columnconfigure(1, weight=1)
        self.object_prev = make_button(nav, "←", lambda: self._move_object(-1), width=7)
        self.object_prev.grid(row=0, column=0)
        ttk.Label(nav, textvariable=self.object_var, anchor="center").grid(row=0, column=1, sticky="ew")
        self.object_next = make_button(nav, "→", lambda: self._move_object(1), width=7)
        self.object_next.grid(row=0, column=2)
        self.inputs_canvas = tk.Canvas(inputs, background=BACKGROUND, highlightthickness=0, height=140)
        input_scroll = ttk.Scrollbar(inputs, orient="vertical", command=self.inputs_canvas.yview)
        self.inputs_canvas.configure(yscrollcommand=input_scroll.set)
        self.inputs_canvas.grid(row=1, column=0, sticky="nsew")
        input_scroll.grid(row=1, column=1, sticky="ns")
        self.inputs_frame = ttk.Frame(self.inputs_canvas)
        self.inputs_window = self.inputs_canvas.create_window((0, 0), window=self.inputs_frame, anchor="nw")
        self.inputs_frame.bind("<Configure>", self._resize_inputs_scroll)
        self.inputs_canvas.bind("<Configure>", self._resize_inputs_width)

        calculation = ttk.LabelFrame(
            work,
            text=self._t("Расчёт для выбранного правила"),
            padding=7,
        )
        calculation.grid(row=0, column=1, sticky="nsew", padx=(4, 0))
        calculation.columnconfigure(1, weight=1)
        rule_nav = ttk.Frame(calculation)
        rule_nav.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 5))
        rule_nav.columnconfigure(1, weight=1)
        self.rule_prev = make_button(rule_nav, "←", lambda: self._move_rule(-1), width=7)
        self.rule_prev.grid(row=0, column=0)
        ttk.Label(rule_nav, textvariable=self.rule_var, anchor="center").grid(row=0, column=1, sticky="ew")
        self.rule_next = make_button(rule_nav, "→", lambda: self._move_rule(1), width=7)
        self.rule_next.grid(row=0, column=2)
        details = (
            ("Класс объекта", self.actual_class_var),
            ("Интервал активации [Tmin; Tmax]", self.activation_var),
            ("Интервал достоверности [Cmin; Cmax]", self.confidence_var),
            ("Оценка достоверности решения (С)", self.score_var),
        )
        for row, (label, variable) in enumerate(details, start=1):
            ttk.Label(calculation, text=self._t(label)).grid(row=row, column=0, sticky="w", pady=2)
            readonly_value(calculation, variable, width=18).grid(
                row=row, column=1, sticky="ew", padx=(8, 0), pady=2
            )
        actions = ttk.Frame(calculation)
        actions.grid(row=len(details) + 1, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        actions.columnconfigure((0, 1), weight=1)
        self.membership_button = make_button(
            actions, self._t("Функции принадлежности"), self._show_memberships
        )
        self.membership_button.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        self.membership_button.configure(state="disabled")
        make_button(actions, self._t("Оценить состояние объекта"), self._evaluate).grid(
            row=0, column=1, sticky="ew", padx=(4, 0)
        )

    def _build_interpretation(self) -> None:
        frame = ttk.LabelFrame(
            self.body,
            text=self._t("Лингвистическая интерпретация решения"),
            padding=8,
        )
        frame.grid(row=3, column=0, sticky="nsew", pady=(7, 0))
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        ttk.Label(
            frame,
            textvariable=self.interpretation_var,
            anchor="center",
            justify="center",
            wraplength=1050,
            font=FONT,
        ).grid(row=0, column=0, sticky="nsew")

    def _choose_knowledge_base(self) -> None:
        path = filedialog.askopenfilename(
            parent=self,
            filetypes=[
                (self._t("База нечётких правил"), "*.nfrules"),
                (self._t("Все файлы"), "*.*"),
            ],
        )
        if not path:
            return
        if not self.view_model.load_knowledge_base(path):
            self._show_error()
            return
        self.knowledge_path_var.set(path)
        self.data_path_var.set("")
        self.selected_rule_number = self.view_model.knowledge_base.rules[0].number
        self.interpretation_var.set(self._t("Загрузите данные или перейдите в интерактивный режим."))
        self._refresh_all()

    def _choose_dataset(self) -> None:
        path = filedialog.askopenfilename(
            parent=self,
            filetypes=[
                (self._t("Табличные данные"), "*.txt *.csv *.tsv"),
                (self._t("Все файлы"), "*.*"),
            ],
        )
        if not path:
            return
        if not self.view_model.load_dataset(path):
            self._show_error()
            return
        self.data_path_var.set(path)
        self._refresh_all()

    def _mode_changed(self) -> None:
        self.data_button.configure(state="normal" if self.mode_var.get() == "batch" else "disabled")
        if self.mode_var.get() == "interactive" and self.view_model.knowledge_base is not None:
            self.view_model.dataset = None
            self.view_model.result = None
        self._refresh_all()

    def _refresh_all(self) -> None:
        knowledge_base = self.view_model.knowledge_base
        self.features_var.set("—" if knowledge_base is None else str(len(knowledge_base.features)))
        self.classes_var.set("—" if knowledge_base is None else str(len(knowledge_base.class_labels)))
        self.rows_var.set(
            "" if self.view_model.dataset is None else str(len(self.view_model.dataset.objects))
        )
        self._populate_system_rules()
        self._populate_conflict_rules()
        self._rebuild_feature_inputs()
        self._refresh_navigation()
        self._refresh_rule_details()
        if hasattr(self, "data_button"):
            self.data_button.configure(state="normal" if self.mode_var.get() == "batch" else "disabled")

    def _populate_system_rules(self) -> None:
        knowledge_base = self.view_model.knowledge_base
        if knowledge_base is None:
            self._configure_tree(self.rules_tree, (), ())
            return
        columns = ("№", *(feature.name for feature in knowledge_base.features), self._t("Класс"), "CF min", "CF max")
        rows = (
            (rule.number, *rule.terms, rule.consequent, _number(rule.cf_low), _number(rule.cf_high))
            for rule in knowledge_base.rules
        )
        self._configure_tree(self.rules_tree, columns, rows)

    def _populate_conflict_rules(self) -> None:
        knowledge_base = self.view_model.knowledge_base
        result = self.view_model.result
        if knowledge_base is None:
            self._configure_tree(self.conflict_tree, (), ())
            return
        columns = (
            "№",
            *(feature.name for feature in knowledge_base.features),
            self._t("Класс"),
            "T min",
            "T max",
            "CF min",
            "CF max",
            "C min",
            "C max",
            "C",
        )
        evaluations = () if result is None else result.fired_rules
        rows = (
            (
                item.rule.number,
                *item.rule.terms,
                item.rule.consequent,
                _number(item.activation_low),
                _number(item.activation_high),
                _number(item.rule.cf_low),
                _number(item.rule.cf_high),
                _number(item.confidence_low),
                _number(item.confidence_high),
                _number(item.point_score),
            )
            for item in evaluations
        )
        self._configure_tree(self.conflict_tree, columns, rows)

    @staticmethod
    def _configure_tree(tree: ttk.Treeview, headings, rows) -> None:
        tree.delete(*tree.get_children())
        rows = tuple(rows)
        tree.configure(columns=tuple(str(index) for index in range(len(headings))))
        tree.tag_configure("oddrow", background="#FFFFFF")
        tree.tag_configure("evenrow", background="#F3F3F3")
        tree.tag_configure("emptyrow", foreground="#808080", background="#FFFFFF")
        for index, heading in enumerate(headings):
            column = str(index)
            tree.heading(column, text=heading)
            width = 38 if index == 0 else max(78, min(160, len(str(heading)) * 8 + 20))
            tree.column(column, width=width, minwidth=38, stretch=True, anchor="center")
        for index, row in enumerate(rows, start=1):
            number = int(row[0])
            tag = "evenrow" if index % 2 == 0 else "oddrow"
            tree.insert("", "end", iid=f"rule-{number}", values=row, tags=(tag,))
        if headings and not rows:
            tree.insert("", "end", values=("",) * len(headings), tags=("emptyrow",))

    def _rebuild_feature_inputs(self) -> None:
        for child in self.inputs_frame.winfo_children():
            child.destroy()
        self.feature_vars = []
        knowledge_base = self.view_model.knowledge_base
        if knowledge_base is None:
            return
        current = self.view_model.current_object
        for row, feature in enumerate(knowledge_base.features):
            ttk.Label(
                self.inputs_frame,
                text=_feature_input_caption(feature, self._t),
            ).grid(row=row, column=0, sticky="w", padx=(0, 8), pady=2)
            value = ""
            if current is not None:
                raw = current.values[row]
                if raw is not None:
                    value = (
                        feature.categories[int(raw)]
                        if feature.categories and 0 <= int(raw) < len(feature.categories)
                        else _number(raw)
                    )
            variable = tk.StringVar(value=value)
            self.feature_vars.append(variable)
            if feature.categories:
                widget = ttk.Combobox(
                    self.inputs_frame,
                    textvariable=variable,
                    values=feature.categories,
                    state="readonly" if self.mode_var.get() == "interactive" else "disabled",
                )
            else:
                widget = ttk.Entry(
                    self.inputs_frame,
                    textvariable=variable,
                    state="normal" if self.mode_var.get() == "interactive" else "readonly",
                )
            widget.grid(row=row, column=1, sticky="ew", pady=2)
        self.inputs_frame.columnconfigure(1, weight=1)

    def _refresh_navigation(self) -> None:
        dataset = self.view_model.dataset
        if dataset is None:
            self.object_var.set(
                self._t("Объект: ручной ввод")
                if self.mode_var.get() == "interactive"
                else self._t("Объект: —")
            )
            self.object_prev.configure(state="disabled")
            self.object_next.configure(state="disabled")
        else:
            count = len(dataset.objects)
            self.object_var.set(
                self._t(
                    "Объект: {current} из {total}",
                    current=self.view_model.object_index + 1,
                    total=count,
                )
            )
            self.object_prev.configure(state="disabled" if self.view_model.object_index == 0 else "normal")
            self.object_next.configure(state="disabled" if self.view_model.object_index == count - 1 else "normal")
        result = self.view_model.result
        rules = () if result is None else tuple(item.rule for item in result.fired_rules)
        position = None
        if not rules:
            self.selected_rule_number = None
            self.rule_var.set(self._t("Правило: —"))
        else:
            position = next(
                (index for index, rule in enumerate(rules) if rule.number == self.selected_rule_number),
                0,
            )
            self.selected_rule_number = rules[position].number
            self.rule_var.set(
                self._t(
                    "Правило: {current} из {total}",
                    current=position + 1,
                    total=len(rules),
                )
            )
        self.rule_prev.configure(state="disabled" if position is None or position == 0 else "normal")
        self.rule_next.configure(state="disabled" if position is None or position == len(rules) - 1 else "normal")

    def _move_object(self, offset: int) -> None:
        self.view_model.move_object(offset)
        self._refresh_all()

    def _move_rule(self, offset: int) -> None:
        result = self.view_model.result
        if result is None or not result.fired_rules:
            return
        numbers = tuple(item.rule.number for item in result.fired_rules)
        current = 0 if self.selected_rule_number not in numbers else numbers.index(self.selected_rule_number)
        current = min(len(numbers) - 1, max(0, current + offset))
        self.selected_rule_number = numbers[current]
        self._show_rule_tab("conflict")
        self._select_rule_in_trees()
        self._refresh_navigation()
        self._refresh_rule_details()

    def _rule_selected(self, event) -> None:
        selection = event.widget.selection()
        if not selection:
            return
        number = int(selection[0].split("-")[-1])
        result = self.view_model.result
        if result is None or not any(item.rule.number == number for item in result.fired_rules):
            return
        self.selected_rule_number = number
        self._refresh_navigation()
        self._refresh_rule_details()

    def _evaluate(self) -> None:
        if self.mode_var.get() == "interactive":
            if not self.view_model.create_interactive_object(
                tuple(variable.get() for variable in self.feature_vars)
            ):
                self._show_error()
                return
        if not self.view_model.infer_current():
            self._show_error()
            return
        winner = self.view_model.result.winner
        self.selected_rule_number = None if winner is None else winner.rule.number
        self._populate_conflict_rules()
        self._show_rule_tab("conflict")
        self._refresh_rule_details()
        self._refresh_navigation()
        self._select_rule_in_trees()

    def _refresh_rule_details(self) -> None:
        evaluation = (
            None
            if self.selected_rule_number is None
            else self.view_model.evaluation_by_rule_number(self.selected_rule_number)
        )
        result = self.view_model.result
        self.conflict_tab_button.configure(state="normal" if result is not None else "disabled")
        self.membership_button.configure(state="normal" if evaluation is not None else "disabled")
        if result is None:
            self._show_rule_tab("system")
        if result is not None and result.predicted_class is not None:
            self.actual_class_var.set(result.predicted_class)
        else:
            self.actual_class_var.set("—")
        if evaluation is None:
            self.activation_var.set("—")
            self.cf_var.set("—")
            self.confidence_var.set("—")
            self.score_var.set("—")
        else:
            self.activation_var.set(_interval(evaluation.activation_low, evaluation.activation_high))
            self.cf_var.set(_interval(evaluation.rule.cf_low, evaluation.rule.cf_high))
            self.confidence_var.set(_interval(evaluation.confidence_low, evaluation.confidence_high))
            self.score_var.set(_number(evaluation.point_score))
        if result is None:
            if self.view_model.knowledge_base is None:
                self.interpretation_var.set(self._t("Загрузите базу правил и входные данные."))
            elif self.view_model.current_object is None:
                self.interpretation_var.set(
                    self._t("Загрузите данные или перейдите в интерактивный режим.")
                )
            return
        if result.winner is None:
            self.interpretation_var.set(self._t("Для объекта не сработало ни одно правило."))
            return
        winner = result.winner
        conditions = (" AND " if self.language_code == "en" else " И ").join(
            f"{feature.feature_name} = {feature.term_name}"
            for feature in winner.features
        )
        self.interpretation_var.set(
            self._t(
                "ЕСЛИ {conditions}, ТО класс объекта «{class_name}».",
                conditions=conditions,
                class_name=winner.rule.consequent,
            )
        )

    def _show_winner(self) -> None:
        result = self.view_model.result
        if result is None or result.winner is None:
            return
        self.selected_rule_number = result.winner.rule.number
        self._show_rule_tab("conflict")
        self._select_rule_in_trees()
        self._refresh_navigation()
        self._refresh_rule_details()

    def _select_rule_in_trees(self) -> None:
        if self.selected_rule_number is None:
            return
        iid = f"rule-{self.selected_rule_number}"
        for tree in (self.rules_tree, self.conflict_tree):
            if tree.exists(iid):
                tree.selection_set(iid)
                tree.focus(iid)
                tree.see(iid)

    def _show_memberships(self) -> None:
        evaluation = (
            None
            if self.selected_rule_number is None
            else self.view_model.evaluation_by_rule_number(self.selected_rule_number)
        )
        if evaluation is None:
            messagebox.showinfo(
                self._t("Функции принадлежности"),
                self._t("Сначала выполните логический вывод."),
                parent=self,
            )
            return
        MembershipWindow(self, evaluation, self._t)

    def _resize_inputs_scroll(self, _event=None) -> None:
        self.inputs_canvas.configure(scrollregion=self.inputs_canvas.bbox("all"))

    def _resize_inputs_width(self, event) -> None:
        self.inputs_canvas.itemconfigure(self.inputs_window, width=event.width)

    def _set_language(self, language_code: str) -> None:
        self.language_code = language_code
        self.title(self._t("Программа использования нечетких правил второго типа для решения задач классификации"))
        self._build_menu()
        self._build_content()
        for child in self.winfo_children():
            if isinstance(child, MembershipWindow):
                child.set_translator(self._t)

    def load_startup_files(self, rules_path: str | None, data_path: str | None) -> None:
        """Загружает переданные при запуске файлы для демонстрации и тестирования."""

        if rules_path:
            if not self.view_model.load_knowledge_base(rules_path):
                self._show_error()
                return
            self.knowledge_path_var.set(str(Path(rules_path).resolve()))
            self.selected_rule_number = self.view_model.knowledge_base.rules[0].number
        if data_path:
            if not self.view_model.load_dataset(data_path):
                self._show_error()
                return
            self.data_path_var.set(str(Path(data_path).resolve()))
        self._refresh_all()


def _number(value: float) -> str:
    return f"{value:.4f}".rstrip("0").rstrip(".").replace(".", ",")


def _feature_input_caption(feature, translator) -> str:
    """Добавляет к имени признака его осмысленные границы допустимого ввода."""

    if feature.kind == "ordinal" and feature.categories:
        minimum = feature.categories[0]
        maximum = feature.categories[-1]
    elif feature.kind != "nominal" and feature.minimum is not None and feature.maximum is not None:
        minimum = _number(feature.minimum)
        maximum = _number(feature.maximum)
    else:
        return feature.name
    return (
        f"{feature.name} "
        f"({translator('мин')}: {minimum}; {translator('макс')}: {maximum})"
    )


def _interval(low: float, high: float) -> str:
    return f"[{_number(low)}; {_number(high)}]"
