from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict, List
from clickhouse_connect import get_client
import requests
import subprocess
from datetime import datetime

class PricePoint(TypedDict):
    date_id: str
    price: float

class State(TypedDict):
    ticker: str
    #price: float
    price_list: List[PricePoint]
    analysis: str


client = get_client(host='localhost', port=18123)

MODEL_1 = "gemma3:4b"
MODEL_2 = "llama3:latest"
MODEL_3 = "phi3:3.8b"

def get_windows_host():
    """
    Возвращает IP-адрес Windows - как его видит WSL
    Это нужно, потому что ollama установлен на Windows, а localhost для Windows и WSL - не совпадает
    """
    result = subprocess.check_output("ip route", shell=True).decode()
    for line in result.splitlines():
        if "default" in line:
            #print(line.split()[2])
            return line.split()[2]
        

def get_price(state: State):
#def get_price_debug():
    print(datetime.now())
    ticker = state["ticker"]
    #ticker = 'SBER'

    # query = f"""
    # SELECT close_price
    # FROM moex.stock_quotes
    # WHERE ticker = '{ticker}'
    # ORDER BY date_id DESC
    # LIMIT 1  
    # """
    query = f"""
    SELECT date_id, close_price
    FROM moex.stock_quotes
    WHERE ticker = '{ticker}'
    ORDER BY date_id  DESC
    LIMIT 2 
    """

    result = client.query(query)

    #price = result.result_rows[0][0]
    #return {"price": price}

    prices = result.result_rows     # Список кортежей (кортеж - одна строка)
    lst = []
    for dt, pr in prices:
        dct = {}
        dct["date_id"] = dt.strftime("%d.%m.%Y")
        dct["price"] = pr
        lst.append(dct)

    print(lst)
    return {"price_list": lst}

#get_price_debug()


def analysis(state: State):
    URL = f"http://{get_windows_host()}:11434"
    
    prompt = f"""
    Ты финансовый аналитик.

    Используй ТОЛЬКО данные ниже.
    НЕ придумывай дополнительные значения.

    Тикер: {state['ticker']}
    На {state['price_list'][0]["date_id"]} цена: {state['price_list'][0]["price"]}
    На {state['price_list'][1]["date_id"]} цена: {state['price_list'][1]["price"]}

    Формат ответа:
    - 2-3 предложения
    - без вымышленных причин роста/падения
    - как изменилась цена акции, на сколько процентов
    - на русском языке 
    """

    response = requests.post(
        f"{URL}/api/generate",
        json={
            "model": MODEL_1,
            "prompt": prompt,
            "stream": False
        } 
    )   

    text = response.json()["response"]

    print(datetime.now())

    return {"analysis": text}


graph = StateGraph(State)

graph.add_node("get_price", get_price)
graph.add_node("analysis", analysis)

graph.add_edge(START, "get_price")
graph.add_edge("get_price", "analysis")
graph.add_edge("analysis", END)

app = graph.compile()

result = app.invoke({"ticker": "SBER"})

print(result)