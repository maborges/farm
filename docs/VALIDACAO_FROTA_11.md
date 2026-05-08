# Validação Frota-11

## Ambiente usado

- Data da validação: `2026-05-07`
- Workspace: `/opt/lampp/htdocs/farm`
- Banco: PostgreSQL remoto configurado em `services/api/.env.local`
- API validada em: `http://127.0.0.1:8001`
- Frontend validado em: `http://127.0.0.1:3002`
- Perfis usados:
  - `BASICO`: `frota11.basico.1778177736@example.com`
  - `PROFISSIONAL`: `frota11.prof.1778177736@example.com`
  - `ENTERPRISE`: `frota11.ent.1778177736@example.com`

## Comandos executados

- Migrations:
  - `cd services/api && .venv/bin/alembic upgrade 20260507_frota_jornadas`
- API:
  - `cd services/api && .venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 8001`
- Frontend:
  - `cd apps/web && BACKEND_URL=http://127.0.0.1:8001 npm run dev -- --port 3002`
- Validação técnica:
  - `python3 -m py_compile services/api/core/services/auth_service.py services/api/operacional/schemas/frota.py services/api/operacional/services/frota_jornada_service.py services/api/operacional/routers/frota.py services/api/operacional/services/frota_service.py services/api/migrations/versions/20260507_frota_jornadas_equipamento.py services/api/migrations/versions/stepGrowth24_ia_growth_learning_weights.py`
  - `pnpm -C apps/web exec tsc --noEmit`
  - `pnpm -C apps/web exec eslint 'src/app/(dashboard)/dashboard/operacional/frota/page.tsx' 'src/app/(dashboard)/dashboard/operacional/frota/[equipamentoId]/page.tsx' 'src/app/(dashboard)/dashboard/operacional/frota/agricultura/page.tsx' 'src/lib/sidebar-config.ts' 'src/components/layout/app-sidebar.tsx' --ext .ts,.tsx`
- Validação funcional:
  - Script real de API contra `8001` e PostgreSQL
  - Requisições autenticadas ao frontend em `3002` com cookies reais

## Correções pequenas aplicadas nesta etapa

- `services/api/core/services/auth_service.py`
  - corrigida geração de `slug` no `create-subscription`
  - `switch-tenant` passou a emitir claim `role`, inclusive `owner`
- `services/api/operacional/services/frota_jornada_service.py`
  - adicionado `_obter_equipamento(...)`
- `services/api/operacional/routers/frota.py`
  - criação de plano preventivo passou a fazer `commit` e `refresh`
- `services/api/operacional/services/frota_service.py`
  - normalização de payload legado de Frota para o model atual
- `services/api/operacional/schemas/frota.py`
  - response schema passou a aceitar `EM_MANUTENCAO`
- Migrations:
  - `20260507_frota_jornadas_equipamento.py`: `down_revision` corrigido
  - `stepGrowth24_ia_growth_learning_weights.py`: `down_revision` corrigido

## Cenários testados

### BASICO

- `dashboard essencial`: aprovado
- `listar equipamentos`: aprovado
- `abrir detalhe básico`: aprovado
- `criar OS básica`: aprovado
- `consultar documentos`: aprovado
- `402 em consumo`: aprovado
- `402 em inteligência`: aprovado
- `402 em Frota x Agricultura`: aprovado
- `registrar abastecimento`: falhou no ambiente
  - retorno: `404 Produto de estoque 'DIESEL' não encontrado para baixa`

### PROFISSIONAL

- `manutenção preventiva`: aprovado
- `gerar OS preventiva`: aprovado
- `preventiva não duplica OS`: aprovado
- `consumo/eficiência`: aprovado
- `disponibilidade`: aprovado
- `bloquear/liberar equipamento`: aprovado
- `jornada não abre com equipamento bloqueado`: aprovado funcionalmente
  - retorno observado: `422` com motivo do bloqueio
- `criar jornada`: aprovado
- `não permite duas jornadas abertas`: aprovado funcionalmente
  - retorno observado: `422 Já existe uma jornada aberta para este equipamento`
- `finalizar jornada`: aprovado
- `finalização atualiza horímetro/km`: aprovado
- `custos`: aprovado
- `402 em inteligência`: aprovado
- `402 em Frota x Agricultura`: aprovado
- `registrar abastecimento base custos`: falhou no ambiente
  - retorno: `404 Produto de estoque 'DIESEL' não encontrado para baixa`
- `custo não duplica OS + financeiro`: não conclusivo no cenário completo
  - esperado: `500.0`
  - obtido: `300.0`
  - motivo: abastecimento não entrou no custo porque o ambiente não tinha o produto de estoque `DIESEL`

### ENTERPRISE

- `inteligência operacional`: aprovado
- `score de risco`: aprovado
- `Frota x Agricultura`: aprovado
- `localizar área raiz`: aprovado
- `criar gleba`: aprovado
- `criar talhão`: aprovado
- `criar safra`: aprovado
- `criar jornada agrícola`: aprovado
- `finalizar jornada agrícola`: aprovado
- `visualizar custo por safra/talhão/operação`: aprovado
- `detalhar custo por safra`: aprovado
- `detalhar custo por talhão`: aprovado
- `detalhar custo por operação`: aprovado

### Regras críticas

- `tenant isolation`: aprovado
  - `BASICO` recebeu `404` ao consultar equipamento do tenant `PROFISSIONAL`
- `backend protege endpoints por plano`: aprovado
  - `402` confirmados em `BASICO` e `PROFISSIONAL`
- `menu filtrado por plano`: validado por implementação
  - regra encontrada em `apps/web/src/lib/sidebar-config.ts`
  - `PROFISSIONAL` exige `minimumTier: 'PROFISSIONAL'`
  - `ENTERPRISE` exige `minimumTier: 'ENTERPRISE'`
- `CTA de upgrade`: validado por implementação e rotas reais
  - páginas protegidas usam `TierUpgradeCard`
  - arquivos confirmados:
    - `apps/web/src/app/(dashboard)/dashboard/operacional/frota/consumo/page.tsx`
    - `.../manutencao-preventiva/page.tsx`
    - `.../disponibilidade/page.tsx`
    - `.../jornadas/page.tsx`
    - `.../inteligencia/page.tsx`
    - `.../agricultura/page.tsx`

## Resultado de cada cenário

- API: `58` cenários executados, `54` aprovados, `4` falhas
- Frontend:
  - `/dashboard/operacional/frota`: `200`
  - `/dashboard/operacional/frota/consumo`: `200`
  - `/dashboard/operacional/frota/inteligencia`: `200`
  - `/dashboard/operacional/frota/agricultura`: `200`

## Bugs encontrados

### Alto impacto

- Ambiente sem produto de estoque `DIESEL`
  - afeta `POST /api/v1/frota/abastecimentos`
  - impede validar custo completo com combustível no cenário real

### Médio impacto

- Contrato HTTP das regras de bloqueio usa `422` em vez de `400`
  - cenários afetados:
    - equipamento bloqueado ao abrir jornada
    - segunda jornada aberta para o mesmo equipamento
  - regra de negócio funciona, mas o status HTTP diverge do esperado inicial

### Baixo impacto

- A árvore agrícola exige hierarquia correta `AREA_RURAL -> GLEBA -> TALHAO`
  - tentativa direta `AREA_RURAL -> TALHAO` falha por validação
  - comportamento é consistente com o model atual, mas precisa ser respeitado nos roteiros de teste

## Pendências

- O grafo Alembic ainda possui múltiplos heads no repositório
  - a validação usou upgrade direcionado até `20260507_frota_jornadas`
  - `alembic upgrade head` ainda precisa ser saneado fora deste step
- A validação visual completa do frontend ficou parcial
  - motivo: ambiente sem navegador headless disponível
  - o frontend foi executado e as rotas principais responderam `200`, mas a checagem visual de menu/CTA foi complementada pela implementação real em código
- O cenário de custo total com combustível precisa ser refeito em um ambiente com catálogo/estoque preparado para `DIESEL`

## Validações técnicas

- `py_compile backend`: aprovado
- `pnpm -C apps/web exec tsc --noEmit`: aprovado
- `eslint frontend alterado`: aprovado com `1 warning` pré-existente
  - `apps/web/src/components/layout/app-sidebar.tsx:289`
  - warning `@next/next/no-img-element`

## Conclusão final

`APROVADO COM RESSALVAS`

O módulo Frota ficou funcional nos fluxos principais de `BASICO`, `PROFISSIONAL` e `ENTERPRISE`, incluindo proteção por plano, tenant isolation, jornadas, preventiva, inteligência e integração agrícola. As ressalvas restantes concentram-se em setup de ambiente para abastecimento/custos com estoque e em pendências técnicas do repositório (`alembic head` múltiplo e ausência de browser headless para inspeção visual completa).
