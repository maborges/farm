-- Massa de dados de apoio ao modulo Agricultura
-- Uso:
-- 1. Descobrir os UUIDs reais do ambiente
-- 2. Substituir os placeholders do arquivo massa-dados-agricultura-api.json
-- 3. Executar os payloads via API
-- 4. Rodar estas queries para validar persistencia e agregacoes

-- =========================================================
-- LOOKUPS DE UUIDS
-- =========================================================

-- Talhoes / areas rurais
select id, nome, area_hectares, tenant_id
from cadastros_areas_rurais
where nome in (
  'Talhão A1',
  'Talhão A2',
  'Talhão B1',
  'Café A1',
  'Café A2',
  'Café B1'
)
order by nome;

-- Produtos
select id, nome, sku, tenant_id
from cadastros_produtos
where nome in (
  'Semente Soja TMG 2383',
  'Ureia 45%',
  'KCl',
  'Glifosato',
  'Fungicida Triazol',
  'Fungicida para ferrugem',
  'Inseticida broca do café',
  'Herbicida pós-emergente'
)
order by nome;

-- Pessoas de apoio
select id, nome, tipo_pessoa, tenant_id
from cadastros_pessoas
order by nome
limit 50;

-- Planos de conta
select id, codigo, nome, tipo, tenant_id
from fin_planos_conta
order by codigo, nome;

-- Escalas fenologicas
select id, cultura, codigo, nome, tenant_id, ativo
from fenologia_escalas
where cultura in ('Soja', 'Café', 'Cafe')
order by cultura, ordem, codigo;

-- Catalogo de monitoramento
select id, tipo, nome_popular, cultura, tenant_id, ativo
from monitoramento_catalogo
where cultura in ('Soja', 'Café', 'Cafe') or cultura is null
order by cultura nulls last, nome_popular;

-- Safras criadas
select id, ano_safra, cultura, status, tenant_id, created_at
from safras
where ano_safra = '2025/26'
order by created_at desc;

-- Production units geradas para a safra
select pu.id,
       pu.safra_id,
       pu.area_id,
       pu.area_ha,
       pu.percentual_participacao,
       pu.status
from production_units pu
where pu.safra_id in (
  select id from safras where ano_safra = '2025/26'
)
order by pu.safra_id, pu.area_id;

-- =========================================================
-- VALIDACAO DE SAFRA E TALHOES
-- =========================================================

select s.id,
       s.ano_safra,
       s.cultura,
       s.status,
       count(st.id) as total_talhoes,
       sum(coalesce(st.area_ha, 0)) as area_total_vinculada
from safras s
left join safra_talhoes st on st.safra_id = s.id
where s.ano_safra = '2025/26'
group by s.id, s.ano_safra, s.cultura, s.status
order by s.created_at desc;

-- =========================================================
-- VALIDACAO DE ORCAMENTO
-- =========================================================

select oi.safra_id,
       count(*) as total_itens,
       sum(oi.custo_total) as custo_total
from agricola_orcamento_itens oi
where oi.safra_id in (
  select id from safras where ano_safra = '2025/26'
)
group by oi.safra_id
order by custo_total desc;

select oi.safra_id,
       oi.categoria,
       sum(oi.custo_total) as custo_categoria
from agricola_orcamento_itens oi
where oi.safra_id in (
  select id from safras where ano_safra = '2025/26'
)
group by oi.safra_id, oi.categoria
order by oi.safra_id, oi.categoria;

-- =========================================================
-- VALIDACAO DE OPERACOES
-- =========================================================

select oa.safra_id,
       oa.tipo,
       count(*) as total_operacoes,
       sum(coalesce(oa.custo_total, 0)) as custo_total
from operacoes_agricolas oa
where oa.safra_id in (
  select id from safras where ano_safra = '2025/26'
)
group by oa.safra_id, oa.tipo
order by oa.safra_id, oa.tipo;

select oa.id,
       oa.safra_id,
       oa.talhao_id,
       oa.tipo,
       oa.fase_safra,
       oa.data_realizada,
       oa.area_aplicada_ha,
       oa.custo_total,
       oa.status
from operacoes_agricolas oa
where oa.safra_id in (
  select id from safras where ano_safra = '2025/26'
)
order by oa.data_realizada, oa.created_at;

-- =========================================================
-- VALIDACAO DE FENOLOGIA
-- =========================================================

select fr.safra_id,
       fr.talhao_id,
       fr.data_observacao,
       fr.escala_id,
       fe.cultura,
       fe.codigo,
       fe.nome
from safra_fenologia_registros fr
left join fenologia_escalas fe on fe.id = fr.escala_id
where fr.safra_id in (
  select id from safras where ano_safra = '2025/26'
)
order by fr.data_observacao, fr.created_at;

-- =========================================================
-- VALIDACAO DE MONITORAMENTO
-- =========================================================

select mp.safra_id,
       mp.talhao_id,
       mp.data_avaliacao,
       mp.tipo,
       mp.nome_popular,
       mp.nivel_infestacao,
       mp.nde_cultura,
       mp.atingiu_nde,
       mp.acao_tomada
from monitoramento_pragas mp
where mp.safra_id in (
  select id from safras where ano_safra = '2025/26'
)
order by mp.data_avaliacao, mp.created_at;

-- =========================================================
-- VALIDACAO DE ROMANEIOS
-- =========================================================

select rc.safra_id,
       count(*) as total_romaneios,
       sum(coalesce(rc.peso_liquido_padrao_kg, 0)) as peso_padrao_total_kg,
       sum(coalesce(rc.sacas_60kg, 0)) as total_sacas,
       sum(coalesce(rc.receita_total, 0)) as receita_total
from romaneios_colheita rc
where rc.safra_id in (
  select id from safras where ano_safra = '2025/26'
)
group by rc.safra_id
order by receita_total desc;

select rc.id,
       rc.safra_id,
       rc.talhao_id,
       rc.numero_romaneio,
       rc.data_colheita,
       rc.peso_bruto_kg,
       rc.tara_kg,
       rc.peso_liquido_padrao_kg,
       rc.sacas_60kg,
       rc.preco_saca,
       rc.receita_total
from romaneios_colheita rc
where rc.safra_id in (
  select id from safras where ano_safra = '2025/26'
)
order by rc.data_colheita, rc.created_at;

-- =========================================================
-- VALIDACAO DE BENEFICIAMENTO
-- =========================================================

select lb.id,
       lb.safra_id,
       lb.numero_lote,
       lb.metodo,
       lb.status,
       lb.peso_entrada_kg,
       lb.peso_saida_kg,
       lb.perda_secagem_kg,
       lb.perda_quebra_kg,
       lb.perda_defeito_kg
from cafe_lotes_beneficiamento lb
where lb.safra_id in (
  select id from safras where ano_safra = '2025/26'
)
order by lb.created_at desc;

select lbr.lote_id,
       lbr.romaneio_id
from cafe_lote_beneficiamento_romaneios lbr
where lbr.lote_id in (
  select id from cafe_lotes_beneficiamento
  where safra_id in (select id from safras where ano_safra = '2025/26')
)
order by lbr.lote_id, lbr.romaneio_id;

-- =========================================================
-- VALIDACAO DE CENARIOS
-- =========================================================

select sc.id,
       sc.safra_id,
       sc.nome,
       sc.tipo,
       sc.eh_base,
       sc.status,
       sc.area_total_ha,
       sc.receita_bruta_total,
       sc.custo_total,
       sc.margem_contribuicao_total,
       sc.depreciacao_total,
       sc.ir_aliquota_pct,
       sc.ir_valor_total,
       sc.resultado_liquido_total,
       sc.ponto_equilibrio_sc_ha,
       sc.calculado_em
from safra_cenarios sc
where sc.safra_id in (
  select id from safras where ano_safra = '2025/26'
)
order by sc.safra_id, sc.eh_base desc, sc.nome;

select scu.cenario_id,
       scu.production_unit_id,
       scu.produtividade_simulada,
       scu.preco_simulado,
       scu.custo_total_simulado_ha,
       scu.depreciacao_ha,
       scu.receita_bruta,
       scu.custo_total,
       scu.margem_contribuicao,
       scu.resultado_liquido
from safra_cenarios_unidades scu
where scu.cenario_id in (
  select id from safra_cenarios
  where safra_id in (select id from safras where ano_safra = '2025/26')
)
order by scu.cenario_id, scu.production_unit_id;

-- =========================================================
-- VALIDACAO EXECUTIVA FINAL
-- =========================================================

select s.id,
       s.cultura,
       s.ano_safra,
       s.status,
       coalesce(orc.custo_total_orcado, 0) as custo_orcado,
       coalesce(ops.custo_operacoes, 0) as custo_operacoes,
       coalesce(rom.total_sacas, 0) as total_sacas,
       coalesce(rom.receita_total, 0) as receita_total,
       coalesce(cen.resultado_liquido_base, 0) as resultado_liquido_base
from safras s
left join (
  select safra_id, sum(custo_total) as custo_total_orcado
  from agricola_orcamento_itens
  group by safra_id
) orc on orc.safra_id = s.id
left join (
  select safra_id, sum(custo_total) as custo_operacoes
  from operacoes_agricolas
  group by safra_id
) ops on ops.safra_id = s.id
left join (
  select safra_id,
         sum(coalesce(sacas_60kg, 0)) as total_sacas,
         sum(coalesce(receita_total, 0)) as receita_total
  from romaneios_colheita
  group by safra_id
) rom on rom.safra_id = s.id
left join (
  select safra_id,
         max(resultado_liquido_total) filter (where eh_base is true) as resultado_liquido_base
  from safra_cenarios
  group by safra_id
) cen on cen.safra_id = s.id
where s.ano_safra = '2025/26'
order by s.created_at desc;
