# NAVIGATION-ARCH-01 — Auditoria do sidebar Web

## Resumo executivo

**Veredicto: GO COM RESSALVAS para uma futura reorganização incremental.** O sidebar atual é predominantemente organizado por módulos comerciais/add-ons, com jornadas operacionais dentro de alguns módulos. Não é uma navegação puramente por domínio nem puramente por camada operacional.

Foram identificadas **11 entradas de módulos operacionais**, **1 entrada de Core (`Cadastros`)**, **4 seções Core**, **38 seções internas dos módulos**, **6 seções de Backoffice** e **136 entradas declaradas** em `sidebar-config.ts` (incluindo rotas repetidas). O componente ainda inclui 1 item geral, 4 itens de Gestão de Acessos e 11 de Configurações: **152 entradas potenciais** antes dos filtros de visibilidade.

## Arquivos e mecanismos auditados

| Papel | Caminho | Evidência |
| --- | --- | --- |
| Configuração canônica | `apps/web/src/lib/sidebar-config.ts` | Core, módulos, seções, labels, ícones, rotas, permission, tier e moduleId. |
| Renderização tenant | `apps/web/src/components/layout/app-sidebar.tsx` | Grupos, expansão, busca, filtros de permissão/tier e `ModuleGate`. |
| Gate de módulo | `apps/web/src/components/shared/module-gate.tsx` | Oculta módulo não contratado; não oferece fallback por padrão. |
| RBAC frontend | `apps/web/src/lib/permissions.ts` | `hasTenantPermission` e `hasBackofficePermission`; é filtro de UX, não autorização backend. |
| Planos | `apps/web/src/lib/constants/planos.ts` | `tierAtLeast` para `PROFISSIONAL`/`ENTERPRISE`. |
| Layout/móvel Web | `apps/web/src/components/ui/sidebar.tsx`, `app/(dashboard)/layout.tsx`, `components/layout/topbar.tsx` | Cookie de colapso, Sheet mobile e atalho `Ctrl/Cmd+B`. |
| Backoffice alternativo | `apps/web/src/components/backoffice/sidebar.tsx` | Menu duplicado, hardcoded e sem filtros RBAC; não foi encontrado consumidor ativo. |
| Campo, somente comparação | `apps/campo/src/components/campo/bottom-nav.tsx` | Quatro atalhos fixos: Início, Tarefas, Sync e Caderno; módulos ficam dentro das telas. |

## Regras de visibilidade e comportamento

1. **Tenant presente:** Dashboard, módulos, Gestão de Acessos e Configurações só renderizam com tenant ativo.
2. **Módulo contratado:** cada `SidebarModuleGroup` é envolvido por `ModuleGate(moduleId)`; Core não usa gate comercial.
3. **Plano:** itens com `minimumTier` exigem `tierAtLeast(activePlanTier, mínimo)`.
4. **Permissão frontend:** `canSeeTenantItem` aplica `hasTenantPermission` usando papel, permissões customizadas ou superuser. Backoffice usa matriz separada.
5. **Expansão:** há um módulo aberto por vez e uma seção aberta por módulo; estado é local, exceto o colapso estrutural do sidebar mantido em cookie pela UI base.
6. **Busca:** indexa Core, módulos, Backoffice, Acessos e Configurações e reaplica tier/RBAC; módulos encontrados ainda passam por `ModuleGate`.
7. **Backend:** continua sendo a fonte de verdade para autorização. O filtro Web pode esconder algo autorizado ou exibir rota cuja API negará; não substitui RBAC/RLS.

## Inventário completo da configuração atual

Cada linha abaixo representa um grupo/seção e lista todos os subitens declarados, na ordem atual. `P=` permissão; `T=` tier; `M=` módulo.

| Ordem | Grupo atual | Item / Subitem (rota) | Domínio | Tipo | Visibilidade | Problema / recomendação |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Core / Minha Propriedade | Unidades Produtivas (`/cadastros/propriedades`); Georreferenciamento (`/cadastros/propriedades/talhoes`); Commodities (`/cadastros/commodities`) | Territorial/produtos | CORE | P tenant:fazendas:view; agricola:talhoes:view; cadastros:commodities:view | Manter Core; nome da seção mistura propriedade e commodity. |
| 2 | Core / Insumos & Ativos | Catálogo de Produtos (`/cadastros/produtos`); Equipamentos & Frota (`/cadastros/equipamentos`); Tipos de Serviço (`/cadastros/tipos-servico`) | Produtos/ativos | CORE | P cadastros:produtos:view; operacional:frota:view | Manter como cadastro mestre; esclarecer que Frota operacional fica em módulo próprio. |
| 3 | Core / Pessoas & Parceiros | Pessoas & Parceiros (`/cadastros/pessoas`) | Pessoas | CORE | P cadastros:pessoas:view | Correto. |
| 4 | Core / Tabelas Auxiliares | Marcas; Modelos; Categorias de Produto (`/cadastros/tabelas/*`) | Cadastros | CORE | P específicos | Correto; acesso secundário, pode ser recolhido. |
| 5 | Imóveis Rurais / Visão Geral | Imóveis Rurais; Avaliação Patrimonial (`/cadastros/imoveis*`) | Fundiário | CORE/IMPLANTAÇÃO | M IMOVEIS_CADASTRO; P imóveis | `Imóveis Rurais` aparece também em Gestão. Preservar domínio separado do agrícola. |
| 6 | Imóveis Rurais / Gestão | Documentos e Cadastro (`/cadastros/imoveis`) | Fundiário | CORE/IMPLANTAÇÃO | M IMOVEIS_CADASTRO; P imoveis:documentos:view | Duplicação da mesma rota; unificar no futuro sem remover capacidade. |
| 7 | Agricultura / Visão Geral | Painel Agrícola (`/agricola`); Safras (`/agricola/safras`) | Agricultura | OPERACIONAL | M A1_PLANEJAMENTO; P agrícola | Boa entrada, mas Safras é a porta de jornada e deveria preceder painel na hierarquia operacional. |
| 8 | Agricultura / Planejamento | Culturas; Análises de Solo; Orçamento; Planejamento Operacional; Receitas; Custeio | Agricultura | OPERACIONAL | M A1; P agrícola; orçamento/planejamento usam rota seletora por safra | Orçamento antes do planejamento operacional é coerente só parcialmente; custos realizados não são planejamento. |
| 9 | Agricultura / Execução & Registros | Operações; Caderno; Timeline | Agricultura/Campo | OPERACIONAL | M A1; P operações | Tarefas não está aqui; Campo está em módulo externo. |
| 10 | Agricultura / Monitoramento | Pragas; Fitossanitário; Dados Climáticos; Fenologia; NDVI; Mapa de Prescrições | Agricultura | OPERACIONAL/INTELIGÊNCIA | M A1; P específicos | Boa coesão, mas recursos pertencem a add-ons diferentes sob um único gate A1. |
| 11 | Agricultura / Colheita | Romaneios; Beneficiamento | Agricultura | PRODUÇÃO | M A1; P colheita/beneficiamento | Correto. |
| 12 | Agricultura / Resultados & Inteligência | Rentabilidade; DRE Agrícola; Central de Inteligência | Agricultura | INTELIGÊNCIA | M A1; T PROFISSIONAL; P relatórios/dashboard | Correto como resultado, mas recomendações globais ficam fora. |
| 13 | Agricultura / Gestão & Relatórios | Relatórios; Central de Ajuda | Agricultura | TRANSVERSAL | M A1; P relatórios | Ajuda não é agrícola; mover conceitualmente para suporte. |
| 14 | Estoque & Suprimento / Dashboard | Painel de Suprimentos (`/suprimentos`) | Estoque/compras | TRANSVERSAL | **M O1_FROTA**; P estoque | Gate incorreto: o grupo depende de Frota, não de Estoque/Compras. |
| 15 | Estoque & Suprimento / Compras | Solicitações; Pedidos; Fornecedores | Compras | OPERACIONAL | **M O1_FROTA**; P compras/estoque | Mesmo gate incorreto; Fornecedores em `/dashboard/operacional`. |
| 16 | Estoque & Suprimento / Estoque | Saldos; Almoxarifado; Lotes; Requisições | Estoque | TRANSVERSAL | **M O1_FROTA**; P estoque | Mesmo gate incorreto. |
| 17 | Frota & Manutenção / Dashboard | Painel da Frota (`/operacional`) | Frota | TRANSVERSAL | M O1_FROTA; P frota | Correto. |
| 18 | Frota & Manutenção / Operação | Frota; Manutenções; Preventiva; Consumo; Custos; Jornadas; Inteligência; Uso Agrícola; Disponibilidade | Frota | OPERACIONAL/INTELIGÊNCIA | M O1_FROTA; T PROF./ENT.; P operacional | Coeso; Uso Agrícola é visão cruzada, não novo domínio. |
| 19 | Pecuária / Dashboard | Painel de Rebanhos; Sync Campo | Pecuária | OPERACIONAL | M P1_REBANHO; P pecuária | Correto. |
| 20 | Pecuária / Estrutura | Piquetes & Pastos | Pecuária | OPERACIONAL | M P1; P piquetes | Correto. |
| 21 | Pecuária / Rebanho | Meus Animais; Lotes; Planejamento de Manejos; Genética | Pecuária | OPERACIONAL | M P1; P pecuária | Genética é add-on próprio, mas está sob gate P1. |
| 22 | Pecuária / Saúde & Nutrição | Manejos Sanitários (`/dashboard/pecuaria/manejos`); Vacinação; Nutrição; Confinamento | Pecuária | OPERACIONAL | M P1; P pecuária | Três rotas não possuem página: `manejos` (existe `manejo`), `vacinas`, `nutricao`. |
| 23 | Pecuária / Leite | Produção de Leite | Pecuária | PRODUÇÃO | M P1; P leite | Correto, porém é add-on P4 sob gate P1. |
| 24 | Financeiro / Dashboard | Painel Financeiro | Financeiro | TRANSVERSAL | M F1_TESOURARIA; P financeiro | Correto. |
| 25 | Financeiro / Receitas & Vendas | Minhas Receitas; Romaneios de Colheita | Financeiro/agricultura | NEGÓCIO | M F1; P receitas/colheita | Romaneio duplica acesso agrícola; justificável como origem de receita, mas rótulo deve evidenciar contexto financeiro. |
| 26 | Financeiro / Despesas & Custos | Minhas Despesas; Ordens de Pagamento | Financeiro | NEGÓCIO | M F1; P despesas | Correto. |
| 27 | Financeiro / Bancário | Contas Bancárias; Conciliação | Financeiro | NEGÓCIO | M F1; P contas | Correto. |
| 28 | Financeiro / Gestão Financeira | Planos de Conta; Custos ABC; Fluxo de Caixa; Lançamentos; DRE | Financeiro | NEGÓCIO | M F1; T PROF. para ABC; P financeiro | Correto. |
| 29 | Financeiro / Hedging & Futuros | Exposição; Painel; Contratos; Registros; MTM | Financeiro/comercial | NEGÓCIO | M F1; P hedge | Add-on F4 está sob gate F1. |
| 30 | Financeiro / Fiscal & Obrigações | NF-e; LCDPR; eSocial | Financeiro | ADMINISTRAÇÃO | M F1; P fiscal | Numeração repetida “⑤”; eSocial também está em RH. |
| 31 | RH / Estrutura | Departamentos; Colaboradores | Pessoas | TRANSVERSAL | M RH1; P pessoas | Correto. |
| 32 | RH / Operação Diária | Registro de Ponto | Pessoas | OPERACIONAL | M RH1; P pessoas | Correto. |
| 33 | RH / Obrigações | Folha; eSocial | Pessoas | ADMINISTRAÇÃO | M RH1; P pessoas | eSocial aparece também em Financeiro, com possível ambiguidade. |
| 34 | SST / Visão Geral | Painel SST | Pessoas | TRANSVERSAL | M RH2; P sst | Correto. |
| 35 | SST / Itens & Entregas | EPI/EPC; Documentos SST | Pessoas | OPERACIONAL | M RH2; P sst | Mesma rota do painel para capacidades distintas. |
| 36 | SST / Relatórios | Relatório NR-31 | Pessoas | ADMINISTRAÇÃO | M RH2; P sst | Mesma rota; tratar como navegação de âncora/aba futura, não como páginas independentes. |
| 37 | Ambiental / Dashboard | Painel Ambiental | ESG | TRANSVERSAL | M AM1; P ambiental | Correto. |
| 38 | Ambiental / CAR & Áreas | Importar CAR; CARs; Áreas; Outorgas; Carbono; Certificações; Relatórios/Passaportes | ESG/fundiário | OPERACIONAL/INTELIGÊNCIA | M AM1; P ambiental | Carbono é AM2 e está sob AM1; ESG mistura compliance ambiental e certificação. |
| 39 | Ambiental / Monitoramento | Mapa; Alertas de Desmatamento; Histórico | ESG | INTELIGÊNCIA | M AM1; P ambiental | Alertas são específicos ambientais; não substituem Alert Engine global. |
| 40 | Copiloto IA / Dashboard | Painel IA; Recomendações Operacionais | Inteligência | INTELIGÊNCIA | **M IA_COPILOT**; P ia:* | `IA_COPILOT` não existe no catálogo oficial, que usa `EXT_IA`; recomendações têm permissão oficial distinta `recommendations:view`. |
| 41 | Copiloto IA / Performance & Estratégia | Performance; Plano de Ação; Resumo IA Safra | Inteligência | INTELIGÊNCIA | **M IA_COPILOT**; P ia:* | Mesmo gate inconsistente. |
| 42 | Campo PWA / Dispositivos | Dispositivos; Tarefas de Campo | Campo | OPERACIONAL | M A2_CAMPO; P campo | É administração/supervisão do PWA, não a navegação do app Campo. |
| 43-48 | Backoffice / Visão, Comercial, Financeiro, Suporte, Cadastros, Configuração | Dashboard/BI; assinantes/planos/módulos/cupons/CRM/IA; billing; chamados/KB; tabelas globais; sistema/ERP/usuários/perfis | SaaS | ADMINISTRAÇÃO | papel backoffice/superuser + P backoffice:* | Config canônica está no sidebar tenant; `AdminSidebar` é menu hardcoded duplicado sem RBAC e sem consumidor confirmado. |

Além da tabela: o sidebar cria **Geral/Dashboard**, **Gestão de Acessos** (Equipe, Perfis, Segurança, Sessões) e **Configurações** (Perfil, Produtor, Wizard, Globais, ERP, OpenWeather, Billing, IA, KB, SMTP, Suporte) diretamente no componente. Eles não constam de `sidebar-config.ts`.

## Rotas, duplicações e lacunas verificadas

- A correlação estática das 136 entradas com `apps/web/src/app` encontrou três links sem `page.tsx`: `/dashboard/pecuaria/manejos`, `/dashboard/pecuaria/vacinas` e `/dashboard/pecuaria/nutricao`. Existe `/dashboard/pecuaria/manejo`, no singular.
- Duplicações: `/cadastros/imoveis` (duas entradas), `/dashboard/rh/seguranca` (quatro entradas), Romaneios em Agricultura e Financeiro, e eSocial em Financeiro e RH.
- Não há entrada global explícita para Alert Engine; há somente alertas ambientais. Recomendações globais estão acopladas a Copiloto IA.
- Não há entrada clara no sidebar para comercialização geral, relatórios zootécnicos, rastreabilidade, arrendamentos ou auditoria, embora páginas/rotas de domínio existam.
- `getModuleFromPath`/`ModuleKey` conhecem A1, P1, F1, O1, RH, RH2, AM1 e Cadastros, mas não I1, O1-FROTA, IA1 ou CAMPO. Esses módulos não têm autoexpansão consistente por rota.

## Fluxos avaliados

### Implantação

O Wizard está escondido em Configurações; Core e Integrações ficam separados em locais diferentes. O caminho Empresa → Propriedades → Pessoas → Produtos → Integrações → prontidão não é apresentado como jornada.

### Agricultura

Há sequência parcial: Safras, planejamento, execução, monitoramento, colheita e resultados. Contudo, tarefas/Campo estão fora da jornada agrícola, Custeio fica em planejamento e recomendações globais ficam no Copiloto IA. Assim, `Safra → Planejamento → Orçamento` é visível, mas a continuidade operacional não é.

### Pecuária

A sequência real visível é Painel → Piquetes → Animais/Lotes → Planejamento de Manejos → Genética → Confinamento/Leite. Saúde e nutrição têm três links quebrados; portanto a jornada não é confiável.

### Gestão transversal

Estoque, Compras e Frota são grupos próprios, mas Estoque está protegido pelo add-on errado. Financeiro é transversal e bem separado. Integrações, Alertas e Recomendações não possuem posicionamento transversal claro.

## Comparação dos modelos

| Modelo | Pontos fortes | Limitações no AgroSaaS atual | Avaliação |
| --- | --- | --- | --- |
| A — camadas operacionais | Explica a jornada agrícola e onboarding. | Dilui Pecuária, Financeiro, Frota e Core; cria múltiplas entradas para capacidades transversais. | Não recomendado como navegação primária. |
| B — domínios | Aderente à arquitetura modular, RBAC e add-ons. | Pode ocultar a ordem de trabalho de Agricultura e Pecuária. | Melhor base, mas insuficiente sozinho. |
| C — híbrido | Mantém Core e capacidades transversais; permite jornada interna por domínio. | Exige separar configuração de navegação de regras de acesso e revisar gates. | **Recomendado.** |

## Árvore proposta (somente rotas existentes)

```text
VISÃO GERAL
- Dashboard

CORE
- Propriedades e território
- Pessoas e parceiros
- Produtos, serviços e tabelas
- Equipamentos (cadastro mestre)
- Imóveis rurais

OPERAÇÕES
- Agricultura
  - Safras
  - Planejamento e orçamento
  - Solo, clima e monitoramento
  - Tarefas, caderno e operações
  - Colheita e beneficiamento
  - Resultados agrícolas
- Pecuária
  - Painel, piquetes, animais e lotes
  - Planejamento de manejos, genética, confinamento e leite
- Suprimentos
  - Compras, fornecedores, estoque e requisições
- Frota e manutenção

GESTÃO
- Financeiro e comercialização
- Pessoas, RH e SST
- Ambiental, ESG e certificações
- Relatórios

INTELIGÊNCIA
- Recomendações operacionais
- Alertas
- IA e indicadores

PLATAFORMA
- Implantação
- Integrações ERP e clima
- Dispositivos Campo
- Equipe, permissões, segurança e configurações
- Administração SaaS (somente backoffice)
```

## Impactos e plano futuro

Mudanças somente de ordem/label: seções Agricultura, renomear “Copiloto IA” para “Inteligência”, agrupar Financeiro/Comercial, mover Wizard/Integrações para Plataforma e explicitar Equipamentos como cadastro mestre.

Mudanças estruturais: corrigir `moduleId` de Suprimentos, alinhar `IA_COPILOT` a `EXT_IA`, suportar gates por submódulo, revisar `ModuleKey/getModuleFromPath`, retirar ou integrar `AdminSidebar`, e criar destinos/retirar referências das três rotas Pecuária após auditoria funcional.

Riscos de regressão: usar gate de módulo inadequado pode ocultar capacidade contratada; alterar labels não deve tocar `href`; mover itens não pode trocar permission, tier ou `ModuleGate`; alerta/recomendação exigem confirmação de permissão backend; Campo deve permanecer PWA offline com navegação própria.

Arquivos candidatos para implementação futura: `sidebar-config.ts`, `app-sidebar.tsx`, `module-gate.tsx`, `constants/modulos.ts`, testes de navegação/RBAC, as três páginas Pecuária ou suas entradas, e documentação de rotas. Não devem ser alterados nesta auditoria.

## Validação

Foram verificados configuração, todos os consumidores da configuração, gates, filtros, sidebar mobile, navegação Campo e páginas Web por correlação estática. Nenhuma rota, permissão, plano, componente, backend ou banco foi alterado nesta execução.
