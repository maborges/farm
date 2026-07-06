# EXECUTION-32A1 — Contratos Oficiais do Dashboard Executivo

## Objetivo

Definir os contratos de consumo do Dashboard Geral sem recalcular indicadores no próprio dashboard.

Premissas adotadas:

- Financeiro já possui resumo oficial reutilizável.
- Agricultura já possui dashboard consolidado reutilizável.
- Pecuária ainda precisa de um resumo executivo único.
- Operacional ainda precisa de um resumo transversal.
- O Dashboard Geral só compõe e exibe; ele não calcula domínio.

---

## 1. Resumo Executivo Pecuário

### Contrato proposto

```ts
type ResumoExecutivoPecuaria = {
  animais_ativos: number;
  lotes_ativos: number;
  piquetes_ativos: number;
  peso_total_kg: number;
  peso_medio_kg: number;
  manejos_pendentes: number;
  vacinacoes_pendentes: number;
  custo_sanitario_acumulado: number;
};
```

### Fonte oficial por campo

| Campo | Origem | Endpoint atual | Service atual | Status |
| --- | --- | --- | --- | --- |
| `animais_ativos` | `Animal` ativo por lote/tenant | `GET /pecuaria/lotes/{lote_id}/indicadores` e listagem de lotes | `LoteIndicadoresService` + `PecuariaDashboard` | ADAPTAR |
| `lotes_ativos` | `LoteAnimal` ativo | `GET /dashboard/pecuaria` e `GET /pecuaria/lotes` | `PecuariaDashboard` / `LoteBovinoService` | REUTILIZAR / ADAPTAR |
| `piquetes_ativos` | `AreaRural` tipo PIQUETE ativo | `GET /dashboard/pecuaria` | `PecuariaDashboard` | REUTILIZAR |
| `peso_total_kg` | Soma de `Animal.peso_atual_kg` | `GET /pecuaria/lotes/{lote_id}/indicadores` | `LoteIndicadoresService` | ADAPTAR |
| `peso_medio_kg` | Média derivada de animais com peso | `GET /pecuaria/lotes/{lote_id}/indicadores` | `LoteIndicadoresService` | REUTILIZAR |
| `manejos_pendentes` | `TarefaCampo` pecuária não concluída | `GET /pecuaria/campo-sync/sync-status` e `GET /campo/tarefas` | `ManejoSyncService` / `CampoService` | CRIAR / ADAPTAR |
| `vacinacoes_pendentes` | tarefas `VACINACAO` pendentes | `GET /pecuaria/campo-sync/sync-status` | `CampoService` + `ManejoSyncService` | CRIAR |
| `custo_sanitario_acumulado` | `CostAllocation` + `EstoqueMovimento` da vacinação | `GET /pecuaria/lotes/{lote_id}/resumo-sanitario` e `GET /pecuaria/lotes/{lote_id}/indicadores` | `LoteResumoSanitarioService` + `LoteIndicadoresService` | REUTILIZAR / ADAPTAR |

### Interpretação técnica

- `peso_medio_kg` já existe de forma oficial por lote e é reutilizável.
- `custo_sanitario_acumulado` já existe de forma oficial por lote, mas para o dashboard geral precisa ser agregado por tenant/fazenda.
- `manejos_pendentes` e `vacinacoes_pendentes` ainda não estão prontos como resumo executivo único; existem no Campo e no sync, mas precisam de agregação.
- `animais_ativos`, `lotes_ativos` e `piquetes_ativos` já existem como base de cálculo e podem ser agregados sem invenção de regra nova.

### Custo estimado

- Se derivado do painel pecuário atual: 2 a 4 queries.
- Se consolidado em um serviço oficial único: 3 a 5 queries.
- Cache recomendado: 60 s a 300 s.

---

## 2. Resumo Operacional

### Contrato proposto

```ts
type ResumoOperacional = {
  pendentes: number;
  em_execucao: number;
  atrasadas: number;
  concluidas: number;
  agricultura?: {
    pendentes: number;
    em_execucao: number;
    atrasadas: number;
    concluidas: number;
  };
  pecuaria?: {
    pendentes: number;
    em_execucao: number;
    atrasadas: number;
    concluidas: number;
  };
};
```

### Fontes por domínio

#### Agricultura

- `TarefaCampo` agrícola ainda é a fonte real para estado operacional de Campo.
- `OperacaoAgricola` é a fonte de detalhe do domínio agrícola, mas não é boa como resumo transversal.
- `GET /agricola/tarefas/safras/{safra_id}/tarefas` em [services/api/agricola/tarefas/router.py:15](/opt/lampp/htdocs/farm/services/api/agricola/tarefas/router.py:15) é a fonte de tarefas planejadas da safra, mas não é consolidado geral.

#### Pecuária

- `TarefaCampo` com `module = pecuaria` é a fonte oficial de manejos.
- `GET /pecuaria/campo-sync/sync-status` em [services/api/pecuaria/routers/campo_sync.py:19](/opt/lampp/htdocs/farm/services/api/pecuaria/routers/campo_sync.py:19) já expõe estado de sincronização e status de processamento.
- `ManejoSyncService` é o motor de materialização, não o resumo executivo.

#### Campo

- `GET /campo/tarefas` em [services/api/campo/router.py:287](/opt/lampp/htdocs/farm/services/api/campo/router.py:287) já expõe listagem de tarefas programadas.
- O serviço de Campo já distingue `PENDENTE`, `EM_EXECUCAO`, `CONCLUIDA`, `CANCELADA`, `INVALIDADA` em [services/api/campo/service.py:278](/opt/lampp/htdocs/farm/services/api/campo/service.py:278).

### Status de existência

- `pendentes`: existe distribuído em Campo e Agricultura/Pecuária, mas não como contrato transversal único.
- `em_execucao`: existe no Campo, mas precisa de consolidação.
- `atrasadas`: existe como conceito em tarefas programadas e pendências por data, mas não como contrato unificado.
- `concluidas`: existe nas tarefas e nas execuções, mas também distribuído.

### Conclusão

O resumo operacional **precisa ser criado** como contrato oficial único. Ele deve ser uma agregação leve sobre `TarefaCampo` e, quando necessário, sobre as especializações por domínio.

### Custo estimado

- Versão mínima: 1 a 2 queries bem indexadas em `campo_tarefas`.
- Versão por domínio: 2 a 4 queries.
- Cache recomendado: 15 s a 60 s.

---

## 3. Compatibilidade Multi-Domínio

### Fazenda agrícola

Blocos visíveis:

- Financeiro
- Operacional
- Agricultura

Bloco oculto:

- Pecuária

### Fazenda pecuária

Blocos visíveis:

- Financeiro
- Operacional
- Pecuária

Bloco oculto:

- Agricultura

### Fazenda mista

Blocos visíveis:

- Financeiro
- Operacional
- Agricultura
- Pecuária

### Regra de exibição

- Se um domínio não existir, o bloco não deve renderizar.
- Se o domínio existir, mas estiver sem dados, exibir estado vazio amigável.
- O bloco operacional sempre deve existir, porque é transversal.

---

## 4. Performance

### Resumo Executivo Pecuário

- Queries estimadas: 3 a 5.
- Cache: 60 s a 300 s.
- Risco de N+1: médio, se continuar consultando por lote isoladamente.
- Estratégia recomendada: consolidar em um único service por tenant/fazenda com agregações por `Animal`, `LoteAnimal`, `AreaRural`, `TarefaCampo`, `EstoqueMovimento` e `CostAllocation`.

### Resumo Operacional

- Queries estimadas: 1 a 3.
- Cache: 15 s a 60 s.
- Risco de N+1: baixo se o resumo for feito com `COUNT(*)` e `GROUP BY`.
- Estratégia recomendada: agregação única em `campo_tarefas`, com filtros por `tenant_id`, `unidade_produtiva_id` e `module`.

### Financeiro e Agricultura

- Financeiro executivo já é relativamente barato e oficial.
- Agricultura consolidada já existe, mas pode ficar cara se o dashboard geral puxar também safra detalhada e IA.
- Estratégia recomendada: consumir apenas o resumo consolidado e evitar cards de detalhamento.

---

## 5. Reutilização, adaptação e criação

### REUTILIZAR

- `GET /financeiro/relatorios/dashboard`
- `GET /financeiro/relatorios/fluxo-caixa`
- `GET /agricola/dashboard/`
- `GET /pecuaria/lotes/{lote_id}/indicadores` para cálculos de lote
- `GET /pecuaria/lotes/{lote_id}/resumo-sanitario` para custo sanitário por lote
- `GET /campo/tarefas` como base de listagem operacional

### ADAPTAR

- `GET /financeiro/lancamentos/resumo`
- `GET /financeiro/lancamentos/insight`
- `GET /dashboard/pecuaria` atual do frontend
- `GET /pecuaria/campo-sync/sync-status`

### CRIAR

- Resumo executivo pecuário oficial por tenant/fazenda.
- Resumo operacional transversal oficial.

---

## 6. Riscos

- Risco de duplicar cálculo de pecuária no dashboard geral se ele continuar lendo diretamente lotes e manejos isolados.
- Risco de operar com “dados de lote” onde o contrato precisa ser de “fazenda”.
- Risco de N+1 se o frontend pedir vários cards separados em vez de um resumo oficial.
- Risco de misturar safra com operação geral e degradar UX.
- Risco de usar sinal de módulo como substituto de dado real.

---

## 7. Ordem recomendada de implementação

### EXECUTION-32A.2

Criar os contratos oficiais e os agregadores backend:

- resumo executivo pecuário;
- resumo operacional transversal.

### EXECUTION-32A.3

Consumir esses contratos no Dashboard Geral:

- financeiro primeiro;
- operacional segundo;
- agricultura condicional;
- pecuária condicional.

### EXECUTION-32A.4

Hardening:

- cache;
- smoke em fazenda agrícola, pecuária e mista;
- verificação de blocos vazios;
- validação de performance.

---

## Resposta objetiva

1. **Contrato final do Resumo Executivo Pecuário:** `animais_ativos`, `lotes_ativos`, `piquetes_ativos`, `peso_total_kg`, `peso_medio_kg`, `manejos_pendentes`, `vacinacoes_pendentes`, `custo_sanitario_acumulado`.
2. **Contrato final do Resumo Operacional:** `pendentes`, `em_execucao`, `atrasadas`, `concluidas`, com quebramento opcional por domínio.
3. **Fontes oficiais utilizadas:** `DashboardService` financeiro, `DashboardAgricolaService`, `LoteIndicadoresService`, `LoteResumoSanitarioService`, `CampoService`.
4. **Campos reutilizados:** peso médio, custo sanitário por lote, totais financeiros, safra consolidada.
5. **Campos adaptados:** animais ativos, lotes ativos, piquetes ativos, manejos pendentes, vacinações pendentes, resumo operacional.
6. **Campos novos:** resumo operacional transversal e resumo executivo pecuário oficial.
7. **Quantidade estimada de queries:** 3 a 5 para pecuária, 1 a 3 para operacional.
8. **Estratégia de cache:** 15 s a 60 s para operacional; 60 s a 300 s para pecuária; financeiro e agrícola já podem seguir a política atual.
9. **Riscos:** N+1, duplicação de regra, excesso de cards safra-first, falso positivo de domínio.
10. **Ordem de implementação:** primeiro os contratos oficiais, depois o consumo no dashboard, depois performance e smoke.
