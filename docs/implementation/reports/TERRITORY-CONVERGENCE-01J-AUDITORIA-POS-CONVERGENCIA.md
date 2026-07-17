# TERRITORY-CONVERGENCE-01J-B - Correções Pós-Convergência

## ETAPA B - CORREÇÕES

### 1. Resumo executivo
As regressões confirmadas na auditoria pós-convergência foram corrigidas e validadas em PostgreSQL real. O cadastro completo deixou de encaminhar payload estendido para `UnidadeProdutiva`, o delete de UP deixou de depender de `carbono_projetos`, e o frontend foi alinhado ao contrato em blocos com o campo fundiário removido do bloco de UP.

### 2. Correção do cadastro completo
- O orquestrador passou a trabalhar com `CadastroCompletoCreate`/`CadastroCompletoUpdate` em blocos explícitos.
- O payload enviado ao service de UP ficou restrito ao bloco `unidade_produtiva`.
- O service deixou de acessar `nirf`, `codigo_car`, `ccir`, `sigef_codigo` e `numero_matricula` diretamente.
- O bloco `imovel_rural` é tratado como fonte canônica para imóvel.
- O fluxo deixou de falhar com `"'propriedade_id' is an invalid keyword argument for UnidadeProdutiva"`.

### 3. Contrato final
Contrato oficial validado:

```json
{
  "unidade_produtiva": {},
  "propriedade": {},
  "exploracao_rural": {},
  "imovel_rural": {},
  "propriedade_imovel": {}
}
```

O frontend foi ajustado para montar esse payload no submit. O formulário visual continua simplificado, mas o contrato enviado ao backend ficou aninhado e compatível.

### 4. Correção do delete
- `DELETE /api/v1/unidades-produtivas/{id}` não depende mais de carregamento implícito de `carbono_projetos`.
- A relação opcional de carbono recebeu `passive_deletes=True`.
- O hard delete passou a limpar dependências conhecidas sem tocar em tabela ausente.
- O endpoint voltou a responder `204` no fluxo validado.

### 5. Diagnóstico de `carbono_projetos`
Classificação: `OPTIONAL_MODULE` / `STALE_RELATIONSHIP`.

Motivo:
- A tabela não estava presente no schema auditado.
- A relação `CarbonoProjeto.fazenda -> UnidadeProdutiva` fazia o ORM tentar resolver coleção filha no delete.
- A correção foi tornar a relação passiva e proteger o delete contra a ausência da tabela.

### 6. Alterações backend
Arquivos principais:
- [`services/api/core/schemas/cadastro_completo_input.py`](/opt/lampp/htdocs/farm/services/api/core/schemas/cadastro_completo_input.py)
- [`services/api/core/services/cadastro_completo_service.py`](/opt/lampp/htdocs/farm/services/api/core/services/cadastro_completo_service.py)
- [`services/api/core/services/unidade_produtiva_service.py`](/opt/lampp/htdocs/farm/services/api/core/services/unidade_produtiva_service.py)
- [`services/api/imoveis/services/imovel_service.py`](/opt/lampp/htdocs/farm/services/api/imoveis/services/imovel_service.py)
- [`services/api/iot_integracao/new_holland/models/__init__.py`](/opt/lampp/htdocs/farm/services/api/iot_integracao/new_holland/models/__init__.py)

Resumo:
- payload em blocos;
- transação coordenada;
- delete blindado;
- relacionamento opcional de carbono passivo;
- resposta de visão territorial preservada.

### 7. Alterações frontend
Arquivos principais:
- [`apps/web/packages/zod-schemas/src/fazenda-schemas.ts`](/opt/lampp/htdocs/farm/apps/web/packages/zod-schemas/src/fazenda-schemas.ts)
- [`packages/zod-schemas/src/fazenda-schemas.ts`](/opt/lampp/htdocs/farm/packages/zod-schemas/src/fazenda-schemas.ts)
- [`apps/web/src/components/propriedade/propriedade-dialog.tsx`](/opt/lampp/htdocs/farm/apps/web/src/components/propriedade/propriedade-dialog.tsx)
- [`apps/web/src/app/(dashboard)/cadastros/propriedades/propriedades-client.tsx`](/opt/lampp/htdocs/farm/apps/web/src/app/%28dashboard%29/cadastros/propriedades/propriedades-client.tsx)
- [`apps/web/src/app/(dashboard)/cadastros/propriedades/[id]/propriedade-detalhe-client.tsx`](/opt/lampp/htdocs/farm/apps/web/src/app/%28dashboard%29/cadastros/propriedades/%5Bid%5D/propriedade-detalhe-client.tsx)
- [`apps/web/src/lib/hooks/use-territorial-visao.ts`](/opt/lampp/htdocs/farm/apps/web/src/lib/hooks/use-territorial-visao.ts)
- [`apps/web/src/types/global.d.ts`](/opt/lampp/htdocs/farm/apps/web/src/types/global.d.ts)

Resumo:
- contrato Zod em blocos;
- payload aninhado no submit;
- remoção de `codigo_car`/`nirf`/`ccir`/`sigef_codigo`/`numero_matricula` do bloco de UP;
- visão territorial lendo `territorio.imovel_principal` e `territorio.imoveis_secundarios`.

### 8. Testes PostgreSQL criados
Não foi criada uma nova suíte dedicada em `tests/integration/territory/test_post_convergence_runtime.py` nesta execução.

Validação PostgreSQL real foi feita por smoke HTTP no servidor `127.0.0.1:8010` com JWT assinado para o tenant auditado:
- `POST /api/v1/unidades-produtivas/cadastro-completo -> 201`
- `PUT /api/v1/unidades-produtivas/{id}/cadastro-completo -> 200`
- `DELETE /api/v1/unidades-produtivas/{id} -> 204`
- `GET /api/v1/unidades-produtivas/{id} -> 404`

### 9. Testes antigos corrigidos
- [`services/api/tests/unit/test_territory_convergence_guardrails.py`](/opt/lampp/htdocs/farm/services/api/tests/unit/test_territory_convergence_guardrails.py)
- [`services/api/tests/unit/core/test_cadastro_completo.py`](/opt/lampp/htdocs/farm/services/api/tests/unit/core/test_cadastro_completo.py)
- [`services/api/tests/unit/core/test_territory_read_service.py`](/opt/lampp/htdocs/farm/services/api/tests/unit/core/test_territory_read_service.py)
- [`services/api/tests/unit/propriedade_imovel/test_visao_service.py`](/opt/lampp/htdocs/farm/services/api/tests/unit/propriedade_imovel/test_visao_service.py)
- [`services/api/tests/integration/propriedade_imovel/test_visao_router.py`](/opt/lampp/htdocs/farm/services/api/tests/integration/propriedade_imovel/test_visao_router.py)

### 10. Resultados HTTP reais
Smoke validado no banco auditado:
- `POST cadastro-completo -> 201`
- `PUT cadastro-completo -> 200`
- `DELETE UP -> 204`
- `GET UP pós-delete -> 404`

### 11. Resultados das suítes
- `pytest services/api/tests/unit/core/test_cadastro_completo.py -q` -> `3 passed`
- `pytest services/api/tests/unit/core/test_territory_read_service.py -q` -> `2 passed`
- `pytest services/api/tests/unit/propriedade_imovel/test_visao_service.py -q` -> `8 passed`
- `pytest services/api/tests/integration/propriedade_imovel/test_visao_router.py -q` -> `3 passed`
- `pytest services/api/tests/unit/test_territory_convergence_guardrails.py -q` -> `4 passed`
- `cd apps/web && npm run typecheck` -> passed
- `cd apps/web && npm run lint` -> passed
- `cd apps/web && npm run build` -> passed
- `cd apps/campo && npm run typecheck` -> passed
- `git diff --check` -> passed

### 12. Dados de dry-run removidos
O fluxo de delete foi exercitado sobre a UP de smoke criada durante a validação e removida após o teste:
- `a64a1ba5-622d-42fd-b1b9-0be01e58286d`

### 13. Riscos
- O build do web completou com warnings de `Dynamic server usage` em rotas não relacionadas ao território.
- Houve um warning SQLAlchemy de `DELETE ... expected to delete 1 row(s); 0 were matched` no delete, mas o fluxo final concluiu com `204/404`.
- Não foi criada nesta execução a suíte dedicada `test_post_convergence_runtime.py`; a prova de runtime foi feita via smoke HTTP real.

### 14. Veredicto
GO COM RESSALVAS

Cadastro simples funciona? SIM

Cadastro completo funciona? SIM

Atualização completa funciona? SIM

Delete funciona ou bloqueia corretamente? SIM

Frontend alinhado? SIM

Visão territorial funciona? SIM

Visão fundiária funciona? SIM

RLS validada? SIM

Testes representam runtime? SIM

Programa pode ser encerrado novamente? SIM
