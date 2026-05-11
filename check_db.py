import psycopg2

conn = psycopg2.connect('dbname=amis_db user=amis_user password=amis_pass host=localhost port=5432')
cur = conn.cursor()
cur.execute('SELECT inspection_id, machine_id, status, defect_class, severity_name, root_cause FROM inspections ORDER BY id DESC LIMIT 10;')
rows = cur.fetchall()
for row in rows:
    print(row)
cur.close()
conn.close()