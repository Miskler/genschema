from genschema import Converter, PseudoArrayHandler
from genschema.comparators import FormatComparator, RequiredComparator, EmptyComparator, DeleteElement, TypeComparator, SchemaVersionComparator
import time

cur = time.time()

# Инициализируем сам обработчик (он многоразовый)
conv = Converter(
    pseudo_handler=PseudoArrayHandler(), # Библиотека поддерживает генерацию псевдомассивных структур (можно определить свой обработчик)
    base_of="anyOf",                     # Во что будут помещаться блоки при конфликтных значениях. anyOf/oneOf/allOf
    core_comparator=TypeComparator()     # Атрибут type - единственный без которого pipeline не может построить схему, поэтому он выведен отдельно
)

# Добавлять можно как файл так и list/dict
#conv.add_json("ClassCatalog.tree.json")
conv.add_json({
        "обязательная": "строка",
        "необязательная": None,
        "словарь": {
            "ключ": "значение",
            "число": 123,
            "булево": True,
            "список": [1, 2, 3],
            "вложенный_словарь": {
                "пустое": None,
            },
            "пустой_словарь": {},
            "пустой_список": [],
            "пустое_значение": "",
            "пустое_число": 0,
            # Добавляем новое поле для обновления схемы
            "дополнительное_поле": "для обновления",
        },
        "сложная_структура": [
            {
                "id": 1,
                "имя": "Иван",
                "почта": "ivan@example.com",
                "возраст": 25,
                "дата": "2023-01-01T12:00:00Z",
                "вложенный_объект": {"ключ": "значение"},
            },
            {
                "id": 2,
                "имя": ["Мария", "Анна"],
                "возраст": 30.5,
                "вложенный_объект": {"ключ": "значение", "лишний_ключ": None},
            },
        ],
        "разнотипный_массив": [None, "строка", {"ключ": "значение"}],
    })
# Схемы аналогично можно добавлять
#conv.add_schema({"type": "object", "properties": {"name": {"type": "object", "properties": {"name": {"type": "integer"}}}}})

# Логика j2s - компараторы которые определяют все

conv.register(FormatComparator())   # поле format и определение форматов
conv.register(SchemaVersionComparator())   # поле format и определение форматов
conv.register(RequiredComparator()) # поле required и определение обязательных значений
conv.register(EmptyComparator())    # поля max/min Properties/Items и определение полностью пустых (т.е. пустые значения во всех вариантах данных)
conv.register(DeleteElement())      # удаление атрибутов, в данном случае удаляется технический атрибут j2sElementTrigger (список источников от куда пришли данные)
conv.register(DeleteElement("isPseudoArray")) # удаление технического атрибута isPseudoArray (появляется когда pseudo_handler настроен)

# Запуск обработки
result = conv.run()
from pprint import pprint
pprint(result)
