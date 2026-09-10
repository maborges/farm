DO $$
DECLARE
  actual_count bigint;
  table_name text;
  expected_count bigint;
BEGIN
  SELECT count(*) INTO actual_count
  FROM pg_constraint c
  JOIN pg_class t ON t.oid = c.conrelid
  JOIN pg_namespace n ON n.oid = t.relnamespace
  WHERE n.nspname = 'farms' AND c.contype = 'f';
  IF actual_count <> 892 THEN
    RAISE EXCEPTION 'FK count mismatch: expected 892, got %', actual_count;
  END IF;

  SELECT count(*) INTO actual_count
  FROM pg_constraint c
  JOIN pg_class t ON t.oid = c.conrelid
  JOIN pg_namespace n ON n.oid = t.relnamespace
  WHERE n.nspname = 'farms'
    AND c.contype = 'f'
    AND c.conname IN (
      'alert_events_causation_id_fkey',
      'cadastros_areas_rurais_parent_id_fkey',
      'cadastros_categorias_produto_parent_id_fkey',
      'cadastros_produtos_produto_referencia_id_fkey',
      'caderno_campo_entradas_retifica_evento_id_fkey',
      'caderno_campo_entradas_retificado_por_evento_id_fkey',
      'categoria_custom_parent_id_fkey',
      'estoque_movimentos_ajuste_de_fkey',
      'fin_planos_conta_parent_id_fkey',
      'imoveis_documentos_substituido_por_fkey',
      'pec_animais_mae_id_fkey',
      'pec_animais_pai_id_fkey',
      'planos_operacionais_tarefas_insumos_substitui_item_id_fkey',
      'recommendation_results_superseded_by_id_fkey',
      'production_units_cultivo_area_id_fkey',
      'romaneios_colheita_qualidade_laudo_id_fkey',
      'operacoes_agricolas_tarefa_id_fkey'
    );
  IF actual_count <> 17 THEN
    RAISE EXCEPTION 'Recreated cycle FK count mismatch: expected 17, got %', actual_count;
  END IF;

  SELECT count(*) INTO actual_count
  FROM pg_constraint c
  JOIN pg_class t ON t.oid = c.conrelid
  JOIN pg_namespace n ON n.oid = t.relnamespace
  WHERE n.nspname = 'farms' AND c.contype = 'f' AND NOT c.convalidated;
  IF actual_count <> 0 THEN
    RAISE EXCEPTION 'Unvalidated FKs: %', actual_count;
  END IF;

  SELECT count(*) INTO actual_count FROM pg_policies WHERE schemaname = 'farms';
  IF actual_count <> 188 THEN
    RAISE EXCEPTION 'Policy count mismatch: expected 188, got %', actual_count;
  END IF;

  SELECT count(*) INTO actual_count
  FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
  WHERE n.nspname = 'farms' AND c.relkind = 'r' AND c.relrowsecurity;
  IF actual_count <> 49 THEN
    RAISE EXCEPTION 'RLS ENABLE count mismatch: expected 49, got %', actual_count;
  END IF;

  SELECT count(*) INTO actual_count
  FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
  WHERE n.nspname = 'farms' AND c.relkind = 'r' AND c.relforcerowsecurity;
  IF actual_count <> 48 THEN
    RAISE EXCEPTION 'RLS FORCE count mismatch: expected 48, got %', actual_count;
  END IF;

  FOR table_name, expected_count IN
    SELECT * FROM (VALUES
      ('tenants', 2), ('usuarios', 6), ('tenant_usuarios', 5),
      ('unidades_produtivas', 3), ('cadastros_propriedades', 3),
      ('imoveis_rurais', 3), ('safras', 3), ('cultivo_areas', 15),
      ('operacoes_agricolas', 54), ('estoque_movimentos', 173),
      ('compras_pedidos', 15), ('financeiro_lancamentos', 19),
      ('tenant_integracoes', 5), ('wizard_implantacoes_operacionais', 2)
    ) AS expected(table_name, expected_count)
  LOOP
    EXECUTE format('SELECT count(*) FROM farms.%I', table_name) INTO actual_count;
    IF actual_count <> expected_count THEN
      RAISE EXCEPTION 'Critical table % mismatch: expected %, got %',
        table_name, expected_count, actual_count;
    END IF;
  END LOOP;
END $$;

WITH expected(table_name, expected_count) AS (
  VALUES
    ('tenants', 2), ('usuarios', 6), ('tenant_usuarios', 5),
    ('unidades_produtivas', 3), ('cadastros_propriedades', 3),
    ('imoveis_rurais', 3), ('safras', 3), ('cultivo_areas', 15),
    ('operacoes_agricolas', 54), ('estoque_movimentos', 173),
    ('compras_pedidos', 15), ('financeiro_lancamentos', 19),
    ('tenant_integracoes', 5), ('wizard_implantacoes_operacionais', 2)
), actual AS (
  SELECT table_name, (xpath('/row/count/text()', query_to_xml(
    format('SELECT count(*) FROM farms.%I', table_name), true, false, ''
  )))[1]::text::bigint AS records
  FROM expected
)
SELECT e.table_name, e.expected_count, a.records,
       a.records - e.expected_count AS delta
FROM expected e JOIN actual a USING (table_name)
WHERE a.records <> e.expected_count;

DO $$
DECLARE
  actual_count bigint;
BEGIN
  SELECT count(*) INTO actual_count
  FROM farms.compras_pedidos
  WHERE deposito_id IS NULL;
  IF (SELECT count(*) FROM farms.compras_pedidos) <> 15 OR actual_count <> 15 THEN
    RAISE EXCEPTION 'compras_pedidos deposito_id validation failed: rows %, nulls %',
      (SELECT count(*) FROM farms.compras_pedidos), actual_count;
  END IF;
END $$;

SELECT 'fk_count' AS check_name, count(*) AS value
FROM pg_constraint c
JOIN pg_class t ON t.oid = c.conrelid
JOIN pg_namespace n ON n.oid = t.relnamespace
WHERE n.nspname = 'farms' AND c.contype = 'f'
UNION ALL
SELECT 'policies', count(*) FROM pg_policies WHERE schemaname = 'farms'
UNION ALL
SELECT 'rls_enable', count(*)
FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'farms' AND c.relkind = 'r' AND c.relrowsecurity
UNION ALL
SELECT 'rls_force', count(*)
FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'farms' AND c.relkind = 'r' AND c.relforcerowsecurity;
