import pickle
import numpy as np
from pprint import pprint

TABLE_VERSION = "02"
QUERY_VERSION = "01"
TOP_N = 20


def read_from_pickle(pickle_file_name: str) -> object:
    """Читать (десериаоизовать) pickle-файл в Python-объект"""
    with open(pickle_file_name, "rb") as f:
        return pickle.load(f)
    

def cosine_similarity(vec1, vec2) -> float:
    """
    Косинусное сходство между векторами. 
    similarity = 1 - означает "очень похожи".
    """
    return np.dot(vec1, vec2) / (
        np.linalg.norm(vec1) * np.linalg.norm(vec2)
    )


def semantic_search(table_index: dict, query_index: dict) -> None:
    """Семантический поиск"""
    
    print("-" * 80)

    for query_id, query_info in query_index.items():
        
        print(f'[{query_id}] {query_info["query"]}')
        vec_query = query_info["vector"]

        table_scores = []
        for table_name, table_info in table_index.items():
            vec_table = table_info["vector"]
            score = cosine_similarity(vec_query, vec_table) 
            table_scores.append((table_name, score, table_info["description"]))
        
        table_scores.sort(key=lambda x: x[1], reverse=True)
        
        for table_name, cos, desc in table_scores[:TOP_N]:
            print(f"{table_name:15}: {cos:.4f} ({desc})")

        print("-" * 80)
            


if __name__ == "__main__":
    table_index = read_from_pickle(f"index/table_embeddings_{TABLE_VERSION}.pkl")
    query_index = read_from_pickle(f"index/query_embeddings_{QUERY_VERSION}.pkl")
    semantic_search(table_index, query_index)