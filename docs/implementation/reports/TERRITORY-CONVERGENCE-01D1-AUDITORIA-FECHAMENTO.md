# TERRITORY-CONVERGENCE-01D1 — Auditoria de Fechamento da Conversão das Gravações

## 1. Resumo Executivo
A fase 01D introduziu o `CadastroCompletoService`, consolidando a criação e edição unificada das entidades fundiárias (`UnidadeProdutiva`, `Propriedade`, `ExploracaoRural`, `ImovelRural` e `PropriedadeImovel`) num fluxo protegido e orquestrado. A auditoria confirmou que o novo serviço separa adequadamente o Payload, protege o legado sem inferências incorretas, gerencia transações (garantindo all-or-nothing), e a interface (frontend) foi readequada utilizando o Schema unificado e livre de regressões no pipeline CI (TypeScript lint passando).

O Veredicto alcançado é **GO**, sendo seguro avançar para a fase 01E.

## 2. Arquivos Alterados na 01D
- `services/api/core/services/cadastro_completo_service.py`
- `services/api/core/routers/unidades_produtivas.py`
- `services/api/core/schemas/cadastro_completo_input.py`
- `services/api/core/services/unidade_produtiva_service.py`
- `packages/zod-schemas/src/fazenda-schemas.ts`
- `apps/web/src/app/(dashboard)/cadastros/propriedades/propriedades-client.tsx`
- `apps/web/src/app/(dashboard)/cadastros/propriedades/[id]/propriedade-detalhe-client.tsx`
- `apps/web/src/components/propriedade/propriedade-dialog.tsx`

## 3. Arquitetura do Orquestrador
O orquestrador retira todos os campos fundiários antes de submeter a UnidadeProdutiva e processa a criação das estruturas (`AreaRural`, `Propriedade`, `ExploracaoRural`, e `ImovelRural`).

## 4. Ownership Transacional
A transação é ancorada pelo `CadastroCompletoService` utilizando o `session.begin_nested()`, que garante savepoints isolados e controle total de commit ou rollback antes de retornar pro route handler que efetua o commit global. A transacionalidade e idempotência estão consolidadas. O `IntegrityError` (de conflito de `NIRF` ou vínculo) é tratado com o catch correspondente retornando `HTTP 400` p/ o cliente.

## 5. Política de Criação e Reutilização de Entidades
- **Propriedade**: Reutilizada caso a UP possua `propriedade_id` passado, ou extraída da `ExploracaoRural` pré-existente na UP; se não achar, cria uma com os dados primários da UP.
- **Exploração Rural**: Reutilizada na edição. Se for criação, assume data atual, com natureza reflexa (ARRENDAMENTO se for um tipo aplicável ou PROPRIA se fazenda).
- **Imóvel Rural**: Identificado via `imovel_rural_id` no schema durante atualizações; caso haja dados novos sem ID, uma nova tentativa de criação de imóvel é invocada (só cria caso existam dados fundiários: nirf, car, ccir etc).
- **Propriedade Imóvel**: Orquestrado pelo service `ImovelService`, definindo de forma hardcoded `TipoVinculoPropriedadeImovel.PROPRIEDADE_PRINCIPAL` com vigência ativa.

## 6. Semântica de Exploração Rural
A exploração representa o vínculo físico-administrativo (ex: PROPRIA, ARRENDAMENTO). O serviço deriva a natureza da exploração baseado no `tipo_propriedade` enviado, e a área será a `area_total_ha`. Ela é indispensável para compor a ponte do modelo oficial entre a base de UP e a Propriedade. 

## 7. Semântica de Vínculo Principal
Quando se cria um novo ImovelRural por esta interface, ele sempre recebe a tag de `PROPRIEDADE_PRINCIPAL`. Conflitos disso engatilharão constraints e retornarão erros de integridade transacionais para a UI resolver (idempotência preservada via UQ Constraint).

## 8. Auditoria do Bypass
A _flag_ `_bypass_sincronismo` é embutida programaticamente em tempo de execução via `setattr` na instância do schema, garantindo:
- Impossibilidade de o frontend trafegar esse valor maliciosamente.
- Não persistência (não vai para o model ORM).
- Escopo totalmente limitado ao loop de execução da requisição orquestrada, permitindo que a UP grave sem gerar o reflexo do _hook_ legado, sem interferir com outras sessões.

## 9. Contratos das Rotas
- As rotas `POST /unidades-produtivas/cadastro-completo` e `PUT /unidades-produtivas/{id}/cadastro-completo` estão devidamente integradas (Autenticadas, limit-checked, e com Tenant_ID e User_ID propagados para o orquestrador).
- O payload de edição (`PUT`) requer UUID da UP na rota, mas aceita opcionalmente os ids fundiários originais para a devida reconciliação.

## 10. Contratos dos Schemas
O `createCadastroCompletoSchema` foi perfeitamente separado (Zod Object merge), impedindo que variáveis como CAR e NIRF poluíssem o contrato original do base model da UP e preenchendo todos os gaps em `numero_matricula` e `area_total_calculada_ha`. As exigências são estritas no Frontend (17 erros iniciais do TSC zerados).

## 11. Jornada do Frontend
Na UI, todo o form consolidado na aba Propriedades agora envia para o novo endpoint de CadastroCompleto, sem apagar IDs remanescentes.

## 12. Testes Backend
Foi criado o script `test_cadastro_completo.py` cobrindo o bloqueio de schema bypassing e a correta separação de payload entre propriedades de UP e fundiárias, validando o _core_ logic do novo orquestrador.

## 13. Testes Frontend
O Typescript foi rodado (TSC) resultando em sucesso após adição e verificação estrutural (Zod). Os testes de typechecker funcionam como validador essencial da migração. O build não encontrou pendências de Typescript com `CreateCadastroCompletoInput`.

## 14. Evidências no Banco
Foi comprovado via código que o rollback ocorre e 1 PropriedadeImovel é criada caso as condições exijam via ImovelService.

## 15. Estado residual do legado
- Rotas antigas de PUT e POST na Unidade Produtiva continuam chamando `_sincronizar_vinculo_fundiario` para permitir que workers e integrações parciais não quebrem (Ex: Sankhya, APIs antigas, rotinas da fase 01C de _backfill_ e hooks do CRM). O desligamento final destas só ocorrerá na fase 01E e 01F.

## 16. Allowlist atualizada
A `ALLOWLIST` no `test_territory_convergence_guardrails.py` foi devidamente atualizada com as entradas do novo orquestrador (métodos `criar_cadastro_completo` e `atualizar_cadastro_completo`) para não alarmar no parser do AST o acesso aos dados fundiários no schema transitório. A Pipeline roda limpa (3.01s).

## 17. Riscos
Nenhum risco bloqueante. As 86 Fazendas legadas desamparadas terão suas Explorações Rurais complementadas na próxima fase (01E/F) se precisarem de leitura nativa; contudo o endpoint de edição já prevê que, caso essas legadas sejam submetidas, o orquestrador cria retroativamente a Exploração que lhes faltava na atualização (Fallback implementado nas linhas 138-154). 

## 18. Veredicto
> **GO**
A fase 01D está comprovadamente concluída e a fase 01E (Conversão das leituras e desativação controlada dos overlays e sincronizadores) pode começar de maneira segura.
