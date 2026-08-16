# Módulo Balança — AgroSaaS

**Status:** Fase 1 implementada (captura manual + sync offline). Bridge de hardware para leitura eletrônica ainda não implementada.
**Desenho completo/decisões de arquitetura:** `docs/brainstorm-modulo-balanca.md`
**Última atualização:** 2026-08-16

## 1. O que é

Módulo de pesagem para a fazenda, pensado desde o início para atender dois cenários com o mesmo fluxo:

- **Carga** (caminhões): colheita, compras e vendas de insumos/produtos — pesagem única (peso bruto − tara cadastrada) ou dupla (entrada/saída, por diferença).
- **Animais e pessoas** (curral, outros usos): pesagem única.

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
  - Operador pesa (digitação manual) e confirma
        │  sincroniza quando há conexão
        ▼
Ordem volta para CONCLUIDA, peso disponível para o módulo cliente
```

Cada fazenda pode ter **uma ou várias estações de balança** cadastradas (ex.: balança de portaria para caminhões, balança de curral para animais) — cada uma com seu próprio código de ativação e token de dispositivo.

## 3. Funciona offline?

**Sim, com duas camadas independentes de conectividade:**

- **PWA ↔ backend central (internet):** só é necessária para *sincronizar*. Se a fazenda ficar dias sem internet, a estação continua pesando e gerando tickets normalmente — tudo fica gravado no IndexedDB do navegador.
- **Sincronização automática:** quando a conexão volta (evento `online` do navegador, ou a cada 30s enquanto há rede), o PWA envia as pesagens pendentes (`push`) e recebe atualizações do servidor (`pull`) automaticamente, sem ação do operador.
- **Idempotência:** cada pesagem tem um `client_id` gerado no dispositivo. Reenviar o mesmo item não duplica o ticket no servidor.

**O que ainda não é 100% offline:** a leitura eletrônica do peso (indicador de balança via bridge de hardware) está planejada para uma fase posterior — hoje o peso é sempre **digitado manualmente** pelo operador, o que não depende de rede alguma.

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

## 6. Uso no dia a dia (operador da balança)

1. A tela de pesagem lista as ordens pendentes (criadas por colheita, compra, venda ou pecuária).
2. Operador seleciona a ordem, digita o peso e confirma:
   - **Pesagem única:** peso informado já é o líquido (ou bruto − tara já cadastrada).
   - **Pesagem dupla:** primeira captura registra "peso de entrada"; a ordem fica `EM_PESAGEM`; segunda captura (quando o veículo retorna vazio/carregado) registra "peso de saída" e o sistema calcula o líquido pela diferença.
3. Cada confirmação é salva localmente e entra na fila de sincronização — o operador não precisa esperar internet para seguir pesando o próximo veículo/animal.
4. O cabeçalho da tela mostra a hora da última sincronização bem-sucedida.

## 7. Limitações conhecidas / pendências

- **Sem módulo de billing próprio ainda:** o gate de visibilidade do menu no `apps/web` reaproveita `A2_CAMPO` temporariamente. Definir o módulo definitivo (ex. `O4_BALANCA`) e o plano em que entra é decisão de produto pendente.
- **Sem bridge de hardware:** indicadores de balança eletrônica (Toledo, Filizola, Digitron etc.) não são lidos automaticamente — desenho já previsto (bridge local + rede LAN), implementação é fase futura.
- **Sem ícones reais no manifest do PWA** (`apps/balanca/public/manifest.json` está sem `icons`) — necessário antes de publicar em produção para a instalação ficar visualmente completa.
- **Vínculo automático com módulos clientes** (colheita, compras, vendas, pecuária chamando `PesagemService.solicitar_pesagem()` de verdade) ainda não foi cabeado em nenhum módulo piloto — hoje a criação de ordens é testável via API (`POST /api/v1/balanca/ordens`), mas nenhuma tela de colheita/compra/venda chama isso automaticamente ainda.

## 8. Referências técnicas

| O quê | Onde |
|---|---|
| Backend (models, service, router) | `services/api/balanca/` |
| Migration | `services/api/migrations/versions/20260816_balanca_modulo.py` |
| Teste de isolamento de tenant | `services/api/tests/integration/balanca/test_balanca_tenant_isolation.py` |
| PWA da estação | `apps/balanca/` |
| Tela administrativa (apps/web) | `apps/web/src/app/(dashboard)/dashboard/operacional/balanca/dispositivos/` |
| Componentes da tela admin | `apps/web/src/components/balanca/` |
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
| GET | `/api/v1/balanca/sync/pull` | PWA busca ordens pendentes (token de dispositivo) |
| POST | `/api/v1/balanca/sync/push` | PWA envia pesagens capturadas (token de dispositivo) |
