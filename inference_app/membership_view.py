"""Интерактивное окно функций принадлежности программы логического вывода."""

from __future__ import annotations

import tkinter as tk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from inference_app.ui import make_button


PLOT_BACKGROUND = "#F2F2F2"
UPPER_COLOR = "#3A73A8"
LOWER_COLOR = "#B04A4A"
INPUT_COLOR = "#217346"
FONT_NAME = "Times New Roman"


def membership_boundaries(membership) -> tuple[tuple[float, ...], tuple[float, ...]]:
    """Возвращает точки верхней и нижней границ интервальной ФП."""

    upper = (
        membership.left_base[0],
        membership.left_core[0],
        membership.right_core[1],
        membership.right_base[1],
    )
    lower = (
        membership.left_base[1],
        membership.left_core[1],
        membership.right_core[0],
        membership.right_base[0],
    )
    return upper, lower


class MembershipWindow(tk.Toplevel):
    """Показывает ФП условия правила в стиле визуализаторов первой программы."""

    def __init__(self, parent, evaluation, translator) -> None:
        super().__init__(parent)
        self.evaluation = evaluation
        self._t = translator
        self.feature_index = 0
        self.hidden_curves: set[str] = set()
        self.artist_groups: dict[str, tuple] = {}
        self.legend_items: dict[object, str] = {}
        self.legend_artists: dict[str, tuple] = {}
        self.support_points: list[tuple[float, float, str, str]] = []
        self.pan_state = None

        self.title(self._t("Функции принадлежности выбранного правила"))
        self.geometry("860x660")
        self.minsize(860, 660)
        self.maxsize(860, 660)
        self.resizable(False, False)
        self.transient(parent)
        self.configure(background=PLOT_BACKGROUND)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        body = tk.Frame(self, background=PLOT_BACKGROUND)
        body.grid(row=0, column=0, sticky="nsew", padx=12, pady=(8, 0))
        body.columnconfigure(0, weight=1)
        body.rowconfigure(0, weight=1)

        self.figure = Figure(figsize=(8.2, 4.35), dpi=100, facecolor=PLOT_BACKGROUND)
        self.axes = self.figure.add_subplot(111)
        self.figure.subplots_adjust(left=0.09, right=0.98, top=0.72, bottom=0.14)
        self.canvas = FigureCanvasTkAgg(self.figure, master=body)
        canvas_widget = self.canvas.get_tk_widget()
        canvas_widget.configure(highlightthickness=0)
        canvas_widget.grid(row=0, column=0, sticky="nsew")

        navigation = tk.Frame(self, background=PLOT_BACKGROUND)
        navigation.grid(row=1, column=0, sticky="ew", padx=12, pady=(4, 12))
        navigation.columnconfigure(0, weight=1)
        navigation.columnconfigure(1, weight=0)
        navigation.columnconfigure(2, weight=1)
        self.prev_button = make_button(
            navigation,
            self._t("Предыдущий признак"),
            lambda: self._move_feature(-1),
            width=24,
        )
        self.prev_button.grid(row=0, column=0, sticky="e", padx=(0, 12))
        make_button(navigation, "OK", self.destroy, width=10).grid(
            row=0,
            column=1,
        )
        self.next_button = make_button(
            navigation,
            self._t("Следующий признак"),
            lambda: self._move_feature(1),
            width=24,
        )
        self.next_button.grid(row=0, column=2, sticky="w", padx=(12, 0))

        self.canvas.mpl_connect("pick_event", self._toggle_curve)
        self.canvas.mpl_connect("scroll_event", self._zoom)
        self.canvas.mpl_connect("button_press_event", self._start_pan)
        self.canvas.mpl_connect("motion_notify_event", self._hover)
        self.canvas.mpl_connect("motion_notify_event", self._move_pan)
        self.canvas.mpl_connect("button_release_event", self._stop_pan)
        self._render()

    def set_translator(self, translator) -> None:
        """Обновляет язык уже открытого окна без его повторного создания."""

        self._t = translator
        self.title(self._t("Функции принадлежности выбранного правила"))
        self.prev_button.configure(text=self._t("Предыдущий признак"))
        self.next_button.configure(text=self._t("Следующий признак"))
        self._render()

    def _move_feature(self, offset: int) -> None:
        """Переключает признак выбранного правила."""

        self.feature_index = min(
            len(self.evaluation.features) - 1,
            max(0, self.feature_index + offset),
        )
        self.hidden_curves.clear()
        self._render()

    def _render(self) -> None:
        """Перерисовывает интервальную ФП и входное значение признака."""

        item = self.evaluation.features[self.feature_index]
        membership = self.evaluation.rule.memberships[self.feature_index]
        upper, lower = membership_boundaries(membership)
        levels = (0.0, 1.0, 1.0, 0.0)

        axes = self.axes
        axes.clear()
        self.artist_groups.clear()
        self.support_points.clear()
        self.annotation = axes.annotate(
            "",
            xy=(0, 0),
            xytext=(14, 14),
            textcoords="offset points",
            fontname=FONT_NAME,
            fontsize=13,
            bbox={"boxstyle": "round,pad=0.35", "fc": "#FFFFFF", "ec": "#A0A0A0", "alpha": 0.96},
            zorder=20,
        )
        self.annotation.set_visible(False)

        upper_line, = axes.plot(
            upper,
            levels,
            color=UPPER_COLOR,
            linewidth=1.8,
            linestyle="-",
            marker="D",
            markersize=4.2,
            markerfacecolor=PLOT_BACKGROUND,
            markeredgewidth=1.0,
            label=self._t("Верхняя ФП"),
        )
        lower_line, = axes.plot(
            lower,
            levels,
            color=LOWER_COLOR,
            linewidth=1.4,
            linestyle="--",
            marker="D",
            markersize=3.8,
            markerfacecolor=PLOT_BACKGROUND,
            markeredgewidth=0.9,
            label=self._t("Нижняя ФП"),
        )
        self.artist_groups["Верхняя ФП"] = (upper_line,)
        self.artist_groups["Нижняя ФП"] = (lower_line,)
        self._remember_support_points(upper, "Верхняя ФП")
        self._remember_support_points(lower, "Нижняя ФП")

        legend_handles = [upper_line, lower_line]
        input_value = item.input_value
        if input_value is not None:
            input_line = axes.axvline(
                input_value,
                color=INPUT_COLOR,
                linewidth=1.2,
                linestyle=":",
                label=self._t("Входное значение"),
            )
            input_points = axes.scatter(
                (input_value, input_value),
                (item.membership_low, item.membership_high),
                s=32,
                facecolors=PLOT_BACKGROUND,
                edgecolors=INPUT_COLOR,
                linewidths=1.2,
                zorder=6,
            )
            self.artist_groups["Входное значение"] = (input_line, input_points)
            legend_handles.append(input_line)
            self.support_points.extend(
                (
                    (input_value, item.membership_low, "Входное значение", "нижняя степень"),
                    (input_value, item.membership_high, "Входное значение", "верхняя степень"),
                )
            )

        for label, artists in self.artist_groups.items():
            visible = label not in self.hidden_curves
            for artist in artists:
                artist.set_visible(visible)

        all_x = (*upper, *lower)
        if input_value is not None:
            all_x = (*all_x, input_value)
        left_limit = min(all_x)
        right_limit = max(all_x)
        margin = max((right_limit - left_limit) * 0.07, 0.1)
        axes.set_xlim(left_limit - margin, right_limit + margin)
        axes.set_ylim(-0.01, 1.12)
        axes.set_facecolor(PLOT_BACKGROUND)
        axes.grid(False)
        axes.spines["top"].set_visible(False)
        axes.spines["right"].set_visible(False)
        axes.set_yticks((0, 0.5, 1))
        axes.set_yticklabels(("0", "0,5", "1"))
        axes.set_xlabel(self._t("Значение входного признака"), fontname=FONT_NAME, fontsize=13)
        axes.set_ylabel("μ(x)", fontname=FONT_NAME, fontsize=13)
        axes.tick_params(axis="both", labelsize=13)
        for tick_label in (*axes.get_xticklabels(), *axes.get_yticklabels()):
            tick_label.set_fontname(FONT_NAME)

        self.figure.suptitle(
            item.feature_name,
            fontname=FONT_NAME,
            fontsize=13,
            fontweight="bold",
            y=0.98,
        )
        axes.text(
            0.5, 0.92,
            f"{self._t('Терм')}: {item.term_name}",
            transform=self.figure.transFigure,
            ha="center", va="center",
            fontname=FONT_NAME, fontsize=13,
        )
        legend = axes.legend(
            handles=legend_handles,
            loc="upper center",
            bbox_to_anchor=(0.5, 0.89),
            bbox_transform=self.figure.transFigure,
            ncol=len(legend_handles),
            frameon=False,
            prop={"family": FONT_NAME, "size": 13},
        )
        self.legend_items.clear()
        self.legend_artists.clear()
        for label, legend_line, legend_text in zip(
            self.artist_groups,
            legend.get_lines(),
            legend.get_texts(),
        ):
            legend_line.set_picker(5)
            legend_text.set_picker(True)
            alpha = 0.28 if label in self.hidden_curves else 1.0
            legend_line.set_alpha(alpha)
            legend_text.set_alpha(alpha)
            self.legend_items[legend_line] = label
            self.legend_items[legend_text] = label
            self.legend_artists[label] = (legend_line, legend_text)

        self.default_limits = (axes.get_xlim(), axes.get_ylim())
        self.prev_button.configure(state="disabled" if self.feature_index == 0 else "normal")
        self.next_button.configure(
            state="disabled" if self.feature_index == len(self.evaluation.features) - 1 else "normal"
        )
        self.canvas.draw_idle()

    def _remember_support_points(self, values, curve_label: str) -> None:
        """Сохраняет точки трапеции для подсказок при наведении."""

        point_names = (
            "левая граница основания",
            "левая граница ядра",
            "правая граница ядра",
            "правая граница основания",
        )
        for x_value, y_value, point_name in zip(values, (0.0, 1.0, 1.0, 0.0), point_names):
            self.support_points.append((float(x_value), y_value, curve_label, point_name))

    def _toggle_curve(self, event) -> None:
        """Скрывает или показывает линию щелчком по легенде."""

        label = self.legend_items.get(event.artist)
        if label is None:
            return
        visible = not self.artist_groups[label][0].get_visible()
        for artist in self.artist_groups[label]:
            artist.set_visible(visible)
        for legend_artist in self.legend_artists[label]:
            legend_artist.set_alpha(1.0 if visible else 0.28)
        if visible:
            self.hidden_curves.discard(label)
        else:
            self.hidden_curves.add(label)
        self.canvas.draw_idle()

    def _zoom(self, event) -> None:
        """Масштабирует график колёсиком относительно указателя."""

        if event.inaxes is not self.axes or event.xdata is None or event.ydata is None:
            return
        scale = 0.85 if event.step > 0 else 1.18
        x_min, x_max = self.axes.get_xlim()
        y_min, y_max = self.axes.get_ylim()
        self.axes.set_xlim(
            event.xdata - (event.xdata - x_min) * scale,
            event.xdata + (x_max - event.xdata) * scale,
        )
        self.axes.set_ylim(
            event.ydata - (event.ydata - y_min) * scale,
            event.ydata + (y_max - event.ydata) * scale,
        )
        self.canvas.draw_idle()

    def _start_pan(self, event) -> None:
        """Начинает перемещение графика левой кнопкой мыши."""

        if event.inaxes is not self.axes or event.button != 1:
            return
        if event.dblclick:
            self.axes.set_xlim(self.default_limits[0])
            self.axes.set_ylim(self.default_limits[1])
            self.canvas.draw_idle()
            return
        self.pan_state = (event.xdata, event.ydata, self.axes.get_xlim(), self.axes.get_ylim())

    def _move_pan(self, event) -> None:
        """Перемещает видимую область во время перетаскивания."""

        if self.pan_state is None or event.inaxes is not self.axes:
            return
        if event.xdata is None or event.ydata is None:
            return
        start_x, start_y, x_limits, y_limits = self.pan_state
        if start_x is None or start_y is None:
            return
        self.axes.set_xlim(x_limits[0] - (event.xdata - start_x), x_limits[1] - (event.xdata - start_x))
        self.axes.set_ylim(y_limits[0] - (event.ydata - start_y), y_limits[1] - (event.ydata - start_y))
        self.annotation.set_visible(False)
        self.canvas.draw_idle()

    def _stop_pan(self, event) -> None:
        """Завершает перемещение графика."""

        if event.button == 1:
            self.pan_state = None

    def _hover(self, event) -> None:
        """Показывает координаты ближайшей опорной точки ФП."""

        if self.pan_state is not None:
            return
        if event.inaxes is not self.axes or event.x is None or event.y is None:
            self._hide_annotation()
            return

        visible_points = (
            point
            for point in self.support_points
            if point[2] not in self.hidden_curves
        )
        nearest = None
        nearest_distance = float("inf")
        for point in visible_points:
            screen_x, screen_y = self.axes.transData.transform((point[0], point[1]))
            distance = (screen_x - event.x) ** 2 + (screen_y - event.y) ** 2
            if distance < nearest_distance:
                nearest = point
                nearest_distance = distance
        if nearest is None or nearest_distance > 100:
            self._hide_annotation()
            return

        x_value, y_value, curve_label, _point_name = nearest
        self.annotation.xy = (x_value, y_value)
        self.annotation.set_text(
            f"{self._t(curve_label)}\n"
            f"x = {_number(x_value)}\nμ(x) = {_number(y_value)}"
        )
        self.annotation.set_visible(True)
        self.canvas.draw_idle()

    def _hide_annotation(self) -> None:
        """Скрывает подсказку после ухода указателя от точки."""

        if self.annotation.get_visible():
            self.annotation.set_visible(False)
            self.canvas.draw_idle()


def _number(value: float) -> str:
    return f"{value:.4f}".rstrip("0").rstrip(".").replace(".", ",")
