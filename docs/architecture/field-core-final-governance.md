# FIELD-CORE Final Governance

## Caderno de Campo como Núcleo Operacional, Documental e Auditável da Safra

## 1. Visão Estratégica

O Caderno de Campo é o núcleo oficial da safra no AgroSaaS porque concentra a linha do tempo documental, operacional e auditável de tudo o que acontece no ciclo produtivo.

Na arquitetura oficial:

- a **safra** é o contexto
- o **Caderno de Campo** é a timeline oficial
- os demais módulos são **produtores e consumidores de eventos**

Isso significa que:

- `OperacaoAgricola` gera fatos operacionais
- `CadernoCampoEntrada` formaliza a linha do tempo canônica
- `Estoque` consome fatos de uso e movimentação
- `Financeiro` consome fatos para custos, DRE e apropriações
- `IA` consome a trilha consolidada para análise operacional e financeira
- `Auditoria` consome a cadeia histórica completa
- `PWA` atua como extensão offline do caderno, não como origem independente da verdade

O objetivo do FIELD-CORE foi transformar um conjunto de registros distribuídos em uma cadeia única, governada e rastreável.

---

## 2. Diagnóstico Arquitetural Consolidado

### Antes do FIELD-CORE

O domínio agrícola existia de forma parcialmente distribuída:

- operações agrícolas já geravam eventos relevantes
- havia timeline, mas não existia uma fonte canônica formal
- o status era parcial ou inconsistente em diferentes caminhos
- exportações existiam, mas sem cadeia documental unificada
- o PWA capturava eventos offline, mas ainda sem contrato documental completo

### Problemas encontrados

- múltiplas fontes de verdade
- timeline paralela entre operação, caderno e exportação
- ausência de governança clara de status
- rastreabilidade distribuída e, em alguns pontos, implícita
- inconsistência entre offline e online
- ausência de retificação documental explícita
- retenção documental sem contrato formal

### Decisões arquiteturais tomadas

- `CadernoCampoEntrada` foi definido como entidade central
- `OperacaoAgricola` permaneceu como gerador de fatos
- eventos passaram a ter contrato canônico
- status ganhou governança formal
- exportação ganhou modo oficial e modo auditoria
- assinatura técnica passou a ser server-side
- retificação passou a criar nova versão sem apagar o original
- o PWA foi definido como extensão offline do caderno oficial

---

## 3. Modelo Oficial do Caderno

### Entidade central

`CadernoCampoEntrada` é a entidade canônica do Caderno de Campo.

Ela representa a unidade documental oficial de evento da safra.

### Relações oficiais

- `Safra`: contexto principal da timeline
- `UnidadeProdutiva`: contexto territorial e de governança
- `Talhão`: local operacional do evento
- `OperacaoAgricola`: origem automática de fatos operacionais
- `Estoque`: consumidor de consumo, movimentação e evidência de uso
- `Financeiro`: consumidor de custos, apropriação e impacto operacional
- `Equipamentos`: fonte e destino de eventos de manutenção, abastecimento e uso
- `IA`: camada analítica sobre a timeline oficial
- `Auditoria`: trilha completa de fatos, versões, assinaturas e retenção

### Papel do `CadernoCampoEntrada`

Ele é a representação formal de:

- observação
- execução
- evidência
- inspeção
- visita técnica
- entrega de EPI
- aplicação
- pulverização
- colheita
- irrigação
- manutenção
- abastecimento
- ocorrência
- clima
- solo

---

## 4. Contrato Canônico do Evento

O contrato canônico consolida:

- `tipo_evento`
- `origem_evento`
- `origem_id`
- `origem_tecnica`
- `status_evento`
- `payload_operacional`
- `evidências`
- `timestamps`
- `proveniência`

### Tipos oficiais aceitos

- `PLANTIO`
- `PULVERIZACAO`
- `APLICACAO`
- `IRRIGACAO`
- `COLHEITA`
- `INSPECAO`
- `OCORRENCIA`
- `MANUTENCAO`
- `ABASTECIMENTO`
- `EXECUCAO_OPERACIONAL`
- `MONITORAMENTO`
- `VISITA_TECNICA`
- `EPI_ENTREGA`
- `OBSERVACAO`
- `CLIMA`
- `SOLO`

### Proveniência oficial

- `OPERACAO_AGRICOLA`
- `WEB_MANUAL`
- `PWA_OFFLINE`
- `IMPORTACAO`
- `SISTEMA`

### Proveniência técnica

- `OPERACAO_AUTO`
- `MANUAL_DIGITAL`
- `SYNC_PWA`
- `IMPORTACAO`
- `SISTEMA`

### Regras principais

- um evento deve ter origem explícita
- tipo de negócio e origem técnica são coisas diferentes
- a origem preserva o vínculo com a fonte geradora
- o contrato deve ser idempotente por origem
- o payload do PWA offline é um contrato futuro de entrada, não uma fonte paralela de verdade

---

## 5. Fluxo Operacional Oficial

Fluxo oficial:

`PLANEJAMENTO -> TAREFA -> EXECUCAO -> EVIDENCIA -> SINCRONIZACAO -> APROVACAO -> CONSOLIDACAO -> EXPORTACAO -> ASSINATURA -> RETENCAO -> RETIFICACAO -> AUDITORIA`

### Interpretação do fluxo

- **Planejamento**: origem da intenção operacional
- **Tarefa**: estruturação do trabalho no campo
- **Execução**: realização prática
- **Evidência**: foto, GPS, observação, documento, visita, EPI
- **Sincronização**: subida do que foi feito no offline
- **Aprovação**: validação técnica ou documental
- **Consolidação**: fixação oficial do evento
- **Exportação**: materialização documental
- **Assinatura**: validação técnica da exportação
- **Retenção**: preservação da cadeia
- **Retificação**: correção por nova versão
- **Auditoria**: leitura histórica e forense

### Pontos de auditoria

- criação
- atualização
- mudança de status
- rejeição
- consolidação
- assinatura
- exportação
- retificação
- cancelamento

---

## 6. Governança de Status

### Estados oficiais

- `RASCUNHO`
- `PENDENTE_SINCRONIZACAO`
- `SINCRONIZADO`
- `PENDENTE_APROVACAO`
- `APROVADO`
- `REJEITADO`
- `CONSOLIDADO`
- `CANCELADO`

### Transições permitidas

- `RASCUNHO -> PENDENTE_APROVACAO`
- `PENDENTE_SINCRONIZACAO -> SINCRONIZADO`
- `SINCRONIZADO -> PENDENTE_APROVACAO`
- `PENDENTE_APROVACAO -> APROVADO`
- `PENDENTE_APROVACAO -> REJEITADO`
- `APROVADO -> CONSOLIDADO`
- qualquer estado -> `CANCELADO` com justificativa e permissão adequada

### Regras de governança

- eventos críticos exigem aprovação
- eventos do `PWA_OFFLINE` exigem aprovação antes da consolidação
- eventos automáticos de operação podem nascer aprovados ou consolidados, quando originados com vínculo válido e consistência de safra/talhão
- transições de aprovação e rejeição exigem permissão operacional apropriada
- transições são registradas em histórico

### Papel do status

O status não é apenas um rótulo visual. Ele define a validade documental do evento.

---

## 7. Cadeia Documental

### Componentes da cadeia

- exportação oficial
- exportação auditoria
- hash documental
- protocolo documental
- assinatura técnica
- retenção histórica
- retificação
- reprocessamento
- versão vigente

### Regras oficiais

- exportação oficial usa apenas eventos válidos e vigentes
- exportação auditoria inclui cadeia completa
- hash documental permite verificar alteração pós-assinatura
- protocolo documental identifica a versão assinada
- assinatura é server-side e auditável
- eventos consolidados não são apagados fisicamente
- evidências associadas a eventos consolidados não devem ser removidas
- retificação não apaga o original
- retificação cria nova versão vinculada

### Preservação histórica

O histórico deve preservar:

- original
- rejeição
- cancelamento
- reprocessamento
- assinatura
- hash
- protocolo
- trilha de status

---

## 8. Papel Oficial do PWA

### Declaração oficial

O PWA não é origem paralela da verdade operacional.

O PWA é a extensão offline do Caderno Oficial.

### Responsabilidades do PWA

- capturar eventos em campo sem internet
- preservar contexto local de dispositivo
- registrar evidências operacionais
- sincronizar depois com o backend
- transportar proveniência offline
- permitir replay e reconciliação
- operar como camada de produtividade de campo

### Limites do PWA

- não cria uma timeline paralela
- não substitui aprovação documental
- não consolida sozinho eventos críticos
- não redefine a cadeia documental
- não é a fonte canônica final

### O que ainda falta evoluir no PWA

- ampliar o contrato de payload documental
- melhorar reconciliação de conflitos multi-device
- fortalecer evidência offline resiliente
- tratar anexos com tolerância a falha de conectividade
- melhorar experiência de uso rural em condições adversas
- consolidar filas de retry e replay
- deixar mais explícita a proveniência de eventos offline

### Integridade temporal

O PWA deve preservar:

- `client_created_at`
- `device_id`
- `origem_evento = PWA_OFFLINE`
- sincronização posterior sem perder o instante de origem

---

## 9. Compliance e Certificação

### Já atendido

- rastreabilidade básica por safra e talhão
- histórico de status
- exportação formal
- assinatura técnica
- hash documental
- retenção lógica de rejeitados e cancelados
- preservação de versão original em retificação

### Parcialmente atendido

- janela de edição e retificação
- governança mais rígida para eventos críticos
- validação documental de campo em cenários offline
- evidência anexada por tipo de evento
- aderência documental com granularidade de certificação

### Futuro

- perfis de exportação por certificadora
- trilhas específicas para MAPA
- trilhas específicas para GlobalG.A.P.
- trilhas específicas para Rainforest
- trilhas específicas para Fair Trade
- retenção parametrizada por tipo de evento
- regras de aprovação por perfil e por contexto

### Leitura prática

A base atual é boa para auditoria operacional e compliance evolutivo. Ainda precisa aprofundar regras específicas por certificação alvo.

---

## 10. Riscos Arquiteturais Remanescentes

Os riscos remanescentes não invalidam a arquitetura, mas precisam ser tratados na evolução do PWA e da operação em escala.

### Principais riscos

- sincronização offline extrema com conectividade intermitente
- conflito entre múltiplos dispositivos para o mesmo contexto de evento
- anexos offline com falha de upload ou duplicidade
- evidência sem persistência resiliente
- UX operacional rural em situação de baixa cobertura
- replay de eventos depois de longos períodos offline
- reconciliação manual de eventos críticos

### Risco mais importante

O maior risco remanescente é a distância entre captura offline e aprovação documental final. Essa distância precisa ser reduzida sem perder controle de governança.

---

## 11. Próximo Macro Ciclo: FIELD-PWA

O próximo ciclo arquitetural deve se chamar **FIELD-PWA**.

### Objetivo

Transformar o PWA em uma extensão offline documentalmente confiável do Caderno Oficial.

### Roadmap inicial

#### FIELD-PWA-01
- contrato documental offline do evento
- persistência local estruturada
- fila formal de sincronização

#### FIELD-PWA-02
- reconciliação e resolução de conflitos
- retentativa idempotente
- vínculo forte com evidências

#### FIELD-PWA-03
- aprovação posterior assistida
- trilha de retificação no PWA
- experiência de campo mais robusta

#### FIELD-PWA-04
- reforço de auditoria local
- anexos resilientes
- observabilidade de sync

#### FIELD-PWA-05
- refinamento de UX rural
- tolerância a baixa conectividade
- estabilidade em operação longa

---

## 12. Decisões Canônicas

As decisões abaixo são oficiais e devem ser preservadas na evolução do sistema.

1. `CadernoCampoEntrada` é a timeline oficial da safra.
2. `OperacaoAgricola` é gerador de fatos operacionais.
3. Eventos consolidados não são editados diretamente.
4. Reprocessamento gera nova versão vinculada ao original.
5. Exportação oficial usa apenas eventos válidos.
6. Exportação auditoria preserva a cadeia completa.
7. A assinatura técnica é server-side.
8. O hash documental protege a integridade do documento.
9. O evento rejeitado permanece rastreável.
10. O evento cancelado permanece rastreável.
11. O PWA não é fonte independente da verdade.
12. O offline é extensão do caderno oficial, não substituto dele.
13. A retenção documental é preservada por desenho.
14. A auditoria é parte da cadeia, não um sistema paralelo.

---

## 13. Conclusão

O FIELD-CORE consolidou o Caderno de Campo como núcleo operacional, documental e auditável da safra.

O resultado final é uma arquitetura em que:

- a safra é o contexto
- o caderno é a timeline oficial
- a operação gera fatos
- a exportação materializa a cadeia
- a assinatura valida tecnicamente
- a retificação corrige sem apagar
- a auditoria preserva tudo
- o PWA captura offline sem disputar a verdade operacional

Este documento deve ser usado como referência oficial para:

- evolução backend
- evolução frontend
- evolução do PWA
- onboarding técnico
- governança operacional
- auditoria
- compliance
- certificações futuras
