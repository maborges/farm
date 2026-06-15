# Runbook - Hedge MVP

Este documento fornece as diretrizes e instruções operacionais para lidar com o módulo F4_HEDGING (Hedge MVP) em ambientes de testes, staging e produção.

## 1. Visão Geral Funcional
O Hedge MVP tem escopo contido. Ele é responsável por:
1. **Contratos Futuros**: Cadastro manual do papel (Bolsa/Balcão), definindo Mercadoria, Safra, Mês de Vencimento, Tipo de Posição (Compra ou Venda).
2. **Registros de Operações**: Materialização das movimentações em cima de um contrato aberto (Abertura de Lote, Rolagem, Ajuste ou Encerramento).
3. **Painel de Exposição**: Projeção em tempo real de:
   - Volume Produzido Estimado
   - Volume Físico Comercializado (Vendido)
   - Volume Financeiro em Contratos de Venda (Protegido)
   - Percentual de Cobertura Final.

O Módulo **NÃO** faz:
- Chamada de Margem (Margin Call).
- Integração direta de preços de tela de corretoras (Marcação a Mercado / MtM).
- CPR ou Barter (Ficam em Crédito e Comercialização, respectivamente).

## 2. Check de Deploy

Antes de colocar o Hedge MVP em Produção, os seguintes cheques DEVEM passar:
- As migrations `hedge_mvp_001.py` e `hedge_mvp_merge_001.py` foram aplicadas via alembic.
- O Enum de Roles (`RBAC`) contempla o módulo `F4_HEDGING`.

## 3. Comandos de Verificação e QA

**Backend Tests** (estrito no módulo hedge para evitar poluição por testes legados):
```bash
cd services/api
PYTHONPATH=. .venv/bin/pytest tests/integration/enterprise/test_hedge_mvp.py -v
```

**Frontend Tests & Lints**:
```bash
cd apps/web
npx tsc --noEmit
npx eslint "src/app/(dashboard)/dashboard/financeiro/hedge/**/*.{ts,tsx}"
npx playwright test tests/e2e/hedge-mvp.spec.ts
```

## 4. Troubleshooting Conhecido

### 4.1 "Banco de Dados Indisponível ou pool de conexões esgotado" (HTTP 503)
**Sintoma**: O carregamento do Painel falha no backend com timeout no SQLAlchemy.
**Causa Histórica**: Concorrência excessiva. A API de telemetria e o Painel chamam muitos endpoints sequenciais que prendiam as conexões.
**Resolução (Mitigada)**: O problema foi resolvido refatorando a telemetria via uso de funções `COUNT(CASE WHEN...)`, liberando o pool para consultas de `HedgeExposure`.

### 4.2 Playwright Fallbacks
Se o playwright disparar `Executable doesn't exist at /home/.../ms-playwright/firefox`, o teste continuará quebrando nos engines não instalados.
**Solução**: Executar `npx playwright install chromium` e direcionar os testes locais apenas para webkit ou chromium, que são as rotas ativas da CI/CD.

### 4.3 Stale UI - React Compiler Warning
Se os logs do eslint indicarem erro em `watch()` dentro das views de criação (`ContratosClient` / `RegistrosClient`), lembre-se que isso é uma limitação arquitetural do hook. O React 19 reporta warning. Não quebra a interface, contudo.

## 5. Próximos Passos (V2)
A tabela `HedgePosition` foi mapeada como "projeção na mosca" nesta release. Para a V2, caso a latência do painel aumente com milhões de registros de soja/milho, recomenda-se criar uma Materialized View ou consolidar por eventos assíncronos.
