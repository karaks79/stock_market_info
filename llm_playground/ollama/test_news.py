# test_news.py
import subprocess
import requests
import json
import time
from pathlib import Path

# Определяем папку, где лежит скрипт
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR / 'data'                  # папка data рядом со скриптом
DATA_FILE = DATA_DIR / 'news.jsonl'             # файл с json-и (каждый json в одной строке)
PROMPT_FILE = DATA_DIR / 'prompt_news_utf8.txt' # файл шаблона промпта новостей компаний

MODEL_1 = "gemma3:4b"
MODEL_2 = "llama3:latest"


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

def get_prompt_template(prompt_file):
    """
    Загружает шаблон промпта для новостей компаний
    """
    with open(PROMPT_FILE, 'r', encoding='utf-8') as f:
        return f.read()

def load_news(data_file):
    """
    Загружать новости из файла 
    """
    news_texts = []
    with open(data_file, 'r', encoding='utf-8') as f:
        for line in f:
            d = json.loads(line)["full_text"]
            news_texts.append(d)

    return news_texts


def request_ollama(prompt):
    """
    Подключение к ollama по API
    """
    URL = f"http://{get_windows_host()}:11434"

    try:
        r = requests.post(
            f"{URL}/api/generate",      # "сгенерируй текст"
            json={
                "model": MODEL_1,
                "prompt": prompt,
                "stream": False,        # stream: False: ждём пока модель полностью ответит, и получаем ОДИН готовый текст
                                        # “подумай и дай финальный ответ”
                                        # stream: True (потоковый режим): ответ приходит кусками (token-by-token)
                "keep_alive": "10m"     # Держать модель в памяти (RAM или VRAM- видеокарта) 10 минут
            },
            timeout=600                 # Сколько секунд ждем ответа сервера - максимум 150 секунд
                                        # Если превышен, вызывает requests.exceptions.Timeout
        )
        r.raise_for_status()            # Вызывает requests.exceptions.HTTPError, если ошибка (API вернул 404,500)
                                        # Превратить HTTP-ошибки в Python-исключения 
        return r.json()["response"]
        #for line in r.iter_lines():    # Если stream: True (потоковый режим)
        #    if line:
        #        print(line.decode())

    except requests.exceptions.ConnectionError:
        return "❌ Ollama не запущен"
    
    except requests.exceptions.Timeout:
        return "❌ Таймаут"
    
    except requests.exceptions.HTTPError:
        return f"❌ HTTP ошибка {r.response.status_code}"

#print(request_ollama("Какая сегодня дата?"))

#print(load_news(DATA_FILE))

#print(get_prompt_template(PROMPT_FILE))
  
def main():
    start = time.perf_counter()

    template = get_prompt_template(PROMPT_FILE)
    all_news = load_news(DATA_FILE)

    res_list = []
    for item in all_news:
        prompt = f"{template}\n\nНовость, которую нужно преолбразовать в JSON:\n{item}"
        res = request_ollama(prompt)
        
        # Если пустой ответ от Ollama
        # "❌ ..." — это мой формат ошибок в функции request_ollama(). Лучше заменить на другой способ.
        if not res or res.startswith("❌"):
            print(res)
            continue

        try:
            parsed = json.loads(res)    # Превратить строку в реальный Python-объект
        except json.JSONDecodeError:
            print("❌ Ошибка парсинга JSON:")
            print(res)
            continue

        # Иногда LLM делает: { ... } вместо: [ { ... } ]
        if not isinstance(parsed, list):
            parsed = [parsed]

        res_list.append(parsed)     # res_list - это список списков словарей
    
    print(res_list)

    for n in res_list:
        for m in n:
            print('\n' + '-'*50)
            # .get('company_name', '') - если модель пропустит поле 
            print(f"company_name: {m.get('company_name', '')}")
            print(f"metric: {m.get('metric', '')}")
            print(f"metric_value: {m.get('metric_value', '')}")
            print(f"unit_measurement: {m.get('unit_measurement', '')}")
            print(f"reason: {m.get('reason', '')}")
            print(f"sentiment: {m.get('sentiment', '')}")
            
    #return res_list

    end = time.perf_counter()
    print(f"Время выполнения - {end - start:.4f} секунд")

if __name__ == "__main__":
    main()

# Время работы для одной новости - 1 минута 50 секунд