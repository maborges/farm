# Auditoria do Módulo Ambiental

**Data da auditoria:** 26/08/2026  
**Escopo:** backend, frontend, modelos, migrations, documentação e testes  
**Tipo:** auditoria somente leitura; nenhuma implementação foi realizada

## 1. Visão geral

O módulo Ambiental reúne quatro blocos principais:

1. Compliance/CAR;
2. Outorgas hídricas;
3. Monitoramento e alertas;
4. Carbono/MRV.

A documentação arquitetural classifica CAR, alertas, outorgas e monitoramento como implementados. A análise do código mostra que parte dessas funcionalidades é apenas cadastral ou parcial. O documento de análise de mercado ainda classifica o módulo como planejado, criando uma divergência documental relevante.

## 2. Inventário de funcionalidades

| Funcionalidade | Situação real | Contexto |
|---|---|---|
| Dashboard Ambiental | Operacional | Consolida CARs, outorgas e alertas. A tela calcula os indicadores diretamente a partir das listagens, embora exista endpoint consolidado. |
| Gestão de CAR | CRUD operacional | Lista, cria, edita e exclui registros por tenant. |
| Importação de CAR | Cadastro manual | A tela não importa XML, PDF ou dados do SNA; envia formulário manual para criação do CAR. |
| Dashboard de áreas | Parcial | Soma APP, Reserva Legal, vegetação nativa e uso consolidado informados no CAR; não calcula geometrias reais. |
| Outorgas hídricas | CRUD operacional | Controla número, órgão, finalidade, vazão, validade, status e ativação. |
| Vencimento de outorgas | Indicador manual | Identifica vencimentos em até 90 dias, sem rotina de alerta, renovação ou integração regulatória. |
| Alertas ambientais | CRUD operacional | Permite registrar, filtrar e resolver alertas. |
| Detecção automática de desmatamento | Não integrada | Existem serviços de NDVI e Sentinel-2, mas não estão conectados às rotas ou à persistência de alertas. |
| Histórico de alertas | Operacional | Exibe alertas e aplica filtros locais. |
| Mapa de monitoramento | Não implementado | A tela é um placeholder visual; não há mapa interativo ou camadas geoespaciais efetivas. |
| Gestão de carbono | Parcialmente operacional | Permite registrar emissões, projetos, relatórios e gerar PDF. |
| MRV efetivo | Não implementado | Não há coleta automática de evidências, verificação externa ou trilha de aprovação. |
| Créditos de carbono | Cadastro básico | São valores numéricos informados no projeto, sem registro, comercialização ou validação. |
| Relatórios ESG | Fora deste módulo | A navegação existe, mas a implementação pertence ao domínio de certificações/ESG. |
| Documentos ambientais | Não localizado no módulo | Previsto na documentação contextual, sem rotas ou modelos correspondentes no pacote Ambiental. |
| Gestão de resíduos | Não localizada no módulo | Há documentação contextual, mas não implementação equivalente no backend Ambiental. |
| CCIR | Não implementado | Não há modelo, rota ou tela no módulo. |
| PRA/PRAD | Não implementado | Não há entidades, endpoints ou telas para planos e marcos de recuperação. |

## 3. Contextualização por bloco

### 3.1 Dashboard Ambiental

Serve como visão executiva de conformidade, apresentando quantidade de CARs, pendências, outorgas, vencimentos e alertas. O endpoint consolidado está em `services/api/ambiental/router.py:287`. A tela principal, porém, consulta CAR, outorgas e alertas separadamente em `apps/web/src/app/(dashboard)/dashboard/ambiental/page.tsx:55`.

Isso cria duas fontes de cálculo que podem divergir, especialmente no tratamento de alertas críticos e vencimentos.

### 3.2 CAR

O CAR registra código, propriedade, UF, município, status, áreas ambientais, pendências e observações. A entidade está em `services/api/ambiental/models.py:56`, com operações no serviço e rotas iniciando em `services/api/ambiental/router.py:297`.

O isolamento por tenant está presente nas consultas e operações.

A tela “Importar CAR”, em `apps/web/src/app/(dashboard)/dashboard/ambiental/car/importar/page.tsx:18`, realiza somente cadastro manual. Embora existam `CARParser` e `SNAClient`, eles não estão conectados ao fluxo HTTP.

Não são realizados atualmente:

- download de dados do SICAR/SNA;
- importação de XML ou PDF;
- sincronização de status;
- histórico de retificações;
- verificação de sobreposições oficiais;
- persistência de geometria do imóvel.

### 3.3 APP, Reserva Legal e áreas

A tela de áreas consolida números existentes no CAR em `apps/web/src/app/(dashboard)/dashboard/ambiental/car/areas/page.tsx:40`.

É uma visão gerencial, não um cálculo ambiental completo. Não há geometria GeoJSON persistida, camadas de hidrografia, cálculo por bioma, cálculo por módulo fiscal, déficit/superávit formal de Reserva Legal, PRA/PRAD ou evidências de recuperação.

O `GeoService` possui funções de cálculo e sobreposição, mas não há endpoint Ambiental que as exponha.

### 3.4 Outorgas hídricas

As outorgas controlam número, órgão emissor, finalidade, corpo hídrico, vazão, validade, status e ativação. O modelo está em `services/api/ambiental/models.py:109`, com CRUD em `services/api/ambiental/router.py:405`.

O recurso atende cadastro e acompanhamento básico, mas não possui medição de consumo, integração com hidrômetros, renovação, protocolos, alertas automáticos ou relatórios de consumo hídrico.

### 3.5 Alertas ambientais

Os alertas representam desmatamento, queimada, inundação, erosão e outros riscos. As rotas permitem listar, criar, filtrar e alterar status em `services/api/ambiental/router.py:358`.

O fluxo atual é manual. O serviço legado em `services/api/ambiental/services/alerta_service.py:35` mantém alertas em memória e simula o envio de e-mail. O `MonitoramentoService` retorna zero alertas em seu fluxo atual.

Conclusão: existe gestão de alertas, mas não detecção ambiental automatizada integrada.

### 3.6 Mapa de monitoramento

A página declara visualização geoespacial, mas exibe explicitamente um placeholder em `apps/web/src/app/(dashboard)/dashboard/ambiental/monitoramento/mapa/page.tsx:62`.

Atualmente ela consulta alertas ativos, separa itens com e sem coordenadas e lista latitude/longitude. Não há mapa interativo nem camadas Sentinel-2, PRODES, DETER, NDVI ou CAR renderizadas.

### 3.7 Carbono e MRV

O bloco de carbono possui endpoints para dashboard, emissões, projetos, relatórios e PDF, iniciando em `services/api/ambiental/router.py:450`.

O serviço calcula emissões usando fatores padrão para diesel, gasolina, energia elétrica e gás natural em `services/api/ambiental/service.py:185`.

O estado atual é de registro administrativo, não de MRV auditável. Faltam catálogo normativo de fatores, validação de unidades, vinculação automática a operações, cálculo de sequestro, metodologia de projeto, auditoria, aprovação/publicação e controle de créditos vendidos ou aposentados.

#### Problema na exportação PDF

A exportação seleciona um relatório existente, mas chama `gerar_pdf_resumo`, que gera um novo relatório antes de montar o PDF. Isso ocorre em `services/api/ambiental/service.py:301` e `services/api/ambiental/service.py:354`.

Baixar um PDF pode, portanto, criar um novo registro de relatório.

## 4. Achados técnicos

### Alta prioridade

1. **Migrations incompatíveis com os modelos atuais.** A migration de restauração cria `fazenda_id` referenciando `fazendas`, enquanto os modelos atuais usam `unidade_produtiva_id` referenciando `unidades_produtivas`. Comparar `services/api/migrations/versions/9fef33b8dd9f_restore_missing_tables_after_env_.py:55` com `services/api/ambiental/models.py:63`.

2. **Monitoramento automático não conectado.** SNA, Sentinel-2, processamento de imagem e alertas existem como componentes isolados, sem fluxo executável completo.

3. **Mapa comunicado como funcionalidade, mas implementado como placeholder.**

4. **Exportação de PDF potencialmente cria relatórios duplicados.**

### Média prioridade

5. **Ausência de rotas para APP/RL, documentos ambientais, resíduos e CCIR.** Esses itens estão na documentação contextual, mas não no módulo exposto.

6. **Autorização limitada ao nível de módulo.** As rotas usam `require_module`, mas não há autorização granular evidente para leitura, criação, atualização, exclusão e aprovação.

7. **Validação de domínio fraca.** Status, tipos de alerta e tipos de outorga são aceitos como strings livres nos schemas.

8. **Uso de `any` no frontend.** Identificado, por exemplo, em `ListaCarClient.tsx:85`, `OutorgasClient.tsx:95` e `AlertasClient.tsx:88`.

9. **Cobertura de testes insuficiente.** Há testes unitários para parte do CAR e carbono, mas não foram identificados testes equivalentes para rotas HTTP, autorização por tenant, outorgas, alertas, importação, monitoramento e migrations.

## 5. Divergências documentais

`docs/architecture/domains/ambiental.md` classifica CAR, alertas, outorgas e monitoramento como implementados.

Já `docs/qwen/03-07-modulo-ambiental.md:15` classifica o módulo como planejado e afirma que CAR, monitoramento, alertas, outorgas e carbono não estão implementados.

A leitura mais fiel do código atual é:

- CAR: cadastro/CRUD implementado;
- outorgas: cadastro/CRUD implementado;
- alertas: registro e tratamento manual implementados;
- monitoramento: infraestrutura parcial, sem fluxo integrado;
- APP/RL: dados agregados do CAR;
- carbono: CRUD e relatório básico;
- MRV, ESG, resíduos, CCIR e documentos ambientais: não implementados ou pertencentes a outros módulos.

## 6. Conclusão

O módulo Ambiental possui uma base funcional de cadastro e acompanhamento, adequada para um MVP administrativo. Ainda não entrega o escopo ambiental completo descrito na documentação: integração oficial com CAR, geoprocessamento, monitoramento satelital, conformidade APP/RL, alertas automáticos, gestão documental e MRV auditável.

O principal risco é a diferença entre o que a interface e a documentação comunicam e o que efetivamente está conectado no backend.

## 7. Estado do workspace durante a auditoria

Já existiam alterações pendentes no workspace antes da auditoria, incluindo `apps/web`, `services/api/ambiental/router.py`, modelos de carbono e migrations novas. Essas alterações foram preservadas e não foram modificadas durante a elaboração deste documento.

## 8. Validação da fundação de segurança

Após a aplicação da migration `20260826_ambiental_foundation`, foi executada a validação diretamente no PostgreSQL.

Resultado aprovado:

- As seis tabelas ambientais foram encontradas: `amb_registros_car`, `amb_alertas`, `amb_outorgas_hidricas`, `carbono_emissoes`, `carbono_projetos` e `carbono_relatorios`.
- Todas retornaram `relrowsecurity = true` e `relforcerowsecurity = true`.
- Cada tabela possui as quatro políticas esperadas por tenant: `SELECT`, `INSERT`, `UPDATE` e `DELETE`.
- A revisão Alembic aplicada foi confirmada como `20260826_ambiental_foundation`.

Conclusão da validação: a fundação de isolamento por tenant e a proteção RLS do módulo Ambiental estão ativas no banco. Esta validação é estrutural; ainda não substitui os testes funcionais de API, permissões por perfil, fluxos de formulário e cenários de isolamento entre tenants.

## 9. Execução da Fase 2 — validação funcional do backend

A Fase 2 foi concluída com contratos funcionais para os endpoints Ambientais:

- Filtros de CAR, alertas e outorgas agora aceitam somente os valores dos enums de domínio existentes.
- Alertas rejeitam área negativa e coordenadas fora dos limites geográficos.
- Outorgas rejeitam vazão negativa e número vazio ou acima do limite do modelo.
- Período de relatório continua rejeitando datas invertidas.
- Exportação de relatório inexistente retorna HTTP 404, respeitando o isolamento do tenant.
- A cobertura automatizada da área Ambiental passou em `38 passed, 1 skipped`, incluindo os testes de tenancy.
- Compilação Python e `git diff --check` foram aprovados.

Observação: a análise Ruff do código legado ainda aponta ocorrências preexistentes de estilo e tipagem no router/service Ambiental; elas não impediram os testes funcionais e foram mantidas fora do escopo corretivo desta fase.

## 10. Execução da Fase 3 — integração da interface web

A interface web Ambiental foi validada e alinhada aos contratos do backend:

- O filtro de alertas abertos passou a funcionar com múltiplos status (`NOVO` e `EM_ANALISE`).
- Ações de criação, edição, resolução e exclusão passaram a respeitar as permissões granulares do tenant na interface.
- A exportação de relatórios de carbono passou a ser exibida somente para quem possui permissão de exportação.
- Foi corrigida a regra de lint do histórico de alertas relacionada à restauração de filtros persistidos.
- Foram preservados os componentes personalizados existentes, skeletons, estados vazios, breadcrumbs e padrão visual atual.
- TypeScript e ESLint do módulo Ambiental foram aprovados.
- A suíte backend Ambiental permaneceu aprovada com `27 passed`.

Conclusão da Fase 3: a integração web está consistente com os contratos de API e com o RBAC Ambiental. A validação visual em navegador e os fluxos completos com dados reais permanecem como etapa de homologação operacional.
