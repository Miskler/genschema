from typing import Optional

from .comparators.template import ProcessingContext


class PseudoArrayHandlerBase:
    def is_pseudo_array(
        self, keys: list[str], ctx: ProcessingContext
    ) -> tuple[bool, Optional[str]]:
        return False, None


class PseudoArrayHandler(PseudoArrayHandlerBase):
    def is_pseudo_array(
        self, keys: list[str], ctx: ProcessingContext
    ) -> tuple[bool, Optional[str]]:
        if not keys:
            return False, None
        try:
            [int(k) for k in keys]
            return True, "^[0-9]+$"
        except ValueError:
            return False, None
