import feedparser
import datetime
import json
import time
import logging
from pathlib import Path
from typing import Optional
import trafilatura
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('news_collector.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Конфигурация
rss_urls = [
    'https://lenta.ru/rss/news',
    'https://www.kommersant.ru/RSS/news.xml',
]

REQUEST_TIMEOUT = 20
MAX_RETRIES = 3

def create_session_with_retries() -> requests.Session:
    """Создает сессию requests с автоматическими повторными попытками"""
    session = requests.Session()
    
    # Упрощенная настройка retry (без параметров, вызывающих ошибки)
    retry_strategy = Retry(
        total=MAX_RETRIES,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    return session

def fetch_article_text_with_retry(url: str) -> Optional[str]:
    """Загружает статью с повторными попытками и правильным User-Agent"""
    session = create_session_with_retries()
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
    }
    
    logger.info(f"Загрузка статьи: {url[:80]}...")
    
    try:
        response = session.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        
        # Проверяем Content-Type
        content_type = response.headers.get('Content-Type', '')
        if 'text/html' not in content_type:
            logger.warning(f"Не HTML ответ: {content_type}")
            return None
        
        # Пробуем извлечь текст через trafilatura
        extracted_text = trafilatura.extract(
            response.text,
            include_comments=False,
            include_tables=False,
            include_formatting=False,
            output_format='txt'
        )
        
        # Если trafilatura не дал результат, пробуем простой поиск <p> тегов
        if not extracted_text or len(extracted_text.strip()) < 200:
            logger.info("Trafilatura не дал текст, пробуем ручной парсинг...")
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Ищем все абзацы
            paragraphs = soup.find_all('p')
            text = '\n'.join(p.get_text() for p in paragraphs)
            
            if text and len(text.strip()) > 200:
                extracted_text = text.strip()
                logger.info(f"Ручной парсинг дал {len(extracted_text)} символов")
        
        if extracted_text and len(extracted_text.strip()) > 200:
            logger.info(f"✅ Успешно загружено: {len(extracted_text)} символов")
            return extracted_text.strip()
        else:
            logger.warning(f"⚠️ Текст слишком короткий: {len(extracted_text or '')} символов")
            return None
            
    except requests.exceptions.Timeout:
        logger.error(f"❌ Таймаут ({REQUEST_TIMEOUT}с): {url}")
        return None
    except requests.exceptions.ConnectionError as e:
        logger.error(f"❌ Ошибка соединения: {url[:80]}... - {e}")
        return None
    except requests.exceptions.HTTPError as e:
        logger.error(f"❌ HTTP ошибка {e.response.status_code}: {url[:80]}...")
        return None
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        return None
    finally:
        session.close()

def fetch_news(feed_url: str) -> list:
    """Парсит RSS-ленту и возвращает список новостей"""
    try:
        logger.info(f"Парсинг RSS: {feed_url}")
        feed = feedparser.parse(feed_url)
        
        if feed.bozo:
            logger.warning(f"Проблемы при парсинге RSS: {feed.bozo_exception}")
        
        news_list = []
        
        for idx, entry in enumerate(feed.entries[:10]):
            # Преобразуем дату
            pub_date = entry.get('published_parsed')
            if pub_date:
                pub_date_iso = datetime.datetime(*pub_date[:6]).isoformat()
            else:
                pub_date_iso = datetime.datetime.now().isoformat()
            
            article_url = entry.link
            
            logger.info(f"Обработка {idx+1}/10: {entry.title[:60]}...")
            
            # Загружаем полный текст
            full_text = fetch_article_text_with_retry(article_url)
            
            # Задержка между запросами
            if idx < len(feed.entries[:10]) - 1:
                time.sleep(1)
            
            news_item = {
                'source': feed.feed.title,
                'source_url': feed_url,
                'title': entry.title,
                'link': article_url,
                'published': pub_date_iso,
                'summary': entry.get('summary', ''),
                'full_text': full_text,
                'collected_at': datetime.datetime.now().isoformat()
            }
            news_list.append(news_item)
            
            if full_text:
                logger.info(f"  ✓ Текст получен ({len(full_text)} символов)")
            else:
                logger.warning(f"  ✗ Не удалось получить текст")
        
        return news_list
        
    except Exception as e:
        logger.error(f"Ошибка при парсинге {feed_url}: {e}")
        return []

def save_to_jsonl(news_items: list, filename: str = 'data/news.jsonl') -> None:
    """Сохраняет новости в JSON Lines файл"""
    Path(filename).parent.mkdir(parents=True, exist_ok=True)
    
    # Проверяем дубликаты
    existing_links = set()
    if Path(filename).exists():
        with open(filename, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    existing = json.loads(line.strip())
                    if existing.get('link'):
                        existing_links.add(existing['link'])
                except json.JSONDecodeError:
                    continue
    
    new_news = [item for item in news_items if item['link'] not in existing_links]
    
    if new_news:
        with open(filename, 'a', encoding='utf-8') as f:
            for item in new_news:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
        
        logger.info(f"✅ Сохранено {len(new_news)} новых новостей")
        
        # Сохраняем отдельно неудачные
        failed = [item for item in new_news if not item['full_text']]
        if failed:
            failed_file = Path(filename).parent / f"{Path(filename).stem}_failed.jsonl"
            with open(failed_file, 'w', encoding='utf-8') as f:
                for item in failed:
                    f.write(json.dumps(item, ensure_ascii=False) + '\n')
            logger.info(f"⚠️ {len(failed)} ссылок без текста сохранены в {failed_file}")
    else:
        logger.info("ℹ️ Новых новостей нет")

def main():
    """Основная функция"""
    start_time = time.time()
    logger.info("=" * 60)
    logger.info("🚀 Начинаем сбор новостей")
    logger.info("=" * 60)
    
    all_news = []
    
    for url in rss_urls:
        logger.info(f"\n📡 Загрузка RSS: {url}")
        news_batch = fetch_news(url)
        all_news.extend(news_batch)
        logger.info(f"Всего собрано новостей = {len(all_news)}")
        
        if url != rss_urls[-1]:
            time.sleep(2)
    
    if all_news:
        save_to_jsonl(all_news)
        
        elapsed = time.time() - start_time
        successful = sum(1 for n in all_news if n['full_text'])
        
        logger.info("\n" + "=" * 60)
        logger.info(f"📊 Статистика:")
        logger.info(f"   Всего: {len(all_news)}")
        logger.info(f"   С текстом: {successful} ({successful/len(all_news)*100:.1f}%)")
        logger.info(f"   Время: {elapsed:.2f} сек")
        logger.info("=" * 60)
        
        # Показываем примеры
        logger.info("\n📰 Примеры новостей (первые 3):")
        for i, news in enumerate(all_news[:3], 1):
            logger.info(f"\n{i}. {news['title']}")
            logger.info(f"   Источник: {news['source']}")
            logger.info(f"   Ссылка: {news['link']}")
            if news['full_text']:
                preview = news['full_text'][:200].replace('\n', ' ')
                logger.info(f"   Текст: {preview}...")
            else:
                logger.warning("   [Текст не получен]")
    else:
        logger.error("❌ Не удалось собрать новости")

if __name__ == "__main__":
    main()