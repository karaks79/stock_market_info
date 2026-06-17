import json
import time
import os
from pprint import pprint
from dotenv import load_dotenv

t0 = time.time()
print(f"{t0=}: Перед import GigaChat")
from langchain_gigachat.chat_models import GigaChat
from langchain_core.messages import SystemMessage, HumanMessage
t1 = time.time()
print(f"{t1=}: После import GigaChat")


def read_from_json(file_name: str) -> dict:
    """Читать JSON в словарь"""
    with open(file_name, "r") as f:
        try:
            result = json.load(f)
            return result
        except json.JSONDecodeError as e:
            return {"error": f"{e}"}


def get_columns(all_tables_columns: dict, tables: list) -> dict:
    """Возвращает словарь полей указанных таблиц"""

    return {k: v for k, v in all_tables_columns.items() if k in tables}


def get_relations(all_relations: dict, tables: list) -> list:
    """Возвращает список связей указанных таблиц"""

    result = []

    for table_name, table_info in all_relations.items():

        if table_name not in tables:
            continue

        for relation in table_info["relations"]:
            if (
                relation["table"] in tables 
                and relation["cardinality"] == "one-to-many"
            ):
              result.append(relation["join_condition"])  
    
    return result


def build_table_graph(relations: dict) -> dict:
    """Строить граф связей таблиц"""
    
    join_tables = {}
    
    for table, val in relations.items():
        for item in val["relations"]:
            if table in join_tables:
                if item["table"] not in join_tables[table]:
                    join_tables[table].append(item["table"])
            else:
                join_tables[table] = [item["table"]]
    
    for v in join_tables.values():
        v.sort()

    return join_tables


def get_system_message() -> str:
    """Возвращает системный prompt"""
    return """
Ты опытный SQL-разработчик.

Твоя задача:
1. Использовать только предоставленные таблицы.
2. Использовать только предоставленные поля.
3. Использовать только предоставленные связи.
4. Вернуть только SQL-запрос.
5. Не добавлять объяснений.  

Верни ответ строго в формате JSON:

{
    "sql": "..."
}

Не добавляй пояснений.
"""


def get_human_message(
    query: str,
    tables: list[str],
    columns: dict,
    relations: list[str]
) -> str:

    tables_text = "\n".join(tables)

    columns_text = ""

    for table in tables:
        columns_text += f"\n[{table}]\n"

        for column, description in columns[table].items():
            columns_text += f"{column} - {description}\n"

    relations_text = "\n".join(relations)

    return f"""
Вопрос:
{query}

Доступные таблицы:
{tables_text}

Поля таблиц:
{columns_text}

Связи:
{relations_text}

Напиши SQL-запрос.
"""


def giga_answer(chat, system: str, human: str):
    """Возвращает ответ GigaChat"""
    system_message = SystemMessage(content=system)
    human_message = HumanMessage(content=human)
    return chat.invoke([system_message, human_message])



def main():
    load_dotenv()   # Загружает настройки из .env в переменные окружения
    sber_studio_api_key = os.getenv("SBER_STUDIO_API_KEY")
    
    selected_query = "Какие три актера снялись в наибольшем количестве фильмов на итальянском языке?"

    selected_tables = [
        "actor",
        "film",
        "film_actor",
        "language"
    ]
    
    all_tables_columns = read_from_json("metadata/columns_02.json")
    #pprint(all_tables_columns)
    #print(f"{len(all_tables_columns)=}")

    selected_tables_columns = get_columns(all_tables_columns, selected_tables)
    #pprint(selected_tables_columns)

    all_relations = read_from_json("metadata/relations_02.json")
    #pprint(all_relations)
    #print(f"{len(all_relations)=}")

    selected_tables_relations = get_relations(all_relations, selected_tables)
    #pprint(selected_tables_relations)

    # join_tables = build_table_graph(relations)
    # pprint(join_tables)

    system = get_system_message()
    human = get_human_message(
        query=selected_query,
        tables=selected_tables,
        columns=selected_tables_columns,
        relations=selected_tables_relations
    )
    #print(human)

    t2 = time.time()
    print(f"{t2=}: Перед запросом к GigaChat")
    chat = GigaChat(
        credentials=sber_studio_api_key,
        # Для работы с API нужны сертификаты НУЦ МинЦифры
        # Если нужно, проверуку сертификатов можно отключить с помощью параметра verify_ssl_certs
        verify_ssl_certs=False,
        temperature=0.2,        # 0.0 → строгий, детерминированный, 2.0 → креативный, «фантазирует»
        max_tokens=300           # ограничение длины ответа
    )

    response = giga_answer(chat, system, human)
    t3 = time.time()
    print(f"{t3}: После запроса к GigaChat")
    print("-" * 80)

    pprint(response)

    print("-" * 80)
    print(f"Вопрос: {selected_query}")

    try:
        result = json.loads(response.content)
        print("JSON валиден ✔")
        pprint(result)
    except json.JSONDecodeError as e:
        print(f"{e} ❌")

    print("-" * 80)
    print(f"Время import GigaChat: {t1 - t0:.2f} секунд")
    print(f"Время запроса к GigaChat: {t3 - t2:.2f} секунд")
    print(f"Время ИТОГО: {t3 - t0:.2f} секунд")


if __name__ == "__main__":
   main()