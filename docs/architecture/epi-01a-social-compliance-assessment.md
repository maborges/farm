# Diagnóstico de Entrega de EPI e Conformidade Social — EPI-01A

Este documento apresenta a análise de reaproveitamento, a avaliação do estado atual das entidades e a proposta de evolução para atender aos requisitos de conformidade social e trabalhista das certificações (Fairtrade, Rainforest Alliance) e indicadores ESG Social no AgroSaaS.

---

## 1. Resumo Executivo

O AgroSaaS já possui no backend toda a modelagem necessária para gerenciar a entrega e a conformidade de Equipamentos de Proteção Individual (EPI). A análise revelou que o sistema dispõe de um catálogo unificado de insumos (com suporte a `ProdutoEPI` e registro de Certificados de Aprovação - CA), um cadastro especializado de colaboradores (`ColaboradorRH`), uma tabela de entregas (`EPIEntrega`) e governança documental de assinaturas imutáveis via hashes SHA-256 no Caderno de Campo.

O principal gap identificado é operacional e de sincronização offline:
1. O aplicativo de campo (PWA) não expõe uma tela ou formulário para registro de recebimento de EPI, nem possui um componente de canvas para assinatura eletrônica do trabalhador.
2. A rotina de sincronização offline (`sincronizar_eventos_offline`) cria o evento de caderno de campo, mas não instancia um registro na tabela `epi_entregas`, gerando inconsistências no histórico.

Este relatório detalha como estender as estruturas preexistentes para fechar o ciclo de conformidade sem introduzir novos módulos complexos ou redundantes.

---

## 2. Análise de Reaproveitamento

Foi mapeado o ecossistema existente na aplicação em relação ao fluxo de EPIs e RH:

| Componente | Classificação | O que é reaproveitado / estendido |
| :--- | :--- | :--- |
| **Pessoas** | **EXISTE E ATENDE** | Entidade central `Pessoa` e seus complementos de documentos e contatos. |
| **Colaboradores** | **EXISTE E ATENDE** | O modelo `ColaboradorRH` (tabela `rh_colaboradores`) com dados de cargo, tipo de contrato e vínculo ativo. |
| **RH Campo** | **EXISTE E ATENDE** | Lançamentos de diárias e empreitadas em andamento. |
| **Usuários** | **EXISTE E ATENDE** | A tabela `usuarios` para auditoria de quem lançou ou validou as entregas. |
| **Assinatura documental** | **EXISTE E PODE SER EVOLUÍDO** | A lógica de hashes SHA-256 e timestamps do `CadernoExportacao` e `LoteComercial` será estendida para a entrega de EPI. |
| **Auditoria** | **EXISTE E ATENDE** | Gravação automática de logs de escrita através do `BaseService` e `TenantAuditLog`. |
| **Caderno de Campo** | **EXISTE E ATENDE** | O caderno já prevê o tipo de evento `"EPI_ENTREGA"` com regras de revalidação e retificação documental. |
| **PWA** | **EXISTE E PODE SER EVOLUÍDO** | O aplicativo offline possui IndexedDB com suporte ao evento `"EPI_ENTREGA"` no log local. |
| **Evidências** | **EXISTE E ATENDE** | Estrutura de fotos georreferenciadas vinculadas a eventos. |
| **Upload de fotos** | **EXISTE E ATENDE** | Sincronizador de fotos com fila e compressão de imagem offline. |
| **Checklists** | **EXISTE E ATENDE** | Checagem de conformidade diária de máquinas e processos. |
| **Equipamentos** | **EXISTE E PODE SER EVOLUÍDO** | A tabela `cadastros_produtos` com `tipo = 'EPI'` e a tabela especialista `cadastros_produtos_epi` controlam a vida útil e os CAs do MTE. |
| **Treinamentos** | **NÃO EXISTE** | Registro de capacitação de NR-31 / uso correto de EPIs (deve ser modelado de forma enxuta futuramente). |
| **Documentos** | **EXISTE E ATENDE** | Tabelas de arquivos e documentos gerais por colaborador. |

### Justificativa Arquitetural:
Evitaremos a criação de qualquer microsserviço ou tabela paralela de RH. Utilizaremos o catálogo de produtos unificado (`Produto` + `ProdutoEPI`) para gerenciar os estoques físicos de EPIs, a tabela `rh_colaboradores` para identificar os trabalhadores e a tabela `epi_entregas` para auditar a recepção. Toda assinatura eletrônica será acoplada de forma descentralizada no snapshot documental e exportada oficialmente no Caderno de Campo.

---

## 3. Estado Atual

A infraestrutura atual está **parcialmente ativada**:
* O backend expõe endpoints `GET/POST /api/v1/caderno/epis` que lêem e gravam na tabela `epi_entregas`.
* A tabela `epi_entregas` possui o campo `assinatura_url` para salvar a prova visual da assinatura do colaborador.
* No entanto, o PWA não possui uma tela de captura e não preenche o banco de dados local com essa estrutura, e o serviço `sincronizar_eventos_offline` possui um gap de instanciação de `EPIEntrega`.

---

## 4. Colaboradores

Sim, o AgroSaaS possui entidades prontas:
* **Entidade**: `ColaboradorRH` em [rh/models.py](file:///opt/lampp/htdocs/farm/services/api/rh/models.py#L28).
* **Estrutura**: Ela se conecta via chave estrangeira com a tabela central `cadastros_pessoas` (onde residem o PII criptografado e LGPD-compliant) e adiciona os campos específicos de RH: cargo, tipo de contrato (CLT, DIARISTA, EMPREITEIRO, TERCEIRO, PJ), valor da diária e data de admissão.
* **Uso**: Esta entidade é perfeitamente adequada para representar o trabalhador que recebe o EPI.

---

## 5. EPI

Sim, o AgroSaaS possui modelagem de EPIs madura no catálogo de insumos:
* **Catálogo**: O modelo `Produto` em [produtos/models.py](file:///opt/lampp/htdocs/farm/services/api/core/cadastros/produtos/models.py#L204) aceita `tipo = 'EPI'`.
* **Regulatório**: Se o tipo for EPI, o modelo se relaciona 1:1 com `ProdutoEPI`, que armazena dados críticos como o número do Certificado de Aprovação do MTE (`ca_numero`), validade do CA (`ca_validade`), tipo de proteção (maos, respiratorio, etc.) e vida útil em meses (`vida_util_meses`).
* **Estoque**: Utiliza o motor tradicional de `ProdutoEstoque` e `EstoqueMovimento` para dar entrada por compras e baixa automática no estoque geral ao realizar a movimentação para o colaborador.

---

## 6. Assinaturas

Sim, a infraestrutura pode ser totalmente reaproveitada:
* A tabela `epi_entregas` possui a coluna `assinatura_url`.
* O mecanismo de imutabilidade baseia-se na serialização ordenada (JSON oficial) de todo o histórico de entregas do colaborador, calculando um hash SHA-256 no momento da geração do snapshot do caderno de campo.
* A assinatura manuscrita coletada no PWA (vetorial em SVG ou rasterizada em PNG) será enviada no payload, salva no storage do tenant e vinculada como evidência visual incontestável.

---

## 7. PWA

O aplicativo offline `@agro/campo` possui o IndexedDB (`caderno_events` com tipo `EPI_ENTREGA`) preparado para enfileirar as entregas.

**O GAP real consiste em:**
1. **Ausência de Interface de Registro**: Falta um formulário offline `/campo/epis/novo` no PWA.
2. **Ausência de Componente de Assinatura (Canvas)**: Falta uma biblioteca de desenho simples no PWA para que o trabalhador assine com o dedo no celular do operador/fiscal de campo.
3. **Persistência Completa no Sync**: O método `sincronizar_eventos_offline` cria apenas o log genérico em `CadernoCampoEntrada`, deixando a tabela `epi_entregas` vazia quando o fluxo vem do PWA offline.

---

## 8. Fairtrade

A ativação do fluxo de EPIs atende a requisitos fundamentais de conformidade Fairtrade (Critérios de Saúde e Segurança Ocupacional):
* **Entrega Documentada**: Comprova que o trabalhador recebeu o EPI adequado para a sua função.
* **Assinatura do Trabalhador**: Serve como declaração formal de que o funcionário foi treinado e recebeu os equipamentos corretos.
* **Retenção Documental**: Garante histórico imutável por tempo regulatório (guardado no snapshot assinado do Caderno de Campo).
* **Auditoria**: Inspetores podem cruzar a lista de aplicações químicas com as datas de entrega de máscaras de carvão ativo vigentes e assinadas pelos operadores.

---

## 9. ESG Social

A ativação do EPI gera métricas sociais auditáveis em tempo real:
* **Indicador de Cobertura**: `% de colaboradores com EPIs válidos / vigentes`.
* **Frequência de Trocas**: Média de tempo para substituição de luvas, botas ou máscaras.
* **Mitigação de Passivo Trabalhista**: Prova física incontestável em juízo de fornecimento de EPI, neutralizando processos judiciais por insalubridade.

---

## 10. Modelo Mínimo

A menor evolução possível consiste em:
1. **Vínculo Físico de Modelos**:
   * No backend, atualizar o schema `EPIEntregaCreate` para exigir `trabalhador_id` (vinculando a `ColaboradorRH`) e `produto_id` (vinculando a `Produto` com `tipo = 'EPI'`).
2. **Atualização do Sync**:
   * No `sincronizar_eventos_offline` de `CadernoCampoService`, se o tipo do evento for `"EPI_ENTREGA"`, chamar o `EPIEntregaService.criar` para gravar na tabela especialista `epi_entregas`.
3. **Captura no PWA**:
   * Adicionar no PWA o formulário de entrega de EPI contendo um canvas de assinatura simples (enviando a imagem base64 convertida no payload do evento).

---

## 11. Roadmap Proposto

* **EPI-01: Ajuste de Modelagem, Sync Backend e Dashboard (Esforço: Baixo)**
  * Ajustar chaves estrangeiras no backend.
  * Atualizar o `sincronizar_eventos_offline` para instanciar a entrega na tabela física `epi_entregas`.
  * Criar interface web no dashboard administrativo para visualização e auditoria das assinaturas de EPI.
* **EPI-02: Form e Assinatura Digital no PWA Offline (Esforço: Médio)**
  * Criar o formulário offline no PWA.
  * Implementar componente de assinatura manuscrita (HTML5 Canvas) no PWA.
  * Integrar o fluxo de armazenamento local e enfileiramento na fila de sync.
* **EPI-03: Relatórios de Cobertura e Alertas ESG (Esforço: Baixo)**
  * Implementar alertas automáticos na tela de Operações Agrícolas caso o operador associado esteja com EPI vencido/ausente.
  * Exportação de planilha de auditoria trabalhista para fiscais.

---

## 12. Recomendação Final

Recomendamos seguir o roadmap incremental. A modelagem básica do AgroSaaS já está pronta, necessitando apenas da costura operacional entre o evento de Caderno de Campo, o sync offline e a interface de coleta no celular. Isso trará conformidade trabalhista plena de forma rápida e segura.

---

## Pergunta Final Obrigatória

**Qual é o menor conjunto de alterações necessárias para que o AgroSaaS passe a possuir comprovação auditável de entrega de EPI compatível com Fairtrade, Rainforest Alliance e auditorias trabalhistas?**

**Resposta Técnica:**
O menor conjunto de alterações necessárias é:
1. **Backend**: Ajustar `sincronizar_eventos_offline` para instanciar a linha física na tabela `epi_entregas` quando receber eventos offline do tipo `EPI_ENTREGA`.
2. **PWA**: Adicionar o formulário de entrega de EPI e um componente de HTML5 Canvas para captura da assinatura do trabalhador (convertida em imagem e transmitida como base64 no payload).
3. **Auditoria**: Expor no relatório de exportação do Caderno de Campo a lista consolidada de entregas com suas respectivas assinaturas e vigência do CA do fabricante.
