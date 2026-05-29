import psycopg2, os
def get_conn():
    return psycopg2.connect(
        host="localhost",
        database="denialdata",
        user="postgres",
        password="newdb_practice"
    )



