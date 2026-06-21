# EXECUTION-01B — Saneamento da Fase 0 da Convergência Propriedades x Imóveis Rurais

Data de execução: 2026-06-21

## 1. Worktree

### Comandos executados

- `git status --short`
- `git branch --show-current`

### Resultado

- Branch atual: `main`
- Status do repositório: **não limpo**

### Classificação das alterações

| Item | Classificação | Observação |
|---|---|---|
| `docs/architecture/agrosaas-ai-rules.md` | Documentação arquitetural já esperada | Faz parte da camada normativa tocada pela convergência |
| `docs/architecture/agrosaas-data-model.md` | Documentação arquitetural já esperada | Atualização coerente com a linha de trabalho |
| `docs/architecture/agrosaas-domain-map.md` | Documentação arquitetural já esperada | Efeito colateral esperado da convergência documental |
| `docs/architecture/agrosaas-master-context.md` | Documentação arquitetural já esperada | Atualização de contexto |
| `docs/architecture/agrosaas-routing-map.md` | Documentação arquitetural já esperada | Atualização operacional esperada |
| `docs/analysis/` | Relatórios de implementação | Diretório novo esperado para a trilha de execução |
| `docs/architecture/adr/` | Relatórios / ADRs | Diretório novo esperado para decisão arquitetural |
| `docs/architecture/agrosaas-territorial-canonical-model.md` | Documentação arquitetural já esperada | Documento canônico da trilha territorial |
| `docs/architecture/domains/` | Documentação de domínio | Diretório novo esperado |
| `docs/architecture/governance/` | Documentação de governança | Diretório novo esperado |
| `docs/architecture/standards/` | Normas arquiteturais | Diretório novo esperado |
| `docs/implementation/` | Relatórios e tickets | Diretório novo esperado |
| `services/api/ia/ux_telemetry_service.py` | Código não relacionado | Alteração funcional em serviço de IA fora do escopo da convergência |
| `apps/web` | Alteração suspeita / submodule dirty | O subprojeto está marcado como `dirty` e precisa ser inspecionado separadamente |

### Recomendação operacional

- Comitar a documentação arquitetural em trilha separada.
- Criar branch específica para a convergência, se ainda não existir.
- Stashear ou isolar alterações não relacionadas antes de qualquer execução técnica.
- Não avançar para implementação com o worktree atual.

---

## 2. RLS

### Evidências encontradas

- `TenantRLSMiddleware` em [services/api/main.py](/opt/lampp/htdocs/farm/services/api/main.py)
- `SET LOCAL app.current_tenant_id = ...` em [services/api/core/dependencies.py](/opt/lampp/htdocs/farm/services/api/core/dependencies.py)
- Regras normativas explícitas em [docs/architecture/agrosaas-ai-rules.md](/opt/lampp/htdocs/farm/docs/architecture/agrosaas-ai-rules.md)
- Referência estratégica em [docs/architecture/agrosaas-master-context.md](/opt/lampp/htdocs/farm/docs/architecture/agrosaas-master-context.md)

### Verificação textual em migrations

- Não foi encontrada evidência textual de:
  - `ENABLE ROW LEVEL SECURITY`
  - `CREATE POLICY`
  - `FORCE ROW LEVEL SECURITY`

### Conclusão

- Existe isolamento por aplicação, sim.
- RLS físico no banco não foi evidenciado nesta varredura.
- A implementação atual depende de middleware + sessão com `SET LOCAL app.current_tenant_id`.

### Tabelas que devem ter policy explícita quando a convergência avançar

- `unidades_produtivas`
- `cadastros_areas_rurais`
- `cadastros_areas_matriculas`
- `cadastros_areas_registros_ambientais`
- `cadastros_arquivos_geo`
- `cadastros_areas_valores_patrimoniais`
- `imoveis_cartorios`
- `imoveis_rurais`
- `imoveis_matriculas`
- `imoveis_documentos`
- `imoveis_documentos_historico`
- `imoveis_arrendamentos`
- `imoveis_arrendamento_parcelas`
- `imoveis_arrendamento_reajustes`
- `imoveis_benfeitorias`
- `imoveis_avaliacoes`
- futura `propriedade_imovel`

### Resposta objetiva

- Existe RLS físico no banco? **Não evidenciado**
- Existe apenas isolamento por aplicação? **Sim, por evidência textual**
- A futura `propriedade_imovel` deve ter RLS físico? **Sim**

---

## 3. Duplicidade fundiária

### Tabela de consolidação

| Campo | Localização atual em Propriedades | Localização atual em Imóveis Rurais | Fonte oficial futura | Ação recomendada |
|---|---|---|---|---|
| CAR | `AreaRural.codigo_car`; `MatriculaImovel.car_numero`; `RegistroAmbiental.tipo_registro = CAR_APP/CAR_RL` | `ImovelRural.car_numero`; `MatriculaImovelRural.car_numero`; `DocumentoLegal.tipo = CAR` | Imóveis Rurais | Migrar e espelhar somente leitura em Propriedades |
| CCIR | `AreaRural.ccir`; `MatriculaImovel.ccir` | `ImovelRural.ccir_numero`; `MatriculaImovelRural.ccir`; `DocumentoLegal.tipo = CCIR` | Imóveis Rurais | Migrar e espelhar somente leitura em Propriedades |
| ITR | `MatriculaImovel.itr_numero` | `DocumentoLegal.tipo = ITR_DITR` | Imóveis Rurais | Migrar / centralizar em Imóveis Rurais |
| NIRF | `AreaRural.nirf`; `MatriculaImovel.nirf` | `ImovelRural.nirf`; `MatriculaImovelRural.nirf`; `DocumentoLegal.tipo = ITR_DITR` como suporte fiscal | Imóveis Rurais | Migrar e espelhar somente leitura em Propriedades |
| SIGEF | `AreaRural.sigef_codigo`; `UnidadeProdutiva.sigef_codigo` | Não modelado explicitamente no trecho analisado; associado ao lastro fundiário/documental | Imóveis Rurais | Migrar para Imóveis Rurais e espelhar somente leitura até a migração |
| Matrícula | `MatriculaImovel.numero_matricula` | `ImovelRural.numero_matricula`; `MatriculaImovelRural.numero_matricula`; `DocumentoLegal.tipo = MATRICULA` | Imóveis Rurais | Migrar e depreciar a escrita em Propriedades |
| Cartório | `MatriculaImovel.cartorio`; `MatriculaImovel.comarca` | `ImovelRural.cartorio_id`; `MatriculaImovelRural.cartorio_id`; `MatriculaImovelRural.cartorio_nome` | Imóveis Rurais | Migrar e espelhar somente leitura em Propriedades |
| Município | `AreaRural.municipio`; `UnidadeProdutiva.municipio` | `ImovelRural.municipio` | Imóveis Rurais | Espelhar somente leitura em Propriedades |
| UF | `AreaRural.uf`; `UnidadeProdutiva.uf` | `ImovelRural.uf`; `Cartorio.uf` | Imóveis Rurais | Espelhar somente leitura em Propriedades |
| Área total | `AreaRural.area_hectares`; `UnidadeProdutiva.area_total_ha` | `ImovelRural.area_total_ha`; `MatriculaImovelRural.area_matricula_ha` | Propriedades para operação; Imóveis Rurais para lastro legal | Manter em Propriedades e espelhar leitura em Imóveis Rurais |
| APP | `AreaRural.APP`; `UnidadeProdutiva.area_app_ha`; `RegistroAmbiental.tipo_registro = CAR_APP` | `ImovelRural.area_app_ha`; `DocumentoLegal` / `CAR` como prova | Compartilhado, com prova legal em Imóveis Rurais | Espelhar somente leitura |
| Reserva Legal | `AreaRural.RESERVA_LEGAL`; `UnidadeProdutiva.area_rl_ha`; `RegistroAmbiental.tipo_registro = CAR_RL` | `ImovelRural.area_rl_ha`; `DocumentoLegal` / `CAR` como prova | Compartilhado, com prova legal em Imóveis Rurais | Espelhar somente leitura |

### Resumo da ação por campo

- Manter em Propriedades: área operacional, talhões, glebas, produção e geometrias operacionais.
- Migrar para Imóveis Rurais: CAR, CCIR, ITR, NIRF, matrícula, cartório e SIGEF.
- Espelhar somente leitura: município, UF, área total, APP e Reserva Legal onde necessário.
- Depreciar: escrita fundiária em entidades territoriais legadas.
- Remover futuramente: campos fundiários duplicados do domínio operacional após a migração e estabilização.

---

## 4. Migrations históricas

### Migrations analisadas

- `services/api/migrations/versions/imoveis_rurais_init.py`
- `services/api/migrations/versions/43cdf769d080_fix_imoveis_broken_fks.py`
- `services/api/migrations/versions/fa37f6f94792_onda1_cadastros_normalizacao.py`
- `services/api/migrations/versions/c853a6f175f1_add_logo_url_to_unidades_produtivas.py`
- `services/api/migrations/versions/step1_migrate_talhoes_to_areas_rurais.py`
- `services/api/migrations/versions/step2_drop_talhoes_legado.py`
- `services/api/migrations/versions/4e0b633ffb18_onda4_limpeza_final.py`

### Tabelas criadas por essas migrações

- `imoveis_cartorios`
- `imoveis_rurais`
- `imoveis_matriculas`
- `imoveis_benfeitorias`
- `imoveis_documentos`
- `imoveis_documentos_historico`
- `imoveis_arrendamentos`
- `imoveis_arrendamento_parcelas`
- `imoveis_arrendamento_reajustes`
- `imoveis_avaliacoes`
- `cadastros_areas_rurais`
- `cadastros_areas_matriculas`
- `cadastros_areas_registros_ambientais`
- `cadastros_areas_valores_patrimoniais`
- `cadastros_infraestruturas`
- `cadastros_arquivos_geo`

### Campos já migrados antes

- Talhões foram consolidados em `cadastros_areas_rurais`.
- Vários FKs antigos baseados em `fazenda_id` foram reescritos para `unidade_produtiva_id`.
- O módulo de imóveis rurais já nasceu com `imoveis_rurais`, `imoveis_matriculas`, `imoveis_documentos`, `imoveis_arrendamentos`, `imoveis_avaliacoes` e suporte a cartório.

### Dependência de ordem de migration

- `step1_migrate_talhoes_to_areas_rurais.py` deve rodar antes de `step2_drop_talhoes_legado.py`.
- `step2_drop_talhoes_legado.py` aborta se ainda existirem FKs apontando para `talhoes`.
- `4e0b633ffb18_onda4_limpeza_final.py` já migra FKs de safras, operações e outros módulos para `cadastros_areas_rurais`.
- `c853a6f175f1_add_logo_url_to_unidades_produtivas.py` já consolida a nomenclatura `fazenda_id` para `unidade_produtiva_id` em várias tabelas.

### Risco de conflito com `propriedade_imovel`

- Não existe conflito direto com uma tabela ainda inexistente.
- Existe risco de ordem e nomenclatura se a futura migration assumir nomes antigos como `fazenda_id` ou modelos legados.
- A futura migration deve ser planejada após o estado atual do schema, usando os nomes já consolidados.

---

## 5. Tenant isolation em entidades filhas

| Entidade | tenant_id direto? | Depende de pai com tenant_id? | Risco de bypass | Recomendação futura |
|---|---|---|---|---|
| `MatriculaImovel` | Não evidenciado | Sim, via `AreaRural` | Médio/alto | Adicionar proteção contextual e evitar escrita fora do fluxo pai |
| `RegistroAmbiental` | Não evidenciado | Sim, via `AreaRural` | Médio/alto | Mesma regra de proteção do pai |
| `Infraestrutura` | Sim | Sim, via `AreaRural` | Baixo | Manter `tenant_id` direto |
| `ArquivoGeo` | Sim | Sim, via `AreaRural` | Baixo | Manter `tenant_id` direto |
| `ValorPatrimonial` | Não evidenciado | Sim, via `AreaRural` | Médio/alto | Garantir tenant explícito na camada de persistência/serviço |
| `MatriculaImovelRural` | Sim | Sim, via `ImovelRural` | Baixo | Manter `tenant_id` direto |
| `DocumentoLegal` | Sim | Sim, via `ImovelRural` | Baixo | Manter `tenant_id` direto |
| `ContratoArrendamento` | Sim | Sim, via `ImovelRural` e `UnidadeProdutiva` | Baixo | Manter `tenant_id` direto |
| `AvaliacaoImovel` | Sim | Sim, via `ImovelRural` | Baixo | Manter `tenant_id` direto |

### Leitura técnica

- As entidades filhas do domínio fundiário já estão melhor protegidas do que as filhas do domínio territorial legadas.
- O principal ponto de atenção continua sendo o bloco `cadastros_areas_*`, onde `MatriculaImovel`, `RegistroAmbiental` e `ValorPatrimonial` dependem do pai sem `tenant_id` direto aparente.
- Para a convergência futura, a nova `propriedade_imovel` deve ter `tenant_id` direto e política física de RLS.

---

## 6. Conclusão de saneamento

### Os bloqueios da Fase 0 foram esclarecidos?

- **Sim, esclarecidos e classificados.**

### O worktree permite avançar?

- **Não permite avançar para implementação.**
- Permite avançar apenas para a Fase 1 em modo documental / de modelagem, desde que a equipe trate o worktree como não confiável para mudanças técnicas.

### A estratégia de RLS está clara?

- **Sim, como isolamento por aplicação com `TenantRLSMiddleware` + `SET LOCAL app.current_tenant_id`.**
- **Não, como RLS físico comprovado em policy PostgreSQL.**

### A duplicidade fundiária está mapeada campo a campo?

- **Sim.**

### As migrations históricas foram compreendidas?

- **Sim.**

### O tenant isolation das entidades filhas foi classificado?

- **Sim.**

### Pode avançar para Fase 1 — Data Model?

- **Sim, para a modelagem documental e para a definição conceitual do Data Model.**
- **Não, para implementação técnica ou criação de migration da convergência, até o worktree ser separado e a estratégia de RLS físico ser formalizada.**

---

## 7. Recomendação final

- Criar ou limpar branch dedicada antes de qualquer implementação.
- Manter a Fase 1 como atividade de modelagem e documentação.
- Não iniciar migration nem backend enquanto o worktree atual continuar misturado com alterações não relacionadas.
- Registrar, em seguida, a decisão de RLS físico para `propriedade_imovel` e para as tabelas críticas do domínio.

