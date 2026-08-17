# Módulo Balança — AgroSaaS

**Status:** captura manual + sync offline + leitura eletrônica via ponte de hardware (`tools/balanca-bridge`) + modelo de pesagem por etapas (peso informado vs aferido) + login de operador + **vínculo real com Colheita, Pecuária, Compras e Vendas** implementados — ver seção 5.3.
**Desenho completo/decisões de arquitetura:** `docs/brainstorm-modulo-balanca.md`
**Manual de uso (admin + operador):** `docs/MANUAL_BALANCA.md`
**Última atualização:** 2026-08-17 (botão de avaliação por motorista, além de placa — módulo com todo o escopo original combinado implementado)

## 1. O que é

Módulo de pesagem para a fazenda, pensado desde o início para atender dois cenários com o mesmo fluxo:

- **Carga** (caminhões): colheita, compras e vendas de insumos/produtos.
- **Animais** (curral, pecuária).

Cada pesagem é uma sequência de **etapas** (1 a 2 eventos físicos na balança), não um único registro:
- `UNICA`: uma passada só.
- `DUPLA`: chegada + saída (caso clássico de romaneio).
- `DUPLA_ENTRADA_DESCARGA`: chegada + pós-descarga (produto pesado na chegada e de novo depois de descarregado).
- `DUPLA_SAIDA_CARREGAMENTO`: pré-carregamento + saída (mesma lógica, no sentido de saída).

Cada evento de pesagem registra **peso informado** (o que o documento/motorista declara) **e peso aferido** (o que a balança efetivamente mediu) — são dois valores propositalmente separados, não um só; divergência entre eles é sinal de auditoria. O peso líquido final da ordem é calculado a partir do par de etapas quando ambas estão completas.

A Balança funciona como um **serviço interno desacoplado**: outros módulos (romaneio de colheita, compras, vendas, pecuária) *solicitam* uma pesagem e recebem o resultado depois — a Balança não precisa conhecer a lógica de negócio de quem pediu. Isso foi decisão deliberada para permitir, no futuro, comercializar o módulo separadamente do restante da plataforma.

## 2. Como funciona (arquitetura resumida)

```
Módulo cliente (colheita/compras/vendas/pecuária)
        │  solicita pesagem (origem_tipo + origem_id genérico)
        ▼
Backend "balanca" (services/api/balanca/)
  - OrdemPesagem (PENDENTE → EM_PESAGEM → CONCLUIDA/CANCELADA)
  - Pesagem (ticket com peso bruto/tara/líquido)
        │  sync push/pull (offline-first, idempotente por client_id)
        ▼
PWA da estação (apps/balanca/, porta 3003)
  - IndexedDB local (Dexie) — funciona sem internet
  - Operador confirma o peso (digitado ou lido da balança) e confirma
        ▲
        │  WebSocket/HTTP, rede local (não depende de internet)
Ponte de hardware (tools/balanca-bridge, roda perto do indicador)
  - Lê o indicador via serial RS232 ou TCP/Ethernet
  - Extrai o peso (parser genérico por regex, configurável — sem
    depender de saber a marca do indicador com antecedência)
```

Depois que o PWA confirma o peso (digitado ou lido da ponte), ele entra na fila de sync normal e a ordem volta para `CONCLUIDA` quando sincronizada.

Cada fazenda pode ter **uma ou várias estações de balança** cadastradas (ex.: balança de portaria para caminhões, balança de curral para animais) — cada uma com seu próprio código de ativação e token de dispositivo.

## 3. Funciona offline?

**Sim, com duas camadas independentes de conectividade:**

- **PWA ↔ backend central (internet):** só é necessária para *sincronizar*. Se a fazenda ficar dias sem internet, a estação continua pesando e gerando tickets normalmente — tudo fica gravado no IndexedDB do navegador.
- **Sincronização automática:** quando a conexão volta (evento `online` do navegador, ou a cada 30s enquanto há rede), o PWA envia as pesagens pendentes (`push`) e recebe atualizações do servidor (`pull`) automaticamente, sem ação do operador.
- **Idempotência:** cada pesagem tem um `client_id` gerado no dispositivo. Reenviar o mesmo item não duplica o ticket no servidor.

**Leitura eletrônica também é local, não depende de internet:** a ponte de hardware (`tools/balanca-bridge`) fica na rede local, perto do indicador — o PWA fala com ela por WebSocket/HTTP na LAN, igual ao raciocínio acima. Só a *sincronização com o backend central* depende de internet; ler o peso do indicador nunca depende.

## 4. Como configurar (administrador do tenant)

1. No `apps/web`, acesse **Balança → Estações de Balança** (`/dashboard/operacional/balanca/dispositivos`).
   > Se o menu não aparecer: hoje ele está condicionado ao módulo de billing `A2_CAMPO` (mesma linha de PWA offline do Campo), enquanto a Balança não tem módulo de billing próprio cadastrado — ver seção 7.
2. Clique em **"Nova estação"**, informe:
   - **Nome da estação** (ex.: "Balança Portaria Principal")
   - **Fazendas** que essa estação pode atender
   - **Validade** (dias até o token expirar — padrão 365)
3. O sistema gera um **código de ativação** (8 caracteres, válido por 30 minutos). Anote ou copie — ele será digitado no dispositivo da balança.
4. Se o código expirar antes de ativar, use **"Reativar"** na listagem para gerar um novo.
5. Para desligar uma estação (perda, troca de equipamento etc.), use **"Revogar Acesso"** — a estação perde o token imediatamente e precisa de nova ativação.

## 5. Como instalar em um dispositivo (PWA da estação)

A estação de balança roda como um **PWA (Progressive Web App)** — não precisa de loja de aplicativos, instala direto do navegador.

**No dispositivo que fica ao lado da balança (PC ou tablet):**

1. Abra o navegador (Chrome/Edge recomendado) e acesse a URL do PWA de Balança (`http://<host>:3003` em dev; em produção, o domínio configurado para o app).
2. A tela pede **código de ativação** + **PIN da estação** (defina um PIN de 4+ dígitos — ele fica salvo com hash local, usado para reautenticação).
3. Após ativar, o navegador oferece **"Instalar aplicativo"** / **"Adicionar à tela inicial"** — isso transforma o PWA num app com ícone próprio, sem barra de endereço, funcionando em modo "kiosk".
4. A partir daí a tela principal é `/pesagem`: lista as ordens de pesagem pendentes trazidas do servidor e permite registrar o peso.

**Reinstalar/trocar de dispositivo:** revogue a estação antiga no `apps/web` e gere um novo código para ativar no dispositivo novo.

## 5.1. Leitura eletrônica do peso (ponte de hardware)

Sem a ponte configurada, a pesagem é 100% manual (funciona normalmente). Com
ela, o PWA mostra o peso ao vivo do indicador e o operador só confirma.

**Instalação da ponte** (`tools/balanca-bridge`) — roda num equipamento perto
do indicador (recomendado: Raspberry Pi dedicado; também funciona no mesmo PC
que roda o PWA):

1. `cd tools/balanca-bridge && python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt`
2. `cp config.yaml.example config.yaml` e ajuste `connection_type` (`SERIAL` ou `TCP`), porta/host do indicador.
3. `./.venv/bin/python -m balanca_bridge.main` — sobe em `http://<ip-da-ponte>:8321`.
4. Sem indicador físico ainda? Use `simulator.py` incluso para testar toda a cadeia com peso simulado (ver `tools/balanca-bridge/README.md`).
5. Para rodar sempre ligado (produção), registre como serviço `systemd` — exemplo completo no README da ponte.

**Configuração no PWA:** na tela de pesagem, botão **"Configurar ponte"** no cabeçalho → informe a URL (ex.: `http://192.168.0.50:8321`) e, se configurado, o token. Fica salvo localmente na estação (não é enviado ao backend).

Depois de configurada, a tela de pesagem mostra o peso ao vivo com indicador de conexão (verde = conectado, cinza = sem ponte, e um aviso quando a leitura está desatualizada) e um botão **"Usar este peso"** que preenche o campo — o campo continua editável manualmente a qualquer momento (`captured_via` registra `ELETRONICA` ou `MANUAL` conforme a origem usada).

## 5.2. Login de operador (PIN pessoal)

Rastreabilidade de quem pesou: antes de ver as ordens pendentes, a estação pede que o
operador se identifique.

**Cadastro (admin, `apps/web`):** **Balança → Operadores** (`/dashboard/operacional/balanca/operadores`)
→ **"Novo operador"** → selecione uma Pessoa já cadastrada no core e defina um PIN
(4 a 8 dígitos, hash gerado no navegador). A mesma pessoa não pode ser cadastrada duas
vezes; revogar remove o acesso imediatamente e some do seletor da estação.

**Login na estação (PWA):** ao abrir `/pesagem`, se ninguém estiver logado, aparece a
tela "Quem está pesando?" — lista os operadores ativos (busca via API, precisa de rede
nesse momento), o operador escolhe o nome e digita o PIN. A verificação do PIN é sempre
no servidor (bcrypt) — não dá pra validar offline com segurança. Depois de logado, o
operador continua pesando 100% offline como antes; só precisa de rede de novo se trocar
de operador. Botão **"Trocar operador"** no cabeçalho da tela de pesagem.

Cada `Pesagem` grava `operador_pessoa_id` do operador logado no momento da captura.

## 5.3. Vínculo com módulos clientes (colheita, pecuária, compras, vendas) — todos implementados e testados

**Como funciona (evento de domínio, não polling):** quando uma `OrdemPesagem` conclui
(todas as etapas registradas), a Balança publica `balanca.pesagem.concluida` na outbox
(`events/`) com `origem_tipo`/`origem_id`/`peso_bruto_kg`/`peso_tara_kg`/`peso_liquido_kg`
no metadata. O worker de outbox (`background_worker.py`, processo separado — precisa estar
rodando em produção) processa a fila e entrega o evento a quem assinou
`event_types = ("balanca.pesagem.concluida",)`. Cada módulo cliente decide sozinho o que
fazer — a Balança nunca importa `agricola`/`pecuaria`/etc, só o contrário.

**Implementado e testado:**
- **Colheita** (`agricola/romaneios/`): `POST /api/v1/romaneios/{id}/solicitar-pesagem-balanca`
  cria a ordem; `agricola/romaneios/event_subscriber.py` atualiza
  `peso_bruto_kg`/`tara_kg` do romaneio quando a pesagem conclui (reaproveita
  `RomaneioService.atualizar()`, que já recalcula sacas/desconto/receita).
- **Pecuária** (`pecuaria/`): `POST /api/v1/pecuaria/animais/{id}/pesagens/solicitar-balanca`
  cria a ordem (pesagem única); `pecuaria/event_subscriber_balanca.py` cria um
  `EventoAnimal(tipo=PESAGEM)` e atualiza `Animal.peso_atual_kg` — mesmo efeito de
  `PesagemService.registrar_pesagem()`, mas sem chamá-lo diretamente (esse método
  comita a própria transação, o que corrompe a transação do outbox relay se
  invocado no meio do processamento de um evento — lição aprendida depurando
  um erro de `asyncpg` só reproduzível dentro do relay).

  **Seleção de animal por brinco/SISBOV na estação:** o sync pull
  (`GET /api/v1/balanca/sync/pull`) agora também devolve `animais` — uma
  projeção leve (id, brinco, SISBOV, nome, categoria, lote) dos animais
  `ATIVO` das fazendas vinculadas ao dispositivo, lida via **SQL cru**
  (não importa o model `Animal` de `pecuaria/`, mantendo o desacoplamento:
  a Balança nunca importa outro módulo, só o contrário). O app `apps/balanca`
  guarda essa lista numa store Dexie própria (`animais`, populada a cada pull)
  e, quando `subject_type=ANIMAL`, a tela de pesagem mostra um busca-e-seleciona
  em vez do campo de placa — 100% offline depois do primeiro sync.

- **Compras** (`operacional/`): `POST /api/v1/compras/pedidos/{id}/solicitar-pesagem-balanca`
  cria a ordem (pesagem dupla — entrada de carga: insumo ou produto de outro
  produtor); `operacional/compras_event_subscriber.py` chama
  `ComprasService.atualizar_peso_balanca()` (método novo, dedicado — não
  reaproveita nenhuma das funções soltas de `compras_service.py` que comitam a
  própria transação, área sinalizada como sensível no histórico do projeto).
- **Vendas / Comercialização** (`financeiro/comercializacao/`):
  `POST /api/v1/financeiro/comercializacoes/{id}/solicitar-pesagem-balanca`
  cria a ordem (pesagem dupla — saída de carga vendida);
  `financeiro/comercializacao/event_subscriber.py` chama
  `ComercializacaoService.registrar_peso_balanca()` (método novo, deliberadamente
  não usa `transicionar_status()`, que comita a própria transação e dispara
  efeitos colaterais como geração de receita e notificações).

Em ambos os casos o event subscriber grava `peso_bruto_kg`/`peso_tara_kg`/
`peso_liquido_kg` (colunas novas, migration `20260817_balanca_compras_vendas.py`)
só com `flush()` — quem comita é o outbox relay, no final do processamento do
lote (mesma lição de Colheita/Pecuária: método que comita a própria transação
corrompe a transação do relay se chamado no meio do processamento de um evento).

## 5.5. Billing — módulo `O4_BALANCA`

A Balança é um módulo comercializável próprio (`core/constants.py`,
`Modulos.OPERACIONAL_BALANCA = "O4_BALANCA"`), bloco Operacional, tier
**PROFISSIONAL+** (seguindo `O1_FROTA`/`O2_ESTOQUE`/`O3_COMPRAS`).

- **Frontend:** menu no `apps/web` (`sidebar-config.ts`) gateado por
  `moduleId: 'O4_BALANCA'` — antes reaproveitava `A2_CAMPO` como gate
  temporário; já trocado.
- **Backend:** endpoints com JWT de usuário (`/balanca/devices`, `/operadores`,
  `/ordens*`) exigem `Depends(require_module("O4_BALANCA"))` junto da
  permissão de tenant. **Não gateado** (propositalmente): `/devices/activate`
  (não tem tenant ainda — identifica pelo código), `/operadores/ativos` e
  `/operadores/login` (auth por device token) e `sync_router` inteiro
  (`/sync/pull`, `/sync/push` — device token, sem JWT de usuário). Módulos
  clientes (romaneios/compras/vendas/pecuária) chamam `PesagemService`
  diretamente em Python, não via HTTP — não passam por esse gate.
- **Planos:** `scripts/seed_plans.py` inclui `O4_BALANCA` nos planos Prata
  (Profissional) e Ouro (Empresarial) para instalações novas. Em bancos já
  seedados, foi feito um backfill pontual adicionando `O4_BALANCA` a todo
  plano que já tinha `A2_CAMPO` (mesmo critério do gate temporário anterior)
  — não há migração automática disso, é histórico de execução manual.

## 5.6. Balança física (equipamento) × Terminal (estação PWA)

Duas entidades separadas desde 2026-08-17, motivadas por metrologia legal
(balança física é ativo regulado, com aferição/calibração periódica exigida
por INMETRO ou órgão delegado — dado que não faz sentido morar no terminal,
que é só o hardware que roda o app e pode ser trocado sem que o equipamento
mude):

- **`BalancaFisica`** (`balanca_fisicas`): o equipamento em si — nome,
  fabricante, modelo, número de série, capacidade, fazenda onde está.
- **`AfericaoBalanca`** (`balanca_afericoes`): histórico de aferições de uma
  balança física — data, validade, órgão aferidor, nº certificado, resultado
  (APROVADA/REPROVADA/APROVADA_COM_RESSALVA). N por balança física.
- **`DispositivoBalanca`** (terminal) ganhou `balanca_fisica_id` **opcional**
  (N:1, não N:N — várias estações podem apontar para a mesma balança física,
  o que já resolve o cenário de terminal backup sem precisar de N:N).
  Nullable: dispositivos existentes continuam funcionando sem vínculo.

**Endpoints:** `POST/GET /balanca/balancas-fisicas`,
`GET/PATCH /balanca/balancas-fisicas/{id}`,
`POST/GET /balanca/balancas-fisicas/{id}/afericoes` — todos com
`require_module("O4_BALANCA")` + permissão de tenant, mesmo padrão dos
demais endpoints administrativos do módulo.

**UI:** tela nova em `apps/web` — **Balança → Balanças Físicas**
(`/dashboard/operacional/balanca/equipamentos`) — lista, cadastro e
aferições (dialog dedicado por balança). O diálogo de nova estação
(`dispositivo-dialog.tsx`) ganhou um seletor opcional de balança física.

**Alerta de aferição vencida (proativo):** além do badge visual na tela,
`AlertasEngine._verificar_afericao_vencida()`
(`notificacoes/alertas_engine.py`) roda a cada tenant no ciclo periódico do
`automacoes/worker.py` (`run_alerts_check`, ~10 min) e gera uma
`Notificacao` (tipo `AFERICAO_BALANCA_VENCIDA`, agregando todas as balanças
vencidas do tenant numa notificação só) — **é o único motor de alerta que
efetivamente chega no sino de notificação do `apps/web`** (o `alert_engine`
canônico com `OperationalAlert` existe em paralelo mas hoje não alimenta o
sino; por isso o alerta plugou no motor antigo, não no novo — ver decisão
registrada nesta sessão). Cooldown de 24h por tipo/origem evita spam a cada
ciclo. Também espelha em `operational_alerts` via `_espelhar_operational_alert`
(mesmo padrão dos demais alertas deste motor), mas isso é só para
consistência entre os dois sistemas — quem o usuário vê é a `Notificacao`.

## 5.7. Ticket de pesagem (PDF)

Comprovante imprimível — o que o motorista leva. `PesagemService.gerar_pdf_ordem()`
(`balanca/service.py`) monta um PDF A5 (reportlab, mesmo padrão de
`ComprasService.gerar_pdf_pedido()`) com origem/sujeito/tipo de pesagem,
placa ou brinco, documento fiscal, cada etapa registrada (peso aferido vs
informado, data/hora) e o peso líquido final.

Dois endpoints, mesmo conteúdo, autenticação diferente:
- `GET /balanca/ordens/{ordem_id}/pdf` — JWT de usuário (admin), gateado
  por `O4_BALANCA` + `balanca:pesagem:listar`.
- `GET /balanca/sync/ordens/{ordem_id}/pdf?device_id=...` — device token
  (estação), sem gate de módulo (mesmo padrão de `/operadores/ativos` e
  `/operadores/login` — a estação já provou posse do device token).

**UI:**
- **PWA (`apps/balanca`):** botão "Baixar ticket" aparece na tela de
  pesagem assim que uma ordem com processo de origem conclui (não
  disponível em pesagem avulsa, pois a ordem "sombra" só existe no servidor
  depois do sync). Abre o PDF numa nova aba (visualizador do navegador,
  que já oferece impressão).
- **Admin (`apps/web`):** botão "Ticket" na tela de Reconciliação, ao lado
  de "Associar" — baixa o PDF da pesagem avulsa selecionada, e também na
  tela de Ordens de Pesagem (seção 5.8) para qualquer ordem concluída.

## 5.8. Ordens de Pesagem (admin) + controle de qualidade + documento fiscal + avaliação de prestador

Tela nova em `apps/web` — **Balança → Ordens de Pesagem**
(`/dashboard/operacional/balanca/ordens`) — lista todas as ordens (de
qualquer origem: colheita, compras, vendas, pecuária, avulsas), com filtro
por status. Fecha o gap de não haver como revisitar/baixar o ticket de uma
pesagem vinculada a outro módulo depois do fato (antes só dava pra baixar
via Reconciliação, que só lista avulsas).

A partir dessa tela, três ações novas por ordem:

**Controle de qualidade (desconto pós-pesagem)** — `POST
/balanca/ordens/{id}/ajuste-qualidade`, só em ordem `CONCLUIDA`. Grava
`desconto_percentual`/`desconto_motivo`/`peso_liquido_comercial_kg` na
própria `OrdemPesagem` — **não** altera `peso_liquido_kg` nem nenhuma
`Pesagem` (a pesagem em si continua imutável e auditável; o desconto é um
dado derivado, à parte). O ticket em PDF passa a mostrar os dois pesos
(original e comercial) quando o ajuste existe.

**Edição de documento fiscal com scan** — `PATCH
/balanca/ordens/{id}/documento-fiscal`. A tela tem um botão de câmera que
usa a `BarcodeDetector` nativa do navegador (Chrome/Edge, sem lib externa)
para ler código de barras/QR e preencher o campo — degrada silenciosamente
para digitação manual em navegadores sem suporte (Safari/Firefox).

**Avaliação de prestador (transportador/motorista)** — `POST
/balanca/ordens/{id}/avaliacoes` + `GET /balanca/prestadores/avaliacoes`.
Sem cadastro formal de "prestador" no sistema (placa/motorista são texto
livre na `Pesagem`), o identificador é a própria placa ou nome,
normalizado (uppercase/trim) para não fragmentar o histórico por variação
de digitação. Nota 1–5 + comentário opcional; histórico mostra média e
lista das últimas avaliações. Na UI, dois botões por ordem: "Avaliar
veículo" (usa a placa do contexto, disponível quando `subject_type=VEICULO`)
e "Avaliar motorista" — como `OrdemPesagem` não tem campo de motorista
próprio (só existe em `Pesagem.motorista`), esse segundo botão busca
`GET /ordens/{id}/pesagens` sob demanda ao clicar para descobrir o nome
antes de abrir o diálogo (nenhuma chamada extra na listagem principal).

## 6. Uso no dia a dia (operador da balança)

1. A tela de pesagem lista as ordens pendentes (criadas por colheita, compra, venda ou pecuária), com o número da NF e agendamento quando presentes.
2. Operador seleciona a ordem — a tela já mostra qual **etapa** falta (Chegada, Pós-descarga, Pré-carregamento ou Saída, conforme o `tipo_pesagem` da ordem).
3. Preenche **peso aferido** (o que a balança mede — via ponte de hardware ou digitado) e, se divergir, **peso informado** (o valor do documento/motorista; por padrão acompanha o aferido).
4. Confirma. Se a ordem tiver mais de uma etapa, a tela permanece na mesma ordem pedindo a próxima; quando todas as etapas estão feitas, o peso líquido é calculado automaticamente e a ordem vira `CONCLUIDA`.
5. Cada confirmação é salva localmente e entra na fila de sincronização — o operador não precisa esperar internet para seguir pesando o próximo veículo/animal.
6. O cabeçalho da tela mostra a hora da última sincronização bem-sucedida.

### Pesagem avulsa (sem ordem prévia)

Duas situações fazem isso necessário: a estação **rodando standalone** (sem nenhum módulo cliente do AgroSaaS solicitando pesagem) ou a **ordem do processo ainda não chegou** (atraso de sync, processo criado depois da pesagem).

1. Na tela de pesagem, se não houver ordem para o veículo/animal, o operador usa **"Pesagem avulsa (sem ordem)"**.
2. Informa manualmente o que está sendo pesado (veículo/carga ou animal) — avulsa só suporta **pesagem única**; múltiplas etapas exigem saber o ID da ordem criada no servidor, que só existe depois de sincronizar (não dá pra encadear offline).
3. Por trás, a estação cria uma **ordem "sombra"** (`origem_tipo=OUTRO`, sem processo vinculado) — não é um estado especial de "pesagem sem ordem": toda pesagem sempre tem uma ordem, só que essa nasceu sem saber a qual processo pertence.
4. O ticket fica disponível como registro histórico permanentemente, mesmo que nunca seja associado a nada.

### Reconciliação (associar pesagem avulsa a um processo)

Quando a ordem do processo chega depois, ou alguém do escritório precisa vincular a pesagem avulsa a uma compra/venda/romaneio/lote:

1. No `apps/web`, acesse **Balança → Reconciliação** (`/dashboard/operacional/balanca/reconciliacao`).
2. A tela lista todas as pesagens avulsas ainda não associadas.
3. Clique em **"Associar"**, escolha o tipo de processo (colheita/compra/venda/pecuária/pessoa) e busque o registro por nome/número/data no seletor — sem precisar copiar/colar UUID (pecuária exige fazenda ativa selecionada; sem isso, cai no ID manual).
4. Depois de associada, a pesagem some da fila de reconciliação e passa a aparecer como qualquer outra pesagem vinculada ao processo.

> Essa tela fica no admin (não no PWA da estação) porque quem reconcilia normalmente tem mais contexto sobre qual processo bate com qual ticket do que o operador que pesou na hora.

## 7. Limitações conhecidas / pendências

- **Ponte de hardware ainda não testada com equipamento real:** o parser é genérico (regex configurável) e foi validado com um simulador — quando a marca/modelo do indicador for definida, confirmar o formato real do frame e ajustar `config.yaml` (ver `tools/balanca-bridge/README.md`).
- **Vínculo depende do worker de outbox estar rodando:** o evento `balanca.pesagem.concluida` só é entregue quando `background_worker.py` processa a fila (`events/outbox_relay.py`) — se o worker não estiver ativo em produção, romaneios/animais não recebem o peso automaticamente (a ordem na Balança continua correta, só o vínculo atrasa).
- **Login de operador exige rede na hora de entrar:** a verificação do PIN pessoal é sempre no servidor (não dá pra validar bcrypt offline com segurança) — o operador precisa de conexão pra logar na estação uma vez; depois disso, pesar continua 100% offline até trocar de operador.
- **Leitura de código de barras/NFe limitada à Balança:** o scan (BarcodeDetector nativo do navegador, sem lib externa) só está disponível para editar `numero_documento_fiscal` de uma ordem já criada, na tela de Ordens de Pesagem — não alcança as telas de romaneio/compras/vendas, onde o documento fiscal também é digitado na criação do processo (fora do escopo deste módulo). Sem suporte em Safari/Firefox (o botão de scan some, mas o campo manual continua disponível).

## 8. Referências técnicas

| O quê | Onde |
|---|---|
| Backend (models, service, router) | `services/api/balanca/` |
| Migrations | `services/api/migrations/versions/20260816_balanca_{modulo,etapas,operadores}.py` |
| Teste de isolamento de tenant | `services/api/tests/integration/balanca/test_balanca_tenant_isolation.py` |
| PWA da estação | `apps/balanca/` |
| Ponte de hardware (leitura eletrônica) | `tools/balanca-bridge/` (serviço Python standalone, roda perto do indicador) |
| Cliente da ponte no PWA | `apps/balanca/src/lib/bridge/peso-ao-vivo.ts` |
| Telas administrativas (apps/web) | `apps/web/src/app/(dashboard)/dashboard/operacional/balanca/{dispositivos,operadores,reconciliacao}/` |
| Componentes das telas admin | `apps/web/src/components/balanca/` |
| Login de operador no PWA | `apps/balanca/src/components/operador-login.tsx` |
| Entrada de menu | `apps/web/src/lib/sidebar-config.ts` (grupo `BALANCA`) |
| Catálogo de permissões | `apps/web/src/lib/permission-catalog.ts` (`balanca:dispositivo`, `balanca:operador`, `balanca:pesagem`) |
| Desenho/decisões de arquitetura | `docs/brainstorm-modulo-balanca.md` |
| Vínculo colheita (endpoint + subscriber) | `services/api/agricola/romaneios/{router,service,event_subscriber}.py` |
| Vínculo pecuária (endpoint + subscriber) | `services/api/pecuaria/routers/animais.py`, `services/api/pecuaria/event_subscriber_balanca.py` |
| Registro de subscribers | `services/api/events/subscribers.py` |
| Teste de integração colheita↔balança | `services/api/tests/integration/agricola/test_romaneio_balanca_integration.py` |
| Teste de integração pecuária↔balança | `services/api/tests/integration/pecuaria/test_pecuaria_balanca_integration.py` |

### Endpoints principais

| Método | Rota | Descrição |
|---|---|---|
| POST | `/api/v1/balanca/devices` | Cria estação, gera código de ativação |
| POST | `/api/v1/balanca/devices/activate` | Ativa estação (código + PIN + fingerprint) → token de dispositivo |
| POST | `/api/v1/balanca/devices/revoke` | Revoga acesso da estação |
| POST | `/api/v1/balanca/devices/reactivate` | Gera novo código para estação revogada/expirada |
| GET | `/api/v1/balanca/devices` | Lista estações do tenant |
| POST | `/api/v1/balanca/balancas-fisicas` | Cadastra balança física (equipamento) |
| GET | `/api/v1/balanca/balancas-fisicas` | Lista balanças físicas do tenant |
| GET/PATCH | `/api/v1/balanca/balancas-fisicas/{id}` | Detalhe / atualização parcial |
| POST/GET | `/api/v1/balanca/balancas-fisicas/{id}/afericoes` | Registra / lista aferições da balança física |
| POST | `/api/v1/balanca/operadores` | Cadastra operador (Pessoa + PIN) |
| GET | `/api/v1/balanca/operadores` | Lista operadores do tenant (admin) |
| POST | `/api/v1/balanca/operadores/{id}/revogar` | Revoga acesso do operador |
| GET | `/api/v1/balanca/operadores/ativos` | Lista operadores ativos (device token — seletor da estação) |
| POST | `/api/v1/balanca/operadores/login` | Login por PIN pessoal (device token) |
| POST | `/api/v1/balanca/ordens` | Solicita pesagem (chamado por módulos clientes) |
| GET | `/api/v1/balanca/ordens` | Lista ordens de pesagem |
| GET | `/api/v1/balanca/ordens/{id}` | Detalhe de uma ordem |
| GET | `/api/v1/balanca/ordens/{id}/pesagens` | Tickets de pesagem de uma ordem |
| POST | `/api/v1/balanca/ordens/{id}/cancelar` | Cancela ordem pendente |
| POST | `/api/v1/balanca/ordens/{id}/reatribuir` | Reconciliação: associa pesagem avulsa ao processo real |
| GET | `/api/v1/balanca/ordens/pendentes-reconciliacao` | Lista pesagens avulsas ainda não associadas |
| GET | `/api/v1/balanca/sync/pull` | PWA busca ordens pendentes (token de dispositivo) |
| POST | `/api/v1/balanca/sync/push` | PWA envia pesagens capturadas (token de dispositivo) |
| GET | `/api/v1/balanca/ordens/{id}/pdf` | Ticket de pesagem em PDF (admin, JWT) |
| GET | `/api/v1/balanca/sync/ordens/{id}/pdf` | Ticket de pesagem em PDF (estação, device token) |
| POST | `/api/v1/balanca/ordens/{id}/ajuste-qualidade` | Desconto de peso pós-pesagem (não altera a pesagem original) |
| PATCH | `/api/v1/balanca/ordens/{id}/documento-fiscal` | Edita nº do documento fiscal (ex.: lido via scan) |
| POST | `/api/v1/balanca/ordens/{id}/avaliacoes` | Avalia transportador/motorista (placa ou nome) |
| GET | `/api/v1/balanca/prestadores/avaliacoes` | Histórico de avaliações por identificador |
| POST | `/api/v1/romaneios/{id}/solicitar-pesagem-balanca` | Colheita: vincula romaneio a uma pesagem oficial |
| POST | `/api/v1/pecuaria/animais/{id}/pesagens/solicitar-balanca` | Pecuária: vincula animal a uma pesagem oficial |
| POST | `/api/v1/compras/pedidos/{id}/solicitar-pesagem-balanca` | Compras: vincula pedido a uma pesagem oficial |
| POST | `/api/v1/financeiro/comercializacoes/{id}/solicitar-pesagem-balanca` | Vendas: vincula comercialização a uma pesagem oficial |
