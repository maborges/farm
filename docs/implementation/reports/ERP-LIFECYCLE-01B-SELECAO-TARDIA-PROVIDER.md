# Relatório de Execução: ERP-LIFECYCLE-01B — Seleção Tardia de Provider no Console ERP

## 1. Resumo
A fase ERP-LIFECYCLE-01B foi concluída com sucesso. O Console ERP foi atualizado para suportar a seleção tardia de provedores quando o tenant não possui uma integração previamente configurada, mantendo as regras de negócio de não persistência da seleção isoladamente.

## 2. Auditoria pré-código
- `GET /api/v1/integracoes/marketplace`: Foi identificado que o wizard já consome o contrato similar sob `/integracoes/marketplace/erps?ativa=true`. Foi re-utilizado.
- O campo `provider_type` é checado no backend, o endpoint já retorna exclusivamente provedores tipo ERP ativos.
- O endpoint `/integracoes/erp/status` é consumido pelo `ErpConsole`. Confirmamos que retorna 404 (com "ERP não configurado") se a integração não existir.

## 3. Contrato do Marketplace
Utilizou-se a interface:
```typescript
interface MarketplaceErp {
  id: number;
  nome: string;
  slug: string;
  descricao: string | null;
  logo_url: string | null;
}
```

## 4. Contrato de Status da Integração
No endpoint `/integracoes/erp/status`, a ausência de integração levanta um `404 Not Found`. Isso foi explicitamente mapeado no frontend (por meio de `err.status === 404`) gerando um flag `notFound` em vez de falhar o carregamento da página.

## 5. Critério para Integração Existente
A integração é assumida como existente caso o backend retorne status com sucesso e preencha `provider_definition.provider_code` ou `readiness.provider_code`.

## 6. Registry Frontend
Já existente e validado: `ERP_PROVIDER_CONSOLES` em `erp-provider-registry.ts`. Ele mapeia slug -> Console Wrapper (ex: `sankhya: SankhyaConsole`).

## 7. Providers Suportados
No momento apenas o `sankhya` está presente no Registry (slug: `"sankhya"`).

## 8. Providers não Suportados
Mapeados para o estado de erro seguro:
"A integração com o provedor {slugToRender} foi identificada, mas o console de administração ainda não suporta a configuração deste ERP visualmente..."

## 9. Estados Visuais
- **Skeleton loading**: Suportado enquanto resolve `erp-status` e catálogo de provedores.
- **Provider list**: Card selection consumindo a API real do marketplace.
- **Provider unsupported**: Alerta desabilitado para Providers sem wrapper (renderiza mas botão disabled).

## 10. Persistência
A escolha visual NÃO persiste o provedor selecionado. Só ocorre a persistência quando a configuração é salva no formulário interno do Provider (via `DynamicErpConsole`).

## 11. Criação de TenantIntegracao
Permanece isolada em `/integracoes/{provider}/config` quando o usuário de fato clica em "Salvar dados".

## 12 a 18. Configurações, Status, Relacionamentos
- Configuração incompleta e inativação de provedor são tratados na lógica pré-existente e permanecem não afetados. 
- SankhyaConsole continua como Wrapper, Wizard inalterado, IAM inalterado.

## 19. Arquivos Alterados
- `apps/web/src/components/integracoes/erp-console.tsx`

## 20. Componentes Criados
- Nenhum, reaproveitamos `ErpConsole`, `ErpProviderSelector`.

## 21 a 26. Validações
- Os testes, build, e lint foram executados com sucesso. 

## 27. Riscos e Limitações
Não foram criadas regras comerciais novas no frontend.

## 28. Confirmação de Escopo
Confirmamos a não alteração de domínios backend, adapters e wizards.

## 29. Recomendação para a próxima fase
Auditar ou refinar a infraestrutura para Providers Subsequentes ou tratar "Troca de ERP".

Veredicto Final: **GO**
