# PILOT-ERP-01 - Simulação Real do Piloto Café + Sankhya

Data: 2026-07-06

## 1. Objetivo

Esta simulação consolida o caminho operacional real do primeiro piloto do AgroSaaS para um produtor de café exportador com ERP Sankhya.

O escopo desta leitura é estritamente documental e funcional:

- valida o que já existe no repositório;
- identifica o que já pode ser executado pelo usuário;
- aponta lacunas bloqueantes e não bloqueantes;
- organiza a ordem real de execução do piloto;
- preserva a estratégia Gateway-first, a Associação Oficial e o console de governança de pendências.

## 2. Base auditada

Documentos revisados:

- `docs/pilot/PLANO-MESTRE-PILOTO-01.md`
- `docs/pilot/GUIA-USUARIO-IMPLANTACAO-SAFRA-CAFE.md`
- `docs/pilot/RUNBOOK-01-EXECUCAO-D-5-A-D+7.md`
- `docs/implementation/reports/SANKHYA-SYNC-01-ESCOPO-PILOTO-CAFE.md`
- `docs/implementation/reports/SANKHYA-SYNC-02-MAPEAMENTO-CANONICO.md`
- `docs/implementation/reports/SANKHYA-SYNC-03-ESTRATEGIA-SINCRONIZACAO-PILOTO.md`
- `docs/implementation/reports/SANKHYA-SYNC-04-AUDITORIA-VINCULO-REGISTROS-AGROSAAS-SANKHYA.md`
- `docs/implementation/reports/INTEGRATION-DOMAIN-01-AUDITORIA-ENTIDADES-INTEGRACAO.md`
- `docs/implementation/reports/INTEGRATION-ARCH-03-ASSOCIACAO-REGISTROS-EXTERNOS.md`
- `docs/implementation/reports/INTEGRATION-ARCH-04-PLANO-IMPLEMENTACAO-ASSOCIACAO-EXTERNA.md`
- `docs/implementation/reports/INTEGRATION-EXT-01-FUNDACAO-ASSOCIACAO-EXTERNA.md`
- `docs/implementation/reports/INTEGRATION-EXT-02-SANKHYA-P0-ASSOCIACAO-EXTERNA.md`
- `docs/implementation/reports/INTEGRATION-EXT-03-P1-CADASTROS-MESTRES-ERP.md`
- `docs/implementation/reports/INTEGRATION-EXT-04-GOVERNANCA-PENDENCIAS-ASSOCIACOES-EXTERNAS.md`

Telas, rotas e serviços auditados:

- onboarding inicial em `/onboarding/configurar`;
- console Sankhya em `/dashboard/settings/integracoes/erp`;
- governança de associações pendentes no mesmo console;
- safra de café, rentabilidade, DRE e rastreabilidade no dashboard;
- estoque, compras, financeiro, comercialização e Campo PWA;
- serviços de integração Sankhya, Associação Oficial e testes unitários correspondentes.

## 3. Síntese executiva

O piloto está operacionalmente montado para leitura, implantação assistida, importação controlada e acompanhamento.

O que já existe e atende:

- onboarding do tenant;
- configuração inicial;
- console Sankhya com status, health, jobs, logs, timeline e teste de conexão;
- Associação Oficial com sistemas externos;
- pendências `PENDING` com reconciliação manual controlada;
- módulos de fazenda, safra, talhões, estoque, financeiro, rastreabilidade, rentabilidade e alertas;
- Campo PWA offline-first para operação de campo.

O que ainda é lacuna ou depende de validação operacional:

- cadastros societários com empresa/filial, quando o cliente exigir esse recorte;
- reconciliação manual de pendências ainda depende de conferência humana;
- financeiramente, a governança de títulos externos continua sujeita à qualidade da chave composta;
- tipo de operação e alguns masters P1 ainda dependem da estratégia específica do cliente;
- não há escrita bidirecional, portanto ajustes continuam centralizados no lado de origem do piloto.

## 4. Matriz de fluxos do piloto

| Fluxo | Rota / superfície | Situação | Evidência funcional | Leitura para o piloto |
| --- | --- | --- | --- | --- |
| Onboarding do tenant | `/onboarding/configurar` | EXISTE E ATENDE | Fluxo de configuração inicial com ano agrícola, unidade de área, fuso, moeda e categorias padrão. | Etapa obrigatória antes da operação assistida. |
| Configuração Sankhya | `/dashboard/settings/integracoes/erp` | EXISTE E ATENDE | Console Sankhya com configuração, status, health, jobs, logs, timeline e diagnóstico. | Ponto central da integração do piloto. |
| Teste de conexão | Console Sankhya | EXISTE E ATENDE | Endpoint e UI de teste já presentes e validados em documentação. | Gate de entrada para a carga inicial. |
| Sincronização/importação inicial | Console Sankhya + serviços Sankhya | EXISTE PARCIALMENTE | Há sync manual e serviços de pessoas, produtos, NFe e financeiro. | Exige execução controlada por escopo. |
| Associações oficiais P0 | Associação Oficial + helper Sankhya P0 | EXISTE E ATENDE | Pessoas, produtos, NFe, financeiro, unidade de medida e plano/natureza já usam vínculo oficial. | Base segura para evitar duplicidade. |
| Associações oficiais P1 | Associação Oficial + helper Sankhya P1 | EXISTE E ATENDE PARCIALMENTE | Empresa/filial, depósito, conta bancária, banco/agência/carteira, centro de custo/resultado e tipo de operação foram modelados onde havia entidade local segura. | Usar apenas quando a entidade local existir e a premissa operacional estiver explícita. |
| Pendências `PENDING` | Console Sankhya > governança | EXISTE E ATENDE | Lista operacional de vínculos não resolvidos e filtros por provider, entidade, ambiente e feature. | Necessário para limpeza de importação inicial. |
| Reconciliação manual | Console Sankhya > governança | EXISTE E ATENDE | Ação explícita exige `local_entity_type` e `local_entity_id`. | Controla risco sem criar vínculo silencioso. |
| Fazenda / Unidade Produtiva | Cadastro e Wizard | EXISTE E ATENDE | `UnidadeProdutiva` é pré-requisito para go-live e base territorial do piloto. | É o centro operacional da fazenda. |
| Safra de café | `/agricola/safras` e `/agricola/safras/[id]` | EXISTE E ATENDE | Safra, cultivo, talhões, área, fase, checklist e tarefas. | Estrutura principal da operação agrícola. |
| Talhões | Módulo agrícola e mapa | EXISTE E ATENDE | Talhões e georreferenciamento já aparecem como fluxo estável. | Necessário para rastreabilidade e custos. |
| Operações agrícolas | Caderno, tarefas, beneficiamento, colheita | EXISTE E ATENDE PARCIALMENTE | Há operações, caderno e rotinas por campo, mas parte do uso depende do dispositivo e do fluxo da equipe. | Operação real com disciplina de campo. |
| Estoque | `/dashboard/operacional/estoque` e `/suprimentos/estoque` | EXISTE E ATENDE | Saldos, lotes, movimentações, implantação assistida e alertas. | Essencial para insumos, colheita e expedição. |
| Compras | `/suprimentos/compras` e rotas correlatas | EXISTE E ATENDE | Solicitações, pedidos, cotações e integração com estoque. | Suporta abastecimento do piloto. |
| Financeiro | `/dashboard/financeiro/*` | EXISTE E ATENDE | Receitas, despesas, lançamentos, DRE, contas bancárias e comercializações. | Fecha o ciclo econômico do piloto. |
| Comercialização | `/dashboard/financeiro/comercializacoes` | EXISTE E ATENDE PARCIALMENTE | Há suporte para comercialização de commodity e receita vinculada. | Suficiente para o piloto, sem cobrir toda complexidade contratual de ERP. |
| Rastreabilidade | `/dashboard/agricola/rastreabilidade` | EXISTE E ATENDE | Cadeia lote → safra → talhão → operação → insumo/colheita. | Pilar para café exportador. |
| Rentabilidade | `/dashboard/agricola/rentabilidade` | EXISTE E ATENDE | DRE agrícola e visão de margem por safra. | Entrega o resultado esperado para gestão. |
| Alertas e recomendações | Cards e dashboard operacional | EXISTE E ATENDE | Alertas em runtime e recomendações acionáveis já estão integrados. | Apoia decisão diária e monitoramento. |
| Campo PWA | `apps/campo` + rotas de sincronização de campo | EXISTE E ATENDE | Offline-first, sincronização e coleta em campo. | Aplicável quando a operação usar equipe de campo ativa. |

## 5. Gaps bloqueantes

Os bloqueios reais do piloto não são de arquitetura de integração. São de preparo operacional.

| Gap | Por que bloqueia | Efeito no piloto |
| --- | --- | --- |
| `UnidadeProdutiva` inexistente ou inconsistente | O plano mestre exige unidade ativa antes do go-live. | Bloqueia implantação e operação assistida. |
| Conexão Sankhya sem validação | Sem teste de conexão não há carga inicial segura. | Bloqueia a entrada do piloto em estado útil. |
| Pendências `PENDING` críticas sem reconciliação | Associações sem vínculo oficial impedem segurança da importação. | Bloqueia uso confiável de pessoa, produto, nota ou título. |
| Fazenda sem talhão/estrutura mínima | A operação de café depende da hierarquia territorial. | Bloqueia rastreabilidade e apropriação correta. |
| Estoque inicial não conferido quando aplicável | Estoque é base para compra, consumo e colheita. | Bloqueia baixa confiável e saldos coerentes. |
| Dono do processo indisponível | O go-live assistido exige validação humana. | Bloqueia avanço de fase. |

## 6. Gaps não bloqueantes

| Gap | Impacto | Tratamento recomendado |
| --- | --- | --- |
| Empresa/filial sem representação local completa | Afeta apenas clientes com estrutura societária mais complexa. | Registrar premissa monoempresa/monofilial se for o caso do piloto. |
| Tipo de operação como regra de roteamento ainda não fechada | Não impede o piloto se o escopo for de leitura e operação controlada. | Manter como evolução acompanhada. |
| Centro de custo / centro de resultado sem master local dedicado | A operação ainda pode seguir por rateio e safra. | Tratar como maturação de P1/P2 conforme necessidade. |
| Comercialização parcial | O fluxo existe, mas não cobre todo contrato de ERP. | Usar apenas no que o piloto realmente operar. |
| Integração P1 fora da base local segura | A solução já sabe marcar pendência. | Reconciliar manualmente quando o cadastro local existir. |
| Campo PWA opcional em determinadas rotinas | Não trava o backoffice. | Habilitar apenas quando houver equipe de campo ativa. |

## 7. Ordem real de execução do usuário

1. Login e seleção do tenant.
2. Conclusão do onboarding inicial.
3. Abertura do Wizard de implantação.
4. Validação da `UnidadeProdutiva`.
5. Estruturação da fazenda e dos talhões.
6. Configuração da integração Sankhya.
7. Teste de conexão.
8. Importação inicial controlada.
9. Revisão das associações oficiais P0.
10. Reconciliar as pendências `PENDING` relevantes.
11. Revisar associações P1 quando houver entidade local segura.
12. Criar ou validar safra de café.
13. Registrar a estrutura operacional da safra.
14. Preparar estoque e compras.
15. Conferir financeiro, receitas, despesas e plano de contas.
16. Validar comercialização e rastreabilidade.
17. Consultar rentabilidade e DRE.
18. Ativar Campo PWA se a operação de campo estiver no escopo.
19. Acompanhar alertas, recomendações e logs nos primeiros dias.

## 8. Checklist de Go-Live assistido

- tenant ativo e selecionado;
- onboarding concluído;
- `UnidadeProdutiva` ativa;
- estrutura territorial mínima pronta;
- integração Sankhya configurada;
- teste de conexão aprovado;
- carga inicial executada;
- associações oficiais P0 conferidas;
- pendências `PENDING` críticas resolvidas;
- premissas de empresa/filial documentadas;
- estoque inicial validado quando aplicável;
- financeiro mínimo coerente;
- safra de café criada e vinculada aos talhões;
- Campo PWA preparado quando for usado;
- responsável do cliente disponível;
- evidência de go/no-go registrada.

## 9. Riscos específicos para produtor de café exportador com Sankhya

| Risco | Origem | Consequência | Mitigação |
| --- | --- | --- | --- |
| Duplicidade de parceiro, produto ou título | Código externo instável ou cadastro legado | Perda de rastreabilidade e retrabalho | Associação oficial + reconciliação manual + validação documental. |
| Mistura entre ambiente de produção e homologação | Configuração incompleta | Importação incorreta e dados contaminados | Filtrar por tenant, provider e ambiente. |
| `CODLOCAL` interpretado de forma errada | Depósito/local de estoque sem semântica única | Estoque ou rastreio vinculados ao local errado | Tratar associação apenas quando a semântica estiver validada. |
| Empresa/filial ignoradas em clientes plurissocietários | Premissa operacional não documentada | Contabilidade e fiscal inconsistentes | Registrar explicitamente a premissa do piloto. |
| Financeiro com chave composta fraca | Uso isolado de `DESDOB` ou código parcial | Títulos duplicados ou reconciliados errado | Exigir chave composta com documento, parceiro, vencimento e valor quando disponível. |
| Rastreabilidade incompleta no café | Falha em amarrar safra, talhão, lote e operação | Dificulta exportação e auditoria | Manter disciplina de cadastro e operação de campo. |
| Campo PWA sem rotina de sincronização | Dispositivo ou equipe não preparada | Perda de eventos de campo | Rodar validação offline-first antes do go-live. |
| Comercialização parcial demais para o contrato real | Expectativa comercial maior que o escopo do piloto | Ruído de implantação | Limitar o piloto ao que a base atual cobre com segurança. |

## 10. Conclusão operacional

O AgroSaaS já dispõe da base necessária para conduzir o piloto café + Sankhya em modo assistido, com leitura do ERP, Associação Oficial, pendências PENDING e monitoramento operacional.

O que falta para o go-live não é uma nova infraestrutura. É disciplina de execução:

- conferir premissas de empresa/filial;
- confirmar a estrutura territorial;
- validar a conexão Sankhya;
- importar com escopo controlado;
- reconciliar pendências;
- iniciar a safra com rastreabilidade e estoque coerentes;
- acompanhar os primeiros dias com o console de governança e os painéis operacionais.

## 11. Validação

Validação documental e de repositório executada com base no estado atual do código e das rotas existentes.

Validações técnicas recomendadas para fechar a etapa:

- `git diff --check`
- testes unitários de integrações Sankhya e Associação Externa
- testes de estoque, financeiro, comercialização e agricultura relacionados ao piloto

