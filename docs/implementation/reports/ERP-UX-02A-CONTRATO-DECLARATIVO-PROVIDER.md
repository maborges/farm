# Relatório: Contrato Declarativo do Provider ERP (ERP-UX-02A)

**Projeto**: ERP-UX-02A
**Tema**: Enriquecimento do Contrato Declarativo de Configuração do Provider ERP
**Data da Implementação**: 2026-07-10

---

## 1. Resumo Executivo
Esta implementação atende à etapa ERP-UX-02A. O objetivo foi materializar o contrato declarativo rico (`ProviderSchemaDefinition`) que permitirá a construção futura do `<DynamicErpConsole />`. Com a alteração, o `canonical_adapter.py` do Sankhya passa a popular `connection_schema` e `credential_schema` não apenas com as chaves obrigatórias e opcionais antigas, mas com os metadados visuais de renderização, mantendo total retrocompatibilidade e segurança de dados, sem duplicação ou persistência indevida de secrets na definição do provider.

## 2. Contrato Anterior
O contrato antigo era fracamente tipado, materializado como um dicionário Python diretamente injetado na tabela `MarketplaceIntegracao`.
Exemplo anterior em `connection_schema`:
```json
{
  "required": ["sankhya_environment", "sankhya_api_base_url", "sankhya_auth_url", "sync_interval"],
  "optional": ["sankhya_client_id", "sankhya_client_secret", ...]
}
```
**Problema**: Sem tipagem de dado, sem ordem, sem placeholder, sem opções de enum.

## 3. Consumidores Encontrados
- **Providers (OpenWeather, Sankhya)**: Injetam esse JSON na criação via os *canonical adapters*.
- **SyncService/AuthService (Backend)**: Lê os arrays `required`/`optional` para checar se o tenant forneceu chaves vitais no runtime (`ErpReadinessService`).
- **Nenhum leitor frontend legível**: Atualmente o frontend Sankhya-Console ignora esse schema e assume as tags React de formulário arbitrariamente de forma estática.

## 4. Decisão de Compatibilidade
- Optamos pela **Estratégia Preferencial**: A classe Pydantic `ProviderSchemaDefinition` mantém intocados os parâmetros legados `required` e `optional`.
- Uma versão foi inserida (`schema_version: 1`).
- Os campos visuais migraram para o novo array `fields` contendo coleções de `ProviderFieldDefinition`.
- Dessa forma, os consumidores legados como `ErpReadinessService` continuarão validando arrays puros, sem causar nenhuma quebra nos testes preexistentes.

## 5. Contrato Novo e Tipos Suportados
O novo contrato foi formalizado no arquivo `services/api/integracoes/schemas.py`.

Tipos definidos (`ProviderFieldType`):
- `string`: Texto livre (input padrão).
- `secret`: Texto sensível mascarado visualmente. Impede a inserção de *defaults* no Pydantic.
- `url`: Texto específico de link.
- `boolean`: Chaves lógicas (Ex: `legacy_auth_model`).
- `integer`: Números inteiros (Ex: `sync_interval`).
- `select`: Caixa de seleção combinada de valores controlados (`options`).

Cada campo agora conta com as diretivas explícitas:
- `key`: Nome exato do payload de conexão/credencial.
- `label`: Nome de apresentação UI.
- `type`: Enum de renderização.
- `required`: Obrigatoriedade booleana.
- `secret`: Flag de mascaramento (aplica na UI de configuração posterior).
- `default`: Valor não-sensível default (ex: "60" no intervalo, "PRODUCAO" no ambiente).
- `order`: Ordem na tela.

## 6. Separação connection/credential
A estrutura obedeceu rigorosamente à arquitetura:
- `connection_schema`: Contém URLs genéricas (`sankhya_api_base_url`), ambientes lógicos (`sankhya_environment`), flags operacionais (`auth_model`) e timeouts (`sync_interval`). Nenhum segredo foi classificado aqui.
- `credential_schema`: Contém chaves e senhas (`sankhya_client_secret`, `sankhya_x_token`, `password`, `sankhya_appkey`), sendo que a flag booleana interna de Pydantic `secret=True` garante que nem o adapter acidentalmente inclua `defaults`.

## 7. Definição Sankhya
O schema foi amplamente descrito em `services/api/integracoes/sankhya/services/canonical_adapter.py`. 
Foram contempladas as opções de Select Dropdowns:
- Para o campo `auth_model`, foram inseridas as opções `gateway_oauth_client_credentials` e `gateway_legacy_login`.
- Para o `sankhya_environment`, as opções de "PRODUCAO", "HOMOLOGACAO" e "SANDBOX".
A ordem visual também foi distribuída com folgas (10, 20, 30...).

## 8. Validações e Segurança
O guardrail validou perfeitamente:
- `@model_validator` na classe `ProviderSchemaDefinition` foi implementado para verificar **unicidade das chaves** contidas no array `fields`.
- Validação impede que chaves com `secret=True` passem com propriedades `default`.
- Tipos `select` obrigatoriamente precisam de `options`.
- Como o schema representa a "fôrma", nenhum dado sensível de cliente está contido ali; o `canonical_adapter.py` passou nas baterias de testes (e os testes de integridade `test_provider_e_provider_definition_nao_podem_armazenar_credenciais_reais_de_cliente` e adapter passaram na pipeline).

## 9. Arquivos Alterados
- `services/api/integracoes/schemas.py`: Adição dos Pydantic Models formais.
- `services/api/integracoes/sankhya/services/canonical_adapter.py`: Atualização do injection do payload no DB para rodar através do Pydantic dump `mode='json'`.

## 10. Limitações e Próximos Passos
**Limitações**: Esta fase apenas injetou a definição no banco de dados para os novos records de Provider, mas não expõe os metadados isoladamente em um router genérico para o frontend ainda.
**Próximo Passo Recomendado**: ERP-UX-02B (exposição segura do schema e persistência genérica).

---

**Veredicto Oficial**: **GO — contrato declarativo pronto.**
