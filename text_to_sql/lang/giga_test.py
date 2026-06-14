from langchain_gigachat.chat_models import GigaChat
#from langchain.schema import SystemMessage, HumanMessage        # Старая версия
from langchain_core.messages import SystemMessage, HumanMessage
from pprint import pprint

chat = GigaChat(
    credentials = "MDE5ZGUzZDgtZDM1Ny03Yjg5LTg0ZGUtZDRhYmZhMjNlYWYwOjg3YzAxMDVlLTgyNTUtNGZlZC1iMTE3LThiZDQyYjQzYzgwMQ==",
    # Для работы с API нужны сертификаты НУЦ МинЦифры
    # Если нужно, проверуку сертификатов можно отключить с помощью параметра verify_ssl_certs
    verify_ssl_certs=False,
    temperature=0.2,        # 0.0 → строгий, детерминированный, 2.0 → креативный, «фантазирует»
    max_tokens=100           # ограничение длины ответа
)

# # Имитация RAG-1 -----------------------------------------
# context = "Секретный код: 123456"
# question = "Какой секретный код?"

# prompt = f"""
# Контекст:
# {context}
# Вопрос: {question}
# """
# messages = [
#     HumanMessage(content=prompt)
# ]
# # Имитация RAG-1 -----------------------------------------


# Имитация RAG-2 -------------------------------------------
# 1. "База данных". docs — это твоя «векторная база», но вручную
docs = [
    "Компания X выросла на 10%",
    "Компания Y упала на 5%",
    "Компания Z выплатила дивиденды"
]

# 2. Простой поиск. simple_search — примитивный retriever (поиск наиболее близких векторов в векторглй базе данных)
def simple_search(query, docs):
    words = query.lower().split()
    result = []

    for doc in docs:
        for word in words:
            if word in doc:
                result.append(doc)
                break
    
    return result

# 3. Вопрос пользователя
query = "Кто выплатил дивиденды ?"

# 4. Ищем релевантные документы
found_docs = simple_search(query, docs)

# 5. Делаем контекст: то, что попадёт в LLM
context = "\n".join(found_docs)

# 6. Формируем prompt (путкая строка между Контекст и Вопрос - для того, чтобы модель легче отделила блоки промпта)
system = SystemMessage(content=f"""
Ты помощник для анализа текстов.
Отвечай кратко и только на основе контекста.
Если информации нет в контексте — скажи "нет данных".
""")

human = HumanMessage(content=f"""
Контекст:
{context}

Вопрос: {query}
""")
# Имитация RAG-2 -------------------------------------------

#response = chat(messages)          # Старая версия
response = chat.invoke([system, human])

pprint(response)
pprint(response.content)

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