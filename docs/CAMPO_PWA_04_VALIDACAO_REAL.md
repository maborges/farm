# CAMPO PWA-04 — Caderno de Validação Real

**Branch:** `feature/campo-pwa-04-hardening`  
**Data:** 2026-05-08  
**Objetivo:** Validar comportamento do PWA em dispositivo real antes de evoluir funcionalidades.

---

## Pré-requisitos

- Dispositivo Android/iOS com Chrome ou Safari
- Dispositivo ativado (código de ativação + PIN cadastrado)
- Backend rodando em rede acessível

---

## Checklist de Validação

### 1. Indicador Offline/Online

| # | Ação | Esperado | ✓/✗ |
|---|------|----------|-----|
| 1.1 | Abrir app com Wi-Fi ativo | Nenhum banner visível | |
| 1.2 | Desativar Wi-Fi | Banner cinza "📵 Offline — dados salvos localmente" aparece no topo | |
| 1.3 | Reativar Wi-Fi | Banner verde "🟢 Conexão restaurada — sincronizando..." por ~3s | |
| 1.4 | Após sync com pendentes | Banner some quando pendentes = 0 | |

### 2. Registro Offline

| # | Ação | Esperado | ✓/✗ |
|---|------|----------|-----|
| 2.1 | Desativar Wi-Fi | Banner offline aparece | |
| 2.2 | Registrar uma aplicação completa | Tela de sucesso normal, sem erro | |
| 2.3 | Ver banner | Mostra "1 pendente de sync" | |
| 2.4 | Reativar Wi-Fi | Sync automático dispara, pendente some | |

### 3. Warning de GPS

| # | Ação | Esperado | ✓/✗ |
|---|------|----------|-----|
| 3.1 | Negar permissão de GPS no device | Step "confirmar" mostra "📵 Sem GPS — registro será salvo sem localização" | |
| 3.2 | Clicar "Tentar" no warning | Hook tenta capturar novamente | |
| 3.3 | GPS disponível | Warning não aparece | |
| 3.4 | GPS aguardando | Spinner "Localizando GPS..." | |

### 4. Retry Manual na Fila

| # | Ação | Esperado | ✓/✗ |
|---|------|----------|-----|
| 4.1 | Simular item FAILED (registrar offline com backend fora) | Item aparece na seção "Falhas" da página /sync | |
| 4.2 | Ligar backend e clicar "Tentar novamente" no item | Item sai de FAILED, sync dispara | |
| 4.3 | Clicar "Sincronizar Agora" com Wi-Fi ativo | Status muda para "Sincronizando..." e depois "Sincronizado" | |

### 5. Exportar Logs de Diagnóstico

| # | Ação | Esperado | ✓/✗ |
|---|------|----------|-----|
| 5.1 | Ir para /sync e clicar "Exportar logs de diagnóstico" | Download de arquivo `.json` com entradas de log | |
| 5.2 | Abrir o JSON | Contém `ts`, `level`, `ctx`, `msg` para cada entrada | |

### 6. Error Boundary

| # | Ação | Esperado | ✓/✗ |
|---|------|----------|-----|
| 6.1 | Forçar erro em componente filho (dev only) | Tela "⚠️ Algo deu errado" com botão "Tentar novamente" | |
| 6.2 | Clicar "Tentar novamente" | Estado de erro limpo, app volta ao normal | |
| 6.3 | Clicar "Voltar ao início" | Navega para /home | |

### 7. Crash Recovery (IN_FLIGHT)

| # | Ação | Esperado | ✓/✗ |
|---|------|----------|-----|
| 7.1 | Durante sync, fechar o app abruptamente | Items ficam como IN_FLIGHT no IndexedDB | |
| 7.2 | Reabrir o app | Items IN_FLIGHT voltam para PENDING automaticamente | |
| 7.3 | Sync dispara | Items são enviados normalmente | |

---

## Problemas Encontrados

| Data | Descrição | Severidade | Status |
|------|-----------|-----------|--------|
| | | | |

---

## Aprovação

- [ ] Testador: ___________
- [ ] Data: ___________
- [ ] Dispositivo: ___________
- [ ] Resultado: APROVADO / REPROVADO
