# AgroSaaS — Análise Completa de Features, Custo e Valor de Mercado
**Data:** Maio 2026

---

## MÓDULO AGRÍCOLA (32 submódulos)

### Tier ESSENCIAL

| Submódulo | Features Identificadas |
|---|---|
| **Safras** | CRUD safra, ciclo de fases, multi-cultivo (Cultivo/CultivoArea), dashboard por safra |
| **Talhões / Áreas Rurais** | Gestão de áreas produtivas, geolocalização, vinculação a safra |
| **Planejamento (a1)** | Orçamento por safra, metas de produtividade, planejamento de custos |
| **Romaneios / Colheita** | Romaneios de colheita, lotes de entrega, integração com beneficiamento, rastreio P0 |
| **Análises de Solo** | Laudo laboratorial → recomendações de calagem/adubação, estimativa automática de custos, vinculação por talhão |
| **Cadastros** | Culturas, variedades, insumos, fornecedores, commodities |
| **Dashboard Agrícola** | KPIs safra, timeline, mapa de talhões |
| **Financeiro KPIs** | DRE por safra, margem operacional, custo/ha |

### Tier PROFISSIONAL

| Submódulo | Features Identificadas |
|---|---|
| **Operações** | Tratos culturais por fase, ordem de serviço, apontamento de horas |
| **Beneficiamento** | Pós-colheita café, geração de venda, integração romaneio→comercialização |
| **Custos** | Custo por operação/fase, rateio por cultura |
| **Checklist** | Templates de checklist operacional, checklists por safra |
| **Agronomo** | Visitas técnicas, laudos agronômicos |
| **Monitoramento** | Pragas, doenças, vigilância fitossanitária |
| **Fenologia** | Estágios fenológicos por cultura |
| **Amostragem de Solo** | Coleta de amostras, mapas de fertilidade, prescrições VRA |
| **Prescricoes** | Receituário agronômico |
| **Irrigação** | Manejo de irrigação, balanço hídrico |
| **Cenários** | Simulação what-if por safra, comparativo de cenários, IA recomenda melhor cenário |
| **Climático / Meteorologia** | Dados climáticos, estações meteorológicas |
| **Caderno de Campo** | Registro de atividades, histórico operacional |
| **Alertas Agrícolas** | Alertas financeiros runtime (3 regras), recomendações acionáveis |
| **Tarefas** | Geração automática de SafraTarefa a partir de prescrições |
| **Templates** | Templates agrícolas reutilizáveis |
| **Rastreabilidade** | Rastreio de lote, cadeia de custódia |
| **Relatórios Agrícolas** | Exportação de relatórios por safra, operação, custo |

### Tier ENTERPRISE

| Submódulo | Features Identificadas |
|---|---|
| **NDVI** | Índices de vegetação por satélite, mapa NDVI por talhão |
| **NDVI Avançado** | Série temporal NDVI, alertas de estresse vegetativo |
| **Previsões** | Modelo preditivo de produtividade |
| **Produção Units** | Gestão de unidades de produção granular |

---

## MÓDULOS COM INTERFACE DIRETA COM AGRÍCOLA

### Financeiro

| Feature | Descrição |
|---|---|
| Lançamentos Financeiros | Custeio de safra, categorização por tipo/fase |
| DRE Operacional por Safra | Step 183 — DRE vinculado à safra ativa |
| Receitas Operacionais | Registro manual de receitas por safra |
| Despesas / Contas a Pagar | CRUD com baixa e conciliação |
| Plano de Contas | Estrutura hierárquica de contas |
| Fluxo de Caixa | Projeção temporal |
| Conciliação Bancária | Contas bancárias + lançamentos bancários |
| Notas Fiscais (NF-e) | Emissão e gestão |
| Comercialização | Venda de commodities vinculada à safra |
| Simulação What-If | Cenários financeiros por safra (Step 185) |
| Plano de Ação | Items de ação vinculados a alertas financeiros |
| Carne Leão / LCDPR / eSocial | Obrigações fiscais produtor rural |
| Rateio | Rateio de custos entre culturas/áreas |

### Operacional

| Feature | Descrição |
|---|---|
| **Estoque** | Ledger canônico FIFO, movimentações, lotes, histórico de custo |
| **Compras** | Pedidos de compra, cotações, aprovação, inteligência de compras |
| **Fornecedores** | Cadastro canônico, índice de desempenho, consolidação |
| **Frota** | Gestão de equipamentos/veículos, manutenções, oficina |
| **Abastecimentos** | Controle de combustível por equipamento |
| **Apontamentos** | Apontamento de horas/atividades operacionais |
| **Requisições** | Requisições internas de estoque |
| **Savings Dashboard** | Economia gerada por inteligência de compras (Step 163) |

### Pecuária

| Feature | Descrição |
|---|---|
| Lotes de Animais | Gestão de lotes, raças, categoria animal |
| Manejo | Registros sanitários, pesagens, reprodução |
| Piquetes | Gestão de piquetes e pastagens |
| Relatórios | Relatórios de desempenho pecuário |

### Inteligência Artificial (IA)

| Serviço | Descrição |
|---|---|
| `insights_service` | Insights automáticos de performance |
| `autopilot_service` | Automações baseadas em regras de negócio |
| `autopilot_metrics_service` | Métricas de performance do autopilot |
| `growth_service` | Análise de crescimento e oportunidades |
| `predicao_risco_service` | Predição de risco financeiro/operacional |
| `estresse_financeiro_service` | Detecção de estresse financeiro por safra |
| `dre_intelligence_service` | IA sobre DRE: tendências, anomalias |
| `plano_acao_service` | Geração automática de planos de ação |
| `adaptive_service` | Adaptação UX por perfil de uso |
| `acoes_assistidas_service` | Assistência contextual por ação do usuário |
| `upgrade_recomendacao_service` | Recomenda upgrade de plano |
| `essential_service` | Modo essencial de IA para usuários básicos |
| `compras_estrategia_service` | IA para otimização de compras |
| `ux_telemetry_service` | Telemetria de UX para otimização de interface |
| `performance_service` | KPIs de performance geral |
| `usage_service` | Rastreamento de uso por feature |

### Notificações

- WebSocket push por tenant
- Notificações persistidas + controle de lidas/não-lidas
- Geração de mensagem via IA
- `sincronizar_safra` — sincroniza alertas com estado da safra
- Deduplicação automática

### Plataforma / SaaS Core

| Feature | Descrição |
|---|---|
| Multi-tenancy | Isolamento absoluto JWT + RLS |
| RBAC 3 camadas | Backoffice / Tenant / Farm-level |
| Feature Gates (Module Flags) | Por tier de plano |
| Onboarding | Fluxo completo de cadastro de produtor |
| Billing (Stripe + Asaas) | Assinaturas, planos, trial, upgrades |
| Backoffice Admin | Gestão de tenants, CRM, auditoria, sessões |
| Auditoria | Trilha de auditoria por tenant |
| Suporte + Knowledge Base | Chat de suporte + base de conhecimento |
| Sessions | Gestão de sessões ativas |
| Cupons | Cupons de desconto |
| Relatórios gerais | Exportação cross-módulo |
| Configurações | SMTP, integrações, configurações de tenant |
| API Pública | API keys, logs, versões |

### Integrações Enterprise

| Integração | Status |
|---|---|
| Sankhya ERP | Ativo |
| Regulatórias (e-CAC, etc.) | Ativo |
| SAP, Power BI, Benchmarks | Roadmap (comentado) |
| IoT / Sensores | Estrutura presente |
| Ambiental | Módulo estruturado |

---

## ANÁLISE DETALHADA — PECUÁRIA (GAP)

### O que existe hoje (estado atual)

**3 routers ativos** (lotes, manejos, piquetes) com apenas GET + POST cada.  
**4 tabelas:** `pec_lotes`, `pec_animais`, `manejo`, `piquete`.  
Subdiretório `producao/` tem model mas **sem router registrado**.  
Frontend: 5 páginas (dashboard, lotes, manejo, piquetes, relatórios) — stubs básicos.

### Cobertura estimada: ~20% do necessário para adoção

### Features ausentes vs. concorrentes (Aegro, Solocria, Sior)

| Feature ausente | Prioridade | Por que importa |
|---|---|---|
| **Movimentação de rebanho** (compra, venda, transferência, morte, abate) | Alta | Sem isso o número de cabeças fica inconsistente |
| **Pesagem e GPD** (ganho de peso diário) | Alta | KPI principal do pecuarista |
| **Manejo sanitário** (vacinas, vermifugação, tratamentos) | Alta | Obrigação legal + rastreabilidade |
| **Manejo reprodutivo** (IA, IATF, gestação, parição) | Alta | Core do negócio para criadores |
| **Registro individual de animal** (brinco, RFID, RGN) | Alta | Rastreabilidade para exportação |
| **Custos por animal/lote** | Média | Integração com financeiro |
| **Pastagem / Lotação** (UA/ha, manejo rotativo) | Média | Diferencial para gestão avançada |
| **Abate e comercialização** (rendimento de carcaça, @ arroba) | Média | Encerra o ciclo produtivo |
| **Relatórios zootécnicos** (natalidade, mortalidade, desfrute) | Média | Indicadores mensais obrigatórios |
| **Nutrição e dieta** (arraçoamento, formulação) | Baixa | Integra com estoque de insumos |
| **Rebanho hierárquico** (matrizes, reprodutores, crias) | Baixa | Genealogia básica |

### Estimativa para fechar o gap básico
~300–400h — sequência recomendada: movimentação → pesagem/GPD → sanitário → reprodutivo.

---

## AVALIAÇÃO DE CUSTO DE DESENVOLVIMENTO

### Estimativa de Horas por Grupo

| Grupo | Horas Estimadas |
|---|---|
| Plataforma SaaS core (auth, multi-tenancy, RBAC, billing, backoffice) | ~800h |
| Módulo Agrícola (32 submódulos, backend + frontend) | ~2.400h |
| Financeiro completo (DRE, fluxo, conciliação, NF-e, LCDPR) | ~600h |
| Operacional (estoque FIFO, compras, frota, apontamentos) | ~700h |
| Pecuária | ~200h |
| IA (15+ serviços + telemetria + autopilot) | ~500h |
| Notificações + WebSocket | ~80h |
| Integrações (Sankhya, regulatórias, IoT) | ~200h |
| Testes, documentação, DevOps/CI | ~300h |
| **TOTAL** | **~5.780h** |

### Custo em BRL (mercado brasileiro, 2026)

| Cenário | Taxa/h | Total |
|---|---|---|
| Dev júnior/pleno outsourcing | R$ 80/h | ~R$ 462.000 |
| Dev sênior / squad misto | R$ 150/h | ~R$ 867.000 |
| Agência especializada AgTech | R$ 200–250/h | ~R$ 1,15M–1,45M |

> Estimativa realista para o estado atual: **R$ 900k–1,2M** em custo direto de desenvolvimento.

---

## AVALIAÇÃO DE VALOR DE MERCADO

### Benchmarks de AgTech SaaS (Brasil, 2025–2026)

| Produto Comparável | MRR estimado por cliente | Posicionamento |
|---|---|---|
| Aegro | R$ 150–600/fazenda/mês | Gestão agrícola básica |
| Agrofy / AgriPoint | R$ 300–1.200/mês | Gestão + comercialização |
| Solocria / Sior | R$ 500–2.000/mês | Pecuária + agrícola |
| **AgroSaaS (este produto)** | R$ 300–1.500/mês | Multi-módulo completo |

### Pontos fortes (agregam valor)

- Plataforma multi-tenant pronta para escala
- IA embarcada com 15+ serviços (diferencial competitivo alto)
- Cobertura end-to-end: planejamento → colheita → financeiro → comercialização
- FIFO/Ledger canônico de estoque (raridade em AgTech BR)
- RBAC granular com feature gates por plano (pronto para freemium/enterprise)
- Integrações Sankhya + regulatórias

### Pontos de atenção (redutores de valor)

- Pecuária básica (~20% do necessário para adoção por pecuaristas)
- Integrações enterprise (SAP, Power BI) não finalizadas
- Módulo ambiental/IoT estruturado mas não maduro
- App mobile ausente

### Valuation estimado

| Método | Valor |
|---|---|
| **Custo de reposição** (dev cost × 1,5–2×) | R$ 1,4M–2,4M |
| **SDE/ARR múltiplo** (50 clientes × R$ 500 MRR = R$ 300k ARR × 5–8×) | R$ 1,5M–2,4M |
| **Potencial com tração** (200+ clientes, ARR R$ 1,2M × 6–10×) | R$ 7M–12M |

> **Valor de mercado atual (pré-receita ou early revenue):** entre **R$ 1,4M e R$ 2,5M** como ativo de software.  
> Com tração comprovada (100+ clientes pagantes), o valor sobe para a faixa de **R$ 5M–10M**.

---

*Documento gerado em: Maio 2026 — baseado em análise estática do código-fonte e comparativo de mercado AgTech BR.*
