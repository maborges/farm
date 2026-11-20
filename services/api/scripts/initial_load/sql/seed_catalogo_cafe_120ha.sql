-- Catálogo inicial de consumo para uma operação de café de até 120 ha.
--
-- Execute APÓS os seeds globais de unidades e categorias:
--   cd services/api
--   psql "$DATABASE_URL" -v tenant_id='UUID_DO_TENANT' \
--     -f scripts/initial_load/sql/seed_catalogo_cafe_120ha.sql
--
-- Não cria saldo inicial. Use a Implantação Assistida para as quantidades
-- físicas existentes. Produtos fitossanitários abaixo são papéis de catálogo:
-- complete marca, registro, princípio ativo, receita e uso apenas sob
-- recomendação e responsabilidade técnica.

\if :{?tenant_id}
\else
  \echo 'Informe -v tenant_id=UUID_DO_TENANT.'
  \quit
\endif

BEGIN;

CREATE TEMP TABLE seed_cafe_120ha_produtos (
  codigo_interno text PRIMARY KEY,
  nome text NOT NULL,
  tipo text NOT NULL,
  categoria text NOT NULL,
  unidade_medida text NOT NULL,
  qtd_conteudo numeric,
  unidade_conteudo text,
  estoque_minimo numeric NOT NULL,
  descricao text NOT NULL,
  classe_agronomica text,
  cultura_alvo text,
  composicao_npk text,
  requer_receituario boolean NOT NULL DEFAULT false,
  lote_controlado boolean NOT NULL DEFAULT false,
  epi_tipo_protecao text
) ON COMMIT DROP;

INSERT INTO seed_cafe_120ha_produtos VALUES
  -- Nutrição e correção: a fórmula e o volume final dependem da análise de solo/foliar.
  ('CAF-FERT-CALCARIO', 'Calcário agrícola', 'FERTILIZANTE', 'Fertilizantes Sólidos', 'KG', NULL, NULL, 1000, 'Corretivo de acidez para manejo de solo em café.', NULL, 'CAFE', NULL, false, true, NULL),
  ('CAF-FERT-GESSO', 'Gesso agrícola', 'FERTILIZANTE', 'Fertilizantes Sólidos', 'KG', NULL, NULL, 1000, 'Condicionador de solo e fonte de cálcio e enxofre.', NULL, 'CAFE', NULL, false, true, NULL),
  ('CAF-FERT-UREIA', 'Fonte nitrogenada — ureia', 'FERTILIZANTE', 'Fertilizantes Sólidos', 'KG', NULL, NULL, 500, 'Fonte nitrogenada; dose e parcelamento dependem da recomendação técnica.', NULL, 'CAFE', '45-00-00', false, true, NULL),
  ('CAF-FERT-SULFATO-AMONIO', 'Fonte nitrogenada — sulfato de amônio', 'FERTILIZANTE', 'Fertilizantes Sólidos', 'KG', NULL, NULL, 500, 'Fonte de nitrogênio e enxofre.', NULL, 'CAFE', '20-00-00+S', false, true, NULL),
  ('CAF-FERT-CLORETO-POTASSIO', 'Fonte potássica — cloreto de potássio', 'FERTILIZANTE', 'Fertilizantes Sólidos', 'KG', NULL, NULL, 500, 'Fonte potássica para adubação conforme análise.', NULL, 'CAFE', '00-00-60', false, true, NULL),
  ('CAF-FERT-MAP', 'Fonte fosfatada — MAP', 'FERTILIZANTE', 'Fertilizantes Sólidos', 'KG', NULL, NULL, 250, 'Fertilizante fosfatado para correção ou manutenção.', NULL, 'CAFE', '11-52-00', false, true, NULL),
  ('CAF-FERT-SSP', 'Fonte fosfatada — superfosfato simples', 'FERTILIZANTE', 'Fertilizantes Sólidos', 'KG', NULL, NULL, 250, 'Fertilizante fosfatado com enxofre e cálcio.', NULL, 'CAFE', '00-18-00', false, true, NULL),
  ('CAF-FERT-NPK-PRESCRITO', 'Fertilizante NPK formulado sob prescrição', 'FERTILIZANTE', 'Fertilizantes Sólidos', 'KG', NULL, NULL, 500, 'Fórmula NPK a definir pelo responsável técnico para os talhões.', NULL, 'CAFE', NULL, false, true, NULL),
  ('CAF-FERT-SULFATO-MAGNESIO', 'Fonte de magnésio — sulfato de magnésio', 'FERTILIZANTE', 'Fertilizantes Sólidos', 'KG', NULL, NULL, 100, 'Fonte de magnésio e enxofre para correção nutricional.', NULL, 'CAFE', NULL, false, true, NULL),
  ('CAF-FERT-ACIDO-BORICO', 'Fonte de boro — ácido bórico', 'FERTILIZANTE', 'Fertilizantes Sólidos', 'KG', NULL, NULL, 25, 'Micronutriente para uso apenas conforme diagnóstico técnico.', NULL, 'CAFE', NULL, false, true, NULL),
  ('CAF-FERT-SULFATO-ZINCO', 'Fonte de zinco — sulfato de zinco', 'FERTILIZANTE', 'Fertilizantes Sólidos', 'KG', NULL, NULL, 25, 'Micronutriente para correção conforme análise.', NULL, 'CAFE', NULL, false, true, NULL),
  ('CAF-FERT-FOLIAR-NPK', 'Fertilizante foliar NPK', 'FERTILIZANTE', 'Foliares', 'L', NULL, NULL, 20, 'Fertilizante foliar a especificar por análise e estádio fenológico.', NULL, 'CAFE', NULL, false, true, NULL),
  ('CAF-FERT-FOLIAR-CALCIO-BORO', 'Fertilizante foliar cálcio e boro', 'FERTILIZANTE', 'Foliares', 'L', NULL, NULL, 20, 'Fertilizante foliar para manejo nutricional sob recomendação.', NULL, 'CAFE', NULL, false, true, NULL),
  ('CAF-FERT-ORGANOMINERAL', 'Fertilizante organomineral para café', 'FERTILIZANTE', 'Fertilizantes Sólidos', 'KG', NULL, NULL, 250, 'Produto organomineral com formulação a definir.', NULL, 'CAFE', NULL, false, true, NULL),

  -- Proteção fitossanitária: cadastros genéricos, sem produto comercial ou dose.
  ('CAF-HERB-PRE-EMERGENCIA', 'Herbicida pré-emergente para entrelinhas de café', 'DEFENSIVO', 'Herbicidas', 'L', NULL, NULL, 20, 'Selecionar somente produto registrado para café e situação da área.', 'HERBICIDA', 'CAFE', NULL, true, true, NULL),
  ('CAF-HERB-POS-EMERGENCIA', 'Herbicida pós-emergente dirigido para entrelinhas de café', 'DEFENSIVO', 'Herbicidas', 'L', NULL, NULL, 20, 'Aplicação dirigida e produto a definir por receita agronômica.', 'HERBICIDA', 'CAFE', NULL, true, true, NULL),
  ('CAF-HERB-GRAMINICIDA', 'Herbicida seletivo para gramíneas em café', 'DEFENSIVO', 'Herbicidas', 'L', NULL, NULL, 10, 'Selecionar conforme planta daninha e registro vigente.', 'HERBICIDA', 'CAFE', NULL, true, true, NULL),
  ('CAF-FUN-FERRUGEM', 'Fungicida para ferrugem do cafeeiro', 'DEFENSIVO', 'Fungicidas', 'L', NULL, NULL, 20, 'Produto, rotação de mecanismos e calendário definidos por responsável técnico.', 'FUNGICIDA', 'CAFE', NULL, true, true, NULL),
  ('CAF-FUN-CERCOSPORIOSE', 'Fungicida para cercosporiose do cafeeiro', 'DEFENSIVO', 'Fungicidas', 'L', NULL, NULL, 20, 'Produto a selecionar conforme monitoramento e registro para cultura.', 'FUNGICIDA', 'CAFE', NULL, true, true, NULL),
  ('CAF-FUN-PHOMA', 'Fungicida para mancha de phoma em café', 'DEFENSIVO', 'Fungicidas', 'L', NULL, NULL, 10, 'Produto a selecionar para áreas e condições de risco monitoradas.', 'FUNGICIDA', 'CAFE', NULL, true, true, NULL),
  ('CAF-INS-BICHO-MINEIRO', 'Inseticida para bicho-mineiro do cafeeiro', 'DEFENSIVO', 'Inseticidas', 'L', NULL, NULL, 10, 'Selecionar após monitoramento e com produto registrado para café.', 'INSETICIDA', 'CAFE', NULL, true, true, NULL),
  ('CAF-INS-BROCA', 'Inseticida para broca-do-café', 'DEFENSIVO', 'Inseticidas', 'L', NULL, NULL, 10, 'Selecionar conforme nível de ação, monitoramento e registro vigente.', 'INSETICIDA', 'CAFE', NULL, true, true, NULL),
  ('CAF-ACA-MANEJO', 'Acaricida para manejo de ácaros em café', 'DEFENSIVO', 'Acaricidas', 'L', NULL, NULL, 10, 'Selecionar conforme identificação da praga e receituário.', 'ACARICIDA', 'CAFE', NULL, true, true, NULL),
  ('CAF-NEM-MANEJO', 'Nematicida para manejo de nematoides em café', 'DEFENSIVO', 'Nematicidas', 'KG', NULL, NULL, 20, 'Selecionar conforme laudo nematológico e recomendação técnica.', 'NEMATICIDA', 'CAFE', NULL, true, true, NULL),
  ('CAF-BIO-TRICHODERMA', 'Biológico à base de Trichoderma para café', 'INOCULANTE', 'Biológicos', 'KG', NULL, NULL, 10, 'Insumo biológico; fabricante, cepa e uso devem ser validados pelo responsável técnico.', NULL, 'CAFE', NULL, false, true, NULL),
  ('CAF-BIO-BACILLUS', 'Biológico à base de Bacillus para café', 'INOCULANTE', 'Biológicos', 'KG', NULL, NULL, 10, 'Insumo biológico para programa técnico de manejo.', NULL, 'CAFE', NULL, false, true, NULL),
  ('CAF-BIO-BEAUVERIA', 'Biológico à base de Beauveria para café', 'INOCULANTE', 'Biológicos', 'KG', NULL, NULL, 10, 'Insumo biológico para programa técnico de manejo.', NULL, 'CAFE', NULL, false, true, NULL),
  ('CAF-BIO-METARHIZIUM', 'Biológico à base de Metarhizium para café', 'INOCULANTE', 'Biológicos', 'KG', NULL, NULL, 10, 'Insumo biológico para programa técnico de manejo.', NULL, 'CAFE', NULL, false, true, NULL),
  ('CAF-ADJ-ESPALHANTE', 'Adjuvante espalhante adesivo', 'ADJUVANTE', 'Adjuvantes', 'L', NULL, NULL, 10, 'Adjuvante a utilizar somente quando compatível com a recomendação do produto principal.', NULL, 'CAFE', NULL, false, true, NULL),
  ('CAF-ADJ-OLHO-VEGETAL', 'Adjuvante óleo vegetal', 'ADJUVANTE', 'Adjuvantes', 'L', NULL, NULL, 10, 'Adjuvante para calda mediante indicação técnica e compatibilidade.', NULL, 'CAFE', NULL, false, true, NULL),
  ('CAF-ADJ-CONDICIONADOR', 'Condicionador de água e pH para pulverização', 'ADJUVANTE', 'Adjuvantes', 'L', NULL, NULL, 10, 'Condicionador de calda conforme qualidade da água e orientação técnica.', NULL, 'CAFE', NULL, false, true, NULL),

  -- Segurança e operação.
  ('EPI-RESP-PFF2', 'Respirador particulado PFF2', 'EPI', 'EPI', 'UN', 1, 'UN', 20, 'Proteção respiratória; validar CA e troca conforme fabricante.', NULL, NULL, NULL, false, false, 'RESPIRATORIO'),
  ('EPI-RESP-SEMI-FACIAL', 'Respirador semifacial reutilizável', 'EPI', 'EPI', 'UN', 1, 'UN', 4, 'Proteção respiratória reutilizável; cadastrar CA do modelo adquirido.', NULL, NULL, NULL, false, false, 'RESPIRATORIO'),
  ('EPI-FILTRO-RESPIRADOR', 'Filtro para respirador reutilizável', 'EPI', 'EPI', 'UN', 1, 'UN', 12, 'Filtro compatível com o respirador aprovado pela operação.', NULL, NULL, NULL, false, false, 'RESPIRATORIO'),
  ('EPI-LUVA-NITRILICA', 'Luva de proteção química nitrílica', 'EPI', 'EPI', 'UN', 1, 'UN', 30, 'Luva para proteção química; validar CA e compatibilidade.', NULL, NULL, NULL, false, false, 'MAOS'),
  ('EPI-OCULOS-AMPLA-VISAO', 'Óculos de proteção ampla visão', 'EPI', 'EPI', 'UN', 1, 'UN', 10, 'Proteção ocular para preparo e aplicação conforme atividade.', NULL, NULL, NULL, false, false, 'OLHOS'),
  ('EPI-AVENTAL-IMPERMEAVEL', 'Avental impermeável de proteção química', 'EPI', 'EPI', 'UN', 1, 'UN', 10, 'Proteção de tronco; validar CA do item adquirido.', NULL, NULL, NULL, false, false, 'CORPO'),
  ('EPI-BOTA-PVC', 'Bota de PVC de cano longo', 'EPI', 'EPI', 'UN', 1, 'UN', 10, 'Proteção de pés para atividades com produtos e lavagem.', NULL, NULL, NULL, false, false, 'PES'),
  ('EPI-MACACAO-IMPERMEAVEL', 'Macacão impermeável de proteção química', 'EPI', 'EPI', 'UN', 1, 'UN', 10, 'Proteção corporal; validar CA e tamanho na aquisição.', NULL, NULL, NULL, false, false, 'CORPO'),
  ('MAT-LIMPEZA-DETERGENTE', 'Detergente para limpeza de equipamentos', 'MATERIAL_GERAL', 'Limpeza e Higiene', 'L', NULL, NULL, 20, 'Limpeza de pulverizadores e utensílios conforme procedimento operacional.', NULL, NULL, NULL, false, false, NULL),
  ('MAT-LIMPEZA-HIGIENIZANTE', 'Higienizante para pós-colheita', 'MATERIAL_GERAL', 'Limpeza e Higiene', 'L', NULL, NULL, 20, 'Higienização de superfícies e equipamentos de pós-colheita.', NULL, NULL, NULL, false, false, NULL),

  -- Colheita, secagem, beneficiamento e expedição.
  ('MAT-COLHEITA-PANO', 'Pano de colheita para café', 'MATERIAL_GERAL', 'Materiais de Colheita', 'UN', 1, 'UN', 20, 'Pano/lona de recolhimento para colheita manual ou derriça.', NULL, NULL, NULL, false, false, NULL),
  ('MAT-COLHEITA-SACARIA', 'Sacaria retornável para café colhido', 'MATERIAL_GERAL', 'Materiais de Colheita', 'UN', 1, 'UN', 100, 'Sacaria para transporte interno de café durante a colheita.', NULL, NULL, NULL, false, false, NULL),
  ('MAT-COLHEITA-BIGBAG', 'Big bag para café', 'MATERIAL_GERAL', 'Materiais de Colheita', 'UN', 1, 'UN', 20, 'Big bag para logística interna e armazenamento conforme padrão da operação.', NULL, NULL, NULL, false, false, NULL),
  ('MAT-POS-COLHEITA-SACA-JUTA', 'Saca de juta para café beneficiado', 'MATERIAL_GERAL', 'Materiais de Pós-colheita', 'UN', 1, 'UN', 100, 'Embalagem para café beneficiado quando aplicável ao padrão comercial.', NULL, NULL, NULL, false, false, NULL),
  ('MAT-POS-COLHEITA-EMBALAGEM', 'Embalagem para amostra de café', 'MATERIAL_GERAL', 'Materiais de Pós-colheita', 'UN', 1, 'UN', 100, 'Embalagem para amostras, classificação e rastreabilidade.', NULL, NULL, NULL, false, false, NULL),
  ('MAT-POS-COLHEITA-ETIQUETA', 'Etiqueta de rastreabilidade para lote de café', 'MATERIAL_GERAL', 'Materiais de Pós-colheita', 'UN', 1, 'UN', 200, 'Etiqueta para identificação de lote, origem e status de processamento.', NULL, NULL, NULL, false, false, NULL),
  ('MAT-POS-COLHEITA-LACRE', 'Lacre ou fita para fechamento de embalagem', 'MATERIAL_GERAL', 'Materiais de Pós-colheita', 'UN', 1, 'UN', 100, 'Lacre de embalagem para armazenamento e expedição.', NULL, NULL, NULL, false, false, NULL),
  ('MAT-POS-COLHEITA-PALET', 'Pallet para armazenagem de café', 'MATERIAL_GERAL', 'Materiais de Pós-colheita', 'UN', 1, 'UN', 10, 'Pallet para manter sacarias afastadas do piso.', NULL, NULL, NULL, false, false, NULL),
  ('MAT-MANUTENCAO-GRAXA', 'Graxa para manutenção de máquinas', 'LUBRIFICANTE', 'Lubrificantes e Filtros', 'KG', NULL, NULL, 20, 'Consumível de manutenção de equipamentos, conforme manual do fabricante.', NULL, NULL, NULL, false, false, NULL),
  ('COMB-DIESEL-S10', 'Óleo diesel S10', 'COMBUSTIVEL', 'Combustíveis', 'L', NULL, NULL, 500, 'Combustível para máquinas e equipamentos compatíveis.', NULL, NULL, NULL, false, false, NULL),
  ('COMB-LUBRIFICANTE-MOTOR', 'Lubrificante de motor para máquinas agrícolas', 'LUBRIFICANTE', 'Lubrificantes e Filtros', 'L', NULL, NULL, 20, 'Especificação deve respeitar o manual de cada equipamento.', NULL, NULL, NULL, false, false, NULL);

-- Categorias complementares do tenant. As categorias globais são pré-requisito.
INSERT INTO cadastros_categorias_produto (id, tenant_id, sistema, parent_id, nome, descricao, cor, icone, ordem, ativo, created_at, updated_at)
SELECT gen_random_uuid(), :'tenant_id'::uuid, false, pai.id, nova.nome, nova.descricao, nova.cor, nova.icone, nova.ordem, true, now(), now()
FROM (VALUES
  ('Acaricidas', 'Defensivos destinados ao manejo de ácaros.', '#0E7490', 'bug', 5, 'Defensivos'),
  ('Biológicos', 'Insumos biológicos para manejo do cafeeiro.', '#15803D', 'leaf', 6, 'Insumos Agrícolas'),
  ('Materiais de Colheita', 'Consumíveis para colheita e transporte interno.', '#92400E', 'package', 5, 'Material Geral'),
  ('Materiais de Pós-colheita', 'Consumíveis para secagem, armazenamento e expedição.', '#A16207', 'package-check', 6, 'Material Geral')
) AS nova(nome, descricao, cor, icone, ordem, pai_nome)
JOIN cadastros_categorias_produto pai
  ON pai.nome = nova.pai_nome AND pai.tenant_id IS NULL AND pai.ativo = true
WHERE NOT EXISTS (
  SELECT 1 FROM cadastros_categorias_produto existente
  WHERE existente.tenant_id = :'tenant_id'::uuid
    AND existente.nome = nova.nome
    AND existente.parent_id = pai.id
);

-- Produtos do tenant: não sobrescreve cadastros já ajustados pela operação.
INSERT INTO cadastros_produtos (
  id, tenant_id, nome, tipo, unidade_medida, codigo_interno, descricao,
  categoria_id, qtd_conteudo, unidade_conteudo, estoque_minimo, preco_medio,
  ativo, created_at, updated_at
)
SELECT
  gen_random_uuid(), :'tenant_id'::uuid, s.nome, s.tipo, s.unidade_medida,
  s.codigo_interno, s.descricao, categoria.id, s.qtd_conteudo,
  s.unidade_conteudo, s.estoque_minimo, 0, true, now(), now()
FROM seed_cafe_120ha_produtos s
JOIN LATERAL (
  SELECT c.id
  FROM cadastros_categorias_produto c
  WHERE c.nome = s.categoria
    AND c.ativo = true
    AND (c.tenant_id = :'tenant_id'::uuid OR c.tenant_id IS NULL)
  ORDER BY (c.tenant_id = :'tenant_id'::uuid) DESC
  LIMIT 1
) categoria ON true
ON CONFLICT (tenant_id, codigo_interno) DO NOTHING;

INSERT INTO cadastros_produtos_agricola (
  id, produto_id, classe_agronomica, cultura_alvo, composicao_npk
)
SELECT gen_random_uuid(), p.id, s.classe_agronomica, s.cultura_alvo, s.composicao_npk
FROM seed_cafe_120ha_produtos s
JOIN cadastros_produtos p
  ON p.tenant_id = :'tenant_id'::uuid AND p.codigo_interno = s.codigo_interno
WHERE s.tipo IN ('FERTILIZANTE', 'DEFENSIVO', 'INOCULANTE', 'ADJUVANTE')
  AND NOT EXISTS (
    SELECT 1 FROM cadastros_produtos_agricola a WHERE a.produto_id = p.id
  );

INSERT INTO cadastros_produtos_estoque (
  id, produto_id, perecivel, requer_receituario, lote_controlado
)
SELECT
  gen_random_uuid(), p.id,
  s.tipo IN ('FERTILIZANTE', 'DEFENSIVO', 'INOCULANTE', 'ADJUVANTE'),
  s.requer_receituario, s.lote_controlado
FROM seed_cafe_120ha_produtos s
JOIN cadastros_produtos p
  ON p.tenant_id = :'tenant_id'::uuid AND p.codigo_interno = s.codigo_interno
WHERE NOT EXISTS (
  SELECT 1 FROM cadastros_produtos_estoque e WHERE e.produto_id = p.id
);

INSERT INTO cadastros_produtos_epi (id, produto_id, tipo_protecao)
SELECT gen_random_uuid(), p.id, s.epi_tipo_protecao
FROM seed_cafe_120ha_produtos s
JOIN cadastros_produtos p
  ON p.tenant_id = :'tenant_id'::uuid AND p.codigo_interno = s.codigo_interno
WHERE s.tipo = 'EPI'
  AND NOT EXISTS (
    SELECT 1 FROM cadastros_produtos_epi e WHERE e.produto_id = p.id
  );

COMMIT;
