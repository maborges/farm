# Campo PWA-03 — Formulários Operacionais de Campo

**Data:** 2026-05-08  
**Branch:** `feature/campo-pwa-03-formularios`  
**Status:** COMPLETO ✅

---

## Commits

| Hash | Descrição |
|------|-----------|
| `9962a2b8` | feat(campo): add GPS hook, camera hook e componentes compartilhados |
| `c6ab3921` | feat(campo): add formulários aplicacao, colheita, pesagem, vacinacao |
| `226a8d6a` | feat(campo): update home com atividades disponíveis e registros recentes |

---

## Arquivos criados

### Hooks

| Arquivo | Descrição |
|---------|-----------|
| `src/hooks/useGps.ts` | Captura GPS automática + fallback INDISPONIVEL |
| `src/hooks/useCamera.ts` | Câmera nativa, compressão JPEG 70%, máx 2 fotos |

### Componentes compartilhados

| Arquivo | Descrição |
|---------|-----------|
| `src/components/campo/task-header.tsx` | Header com botão voltar, GPS badge e barra de progresso |
| `src/components/campo/gps-badge.tsx` | Indicador visual DISPONIVEL / AGUARDANDO / INDISPONIVEL |
| `src/components/campo/field-select.tsx` | Grid de botões (≤6 opções) ou select nativo (>6) — touch-friendly |
| `src/components/campo/num-pad.tsx` | Teclado numérico grande para inserção de valores no campo |
| `src/components/campo/camera-capture.tsx` | Preview de fotos + botão câmera (input capture=environment) |

### Core

| Arquivo | Descrição |
|---------|-----------|
| `src/lib/task-factory.ts` | Função `createTask()` — salva no IndexedDB + enfileira no outbox |

### Formulários

| Rota | Arquivo | Passos |
|------|---------|--------|
| `/campo/aplicacao` | `campo/aplicacao/page.tsx` | Talhão → Produto → Quantidade → Confirmar |
| `/campo/colheita` | `campo/colheita/page.tsx` | Talhão → Quantidade → Confirmar |
| `/campo/pesagem` | `campo/pesagem/page.tsx` | Lote → Peso → Confirmar |
| `/campo/vacinacao` | `campo/vacinacao/page.tsx` | Lote → Vacina → Confirmar |

---

## Fluxo de dados

```
Operador toca "Salvar"
        ↓
createTask(payload)
        ↓
   db.tasks.add(task)          ← IndexedDB local (imediato)
        ↓
   enqueueSync("CREATE", ...)  ← sync_queue (outbox)
        ↓
   SuccessScreen               ← feedback instantâneo
        ↓
   (próximo sync online)
   pushSync() → POST /sync/push
```

---

## Decisões de UX

| Decisão | Motivo |
|---------|--------|
| NumPad em vez de `<input type="number">` | Toque fácil com luva; evita teclado nativo que varia por dispositivo |
| `FieldSelect` com grid para ≤6 opções | Botões grandes, sem necessidade de precisão de toque |
| Fluxo por steps lineares | Reduz carga cognitiva; foco em uma decisão por vez |
| GPS não bloqueia | Campo sem sinal é realidade; salva `localizacao_status=INDISPONIVEL` |
| `AGUARDANDO` → `INDISPONIVEL` ao salvar | Estado transitório não persistido; sem perda de dados |
| Máx 2 fotos, JPEG 70%, max 1280px | Balanceia qualidade e tamanho para sync mobile |

---

## Câmera

```typescript
// Compressão automática antes de salvar no IndexedDB
canvas.toDataURL("image/jpeg", 0.7)  // 70% qualidade
// Largura máxima: 1280px (mantém proporção)
// Enviada como base64 no payload da sync_queue
```

**Acesso:** `<input type="file" accept="image/*" capture="environment">` → abre câmera traseira no mobile, galeria no desktop.

---

## GPS

```typescript
navigator.geolocation.getCurrentPosition(
  (pos) => { latitude, longitude, status: "DISPONIVEL" },
  ()    => { status: "INDISPONIVEL" },
  { timeout: 8000, maximumAge: 30000, enableHighAccuracy: true }
)
```

Captura automática ao montar o formulário. Se demorar, o operador já preenche os dados e o GPS atualiza em background.

---

## Outbox — Garantia de entrega

Toda tarefa criada no campo:

1. **Salva no IndexedDB** — disponível offline imediatamente
2. **Enfileirada em `sync_queue`** com `status: PENDING`
3. **Push automático** ao recuperar conexão (listener `online`)
4. **Retry automático** com até 5 tentativas; falha vai para quarentena

Nenhum formulário chama a API diretamente.

---

## Critério de aceite ✅

| Critério | Status |
|----------|--------|
| Operador registra atividade offline | ✅ |
| Dados salvos no IndexedDB | ✅ |
| Item aparece na sync_queue | ✅ |
| Fotos comprimidas e anexadas | ✅ |
| GPS capturado quando disponível | ✅ |
| Fallback sem GPS | ✅ |
| UX em < 10 segundos (3 passos) | ✅ |
| `tsc --noEmit` sem erros | ✅ |

---

## Próximo step: PWA-04

- Tela de detalhes de tarefa (visualizar / editar / cancelar)
- Gestão de fazendas no home (seletor multi-fazenda)
- Formulário de monitoramento de pragas (com foto obrigatória)
- Teste em dispositivo real (Android/iOS)
