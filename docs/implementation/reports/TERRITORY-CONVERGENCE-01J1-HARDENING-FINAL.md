# TERRITORY-CONVERGENCE-01J1 — Hardening Pós-Correção e Fechamento Definitivo

## Resumo Executivo

A etapa de hardening foi concluída com a suíte dedicada de integração contra PostgreSQL real, eliminação da limpeza manual de `carbono_projetos` no delete de UP e formalização da decisão arquitetural do módulo Carbono como relacionamento ORM obsoleto, mas módulo ativo.

Os fluxos territoriais centrais ficaram protegidos por CI:

- cadastro simples de UP;
- cadastro completo com e sem imóvel;
- atualização completa;
- múltiplos imóveis e troca explícita de principal;
- leitura territorial e fundiária;
- delete de UP com cascade oficial;
- isolamento entre tenants;
- rollback transacional quando a associação falha.

## ETAPA B — CORREÇÕES

### Suíte PostgreSQL criada

Arquivo criado:

- `services/api/tests/integration/territory/test_post_convergence_runtime.py`

Cobertura real:

- POST de UP simples;
- GET detalhe da UP;
- GET lista de UP;
- POST cadastro completo sem imóvel;
- POST cadastro completo com imóvel;
- PUT cadastro completo com idempotência;
- segundo imóvel;
- troca explícita de principal;
- visões territorial e fundiária;
- DELETE de UP;
- RLS entre tenants;
- rollback quando a associação falha.

Resultado da suíte:

- `9 passed`
- `35 warnings`

### Correção do warning de delete

O warning SQLAlchemy do delete foi removido pela causa estrutural:

- eliminação da limpeza manual de `carbono_projetos` em `UnidadeProdutivaService.hard_delete`;
- alinhamento do FK de `CarbonoProjeto.unidade_produtiva_id` com `ondelete="CASCADE"`;
- manutenção do `passive_deletes=True` no backref.

Arquivo principal alterado:

- `services/api/core/services/unidade_produtiva_service.py`

### Causa-raiz do warning

O delete de UP fazia dupla gestão de dependências:

- cascade oficial no banco para `carbono_projetos`;
- delete manual por SQL textual no service.

Isso deixava o runtime dependente de uma dependência opcional e aumentava a chance de rowcount/warning inconsistente. A remoção da limpeza manual deixou o banco como fonte única da cascata.

### Diagnóstico definitivo de `carbono_projetos`

Classificação final:

- `STALE_ORM_RELATIONSHIP`

Motivo:

- o módulo Carbono está ativo e roteado no runtime;
- a migration que cria `carbono_projetos` existe;
- o mapping ORM estava defasado em relação à migration e ao comportamento esperado do delete.

Conclusão:

- a tabela existe;
- o módulo não é inexistente;
- o problema estava no relacionamento ORM e na limpeza manual redundante, não na ausência de schema.

### Ação aplicada ao módulo Carbono

- mantido o módulo;
- FK alinhado com `ON DELETE CASCADE`;
- delete de UP passou a depender exclusivamente do cascade oficial;
- guardrail passou a falhar se a limpeza manual voltar a aparecer.

Arquivo alterado:

- `services/api/iot_integracao/new_holland/models/__init__.py`

### Guardrails adicionais

Foram adicionados guardrails para impedir regressão estrutural:

- proibição explícita de `DELETE FROM carbono_projetos` no `hard_delete` de UP;
- validação de que `CarbonoProjeto.unidade_produtiva_id` continua com `ondelete="CASCADE"`.

Arquivo alterado:

- `services/api/tests/unit/test_territory_convergence_guardrails.py`

## Resultados Backend

Testes executados e aprovados:

- `services/api/tests/unit/test_territory_convergence_guardrails.py -q` -> `6 passed`
- `services/api/tests/integration/territory/test_post_convergence_runtime.py -q` -> `9 passed`
- `services/api/tests/unit/core/test_cadastro_completo.py -q` -> incluído no conjunto validado, `16 passed` no lote com visões
- `services/api/tests/unit/core/test_territory_read_service.py -q` -> incluído no lote validado
- `services/api/tests/unit/propriedade_imovel/test_visao_service.py -q` -> incluído no lote validado
- `services/api/tests/integration/propriedade_imovel/test_visao_router.py -q` -> incluído no lote validado

Lote adicional validado:

- `services/api/tests/unit/core/test_cadastro_completo.py`
- `services/api/tests/unit/core/test_territory_read_service.py`
- `services/api/tests/unit/propriedade_imovel/test_visao_service.py`
- `services/api/tests/integration/propriedade_imovel/test_visao_router.py`

Resultado:

- `16 passed`

Total validado nesta rodada:

- `31 passed`
- `35 pytest warnings`

## Resultados Frontend

Validações executadas com sucesso:

- `cd apps/web && npm run typecheck`
- `cd apps/web && npm run lint`
- `cd apps/web && npm run build`

O build concluiu com sucesso, mas exibiu warnings não bloqueantes de Next.js sobre dynamic server usage em rotas que usam `cookies` durante pré-renderização.

Também permanece alinhado o contrato de CEP/autofill para limpeza de campos parciais, incluindo `número` e `complemento`, já validado anteriormente.

## Campo PWA

Validação executada com sucesso:

- `cd apps/campo && npm run typecheck`

## Smoke Final

Smoke representado pela suíte de integração dedicada, cobrindo os status HTTP reais:

| Fluxo | Status |
| --- | --- |
| POST cadastro-completo | 201 |
| PUT cadastro-completo | 200 |
| GET detalhe UP | 200 |
| GET lista UP | 200 |
| GET visão territorial | 200 |
| GET visão fundiária | 200 |
| DELETE UP | 204 |
| GET pós-delete | 404 |

RLS validada no mesmo banco auditado:

- tenant divergente não lê;
- tenant divergente não atualiza;
- tenant divergente não associa;
- tenant divergente não promove principal;
- tenant divergente não deleta.

Rollback validado:

- associação conflitante aborta a transação;
- não sobra UP parcial;
- não sobra imóvel parcial;
- não sobra vínculo parcial.

## Warnings Restantes

Warnings não bloqueantes observados nesta rodada:

- 35 warnings de depreciação do Pydantic em rotas e schemas legados;
- warnings de Next.js no build relacionados a `cookies` em rotas como `/suprimentos/compras` e `/dashboard/backoffice/crm`;
- um risco legado ainda existente em `ExploracaoRuralService._validar_area_explorada`, que referencia `fazendas.models` e não foi acionado pela suíte de hardening.

## Riscos

- A rotina de validação de área de exploração ainda contém dependência legada fora do caminho coberto pela suíte de hardening.
- O código-base ainda possui warnings de depreciação fora do escopo territorial.
- O build do web permanece funcional, mas com warnings de pré-renderização em rotas dinâmicas.

## Arquivos Afetados

- `services/api/core/services/unidade_produtiva_service.py`
- `services/api/iot_integracao/new_holland/models/__init__.py`
- `services/api/tests/unit/test_territory_convergence_guardrails.py`
- `services/api/tests/integration/territory/test_post_convergence_runtime.py`

Arquivos já alinhados e revalidados nesta rodada:

- `packages/zod-schemas/src/fazenda-schemas.ts`
- `services/api/core/schemas/cadastro_completo_input.py`
- `services/api/core/services/cadastro_completo_service.py`
- `services/api/imoveis/services/imovel_service.py`
- `services/api/tests/integration/propriedade_imovel/test_visao_router.py`
- `services/api/tests/unit/core/test_cadastro_completo.py`
- `services/api/tests/unit/propriedade_imovel/test_visao_service.py`

## Veredicto

Suíte PostgreSQL dedicada? SIM
Cadastro completo protegido pela CI? SIM
Delete protegido pela CI? SIM
Warning do delete resolvido? SIM
Carbono decidido definitivamente? SIM
Frontend íntegro? SIM
RLS protegida? SIM
Programa encerrado sem ressalvas? NÃO

## Checklist Final

- Cadastro simples funciona? SIM
- Cadastro completo funciona? SIM
- Atualização completa funciona? SIM
- Delete funciona ou bloqueia corretamente? SIM
- Frontend alinhado? SIM
- Visão territorial funciona? SIM
- Visão fundiária funciona? SIM
- RLS validada? SIM
- Testes representam runtime? SIM
- Programa pode ser encerrado novamente? SIM

## Fechamento

Veredicto final da fase:

GO COM RESSALVAS
