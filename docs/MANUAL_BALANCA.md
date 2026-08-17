# Manual da Balança — AgroSaaS

> Manual de uso, para administradores e operadores de estação. Para detalhes técnicos de arquitetura, decisões de design e referência de API, ver `docs/MODULO_BALANCA.md`.

**Atualizado em:** 2026-08-17

---

## 1. Visão geral

A Balança registra o peso de caminhões e animais na entrada e saída da fazenda — para colheita, compras, vendas e pecuária — mesmo sem internet no ponto de pesagem. Duas pessoas usam o módulo, cada uma com sua própria tela:

- **Administrador (escritório):** cadastra estações e balanças físicas, gerencia operadores, acompanha todas as ordens de pesagem, aplica descontos de qualidade e reconcilia pesagens avulsas — pelo painel web, de qualquer computador.
- **Operador de balança (estação):** pesa o veículo ou animal no tablet fixado perto da balança, mesmo sem internet — os dados sincronizam sozinhos assim que a conexão volta.

### Fluxo geral

1. **Processo pede pesagem** — colheita, compra, venda ou pecuária solicita uma ordem.
2. **Operador pesa** — na estação, offline se preciso.
3. **Sincroniza** — assim que houver conexão.
4. **Peso volta ao processo** — automático, via evento interno.
5. **Ticket disponível** — PDF pro motorista, a qualquer momento.

---

## 2. Para administradores (painel web)

Tudo fica em **Operacional → Balança**, no menu lateral.

### Estações de Balança
`/dashboard/operacional/balanca/dispositivos`

Cada tablet ou computador fixado perto de uma balança é uma **estação**. Cadastre uma nova, escolha as fazendas que ela pode atender, e um código de ativação é gerado.

1. Clique em **Nova estação**, dê um nome (ex: "Balança Portaria 1") e selecione as fazendas.
2. Copie o código de 8 dígitos gerado.
3. No tablet da estação, abra o app da balança e informe o código — ele fica ativo por 30 minutos.

Se uma estação for perdida ou trocar de aparelho, use **Revogar** e depois **Reativar** para gerar um novo código.

### Balanças Físicas
`/dashboard/operacional/balanca/equipamentos`

O equipamento em si — fabricante, modelo, número de série e capacidade — separado do tablet que roda o app, para acompanhar a **aferição legal** independente de qual terminal está ligado a ele.

1. Cadastre a balança física com os dados do equipamento.
2. Ao ativar uma estação, vincule-a à balança física correspondente (opcional).
3. Registre cada aferição (data, órgão aferidor, validade, resultado) pelo botão **Aferições**.

Uma balança com aferição vencida mostra um selo vermelho na lista, e você recebe uma notificação automática.

### Operadores
`/dashboard/operacional/balanca/operadores`

Cadastre quem pode logar na estação com um **PIN pessoal** de 4 dígitos — assim cada pesagem fica registrada com o nome de quem pesou, mesmo que várias pessoas usem o mesmo tablet.

### Ordens de Pesagem
`/dashboard/operacional/balanca/ordens`

Lista **todas** as pesagens, de qualquer origem, com filtro por status. Em cada ordem concluída:

- **Ticket** — baixa o comprovante em PDF, pronto pra impressão.
- **Ajustar** — aplica um desconto de qualidade (ex.: umidade, impureza) sem alterar a pesagem original, que continua registrada e auditável.
- Ícone de **documento** — edita o número da nota fiscal, com opção de escanear o código de barras/QR pela câmera.
- Ícones de **estrela** — avaliam o veículo (placa) ou o motorista, com nota de 1 a 5 e histórico.

### Reconciliação
`/dashboard/operacional/balanca/reconciliacao`

Quando a estação pesa sem uma ordem prévia (fora do ar, ou processo criado depois), a pesagem fica disponível aqui pra ser associada manualmente ao romaneio, compra, venda ou lote correto — com busca por nome, não precisa copiar ID.

---

## 3. Para o operador da estação

O app da balança roda direto no navegador do tablet fixado no ponto de pesagem, e funciona **sem internet** depois da primeira sincronização.

### Login por PIN

Ao abrir o app, escolha seu nome na lista e digite seu PIN pessoal. Isso exige internet na hora de entrar — depois de logado, pesar continua funcionando offline até você trocar de operador.

### Pesar um veículo ou animal

1. Selecione a ordem pendente na lista (ou toque em **Pesagem avulsa** se não houver ordem pra esse veículo).
2. Informe o **peso aferido** — o que a balança mediu. Se houver uma ponte de hardware configurada, o peso já aparece sozinho, com um botão pra usar a leitura.
3. Se o peso da nota fiscal for diferente do aferido, ajuste o **peso informado** — do contrário ele acompanha o aferido automaticamente.
4. Ao pesar um animal, busque pelo brinco ou SISBOV em vez de digitar a placa.
5. Confirme. Se a ordem tiver mais de uma etapa (chegada e saída, por exemplo), a tela já pede a próxima.

> **Sem conexão?** Sem problema — cada pesagem fica guardada no tablet e entra na fila de envio automaticamente assim que a internet voltar.

### Ticket para o motorista

Assim que uma ordem é concluída, o botão **Baixar ticket** aparece na tela — abre o comprovante em PDF numa nova aba, pronto pra impressão.

---

## 4. Notificações

O sino de notificações do painel avisa automaticamente quando:

- **Aferição vencida** — uma ou mais balanças físicas passaram da validade da última aferição — a notificação lista quais.

---

## 5. Referência rápida de telas

| Tela | Caminho | Quem usa |
|---|---|---|
| Estações de Balança | `/dashboard/operacional/balanca/dispositivos` | Admin |
| Balanças Físicas | `/dashboard/operacional/balanca/equipamentos` | Admin |
| Ordens de Pesagem | `/dashboard/operacional/balanca/ordens` | Admin |
| Operadores | `/dashboard/operacional/balanca/operadores` | Admin |
| Reconciliação | `/dashboard/operacional/balanca/reconciliacao` | Admin |
| App da estação (PWA) | `apps/balanca` (porta 3003) | Operador |

---

## 6. Dúvidas frequentes

**O peso não chegou no romaneio/compra/venda depois de pesar. Por quê?**
O vínculo entre a Balança e o processo original é feito por um serviço interno que roda em segundo plano no servidor. Se ele estiver parado, a pesagem continua correta na Balança, só o repasse automático atrasa — avise o suporte técnico se isso persistir.

**Posso pesar sem ter uma ordem criada?**
Sim — use **Pesagem avulsa** na estação. Ela vira uma pesagem "solta" que aparece na tela de Reconciliação do admin, pra ser associada ao processo certo depois.

**O desconto de qualidade apaga o peso original?**
Não. O peso aferido na balança nunca é alterado. O desconto grava um "peso comercial" separado, com o motivo, e os dois aparecem lado a lado no ticket.

**O botão de escanear código de barras não aparece.**
Ele depende de um recurso nativo disponível em Chrome e Edge (inclusive Android). Em Safari ou Firefox, o botão some e sobra o campo de digitação manual — nada é perdido, só a leitura automática não roda nesse navegador.

**Como troco o operador no meio do turno?**
No topo da tela de pesagem, toque em **Trocar operador**. Isso exige conexão à internet — pesagens já feitas pelo operador anterior continuam salvas normalmente.
