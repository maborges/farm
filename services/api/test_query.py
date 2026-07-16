import psycopg2

conn = psycopg2.connect("dbname=farm user=borgus")
cur = conn.cursor()

cur.execute("""
    SELECT DISTINCT up.id as up_id, up.tenant_id, pi.propriedade_id
    FROM unidades_produtivas up
    JOIN imoveis_rurais ir ON ir.unidade_produtiva_id = up.id
    JOIN propriedade_imovel pi ON pi.imovel_rural_id = ir.id
    LEFT JOIN cadastros_exploracoes_rurais er ON er.unidade_produtiva_id = up.id
    WHERE er.id IS NULL
""")
rows = cur.fetchall()
print("Orphans:", len(rows))
for r in rows:
    print(r)

