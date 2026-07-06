# LAUNCH-R3 — Auditoria dos Custos de Mão de Obra (RH) e Apropriação Operacional

## 1. Resumo executivo

A auditoria confirma que o módulo de RH existe, é operacional e possui telas, rotas e testes próprios. Também existe integração financeira parcial: diárias e empreitadas podem gerar `Despesa` ao serem pagas.  
Mesmo assim, a cadeia econômica não está fechada de ponta a ponta. Não encontrei evidência de geração automática de `CostAllocation` a partir de execução de colaboradores, nem de uma ponte oficial de RH até DRE e rentabilidade sem intervenção manual.

Conclusão objetiva: **não**, toda operação executada por colaboradores ainda **não** gera automaticamente seus custos econômicos completos até `CostAllocation`, Financeiro, DRE e Rentabilidade.

Classificação do fluxo: **🟡 Parcial**.

## 2. Escopo auditado

Backend:

- `services/api/rh/`
- `services/api/campo/`
- `services/api/agricola/`
- `services/api/operacional/`
- `services/api/financeiro/`

Frontend:

- `apps/web/`
- `apps/campo/`

Testes:

- unitários
- integração
- Playwright
- E2E

## 3. Evidências encontradas

### 3.1 RH é operacional, não apenas cadastral

O domínio RH possui entidades específicas para colaborador, diária, empreitada, eSocial e segurança do trabalho.

- `ColaboradorRH` possui `tipo_contrato`, `valor_diaria`, `valor_hora`, `data_admissao`, `data_demissao`.
- `LancamentoDiaria` armazena `horas_trabalhadas`, `atividade`, `valor_diaria`, `status` e vínculo com `colaborador_id`, `unidade_produtiva_id` e `safra_id`.
- `Empreitada` armazena `quantidade`, `valor_unitario`, `valor_total`, `status` e vínculos de contexto.

Referência:

- [`services/api/rh/models.py:28-76`](</opt/lampp/htdocs/farm/services/api/rh/models.py:28>)
- [`services/api/rh/models.py:106-173`](</opt/lampp/htdocs/farm/services/api/rh/models.py:106>)

### 3.2 Há integração financeira parcial

O RH consegue gerar `Despesa` em dois pontos:

- `DiariaService.pagar_lote(...)` agrupa diárias por unidade produtiva e cria `Despesa` quando encontra um `PlanoConta` válido.
- `EmpreitadaService.pagar(...)` também cria `Despesa` com base no valor total da empreitada, novamente condicionado à existência de `PlanoConta`.

Isso comprova integração com o módulo financeiro, mas não comprova apropriação econômica oficial.

Referência:

- [`services/api/rh/service.py:143-206`](</opt/lampp/htdocs/farm/services/api/rh/service.py:143>)
- [`services/api/rh/service.py:257-297`](</opt/lampp/htdocs/farm/services/api/rh/service.py:257>)

### 3.3 Não há evidência de `CostAllocation` no fluxo de RH

Não encontrei, em `services/api/rh/`, qualquer chamada a `registrar_cost_allocation` ou escrita em `cost_allocations`.  
A busca no repositório mostrou `CostAllocation` amplamente usado em operações agrícolas e financeiras, mas não no fluxo RH.

Referências:

- `rg -n "CostAllocation|registrar_cost_allocation" services/api/rh ...` não retornou uso em RH.
- `services/api/agricola/custos/allocation_service.py` define o mecanismo oficial de alocação.
- `services/api/agricola/dre/service.py` consome `CostAllocation` como fonte oficial de custo.

Referências oficiais:

- [`services/api/agricola/custos/allocation_service.py:16-54`](</opt/lampp/htdocs/farm/services/api/agricola/custos/allocation_service.py:16>)
- [`services/api/agricola/dre/service.py:520-571`](</opt/lampp/htdocs/farm/services/api/agricola/dre/service.py:520>)

### 3.4 O DRE agrícola depende de `CostAllocation`, não de RH diretamente

O serviço de DRE agrícola consolida custos diretos e operacionais a partir de `CostAllocation`.  
Como RH não emite `CostAllocation`, o seu impacto econômico não entra na camada oficial de DRE da mesma forma que ocorre com outras origens já integradas.

Referência:

- [`services/api/agricola/dre/service.py:520-571`](</opt/lampp/htdocs/farm/services/api/agricola/dre/service.py:520>)

### 3.5 Frontend existe e expõe fluxo operacional de RH

Há telas para:

- painel de RH
- colaboradores
- ponto / diárias
- folha de pagamento
- empreitadas
- eSocial

O frontend usa consultas e mutações para `/rh/colaboradores`, `/rh/diarias`, `/rh/diarias/pagar-lote`, `/rh/empreitadas` e `/rh/empreitadas/{id}/pagar`.

Referências:

- [`apps/web/src/app/(dashboard)/dashboard/rh/page.tsx:104-220`](</opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/dashboard/rh/page.tsx:104>)
- [`apps/web/src/app/(dashboard)/dashboard/rh/ponto/PontoClient.tsx:40-172`](</opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/dashboard/rh/ponto/PontoClient.tsx:40>)
- [`apps/web/src/app/(dashboard)/dashboard/rh/folha-pagamento/FolhaPagamentoClient.tsx:41-125`](</opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/dashboard/rh/folha-pagamento/FolhaPagamentoClient.tsx:41>)

## 4. Fluxo auditado

### Cadastro do colaborador

- Existe.
- Backend: sim.
- Frontend: sim.
- Teste: sim.
- Integração: apenas cadastro e listagem.
- Intervenção manual: sim, para definir valores e contexto.

### Equipe / departamento / função

- Existe parcialmente.
- Há `Departamento` e vínculo em `ColaboradorRH`, mas não encontrei um motor econômico de equipe.
- Backend: sim.
- Frontend: sim.
- Teste: parcial.
- Integração: administrativa, não econômica.

### Ordem de serviço / campo / execução

- Existe parcialmente via outros módulos da plataforma.
- Para RH, não encontrei ponte automática que converta apontamento de campo em custo econômico oficial.
- Backend: parcial.
- Frontend: parcial.
- Teste: parcial.
- Intervenção manual: sim, nos lançamentos de diária / empreitada e na quitação.

### Apontamento / horas trabalhadas

- Existe.
- O modelo guarda `horas_trabalhadas`, mas não há evidência de cálculo automático de custo horário oficial até `CostAllocation`.
- Backend: sim.
- Frontend: sim.
- Teste: sim, para cadastro, não para apropriação econômica completa.

### Custo operacional / CostAllocation

- Existe parcialmente.
- Há geração de `Despesa` no pagamento de diárias e empreitadas.
- Não encontrei geração automática de `CostAllocation`.
- Backend: parcial.
- Frontend: não comprovado.
- Teste: não comprovado.
- Intervenção manual: sim, no fechamento/pagamento.

### Financeiro / centro de custos / DRE / rentabilidade

- Existe parcialmente.
- Financeiro recebe `Despesa` do RH.
- Não encontrei vínculo automático de RH com centro de custos nem trânsito oficial até DRE/rentabilidade via `CostAllocation`.
- Backend: parcial.
- Frontend: parcial.
- Teste: não comprovado para a cadeia completa.

## 5. Respostas obrigatórias

1. Existe apontamento de horas? **Sim**.
2. Existe equipe operacional? **Sim, parcialmente, via departamento/colaborador**.
3. Existe vínculo colaborador → operação? **Parcial**.
4. Existe custo horário? **Existe como campo (`valor_hora`), mas não como motor automático comprovado**.
5. Existe custo diário? **Sim, como `LancamentoDiaria.valor_diaria`**.
6. Existe custo automático da operação? **Parcial**.
7. Existe geração automática de `CostAllocation`? **Não encontrei evidência**.
8. Existe integração automática com Financeiro? **Sim, parcial, via `Despesa` em pagamento**.
9. Existe integração automática com DRE? **Não comprovada**.
10. Existe integração automática com Rentabilidade? **Não comprovada**.
11. Existe rastreabilidade completa? **Não**.
12. Existe intervenção manual? **Sim**.
13. O RH é apenas cadastral ou realmente operacional? **É operacional, mas a apropriação econômica ainda é parcial**.
14. Existe reutilização do serviço financeiro oficial de lançamentos operacionais? **Não encontrei no fluxo RH**.
15. Há um motor econômico único ou múltiplos caminhos independentes? **Múltiplos caminhos; RH não entra no mesmo caminho oficial de `CostAllocation`**.

## 6. Comparação com LAUNCH-R2

Os problemas encontrados em RH são **equivalentes em natureza** aos encontrados em Máquinas:

- existe registro operacional;
- existe alguma conversão para custo/financeiro em pontos específicos;
- falta fechamento econômico oficial e uniforme;
- falta apropriação automática completa até `CostAllocation`, DRE e Rentabilidade;
- há intervenção manual em etapas de quitação/fechamento.

Diferença principal:

- em Máquinas, a integração com `CostAllocation` já está mais explícita na cadeia operacional;
- em RH, a integração visível é principalmente para `Despesa`, sem evidência de saída oficial para `CostAllocation`.

## 7. Testes

Há testes de integração para RH cobrindo:

- criação de colaborador
- lançamento de diária
- pagamento em lote de diárias
- criação de empreitada
- conclusão de empreitada
- proteção por autenticação

Mas não encontrei teste que valide:

- criação automática de `CostAllocation`
- reflexo em DRE
- reflexo em rentabilidade
- idempotência econômica da cadeia RH

Referência:

- [`services/api/tests/integration/test_rh.py:158-269`](</opt/lampp/htdocs/farm/services/api/tests/integration/test_rh.py:158>)

## 8. Classificação

**🟡 Parcial**

Motivo:

- RH existe e opera.
- Há integração financeira parcial.
- A cadeia não fecha automaticamente em `CostAllocation`, DRE e Rentabilidade.
- Persistem passos manuais de pagamento/fechamento.

## 9. Conclusão

A resposta para a pergunta central é **não**: a operação executada por colaboradores ainda não gera automaticamente seus custos econômicos completos e não atualiza de forma comprovada `CostAllocation`, Financeiro, DRE e Rentabilidade sem intervenção manual.

Isso **justifica sim** uma execução única **LAUNCH-W6 — Motor Oficial de Custos Operacionais**, desde que o objetivo seja unificar Máquinas, Equipamentos e Mão de Obra sob uma camada econômica comum e rastreável.

O ponto de corte técnico é claro: hoje existem fluxos operacionais e algumas conversões em `Despesa`, mas não existe um motor oficial único para apropriação econômica operacional.
