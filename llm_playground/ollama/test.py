# test.py
import subprocess
import requests

MODEL_1 = "gemma3:4b"

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
            timeout=150                 # Сколько секунд ждем ответа сервера - максимум 150 секунд
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

print(request_ollama("Какая сегодня дата?"))

