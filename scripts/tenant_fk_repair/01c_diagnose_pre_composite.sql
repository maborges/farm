-- TENANT-FK-REPAIR-01C — Diagnóstico pré-composição
-- Somente leitura. Verifica que:
--   1. Não restam cruzamentos A→B (01A concluído)
--   2. Unicidade de (tenant_id, id) nos pais já existe ou pode ser criada
--   3. Filhos não têm linhas órfãs na chave composta
--
-- Todos os resultados devem ser 0 antes de aplicar as migrations 01C.

SET search_path = farms, public;

\echo '=== 1. Cruzamentos residuais A→B (deve ser 0 em tudo) ==='

SELECT 'cadastros_areas_rurais x unidades_produtivas' AS relacao,
       COUNT(*) AS cruzamentos
FROM farms.cadastros_areas_rurais car
JOIN farms.unidades_produtivas up ON up.id = car.unidade_produtiva_id
WHERE car.unidade_produtiva_id IS NOT NULL AND car.tenant_id <> up.tenant_id
UNION ALL
SELECT 'estoque_depositos x unidades_produtivas',
       COUNT(*)
FROM farms.estoque_depositos ed
JOIN farms.unidades_produtivas up ON up.id = ed.unidade_produtiva_id
WHERE ed.unidade_produtiva_id IS NOT NULL AND ed.tenant_id <> up.tenant_id
UNION ALL
SELECT 'cadastros_equipamentos x unidades_produtivas',
       COUNT(*)
FROM farms.cadastros_equipamentos ce
JOIN farms.unidades_produtivas up ON up.id = ce.unidade_produtiva_id
WHERE ce.unidade_produtiva_id IS NOT NULL AND ce.tenant_id <> up.tenant_id
UNION ALL
SELECT 'compras_pedidos x estoque_depositos',
       COUNT(*)
FROM farms.compras_pedidos cp
JOIN farms.estoque_depositos ed ON ed.id = cp.deposito_id
WHERE cp.deposito_id IS NOT NULL AND cp.tenant_id <> ed.tenant_id
UNION ALL
SELECT 'frota_jornadas_equipamento x unidades_produtivas',
       COUNT(*)
FROM farms.frota_jornadas_equipamento fje
JOIN farms.unidades_produtivas up ON up.id = fje.unidade_produtiva_id
WHERE fje.unidade_produtiva_id IS NOT NULL AND fje.tenant_id <> up.tenant_id
UNION ALL
SELECT 'frota_apontamentos_uso x frota_jornadas_equipamento',
       COUNT(*)
FROM farms.frota_apontamentos_uso fau
JOIN farms.frota_jornadas_equipamento fje ON fje.id = fau.jornada_id
WHERE fau.jornada_id IS NOT NULL AND fau.tenant_id <> fje.tenant_id
UNION ALL
SELECT 'frota_abastecimentos x cadastros_equipamentos',
       COUNT(*)
FROM farms.frota_abastecimentos fa
JOIN farms.cadastros_equipamentos ce ON ce.id = fa.equipamento_id
WHERE fa.equipamento_id IS NOT NULL AND fa.tenant_id <> ce.tenant_id
ORDER BY cruzamentos DESC;

\echo '=== 2. Duplicatas em (tenant_id, id) nos pais (deve ser 0) ==='
-- Bloqueia criação de UNIQUE — investigar antes

SELECT 'unidades_produtivas' AS tabela, COUNT(*) - COUNT(DISTINCT (tenant_id, id)) AS duplicatas
FROM farms.unidades_produtivas
UNION ALL
SELECT 'estoque_depositos', COUNT(*) - COUNT(DISTINCT (tenant_id, id))
FROM farms.estoque_depositos
UNION ALL
SELECT 'cadastros_equipamentos', COUNT(*) - COUNT(DISTINCT (tenant_id, id))
FROM farms.cadastros_equipamentos
UNION ALL
SELECT 'frota_jornadas_equipamento', COUNT(*) - COUNT(DISTINCT (tenant_id, id))
FROM farms.frota_jornadas_equipamento;

\echo '=== 3. Filhos sem par (tenant_id, parent_id) válido no pai ==='
-- Deve ser 0 após 01A. Se > 0, há orphans pela chave composta.

SELECT 'cadastros_areas_rurais → unidades_produtivas' AS relacao,
       COUNT(*) AS sem_par_composto
FROM farms.cadastros_areas_rurais car
WHERE car.unidade_produtiva_id IS NOT NULL
  AND NOT EXISTS (
      SELECT 1 FROM farms.unidades_produtivas up
      WHERE up.id = car.unidade_produtiva_id AND up.tenant_id = car.tenant_id
  )
UNION ALL
SELECT 'estoque_depositos → unidades_produtivas',
       COUNT(*)
FROM farms.estoque_depositos ed
WHERE ed.unidade_produtiva_id IS NOT NULL
  AND NOT EXISTS (
      SELECT 1 FROM farms.unidades_produtivas up
      WHERE up.id = ed.unidade_produtiva_id AND up.tenant_id = ed.tenant_id
  )
UNION ALL
SELECT 'cadastros_equipamentos → unidades_produtivas',
       COUNT(*)
FROM farms.cadastros_equipamentos ce
WHERE ce.unidade_produtiva_id IS NOT NULL
  AND NOT EXISTS (
      SELECT 1 FROM farms.unidades_produtivas up
      WHERE up.id = ce.unidade_produtiva_id AND up.tenant_id = ce.tenant_id
  )
UNION ALL
SELECT 'compras_pedidos → estoque_depositos',
       COUNT(*)
FROM farms.compras_pedidos cp
WHERE cp.deposito_id IS NOT NULL
  AND NOT EXISTS (
      SELECT 1 FROM farms.estoque_depositos ed
      WHERE ed.id = cp.deposito_id AND ed.tenant_id = cp.tenant_id
  )
UNION ALL
SELECT 'frota_jornadas_equipamento → unidades_produtivas',
       COUNT(*)
FROM farms.frota_jornadas_equipamento fje
WHERE fje.unidade_produtiva_id IS NOT NULL
  AND NOT EXISTS (
      SELECT 1 FROM farms.unidades_produtivas up
      WHERE up.id = fje.unidade_produtiva_id AND up.tenant_id = fje.tenant_id
  )
UNION ALL
SELECT 'frota_apontamentos_uso → frota_jornadas_equipamento',
       COUNT(*)
FROM farms.frota_apontamentos_uso fau
WHERE fau.jornada_id IS NOT NULL
  AND NOT EXISTS (
      SELECT 1 FROM farms.frota_jornadas_equipamento fje
      WHERE fje.id = fau.jornada_id AND fje.tenant_id = fau.tenant_id
  )
UNION ALL
SELECT 'frota_abastecimentos → cadastros_equipamentos',
       COUNT(*)
FROM farms.frota_abastecimentos fa
WHERE fa.equipamento_id IS NOT NULL
  AND NOT EXISTS (
      SELECT 1 FROM farms.cadastros_equipamentos ce
      WHERE ce.id = fa.equipamento_id AND ce.tenant_id = fa.tenant_id
  )
ORDER BY sem_par_composto DESC;

\echo '=== FIM — todos os valores devem ser 0 antes de aplicar 01C ==='
