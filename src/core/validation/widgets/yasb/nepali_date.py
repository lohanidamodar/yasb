from pydantic import Field

from core.validation.widgets.base_model import (
    AnimationConfig,
    CallbacksConfig,
    CustomBaseModel,
    KeybindingConfig,
    ShadowConfig,
)


class CallbacksNepaliDateConfig(CallbacksConfig):
    on_left: str = "toggle_label"
    on_right: str = "toggle_converter"


class ConverterConfig(CustomBaseModel):
    blur: bool = True
    round_corners: bool = True
    round_corners_type: str = "normal"
    border_color: str = "System"
    alignment: str = "center"
    direction: str = "down"
    offset_top: int = 6
    offset_left: int = 0


class NepaliDateConfig(CustomBaseModel):
    label: str = "\uf073 {np_date}"
    label_alt: str = "\uf073 {np_date_full}"
    class_name: str = ""
    update_interval: int = Field(default=60000, ge=1000, le=3600000)
    tooltip: bool = True
    tooltip_label: str = "{np_date_full}\n{en_date_full}"
    animation: AnimationConfig = AnimationConfig()
    label_shadow: ShadowConfig = ShadowConfig()
    container_shadow: ShadowConfig = ShadowConfig()
    callbacks: CallbacksNepaliDateConfig = CallbacksNepaliDateConfig()
    keybindings: list[KeybindingConfig] = []
    converter: ConverterConfig = ConverterConfig()
