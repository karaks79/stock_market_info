import psycopg

with psycopg.connect(
    host="192.168.240.1", dbname="postgres", user="postgres", password="2211", port=5432
) as conn:
# чтобы не писать conn.close()
    query = """
    SELECT country_id, country, last_update 
    FROM public.country 
    ORDER BY country_id 
    LIMIT 5
    """

    cur = conn.cursor()
    cur.execute(query)
    rows = cur.fetchall()
    columns = [desc[0] for desc in cur.description]

    result = list(dict(zip(columns, row)) for row in rows)

    #print(rows)
    #print(cur.description)
    #print(type(cur.description))
    #print(cur.description[0])
    #print(type(cur.description[0]))
    #print(cur.description[0][0])
    #print(type(cur.description[0][0]))
    print(result)

    cur.close()
