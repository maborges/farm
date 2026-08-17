# Módulo Balança — AgroSaaS

**Status:** captura manual + sync offline + leitura eletrônica via ponte de hardware (`tools/balanca-bridge`) + modelo de pesagem por etapas (peso informado vs aferido) implementados. Prioridade de desenvolvimento: carga (veículo) primeiro, animal depois.
**Desenho completo/decisões de arquitetura:** `docs/brainstorm-modulo-balanca.md`
**Última atualização:** 2026-08-16 (modelo de pesagem por etapas, peso informado/aferido, produto/volumes/agendamento/NF na ordem)

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
3. Clique em **"Associar"**, escolha o tipo de processo (colheita/compra/venda/pecuária) e informe o ID do registro correspondente.
4. Depois de associada, a pesagem some da fila de reconciliação e passa a aparecer como qualquer outra pesagem vinculada ao processo.

> Essa tela fica no admin (não no PWA da estação) porque quem reconcilia normalmente tem mais contexto sobre qual processo bate com qual ticket do que o operador que pesou na hora.

## 7. Limitações conhecidas / pendências

- **Sem módulo de billing próprio ainda:** o gate de visibilidade do menu no `apps/web` reaproveita `A2_CAMPO` temporariamente. Definir o módulo definitivo (ex. `O4_BALANCA`) e o plano em que entra é decisão de produto pendente.
- **Ponte de hardware ainda não testada com equipamento real:** o parser é genérico (regex configurável) e foi validado com um simulador — quando a marca/modelo do indicador for definida, confirmar o formato real do frame e ajustar `config.yaml` (ver `tools/balanca-bridge/README.md`).
- **Pesagem de animal ainda não tem tela/fluxo específico de pecuária** (ex.: seleção de lote/brinco) — a prioridade combinada foi carga primeiro; hoje `subject_type=ANIMAL` funciona igual a `VEICULO` (só sem campo de placa).
- **Vínculo automático com módulos clientes** (colheita, compras, vendas, pecuária chamando `PesagemService.solicitar_pesagem()` de verdade) ainda não foi cabeado em nenhum módulo piloto — hoje a criação de ordens é testável via API (`POST /api/v1/balanca/ordens`), mas nenhuma tela de colheita/compra/venda chama isso automaticamente ainda.
- **Reconciliação sem busca assistida:** a tela de reconciliação pede o ID do registro (romaneio/compra/venda/lote) digitado/colado manualmente — ainda não há um seletor com busca por nome/data dentro de cada módulo.
- **Operador não é identificado por login:** `Pesagem.operador_pessoa_id` já existe no schema, mas o PWA não pede login de uma Pessoa cadastrada — hoje só a estação (PIN) é autenticada, não quem está operando.
- **Terminal × Balança ainda é um cadastro só:** `DispositivoBalanca` representa a estação inteira; não há um cadastro de "balança" separado do "terminal" (relação ainda não definida — decisão de produto pendente).
- **Sem controle de qualidade / ajuste de peso:** não existe fluxo para descontar peso pós-pesagem (ex.: desconto por umidade/impureza em grãos) — pesagens são imutáveis uma vez registradas.
- **Sem leitura automática de código de barras/NFe:** `numero_documento_fiscal` existe mas é preenchido manualmente (na solicitação, pelo módulo cliente) — sem scanner/OCR.
- **Sem etiqueta/relatório de pesagem, nem histórico de avaliação de prestadores** (transportadora/motorista) — não solicitados ainda para esta fase.

## 8. Referências técnicas

| O quê | Onde |
|---|---|
| Backend (models, service, router) | `services/api/balanca/` |
| Migration | `services/api/migrations/versions/20260816_balanca_modulo.py` |
| Teste de isolamento de tenant | `services/api/tests/integration/balanca/test_balanca_tenant_isolation.py` |
| PWA da estação | `apps/balanca/` |
| Ponte de hardware (leitura eletrônica) | `tools/balanca-bridge/` (serviço Python standalone, roda perto do indicador) |
| Cliente da ponte no PWA | `apps/balanca/src/lib/bridge/peso-ao-vivo.ts` |
| Telas administrativas (apps/web) | `apps/web/src/app/(dashboard)/dashboard/operacional/balanca/{dispositivos,reconciliacao}/` |
| Componentes das telas admin | `apps/web/src/components/balanca/` |
| Entrada de menu | `apps/web/src/lib/sidebar-config.ts` (grupo `BALANCA`) |
| Catálogo de permissões | `apps/web/src/lib/permission-catalog.ts` (`balanca:dispositivo`, `balanca:pesagem`) |
| Desenho/decisões de arquitetura | `docs/brainstorm-modulo-balanca.md` |

### Endpoints principais

| Método | Rota | Descrição |
|---|---|---|
| POST | `/api/v1/balanca/devices` | Cria estação, gera código de ativação |
| POST | `/api/v1/balanca/devices/activate` | Ativa estação (código + PIN + fingerprint) → token de dispositivo |
| POST | `/api/v1/balanca/devices/revoke` | Revoga acesso da estação |
| POST | `/api/v1/balanca/devices/reactivate` | Gera novo código para estação revogada/expirada |
| GET | `/api/v1/balanca/devices` | Lista estações do tenant |
| POST | `/api/v1/balanca/ordens` | Solicita pesagem (chamado por módulos clientes) |
| GET | `/api/v1/balanca/ordens` | Lista ordens de pesagem |
| GET | `/api/v1/balanca/ordens/{id}` | Detalhe de uma ordem |
| GET | `/api/v1/balanca/ordens/{id}/pesagens` | Tickets de pesagem de uma ordem |
| POST | `/api/v1/balanca/ordens/{id}/cancelar` | Cancela ordem pendente |
| POST | `/api/v1/balanca/ordens/{id}/reatribuir` | Reconciliação: associa pesagem avulsa ao processo real |
| GET | `/api/v1/balanca/ordens/pendentes-reconciliacao` | Lista pesagens avulsas ainda não associadas |
| GET | `/api/v1/balanca/sync/pull` | PWA busca ordens pendentes (token de dispositivo) |
| POST | `/api/v1/balanca/sync/push` | PWA envia pesagens capturadas (token de dispositivo) |
