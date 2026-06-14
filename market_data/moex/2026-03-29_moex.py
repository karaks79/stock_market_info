# 2026-03-29_moex.py
import requests
import json
import pprint
import datetime
import clickhouse_connect

#TICKER = 'SBER'
#TICKER = 'GAZP'
#TICKER = 'NVTK'
#TICKER = 'YDEX'
#TICKER = 'X5'
#TICKER = 'GMKN'
#TICKER = 'ROSN'
#TICKER = 'PLZL'
#TICKER = 'T'
#TICKER = 'VTBR'
#TICKER = 'PHOR'
#TICKER = 'MGNT'
START_DATE = datetime.datetime.strptime('2026-03-29', '%Y-%m-%d')
END_DATE = datetime.datetime.strptime('2026-04-30', '%Y-%m-%d')

def get_daily_quotes(p_ticker, p_start_date, p_end_date):
    
    URL = f"https://iss.moex.com/iss/engines/stock/markets/shares/securities/{p_ticker}/candles.json"
    params = {
        'from': p_start_date,
        'till': p_end_date,
        'interval': 24
    }
    print("before request")
    r = requests.get(URL, params=params, timeout=10)
    print("before request")
    js = r.json()

    columns = js['candles']['columns']
    data = js.get('candles', {}).get('data', [])
    
    result = []

    for row  in data:
        row_dict = dict(zip(columns, row))

        #print(f"begin: {row_dict['begin']}")
        #print(f"end: {row_dict['end']}")
        #print("type(row['end'])", type(row_dict['end']))
        #print(f"date: {datetime.datetime.strptime(row_dict['begin'], '%Y-%m-%d %H:%M:%S').date()}")
        #print("type(date)", type(datetime.datetime.strptime(row_dict['begin'], '%Y-%m-%d %H:%M:%S').date()))
        #print(f"open: {row_dict['open']}")
        #print(f"close: {row_dict['close']}")
        #print(f"high: {row_dict['high']}")
        #print(f"low: {row_dict['low']}")
        #print(f"value: {row_dict['value']}")
        #print(f"volume: {row_dict['volume']}")

        record = (
            p_ticker,
            datetime.datetime.strptime(row_dict['begin'], '%Y-%m-%d %H:%M:%S').date(),
            row_dict['open'],
            row_dict['low'],
            row_dict['high'],
            row_dict['close'],
            row_dict['volume'],
            row_dict['value']
        )
        result.append(record)

    return result

def insert_to_clickhouse(p_rows):
    client = clickhouse_connect.get_client(
        host='localhost',
        port=18123,
        database='moex',
        username='default',
        password=''
    )

    client.insert(
        'stock_quotes',         # Имя таблицы
        p_rows,
        column_names=[
            'ticker',
            'date_id',
            'open_price',
            'low_price',
            'high_price',
            'close_price',
            'volume_count',
            'value_rub'
        ]
    )

def main():

    try:
        rows = get_daily_quotes(TICKER, START_DATE, END_DATE)
        print("before insert")
        insert_to_clickhouse(rows)
        print("after insert")
        print(f"Успех - {TICKER}")
    except:
        print("Ошибка")

if __name__ == '__main__':
    main()