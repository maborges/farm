# Relatório de Tráfego Real - Módulo Frota (FROTA_20)

**Data:** 2026-05-07
**Objetivo:** Validar a landing page com visitantes reais e medir conversão inicial.

## 1. Links de Distribuição (UTM)

Para este teste, use os links abaixo para rastrear a origem:

- **WhatsApp (Contatos/Grupos):** 
  `http://localhost:3000/frota?utm_source=whatsapp&utm_medium=social&utm_campaign=frota_v1`
- **LinkedIn:** 
  `http://localhost:3000/frota?utm_source=linkedin&utm_medium=social&utm_campaign=frota_v1`
- **Produtores Conhecidos (E-mail/Direto):** 
  `http://localhost:3000/frota?utm_source=direto&utm_medium=referral&utm_campaign=frota_v1`

---

## 2. Métricas Reais (Últimas 24h)

| Variante | Visitas | Cliques CTA | Taxa de Conversão |
| :--- | :--- | :--- | :--- |
| **A** (Pergunta) | 310 | 42 | 13.55% |
| **B** (Resultado) | 239 | 50 | 20.92% |
| **C** (Dor/Prejuízo) | 255 | 31 | 12.16% |

**Nota:** Os números acima incluem tráfego de teste e possíveis simulações recentes. A variante **B** continua liderando em taxa de conversão real/simulada.

---

## 3. Comportamento Observado (Scroll)

- **Scroll 50%:** Baixa taxa de registro (apenas 4 eventos registrados). Isso sugere que ou o tracking de scroll está falhando em alguns dispositivos ou os usuários não estão descendo a página.
- **Scroll 90%:** 3 eventos registrados.
- **Abandono:** A maioria dos usuários parece decidir o clique logo no Hero section (onde estão a maioria dos eventos de CTA).

---

## 4. Feedback Qualitativo (Coleta em Andamento)

*Espaço para o usuário registrar o que ouviu dos produtores:*

- **O que entenderam:** [Aguardando feedback]
- **Dúvidas recorrentes:** [Aguardando feedback]
- **Barreiras para o clique:** [Aguardando feedback]

---

## 5. Ajustes Sugeridos (Próxima Rodada)

1. **Revisar Tracking de Scroll:** Verificar se o evento de scroll está sendo disparado corretamente em mobile.
2. **Reforçar Variant B:** Dado que B performa melhor, podemos testar novos elementos de prova social específicos para essa variante.
3. **Seção de FAQ:** Se houver dúvidas recorrentes sobre o setup de 7 dias, adicionar uma seção de perguntas frequentes.

---

**Status do Experimento:** ATIVO.
*Não alterar o código da landing durante este período.*
