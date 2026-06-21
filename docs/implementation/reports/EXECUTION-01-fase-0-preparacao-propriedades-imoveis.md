# EXECUTION-01 — Fase 0 da Convergência Propriedades x Imóveis Rurais

Data de execução: 2026-06-21

## 1. Branch atual e status do repositório

### Branch

- Branch atual: `main`

### Status do repositório

O repositório **não está em base limpa** no momento da execução.

Principais alterações já presentes no worktree:

- `m apps/web`
- `M docs/architecture/agrosaas-ai-rules.md`
- `M docs/architecture/agrosaas-data-model.md`
- `M docs/architecture/agrosaas-domain-map.md`
- `M docs/architecture/agrosaas-master-context.md`
- `M docs/architecture/agrosaas-routing-map.md`
- `M services/api/ia/ux_telemetry_service.py`
- diretórios/documentos novos ainda não rastreados em `docs/analysis/`, `docs/architecture/adr/`, `docs/architecture/domains/`, `docs/architecture/governance/`, `docs/architecture/standards/` e `docs/implementation/`

### Leitura técnica

- A Fase 0 exige base limpa para reduzir risco de confundir diagnóstico com mudança pendente.
- Há mudanças pré-existentes no worktree que não fazem parte deste relatório e precisam ser separadas antes da implementação.

---

## 2. Migrations encontradas e riscos

### Caminho correto identificado

- As migrations do projeto estão em `services/api/migrations/versions`
- O caminho `services/api/alembic/versions` não existe neste repositório

### Migrations relevantes encontradas

- `services/api/migrations/versions/imoveis_rurais_init.py`
- `services/api/migrations/versions/43cdf769d080_fix_imoveis_broken_fks.py`
- `services/api/migrations/versions/fa37f6f94792_onda1_cadastros_normalizacao.py`
- `services/api/migrations/versions/c853a6f175f1_add_logo_url_to_unidades_produtivas.py`
- `services/api/migrations/versions/step2_drop_talhoes_legado.py`
- `services/api/migrations/versions/step1_migrate_talhoes_to_areas_rurais.py`
- `services/api/migrations/versions/4e0b633ffb18_onda4_limpeza_final.py`
- `services/api/migrations/versions/9be54904b80e_frota_apontamento_abastecimento_.py`

### Riscos observados

- `imoveis_rurais_init.py` confirma que o domínio fundiário já existe como tabela e pacote migratório próprio.
- `fa37f6f94792_onda1_cadastros_normalizacao.py` e outras migrations históricas mostram que `cadastros_areas_rurais` e `imoveis_rurais` já passaram por reestruturações e podem ter dependências indiretas.
- Há histórico de migração de talhões e de ajustes em tabelas de áreas rurais, o que aumenta o risco de regressão estrutural se a convergência for tratada sem revisão cuidadosa.
- Não foi encontrada, por varredura textual nas migrations, prova de políticas explícitas de RLS (`CREATE POLICY`, `ENABLE ROW LEVEL SECURITY`) para as tabelas de interesse.

---

## 3. Situação de RLS

### Evidência encontrada

- Existe middleware específico para extrair `tenant_id` do JWT:
  - [services/api/main.py](/opt/lampp/htdocs/farm/services/api/main.py)
- Existe injeção de tenant na sessão:
  - [services/api/core/dependencies.py](/opt/lampp/htdocs/farm/services/api/core/dependencies.py)

### O que o código faz

- `TenantRLSMiddleware` lê o `tenant_id` do token e o grava em `request.state.rls_tenant_id`.
- `get_session()` aplica `SET LOCAL app.current_tenant_id = '<tenant_id>'` quando o tenant foi resolvido.

### O que não foi evidenciado

- Não encontrei, nas migrations varridas, políticas explícitas de banco de dados para RLS.
- Portanto, a proteção está evidenciada na camada de aplicação, mas não houve prova textual da camada física de políticas PostgreSQL para as tabelas envolvidas.

### Classificação da situação

- **Parcial**

### Risco

- A solução depende de middleware + sessão para ativar o isolamento.
- Sem políticas explícitas no banco, a robustez fica mais dependente do caminho de acesso da aplicação.

---

## 4. Situação de `tenant_id`

### Entidades com `tenant_id` evidenciado

- `UnidadeProdutiva`
- `AreaRural`
- `ImovelRural`
- `MatriculaImovelRural`
- `DocumentoLegal`
- `ContratoArrendamento`
- `AvaliacaoImovel`

### Evidência direta nos modelos

- `AreaRural` possui `tenant_id` explícito:
  - [services/api/core/cadastros/propriedades/models.py](/opt/lampp/htdocs/farm/services/api/core/cadastros/propriedades/models.py)
- `ImovelRural` possui `tenant_id` explícito:
  - [services/api/imoveis/models/imovel.py](/opt/lampp/htdocs/farm/services/api/imoveis/models/imovel.py)
- `UnidadeProdutiva` possui `tenant_id` explícito:
  - [services/api/core/models/unidade_produtiva.py](/opt/lampp/htdocs/farm/services/api/core/models/unidade_produtiva.py)

### Lacunas importantes

- `MatriculaImovel` dentro de Propriedades não mostra `tenant_id` explícito no trecho analisado e depende apenas de `area_id`.
- `RegistroAmbiental` também está ancorado em `area_id`.
- Isso não invalida o isolamento funcional, mas deixa a proteção mais indireta do que nos modelos raiz.

### Classificação

- **Parcialmente adequada**

### Risco

- Entidades filhas sem `tenant_id` explícito podem dificultar auditoria e endurecimento futuro da convergência.

---

## 5. Campos fundiários duplicados

### Em Propriedades

`cadastros_areas_rurais` e entidades filhas carregam dados fundiários e legais:

- `codigo_car`
- `nirf`
- `ccir`
- `sigef_codigo`
- `area_total_ha`
- `area_app_ha`
- `area_rl_ha`
- `coordenadas_sede`
- `municipio`
- `uf`

`cadastros_areas_matriculas` também carrega:

- `numero_matricula`
- `cartorio`
- `comarca`
- `car_numero`
- `nirf`
- `incra`
- `ccir`
- `sncr`
- `itr_numero`

### Em Imóveis Rurais

`imoveis_rurais` carrega:

- `numero_matricula`
- `cartorio_id`
- `nirf`
- `car_numero`
- `ccir_numero`
- `area_total_ha`
- `area_aproveitavel_ha`
- `area_app_ha`
- `area_rl_ha`
- `municipio`
- `uf`
- `codigo_municipio_ibge`
- `latitude`
- `longitude`

### Duplicidades mais críticas

- `CAR`
- `CCIR`
- `ITR`
- `NIRF`
- `SIGEF`
- `matrícula`
- `cartório`
- `município`
- `UF`
- `área total`
- `APP`
- `Reserva Legal`

### Classificação

- **Duplicidade real e relevante**

### Risco

- Divergência entre fonte operacional e fonte fundiária.
- Ambiguidade para auditoria, certificações e rastreabilidade.

---

## 6. Rotas impactadas

### Backend

- `/api/v1/cadastros/areas-rurais`
- `/api/v1/cadastros/areas-rurais/{id}/matriculas`
- `/api/v1/cadastros/areas-rurais/{id}/registros-ambientais`
- `/api/v1/cadastros/areas-rurais/{id}/valores-patrimoniais`
- `/api/v1/imoveis`
- `/api/v1/imoveis/arrendamentos`
- `/api/v1/imoveis/avaliacoes`
- `/api/v1/rastreabilidade`

### Evidência de cobertura

- O domínio territorial é atendido por:
  - [services/api/core/cadastros/propriedades/router.py](/opt/lampp/htdocs/farm/services/api/core/cadastros/propriedades/router.py)
- O domínio fundiário é atendido por:
  - [services/api/imoveis/routers/imovel.py](/opt/lampp/htdocs/farm/services/api/imoveis/routers/imovel.py)
  - [services/api/imoveis/routers/arrendamento.py](/opt/lampp/htdocs/farm/services/api/imoveis/routers/arrendamento.py)
  - [services/api/imoveis/routers/avaliacao.py](/opt/lampp/htdocs/farm/services/api/imoveis/routers/avaliacao.py)

### Risco

- As rotas de Propriedades ainda expõem dados fundiários legados.
- As rotas de Imóveis Rurais já sustentam a verdade fundiária e podem conflitar com o legado enquanto a transição não for formalizada.

---

## 7. Telas impactadas

### Propriedades

- [apps/web/src/app/(dashboard)/cadastros/propriedades/page.tsx](/opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/cadastros/propriedades/page.tsx)
- [apps/web/src/app/(dashboard)/cadastros/propriedades/[id]/page.tsx](/opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/cadastros/propriedades/[id]/page.tsx)
- [apps/web/src/app/(dashboard)/cadastros/propriedades/talhoes/page.tsx](/opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/cadastros/propriedades/talhoes/page.tsx)
- [apps/web/src/app/(dashboard)/cadastros/propriedades/propriedades-client.tsx](/opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/cadastros/propriedades/propriedades-client.tsx)

### Imóveis Rurais

- [apps/web/src/app/(dashboard)/cadastros/imoveis/page.tsx](/opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/cadastros/imoveis/page.tsx)
- [apps/web/src/app/(dashboard)/cadastros/imoveis/ImoveisClient.tsx](/opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/cadastros/imoveis/ImoveisClient.tsx)
- [apps/web/src/app/(dashboard)/cadastros/imoveis/ArrendamentosClient.tsx](/opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/cadastros/imoveis/ArrendamentosClient.tsx)
- [apps/web/src/app/(dashboard)/cadastros/imoveis/avaliacoes/page.tsx](/opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/cadastros/imoveis/avaliacoes/page.tsx)

### Rastreabilidade

- [apps/web/src/app/(dashboard)/agricola/rastreabilidade/page.tsx](/opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/agricola/rastreabilidade/page.tsx)
- [apps/web/src/app/(dashboard)/dashboard/agricola/rastreabilidade/page.tsx](/opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/dashboard/agricola/rastreabilidade/page.tsx)

### Risco

- As telas já existem e são relevantes.
- O risco não é ausência de UI; é a semântica atual ainda misturar domínio operacional e fundiário em pontos legados.

---

## 8. Bloqueios encontrados

1. O worktree não está limpo.
2. As migrations existem e mostram histórico de reestruturação, o que exige revisão cuidadosa antes de qualquer implementação.
3. Não foi evidenciada política explícita de RLS em migrations para as tabelas analisadas.
4. `MatriculaImovel` e outras entidades filhas de Propriedades ainda carregam dados fundiários que o novo modelo pretende centralizar.
5. A convergência depende da decisão arquitetural já aprovada, mas ainda não existe implementação.

---

## 9. Recomendação para seguir ou não para a Fase 1

### Recomendação

- **Não avançar ainda para a Fase 1 — Data Model**

### Motivo

- A base de trabalho não está limpa.
- A proteção de RLS está parcialmente evidenciada, mas não validada em política física de banco.
- O mapeamento de duplicidades já confirmou conflito real de campos fundiários.
- Antes de modelar `PropriedadeImovel` no banco, é necessário estabilizar o diagnóstico e separar o worktree das alterações pendentes.

### O que precisa ser resolvido antes da Fase 1

- Limpar ou isolar as alterações já existentes no repositório.
- Confirmar explicitamente a estratégia de RLS no banco, não apenas no middleware.
- Consolidar a lista final de campos duplicados que serão migrados, mantidos ou deprecados.
- Validar o impacto das migrations históricas em Propriedades e Imóveis Rurais.

---

## Resposta final

### Fase 0 aprovada?

- **Não.**

### Pode avançar para Fase 1 — Data Model?

- **Não ainda.**

### Quais riscos precisam ser resolvidos antes?

- Base de trabalho suja.
- RLS sem evidência de política explícita de banco nas migrations analisadas.
- Duplicidade fundiária em Propriedades e Imóveis Rurais.
- Possível impacto colateral das migrations históricas.
- Necessidade de proteger a semântica de tenant isolation nas entidades filhas.

