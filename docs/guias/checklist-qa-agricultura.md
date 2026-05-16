# Checklist QA — Módulo Agricultura

## Objetivo

Checklist objetivo para validar o fluxo principal do módulo Agricultura sem depender de interpretação livre do testador.

Documento base relacionado:

- [workflow-atricultura.md](/opt/lampp/htdocs/farm/docs/guias/workflow-atricultura.md)

## Capturas de referência

### Dashboard Agrícola

![Dashboard Agrícola](./assets/agricola-dashboard.png)

### Safras

![Safras](./assets/agricola-safras.png)

## Validação específica de IA

- [ ] Quando a funcionalidade usar IA, a interface deixa isso claro
- [ ] A explicação da IA está ligada aos dados reais da funcionalidade
- [ ] A IA sugere uma ação prática e compreensível
- [ ] O texto não parece genérico ou solto do contexto da safra

## Pré-requisitos

- [ ] Usuário autenticado
- [ ] Tenant correto selecionado
- [ ] Fazenda cadastrada
- [ ] Talhões cadastrados
- [ ] Plano de conta de despesa ativo
- [ ] Plano de conta de receita ativo
- [ ] Produtos/insumos cadastrados
- [ ] Estoque inicial carregado, se aplicável

## Massa mínima

- [ ] Fazenda `Fazenda Santa Helena`
- [ ] Talhão A1 com `30,00 ha`
- [ ] Talhão A2 com `25,00 ha`
- [ ] Talhão B1 com `20,00 ha`
- [ ] Safra `Soja 2025/26`
- [ ] Área total da safra `75,00 ha`

## 1. Safra

### Cadastro

- [ ] Acessar `/agricola/safras`
- [ ] Criar safra com cultura `Soja`
- [ ] Informar ano agrícola `2025/26`
- [ ] Vincular A1, A2 e B1
- [ ] Salvar sem erro

### Validação

- [ ] Safra aparece na listagem
- [ ] Status inicial é `PLANEJADA`
- [ ] Safra aparece em `/agricola/dashboard`

## 2. Orçamento

### Cadastro

- [ ] Acessar `/agricola/planejamento`
- [ ] Selecionar a safra criada
- [ ] Cadastrar ao menos 5 itens de orçamento
- [ ] Salvar orçamento sem erro

### Validação

- [ ] Custo total previsto é exibido
- [ ] Receita esperada é exibida
- [ ] Margem projetada é exibida
- [ ] Ponto de equilíbrio é exibido

## 3. Mudança de fase

- [ ] Avançar a safra para `PREPARO_SOLO`
- [ ] Confirmar que o status mudou
- [ ] Confirmar que a safra mudou de fase no dashboard

## 4. Operações de campo

### Cadastro

- [ ] Acessar `/agricola/operacoes`
- [ ] Registrar operação `CALAGEM`
- [ ] Registrar operação `ADUBACAO`
- [ ] Informar custo total nas operações

### Validação

- [ ] Operações aparecem na listagem
- [ ] Operações aparecem no caderno de campo
- [ ] Custos são refletidos no resumo financeiro da safra

## 5. Plantio

- [ ] Avançar a safra para `PLANTIO`
- [ ] Registrar ao menos 1 operação `PLANTIO`
- [ ] Validar que a operação foi aceita na fase correta

## 6. Fenologia

### Cadastro

- [ ] Acessar `/agricola/fenologia`
- [ ] Registrar 2 ou mais observações fenológicas

### Validação

- [ ] Registros aparecem na listagem
- [ ] Filtro por safra funciona
- [ ] Dashboard agrícola exibe estágio atual ou reflexo do dado

## 7. Monitoramento

### Cadastro

- [ ] Acessar `/agricola/monitoramento`
- [ ] Registrar 1 ocorrência leve
- [ ] Registrar 1 ocorrência crítica

### Validação

- [ ] Ocorrências aparecem na listagem
- [ ] Ocorrências aparecem no caderno, se integradas
- [ ] Alertas executivos aparecem no dashboard da safra, se aplicável
- [ ] Se houver IA, o risco e a ação recomendada ficam claros

## 8. Desenvolvimento

- [ ] Avançar a safra para `DESENVOLVIMENTO`
- [ ] Registrar 2 operações coerentes com a fase
- [ ] Validar recálculo de custo acumulado

## 9. Caderno de campo

- [ ] Acessar `/agricola/safras/{id}/caderno`
- [ ] Validar presença de operações
- [ ] Validar presença de monitoramentos
- [ ] Registrar 1 entrada manual
- [ ] Testar exportação do caderno

## 10. Colheita

- [ ] Avançar a safra para `COLHEITA`
- [ ] Confirmar mudança no dashboard agrícola

## 11. Romaneios

### Cadastro

- [ ] Acessar `/agricola/romaneios`
- [ ] Registrar 3 romaneios
- [ ] Informar quantidade e preço

### Validação

- [ ] Romaneios aparecem na listagem
- [ ] Produção total é calculada
- [ ] Receita total é calculada
- [ ] Financeiro da safra reflete os romaneios

## 12. Beneficiamento

- [ ] Acessar `/agricola/beneficiamento`
- [ ] Criar 1 lote de beneficiamento
- [ ] Vincular lote à origem correta
- [ ] Validar perda/quebra registrada

## 13. Financeiro da safra

- [ ] Acessar `/agricola/safras/{id}/financeiro`
- [ ] Validar `total_operacoes > 0`
- [ ] Validar `total_romaneios > 0`
- [ ] Validar `receita_total > 0`
- [ ] Validar `despesa_total > 0`
- [ ] Validar lucro bruto
- [ ] Validar ROI

## 14. Cenários

### Cadastro

- [ ] Acessar `/agricola/safras/{id}/cenarios`
- [ ] Criar ou revisar cenário `BASE`
- [ ] Criar cenário `Otimista`
- [ ] Criar cenário `Pessimista`

### Validação

- [ ] Cálculo de receita bruta aparece
- [ ] Cálculo de custo total aparece
- [ ] Cálculo de margem aparece
- [ ] Resultado líquido aparece
- [ ] Se houver IA, a explicação do cenário está conectada aos números

## 15. Comparativo de cenários

- [ ] Acessar `/agricola/safras/{id}/cenarios/comparativo`
- [ ] Selecionar 3 cenários
- [ ] Confirmar carregamento sem erro
- [ ] Validar colunas com receita, custo, margem, depreciação, IR e resultado líquido
- [ ] Validar detalhe por unidade produtiva
- [ ] Se houver IA, ela resume diferenças e ajuda na decisão

## 16. Dashboard executivo da safra

- [ ] Acessar `/agricola/safras/{id}/dashboard`
- [ ] Validar cards principais
- [ ] Validar alertas executivos
- [ ] Validar resumo do cenário base
- [ ] Validar comparativo executivo
- [ ] Validar ranking por unidade produtiva
- [ ] Se houver IA, validar destaque visual e utilidade prática da explicação

## 17. Dashboard agrícola global

- [ ] Acessar `/agricola/dashboard`
- [ ] Validar presença da safra no acompanhamento
- [ ] Validar gráfico de produção x meta
- [ ] Validar dados financeiros resumidos
- [ ] Validar bloco de fenologia

## Casos negativos mínimos

- [ ] Tentar criar safra com área acima da área do talhão
- [ ] Tentar registrar operação em fase não permitida
- [ ] Tentar registrar operação com data futura
- [ ] Tentar abrir safra de outro tenant
- [ ] Tentar comparar cenários insuficientes

## Critério de aprovação

- [ ] Fluxo completo executado sem erro bloqueante
- [ ] Dados refletem corretamente nas telas dependentes
- [ ] Integrações agrícola-financeiras funcionam
- [ ] Cenários e comparativo funcionam
- [ ] Dashboards mostram dados coerentes
- [ ] Toda funcionalidade com IA destaca seu uso e sua utilidade operacional

## Matriz Final

| Tela | Dado esperado | Regra validada |
|---|---|---|
| `/agricola/safras` | safra criada e listada | criação da safra e validação de área |
| `/agricola/dashboard` | safra visível no acompanhamento | reflexo do status atual no dashboard |
| `/agricola/planejamento` | orçamento com KPIs preenchidos | cálculo previsto da safra |
| `/agricola/operacoes` | operações exibidas corretamente | persistência e restrição por fase |
| `/agricola/fenologia` | estágios registrados e filtráveis | vínculo correto com safra |
| `/agricola/monitoramento` | ocorrências persistidas | registro de eventos sanitários |
| `/agricola/monitoramento` | quando houver IA, leitura de risco e ação sugerida | apoio de IA no monitoramento |
| `/agricola/safras/{id}/caderno` | eventos consolidados na timeline | unificação do histórico operacional |
| `/agricola/romaneios` | produção e receita calculadas | entrada de colheita e cálculo de volume |
| `/agricola/beneficiamento` | lote com perda/quebra | rastreabilidade da pós-colheita |
| `/agricola/safras/{id}/financeiro` | despesa, receita, lucro e ROI | integração automática com financeiro |
| `/agricola/safras/{id}/cenarios` | cenários com indicadores calculados | motor de cenários da safra |
| `/agricola/safras/{id}/cenarios` | quando houver IA, interpretação útil dos números | apoio de IA na análise econômica |
| `/agricola/safras/{id}/cenarios/comparativo` | comparação sem erro entre cenários | consistência do payload comparativo |
| `/agricola/safras/{id}/dashboard` | cards e alertas executivos | leitura consolidada da safra |
| `/agricola/safras/{id}/dashboard` | quando houver IA, destaque visual e recomendação clara | apoio executivo assistido por IA |
