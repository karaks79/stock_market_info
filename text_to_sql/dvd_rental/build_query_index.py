import time
import json
import pickle
from pprint import pprint

t0 = time.time()
print(f"{t0} - start")
from sentence_transformers import SentenceTransformer
t1 = time.time()

VERSION = "01"


def read_queries_from_json(json_file_name: str) -> dict[str, str]:
    """Загрузить вопросы из JSON-файла.""" 
    with open(json_file_name, encoding="utf-8") as f:
        return json.load(f)
    

def build_embeddings(model: object, queries: dict[str, str]) -> dict:
    """Посчитать embedding-вектор для описания каждой таблицы"""

    result = {}

    names = list(queries.keys())
    descriptions = list(queries.values()) 

    vectors = model.encode(descriptions, show_progress_bar=True)

    for name, desc, vec in zip(names, descriptions, vectors):
        result[name] = {
            "query": desc,
            "vector": vec
        }

    return result


def save_to_pickle(pickle_file_name: str, obj: object):
    """Сохранить (сериализовать) Python-объект obj в файл pickle (поток байтов)"""
    with open(pickle_file_name, "wb") as f:
        pickle.dump(obj, f)


def read_from_pickle(pickle_file_name: str) -> object:
    """Читать (десериализовать) в Python-объект из pickle-файла (поток байт)"""
    with open(pickle_file_name, "rb") as f:
        return pickle.load(f)


if __name__ == "__main__":
 
    t2 = time.time()
    print(f"{t2} - loading model")
    model_sentence = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    # Что происходит при первом запуске model = SentenceTransformer("...")
    # 1.Проверяет локальный кэш. 2.Если нет — скачивает модель. 
    # 3.Сохраняет в папку: ~/.cache/huggingface/. 4.Дальше использует локально
    # После того как модель скачалась один раз, она остаётся на диске (даже после выключения компьютера).
    # pip install sentence-transformers - это код для работы с моделями, а не сами модели. 
    t3 = time.time()
    print(f"{t3} - loaded!")
    print(f"Время загрузки import sentence_transformers - {t1 - t0:.2f} секунд")
    print(f"Время загрузки model_sentence = SentenceTransformer(...) - {t3 - t2:.2f} секунд")
    print(f"ИТОГО время загрузки - {t3 - t0:.2f} секунд")
    print("-" * 80)
    
    query_descriptions = read_queries_from_json(f"metadata/queries_{VERSION}.json")
    pprint(query_descriptions)
    #print(f"{type(query_descriptions)=}")
    #print(f"{len(query_descriptions)=}")
    index = build_embeddings(model_sentence, query_descriptions)
    save_to_pickle(f"index/query_embeddings_{VERSION}.pkl", index)
    #obj = read_from_pickle(f"index/query_embeddings_{VERSION}.pkl")
    #pprint(obj)

    
    

