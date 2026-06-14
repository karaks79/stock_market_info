import feedparser
import datetime
import json
from pathlib import Path
import trafilatura
import time
import requests

# Определяем папку, где лежит скрипт
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR / 'data'  # папка data рядом со скриптом

rss_urls = [
    'https://www.vedomosti.ru/rss/rubric/economics/macro',
    'https://www.vedomosti.ru/rss/rubric/business',
    'https://www.vedomosti.ru/rss/rubric/auto/auto_industry',
    'https://www.vedomosti.ru/rss/rubric/technology',
    
    'https://ria.ru/export/rss2/business/index.xml',
    'https://ria.ru/export/rss2/economy/index.xml',
    
    'https://www.banki.ru/xml/news.rss',
]

def fetch_article_text(url):
    """Загружает текст статьи"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        text = trafilatura.extract(response.text)
        return text if text else None
    except Exception as e:
        return None

def fetch_news(feed_url):
    """Парсит RSS и возвращает список новостей"""
    print(f"\n📡 {feed_url}")
    
    feed = feedparser.parse(feed_url)
    
    if not feed.entries:
        print(f"  ❌ Не удалось загрузить RSS")
        return []
    
    print(f"  Найдено новостей в RSS: {len(feed.entries)}")
    news_list = []
    
    for i, entry in enumerate(feed.entries[:5]):
        # Дата
        pub_date = entry.get('published_parsed')
        if pub_date:
            pub_date_iso = datetime.datetime(*pub_date[:6]).isoformat()
        else:
            pub_date_iso = datetime.datetime.now().isoformat()
        
        print(f"\n  {i+1}. {entry.title[:60]}...")
        full_text = fetch_article_text(entry.link)
        
        if full_text:
            print(f"     ✅ Текст: {len(full_text)} символов")
        else:
            print(f"     ❌ Текст не получен")
        
        news_item = {
            'source': feed.feed.title,
            'title': entry.title,
            'link': entry.link,
            'published': pub_date_iso,
            'full_text': full_text,
            'collected_at': datetime.datetime.now().isoformat()
        }
        news_list.append(news_item)
        
        time.sleep(1)
    
    return news_list

def main():
    all_news = []
    
    for url in rss_urls:
        news = fetch_news(url)
        all_news.extend(news)
    
    if all_news:
        # Создаем папку data рядом со скриптом
        DATA_DIR.mkdir(exist_ok=True)
        
        # Путь к файлу с новостями
        file_path = DATA_DIR / 'news.jsonl'
        
        # Сохраняем новости
        with open(file_path, 'a', encoding='utf-8') as f:
            for item in all_news:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
        
        successful = sum(1 for nw in all_news if nw['full_text'])
        print(f"\n{'='*50}")
        print(f"✅ Сохранено {len(all_news)} новостей")
        print(f"📝 С текстом: {successful} из {len(all_news)}")
        print(f"📁 Папка: {DATA_DIR}")
        print(f"📄 Файл: {file_path}")
        print(f"{'='*50}")

if __name__ == "__main__":
    main()