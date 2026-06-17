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



def read_tables_from_json(json_file_name: str) -> dict[str, str]:
    """Загрузить описания таблиц из JSON-файла.""" 
    with open(json_file_name, encoding="utf-8") as f:
        return json.load(f)


def read_queries_from_json(json_file_name: str) -> dict[str, str]:
    """Загрузить вопросы из JSON-файла.""" 
    with open(json_file_name, encoding="utf-8") as f:
        return json.load(f)
    

def get_system_message() -> str:
    """Возвращает системный prompt"""
    return """
Ты помощник для SQL.

Задача: оценить, какие таблицы нужны для построения SQL-запроса для ответа на вопрос.

Таблица важна, если она содержит:
- сущности из вопроса;
- или связи между ними;
- или данные, необходимые для фильтрации/агрегации.

Оцени каждую таблицу десятичным числом от 0 до 1, где:
    0 = таблица совсем не нужна для запроса;
    1 = без таблицы невозможно построить SQL-запрос для ответа.        
"""


def get_human_message(query: str, tables: dict[str, str]) -> str:
    """Возвращает пользовательский prompt"""

    tables_text = "\n".join(
        f"    {k} - {v}" for k, v in tables.items()
    )

    output_format = ",\n".join(
        f'    "{k}": 0.0000' for k in tables.keys()
    )
    output_format = "{\n" + output_format + "\n}"

    return f"""
Вопрос:
{query}

Таблицы:
{tables_text}

Формат ответа - строго JSON:
{output_format}

Включай только таблицы с оценкой больше 0.0000.

Запрещено:
- любые комментарии;
- любые объяснения;
- любой текст кроме JSON;
- включать в JSON таблицы с оценкой 0.0000.
"""


def giga_answer(chat, system: str, human: str):
    """Возвращает ответ GigaChat"""
    system_message = SystemMessage(content=system)
    human_message = HumanMessage(content=human)
    return chat.invoke([system_message, human_message])


# AIMessage(
#         # --------- GigaChat ------------------------------------------------------------------
#         content='Компания Z выплатила дивиденды.', 
#         additional_kwargs={}, 
#         response_metadata={
#             'token_usage': {                      # GigaChat
#                 'prompt_tokens': 62,              # Токенов промпта
#                 'completion_tokens': 8,           # Токенов ответа
#                 'total_tokens': 70,               # Токенов итого
#                 'precached_prompt_tokens': 2
#             }, 
#             'model_name': 'GigaChat:2.0.28.2',    # Модель GigaChat
#             'x_headers': {                        # серверная кухня GigaChat
#                 'x-request-id': '35d1d53d-e2c4-4d37-a930-174c241ee92d', 
#                 'x-session-id': '1dbdf475-99b6-41c2-83c2-8a8d32c92fc0', 
#                 'x-client-id': None
#             }, 
#             'finish_reason': 'stop'               # stop → нормально завершила ответ, length → упёрлась в лимит токенов, tool_calls → вызвала инструмент
#         }, 
#         # ---------- LangChain ------------------------------------------------------------------
#         id='35d1d53d-e2c4-4d37-a930-174c241ee92d',    # идентификатор сообщения в LangChain
#         tool_calls=[],                            # Какие инструменты вызывала модель
#         invalid_tool_calls=[], 
#         usage_metadata={                          # уже нормализованная версия token_usage LangChain
#             'output_tokens': 8, 
#             'input_tokens': 62, 
#             'total_tokens': 70, 
#             'input_token_details': {'cache_read': 2}
#         }
#     )


def main():
    load_dotenv()
    sber_studio_api_key = os.getenv("SBER_STUDIO_API_KEY")

    query_number = "9"

    tables = read_tables_from_json("metadata/tables_02.json")
    #pprint(tables)
    queries = read_queries_from_json("metadata/queries_01.json")
    #pprint(tables)

    system = get_system_message()
    human = get_human_message(query=queries[query_number], tables=tables)
    #pprint(human)

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
    #pprint(response.content)

    #print(f"{type(chat)=}")

    print("-" * 80)
    print(f"Вопрос: {query_number}.{queries[query_number]}")

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

    