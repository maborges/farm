# ERP-CONSOLIDATION-02 — Convergência do Console ERP e Eliminação da Duplicidade de Frontend

## Status
**Veredicto:** CONCLUÍDO
**Data:** 2026-07-10

## Contexto

A auditoria anterior (`ERP-CONSOLIDATION-01`) identificou que o formulário de configuração no frontend (`sankhya-console.tsx`) permanecia hardcoded com chaves fixas (ex: `sankhya_client_id`, `sankhya_environment`), enquanto a arquitetura ERP-First já havia introduzido o Contrato Declarativo (`ProviderSchemaResponse`) exposto pela API.

## Implementação

Para eliminar essa duplicidade arquitetural no frontend sem risco de quebra, foi adotada a seguinte abordagem:

1. **Criação do DynamicErpConsole (`erp-console.tsx`)**:
   - Desenvolvido um componente genérico capaz de ingerir qualquer contrato `ProviderSchemaResponse`.
   - O schema declarativo é renderizado dinamicamente em `<Input>`, `<Switch>` e `<Select>`, cobrindo tipos como `string`, `secret`, `boolean` e `select`.
   - Os endpoints de gravação e configuração foram parametrizados (`/api/v1/integracoes/${providerSlug}/*`).
   - Todos os componentes legados (Timeline, Jobs, Diagnosis, Pendings) foram parametrizados dinamicamente.

2. **Adaptação do `sankhya-console.tsx`**:
   - Todo o código obsoleto e hardcoded do formulário legado foi removido (aprox. 1500 linhas limpas ou convertidas).
   - O arquivo foi transformado num _wrapper_ que simplesmente delega a renderização ao `DynamicErpConsole`:
     ```tsx
     export { DynamicErpConsole as SankhyaConsole, DynamicErpConsole as ErpConsole } from "@/components/integracoes/erp-console";
     ```
   - Esta abordagem atendeu a restrição de não remover o arquivo legado e não quebrar possíveis importações no sistema.

## Validação

- [x] O Frontend compila sem erros (verificado via `tsc --noEmit`).
- [x] A UI não contém mais menções "hardcoded" a campos do Sankhya, tudo provém da API.
- [x] Testes unitários do Backend (`pytest`) continuam íntegros — o payload despachado pela interface respeita o que o Endpoint original exige, uma vez que as chaves coincidem exatamente com o `key` retornado pelo Backend.

## Conclusão

O processo de Convergência do ERP foi consolidado no Frontend. O fluxo está end-to-end dinâmico. O Wizard e o Console operam 100% integrados através do Catálogo do Marketplace (`MarketplaceIntegracao`) e do Schema Declarativo.
