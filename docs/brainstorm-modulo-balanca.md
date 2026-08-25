# Brainstorm — Módulo de Balança

**Status:** desenho aprovado, implementação iniciada (migration/models backend)
**Data:** 2026-08-16

## Escopo

Módulo único de pesagem servindo dois tipos de sujeito desde o início:
- **Carga** (caminhões: colheita, compras, vendas de insumos/produtos)
- **Animal** e **Pessoa** (curral/pecuária, outros usos futuros)

Suporta pesagem **única** (peso bruto − tara cadastrada) e **dupla** (entrada/saída, diferença), captura **manual** ou **eletrônica** (indicador de balança).

## Decisões de arquitetura

1. **Balança como serviço, não como "dono" dos módulos clientes.** Romaneio/compras/vendas/pecuária/pessoas *solicitam* pesagem (`PesagemService.solicitar_pesagem()`); a Balança não conhece a lógica interna desses módulos. Vínculo via `origem_tipo`/`origem_id` genérico (sem FK direta a tabelas de outros módulos) — permite o módulo ser extraído/comercializado separadamente no futuro.

2. **Offline-first via app dedicado (`balanca-platform/station`), reaproveitando o padrão já existente em `apps/campo`:**
   - IndexedDB (Dexie) + service worker + fila de sync (`sync_queue`)
   - `push`/`pull` idempotente por `client_id`, com `SyncTombstone` para deleções
   - Padrão de "solicitação pendente resolvida por outro dispositivo" já existe em `RequisicaoMaterial`/`RequisicaoConfirmacao` (estoque) — a `OrdemPesagem` segue o mesmo modelo: criada por um módulo cliente, resolvida depois pela estação de balança.

3. **App PWA separado do `apps/campo`** (não reaproveita a mesma instância): a balança é uma estação fixa (kiosk), com autenticação de **dispositivo** (não de operador móvel) e integração de hardware própria — diferente do perfil de uso do app de campo.

4. **Integração com hardware do indicador (Toledo, Filizola, Digitron etc.) via bridge local:**
   - Web Serial API é insuficiente (só Chrome desktop, não cobre TCP/Ethernet nem tablet)
   - Solução: serviço-ponte local (Python/pyserial ou TCP), com adapter por protocolo/fabricante, expondo endpoint HTTP/WebSocket na rede local
   - PWA consome a ponte via rede local (não depende de internet); fallback sempre disponível: digitação manual (`captured_via=MANUAL`)
   - Fase 1 da implementação: só captura manual, ponte de hardware entra depois

5. **Dupla camada de offline:** PWA↔bridge (rede local, nunca depende de internet) é independente de PWA↔backend central (internet, só necessária para sync). A balança opera dias sem internet; sync roda quando a conexão volta.

## Modelo de dados (fase 1 — backend)

- `DispositivoBalanca` (`balanca_dispositivos`): auth de estação, espelha `DispositivoCampo`
- `OrdemPesagem` (`balanca_ordens`): solicitação criada pelo módulo cliente — `origem_tipo`, `origem_id`, `subject_type` (VEICULO/ANIMAL — pesagem de pessoas removida do escopo, não é caso de uso real em fazenda), status (PENDENTE/EM_PESAGEM/CONCLUIDA/CANCELADA)
- `Pesagem` (`balanca_pesagens`): resultado — peso_bruto/tara/liquido (`Numeric`), tipo_pesagem (UNICA/DUPLA), `captured_via`, `client_id` (idempotência), timestamps de entrada/saída
- `SyncTombstoneBalanca` (`balanca_sync_tombstones`): mesmo padrão de `campo`

## Decisão adicional — pesagem sem ordem (avulsa)

Pergunta que motivou a revisão: "pode existir uma pesagem sem uma ordem?" — sim, por dois motivos reais:
1. A estação pode rodar **standalone** (módulo vendido separadamente, decisão 1 acima) — sem nenhum módulo cliente chamando `solicitar_pesagem()`, o operador nunca teria o que pesar.
2. A ordem de um processo pode **chegar atrasada** (falha de sync, processo criado depois da pesagem).

**Abordagem escolhida: ordem "sombra" automática**, não `ordem_id` nullable em `Pesagem`:
- Ao pesar sem ordem selecionada no PWA, o `sync push` cria uma `OrdemPesagem` com `origem_tipo=OUTRO`, `origem_id=null`, já a partir do `subject_type`/`tipo_pesagem` escolhidos pelo operador na hora.
- `Pesagem.ordem_id` continua sempre presente (sem migration, sem FK nullable, sem tratamento de null espalhado pelo sync/relatórios).
- Reconciliação = `PesagemService.reatribuir_ordem()` — troca `origem_tipo`/`origem_id` da ordem sombra pelo processo real. Endpoint `POST /balanca/ordens/{id}/reatribuir`, tela dedicada em `apps/web` (`/dashboard/operacional/balanca/reconciliacao`), pois quem reconcilia (escritório) tem mais contexto que o operador da balança.
- Fila de pendências: `GET /balanca/ordens/pendentes-reconciliacao` (filtra `origem_tipo=OUTRO AND origem_id IS NULL`).

## Decisão adicional — leitura eletrônica (ponte de hardware)

Confirmado com o usuário: equipamento ainda não definido → desenho genérico (regex configurável, não hardcoda marca). Conexão serial RS232 **e** TCP/Ethernet desde o já, ambas suportadas pela mesma ponte via `connection_type` no config. Ponte roda **separada** do dispositivo que exibe o PWA (recomendado: Raspberry Pi dedicado perto do indicador), comunicando por rede local — mas nada impede rodar no mesmo PC (a URL da ponte é só configuração no PWA, `http://localhost:porta` funciona igual).

Escopo combinado: **carga (veículo) primeiro, animal depois** — na prática a ponte/protocolo já serve os dois desde o início (mesmo endpoint `/peso-atual`), a diferença é só de UI/prioridade de tela. Pesagem de pessoas foi **removida do escopo** (`subject_type` agora só `VEICULO`/`ANIMAL`) — não é caso de uso real numa fazenda.

Implementado em `balanca-platform/bridge/` (Python/FastAPI standalone, fora de `services/api`):
- `ProtocolAdapter`: extrai peso via regex configurável (`weight_regex`, `decimal_separator`, `unit`, `scale_factor`) — cobre a maioria dos indicadores em modo "contínuo" ASCII sem saber a marca.
- `serial_reader.py` / `tcp_reader.py`: loops de leitura com reconexão automática em falha.
- `GET /peso-atual` (poll) + `WS /ws/peso` (push) — PWA usa WebSocket com fallback de reconexão.
- `simulator.py`: indicador fake via TCP, para testar toda a cadeia sem hardware físico (usado nos testes de integração).
- Token opcional (`api_token`) via header (REST) ou query string (WebSocket, já que browser não permite header customizado no handshake).

PWA (`balanca-platform/station`): `session.bridge_url`/`bridge_token` configuráveis por estação (tela "Configurar ponte"), hook `usePesoAoVivo()` mantém leitura ao vivo com indicador de conectado/desatualizado, botão "Usar este peso" preenche o campo mantendo edição manual sempre disponível. `captured_via` registra `ELETRONICA` vs `MANUAL` conforme a origem realmente usada.

## Decisão adicional — modelo de pesagem por etapas (spec de negócio detalhada)

Usuário trouxe spec de negócio completa (expedição, agendamento, processo gerador,
NF, produto, motorista/caminhão, operador, peso informado vs aferido, (des)carregamento
entre pesagens, controle de qualidade, use cases). Gap analysis feita item a item;
prioridade combinada: **modelo de pesagem por etapas + peso informado/aferido primeiro**
(produto/volumes/agendamento/NF pendem disso, então entraram juntos).

**Implementado:**
- `Pesagem` deixou de ser "1 registro por perna" (bruto/tara/líquido) e virou **1 registro
  por evento físico de pesagem** (`etapa`), com `peso_informado_kg` (declarado) e
  `peso_aferido_kg` (medido) separados — confirmado pelo usuário: "no caso de entrada de
  nota fiscal, é informado o peso e o aferido é o da balança".
- `OrdemPesagem.tipo_pesagem` ganhou `DUPLA_ENTRADA_DESCARGA` (chegada + pós-descarga) e
  `DUPLA_SAIDA_CARREGAMENTO` (pré-carregamento + saída), cobrindo o cenário confirmado:
  "em alguns processos o produto é pesado duas vezes... entrada pesado na chegada e na
  descarga, saída pesado no carregamento e na saída". `ETAPAS_POR_TIPO_PESAGEM` (schemas.py
  e db.ts, espelhados) define a sequência esperada por tipo.
- Peso líquido da ordem passou a viver em `OrdemPesagem.peso_liquido_kg`, calculado quando
  o par de etapas esperado está completo (`PesagemService._avaliar_conclusao_ordem`).
- `OrdemPesagem` ganhou `produto_id`/`produto_tipo` (COMMODITY/ALMOXARIFADO — "temos que ter
  o produto cadastrado"), `tipo_volume`/`quantidade_volumes` ("tipos e quantidade de
  volumes: sacas, bags etc"), `data_agendada` ("a solicitação passa a ter também o
  conceito de agendamento" — confirmado), `numero_documento_fiscal` (leitura automática de
  código de barras/NFe fica para fase futura — campo já existe, preenchimento manual).
- `Pesagem` ganhou `operador_pessoa_id` — campo já existe no schema, mas login por operador
  no PWA (autenticação por Pessoa cadastrada, não só PIN de estação) **ainda não implementado**.

**Explicitamente deferidos (não bloqueiam esta fase):**
- ~~Login de operador por Pessoa~~ — implementado a seguir (ver abaixo).
- Relação Terminal × Balança como cadastros distintos — usuário quer definir antes.
- `AjusteQualidadePeso` (desconto de peso pós-controle de qualidade, não destrutivo).
- Leitura automática de código de barras/NFe (campo existe, sem OCR/scanner ainda).
- Emissão de etiqueta/relatório.
- Histórico de avaliação de prestadores de serviço (transportadora/motorista).

**Migration:** `20260816_balanca_etapas` — destrutiva nas colunas antigas de `Pesagem`
(sem dados reais em produção neste módulo ainda, só tenants de teste).

## Decisão adicional — login de operador por PIN pessoal

Pesquisa prévia (subagent) confirmou: não existia em lugar nenhum do sistema (rh/,
operacional/, core/) um padrão de PIN pessoal por Pessoa/Colaborador em terminal
compartilhado — só PIN por dispositivo (`DispositivoCampo.pin_hash`,
`DispositivoBalanca.pin_hash`, cada um atrelado a 1 usuário/estação). Balança precisa de
terminal compartilhado por vários operadores em turnos diferentes, então foi criado
cadastro próprio: **`OperadorBalanca`** (`balanca_operadores`) — `tenant_id`, `pessoa_id`
(referência por convenção, sem FK — mesmo princípio de `origem_id`/`produto_id`),
`nome_exibicao`, `pin_hash` (bcrypt, hash gerado no cliente na tela de cadastro admin,
igual ao padrão já usado na ativação de dispositivo), `status`.

Fluxo: admin cadastra operador (`apps/web` → Balança → Operadores, seleciona Pessoa do
core + define PIN). PWA, antes de mostrar ordens pendentes, exige login — lista
operadores ativos (`GET /balanca/operadores/ativos`, device token) e valida PIN
(`POST /balanca/operadores/login`, bcrypt no servidor, sem token/sessão retornado — o PWA
só guarda `operador_id`/`pessoa_id`/`nome_exibicao` localmente até trocar). Login exige
rede (verificação de PIN não pode ser feita offline com segurança); depois de logado, a
pesagem em si continua 100% offline como antes. `Pesagem.operador_pessoa_id` passa a ser
preenchido de verdade a partir daqui.

Migration `20260816_balanca_operadores`. 4º teste de integração cobre cadastro, seletor
sem PIN exposto, PIN errado rejeitado, PIN certo autentica, e revogação remove do
seletor e bloqueia login.

## Ordem de implementação

1. ✅ Migration + models (`DispositivoBalanca`, `OrdemPesagem`, `Pesagem`, tombstone)
2. ✅ `PesagemService` (API interna de solicitação) + `SyncService` (push/pull)
3. ✅ Router + registro em `main.py`
4. ✅ Scaffold do `balanca-platform/station` (PWA: captura manual)
5. ✅ Pesagem avulsa + reconciliação (`OrdemPesagem` sombra, tela admin)
6. ✅ Ponte de hardware (`balanca-platform/bridge`) + integração de leitura ao vivo no PWA
7. Piloto de integração: romaneio de colheita chamando `PesagemService.solicitar_pesagem()` de verdade (pendente)
8. Fluxo/tela específica de pecuária para pesagem de animal (lote/brinco) — próxima prioridade combinada
