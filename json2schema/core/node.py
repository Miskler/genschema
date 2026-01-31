from enum import Enum, auto
from typing import Dict, Any


class NodeKind(Enum):
    SCALAR = auto()
    OBJECT = auto()
    ARRAY = auto()
    UNION = auto()


class SchemaNode:
    def __init__(self, kind: NodeKind):
        self.kind = kind
        self.schema: Dict[str, Any] = {}

    def as_dict(self) -> Dict[str, Any]:
        return self.schema
