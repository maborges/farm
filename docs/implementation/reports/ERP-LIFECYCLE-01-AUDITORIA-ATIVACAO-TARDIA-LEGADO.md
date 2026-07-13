# Relatório de Auditoria: Ciclo de Ativação ERP para Tenants Novos, Legados e Pós-Implantação

**Fase:** ERP-LIFECYCLE-01
**Data:** 2026-07-12
**Veredicto:** GO COM RESSALVAS (Correção apenas de UX sugerida)

## 1. Resumo Executivo e Problema
A arquitetura do `Console ERP` foi auditada para garantir compatibilidade com Tenants que não efetuaram ativação via Wizard (tenants legados, setups parciais ou adoção de ERP pós-onboarding). O resultado central atesta a **total resiliência do Backend**: as APIs não exigem *Wizard* e as permissões de acesso ao console estão intactas (`OnboardingGuard` autoriza a rota). O gargalo exclusivo repousa no Frontend (`ErpConsole`), que, ao não possuir uma configuração ERP prévia instanciada, renderiza de imediato o componente Sankhya (`SankhyaConsole`) via um *alias fixo*, não apresentando o Marketplace de Provedores para uma "escolha".

## 2. Arquitetura Atual e Fluxo de Acesso
- **Guards:** `OnboardingGuard` foi verificado (`apps/web/src/components/auth/onboarding-guard.tsx`). A rota `/dashboard/settings/integracoes/erp` encontra-se isenta (`ONBOARDING_ALLOWED_PATHS`). Assim, Tenants com implantação não concluída ou em "cargas manuais" acessam normalmente.
- **Permissões:** O acesso exige `integrations:view`. A alteração do *provider* ERP exige `integrations:configure`.
- **Planos e Assinatura:** O código atual da API de configuração (`configurar_sankhya`) e a renderização do `ErpConsole` não travam estritamente tenants caso um plano comercial não preveja o ERP, sugerindo que a liberação opera atualmente com permissões de IAM do usuário em vez de _locks_ de _billing_ (salvo checagens secundárias via `readiness_service`).

## 3. Seleção de Provider e `TenantIntegracao`
- **Marketplace e Seleção:** Atualmente a seleção ocorre implicitamente. A rota ERP da UI força a leitura do *Wrapper* estático (`SankhyaConsole`).
- **Criação de `TenantIntegracao`:** Ela é criada via *Upsert* (idempotente). O endpoint `/integracoes/sankhya/config` (POST) utiliza `CanonicalAdapter.sync_provider_config` para recuperar a configuração legada e acionar a gravação. Não há risco sistêmico de duplicação, pois a arquitetura faz `update` se o tenant já possuir o ID daquele provider.
- **Wizard:** O Wizard não cria registros `TenantIntegracao`. Ele apenas orquestra intenções no Payload do checklist, evitando acoplamento e corrupção.

## 4. Matriz de Cenários
| Cenário | Funciona hoje? | Bloqueio | Fonte da regra | Correção necessária |
|---------|:---:|----------|----------------|---------------------|
| Novo Tenant com ERP | Sim | Fluxo Mestre UX | ErpConsole estático | Exibir Marketplace se s/ ERP. |
| Novo Tenant configurar depois | Parcial | Falta Escolha UX | ErpConsole estático | Requer seletor de ERPs inicial. |
| Tenant legado sem Wizard | Parcial | Escolha UX | ErpConsole estático | Requer seletor de ERPs. |
| Tenant implantado sem ERP | Parcial | Escolha UX | ErpConsole estático | Requer seletor de ERPs. |
| Tenant com carga manual | Sim | Nenhum | Readiness API | Nenhuma modificação Backend. |
| Integração incompleta | Sim | Nenhum | Canonical Adapter | Preenchimento pacífico de *form*. |
| Integração inativa | Sim | Nenhum | Canonical Adapter | Atualiza dados e volta a conectar. |
| Sem permissão | Bloqueado | Regra IAM correta | Router Guards | -- |
| Sem plano | Permite/Parcial| Depende de ACL | ErpConsole | Bloquear/avisar s/ módulo billing. |
| Provider inativo | Trata (API 400)| Marketplace Inativo | Endpoint Schema | Tratar na UI Frontend. |

## 5. Tenancy, Riscos e Duplicações (Backend Intocado)
- A *Ownership* das informações e a resiliência Multi-Tenant não correm risco. As chamadas (`get_tenant_id`) garantem separação de instâncias e não cruzam configurações. 
- **Duplicações identificadas**: Foi apontado apenas a "Duplicação de Decisão" (O *Wizard* não concretiza o provider, o *ErpConsole* força um provider), portanto deve haver uma uniformização que permita que o Dashboard ERP carregue em "Estado Branco" listando opções.

## 6. Lacunas Classificadas
1. `PROVIDER_SELECTION`: O Frontend injeta um _Hardcode Alias_ (`export const ErpConsole = SankhyaConsole`).
2. `UX_ONLY`: Ausência de cartões introdutórios ilustrando "Escolha seu ERP" para os não-configurados (Estado 1 e 2 solicitados).

## 7. Menor Solução Recomendada
Para a Próxima Fase (Sugestão: **ERP-LIFECYCLE-01B**):
Substituir o componente `ErpConsole` dentro do repositório frontend por um roteador inteligente:
1. Ao montar `/dashboard/settings/integracoes/erp`, se `/integracoes/erp/status` ou `config` retornarem `null` / `404`, exibe uma galeria do Marketplace.
2. Ao selecionar *Sankhya*, carrega dinamicamente o `<SankhyaConsole />`. O Backend e fluxos de criação permanecem _Zero-Code_.

## 8. Veredicto Final
**GO COM RESSALVAS**: O fluxo fundamental está viável e preserva totalmente a segurança e robustez entre Tenants novos e velhos. A "Ressalva" repousa apenas em um micro-ajuste de *UX Frontend*, uma vez que a página atualmente engessa o primeiro passo da adoção tardia por falta de uma interface de Seleção Genérica, obrigando todo Tenant a consumir o *Sankhya*. Confirmada a manutenção de Estoque P2 sem violações. Nenhuma migração ou alteração de API foi requisitada para corrigir a lacuna atual.

*(Fim do Relatório)*
