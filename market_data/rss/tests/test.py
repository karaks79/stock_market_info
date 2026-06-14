# test.py

# import time
# import os

# print(f"Мой PID: {os.getpid()}")
# print("Работаю 30 секунд...")
# time.sleep(30)
# print("Завершен")

import json

# Создадим список новостей
news = [
    {
        'title': 'Python стал популярнее кофе', 
        'rating': 10
        },
    {
        'title': 'JSON-монстр атаковал дата-центр',
        'rating': 8
        }
]

# Попробуйте поменять 'a' на 'w' и запустить несколько раз
# with open('news.jsonl', 'a', encoding='utf-8') as f:
#     for item in news:
#         f.write(json.dumps(item, ensure_ascii=False) + '\n')

# А теперь прочитаем и посмотрим, что получилось
# with open('news.jsonl', 'r', encoding='utf-8') as f:
#     for line in f:
#         data = json.loads(line)
#         print(f"Новость: {data['title']}, рейтинг: {data['rating']}")

with open('news.jsonl', 'a', encoding='utf-8') as f:
    json.dump(news, f, ensure_ascii=False, indent=4)
    