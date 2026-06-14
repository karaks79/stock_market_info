from langchain_gigachat.chat_models import GigaChat
from langchain_core.messages import SystemMessage, HumanMessage
from sentence_transformers import SentenceTransformer  # 2.7 GB - вес библиотеки (на D:\wsl)!!!
import psycopg
import json
from pprint import pprint

chat = GigaChat(
    credentials = "MDE5ZGUzZDgtZDM1Ny03Yjg5LTg0ZGUtZDRhYmZhMjNlYWYwOjg3YzAxMDVlLTgyNTUtNGZlZC1iMTE3LThiZDQyYjQzYzgwMQ==",
    # Для работы с API нужны сертификаты НУЦ МинЦифры
    # Если нужно, проверуку сертификатов можно отключить с помощью параметра verify_ssl_certs
    verify_ssl_certs=False,
    temperature=0.2,        # 0.0 → строгий, детерминированный, 2.0 → креативный, «фантазирует»
    max_tokens=100           # ограничение длины ответа
)

sent_transf_model = SentenceTransformer(
    "paraphrase-multilingual-MiniLM-L12-v2"
)

def prompt_choose_table_1():
    txt = """
Ты — эксперт по анализу SQL-схем.

Тебе дан:
1) Вопрос пользователя
2) Список таблиц и VIEW

Задача:
Выбрать минимальный набор объектов, нужных для ответа.

Правила:
- Не добавляй лишние таблицы
- Используй только описания
- Если одна таблица подходит — выбери только её

Ты возвращаешь ТОЛЬКО валидный JSON.

Запрещено:
- любые строки вокруг JSON
- markdown
- объяснения
- переносы текста вне JSON
- оборачивание JSON в кавычки

Формат ответа строго:
[
  {
    "sql_object_name": "...",
    "reason": "..."
  }
]

ВАЖНО:
Поле sql_object_name должно содержать только одно из значений sql_object_name,
которые присутствуют во входных данных.

Нельзя:
- переводить названия
- изменять названия
- придумывать новые sql_object_name
- использовать синонимы

Если подходящего sql_object_name нет во входных данных —
не придумывай его.

Используй exact match из schema_objects.

- Верни только JSON
- Не оборачивай JSON в строку
"""
    return txt

def prompt_choose_table_2():
    txt = f"""
    Ты — эксперт по анализу SQL-схем.

    Тебе дан:
    1) Вопрос пользователя
    2) Список таблиц и VIEW с описанием:

    {schema_objects}

    Задача:
    Выбрать минимальный набор объектов, нужных для ответа.

    Выбирай sql_object_id, используя sql_object_name и description для понимания.

    Важно:
    - ориентируйся прежде всего на object_description таблиц
    - имя таблицы используется только для идентификации
    - не выбирай таблицы только по совпадению названия

    Формат ответа строго JSON:
    [
        {{                                  # {{ - экранирование f-строки
            "sql_object_id": "...",
            "sql_object_name": "...",
            "reason": "..."
        }}                                  # }} - экранирование f-строки
    ]
    """
    return txt

def prompt_choose_table_3():
    txt = f"""
    Ты — эксперт по анализу SQL-схем.

    Тебе дан:
    1) Вопрос пользователя
    2) Список таблиц и VIEW

    Задача:
    Выбрать минимальный набор объектов, нужных для ответа.

    Список допустимых sql_object_name:

    {list_of_objects}

    Правила:
    - Используй ТОЛЬКО значения из списка
    - НЕ переводи названия
    - НЕ создавай новые значения
    - НЕ используй синонимы
    - sql_object_name = ENUM    

    Формат ответа строго JSON:
    [
        {{                                  # {{ - экранирование f-строки
            "sql_object_name": "...",
            "reason": "..."
        }}                                  # }} - экранирование f-строки
    ]
    """
    return txt

def prompt_entity_extractor_1():
    txt = f"""
    Ты — система извлечения сущностей из пользовательского запроса.

    Твоя задача:
    выделить бизнес-сущности, упомянутые в вопросе пользователя.

    Формат ответа строго JSON:
    {{                                  # {{ - экранирование f-строки
        "entities": [
            "Сущность1",
            "Сущность2"
        ]
    }}                                  # }} - экранирование f-строки
    """
    return txt

def prompt_entity_extractor_2():
    txt = f"""
    Ты — система извлечения сущностей из пользовательского запроса.

    Твоя задача:
    выделить бизнес-сущности, упомянутые в вопросе пользователя.

    Список допустимых сущностей:

    {list_of_objects}
    
    Формат ответа строго JSON:
    {{                                  # {{ - экранирование f-строки
        "entities": [
            "Сущность1",
            "Сущность2"
        ]
    }}                                  # }} - экранирование f-строки
    """
    return txt

def select_tables(user_question: str, list_of_objects: list, schema_objects: list[dict]):
    """ИИ выбирает таблицы для запроса"""
     
    system_prompt = prompt_entity_extractor_2()

    user_prompt = f"""
    Вопрос пользователя:
    {user_question}
 
    """
    
    # Список таблиц и VIEW:
    # {json.dumps(schema_objects, ensure_ascii=False, indent=2)}

    system = SystemMessage(content=system_prompt)
    human = HumanMessage(content=user_prompt)

    response = chat.invoke([system, human])

    return response

def get_table_metadata():
    """Получить список таблиц и VIEW и их описание"""
    with psycopg.connect(
        host="192.168.240.1", dbname="postgres", user="postgres", password="2211", port=5432
    ) as conn:
    # чтобы не писать conn.close()
        query = """
        SELECT 
	        b.object_id AS sql_object_id,
            b.object_name AS sql_object_name, 
            b.object_description AS object_description,
            array_agg(c.column_name ORDER BY c.column_name) AS columns_summary
        FROM
	        metadata.schema_objects AS b
	        INNER JOIN metadata.schema_columns AS c 
		        ON b.object_id = c.object_id
        GROUP BY 
	        b.object_id,
            b.object_name, 
            b.object_description
        """

        cur = conn.cursor()
        cur.execute(query)
        rows = cur.fetchall()                               # list[tuple]
        columns = [desc[0] for desc in cur.description]     # list()

    result = [dict(zip(columns, row)) for row in rows]
    #pprint(result)
    # [
    #     {"sql_object_name": "actor", "object_description": "список актёров", "columns_summary": ['actor_id', 'first_name', 'last_name', 'last_update']},
    #     {"sql_object_name": "city", "object_description": "города", "columns_summary": ['city', 'city_id', 'country_id', 'last_update']},
    #     ...
    # ]


def get_list_table_metadata():
    """Получить только список таблиц и VIEW"""
    with psycopg.connect(
        host="192.168.240.1", dbname="postgres", user="postgres", password="2211", port=5432
    ) as conn:
    # чтобы не писать conn.close()
        query = """
        SELECT array_agg(object_description ORDER BY object_description) FROM metadata.schema_objects
        """

        cur = conn.cursor()
        cur.execute(query)
        row = cur.fetchone()

        return row[0]


def parse_llm_output(content: str):
    """Извлечь JSON из строки"""
    content = content.strip()

    # если это строка, содержащая JSON
    # if content.startswith('"') and content.endswith('"'):
    #     content = json.loads(content)

    # теперь нормальный JSON
    return json.loads(content)


def compare_embeddings(list_of_objects, entities):
    """Сравнение эмбеддингов"""
    for entity in entities["entities"]:
        vector = sent_transf_model.encode(entity)      # 384 координаты вектора (от -1 до 1)
        print(f'{entity}: {vector}')



#question = "Покажи всех клиентов и их адреса"
#question = "Покажи всех клиентов и их адреса, города и страны"
question = "Покажи всех клиентов, которые брали в аренду фильмы на испанском языке"

list_of_objects = get_list_table_metadata()
schema_objects = get_table_metadata()

#result = select_tables(question, list_of_objects, schema_objects)

# #pprint(result)
# pprint(result.content)
# print(f'input_tokens: {result.usage_metadata['input_tokens']}')
# print(f'output_tokens: {result.usage_metadata['output_tokens']}')
# print(f'total_tokens: {result.usage_metadata['total_tokens']}')

#print(parse_llm_output(json.dumps(result.content, ensure_ascii=False, indent=2)))

#print(list_of_objects)

# S = "[\n        {\n            \"sql_object_name\": \"customer\",\n            \"reason\": \"требуется для вывода информации о клиентах\"\n        },\n        {\n            \"sql_object_name\": \"address\",\n            \"reason\": \"требуется для получения информации об адресах клиентов\"\n        }\n]"
# s_after_parse = parse_llm_output(S)
# print(s_after_parse)
# print(type(s_after_parse))

entities = {
    "entities": [
        "клиенты магазина",
        "языки фильмов",
        "факты аренды фильмов"
    ]
}

compare_embeddings(list_of_objects, entities)
