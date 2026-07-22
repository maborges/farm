# PILOT-DRYRUN-03 — Auditoria do Roteiro de Dry Run

## 1. Resumo Executivo

O roteiro oficial do Dry Run (`RUNBOOK-01-EXECUCAO-D-5-A-D+7.md`) cobre corretamente governança, Wizard, estrutura produtiva, Campo PWA offline, estoque, ERP e cenários de falha, mas estava desatualizado em relação à arquitetura econômica consolidada em SOIL-PLAN-EXEC (04I/04J/04K/04L0/04M): não mencionava `ProductionUnit`, `OperacaoExecucao`, `CostAllocation`, Dashboard nem DRE, e ainda listava `Despesa` como parte da cadeia econômica ativa (obsoleto desde 04I). O fluxo de validação por passo (interface → persistência → regra de negócio → banco → eventos → Dashboard → DRE → evidência) não estava explicitado, e a escala de classificação de falhas (CRÍTICA/ALTA/MÉDIA/BAIXA/OBSERVAÇÃO) exigida pelo épico não existia no documento (apenas GO/GO COM RESSALVAS/NO-GO macro e P0-P3 nos relatórios de execução). Essas lacunas foram corrigidas diretamente no roteiro nesta auditoria, sem alterar arquitetura, sem reabrir programas encerrados e sem tocar código.

## 2. Objetivo da Auditoria

Verificar se o roteiro de Dry Run vigente cobre integralmente a jornada operacional em 9 blocos, reflete as decisões arquiteturais consolidadas (especialmente SOIL-PLAN-EXEC pós-04K/04M), segue o fluxo obrigatório de validação por etapa e usa a classificação de falhas exigida — e corrigir lacunas exclusivamente documentais quando encontradas.

## 3. Escopo Avaliado

- `docs/pilot/RUNBOOK-01-EXECUCAO-D-5-A-D+7.md` (roteiro oficial único, conforme PILOT-DRYRUN-01)
- `docs/pilot/PILOT-ERP-02-ROTEIRO-EXECUCAO-ASSISTIDA-CAFE-SANKHYA.md` (roteiro temático complementar)
- `docs/pilot/PLANO-MESTRE-PILOTO-01.md` (documento mestre)
- Relatórios de execução: `PILOT-DRYRUN-01`, `PILOT-DRYRUN-02`, `PILOT-DRYRUN-03-EXECUCAO-ASSISTIDA-RETOMADA`
- Relatórios SOIL-PLAN-EXEC-04I a 04M (decisões econômicas consolidadas)
- Demais roteiros/relatórios de piloto encontrados via busca (`PILOT-*`, `COFFEE-PILOT-*`, `ERP-PILOT-*`, `PERSON-PILOT-*`) — usados como contexto histórico, sem alteração.

Não houve leitura ou alteração de código de produção, migrations ou testes.

## 4. Cobertura Atual do Roteiro

| Bloco | Cobertura | Observação |
| --- | --- | --- |
| 1. Onboarding | Completa | Cenário A, D-5, D-1 |
| 2. Cadastros | Completa | D-4, massa mínima (seção 7) |
| 3. Planejamento | Parcial | "atividade planejada ou equivalente"; não detalha plano de safra/cronograma de insumos como etapa própria |
| 4. Execução (Web/Campo/Offline/Sync) | Completa | Cenário B, seção 15 (agora com 13 passos após correção) |
| 5. Motor Econômico | Corrigida nesta auditoria | Antes: ausente `ProductionUnit`/`CostAllocation`/Dashboard/DRE explícitos; agora presentes na seção 3 e no Cenário B |
| 6. Estoque | Completa | Cenário B e E |
| 7. Eventos | Completa | Engines citadas nas seções 3, 10, 18 |
| 8. Governança | Completa | RLS, tenant, matriz de responsabilidades |
| 9. Go Live | Completa | Seções 6, 12, 21 |

## 5. Conformidade com os Programas Consolidados

- **SOIL-PLAN-EXEC**: não conforme antes da correção (ausência total de `ProductionUnit`/`CostAllocation`/DRE/Dashboard; `Despesa` listada indevidamente como parte do domínio econômico ativo). Corrigido.
- **ERP**: conforme — separação `erp/*` comum vs. `sankhya/*` provider-specific mantida, sem reabrir decisões.
- **TERRITORY**: conforme — `UnidadeProdutiva`, propriedade e imóveis rurais tratados como estrutura fundiária; `ProductionUnit` agora tratada explicitamente como dimensão econômica separada (adicionado).
- **WIZARD**: conforme — onboarding limitado a Tenant+Owner+Assinatura, Wizard cuida da implantação depois; nenhuma alteração necessária.
- **CAMPO PWA**: conforme — já exigia Campo sem lógica paralela; reforçado com menção explícita ao `OperacaoService` compartilhado.

## 6. Lacunas Encontradas

1. `docs/pilot/RUNBOOK-01-EXECUCAO-D-5-A-D+7.md`, seção 3 (Arquitetura obrigatória): não citava `ProductionUnit`, `OperacaoExecucao`, `CostAllocation`, Dashboard, DRE — o motor econômico oficial pós-SOIL-PLAN-EXEC estava invisível no roteiro. Corrigido.
2. Mesma seção: listava `Despesa` junto da cadeia operacional ativa, sugerindo que a operação agrícola ainda gera `Despesa(OPERACAO_AGRICOLA)` — arquitetura removida em 04I. Corrigido (removida a menção e adicionada nota explícita de que esse registro não deve mais ser esperado).
3. Seção 15 (Cenário B): não exigia validação de `CostAllocation`, Dashboard nem DRE como parte do fluxo obrigatório de operação agrícola — apenas "estoque e custo" de forma genérica, sem amarrar à `ProductionUnit`. Corrigido com passos 8, 10, 11 e 12 novos.
4. Ausência geral do fluxo obrigatório por etapa (preparar → executar → validar interface → validar persistência → validar regra de negócio → validar banco → validar eventos → validar Dashboard → validar DRE → evidência → classificar → prosseguir). Corrigido com nota introdutória no Cenário B; recomenda-se replicar a mesma nota nos Cenários A, C e D em ciclo futuro (ver seção 8).
5. Ausência da escala de classificação de falhas CRÍTICA/ALTA/MÉDIA/BAIXA/OBSERVAÇÃO exigida pelo épico — o roteiro só tinha a decisão macro GO/GO COM RESSALVAS/NO-GO. Corrigido com nova seção 20.1.

## 7. Etapas Obsoletas

- Seção 3 do RUNBOOK-01, menção a `Despesa` na cadeia operacional (removida — não é mais gerada pela operação agrícola desde SOIL-PLAN-EXEC-04I).
- Não foram encontradas referências a resolução de `ProductionUnit` por `.first()`/`created_at` no roteiro (o roteiro simplesmente não mencionava `ProductionUnit`, o que já foi corrigido acrescentando a exigência de resolução determinística).

## 8. Atualizações Documentais Recomendadas

Aplicadas nesta auditoria (arquivo `docs/pilot/RUNBOOK-01-EXECUCAO-D-5-A-D+7.md`):

- Seção 3: adicionado bloco "Motor econômico" com a cadeia oficial, obrigatoriedade de `ProductionUnit`, fonte econômica oficial, remoção de `Despesa(OPERACAO_AGRICOLA)`, Campo PWA sem lógica paralela e não-reparo de dados históricos.
- Seção 15 (Cenário B): passos renumerados de 9 para 13, incluindo validação de `ProductionUnit`, `OperacaoExecucao`/`CostAllocation`, Dashboard e DRE, e confirmação de ausência de `Despesa(OPERACAO_AGRICOLA)`; evidências expandidas.
- Nova seção 20.1: escala de classificação CRÍTICA/ALTA/MÉDIA/BAIXA/OBSERVAÇÃO por desvio, com campos obrigatórios de registro.

Recomendado para ciclo futuro (não aplicado nesta auditoria por estar fora do bloco com maior risco econômico e para manter a mudança mínima):

- Replicar a nota do fluxo obrigatório por etapa (interface→persistência→regra→banco→eventos→Dashboard→DRE→evidência→classificação) nos Cenários A, C e D, hoje descritos apenas como tabela de passos.
- Detalhar melhor o bloco "Planejamento" (plano de safra, cronograma de insumos) como passos explícitos do D-4, hoje implícito em "atividade planejada ou equivalente".

## 9. Critérios para Início do Dry Run

Mantidos os critérios de entrada já formalizados na seção 6 do RUNBOOK-01 (ambiente, tenant, Owner/Admin, `UnidadeProdutiva`, usuário operacional, massa mínima, PWA, ERP configurado/dispensado, janela D-5/D+7, responsáveis, contingência). Adicionalmente, para o motor econômico: confirmar que existe ao menos uma `ProductionUnit` resolvível deterministicamente para o cenário mínimo antes de iniciar o Cenário B, evitando bloqueio no meio da execução.

## 10. Conclusão

O roteiro já era estruturalmente maduro (critérios de entrada/sucesso/interrupção, matriz de responsabilidades, evidências padronizadas, cenários A-E), mas estava desalinhado com a arquitetura econômica mais recente e não trazia a granularidade de validação e classificação exigida pelo épico PILOT-DRYRUN-03. As lacunas identificadas eram documentais e foram corrigidas diretamente no roteiro, sem alterar arquitetura, sem reabrir os 13 programas encerrados e sem tocar dados históricos ou código.

**Veredicto: GO COM RESSALVAS** — roteiro atualizado está apto a conduzir o próximo Dry Run; ressalva aberta é a réplica do fluxo de validação granular nos Cenários A, C e D, recomendada para o próximo ciclo documental.
