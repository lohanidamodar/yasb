import logging
import re
from datetime import date, datetime, timedelta

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from core.utils.tooltip import set_tooltip
from core.utils.utilities import PopupWidget, add_shadow, build_widget_label
from core.utils.widgets.animation_manager import AnimationManager
from core.validation.widgets.yasb.nepali_date import NepaliDateConfig
from core.widgets.base import BaseWidget
from core.widgets.yasb.nepali_date_data import EN_TO_NP_DATA, NP_TO_EN_DATA

NP_MONTHS = [
    "बैशाख",
    "जेठ",
    "असार",
    "साउन",
    "भदौ",
    "असोज",
    "कार्तिक",
    "मंसिर",
    "पुष",
    "माघ",
    "फाल्गुन",
    "चैत्र",
]

NP_MONTHS_EN = [
    "Baisakh",
    "Jestha",
    "Asar",
    "Shrawan",
    "Bhadra",
    "Asoj",
    "Kartik",
    "Mangsir",
    "Poush",
    "Magh",
    "Falgun",
    "Chaitra",
]

NP_DAYS = [
    "आइतबार",
    "सोमबार",
    "मंगलबार",
    "बुधबार",
    "बिहीबार",
    "शुक्रबार",
    "शनिबार",
]

NP_DIGITS = ["०", "१", "२", "३", "४", "५", "६", "७", "८", "९"]

EN_MONTHS = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]


def _to_nepali_digits(num):
    return "".join(NP_DIGITS[int(d)] for d in str(num))


def _get_np_month_days(np_year, np_month):
    entry = NP_TO_EN_DATA.get((np_year, np_month))
    return entry[0] if entry else None


def en_to_np(en_year, en_month, en_day):
    entry = EN_TO_NP_DATA.get((en_year, en_month))
    if not entry:
        return None
    days_in_month, np_year, np_month, np_day = entry
    # Data stores NP date for the last day of the EN month; subtract back
    days_to_subtract = days_in_month - en_day
    new_day = np_day - days_to_subtract
    while new_day <= 0:
        if np_month == 1:
            np_year -= 1
            np_month = 12
        else:
            np_month -= 1
        new_day += _get_np_month_days(np_year, np_month)
    return np_year, np_month, new_day


def np_to_en(np_year, np_month, np_day):
    entry = NP_TO_EN_DATA.get((np_year, np_month))
    if not entry:
        return None
    days_in_month, en_year, en_month, en_day = entry
    # Data stores EN date for the last day of the NP month; offset back
    en_date = date(en_year, en_month, en_day) + timedelta(days=np_day - days_in_month)
    return en_date.year, en_date.month, en_date.day


class NepaliDateWidget(BaseWidget):
    validation_schema = NepaliDateConfig

    def __init__(self, config: NepaliDateConfig):
        super().__init__(config.update_interval, class_name=f"nepali-date-widget {config.class_name}")
        self.config = config
        self._show_alt_label = False
        self._label_content = config.label
        self._label_alt_content = config.label_alt

        self._widget_container_layout = QHBoxLayout()
        self._widget_container_layout.setSpacing(0)
        self._widget_container_layout.setContentsMargins(0, 0, 0, 0)
        self._widget_container = QFrame()
        self._widget_container.setLayout(self._widget_container_layout)
        self._widget_container.setProperty("class", "widget-container")
        add_shadow(self._widget_container, config.container_shadow.model_dump())
        self.widget_layout.addWidget(self._widget_container)

        build_widget_label(self, self._label_content, self._label_alt_content, config.label_shadow.model_dump())

        self.register_callback("toggle_label", self._toggle_label)
        self.register_callback("toggle_converter", self._toggle_converter)
        self.register_callback("update_label", self._update_label)

        self.callback_left = config.callbacks.on_left
        self.callback_right = config.callbacks.on_right
        self.callback_middle = config.callbacks.on_middle
        self.callback_timer = "update_label"

        self._update_label()

    def _get_today_nepali(self):
        today = datetime.now()
        result = en_to_np(today.year, today.month, today.day)
        if result is None:
            return None
        np_y, np_m, np_d = result
        weekday = today.weekday()
        # Python weekday: Mon=0, Sun=6. Nepali: Sun=0, Sat=6
        np_weekday = (weekday + 1) % 7
        return {
            "np_year": np_y,
            "np_month": np_m,
            "np_day": np_d,
            "np_month_name": NP_MONTHS[np_m - 1],
            "np_month_name_en": NP_MONTHS_EN[np_m - 1],
            "np_day_name": NP_DAYS[np_weekday],
            "np_year_np": _to_nepali_digits(np_y),
            "np_month_np": _to_nepali_digits(np_m),
            "np_day_np": _to_nepali_digits(np_d),
            "np_date": f"{_to_nepali_digits(np_y)}/{_to_nepali_digits(np_m)}/{_to_nepali_digits(np_d)}",
            "np_date_en": f"{np_y}/{np_m:02d}/{np_d:02d}",
            "np_date_full": f"{NP_DAYS[np_weekday]}, {_to_nepali_digits(np_d)} {NP_MONTHS[np_m - 1]} {_to_nepali_digits(np_y)}",
            "np_date_full_en": f"{NP_MONTHS_EN[np_m - 1]} {np_d}, {np_y}",
            "en_date": today.strftime("%Y/%m/%d"),
            "en_date_full": today.strftime("%A, %B %d, %Y"),
        }

    def _update_label(self):
        np_info = self._get_today_nepali()
        if np_info is None:
            return

        active_widgets = self._widgets_alt if self._show_alt_label else self._widgets
        active_label_content = self._label_alt_content if self._show_alt_label else self._label_content
        label_parts = re.split("(<span.*?>.*?</span>)", active_label_content)
        label_parts = [part for part in label_parts if part]
        widget_index = 0

        for part in label_parts:
            part = part.strip()
            if part and widget_index < len(active_widgets) and isinstance(active_widgets[widget_index], QLabel):
                if "<span" in part and "</span>" in part:
                    icon = re.sub(r"<span.*?>|</span>", "", part).strip()
                    try:
                        icon = icon.format(**np_info)
                    except (KeyError, IndexError):
                        pass
                    active_widgets[widget_index].setText(icon)
                else:
                    try:
                        formatted = part.format(**np_info)
                    except (KeyError, IndexError):
                        formatted = part
                    active_widgets[widget_index].setText(formatted)
                widget_index += 1

        if self.config.tooltip:
            try:
                tooltip_text = self.config.tooltip_label.format(**np_info)
                set_tooltip(self, tooltip_text)
            except (KeyError, IndexError):
                pass

    def _toggle_label(self):
        if self.config.animation.enabled:
            AnimationManager.animate(self, self.config.animation.type, self.config.animation.duration)
        self._show_alt_label = not self._show_alt_label
        for widget in self._widgets:
            widget.setVisible(not self._show_alt_label)
        for widget in self._widgets_alt:
            widget.setVisible(self._show_alt_label)
        self._update_label()

    def _toggle_converter(self):
        if self.config.animation.enabled:
            AnimationManager.animate(self, self.config.animation.type, self.config.animation.duration)
        self._show_converter()

    def _show_converter(self):
        converter_cfg = self.config.converter
        popup = PopupWidget(
            self,
            converter_cfg.blur,
            converter_cfg.round_corners,
            converter_cfg.round_corners_type,
            converter_cfg.border_color,
        )
        popup.setProperty("class", "nepali-date-popup converter")

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        popup.setLayout(layout)

        # Title
        title = QLabel("Date Converter")
        title.setProperty("class", "converter-title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Mode selector
        mode_layout = QHBoxLayout()
        en_to_np_btn = QPushButton("EN → NP")
        en_to_np_btn.setProperty("class", "button mode active")
        en_to_np_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        en_to_np_btn.setCheckable(True)
        en_to_np_btn.setChecked(True)

        np_to_en_btn = QPushButton("NP → EN")
        np_to_en_btn.setProperty("class", "button mode")
        np_to_en_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        np_to_en_btn.setCheckable(True)

        mode_layout.addWidget(en_to_np_btn)
        mode_layout.addWidget(np_to_en_btn)
        layout.addLayout(mode_layout)

        # Input container
        input_container = QFrame()
        input_container.setProperty("class", "converter-input-container")
        input_layout = QVBoxLayout(input_container)
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.setSpacing(4)

        # Date input row
        date_row = QHBoxLayout()

        year_spin = QSpinBox()
        year_spin.setProperty("class", "converter-input")
        year_spin.setRange(1844, 2143)
        year_spin.setValue(datetime.now().year)
        year_spin.setPrefix("Y: ")

        month_combo = QComboBox()
        month_combo.setProperty("class", "converter-input")

        day_spin = QSpinBox()
        day_spin.setProperty("class", "converter-input")
        day_spin.setRange(1, 31)
        day_spin.setValue(datetime.now().day)
        day_spin.setPrefix("D: ")

        date_row.addWidget(year_spin)
        date_row.addWidget(month_combo)
        date_row.addWidget(day_spin)
        input_layout.addLayout(date_row)

        layout.addWidget(input_container)

        # Convert button
        convert_btn = QPushButton("Convert")
        convert_btn.setProperty("class", "button convert")
        convert_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(convert_btn)

        # Result display
        result_frame = QFrame()
        result_frame.setProperty("class", "converter-result")
        result_layout = QVBoxLayout(result_frame)
        result_layout.setContentsMargins(8, 8, 8, 8)

        result_label = QLabel("")
        result_label.setProperty("class", "result-text")
        result_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        result_label.setWordWrap(True)
        result_layout.addWidget(result_label)

        layout.addWidget(result_frame)

        # Today info
        np_info = self._get_today_nepali()
        if np_info:
            today_label = QLabel(f"Today: {np_info['np_date_full']}")
            today_label.setProperty("class", "today-label")
            today_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(today_label)

        is_en_mode = [True]

        def _populate_months_en():
            month_combo.clear()
            for i, m in enumerate(EN_MONTHS):
                month_combo.addItem(m, i + 1)
            month_combo.setCurrentIndex(datetime.now().month - 1)

        def _populate_months_np():
            month_combo.clear()
            for i, m in enumerate(NP_MONTHS_EN):
                month_combo.addItem(f"{m} ({NP_MONTHS[i]})", i + 1)
            if np_info:
                month_combo.setCurrentIndex(np_info["np_month"] - 1)

        def _update_day_range():
            if is_en_mode[0]:
                y = year_spin.value()
                m = month_combo.currentData()
                if m is None:
                    return
                entry = EN_TO_NP_DATA.get((y, m))
                max_days = entry[0] if entry else 31
            else:
                y = year_spin.value()
                m = month_combo.currentData()
                if m is None:
                    return
                entry = NP_TO_EN_DATA.get((y, m))
                max_days = entry[0] if entry else 32
            current_day = day_spin.value()
            day_spin.setRange(1, max_days)
            if current_day > max_days:
                day_spin.setValue(max_days)

        def _switch_to_en():
            if is_en_mode[0]:
                return
            is_en_mode[0] = True
            en_to_np_btn.setChecked(True)
            np_to_en_btn.setChecked(False)
            en_to_np_btn.setProperty("class", "button mode active")
            np_to_en_btn.setProperty("class", "button mode")
            en_to_np_btn.style().unpolish(en_to_np_btn)
            en_to_np_btn.style().polish(en_to_np_btn)
            np_to_en_btn.style().unpolish(np_to_en_btn)
            np_to_en_btn.style().polish(np_to_en_btn)
            year_spin.setRange(1844, 2143)
            year_spin.setValue(datetime.now().year)
            _populate_months_en()
            day_spin.setValue(datetime.now().day)
            result_label.setText("")
            _update_day_range()

        def _switch_to_np():
            if not is_en_mode[0]:
                return
            is_en_mode[0] = False
            en_to_np_btn.setChecked(False)
            np_to_en_btn.setChecked(True)
            en_to_np_btn.setProperty("class", "button mode")
            np_to_en_btn.setProperty("class", "button mode active")
            en_to_np_btn.style().unpolish(en_to_np_btn)
            en_to_np_btn.style().polish(en_to_np_btn)
            np_to_en_btn.style().unpolish(np_to_en_btn)
            np_to_en_btn.style().polish(np_to_en_btn)
            year_spin.setRange(1901, 2199)
            if np_info:
                year_spin.setValue(np_info["np_year"])
            else:
                year_spin.setValue(2080)
            _populate_months_np()
            if np_info:
                day_spin.setValue(np_info["np_day"])
            result_label.setText("")
            _update_day_range()

        def _convert():
            y = year_spin.value()
            m = month_combo.currentData()
            d = day_spin.value()
            if m is None:
                result_label.setText("Please select a month")
                return
            if is_en_mode[0]:
                result = en_to_np(y, m, d)
                if result:
                    np_y, np_m, np_d = result
                    np_date_str = f"{_to_nepali_digits(np_y)} {NP_MONTHS[np_m - 1]} {_to_nepali_digits(np_d)}"
                    en_date_str = f"{NP_MONTHS_EN[np_m - 1]} {np_d}, {np_y}"
                    result_label.setText(f"{np_date_str}\n{en_date_str}")
                else:
                    result_label.setText("Date out of range")
            else:
                result = np_to_en(y, m, d)
                if result:
                    en_y, en_m, en_d = result
                    result_label.setText(f"{EN_MONTHS[en_m - 1]} {en_d}, {en_y}\n{en_y}/{en_m:02d}/{en_d:02d}")
                else:
                    result_label.setText("Date out of range")

        en_to_np_btn.clicked.connect(_switch_to_en)
        np_to_en_btn.clicked.connect(_switch_to_np)
        convert_btn.clicked.connect(_convert)
        year_spin.valueChanged.connect(lambda: _update_day_range())
        month_combo.currentIndexChanged.connect(lambda: _update_day_range())

        _populate_months_en()
        _update_day_range()

        popup.adjustSize()
        popup.setPosition(
            alignment=converter_cfg.alignment,
            direction=converter_cfg.direction,
            offset_left=converter_cfg.offset_left,
            offset_top=converter_cfg.offset_top,
        )
        popup.show()
