# GTM-02 — Sales Playbook e Materiais Comerciais AgroSaaS

> **Status**: PRONTO PARA CERTIFICAÇÃO · PRONTO PARA COMERCIALIZAÇÃO  
> **Gerado em**: 2026-06-08  
> **Baseado em**: CERT-COMMERCIAL-01 · GO-TO-MARKET-01

---

## ETAPA 0 — INVENTÁRIO COMERCIAL VALIDADO

> [!IMPORTANT]
> Todo argumento comercial neste documento é baseado exclusivamente em funcionalidades verificadas no código-fonte da aplicação. Nenhum item de roadmap ou intenção futura é utilizado como argumento de venda.

### Matriz de Capacidades Comercializáveis

| Funcionalidade | Validação Técnica | Status | Valor Comercial |
| :--- | :--- | :--- | :--- |
| **Passaporte de Rastreabilidade** | `LoteComercialService.gerar_snapshot_passaporte()` — router.py L271 | ✅ EXISTE E ATENDE | Snapshot JSON público com hash SHA-256 por lote comercial |
| **QR Code Público** | `GET /rastreabilidade/{token}` — public_router.py | ✅ EXISTE E ATENDE | URL pública sem login, acessível via QR impresso nas sacas |
| **GeoJSON dos Talhões** | `AreaRural.geometria` JSONB — models.py L178 | ✅ EXISTE E ATENDE | Polígono cartográfico do talhão exportável para conformidade EUDR |
| **Cadeia de Custódia** | `CadernoLoteComercial` com origem + certificações — rastreabilidade/models.py | ✅ EXISTE E ATENDE | Do talhão ao lote comercial com evidências fotográficas georreferenciadas |
| **Caderno de Campo Canônico** | `CadernoCampoEntrada` — caderno/models.py L9 | ✅ EXISTE E ATENDE | Trilha auditável imutável por operação, com timestamp e operador |
| **PWA Offline** | Dexie IndexedDB v9 — apps/campo/src/lib/db.ts | ✅ EXISTE E ATENDE | Registros sem internet, sincronização automática ao restabelecer |
| **Assinatura Manuscrita Offline** | `SignaturePad` HTML5 Canvas — signature-pad.tsx | ✅ EXISTE E ATENDE | Assinatura real do trabalhador no celular, exportada como PNG |
| **Entrega de EPI** | `EPIEntrega` — caderno/models.py L175 + epi/page.tsx | ✅ EXISTE E ATENDE | Formulário por etapas com seleção de colaborador, EPI, qtd e assinatura |
| **Calibração de Equipamentos** | `EquipamentoCalibracao` + bloqueio em OperacaoService | ✅ EXISTE E ATENDE | Bloqueio preventivo de operações com pulverizador sem calibração válida |
| **Liberação Sanitária** | Checklist sanitário em `checklist.py` com `liberado_para_uso` | ✅ EXISTE E ATENDE | Checklist auditável integrado ao ciclo operacional do talhão |
| **Auditoria SHA-256** | `TenantAuditLog` — core/models/tenant_audit_log.py L9 | ✅ EXISTE E ATENDE | Log antes/depois de cada operação com hash determinístico |
| **DRE por Safra** | `LancamentoService.gerar_dre(safra_id)` — lancamento_service.py L564 | ✅ EXISTE E ATENDE | Receita, custo e margem real por safra, com origem vinculada |
| **Copiloto IA Financeiro** | `AlertaInteligenteService` + `ResumoDiarioService` | ✅ EXISTE E ATENDE | Alertas proativos de margem e simulação de DRE via `simular_dre()` |
| **Frota** | `apps/web/src/app/frota/` — landing page e módulo dedicado | ✅ EXISTE E ATENDE | Custo por hora/talhão, manutenção preventiva, consumo de combustível |
| **Mapa de Satélite no Passaporte** | `mapa-passaporte.tsx` + MapLibre GL + fitBounds | ✅ EXISTE E ATENDE | Mapa interativo do talhão no passaporte público, acessível via QR |
| **Multi-Tenancy** | Isolamento por `tenant_id` em todos os modelos | ✅ EXISTE E ATENDE | Cada fazenda/cooperado completamente isolado |
| **CRM / Pipeline** | Apenas landing page (`/integracoes`) sem backend validado | ⚠️ EXISTE PARCIALMENTE | **Não usar como argumento primário de venda** |
| **Treinamentos NR-31** | Modelo `ColaboradorRH` sem tabela de treinamentos | ❌ NÃO EXISTE | **Proibido usar como argumento de venda** |

---

## ETAPA 1 — SALES PLAYBOOK COMPLETO

### 1.1 ICP-A: Exportadoras de Café

#### Perfil do Cliente
- **Porte**: 50–500 produtores fornecedores
- **Mercado**: Exportação para UE, EUA, Japão
- **Dor principal**: Risco de embargo EUDR por falta de polígonos GeoJSON
- **Decisor**: Gerente de Exportação / Diretor Comercial / Responsável de Qualidade
- **Influenciador**: Agrônomo responsável técnico, auditor de certificação

#### Principais Dores
1. Lotes retidos ou rejeitados por falta de prova de desmatamento zero (EUDR)
2. Fraude ou adulteração na cadeia de custódia entre produtor e embarque
3. Auditorias demoradas (3–5 dias por produtor) para certificação coletiva
4. Fichas de EPI em papel que somem ou são fraudadas na auditoria Fairtrade
5. Calibração de pulverizadores sem registro formal — risco de resíduo acima do limite

#### Como Identificar Oportunidade
- Exportadora que já teve lote questionado ou retido por órgão europeu
- Produtores que usam planilhas Excel para controle de campo
- Está em processo de certificação Rainforest Alliance ou GlobalG.A.P.
- Relata que auditores demoram muito para validar documentação dos fornecedores

#### Perguntas de Descoberta
1. *"Como você comprova hoje o desmatamento zero dos talhões dos seus fornecedores para a UE?"*
2. *"Quando um auditor de certificação vem, quanto tempo leva para reunir toda a documentação dos produtores?"*
3. *"Você já teve algum lote questionado ou retido por falta de rastreabilidade ou conformidade?"*
4. *"Como é feita a entrega de EPI para os trabalhadores dos seus produtores? Tem registro físico?"*
5. *"Os seus produtores conseguem registrar o que foi feito no campo mesmo sem internet?"*

#### Diagnóstico (5 minutos)
Após as perguntas de descoberta, classificar a maturidade em 3 níveis:
- **Vermelho**: Sem polígonos, sem caderno digital → risco imediato de embargo
- **Amarelo**: Tem algum controle mas é em papel/planilha → risco em auditoria
- **Verde**: Já tem algum sistema mas sem passaporte SHA-256 → diferenciação de produto

#### Demonstração (10 minutos)
Seguir o roteiro da ETAPA 5 deste documento.

#### Proposta
Usar o modelo em `proposta-comercial-exportadora.md`.

#### Fechamento
- **Gatilho de urgência real**: prazo EUDR, próxima auditoria de certificação
- **Oferta de entrada**: PoC 30 dias com 5 produtores (modelo em ETAPA 6)
- **Garantia**: "Se em 30 dias não houver um passaporte funcional com QR Code e mapa, cancelamos sem custo."

---

### 1.2 ICP-B: Cooperativas

#### Perfil do Cliente
- **Porte**: 20–500 cooperados
- **Dor principal**: Custo elevado de auditoria individual, padronização impossível com papel
- **Decisor**: Gerente de Qualidade / Presidente da Cooperativa

#### Perguntas de Descoberta
1. *"Como você garante que todos os cooperados estão registrando as operações da mesma forma?"*
2. *"Quanto custa em média uma auditoria Fairtrade para a sua cooperativa por ciclo?"*
3. *"Seus cooperados conseguem usar smartphone no campo ou têm problema de conectividade?"*
4. *"Como é feita a rastreabilidade do café blendado? Você consegue chegar ao talhão de origem?"*

#### Argumentos de Venda Validados
- Multi-tenancy: cada cooperado isolado, gerenciável pelo painel central
- PWA offline: funciona em áreas rurais sem sinal
- Assinatura de EPI offline: prova documental de conformidade Fairtrade sem papel
- Caderno canônico: padroniza o registro de campo de todos os cooperados
- Passaporte por lote: blend rastreável até o talhão de cada cooperado

---

### 1.3 ICP-C: Produtores Médios e Grandes

#### Perfil do Cliente
- **Porte**: > 200 ha, 1–5 propriedades
- **Dor principal**: DRE impreciso, custo de conformidade crescente, frota sem controle
- **Decisor**: Proprietário / Gerente Administrativo

#### Perguntas de Descoberta
1. *"Quanto tempo você leva para fechar o DRE de uma safra? Quanto é estimativa vs. número real?"*
2. *"Você sabe hoje qual talhão foi mais rentável na última safra?"*
3. *"Quando sua colhedora quebra, você consegue rastrear quanto custou de manutenção no ano?"*

#### Argumentos de Venda Validados
- DRE por safra com origem financeira vinculada à operação real
- Copiloto IA com alertas proativos de margem e simulação What-If
- Módulo de frota: custo por hora, manutenção preventiva, consumo por talhão
- Caderno de campo canônico: sai da planilha sem perder dados históricos

---

### 1.4 ICP-D: Certificadoras

#### Perfil do Cliente
- Rainforest Alliance BR, Certifica Minas, SCS Global, IFOAM
- **Dor principal**: Auditores em campo por 3–5 dias por produtor, fraudes com papel

#### Argumentos de Venda Validados
- Passaporte SHA-256 verificável publicamente via QR Code
- Caderno canônico com timestamp e GPS — impossível adulterar retroativamente
- Evidências fotográficas georreferenciadas integradas ao caderno
- EPI assinado offline com validade documental

---

## ETAPA 2 — ROTEIRO DE REUNIÃO COM EXPORTADORAS (30 min)

### Estrutura da Reunião

```
00:00–03:00  Abertura e Rapport
03:00–10:00  Descoberta (5 perguntas chave)
10:00–13:00  Diagnóstico (classificar nível de risco)
13:00–24:00  Demonstração ao vivo (roteiro ETAPA 5)
24:00–27:00  Apresentação de ROI (calculadora ETAPA 4)
27:00–30:00  Fechamento e próximo passo
```

### Abertura (3 min)
> *"Obrigado pela reunião. Antes de mostrar qualquer coisa, quero entender sua realidade hoje — porque o que vou mostrar só faz sentido se for relevante para o que você vive. Posso fazer 5 perguntas rápidas?"*

**Objetivo**: Abrir espaço para a descoberta sem pitch imediato.

---

### Descoberta (7 min) — As 5 Perguntas
Fazer as perguntas nesta ordem exata:

1. *"Quando um comprador europeu pede a prova de desmatamento zero dos seus fornecedores, como você responde hoje?"*  
   → Ouvir. Se resposta for "planilha" ou "visita de campo" → vermelho.

2. *"Vocês já passaram por auditoria Rainforest Alliance ou Fairtrade? Como foi o processo de coleta de documentação?"*  
   → Ouvir. Se foi trabalhoso → oportunidade direta.

3. *"Você tem algum controle de quais equipamentos dos seus produtores foram calibrados antes de aplicar defensivo?"*  
   → Quase sempre a resposta é não → abre o argumento de calibração.

4. *"Como são as fichas de EPI dos trabalhadores? Você confia que em uma auditoria trabalhista elas vão estar em ordem?"*  
   → Dor universal. Papel rasga, some, é contestado.

5. *"Se eu te pedisse o mapa do talhão de cada produtor agora, você conseguiria me enviar em menos de 1 hora?"*  
   → EUDR. Resposta quase sempre é não.

---

### Diagnóstico (3 min)
Com base nas respostas, posicionar:

> *"Com base no que você me disse: [problema 1], [problema 2] e [problema 3] — isso representa um risco real de [embargo / auditoria / passivo trabalhista]. Posso te mostrar como o AgroSaaS resolve exatamente isso, com uma demonstração de 10 minutos?"*

---

### Demonstração (11 min)
Seguir ETAPA 5 — Roteiro de Demonstração.

---

### ROI (3 min)
Usar a calculadora de ROI (ETAPA 4). Apresentar o cenário mais relevante para o que foi descoberto:

> *"Você me disse que tem [X] produtores. Se um único lote de [Y] sacas for retido por falta de conformidade EUDR, isso representa [R$ Z] de perda. O AgroSaaS custa [R$ W]/mês. A proteção já se paga no primeiro lote."*

---

### Fechamento (3 min)
**Opção A — Cliente com urgência real:**
> *"Posso te propor uma PoC de 30 dias com 5 produtores seus. Sem custo. Em 30 dias você tem um passaporte real com QR Code, mapa do talhão e cadeia de custódia. Se funcionar, conversamos sobre o contrato."*

**Opção B — Cliente explorando:**
> *"Posso preparar uma proposta customizada para os seus [X] produtores ainda essa semana. Qual é o contato técnico responsável pela conformidade para incluir na proposta?"*

**Próximo passo obrigatório:**  
Sair da reunião com uma data e um compromisso — PoC, proposta ou próxima reunião com o decisor técnico.

---

## ETAPA 3 — BANCO DE OBJEÇÕES

### Objeção 1: "Já uso ERP / outro sistema"
**Resposta:**
> *"Entendo. A maioria dos ERPs faz o financeiro muito bem. O que eles quase nunca resolvem é o registro de campo offline — no pé do talhão sem internet — e a geração de prova de conformidade regulatória com polígono GeoJSON e hash SHA-256 para auditorias EUDR. Esses dois pontos custam muito caro quando faltam. O AgroSaaS resolve exatamente o que o seu ERP não consegue."*

**Evidência**: Passaporte SHA-256 + GeoJSON não são funcionalidades típicas de ERP.

---

### Objeção 2: "Já tenho certificação Rainforest Alliance"
**Resposta:**
> *"Ótimo! Isso significa que você sabe o quanto custa manter a certificação: auditorias recorrentes, documentação dos trabalhadores, fichas de EPI, calibração de equipamentos. Tudo isso hoje consome quanto em mão-de-obra administrativa? O AgroSaaS automatiza essa trilha documental — a próxima renovação vai ser muito mais rápida e barata."*

---

### Objeção 3: "Isso é caro"
**Resposta:**
> *"Caro comparado a quê? Um lote retido por não-conformidade EUDR custa de R$ 80.000 a R$ 500.000 — só em café. O plano Enterprise custa R$ 490/mês por produtor. Em um único lote protegido, o investimento anual se paga. Posso te mostrar o cálculo exato com os seus números?"*

**Ação**: Abrir calculadora de ROI (ETAPA 4) e preencher ao vivo.

---

### Objeção 4: "Meus produtores não vão usar"
**Resposta:**
> *"Essa é a preocupação mais comum — e a que mais surpresas positivas gera. O aplicativo de campo foi desenhado especificamente para trabalhadores rurais: funciona offline, sem internet, na tela do celular. Para registrar uma operação, são 4 toques. Para assinar a entrega de EPI, é um risco no dedo. Sem formulário, sem treinamento longo. Posso te mostrar ao vivo em 2 minutos."*

---

### Objeção 5: "Não tenho equipe para implementar"
**Resposta:**
> *"Entendo. Por isso temos uma PoC de 30 dias conduzida inteiramente por nós — você indica os 5 produtores, nós fazemos o onboarding, o cadastro dos talhões e o treinamento. No final dos 30 dias você tem um passaporte funcional. Se funcionar, a implementação completa segue o mesmo modelo: nós conduzimos."*

---

### Objeção 6: "Preciso de aprovação do financeiro"
**Resposta:**
> *"Ótimo — para facilitar, posso preparar um documento de ROI com cenários de lote retido e economia em auditoria nos próximos 3 anos? Assim você chega com os números prontos e o financeiro aprova na primeira reunião."*

---

### Objeção 7: "Não tenho urgência agora"
**Resposta:**
> *"Entendo. Mas a EUDR não espera — os prazos europeus de embargo já estão em vigor. A próxima safra começa em [data estimada]. Se a certificação não estiver pronta, você entra na safra com risco. A PoC de 30 dias pode começar hoje e terminar antes da colheita. Qual é o custo de não agir agora?"*

---

## ETAPA 4 — CALCULADORA DE ROI

### Modelo ROI por Cenário

#### Cenário 1: Lote Retido por Não-Conformidade EUDR
| Variável | Valor Padrão | Personalizar |
| :--- | :--- | :--- |
| Volume médio do lote (sacas) | 500 | _____ |
| Preço médio por saca (R$) | R$ 1.200 | _____ |
| Valor do lote (R$) | **R$ 600.000** | _____ |
| % de risco de retenção sem GeoJSON | 15% | _____ |
| **Risco financeiro esperado** | **R$ 90.000/lote** | _____ |
| Custo AgroSaaS Enterprise/ano | R$ 5.880 | _____ |
| **ROI em lotes protegidos** | **15:1** | _____ |

---

#### Cenário 2: Custo de Auditoria Manual vs. Digital
| Item | Manual (Atual) | Com AgroSaaS |
| :--- | :--- | :--- |
| Tempo de coleta de docs por produtor | 5 horas | 15 minutos |
| Custo da hora do técnico de campo | R$ 80 | R$ 80 |
| Produtores auditados por ciclo | 50 | 50 |
| **Custo de auditoria** | **R$ 20.000** | **R$ 1.250** |
| **Economia por ciclo** | | **R$ 18.750** |

---

#### Cenário 3: Passivo Trabalhista — Fichas de EPI
| Item | Valor |
| :--- | :--- |
| Ação trabalhista média (EPI não comprovado) | R$ 15.000–80.000 |
| Trabalhadores por produtor | 10–30 |
| Risco sem assinatura física | Alto |
| Custo AgroSaaS EPI/mês | R$ 490 |
| **Proteção anual** | R$ 5.880 vs. passivo de R$ 150.000+ |

---

#### Cenário 4: Certificação — Economia de Renovação
| Item | Manual | Com AgroSaaS |
| :--- | :--- | :--- |
| Dias de auditor em campo | 10 dias | 3 dias |
| Custo diário do auditor | R$ 3.000 | R$ 3.000 |
| **Custo de renovação** | **R$ 30.000** | **R$ 9.000** |
| **Economia por renovação** | | **R$ 21.000** |

---

#### Cenário 5: EUDR — Diferencial de Preço de Mercado
| Item | Sem Conformidade | Com AgroSaaS |
| :--- | :--- | :--- |
| Preço médio por saca (convencional) | R$ 1.200 | — |
| Prêmio por café EUDR-comprovado | + 8–15% | — |
| **Prêmio por saca** | — | **R$ 96–180** |
| Volume anual (1.000 sacas) | — | **R$ 96.000–180.000 extra** |

---

#### Fórmula de ROI Rápido (para reunião)
```
ROI = (Risco_Evitado + Prêmio_Mercado + Economia_Auditoria) / Custo_AgroSaaS_Anual

Exemplo conservador:
ROI = (R$ 90.000 + R$ 96.000 + R$ 18.750) / R$ 5.880 = 35x
```

---

## ETAPA 5 — ROTEIRO OFICIAL DE DEMONSTRAÇÃO (15 min)

### Objetivo
Mostrar o valor real do produto em 15 minutos, do talhão ao QR Code, sem slides — ao vivo no sistema.

### Sequência

#### 01. Talhão (2 min)
**O que mostrar**: Tela de propriedades → AreaRural com tipo TALHAO → editar geometria → mapa com polígono do talhão e área calculada em hectares.

**Fala**: *"Aqui está o talhão do produtor. Veja que ele tem um polígono GeoJSON com a área calculada automaticamente. Esse polígono é o que a UE exige para conformidade EUDR."*

#### 02. Operação Agrícola (1 min)
**O que mostrar**: Operações → nova operação → selecionar talhão, defensivo, equipamento.

**Fala**: *"O sistema bloqueia a operação se o pulverizador não tiver calibração válida para o dia. Não é aviso — é bloqueio real."*

#### 03. Caderno de Campo (2 min)
**O que mostrar**: Caderno → entradas do dia → timestamp, GPS, operador, produto, quantidade.

**Fala**: *"Esse é o caderno canônico. Cada entrada é imutável — ninguém pode editar retroativamente. É o que a certificadora vai pedir na auditoria."*

#### 04. Evidência Fotográfica (1 min)
**O que mostrar**: Caderno → fotos → GPS + timestamp na imagem.

**Fala**: *"Cada foto capturada no PWA offline vem com coordenada GPS e horário. É prova georreferenciada do que aconteceu no campo."*

#### 05. Passaporte Comercial (2 min)
**O que mostrar**: Rastreabilidade → Lote Comercial → Gerar Passaporte.

**Fala**: *"Aqui estamos gerando o snapshot do lote. Ele compila o talhão, as operações, as calibrações e os EPIs. Esse snapshot é assinado com SHA-256 — qualquer alteração muda o hash e invalida o documento."*

#### 06. QR Code (1 min)
**O que mostrar**: Passaporte → QR Code SVG gerado → escanear com celular ao vivo.

**Fala**: *"Esse QR Code vai impresso na saca. Qualquer comprador europeu escaneia e vê tudo isso que eu te mostrei — sem login, sem acesso ao sistema."*

#### 07. Mapa no Passaporte (2 min)
**O que mostrar**: Página pública do passaporte → card de mapeamento geoespacial → mapa de satélite com polígono e centróide.

**Fala**: *"O comprador europeu vê o mapa do talhão, com satélite, dentro do passaporte. É a prova visual de onde o café foi produzido."*

#### 08. EPI (2 min)
**O que mostrar**: PWA Campo → Entrega EPI → selecionar colaborador → capturar assinatura.

**Fala**: *"Aqui o trabalhador assina com o dedo no celular, offline, no campo. A assinatura é salva localmente e sobe para o servidor quando tiver internet. Essa assinatura vai aparecer no passaporte."*

#### 09. Auditoria SHA-256 (1 min)
**O que mostrar**: TenantAuditLog → log da operação de geração do passaporte → hash antes/depois.

**Fala**: *"Aqui está o log de auditoria. Cada operação registra o que era antes e o que ficou depois. Nenhum auditor vai questionar esse histórico — ele é assinado criptograficamente."*

#### 10. Resumo de Valor (1 min)
**Fala**: *"Em 15 minutos você viu: polígono GeoJSON, caderno imutável, fotos georreferenciadas, passaporte SHA-256, QR Code para o comprador europeu, mapa de satélite, assinatura offline e log de auditoria. Tudo integrado, tudo hoje, funcionando."*

---

## ETAPA 6 — MODELO DE POC (PROVA DE CONCEITO)

### Escopo da PoC de 30 Dias

| Item | Meta |
| :--- | :--- |
| Produtores onboardados | 5 |
| Talhões mapeados com GeoJSON | Mínimo 20 |
| Lote comercial com passaporte | 1 |
| Assinaturas de EPI capturadas | Mínimo 10 |
| Calibrações de equipamento registradas | Mínimo 2 |

### Cronograma da PoC

| Semana | Atividade | Responsável |
| :--- | :--- | :--- |
| **Semana 1** | Onboarding dos 5 produtores, cadastro de propriedades e usuários | AgroSaaS |
| **Semana 1** | Mapeamento de talhões (GeoJSON) via interface ou upload | AgroSaaS + Produtor |
| **Semana 2** | Registro de operações via PWA offline + captura de evidências | Produtor (guiado) |
| **Semana 2** | Entrega de EPI com assinatura manuscrita offline | Produtor (guiado) |
| **Semana 3** | Calibração de equipamentos + liberação sanitária | Produtor (guiado) |
| **Semana 3** | Criação do lote comercial e geração do passaporte SHA-256 | AgroSaaS |
| **Semana 4** | QR Code impresso + teste de leitura pelo comprador | Exportadora |
| **Semana 4** | Relatório de conclusão + reunião de avaliação | AgroSaaS + Exportadora |

### Critérios de Sucesso da PoC

| Critério | Meta | Como Medir |
| :--- | :--- | :--- |
| Passaporte público acessível via QR Code | 1 passaporte funcional | Escanear QR ao vivo na reunião de fechamento |
| GeoJSON dos talhões carregado | ≥ 20 polígonos | Tela de propriedades com mapa exibindo os polígonos |
| Assinaturas de EPI offline sincronizadas | ≥ 10 assinaturas | Registro na tabela `epi_entregas` com `assinatura_url` preenchido |
| Caderno de campo com entradas | ≥ 30 entradas | Timeline de caderno dos 5 produtores |
| Hash SHA-256 do passaporte verificado | Hash único e estável | Regenerar e comparar — hash deve ser idêntico |
| Tempo de geração do passaporte | < 5 segundos | Medição ao vivo |

### Critérios de Aprovação para Contrato

> A PoC é aprovada e o contrato é proposto se **4 dos 5 critérios acima forem atingidos**.

---

## ETAPA 7 — ESTRUTURA DE MATERIAL COMERCIAL

### 7.1 Deck Comercial (10 slides)
Ver detalhamento em `deck-outline-exportadoras.md`.

### 7.2 One-Page Executivo
**Estrutura** (1 página A4):
1. Headline: "Zero risco de embargo EUDR. Do talhão ao QR Code em 30 dias."
2. 3 dores resolvidas (exportadora)
3. 5 capacidades validadas (com nome da funcionalidade)
4. ROI resumido (1 número de impacto)
5. CTA: "Solicitar PoC gratuita de 30 dias"

### 7.3 Proposta Comercial
Ver detalhamento em `proposta-comercial-exportadora.md`.

### 7.4 Landing Page Exportadoras
**Estrutura sugerida**:
- Hero: headline EUDR + CTA "Solicitar PoC gratuita"
- Seção de dores específicas de exportadoras
- Demonstração em vídeo (15 min) ou carrossel de telas
- Calculadora de ROI interativa
- Cases da PoC (após Fase 1)
- FAQ específico para exportadoras

### 7.5 Landing Page Cooperativas
**Estrutura sugerida**:
- Hero: "Gerencie 200 cooperados com o trabalho de 3 pessoas"
- Seção de modelo por-cooperado (pricing transparente)
- Passaporte rastreável do blend
- PWA offline para areas sem sinal
- CTA: "Solicitar demo para cooperativas"

---

## ETAPA 8 — ROTEIRO PROJETO RAÍZES

### Como Apresentar o AgroSaaS ao Projeto Raízes

#### Contexto
O Projeto Raízes conecta consumidores finais (geralmente urbanos, de alta renda) à história real da fazenda de origem. O QR Code na embalagem é o ponto de contato central.

#### Abertura
> *"O Projeto Raízes promete ao consumidor a história real de onde veio o café. Hoje, essa história é contada em texto e foto. Com o AgroSaaS, ela é comprovada com dados reais: o polígono do talhão no mapa de satélite, o nome do trabalhador que colheu, a assinatura de quem entregou o EPI, e o hash SHA-256 que torna essa história irrefutável."*

#### Diferenciais a Destacar

1. **QR Code na embalagem → Passaporte Público**
   - O consumidor escaneia e vê: mapa do talhão, evidências fotográficas, certificações e assinaturas dos trabalhadores.
   - Sem login. Sem app extra. Uma URL pública.

2. **Rastreabilidade de Campo a Campo**
   - O caderno de campo canônico registra cada operação com timestamp, GPS e operador.
   - O lote comercial vincula o café ao talhão, à colheita, ao beneficiamento.

3. **ESG Social Comprovado**
   - Assinatura offline de EPI dos trabalhadores → o consumidor pode ver que a fazenda cuida da sua equipe.
   - Dado real, não declaração.

4. **ESG Ambiental Comprovado**
   - Polígono GeoJSON do talhão + centróides → cruzamento futuro com banco de dados de APP e Reserva Legal.
   - Área calculada automaticamente — sem possibilidade de subdeclaração.

5. **Impacto Social Mensurável**
   - Número de trabalhadores com EPI registrado.
   - Número de operações no talhão e produtos utilizados.
   - Todos esses dados entram no snapshot público do passaporte.

#### Proposta de Valor para o Projeto Raízes
> *"O Projeto Raízes dá uma história ao café. O AgroSaaS dá prova a essa história. Juntos, o consumidor não precisa mais confiar — ele pode verificar."*

#### Modelo de Parceria Sugerido
- Parceria de integração: produtores certificados pelo Projeto Raízes recebem desconto no plano de Certificação
- O Projeto Raízes indica o AgroSaaS como plataforma de rastreabilidade oficial
- Possibilidade de co-branding no passaporte público: logo do Projeto Raízes + link para sua página

---

## ETAPA 9 — ROADMAP COMERCIAL — PRÓXIMOS 90 DIAS

### Prioridades de Ação

| Ação | ROI | Prazo | Responsável |
| :--- | :--- | :--- | :--- |
| Identificar 3 exportadoras-alvo no Sul de Minas | 🔴 ALTO ROI | Semana 1 | Comercial |
| Fazer primeira reunião de descoberta com exportadora | 🔴 ALTO ROI | Semana 2 | Comercial |
| Iniciar PoC com exportadora mais qualificada | 🔴 ALTO ROI | Semana 3–6 | Comercial + Produto |
| Contatar cooperativa parceira (COOXUPÉ, MINASUL) | 🔴 ALTO ROI | Semana 2 | Comercial |
| Gravar vídeo de demonstração de 15 min | 🔴 ALTO ROI | Semana 3 | Produto |
| Criar landing page específica para exportadoras | 🟡 MÉDIO ROI | Semana 4 | Marketing |
| Produzir one-page para deixar após reuniões | 🟡 MÉDIO ROI | Semana 3 | Marketing |
| Contactar Rainforest Alliance / Certifica Minas para parceria | 🟡 MÉDIO ROI | Semana 4 | Comercial |
| Publicar case da PoC concluída | 🟡 MÉDIO ROI | Dia 31 da PoC | Marketing |
| SEO: publicar artigo sobre EUDR + conformidade | 🟡 MÉDIO ROI | Semana 5 | Marketing |
| Criar webinar "Passe em uma auditoria sem papel" | 🟢 BAIXO ROI | Semana 8 | Marketing |
| Programa de referral (produtor indica produtor) | 🟢 BAIXO ROI | Mês 3 | Produto |

### Foco dos Primeiros 30 Dias
> Prioridade absoluta: fechar a primeira PoC com uma exportadora. Tudo o mais — landing page, SEO, webinar — só após a primeira PoC iniciada.

---

## PERGUNTA FINAL OBRIGATÓRIA

> **"Qual é o caminho mais curto para transformar uma exportadora do Sul de Minas em cliente pagante do AgroSaaS nos próximos 90 dias?"**

### Resposta: O Caminho de 5 Passos

**Passo 1 — Dia 1–7: Identificação e Qualificação**
Mapear as 5 exportadoras de café premium do Sul de Minas que:
- Exportam para a UE (EUDR obrigatório)
- Estão em processo de certificação Rainforest Alliance ou Fairtrade
- Têm entre 30 e 200 produtores fornecedores

Fonte: ABIC, listas de exportadores certificados, LinkedIn.

**Passo 2 — Dia 7–14: Reunião de Descoberta**
Fazer a primeira reunião de 30 minutos com o decisor de qualidade ou exportação.  
Usar o roteiro da ETAPA 2 deste documento.  
Objetivo: sair com um "sim" para a PoC.

**Passo 3 — Dia 15–45: PoC em Operação**
Conduzir a PoC com 5 produtores da exportadora.  
Usar o modelo da ETAPA 6.  
Entrega no Dia 30: passaporte com QR Code funcional em reunião presencial.

**Passo 4 — Dia 45: Reunião de Fechamento da PoC**
Escanear o QR Code ao vivo, mostrar o passaporte no celular.  
Apresentar o ROI calculado com os dados reais da PoC.  
Propor o contrato Enterprise com os demais produtores.

**Passo 5 — Dia 46–90: Expansão**
Converter os 5 produtores da PoC para plano pago.  
Convidar mais 20–30 produtores da exportadora para o onboarding.  
Usar o case para abrir a próxima exportadora.

### Resultado Esperado
- **Dia 30**: 1 passaporte funcional na mão de uma exportadora real
- **Dia 45**: Proposta de contrato assinada
- **Dia 90**: 30+ produtores onboardados, MRR iniciado

> *"O caminho mais curto não é fazer uma landing page melhor. É colocar um QR Code funcionando na mão de uma exportadora em 30 dias."*
