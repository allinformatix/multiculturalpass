import os
import psycopg2
from psycopg2 import sql
password=os.environ['DB_PASSWORD']
connection=psycopg2.connect(dbname='postgres',user='postgres',host='127.0.0.1',password=os.environ['PG_ADMIN_PASSWORD'])
connection.autocommit=True
with connection.cursor() as cur:
    cur.execute("SELECT 1 FROM pg_roles WHERE rolname='odoo'")
    if not cur.fetchone():
        cur.execute(sql.SQL('CREATE ROLE odoo LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD {}').format(sql.Literal(password)))
    else:
        cur.execute(sql.SQL('ALTER ROLE odoo PASSWORD {}').format(sql.Literal(password)))
    cur.execute('SELECT 1 FROM pg_database WHERE datname=%s',(os.environ['DATABASE'],))
    if not cur.fetchone():
        cur.execute(sql.SQL('CREATE DATABASE {} OWNER odoo TEMPLATE template0 ENCODING %s').format(sql.Identifier(os.environ['DATABASE'])),('UTF8',))
