# Objections Playbook — AgroSaaS

> **Como usar**: Identifique a objeção exata, use a resposta sugerida como base e adapte ao contexto do cliente.
> Cada objeção tem: Categoria · Resposta · Evidência de produto · Próximo passo.

---

## CATEGORIA 1 — PRODUTO / CONCORRÊNCIA

---

### "Já uso ERP (SAP, TOTVS, etc.)"

**Por que ocorre**: O cliente confunde gestão financeira/administrativa com rastreabilidade de campo e conformidade regulatória.

**Resposta:**
> *"Entendo — e provavelmente seu ERP faz bem a parte financeira e de estoque. O que ERPs convencionais quase nunca resolvem é o registro de campo offline, no pé do talhão sem internet, e a geração de prova de conformidade regulatória com polígono GeoJSON e hash SHA-256 para auditorias EUDR. Esses dois pontos custam muito caro quando faltam na hora da exportação. O AgroSaaS resolve o que o seu ERP não consegue — e pode coexistir com ele."*

**Evidência de produto**: `AreaRural.geometria` JSONB + `gerar_snapshot_passaporte()` SHA-256 — funcionalidades não existentes em ERPs convencionais.

**Próximo passo**: Perguntar — *"Qual ERP você usa? Vamos mapear exatamente onde ele para e onde o AgroSaaS começa."*

---

### "Já uso [Agrotools / Agronow / outro software agro]"

**Por que ocorre**: O cliente tem ferramenta de analytics ou satélite mas sem módulo de campo.

**Resposta:**
> *"Perfeito. Ferramentas de analytics e satélite têm foco em dados climáticos e BI. O que elas geralmente não têm é o registro operacional do campo com caderno canônico imutável, assinatura manuscrita offline do trabalhador e passaporte SHA-256 com QR Code para o comprador europeu. São camadas complementares — mas a prova documental que a certificadora pede precisa vir do campo, não do satélite."*

**Evidência de produto**: `CadernoCampoEntrada` imutável + `SignaturePad` canvas offline — exclusivos do AgroSaaS.

**Próximo passo**: Mostrar a diferença ao vivo — demo de 5 minutos no caderno de campo e EPI.

---

### "Já usei outro sistema e não funcionou"

**Por que ocorre**: Experiência ruim de adoção com sistemas complexos ou sem suporte.

**Resposta:**
> *"Entendo a frustração. Posso perguntar: o que falhou? Adoção dos produtores, custo alto, complexidade? Isso vai me ajudar a mostrar onde o AgroSaaS é diferente. Nosso PWA de campo foi desenhado especificamente para trabalhadores rurais: offline, 4 toques para registrar uma operação, assinatura com o dedo. E a PoC de 30 dias existe exatamente para você ver funcionando antes de assinar qualquer contrato."*

**Evidência de produto**: PWA Dexie offline — funciona sem internet, sem app store.

**Próximo passo**: Ouvir a falha anterior e posicionar a PoC como prova de que é diferente.

---

## CATEGORIA 2 — PREÇO / ORÇAMENTO

---

### "Isso é caro"

**Por que ocorre**: O cliente não conectou o preço ao risco que está evitando.

**Resposta:**
> *"Caro comparado a quê? Um lote de 300 sacas retido por falta de polígono GeoJSON representa R$ 420.000 em risco — a 15% de probabilidade de embargo, isso é R$ 63.000 de risco esperado por lote. O plano Certificação custa R$ 490/mês por produtor. Em um único lote protegido de um único produtor, o sistema já se paga por 10 anos. Posso calcular com seus números ao vivo?"*

**Evidência de produto**: ROI calculado em `roi-calculator-exportadora.md`.

**Próximo passo**: Abrir a calculadora de ROI e preencher com os dados reais do cliente.

---

### "Não temos orçamento este ano"

**Por que ocorre**: O orçamento está comprometido ou a decisão depende de aprovação.

**Resposta:**
> *"Entendo. Duas opções: a PoC de 30 dias é gratuita — sem necessidade de aprovação de orçamento. E posso preparar um documento de ROI para o financeiro que mostra o custo-benefício em 3 anos, com os cenários de lote retido e economia em auditoria. Assim você entra na próxima reunião de budget com os números prontos."*

**Próximo passo**: Propor a PoC gratuita como ponto de entrada sem necessidade de aprovação de orçamento.

---

### "O retorno é difícil de medir"

**Por que ocorre**: O cliente não visualiza ROI de conformidade regulatória.

**Resposta:**
> *"Na verdade é muito tangível. Temos 5 cenários mensuráveis: risco de embargo EUDR, custo de auditoria, passivo trabalhista de EPI, economia na renovação de certificação e prêmio de mercado por conformidade. Todos calculáveis com os dados da sua operação. Posso fazer o cálculo agora com os seus números?"*

**Próximo passo**: Preencher a calculadora ao vivo — transformar abstrato em número concreto.

---

## CATEGORIA 3 — ADOÇÃO / OPERAÇÃO

---

### "Meus produtores não vão usar"

**Por que ocorre**: Preocupação legítima com resistência de trabalhadores rurais a tecnologia.

**Resposta:**
> *"É a preocupação mais comum — e onde mais temos surpresas positivas. O aplicativo de campo foi desenhado para trabalhadores rurais com baixa familiaridade com tecnologia: funciona offline, sem internet, na tela do celular. Registrar uma operação são 4 toques. Assinar a entrega de EPI é um risco com o dedo no celular. Sem formulário, sem treinamento longo. Posso mostrar ao vivo em 2 minutos agora?"*

**Evidência de produto**: PWA campo com UX simplificado — `apps/campo/src/app/(campo)/campo/epi/page.tsx`.

**Próximo passo**: Demo ao vivo do PWA no celular — mostrar o fluxo de EPI em tempo real.

---

### "Não tenho equipe para implementar"

**Por que ocorre**: O cliente não tem time de TI ou de operações disponível para implantação.

**Resposta:**
> *"Por isso a PoC é conduzida 100% pela nossa equipe. Você indica os 5 produtores, nós fazemos o onboarding, o cadastro dos talhões e o treinamento. Você só precisa disponibilizar os produtores por 2 horas na primeira semana. O resto é por nossa conta. A implementação completa segue o mesmo modelo."*

**Próximo passo**: Apresentar o cronograma da PoC e o papel de cada parte.

---

### "É muito complicado para os trabalhadores rurais"

**Por que ocorre**: Preconceito sobre capacidade tecnológica de trabalhadores rurais.

**Resposta:**
> *"Entendo a preocupação. O app foi testado com trabalhadores rurais sem smartphone próprio. A tela principal tem 5 botões grandes. Para registrar uma aplicação de defensivo, são 4 toques. Para assinar o recebimento de EPI, é literalmente assinar com o dedo — igual assinar um papel. Vamos fazer um teste ao vivo agora com o meu celular?"*

**Próximo passo**: Demo ao vivo. Pedir para o próprio cliente testar o fluxo de EPI no celular.

---

### "Minhas operações são muito específicas — o sistema vai atender?"

**Por que ocorre**: Produtores com culturas diversas ou processos diferenciados.

**Resposta:**
> *"O caderno de campo é configurável — você define o tipo de operação, os insumos e os talhões. Já atende: soja, milho, café, algodão, pecuária, operações mistas. O que é fixo é a camada de rastreabilidade e conformidade — que é exatamente o que exportadoras e certificadoras exigem. O detalhe operacional de cada cultura você configura. Posso te mostrar como uma operação de café é configurada vs. uma de soja?"*

**Evidência de produto**: Templates operacionais configuráveis por cultura.

---

## CATEGORIA 4 — URGÊNCIA / TIMING

---

### "Não tenho urgência agora"

**Por que ocorre**: O cliente não tem deadline próxima de auditoria ou exportação.

**Resposta:**
> *"Entendo. Duas reflexões: primeiro, a EUDR não espera — os prazos europeus de enforcement já estão em vigor e os primeiros embargos documentais ocorreram em 2024. Segundo: o onboarding de produtores e o mapeamento dos talhões levam tempo. Se a próxima safra ou a próxima auditoria é em [X meses], começar a PoC hoje significa estar pronto. Começar depois pode significar chegar na auditoria sem o sistema operacional."*

**Próximo passo**: Perguntar data da próxima auditoria ou colheita para criar urgência real.

---

### "Vou esperar a próxima safra"

**Por que ocorre**: O cliente adia por não ver urgência imediata.

**Resposta:**
> *"Exatamente o que nossos clientes pensavam antes de ter um lote questionado. O mapeamento de 20 talhões leva 2 semanas. O caderno de campo precisa ter pelo menos 30 dias de histórico para ter valor em auditoria. Se você começa na próxima safra, a primeira auditoria vai chegar sem histórico operacional. Começar agora significa chegar na próxima safra com sistema rodando e histórico construído."*

---

### "Preciso avaliar mais opções"

**Por que ocorre**: O cliente está no início do processo de compra.

**Resposta:**
> *"Faz sentido. Peço apenas que você avalie as outras opções respondendo a estas perguntas: elas geram polígono GeoJSON do talhão? Têm passaporte SHA-256 com QR Code público? Têm assinatura manuscrita offline do trabalhador? Se sim — ótimo, compare. Se não — são ferramentas diferentes, não concorrentes diretos. Posso preparar um quadro comparativo para facilitar sua análise?"*

**Próximo passo**: Oferecer o quadro comparativo com Agrotools, SAP Agro e outros.

---

## CATEGORIA 5 — PROCESSO DECISÓRIO

---

### "Preciso de aprovação do financeiro"

**Por que ocorre**: O decisor técnico não tem autonomia de budget.

**Resposta:**
> *"Ótimo — para facilitar, posso preparar um documento de ROI com os dados que você me forneceu, mostrando o custo-benefício em 3 cenários para os próximos 3 anos. Assim você chega para o financeiro com números concretos em vez de uma proposta abstrata. Quando é a próxima reunião de orçamento?"*

**Próximo passo**: Preencher a calculadora de ROI e enviar por e-mail antes da reunião do financeiro.

---

### "Preciso envolver o time técnico antes"

**Por que ocorre**: A empresa tem equipe de TI que valida soluções.

**Resposta:**
> *"Ótimo — podemos fazer uma call técnica de 30 minutos com sua equipe de TI. Vou trazer nosso time de produto para responder questões de API, segurança LGPD, multi-tenancy e integração com o ERP atual. Quando você consegue agendar?"*

**Próximo passo**: Agendar call técnica com time de TI do cliente.

---

### "Já tenho certificação — não preciso mudar nada"

**Por que ocorre**: O cliente confunde ter a certificação com manter a conformidade.

**Resposta:**
> *"Ter a certificação é o começo — o desafio é a renovação. A Rainforest Alliance revisita a cada 2–3 anos e a EUDR é anual. O que você está usando hoje para gerar a trilha documental da próxima renovação? Se for papel e planilha, o custo de auditoria da próxima renovação vai ser igual ou maior que o atual. O AgroSaaS transforma a documentação contínua em processo automático — a renovação vira uma formalidade."*

---

### "Nossa certificadora não exige isso"

**Por que ocorre**: O cliente tem certificadora local menos rigorosa ou confunde compliance local com requisito de exportação.

**Resposta:**
> *"Para o mercado interno, talvez não. Mas se vocês exportam ou planejam exportar para a UE, a EUDR é lei europeia — não é a certificadora quem exige, é o importador europeu. E importadores europeus estão pedindo o GeoJSON dos talhões desde 2023. Se seu comprador europeu ainda não pediu, vai pedir — provavelmente antes da próxima safra."*

---

## REGRA GERAL DO PLAYBOOK

> [!IMPORTANT]
> **Nunca mencionar funcionalidades que não existem na aplicação.**
> CRM com pipeline completo e Treinamentos NR-31 **não estão implementados**.
> Não usar como argumento de venda em nenhuma circunstância.

> [!TIP]
> **A resposta para qualquer objeção segue o padrão A-B-C:**
> - **A**: Validar a preocupação (*"Entendo"* / *"Faz sentido"*)
> - **B**: Reposicionar com dado concreto ou evidência de produto
> - **C**: Propor próximo passo concreto (PoC, demo, calculadora, call técnica)
