# FIELD-CORE-01 - Modelo Oficial do Caderno de Campo

> Objetivo: transformar o Caderno de Campo no núcleo oficial, transacional, rastreável e auditável da safra sem criar um caderno paralelo ou reescrever a arquitetura existente.

## Base analisada

Esta proposta foi construída a partir do estado real do projeto, com foco nos componentes já existentes:

- [Caderno de Campo - contexto funcional](/opt/lampp/htdocs/farm/apps/web/docs/contexts/agricola/essencial/caderno-campo.md)
- [Modelos do caderno](/opt/lampp/htdocs/farm/services/api/agricola/caderno/models.py)
- [Serviço do caderno](/opt/lampp/htdocs/farm/services/api/agricola/caderno/service.py)
- [Rotas do caderno](/opt/lampp/htdocs/farm/services/api/agricola/caderno/router.py)
- [Operações agrícolas](/opt/lampp/htdocs/farm/services/api/agricola/operacoes/service.py)
- [Modelo de operação agrícola](/opt/lampp/htdocs/farm/services/api/agricola/operacoes/models.py)
- [StorageService](/opt/lampp/htdocs/farm/services/api/core/services/storage_service.py)
- [AuditService](/opt/lampp/htdocs/farm/services/api/core/services/audit_service.py)
- [Tela web do caderno](/opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/agricola/caderno/page.tsx)
- [PWA de campo - home](/opt/lampp/htdocs/farm/apps/campo/src/app/(campo)/home/page.tsx)
- [PWA de campo - layout/sync](/opt/lampp/htdocs/farm/apps/campo/src/app/(campo)/layout.tsx)
- [Sync local do PWA](/opt/lampp/htdocs/farm/apps/campo/src/lib/sync/push.ts)
- [Sync pull do PWA](/opt/lampp/htdocs/farm/apps/campo/src/lib/sync/pull.ts)
- [Teste de isolamento multi-tenant](/opt/lampp/htdocs/farm/services/api/tests/e2e/test_caderno_tenant_isolation.py)

## 1. Diagnóstico Atual

### O que já existe e já funciona

- Há uma estrutura de dados específica para o caderno:
  - `CadernoCampoEntrada`
  - `CadernoCampoFoto`
  - `VisitaTecnica`
  - `EPIEntrega`
  - `CadernoExportacao`
- A operação agrícola já empurra eventos para o caderno quando é concluída como `REALIZADA` [operacoes/service.py](/opt/lampp/htdocs/farm/services/api/agricola/operacoes/service.py#L1023-L1048) [operacoes/service.py](/opt/lampp/htdocs/farm/services/api/agricola/operacoes/service.py#L1171-L1190).
- O caderno já possui:
  - timeline
  - alertas de safra sem registros recentes
  - upload de fotos
  - visita técnica
  - entrega de EPI
  - exportação PDF com modelos de certificação
- O isolamento por tenant já está coberto por testes e é uma base importante para compliance multi-tenant [test_caderno_tenant_isolation.py](/opt/lampp/htdocs/farm/services/api/tests/e2e/test_caderno_tenant_isolation.py).
- O storage já tem abstração compatível com local, S3 e MinIO [storage_service.py](/opt/lampp/htdocs/farm/services/api/core/services/storage_service.py).

### O que está parcial

- A timeline principal do caderno agrega entradas manuais e operações automáticas, mas ainda não incorpora de forma nativa `VisitaTecnica` e `EPIEntrega` [caderno/service.py](/opt/lampp/htdocs/farm/services/api/agricola/caderno/service.py#L93-L176).
- O tipo do evento ainda é uma string livre no modelo e no schema, o que fragiliza a taxonomia oficial [caderno/models.py](/opt/lampp/htdocs/farm/services/api/agricola/caderno/models.py#L17-L20) [caderno/schemas.py](/opt/lampp/htdocs/farm/services/api/agricola/caderno/schemas.py).
- A regra de 72h para retroatividade existe, mas hoje está aplicada só na criação quando o payload marca `digitalizacao_retroativa`; update e delete ainda dependem de reforço de governança [caderno/service.py](/opt/lampp/htdocs/farm/services/api/agricola/caderno/service.py#L28-L46) [caderno/router.py](/opt/lampp/htdocs/farm/services/api/agricola/caderno/router.py#L165-L192).
- A validação agronômica obrigatória ainda é parcial:
  - foto obrigatória por tipo
  - receituário para pulverização/aplicação
  - validação mais forte de CREA e assinatura
  - obrigatoriedade de evidência por evento crítico
- O PWA de campo ainda não é o canal nativo do caderno; hoje ele opera como shell offline-first para tarefas e sync geral [campo/home](/opt/lampp/htdocs/farm/apps/campo/src/app/(campo)/home/page.tsx) [campo/layout](/opt/lampp/htdocs/farm/apps/campo/src/app/(campo)/layout.tsx).

### O que conflita ou gera redundância

- Existem dois caminhos de exportação:
  - um caminho simples e operacional em rotas de operações
  - um caminho dedicado e mais rico em `CadernoExportacaoService`
- A timeline do caderno usa as entradas do caderno e, como fallback, recria eventos a partir de operações realizadas. Isso é útil para tolerância a falhas, mas cria risco de duplicidade e divergência se a convenção de vínculo não for respeitada [caderno/service.py](/opt/lampp/htdocs/farm/services/api/agricola/caderno/service.py#L122-L172).
- O PWA mantém sua própria base local e fila de sync. Isso é correto como cache/outbox, mas não deve evoluir para uma origem independente da verdade operacional [campo/sync/push](/opt/lampp/htdocs/farm/apps/campo/src/lib/sync/push.ts) [campo/sync/pull](/opt/lampp/htdocs/farm/apps/campo/src/lib/sync/pull.ts).

## 2. Definição Oficial do Caderno

No AgroSaaS, o Caderno de Campo é o **registro oficial da execução da safra**.

Ele não é apenas uma tela de histórico. Ele é o **diário operacional oficial** da safra, onde cada evento relevante do campo fica vinculado a:

- tenant
- safra
- talhão
- autor
- momento da ocorrência
- evidências
- origem técnica do evento
- impacto operacional
- impacto documental
- impacto financeiro, quando aplicável

O caderno é a linha do tempo oficial do trabalho realizado no campo. Operações, fotos, visitas, EPIs, observações e ajustes retroativos só são válidos como histórico oficial quando entram nessa cadeia oficial.

## 3. Modelo Oficial

### Entidade central

A entidade central continua sendo `CadernoCampoEntrada`, mas com um papel formalmente ampliado:

- é o registro oficial da ocorrência
- é a base da timeline oficial
- é o ponto de convergência entre operação, evidência, auditoria e exportação

### Papel das demais entidades

| Entidade | Papel oficial |
|---|---|
| `CadernoCampoEntrada` | Evento oficial da safra |
| `CadernoCampoFoto` | Evidência anexada ao evento |
| `VisitaTecnica` | Evento técnico especializado, com assinatura do RT |
| `EPIEntrega` | Evento de responsabilidade laboral e segurança do aplicador |
| `CadernoExportacao` | Snapshot documental assinado para auditoria/certificação |
| `OperacaoAgricola` | Fato operacional gerador de evento oficial |
| `OperacaoExecucao` | Fato transacional da execução que impacta estoque e custo |

### Relação com safra, UP e talhão

- `tenant_id` é obrigatório em tudo.
- `safra_id` é o eixo temporal e produtivo.
- `talhao_id` é o eixo espacial/operacional.
- O caderno deve ser consultado e exportado sempre no contexto de safra e talhão, mesmo quando houver visão global.

### Relação com operações

- Operação concluída gera evento oficial.
- O evento oficial não deve depender de digitação manual quando a operação já existe.
- O caderno não substitui a operação transacional, mas é a **narrativa oficial** da execução.

### Relação com estoque

- Consumo de insumos e devoluções continuam sendo responsabilidade das operações e execuções.
- O caderno deve carregar o rastro documental do consumo:
  - produto
  - dose
  - área
  - receituário
  - intervalo de segurança
- O estoque não deve ser a origem da narrativa do caderno. Ele é um consumidor e um espelho transacional.

### Relação com financeiro

- O caderno é fonte documental para custo e auditoria operacional.
- O custo efetivo nasce da operação/executação, mas a validação do evento precisa aparecer no caderno como prova operacional.
- A linha do tempo oficial deve permitir reconciliar custo, insumo e execução.

### Relação com IA

- A IA deve consumir eventos oficiais e evidências.
- A IA não deve escrever a verdade oficial diretamente.
- Sugestões de IA podem apoiar monitoramento, recomendação e triagem, mas a consolidação final é humana e/ou server-side.

## 4. Tipos Oficiais de Evento

### 4.1. Tipos já presentes ou implicitamente suportados

O código já reconhece, em maior ou menor grau:

- `OPERACAO_AUTO`
- `MONITORAMENTO`
- `VISITA_TECNICA`
- `EPI_ENTREGA`
- `OBSERVACAO`
- `CLIMA`
- `SOLO`

### 4.2. Tipos oficiais de negócio

Para o FIELD-CORE, os tipos de negócio oficiais devem ser normalizados em uma taxonomia única.

Proposta inicial:

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
- `CLIMA`
- `SOLO`

### 4.3. Regra de canonização

- `OPERACAO_AUTO` deve continuar existindo como **proveniência técnica**.
- O tipo de negócio deve refletir o que aconteceu de fato.
- Exemplo:
  - uma operação de pulverização pode entrar na timeline como `APLICACAO` ou `PULVERIZACAO`
  - o marcador `OPERACAO_AUTO` apenas indica que veio da operação transacional

Em outras palavras:

- `tipo` não deve ser apenas um rótulo técnico
- `subtipo` ou um campo de mapeamento deve preservar a granularidade real da operação

## 5. Fluxo Oficial

O fluxo oficial do FIELD-CORE deve ser:

**PLANEJAMENTO**  
→ **TAREFA**  
→ **EXECUCAO**  
→ **EVIDENCIA**  
→ **SINCRONIZACAO**  
→ **APROVACAO**  
→ **CONSOLIDACAO**  
→ **AUDITORIA**  
→ **IMPACTO_FINANCEIRO**  
→ **RASTREABILIDADE**

### Observações de governança

- Planejamento define a intenção.
- Tarefa define a ordem operacional.
- Execução define o fato ocorrido.
- Evidência torna o fato verificável.
- Sincronização traz o evento offline para a verdade oficial.
- Aprovação valida exceções e registros críticos.
- Consolidação fecha a linha do tempo.
- Auditoria observa o histórico imutável.
- Impacto financeiro é derivado.
- Rastreabilidade é a leitura formal do conjunto.

### Regras práticas do fluxo

- O fluxo deve ser predominantemente append-only.
- Alterações devem ser registradas como nova versão ou evento corretivo.
- Exclusão lógica deve ser exceção.
- Quanto mais crítico o evento, maior a exigência de evidência e aprovação.

## 6. Papel Oficial do PWA

O PWA de campo deve ser a **extensão offline do caderno oficial**.

Ele não deve ser uma origem independente da verdade.

### O que o PWA pode fazer

- criar eventos provisórios offline
- capturar fotos e geolocalização
- enfileirar sincronização
- registrar tarefas e execução operacional de campo
- enviar evidências
- preservar timestamp local do usuário

### O que o PWA não deve fazer

- não deve ser dono de uma timeline paralela
- não deve consolidar financeiramente eventos sozinho
- não deve aprovar conformidade crítica localmente
- não deve substituir a origem oficial do servidor

### Como tratar conflitos

- o cliente mantém outbox local
- o servidor recebe e decide a versão oficial
- conflitos devem preservar:
  - `client_created_at`
  - identidade do dispositivo
  - origem do evento
  - evidências
- o PWA pode mostrar conflito ao operador, mas não decide a verdade oficial

### Situação atual do PWA

Hoje o PWA de campo está forte para operação geral e offline-first, mas ainda não expõe o fluxo oficial do caderno como canal principal. Isso é um gap de produto, não uma falha da base técnica.

## 7. Governança Operacional

### Papéis

| Papel | Responsabilidade oficial |
|---|---|
| Planejador / gestor | cria tarefas e organiza safra |
| Operador | executa e registra campo |
| Agrônomo | supervisiona, complementa e valida |
| RT | assina, aprova e responde tecnicamente |
| Gerente | acompanha execução e pendências |
| Sistema | gera eventos automáticos e vínculos |

### Permissões oficiais

- criar evento
- ler timeline
- anexar evidência
- assinar
- exportar
- corrigir
- rejeitar
- consolidar

### O que deve ser append-only

- eventos oficiais da safra após consolidação
- evidências anexadas
- assinaturas
- exportações geradas

### O que pode ser editado

- rascunhos recentes
- eventos ainda não consolidados
- metadados operacionais não críticos, dentro da janela permitida

### O que deve gerar histórico

- toda alteração posterior a registro
- toda exclusão lógica
- toda correção retroativa
- toda assinatura
- toda exportação

### O que pode ser rejeitado

- evento sem safra/talhão
- evento sem autor válido
- evento crítico sem evidência mínima
- evento retroativo fora da regra sem justificativa
- assinatura com CREA inválido

## 8. Auditoria e Compliance

### Trilha obrigatória

Cada evento oficial deve preservar, no mínimo:

- tenant
- safra
- talhão
- autor
- papel do autor
- data de ocorrência
- data de criação no servidor
- origem do evento
- IP/dispositivo
- evidências
- justificativa de retroatividade, quando existir
- estado de aprovação
- assinatura, quando aplicável

### Integridade histórica

- a regra padrão deve ser não apagar o fato
- correções devem preferir novo evento de retificação
- soft delete deve ser a exceção, não a regra
- o histórico deve ser exportável para auditoria sem “limpeza” do passado

### Versionamento

O modelo atual já possui campos de auditoria, mas ainda não fecha um versionamento explícito de histórico. Isso deve evoluir incrementalmente com:

- versão do evento
- referência ao evento anterior
- motivo da substituição
- autor da correção

### Aderência futura a certificações

O caderno já aponta o caminho para:

- MAPA
- GlobalG.A.P.
- Rainforest Alliance
- orgânicos

Para suportar certificação forte, o sistema precisa preservar:

- rastreabilidade de insumos
- receituário
- fotos com geolocalização
- assinatura do RT
- histórico cronológico consistente
- evidência de EPI
- vínculo com safra/talhão

## 9. Riscos Arquiteturais

### 9.1. Duplicidade

- operação gera caderno automaticamente
- timeline também lê operação como fallback
- se o vínculo não for controlado, existe risco de evento duplicado

### 9.2. Inconsistência

- `tipo` ainda é livre
- `nivel_severidade` ainda é livre
- assinatura e criação manual não estão totalmente normalizadas

### 9.3. Perda de rastreabilidade

- exclusão lógica sem workflow forte
- retroatividade sem aprovação obrigatória em todas as rotas
- evidência não obrigatória em todos os tipos críticos

### 9.4. Risco offline

- o PWA já faz outbox e sync, mas ainda não é o canal oficial do caderno
- se o operador usar apenas o PWA, o fluxo documental completo ainda não está fechado

### 9.5. Risco documental

- há diferença de robustez entre exportações
- a timeline não contém todas as entidades relevantes
- visita técnica e EPI ainda não entram como cidadãos plenos da timeline

### 9.6. Risco de auditoria

- o histórico pode parecer “correto”, mas não estar suficientemente blindado para inspeção formal se o sistema crescer sem o reforço de governança

## 10. Roadmap Evolutivo

### FIELD-CORE-02 - Contrato Oficial

Objetivo:

- padronizar o tipo de evento
- separar proveniência técnica de tipo de negócio
- introduzir status oficial do evento
- alinhar `CadernoCampoEntrada` como contrato oficial

Entregas esperadas:

- enum/tabela de tipos oficiais
- mapeamento de operações para eventos oficiais
- contrato de evento offline/síncrono
- campo de origem e referência cruzada

### FIELD-CORE-03 - Aprovação e Auditoria

Objetivo:

- reforçar aprovação do RT
- fechar regra de retroatividade
- tornar correção rastreável
- integrar visita técnica e EPI na timeline oficial

Entregas esperadas:

- workflow de aprovação
- versionamento de correções
- trilha de auditoria reforçada
- assinatura com regras server-side mais rígidas

### FIELD-CORE-04 - PWA como Extensão Oficial

Objetivo:

- transformar o PWA no canal oficial de captura offline do caderno
- preservar a operação em campo sem internet

Entregas esperadas:

- formulários oficiais do caderno no PWA
- captura de evidência e GPS
- sincronização com resolução de conflitos
- visualização de pendências e status de aprovação

### FIELD-CORE-05 - Consumo por Estoque, Financeiro e IA

Objetivo:

- consolidar o caderno como origem operacional para leitura derivada

Entregas esperadas:

- consumidores financeiros da timeline oficial
- vínculos mais fortes com estoque e execuções
- IA lendo eventos oficiais e evidências
- painéis de conformidade e risco

## Diretriz final

O FIELD-CORE deve ser construído **em cima do que já existe**, não ao lado do que já existe.

Principio operacional:

- **uma safra**
- **uma timeline oficial**
- **uma cadeia oficial**
- **um PWA como extensão offline**
- **uma verdade operacional consolidada no servidor**

Se o projeto seguir essa linha, o Caderno de Campo deixa de ser apenas um registro auxiliar e passa a ser o núcleo oficial de rastreabilidade da safra, com base suficiente para auditoria, compliance e escala.
