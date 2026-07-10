# Relatório: Exposição Segura do Contrato Declarativo do Provider ERP (ERP-UX-02B)

**Projeto**: ERP-UX-02B
**Tema**: Superfície HTTP de Exposição do Contrato Declarativo
**Data da Implementação**: 2026-07-10

---

## 1. Resumo Executivo
Esta implementação atende à etapa ERP-UX-02B, cujo objetivo é fornecer uma superfície HTTP para consulta do contrato declarativo de providers ERP (`connection_schema` e `credential_schema`), sem vazar segredos e sem acoplar regras de negócios provider-specific dentro da rota. Criamos o endpoint `/api/v1/integracoes/erp/providers/{provider_slug}/schema` assegurando um contrato formal no frontend, compatibilidade nativa com as implementações passadas e sem afetar a arquitetura ERP-First.

## 2. Auditoria de Reutilização e Arquitetural
- `services/api/integracoes/marketplace_router.py`: Verificamos que só exporta informações rasas (id, nome, logo). Não faz sentido poluir essa rota, já que a configuração pertence à implantação/configuração do ERP.
- `services/api/integracoes/erp/router.py`: Contém a superfície ERP genérica oficial. Criamos a rota `GET /providers/{provider_slug}/schema` nesta malha, garantindo namespace de `/api/v1/integracoes/erp`.
- `services/api/integracoes/models.py`: Confirmamos a leitura unicamente do `MarketplaceIntegracao`. Nenhum dado ou configuração do `TenantIntegracao` ou `IntegrationCredential` foi invocado, bloqueando assim qualquer vazamento por design.
- O endpoint resolve por `provider_slug`, para permitir aos usuários uma visualização do blueprint (formulário estético do Pydantic) antes de realmente instanciar um `TenantIntegracao`.

## 3. Contrato HTTP de Resposta
A fim de tipar as saídas corretamente, estendemos o arquivo `services/api/integracoes/schemas.py` com `ProviderSchemaResponse` e `ProviderPublicIdentity`. 

A resposta estruturada contém:
```json
{
  "provider": {
    "id": 1,
    "slug": "sankhya",
    "nome": "Sankhya",
    "provider_type": "ERP",
    "ativa": true,
    ...
  },
  "schema_version": 1,
  "connection_schema": {
    "required": [],
    "optional": [],
    "fields": [...]
  },
  "credential_schema": { ... }
}
```

## 4. Regras de Validação (Rejeições)
O endpoint provê validações rigorosas e blindagem a cenários não previstos:
- **404**: Se o slug do provider for inexistente.
- **400**: Se o `provider_type` não for `ERP`.
- **400**: Se o provider estiver inativo (`ativa=False`).
- **Segurança**: Pydantic models não carregam chaves não-declaradas. E na leitura, nós não lemos configurações de usuário.

## 5. Extensibilidade
- O endpoint não possui hardcodes ou switches do tipo `if slug == "sankhya": return [...]`. Ele reflete o catálogo passivamente e materialmente via DB.
- Por não invocar `TenantIntegracao`, ele atende tanto o fluxo do Wizard de primeiro uso (usuário explora configuração antes de ter TenantIntegracao configurado) quanto o Console de Edição futura.

## 6. Testes e Validação
Testes unitários rigorosos foram injetados no `services/api/tests/unit/integracoes/test_erp_router.py`.
Abrangemos:
1. Resposta de sucesso (200 OK) ao buscar Provider ERP válido.
2. Rejeição estruturada (404 Not Found) ao buscar inexistentes.
3. Rejeição (400 Bad Request) ao tentar buscar um CRM num endpoint ERP.
4. Rejeição (400 Bad Request) para providers inativos.

A suite test_erp_router encerrou com 100% de sucesso (`pytest -q`).
Não houve desvios do diff ou artefatos marginais nas checagens de linters (`git diff --check`).

## 7. Limitações e Próximos Passos
**Limitações**: Esta fase apenas injetou a definição na visualização de leitura. Ainda não temos o payload de SAVE/CREATE.
**Próximo Passo Recomendado**: ERP-UX-02C (persistência genérica e segura da configuração) ou ERP-UX-02D (renderização dinâmica no Console ERP).

---

**Veredicto Oficial**: **GO — contrato declarativo exposto com segurança**
