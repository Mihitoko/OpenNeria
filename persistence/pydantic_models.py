from typing import Optional

from pydantic import BaseModel


class AdvancedOptions(BaseModel):
    min_gear_score: Optional[int] = None
    max_same_class: Optional[int] = None
    min_supporters: Optional[int] = 0
    prio_roles: Optional[list[int]] = []
    prio_time: Optional[int] = 0
    ping_roles: Optional[list[int]] = []
    text_on_exit: Optional[bool] = False
