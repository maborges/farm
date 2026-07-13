# ERP-GATE-01A — Persistência Schema-Driven da Configuração ERP

## 1. Resumo

Esta etapa resolveu o `PILOT_BLOCKER` identificado na auditoria `ERP-GATE-01`.
A limitação que impedia a gravação de campos valiosos (como `auth_model` e `ws_url`) devido a um hardcode específico no frontend foi removida com a implementação de um construtor de payload puramente orientado pelo schema.

## 2. Ações Realizadas

### 2.1. Extração do Builder de Payload
- Criada a função pura `buildProviderConfigPayload` em `apps/web/src/components/integracoes/erp/provider-config-payload.ts`.
- O payload agora é gerado iterando dinamicamente sobre o `connection_schema` e o `credential_schema` fornecidos pelo backend.

### 2.2. Integração no `DynamicErpConsole`
- O `handleSave` no `apps/web/src/components/integracoes/erp-console.tsx` foi atualizado para não mais enviar o objeto restrito (`sankhya_api_base_url`, etc.).
- Utiliza a nova função passando o `schema` fornecido, os valores atuais do form (`formData`), e os valores iniciais carregados da configuração anterior.
- Segredos inalterados que contenham máscaras (ex: `••••••••` ou com prefixo `enc::`) são descartados de forma segura, impedindo que máscaras sobrescrevam as credenciais no banco.

### 2.3. Cobertura de Testes Unitários
- Criado o arquivo `provider-config-payload.test.ts`.
- Executados 16 casos de testes através do **Playwright Test** (já configurado no projeto) garantindo que:
  - Campos não-previstos no schema sejam descartados.
  - Tipos primitivos (`integer`, `boolean`) sejam normalizados.
  - Omissão de senhas mascaradas funcione devidamente (simulando a interface do frontend).
  - Valores vazios sejam descartados para garantir estabilidade com o backend (sem sobrescrever acidentalmente propriedades omitidas).

## 3. Veredito Final
A arquitetura ERP-First está agora preservada de ponta a ponta. 
A persistência da configuração no console foi tornada verdadeiramente agnóstica em relação a um ERP específico. Logins alternativos e parâmetros extras enviados por providers flexíveis serão agora armazenados com sucesso.

**Status:** APROVADO. Bloqueador para o piloto Safra Café superado com sucesso.
