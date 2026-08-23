import sqlite3
import uuid

def migrate():
    # Connect to the local SQLite DB
    conn = sqlite3.connect("agrosaas.db")
    cursor = conn.cursor()

    try:
        # Check if tenant_id already exists
        cursor.execute("PRAGMA table_info(modelos_fitossanitarios)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        if "tenant_id" not in column_names:
            print("Adicionando coluna tenant_id e recriando constraints...")
            
            # SQLite doesn't allow dropping unique constraints easily.
            # We need to recreate the table.
            
            # 1. Rename existing table
            cursor.execute("ALTER TABLE modelos_fitossanitarios RENAME TO modelos_fitossanitarios_old")
            
            # 2. Create new table with tenant_id and new constraint
            cursor.execute("""
            CREATE TABLE modelos_fitossanitarios (
                id CHAR(32) NOT NULL,
                tenant_id CHAR(32),
                cultura VARCHAR(100) NOT NULL,
                doenca VARCHAR(150) NOT NULL,
                regras_risco JSON NOT NULL,
                created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
                PRIMARY KEY (id),
                FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE,
                CONSTRAINT uq_modelos_fito_cultura_doenca UNIQUE (tenant_id, cultura, doenca)
            )
            """)
            
            # 3. Create indices
            cursor.execute("CREATE INDEX ix_modelos_fitossanitarios_cultura ON modelos_fitossanitarios (cultura)")
            cursor.execute("CREATE INDEX ix_modelos_fitossanitarios_tenant_id ON modelos_fitossanitarios (tenant_id)")
            
            # 4. Copy data from old table to new table (tenant_id will be NULL)
            cursor.execute("""
            INSERT INTO modelos_fitossanitarios (id, cultura, doenca, regras_risco, created_at)
            SELECT id, cultura, doenca, regras_risco, created_at FROM modelos_fitossanitarios_old
            """)
            
            # 5. Drop old table
            cursor.execute("DROP TABLE modelos_fitossanitarios_old")
            
            conn.commit()
            print("Migração concluída com sucesso!")
        else:
            print("Coluna tenant_id já existe na tabela modelos_fitossanitarios.")
            
    except Exception as e:
        conn.rollback()
        print(f"Erro durante a migração: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
