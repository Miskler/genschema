from json2schema.core.pipeline import Converter
from json2schema.core.comparators import TypeComparator, FormatComparator, RequiredComparator
import json
import time

cur = time.time()

conv = Converter()
conv.add_schema({"type": "object", "properties": {"name": {"type": "integer"}}})
conv.add_json([{"name": "fdfddfm"}])
conv.add_json({"name": "fdfddfm"})
conv.add_json([{"name": "https://dddd.ru"}])
conv.add_json({"name": "https://dddd.ru"})
conv.add_json({
    "name": "alice@example.com",
    "email": "alice@example.com",
    "identifier": "3f2504e0-4f89-11d3-9a0c-0305e82c3301",
    "created": "2024-01-31"
})
conv.register(TypeComparator())
conv.register(FormatComparator())
conv.register(RequiredComparator())
print(json.dumps(conv.run(), indent=2, ensure_ascii=False))
print(f"Затраченное время: {round(time.time()-cur, 5)}")
