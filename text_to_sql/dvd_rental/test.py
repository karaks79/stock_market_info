import json
from pprint import pprint


def read_from_json(file_name: str) -> dict:
    """Читать JSON в словарь"""
    with open(file_name, "r") as f:
        try:
            result = json.load(f)
            return result
        except json.JSONDecodeError as e:
            return {"error": f"{e}"}


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



if __name__ == "__main__":
    # columns = read_from_json("metadata/columns_02.json")
    # pprint(columns)
    # print(f"{len(columns)=}")

    relations = read_from_json("metadata/relations_02.json")
    print(f"{len(relations)=}")

    join_tables = build_table_graph(relations)
    pprint(join_tables)