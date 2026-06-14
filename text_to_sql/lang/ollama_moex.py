import requests
import subprocess
from datetime import date, datetime, timedelta
from clickhouse_connect import get_client
import pprint


MODEL_1 = "gemma3:4b"
MODEL_2 = "llama3:latest"

ch_client = get_client(host='localhost', port=18123)
set_move = {'down', 'flat', 'up', }
dim_move_type = {"down": "снижение цен", "up": "рост цен", "flat": "нет явно выраженной тенденции роста или снижения"}


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


def request_ollama(*, prompt: str) -> str:
    """Подключение к ollama по API. Возвращает строку - ответ LLM"""
    URL = f"http://{get_windows_host()}:11434"

    try:
        r = requests.post(
            #f"{URL}/api/generate",     # Режим генерации: {URL}/api/generate
            f"{URL}/api/chat",          # Режим чата: {URL}/api/chat
            json={
                "model": MODEL_1,
                #"prompt": prompt,      # Режим генерации: {URL}/api/generate
                "messages": [           # Режим чата: {URL}/api/chat
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": prompt}
                ],
                "stream": False,        # stream: False: ждём пока модель полностью ответит, и получаем ОДИН готовый текст
                                        # “подумай и дай финальный ответ”
                                        # stream: True (потоковый режим): ответ приходит кусками (token-by-token)
                "keep_alive": "10m",    # Держать модель в памяти (RAM или VRAM- видеокарта) 10 минут
                "options": {
                    "temperature": 1,
                    "top_p": 0.95,
                    "top_k": 64,
                    #"seed": 42
                }
            },
            timeout=600                 # Сколько секунд ждем ответа сервера - максимум 150 секунд
                                        # Если превышен, вызывает requests.exceptions.Timeout
        )
        r.raise_for_status()            # Вызывает requests.exceptions.HTTPError, если ошибка (API вернул 404,500)
                                        # Превратить HTTP-ошибки в Python-исключения 
        #return r.json()["response"]
        #for line in r.iter_lines():    # Если stream: True (потоковый режим)
        #    if line:
        #        print(line.decode())

        data = r.json()
        if "message" in data:           # Режим чата: {URL}/api/chat
            return data["message"]["content"]
        elif "response" in data:        # Режим генерации: {URL}/api/generate
            return data["response"]
        else:
            raise ValueError(f"Неожиданный формат ответа: {data}")

    except requests.exceptions.ConnectionError:
        return "❌ Ollama не запущен"
    
    except requests.exceptions.Timeout:
        return "❌ Таймаут"
    
    except requests.exceptions.HTTPError:
        return f"❌ HTTP ошибка {r.response.status_code}"


def get_quotes(*
        ,ticker: str = 'SBER'
        ,start_date: date = date(2026, 1, 1)
        ,end_date: date = date(2026, 1, 31)
    ) -> list[dict]:
    """Получает из ClickHouse котировки p_ticker с p_start_date по p_end_date """

    str_start_date = start_date.strftime("%Y-%m-%d")
    str_end_date = end_date.strftime('%Y-%m-%d')

    quote_text = f"""
    SELECT
	    ticker   			-- Тикер - уникальный идентиикатор акции (например, 'SBER', 'ROSN')
	    ,date_id  			-- Дата котировки
	    ,open_price 		-- Цена открытия дня
	    ,low_price 			-- Минимальная цена дня
	    ,high_price 		-- Максимальная цена дня
	    ,close_price 		-- Цена закрытия дня
	    ,volume_count 		-- Объем торгов за день в штуках акций	
	    ,value_rub 			-- Объем торгов за день в рублях 
    FROM moex.stock_quotes
    WHERE 
	    ticker = '{ticker}'
	    AND date_id BETWEEN '{str_start_date}' AND '{str_end_date}'
    ORDER BY date_id
    """

    result = ch_client.query(quote_text).result_rows        # Список кортежей (один кортеж = одна строка)

    lst_prices = []
    for row in result:
        lst_prices.append(
            {
                "ticker":           row[0]
                ,"date_id":         row[1]
                ,"open_price":      row[2]
                ,"low_price":       row[3]
                ,"high_price":      row[4]
                ,"close_price":     row[5]
                ,"volume_count":    row[6]
                ,"value_rub":       row[7]
            }
        )

    return lst_prices


def get_quotes_dict(*
        ,ticker: str = 'SBER'
        ,start_date: date = date(2026, 1, 1)
        ,end_date: date = date(2026, 1, 31)
    ) -> dict[list]:
    """Получает из ClickHouse котировки p_ticker с p_start_date по p_end_date. Возвращает словарь списков"""

    str_start_date = start_date.strftime("%Y-%m-%d")
    str_end_date = end_date.strftime('%Y-%m-%d')

    quote_text = f"""
    SELECT
	    ticker   			-- Тикер - уникальный идентиикатор акции (например, 'SBER', 'ROSN')
	    ,date_id  			-- Дата котировки
	    ,open_price 		-- Цена открытия дня
	    ,low_price 			-- Минимальная цена дня
	    ,high_price 		-- Максимальная цена дня
	    ,close_price 		-- Цена закрытия дня
	    ,volume_count 		-- Объем торгов за день в штуках акций	
	    ,value_rub 			-- Объем торгов за день в рублях 
    FROM moex.stock_quotes
    WHERE 
	    ticker = '{ticker}'
	    AND date_id BETWEEN '{str_start_date}' AND '{str_end_date}'
    ORDER BY date_id
    """

    result = ch_client.query(quote_text).result_rows        # Список кортежей (один кортеж = одна строка)

    lst_date_id         = [row[1] for row in result]
    lst_open_price      = [row[2] for row in result]
    lst_low_price       = [row[3] for row in result]
    lst_high_price      = [row[4] for row in result]
    lst_close_price     = [row[5] for row in result]
    lst_volume_count    = [row[6] for row in result]
    lst_value_rub       = [row[7] for row in result]

    return {
                "ticker":           ticker
                ,"date_id":         lst_date_id
                ,"open_price":      lst_open_price
                ,"low_price":       lst_low_price
                ,"high_price":      lst_high_price
                ,"close_price":     lst_close_price
                ,"volume_count":    lst_volume_count
                ,"value_rub":       lst_value_rub
    }


def select_interval(*
        ,ticker: str = 'SBER'
        ,start_date: date = date(2026, 1, 1)
        ,end_date: date = date(2026, 1, 18)
        ,prices: list[dict] = [{}]
    ) -> list[dict]:
    """Получает полный список котировок. Возвращает список котировок за указанный интервал."""

    result = []
    for row in prices:
        if row["ticker"] == ticker and row["date_id"] >= start_date and row["date_id"] <= end_date:
            result.append(row)

    return result


def aggregate_quotes(prices: list[dict]) -> tuple:
    """Получает список котировок по датам. Возвращает кортеж агрегированных данные по котировкам за период."""

    cnt = len(prices)
    if cnt == 0:
        return tuple()
    
    start_price = sorted( prices, key=lambda x: x["date_id"] )[0]["open_price"]
    end_price = sorted( prices, key=lambda x: x["date_id"], reverse=True )[0]["close_price"]
    max_price = max( x["high_price"] for x in prices )
    min_price = min( x["low_price"] for x in prices )
    avg_close = sum( x["close_price"] for x in prices ) / cnt
    avg_range = sum( abs( x["close_price"] - x["open_price"] ) for x in prices ) / cnt
    range_ratio = avg_range / avg_close

    return (start_price, end_price, max_price, min_price, avg_close, avg_range, range_ratio)


def recognize_move(*, aggr: tuple) -> str:
    """Получает агрегированные данные по котировкам за период. Возвращает тип движения: тренд вверх, тренд вниз или флэт."""

    prompt = f"""
    Ты – опытный трейдер акций на бирже.
    Ты видишь такие параметры движения цены акции за интервал.
    Цена в начале интервала – {str(aggr[0]).replace('.', ',')}.
    Цена в конце интервала – {str(aggr[1]).replace('.', ',')}.
    Максимальная цена за интервал – {str(aggr[2]).replace('.', ',')}.
    Минимальная цена за интервал – {str(aggr[3]).replace('.', ',')}.
    Среднеарифметическое цен закрытия дня за интервал – {str(aggr[4]).replace('.', ',')}.
    Среднеарифметическое размаха цены дня за интервал – {str(aggr[5]).replace('.', ',')}. 
    Размах цены дня – абсолютное значение разности цены открытия и цены закрытия дня. 
    Этот показатель всегда положительный для каждого дня.
    Твоя задача – оценить характер движения цены. 
    Ответ не должен быть основан только на одном показателе, например, только на разности цены на начало и цены на конец. 
    Нужно учесть все исходные данные. Отдельные показатели могут приводить к противоположным выводам. 
    Тогда нужно оценить силу каждого показателя и сделать итоговый вывод о наиболее сильной тенденции. 
    Отвечай одним словом – up, down или flat:
    up, если сильнее тенденция роста цены;
    down, если сильнее тенденция снижения цены;
    flat, если нет явно выраженной тенденции роста и снижения.  
    """
    #print(prompt)

    result = request_ollama(prompt=prompt)
    result = ''.join(c for c in result if c.isprintable())    # Удаляет все непечатные символы
    #print(f"Ответ модели - {result}")
    #print(set_move)

    if result in set_move:
        return result

    return 'none'


def compare_intervals(mv1: str, mv2: str) -> str:
    """Получает типы движения двух интервалов. Возвращает результат сравнения."""

    if mv1 in set_move and mv2 in set_move:
        return f"{mv1}_{mv2}"

    return 'none' 


def find_date_of_change(*
        ,start_move_type: str
        ,end_move_type: str
        ,dict_prices :dict[list]
    ) -> str:
    """Возвращает дату разворота, если есть смена тенденции"""

    if start_move_type == end_move_type:
        return 'Нет смены тенденции'
    
    if start_move_type not in set_move:
        return f"Неверный формат - {start_move_type}"
    
    if end_move_type not in set_move:
        return f"Неверный формат - {end_move_type}"

    dates = [d.strftime('%d-%m-%Y') for d in dict_prices["date_id"]]

    prompt = f"""
    Ты – опытный трейдер акций на бирже.
    Ты видишь списки данных.
    Даты: {dates}
    Цены открытия дня: {dict_prices['open_price']}.
    Минимальная цена дня: {dict_prices['low_price']}.
    Максимальная цена дня: {dict_prices['high_price']}.
    Цены закрытия дня: {dict_prices['close_price']}.
    В начале этого интервала – {dim_move_type[start_move_type]}, в конце этого интервала – {dim_move_type[end_move_type]}.
    Твоя задача – определить дату, когда произошло изменение типа движения.
    Твои ответ должен быть только датой в формате YYYY-MM-DD, где 
    YYYY – год (четыре цифры);
    MM – месяц (2 цифры – 01, 02, 03, 04, 05, 06, 07, 08, 09, 10, 11, 12);
    DD – дата (2 цифры – 01, 02, 03, 04, 05, 06, 07, 08, 09, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31).

    """

    #print(prompt)

    result = request_ollama(prompt=prompt)
    result = ''.join(c for c in result if c.isprintable())    # Удаляет все непечатные символы
    #print(f"Ответ модели - {result}")
    
    return result



def main():
        
    #list_prices = get_quotes(ticker='SBER', start_date=date(2025, 9, 1), end_date=date(2025, 9, 30))       # down
    #list_prices = get_quotes(ticker='SBER', start_date=date(2025, 12, 23), end_date=date(2026, 1, 12))     # flat
    #list_prices = get_quotes(ticker='SBER', start_date=date(2026, 1, 14), end_date=date(2026, 1, 24))       # up
    #list_prices = get_quotes(ticker='SBER', start_date=date(2026, 2, 1), end_date=date(2026, 2, 11))
    #print(list_prices)

    #dict_prices = get_quotes_dict(ticker='SBER', start_date=date(2026, 2, 1), end_date=date(2026, 2, 11))
    #pprint.pprint(dict_prices)
    #print(dict_prices)
    #print([d.strftime('%d-%m-%Y') for d in dict_prices["date_id"]])

    #first_part = select_interval(ticker='SBER', start_date=date(2026, 1, 1), end_date=date(2026, 1, 18), prices=list_prices)
    #second_part = select_interval(ticker='SBER', start_date=date(2026, 1, 19), end_date=date(2026, 1, 21), prices=list_prices)
    #aggr = aggregate_quotes(list_prices)
    #aggr1 = aggregate_quotes(first_part)
    #aggr2 = aggregate_quotes(second_part)
    #compare_move = compare_intervals('up', 'down')
    #price_trend = recognize_move(aggr=aggr)

    #print(aggr)
    #print(f"Итоговый ответ - {price_trend}")
    #print(compare_move)

    #str_date_reversal = find_date_of_change(start_move_type='down', end_move_type='up', dict_prices=dict_prices)
    #print(str_date_reversal)

    # ---- Разворот с падения на рост ----------------------------------------------------------------
    # dt_1 = date(2026, 2, 1)
    # dt_2 = date(2026, 2, 16)
    # dt_mid = dt_1 + timedelta(days=(dt_2 - dt_1).days // 2)
    # list_prices = get_quotes(ticker='SBER', start_date=dt_1, end_date=dt_2)
    # first_part = select_interval(ticker='SBER', start_date=dt_1, end_date=dt_mid, prices=list_prices)
    # second_part = select_interval(ticker='SBER', start_date=dt_mid, end_date=dt_2, prices=list_prices)
    # aggr_first = aggregate_quotes(first_part)
    # print(aggr_first)
    # aggr_second = aggregate_quotes(second_part)
    # print(aggr_second)
    # price_trend_first = recognize_move(aggr=aggr_first)
    # print(price_trend_first)
    # price_trend_second = recognize_move(aggr=aggr_second)
    # print(price_trend_second)
    # dict_prices = get_quotes_dict(ticker='SBER', start_date=dt_1, end_date=dt_2)
    # str_date_reversal = find_date_of_change(
    #         start_move_type=price_trend_first, 
    #         end_move_type=price_trend_second, 
    #         dict_prices=dict_prices
    #     )
    # print(str_date_reversal)
    # ---- Разворот с падения на рост ----------------------------------------------------------------

    # ---- Разворот с роста на падение ----------------------------------------------------------------
    dt_1 = date(2026, 2, 18)
    dt_2 = date(2026, 3, 4)
    dt_mid = dt_1 + timedelta(days=(dt_2 - dt_1).days // 2)
    list_prices = get_quotes(ticker='SBER', start_date=dt_1, end_date=dt_2)
    first_part = select_interval(ticker='SBER', start_date=dt_1, end_date=dt_mid, prices=list_prices)
    second_part = select_interval(ticker='SBER', start_date=dt_mid, end_date=dt_2, prices=list_prices)
    aggr_first = aggregate_quotes(first_part)
    print(aggr_first)
    aggr_second = aggregate_quotes(second_part)
    print(aggr_second)
    price_trend_first = recognize_move(aggr=aggr_first)
    print(price_trend_first)
    price_trend_second = recognize_move(aggr=aggr_second)
    print(price_trend_second)
    dict_prices = get_quotes_dict(ticker='SBER', start_date=dt_1, end_date=dt_2)
    str_date_reversal = find_date_of_change(
            start_move_type=price_trend_first, 
            end_move_type=price_trend_second, 
            dict_prices=dict_prices
        )
    print(str_date_reversal)
    # ---- Разворот с роста на падение ----------------------------------------------------------------


    # dt = datetime(2026, 1, 1, 0, 0, 0)
    # new_d = dt + timedelta(days=1, hours=2, minutes=30)
    # print(new_d)



if __name__ == "__main__":
    main()