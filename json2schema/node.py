from enum import Enum, auto
from typing import Any


class NodeKind(Enum):
    SCALAR = auto()
    OBJECT = auto()
    ARRAY = auto()
    UNION = auto()


class SchemaNode:
    def __init__(self, kind: NodeKind):
        self.kind = kind
        self.schema: dict[str, Any] = {}

    def as_dict(self) -> dict[str, Any]:
        return self.schema
