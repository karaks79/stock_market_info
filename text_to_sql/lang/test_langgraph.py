from langgraph.graph import StateGraph, START, END
# StateGraph - класс, который позволяет строить цепочки шагов, ветвления, циклы, агентные системы
# START - это точка входа в граф
# END - это конец выполнения графа

from typing_extensions import TypedDict
# TypedDict - способ описать структуру словаря (dict) с типами полей. 
# В программе работает обычный словарь dict(). TypedDict говорит - какого типа данных должны быть значения ключей.
# TypedDict нужен для:
# - статической проверки типов
# - подсказок IDE
# - структурирования данных
# Но без изменения runtime поведения (поведения обычного словаря)


class State(TypedDict):
    text: str
# TypeDict - это контракт для State.
# TypedDict - это специализированный механизм для описания структуры словаря, а не класс для объектов
# State не создает объект.State(text="hello")-это не работает как обычный класс, потому что State - это не класс для инстансов.
# class State(TypedDict)
#    text: str   == Любой dict(), у которого есть ключ text типа str

# Зачем нужен class State(TypedDict), если уже есть TypedDict?
# Можно, но это будет неудобно и нерасширяемо.
# Вариант без класса: State = TypedDict("State", {"text": str})
# Это рабочий вариант, но плохо читается, неудобно расширять, хуже поддержка IDE.

# class State(TypedDict):
#     text: str 
# и 
# State = TypedDict("State", {"text": str})
#  - это одно и то же.

def step(state: State):
    return {"text": state["text"] + " OK"}
# Функция step принимает параметр state типа State. 
# Возвращает словарь с ключем "text" и знаением state["text"] + " OK". 
# state["text"] + " OK" - это конкатенация (сцепка) двух строк - значение словаря state по ключу "text" и строки " OK".
# {"text": "..."} - это НЕ изменение старого словаря. Это новый словарь.

# return {"text": ...} в LangGraph означает: обнови state новым значением
# Очень простая модель LangGraph: старый state -> node -> новый state
# Было: {"text": "Hello"}. Функция step делает: + " OK". Стало: {"text": "Hello OK"} 

graph = StateGraph(State)
# Создай пустой граф, который будет работать с данным State
# StateGraph - это конструктор графа
# State - это не значение, а описание структуры данных, которую граф будет использовать:
# Все шаги графа будут работать с dict, у которого есть ключ "text", значение которого имеет тип str
# graph = StateGraph(State) - создание объекта графа (пустого графа).
# graph - это программа, которая гоняет по щагам дагнные формата State
# graph = StateGraph(State) - "я создаю будущий процесс обработки данных типа State".

graph.add_node("step", step)
# Добавь в граф шаг (node) с именем "step", который выполняет функцию step.
# Фуркция step - получает state, делает работу, возвращает новый state.
# Имя ("step") нужно, чтобы потом связывать узлы графа (по именам)

graph.add_edge(START, "step")
# После старта программы первым далом выполни node "step"
graph.add_edge("step", END)
# После выполнения "step" заверши программу
# Теперь есть граф: START -> step -> END

app = graph.compile()
# Возьми описание графа и преврати его в исполняемую программу
# graph - план, compile - запуск завода.

print( app.invoke( {"text": "TEST"} ) )
# Запусти граф и передай ему входные данные (state = {"text": "TEST"} )
# invoke() - один полный прогон графа
# Начальное значение state задается в функкции invoke: {"text": "TEST"} = initial state
# Если не передать state: app.invoke(), то будет ошибка: графу не с чем работать.

# Обычно делают так:
# initial_state = {"text": ""}
# app.invoke(initial_state)

# invoke() создает локальный execution context. Внутри него живет state.
# state живёт не в коде, а в движке выполнения графа
# При запуске app.invoke({"text": "TEST"}) LangGraph создаёт: execution_state = {"text": "TEST"}
# Передаёт в node: step(execution_state). node возвращает: {"text": "TEST OK"}
# LangGraph делает: execution_state = merge(old, new), где old = {"text": "TEST"}, new = {"text": "TEST OK"}
# Пример. Было: old = {"text": "TEST", "count": 1}. node вернул: new = {"text": "TEST OK"}. Стало: execution_state = {"text": "TEST OK", "count": 1}.
# node НЕ заменяет state. node возвращает “изменения”. merge применяет эти изменения.
# node → говорит "что поменять". LangGraph → сам применяет изменения.

# LangGraph делает: shallow merge (поверхностное обновление dict). А не: deep merge (глубокое объединение структуры).

# Функция для node обязан возвратить словарь?
# Короткий ответ: почти всегда ДА.
# node = функция, которая возвращает изменения state в виде dict
# Очень простая формула:
# def node(state):
#     return {"ключ": новое_значение}
# Важно: ты НЕ возвращаешь “новый state целиком”, ты возвращаешь “patch (изменение)”

# В LangGraph: tool ≈ функция, которую может вызвать агент (в том числе самописная на Python)