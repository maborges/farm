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

2. **Offline-first via app dedicado (`apps/balanca`), reaproveitando o padrão já existente em `apps/campo`:**
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
- `OrdemPesagem` (`balanca_ordens`): solicitação criada pelo módulo cliente — `origem_tipo`, `origem_id`, `subject_type` (VEICULO/ANIMAL/PESSOA), status (PENDENTE/EM_PESAGEM/CONCLUIDA/CANCELADA)
- `Pesagem` (`balanca_pesagens`): resultado — peso_bruto/tara/liquido (`Numeric`), tipo_pesagem (UNICA/DUPLA), `captured_via`, `client_id` (idempotência), timestamps de entrada/saída
- `SyncTombstoneBalanca` (`balanca_sync_tombstones`): mesmo padrão de `campo`

## Ordem de implementação

1. ✅ Migration + models (`DispositivoBalanca`, `OrdemPesagem`, `Pesagem`, tombstone)
2. `PesagemService` (API interna de solicitação) + `SyncService` (push/pull)
3. Router + registro em `main.py`
4. Scaffold do `apps/balanca` (PWA: captura manual primeiro)
5. Piloto de integração: romaneio de colheita (dupla pesagem)
6. Testes de isolamento de tenant + idempotência de sync
7. Bridge de hardware (fase posterior)
