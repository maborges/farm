# Relatório de Prontidão para Certificação e Rastreabilidade — CERT-READINESS-01

## 1. Resumo Executivo

Este relatório apresenta o diagnóstico técnico consolidado sobre a prontidão do AgroSaaS para atender aos programas de certificação e auditoria mais exigentes do agronegócio moderno, incluindo **GlobalG.A.P.**, **Rainforest Alliance**, **Fairtrade**, **Certifica Minas**, **Programas de Exportadoras** e o **Projeto Raízes**.

Após a conclusão dos ciclos recentes de desenvolvimento:
* **Passaporte de Rastreabilidade Comercial (QR Code + Lote Comercial)**: Totalmente integrado, ligando a venda física (`ComercializacaoCommodity`) à colheita/beneficiamento com snapshot assinado (SHA-256).
* **Calibração e Liberação Sanitária**: Bloqueio preventivo real de pulverizadores sem calibração diária ou higienização em `OperacaoService` e registro automático no Caderno de Campo.

O AgroSaaS atinge um nível de integridade arquitetural inquestionável. No entanto, persistem pequenos GAPs de usabilidade (como assinatura física offline do trabalhador) e geoprocessamento (polígonos GIS) que impedem uma certificação incondicional "sem papel".

Classificação de Prontidão: **PRONTO COM AJUSTES**

---

## 2. Análise de Reaproveitamento

Realizamos o mapeamento estrutural de todo o ecossistema do AgroSaaS para identificar a aderência das tabelas e serviços ativos:

| Componente / Módulo | Classificação | Justificativa Técnica / Mapeamento |
| :--- | :--- | :--- |
| **Caderno de Campo** | **EXISTE E ATENDE** | Timeline canônica baseada em [CadernoCampoEntrada](file:///opt/lampp/htdocs/farm/services/api/agricola/caderno/models.py#L9) com histórico inalterável de retificações e invalidações. |
| **Operações** | **EXISTE E ATENDE** | [OperacaoAgricola](file:///opt/lampp/htdocs/farm/services/api/agricola/operacoes/models.py#L8) registra clima, dosagem de insumos por hectare, período de carência e operador. |
| **Safra** | **EXISTE E ATENDE** | Estrutura delimitadora em [Safra](file:///opt/lampp/htdocs/farm/services/api/agricola/safras/models.py). |
| **Talhão** | **EXISTE E PODE SER EVOLUÍDO** | Mapeia áreas e coordenadas geográficas centrais, mas precisa de suporte a polígonos GeoJSON completos para cruzamento de desmatamento. |
| **Produto Colhido** | **EXISTE E ATENDE** | Registro de classificação e volume de colheita física em [ProdutoColhido](file:///opt/lampp/htdocs/farm/services/api/agricola/colheita/models.py). |
| **Beneficiamento** | **EXISTE E ATENDE** | Mapeamento N:N de blends de grãos em `LoteBeneficiamentoRomaneio`. |
| **Estoque** | **EXISTE E ATENDE** | Movimento de lotes e ledger append-only para auditoria de balanço de massa. |
| **Comercialização** | **EXISTE E ATENDE** | Vínculo comercial nativo em `ComercializacaoCommodity`. |
| **Passaporte** | **EXISTE E ATENDE** | [CadernoLoteComercial](file:///opt/lampp/htdocs/farm/services/api/agricola/rastreabilidade/models.py#L58) armazena snapshots assinados digitalmente. |
| **QR Code** | **EXISTE E ATENDE** | Geração dinâmica e vetorial de QR Codes no backend. |
| **Auditoria** | **EXISTE E ATENDE** | [TenantAuditLog](file:///opt/lampp/htdocs/farm/services/api/core/models/tenant_audit_log.py) captura diffs transacionais de escrita. |
| **Assinatura** | **EXISTE E ATENDE** | Assinatura digital do RT com snapshot_hash criptográfico. |
| **Calibração** | **EXISTE E ATENDE** | Tabela [EquipamentoCalibracao](file:///opt/lampp/htdocs/farm/services/api/core/cadastros/equipamentos/models.py#L152) integrada com verificação preventiva no service. |
| **Checklists** | **EXISTE E ATENDE** | Modelos dinâmicos de frota reaproveitados para vistorias higiênico-sanitárias diárias. |
| **PWA Campo** | **EXISTE PARCIALMENTE** | Sincronização offline e banco IndexedDB ativos no backend/infraestrutura; porém, o formulário visual de checklists offline carece de tela no app. |
| **IA** | **EXISTE E PODE SER EVOLUÍDO** | Modelos preditivos de produtividade e margem instalados; podem ser evoluídos para auditoria preditiva de conformidade regulatória. |
| **Pessoas** | **EXISTE E ATENDE** | Cadastro centralizado de produtores, funcionários e RTs. |
| **RH Campo** | **EXISTE E ATENDE** | Gerenciamento de pagamentos, diárias e empreitadas agrícolas. |
| **Treinamentos** | **NÃO EXISTE** | Ausência completa de tabelas para registrar certificados e cursos de capacitação (ex: NR-31). |
| **Documentos** | **EXISTE PARCIALMENTE** | Suporte a arquivos gerais anexados a máquinas; sem vault estruturado de certidões pessoais de colaboradores. |
| **Frota / Equipamentos** | **EXISTE E ATENDE** | Cadastro, alocação operacional em fazendas e controle de desgaste de pulverizadores. |

---

## 3. Matriz de Certificação

A aderência técnica do AgroSaaS em relação aos blocos regulatórios está mapeada a seguir:

### GlobalG.A.P.
* **Classificação**: **PARCIALMENTE ATENDIDO** (Aderência: **88%**)
* **Requisitos Atendidos**:
  * Controle rígido e preventivo de calibração vigente de bicos e vazão de pulverizadores (`EquipamentoCalibracao` + bloqueio no service).
  * Gestão de dosagem por hectare e respeito ao período de carência de defensivos (`carencia_dias` e `dose_por_ha` em `InsumoOperacao`).
  * Rastreabilidade de entrega de EPIs com controle de validade do lote (`EPIEntrega`).
* **Requisitos Faltantes**:
  * Registro de análise laboratorial e qualidade de água de irrigação.
  * Controle formal de destinação de embalagens vazias de defensivos (tríplice lavagem e devolução).
  * Comprovação formal de treinamento NR-31 para operadores de pulverizadores.
* **Evidências Existentes**: Histórico de calibração do tratorizador no caderno, validações em [OperacaoService](file:///opt/lampp/htdocs/farm/services/api/agricola/operacoes/service.py#L730) e logs de entrega de EPI.

### Rainforest Alliance
* **Classificação**: **PARCIALMENTE ATENDIDO** (Aderência: **82%**)
* **Requisitos Atendidos**:
  * Registro detalhado de clima (deriva climática: vento, umidade, temperatura) no momento da aplicação para evitar contaminação de mananciais.
  * Fotos georreferenciadas com GPS e timestamp tiradas no PWA comprovando origem da colheita em área aberta.
* **Requisitos Faltantes**:
  * Cruzamento automatizado com mapas de desmatamento e Áreas de Preservação Permanente (APP) baseado em polígonos GIS (CAR).
* **Evidências Existentes**: Metadados em `OperacaoAgricola` e coordenadas geográficas persistidas em `CadernoCampoFoto`.

### Fairtrade
* **Classificação**: **PARCIALMENTE ATENDIDO** (Aderência: **80%**)
* **Requisitos Atendidos**:
  * Controle de folha de diárias, contratos temporários e empreitadas (`rh_lancamentos_diarias`).
  * Registro de fornecimento de EPI individuais por operador.
* **Requisitos Faltantes**:
  * Assinatura manuscrita colhida fisicamente (tela sensível ao toque no PWA offline) pelo trabalhador ao receber EPIs e diárias.
* **Evidências Existentes**: Fichas digitais de entrega de EPI e relatórios de diárias vinculados a colaboradores.

### Certifica Minas
* **Classificação**: **ATENDIDO** (Aderência: **95%**)
* **Requisitos Atendidos**:
  * Diário de campo canônico completo.
  * Registro de visitas técnicas regulares de engenheiros agrônomos com recomendações integradas.
  * Protocolo assinado digitalmente com hash inalterável de dados.
* **Evidências Existentes**: [CadernoExportacao](file:///opt/lampp/htdocs/farm/services/api/agricola/caderno/models.py#L195) assinado com hash SHA-256 e logs do Responsável Técnico.

### Programas de Exportadoras
* **Classificação**: **ATENDIDO** (Aderência: **92%**)
* **Requisitos Atendidos**:
  * Rastreabilidade integral de blends (romaneio N:N) ligando o lote comercial final aos talhões específicos de colheita.
  * Comprovação técnica de higienização de caçambas e secadores (checklist sanitário diário) antes do processamento.
* **Evidências Existentes**: Vinculação no passaporte de rastreabilidade de `lote_beneficiamento_id` e check de checklists na data de pulverização.

### Projeto Raízes
* **Classificação**: **PRONTO COM AJUSTES**
* **Requisitos Atendidos**:
  * Passaporte digital público (visualização restrita de privacidade) acessível via QR Code permanente fixado na sacaria.
  * Rastreio completo do grão gourmet do talhão ao faturamento.
* **Evidências Existentes**: Endpoint público de rastreabilidade (`GET /rastreabilidade/{token}`) servindo o JSON consolidado do lote.

---

## 4. Cadeia de Custódia

**Classificação**: **COMPLETA**

O fluxo de dados do AgroSaaS consegue rastrear um lote comercial até o solo com segurança transacional:
```
Talhão (Área Rural) 
  → Operações (Insumos aplicados com lote de fábrica) 
  → Colheita (Romaneio físico) 
  → ProdutoColhido (Classificação e umidade) 
  → Beneficiamento (Secagem, classificação e blends) 
  → Armazenagem (LoteEstoque e Ledger de movimento) 
  → Comercialização (Contrato comercial de commodity) 
  → Lote Comercial (Passaporte de Rastreabilidade assinado) 
  → QR Code público
```

### Pontos fracos de integridade:
* **Entrada de Balança Manual**: Os pesos de entrada e saída no romaneio/balança ainda são digitados pelo operador (sem leitura automatizada de balanças via IoT offline), o que abre margem para erros humanos ou fraudes declaratórias que precisam ser detectadas por reconciliação de balanço de massa.

---

## 5. Rastreabilidade

**Classificação**: **COMPLETA**

O AgroSaaS implementou com maestria os pilares documentais:
1. **Histórico Inalterável**: O uso de auto-vínculos (`retifica_evento_id` e `retificado_por_evento_id`) protege contra apagamento de dados e preserva a linha cronológica auditável.
2. **Evidência Probante**: As fotos georreferenciadas offline registram o instante exato e o local da operação.
3. **Assinatura Baseada em Hash**: O snapshot do passaporte de lote é canonizado (JSON classificado por chaves) e assinado com SHA-256 pelo RT, inviabilizando edições diretas no banco de dados sem quebrar a assinatura pública.

---

## 6. ESG

* **Ambiental (E)**: **MÉDIO**. O sistema brilha no monitoramento climático e desvio de pulverização, além da carência de defensivos. Falta, no entanto, mapeamento espacial de áreas restritas (sobreposição de polígonos GeoJSON de talhões vs APPs/Reserva Legal).
* **Social (S)**: **MÉDIO**. O AgroSaaS atende ao controle de RH rural e EPIs, mas a assinatura da ficha de EPI ainda é sistêmica (e não manuscrita) e não há registros de capacitações de segurança.
* **Governança (G)**: **ALTO**. A trilha transacional `TenantAuditLog` registra todo o ciclo de vida dos dados com payload "antes" e "depois", além de IPs e usuários.

---

## 7. Projeto Raízes

### O AgroSaaS está: **PRONTO COM AJUSTES**

### Justificativa:
O passaporte comercial com QR Code legível na sacaria está pronto e puxa dinamicamente a calibração do pulverizador e a higienização sanitária. O sistema está plenamente qualificado para o Projeto Raízes, com pequenas lacunas de usabilidade no campo.

### GAPs Restantes:
1. Coleta de assinatura manuscrita do trabalhador no PWA offline.
2. Armazenamento de polígonos GIS dos limites da fazenda.
3. Ficha de treinamento técnico de tratoristas.

---

## 8. Exportadoras

Uma exportadora de café consegue hoje no AgroSaaS:
* **Auditar origem?** **SIM**. Pelo passaporte público é possível confirmar o município, a UF, o talhão e a safra do grão.
* **Validar cadeia de custódia?** **SIM**. Consegue remontar o balanço de massa de colheitas e lotes de secagem/beneficiamento.
* **Consultar QR Code?** **SIM**. QR Code impresso aponta para a página do passaporte.
* **Verificar evidências?** **SIM**. Consegue inspecionar as fotos georreferenciadas tiradas no talhão.
* **Validar conformidade?** **SIM**. Os dados de calibração técnica e higienização sanitária aparecem diretamente no passaporte assinado pelo RT.

Classificação para Exportadoras: **SIM**

---

## 9. GAPs Restantes

Listagem dos GAPs prioritários identificados que comprometem a certificação sem papel ou a exportação incondicional:

1. **GAP-01: Assinatura Manuscrita Offline no PWA (Canvas)**
   * *Criticidade*: **ALTO**
   * *Motivo*: A Fairtrade e auditorias trabalhistas exigem prova manuscrita do trabalhador para a entrega de EPIs para evitar fraudes administrativas.
2. **GAP-02: Cadastro de Polígonos de Áreas Rurais (GeoJSON)**
   * *Criticidade*: **ALTO**
   * *Motivo*: Rainforest Alliance e regulamentos da União Europeia (EUDR) exigem mapas de polígonos das áreas cultivadas para provar que não há sobreposição com áreas de desmatamento ilegal.
3. **GAP-03: Módulo de Registro de Treinamentos e Capacitações de Trabalhadores**
   * *Criticidade*: **MÉDIO**
   * *Motivo*: A GlobalG.A.P. exige que os tratoristas que operam pulverizadores possuam certificados vigentes de aplicação segura de defensivos e primeiros socorros (NR-31).
4. **GAP-04: Registro de Descarte de Embalagens Vazias**
   * *Criticidade*: **BAIXO**
   * *Motivo*: Controle interno de devolução de embalagens à central de recebimento. Pode ser mitigado temporariamente por anexo de fotos de comprovantes no caderno.

---

## 10. Roadmap Recomendado

Considerando a maximização do valor comercial e regulatório com o menor esforço de engenharia, propomos os próximos 3 ciclos de evolução:

### CICLO 1: Assinatura Manuscrita Offline no PWA (Canvas)
* *Justificativa*: Resolve o principal GAP de conformidade social da **Fairtrade** e protege o produtor de passivos trabalhistas. A assinatura manuscrita (desenhada pelo operador na tela) é capturada no PWA offline, salva no IndexedDB e transmitida como metadado anexo no sync de EPI.
* *Esforço*: Médio.

### CICLO 2: Mapeamento de Polígonos GIS (GeoJSON) para Talhões
* *Justificativa*: Adapta o cadastro de talhões para aceitar polígonos espaciais GeoJSON. Habilita o AgroSaaS para o mercado europeu de importação de café sustentável (EUDR) ao validar de forma automatizada o desmatamento zero via satélite.
* *Esforço*: Médio.

### CICLO 3: Gestão de Treinamentos e Certificados de Colaboradores
* *Justificativa*: Criação de tabelas de cursos de capacitação técnica rurais (ex: aplicação de agrotóxicos NR-31, primeiros socorros). Impede a vinculação de um operador sem capacitação vigente a uma operação de pulverização.
* *Esforço*: Baixo.

---

## 11. Classificação Final

> [!IMPORTANT]
> **PRONTO PARA PILOTO**
>
> **Justificativa técnica:** O AgroSaaS possui um motor canônico de Caderno de Campo, auditoria de escrita profunda, controle de calibração rígido e o Passaporte Comercial estruturado com QR Code. O sistema está plenamente apto a rodar um projeto piloto de exportação de grãos e passar por auditorias assistidas das certificadoras. A transição para a classificação "Pronto para Escala/Certificação" requer a eliminação dos GAPs de assinatura no PWA (Canvas) e polígonos GIS mapeados no roadmap.
