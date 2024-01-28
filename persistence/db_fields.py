from typing import Optional
from typing import Any, Union, Type


from tortoise.fields import JSONField
from .pydantic_models import AdvancedOptions
from tortoise import Model


class PydanticDBField(JSONField):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def to_db_value(self, value: "AdvancedOptions", instance: "Union[Type[Model], Model]") -> "Any":
        return super().to_db_value(value.dict() if value else None, instance)

    def to_python_value(
        self, value: Optional[Union[str, bytes, dict, list]]
    ) -> Optional[AdvancedOptions]:
        data = super().to_python_value(value)
        if data is None:
            return None
        if not isinstance(data, AdvancedOptions):
            return AdvancedOptions(**data)
        return value


