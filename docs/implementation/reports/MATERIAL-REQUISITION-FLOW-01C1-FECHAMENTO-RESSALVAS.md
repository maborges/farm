# MATERIAL-REQUISITION-FLOW-01C1 — Fechamento das Ressalvas da Fundação

Data da validação: 2026-09-25  
Ambiente: PostgreSQL de desenvolvimento/teste, schema `farms`, PostgreSQL 16.15  
Escopo: migration, tenant/RLS, identidade operacional, registry e regressões diretamente relacionadas.  
Fora do escopo: picking, entrega canônica, recebimento no Campo, Dexie, sync offline, consumo, devolução operacional e CostAllocation.

## 1. Resumo executivo

O 01C1 fechou a principal ressalva do 01C: não existia vínculo canônico entre a conta autenticada `Usuario` e a `Pessoa` usada como operador/responsável.

Foi criada a associação contextual `PessoaUsuario`, tenant-scoped, com vigência, revogação e unicidade de identidade ativa. O histórico de responsabilidade passou a poder referenciar essa associação por `pessoa_usuario_id`. Também foi criado um serviço de resolução/autorização futura que não usa e-mail, CPF, nome ou igualdade acidental de UUIDs.

A migration foi validada em PostgreSQL real com upgrade, downgrade, inspeção e upgrade novamente. RLS, FKs compostas tenant-safe, unicidade ativa e isolamento foram testados. Não houve backfill de identidade, recebimento ou consumo histórico.

Veredicto: **GO COM RESSALVAS**.  
Autorização para 01D: **SIM**, limitada ao escopo de reserva/picking/entrega canônica, desde que 01D reutilize o serviço de identidade e não faça cutover do fluxo legado fora de seu plano aprovado.

## 2. Estado herdado do 01C

O 01C foi entregue como `GO COM RESSALVAS`. A fundação já continha:

- `RequisicaoItemEvento` append-only e idempotente;
- versionamento da requisição;
- origem operacional estruturada;
- snapshot `CONSUMIVEL`/`RETORNAVEL`;
- vínculo tenant-safe de `ReservaEstoque` ao item;
- referência opcional do ledger ao evento;
- classificação conservadora de legado;
- RLS e policies nas duas tabelas novas.

A ressalva bloqueante era a impossibilidade de provar que o `User` autenticado correspondia ao `Pessoa` responsável. A migration 01C também deixou `estoque_requisicoes_itens.tenant_id` sem FK direta para `tenants` e suas duas tabelas novas com FK direta `CASCADE`, fatos detectados pelos guardrails de tenant durante esta fase.

## 3. PostgreSQL utilizado para validação

Evidências:

- servidor PostgreSQL 16.15 Ubuntu;
- usuário conectado sem superuser e sem bypass de RLS;
- banco/schema `farms`;
- baseline antes do ciclo: `20260924_material_requisition_01c`;
- head final: `20260925_material_requisition_01c1`;
- conexão apontada para desenvolvimento, nunca produção.

## 4. Upgrade

Executado:

```text
20260924_material_requisition_01c
→ 20260925_material_requisition_01c1
```

Resultado final: PASS.

A migration criou `cadastros_pessoas_usuarios`, acrescentou `pessoa_usuario_id` a `estoque_requisicao_responsabilidades`, criou os índices/constraints/RLS e completou a FK direta de `estoque_requisicoes_itens.tenant_id`.

## 5. Downgrade

Executado:

```text
20260925_material_requisition_01c1
→ 20260924_material_requisition_01c
```

Resultado final: PASS.

Após o downgrade, foi confirmado:

- `cadastros_pessoas_usuarios` inexistente;
- `pessoa_usuario_id` inexistente no histórico de responsabilidades;
- FK `fk_estoque_requisicoes_itens_tenant` inexistente;
- head Alembic em `20260924_material_requisition_01c`.

O downgrade foi tornado tolerante aos nomes antigo e novo das FKs normalizadas, preservando reversibilidade após a evolução da migration.

## 6. Upgrade final

O upgrade foi reaplicado após o downgrade e terminou em PASS:

```text
20260924_material_requisition_01c
→ 20260925_material_requisition_01c1
```

Inspeção final:

- head: `20260925_material_requisition_01c1`;
- `cadastros_pessoas_usuarios`: presente;
- contagem de identidades: `0` — nenhum backfill especulativo;
- contagem de responsabilidades: `0` no ambiente de validação;
- FKs diretas para `tenants` das estruturas do fluxo: `RESTRICT`/`NO ACTION`;
- dados históricos de requisição preservados.

## 7. Migration histórica/offline

Arquivo auditado:

```text
services/api/migrations/versions/8c2e891d6ba9_caderno_campo.py
```

O `upgrade()` chama `op.get_bind()`, `sa.inspect(bind)` e `inspector.has_table(...)`. Em `alembic upgrade head --sql`, o bind é um `MockConnection`, gerando:

```text
sqlalchemy.exc.NoInspectionAvailable:
No inspection system is available for object of type MockConnection
```

Conclusão:

- afeta a geração SQL offline/static;
- o upgrade online normal no PostgreSQL atravessa essa migration;
- não foi observado bloqueio no deploy online PostgreSQL;
- a migration histórica não foi editada, para não reescrever história já aplicada;
- permanece dívida técnica de geração offline, fora do escopo 01C1.

## 8. RLS

As três estruturas tenant-scoped relevantes possuem RLS e `FORCE ROW LEVEL SECURITY`:

- `estoque_requisicao_item_eventos`;
- `estoque_requisicao_responsabilidades`;
- `cadastros_pessoas_usuarios`.

As policies usam o contexto:

```sql
tenant_id::text = NULLIF(current_setting('app.current_tenant_id', true), '')
```

Foram confirmadas policies de `SELECT`, `INSERT`, `UPDATE` e `DELETE`.

## 9. Tenant isolation

Testes PostgreSQL rollback-only com Tenant A e Tenant B:

- Tenant A lê a própria identidade: PASS;
- Tenant B não lê a identidade de A: PASS;
- Tenant B não altera nem remove a identidade de A: PASS — zero linhas afetadas;
- Tenant B não insere linha com `tenant_id` de A: PASS — RLS rejeita;
- Pessoa de B em relação contextual de A: PASS — FK composta rejeita;
- usuário de B em relação contextual de A: PASS — FK composta rejeita;
- identidade de evento/responsabilidade e reservas continuam com FKs compostas tenant-safe do 01C;
- unicidade `(tenant_id, usuario_id)` de `tenant_usuarios` foi formalizada para permitir a FK composta da identidade.

## 10. Append-only

O diário `RequisicaoItemEvento` continua protegido no PostgreSQL por:

- trigger `trg_estoque_requisicao_item_evento_append_only`;
- função `fn_estoque_requisicao_item_evento_append_only`;
- rejeição de `UPDATE` direto;
- rejeição de `DELETE` direto.

O 01C1 não torna `PessoaUsuario` append-only: identidade precisa poder ser revogada. O histórico da associação permanece preservado por status/vigência; o diário operacional continua imutável.

## 11. Idempotência

No evento por item, a constraint real continua sendo:

```text
UNIQUE (tenant_id, client_operation_id)
```

Foram validados no PostgreSQL:

1. primeira operação cria um evento;
2. retry com a mesma chave não cria segundo evento;
3. payload incompatível para a mesma chave é rejeitado;
4. mesma chave em outro tenant é independente;
5. duas conexões concorrentes não criam dois eventos.

O contrato de ACK futuro permanece baseado em `client_operation_id`; o 01C1 não implementa sync offline.

## 12. Versionamento

O agregado de requisição continua usando uma única versão monotônica. O teste real validou:

```text
v1 → evento → v2 → evento → v3
```

Comando baseado em versão obsoleta é rejeitado como conflito; não há atualização silenciosa. O 01C1 não criou uma segunda versão independente.

## 13. User ↔ Pessoa/Operador

Auditoria do código atual:

| Evidência | Estado encontrado |
|---|---|
| `core/models/auth.py :: Usuario` | identidade global; não possui `pessoa_id` |
| `core/models/auth.py :: TenantUsuario` | associação contextual User ↔ Tenant |
| `core/cadastros/pessoas/models.py :: Pessoa` | entidade tenant-scoped; não possuía User associado |
| `PessoaAcessoLog.usuario_id` | auditoria de acesso PII, não vínculo de identidade |
| `agricola/operacoes/models.py :: OperacaoAgricola.operador_id` | FK para `cadastros_pessoas.id` |
| `agricola/operacoes/models.py :: OperacaoExecucao.operador_id` | FK para `cadastros_pessoas.id` |
| `campo/models.py :: DispositivoCampo.user_id` | FK para `usuarios.id`; identifica a conta do dispositivo, não a Pessoa |
| `campo/models.py :: TarefaCampo.user_id/operador_id` | campos independentes; `operador_id` não possuía FK User/Pessoa |
| `campo/service.py` | havia fallback `task.operador_id or task.user_id`, sem prova de identidade |
| `apps/campo/.../tarefa/[id]/page.tsx` | filtro de interface; não mecanismo de autorização |

Não foi encontrado join canônico por e-mail, CPF ou nome. Essas informações continuam dados de identificação/PII e não são usadas como chave operacional.

## 14. Regra canônica de identidade operacional

Foi criada:

```text
PessoaUsuario
  tenant_id
  pessoa_id
  usuario_id
  status
  vigencia_inicio / vigencia_fim
```

Evidências:

- model: `services/api/core/cadastros/pessoas/models.py :: PessoaUsuario`;
- tabela: `farms.cadastros_pessoas_usuarios`;
- migration: `services/api/migrations/versions/20260925_material_requisition_01c1_identity.py`;
- resolver: `services/api/operacional/services/identidade_operacional_service.py :: IdentidadeOperacionalService`;
- testes unitários: `services/api/tests/unit/operacional/test_identidade_operacional_01c1.py`;
- teste PostgreSQL real: resolução User → Pessoa executada com transação revertida.

O vínculo é contextual ao Tenant, não global. Um `Usuario` global pode participar de vários tenants, e cada contexto pode ter sua própria `Pessoa`. Dentro do mesmo tenant, apenas uma relação ativa é permitida por usuário e por Pessoa.

O serviço também exige `TenantUsuario.status = ATIVO` e `Usuario.ativo = true`. A vigência é comparada com `CURRENT_TIMESTAMP` do banco para evitar divergência de relógio entre API e PostgreSQL.

## 15. Responsável/delegado

`RequisicaoResponsabilidadeHistorico` foi preservado e recebeu `pessoa_usuario_id` nullable para compatibilidade. Uma futura delegação canônica deverá apontar para:

```text
Tenant
→ PessoaUsuario ativo
→ Usuario autenticado
→ RequisicaoResponsabilidadeHistorico vigente
→ papel DELEGADO
```

O responsável direto é autorizado quando `PessoaUsuario.pessoa_id` coincide com `RequisicaoMaterial.responsavel_pessoa_id`. O delegado é autorizado somente quando há histórico vigente com `pessoa_usuario_id` correspondente.

Não foram convertidas linhas históricas de responsabilidade sem prova da identidade. Não existe autorização de terceiro apenas por estar autenticado no dispositivo.

## 16. Registry 375/376

O delta do registry foi separado por fase:

```text
baseline original: 373
01C: +2 tabelas intencionais = 375
01C1: +1 tabela intencional (`cadastros_pessoas_usuarios`) = 376
```

O teste foi atualizado para verificar:

- idempotência do registro;
- conjunto explícito das tabelas introduzidas por 01C;
- conjunto explícito da tabela introduzida por 01C1;
- contagens derivadas desses conjuntos;
- cobertura dos models e decisões de baseline;
- ausência de colisões.

O guardrail não foi enfraquecido: a contagem continua protegida e as tabelas críticas precisam estar presentes.

## 17. Falhas preexistentes e classificação

| Falha | Classificação | Evidência/decisão |
|---|---|---|
| Registry 373 após 01C | `INTRODUZIDA_01C`, corrigida | duas tabelas intencionais agora contabilizadas |
| `estoque_requisicoes_itens` sem FK direta para `tenants` | `INTRODUZIDA_01C`, corrigida em 01C1 | criada `fk_estoque_requisicoes_itens_tenant` |
| FKs diretas das novas tabelas com `CASCADE` | `INTRODUZIDA_01C`, corrigida em 01C1 | normalizadas para `RESTRICT` |
| Registry 375 após associação User/Pessoa | `INTRODUZIDA_01C1`, corrigida | tabela 01C1 explicitamente incluída no guardrail |
| Fixture financeiro sem `solicitante_id` | `PREEXISTENTE` | falha em `test_requisicao_financeiro_integration`; 01C1 não altera `EstoqueService` |
| `fix_imports.py` contém `MovimentacaoEstoque` | `PREEXISTENTE` | guardrail legado já falhava antes |
| 24 FKs não relacionadas com `CASCADE` para `tenants` | `GUARDRAIL_REAL` / `FORA_ESCOPO` | domínios preexistentes; pertencem ao TENANT-FK-REPAIR, não ao 01C1 |
| 13 tabelas preexistentes sem índice de tenant | `GUARDRAIL_REAL` / `FORA_ESCOPO` | nenhum nome novo da 01C/01C1 após correção |
| `prescricoes_vra` com `CASCADE` | `GUARDRAIL_REAL` / `FORA_ESCOPO` | dívida da onda anterior |
| execução agregada de parte da suíte com `E`/timeout | `AMBIENTE` | não usada como evidência de regressão; suites unitárias foram executadas isoladamente |

Não foi identificada falha `INTRODUZIDA_01C1` pendente.

## 18. Legado

Revalidação no PostgreSQL:

- `LEGACY_OPEN`: preservado;
- `LEGACY_DELIVERED`: preservado;
- `LEGACY_RETURNED`: preservado quando comprovado;
- `NULL`: permanece possível para desconhecido.

O 01C1 não criou:

- evento de `CONSUMO` histórico;
- evento de `RECEBIMENTO` histórico;
- movimento físico fictício;
- `CostAllocation` novo;
- lançamento financeiro paralelo;
- recalculo de DRE.

Não houve backfill para `PessoaUsuario`: contagem final zero.

## 19. Regressões

PASS:

- import da aplicação;
- registry e cobertura de models;
- testes direcionados 01C/01C1: **19 passed**;
- upgrade/downgrade/upgrade PostgreSQL;
- RLS e FKs tenant-safe;
- resolução real User → Pessoa;
- `git diff --check`.

Falhas não introduzidas e mantidas documentadas:

- duas falhas unitárias legadas relacionadas a fixture financeiro e termo em `fix_imports.py`;
- guardrails globais de tenant preexistentes listados na seção 17.

O `ruff` no conjunto amplo de arquivos reporta centenas de violações preexistentes de estilo/importação, principalmente nos models legados. Não foi usado como prova de regressão 01C1; os arquivos novos passaram por `py_compile` e os testes direcionados passaram.

## 20. Pendências

Antes ou durante as fases seguintes, permanecem:

1. implementar o comando backend de recebimento usando `IdentidadeOperacionalService.validar_recebedor`;
2. criar o fluxo de delegação que popula `pessoa_usuario_id` com autorização e auditoria;
3. impedir o fallback legado `operador_id or user_id` no contexto em que ele representar recebimento/autorização;
4. implementar Campo offline/idempotência/sync em 01E;
5. completar consumo, devolução e retornáveis em 01F;
6. integrar consumo real ao caminho `OperacaoAgricola → OperacaoExecucao → CostAllocation` em 01G;
7. tratar a dívida offline da migration `8c2e891d6ba9_caderno_campo.py` em fase própria, sem editar história silenciosamente;
8. tratar os guardrails globais G1/G3/B2.3 na frente TENANT-FK-REPAIR.

## 21. Prontidão para 01D

O 01D pode iniciar a fundação de reserva/picking/entrega canônica porque:

- a migration incremental foi validada no PostgreSQL real;
- downgrade e upgrade posterior foram validados;
- novas estruturas estão isoladas por tenant;
- a identidade operacional é canônica e contextual;
- a autorização de responsável/delegado é resolvível sem heurística;
- o registry conhece todas as tabelas intencionais;
- não houve cutover do fluxo legado;
- não houve alteração econômica histórica.

Condição: 01D deve manter o fluxo atual compatível e registrar a entrega vinculada ao item/evento, sem presumir que `User` seja `Pessoa` quando não houver `PessoaUsuario` ativo.

## 22. Veredicto

### Perguntas obrigatórias

**A. Qual é o vínculo canônico final entre User e Pessoa/Operador?**  
`cadastros_pessoas_usuarios` / model `PessoaUsuario`, com `tenant_id`, `pessoa_id`, `usuario_id`, status e vigência.

**B. Ele é global ou contextual ao Tenant?**  
Contextual ao Tenant. `Usuario` permanece global; `Pessoa` permanece tenant-scoped.

**C. Como o backend saberá que o usuário autenticado é o responsável da tarefa?**  
Resolve `PessoaUsuario` ativo para `(tenant_id, usuario_id)` e compara `pessoa_id` com a Pessoa responsável da requisição/tarefa. Não usa e-mail, CPF ou nome.

**D. Como saberá que é delegado?**  
Resolve o mesmo `PessoaUsuario` e exige `RequisicaoResponsabilidadeHistorico` vigente, papel `DELEGADO`, mesmo tenant, requisição, usuário e `pessoa_usuario_id`.

**E. As migrations 01C executam upgrade/downgrade corretamente em PostgreSQL real?**  
Sim para o ciclo final validado: upgrade 01C1, downgrade para 01C, inspeção e upgrade novamente. A migration histórica offline continua uma dívida técnica separada.

**F. RLS e FKs impedem cross-tenant de fato?**  
Sim para as estruturas novas e os vínculos testados. Tenant B não lê, insere, altera ou remove dados de A; FKs compostas rejeitam Pessoa/User de outro tenant.

**G. Append-only funciona no banco real?**  
Sim para `RequisicaoItemEvento`, por trigger PostgreSQL testado. `PessoaUsuario` é revogável por desenho e não é diário append-only.

**H. Idempotência funciona sob concorrência?**  
Sim para eventos por item: unique `(tenant_id, client_operation_id)` e teste com duas conexões não produziram duplicidade.

**I. A mudança 373 → 375 é legítima e o guardrail foi atualizado sem ser enfraquecido?**  
Sim. É o delta exato das duas tabelas 01C. A 01C1 acrescenta uma terceira tabela intencional, levando o total a 376; a contagem e o conjunto continuam protegidos.

**J. Existe BLOCKING/HIGH restante antes do 01D?**  
Não no escopo da fundação 01C1. Existem ressalvas preexistentes de guardrails globais e dívida de migration offline, que não bloqueiam a implementação incremental de 01D, mas impedem declarar toda a suíte/repositório globalmente verde.

```text
MATERIAL-REQUISITION-FLOW-01C1
STATUS: GO COM RESSALVAS
AUTORIZAÇÃO PARA 01D: SIM
PRÓXIMA FASE: MATERIAL-REQUISITION-FLOW-01D — reserva, picking e entrega canônica
```
