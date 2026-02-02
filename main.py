from json2schema2schema import Converter, PseudoArrayHandler
from json2schema2schema.comparators import FormatComparator, RequiredComparator, EmptyComparator, DeleteElement, TypeComparator
import time

cur = time.time()

# Инициализируем сам обработчик (он многоразовый)
conv = Converter(
    pseudo_handler=PseudoArrayHandler(), # Библиотека поддерживает генерацию псевдомассивных структур (можно определить свой обработчик)
    base_of="anyOf",                     # Во что будут помещаться блоки при конфликтных значениях. anyOf/oneOf/allOf
    core_comparator=TypeComparator()     # Атрибут type - единственный без которого pipeline не может построить схему, поэтому он выведен отдельно
)

# Добавлять можно как файл так и list/dict
conv.add_json("ClassCatalog.tree.json")
conv.add_json({
    "name": "alice@example.com",
    "email": "alice@example.com",
    "identifier": "3f2504e0-4f89-11d3-9a0c-0305e82c3301",
    "created": "2024-01-31"
})
# Схемы аналогично можно добавлять
conv.add_schema({"type": "object", "properties": {"name": {"type": "object", "properties": {"name": {"type": "integer"}}}}})

# Логика j2s - компараторы которые определяют все

conv.register(FormatComparator())   # поле format и определение форматов
conv.register(RequiredComparator()) # поле required и определение обязательных значений
conv.register(EmptyComparator())    # поля max/min Properties/Items и определение полностью пустых (т.е. пустые значения во всех вариантах данных)
conv.register(DeleteElement())      # удаление атрибутов, в данном случае удаляется технический атрибут j2sElementTrigger (список источников от куда пришли данные)
conv.register(DeleteElement("isPseudoArray")) # удаление технического атрибута isPseudoArray (появляется когда pseudo_handler настроен)

# Запуск обработки
result = conv.run()
print(result)
