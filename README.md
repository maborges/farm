# AgroSaaS - Plataforma de Gestão Rural Modular

Sistema avançado para gestão de fazendas, focado em produtividade, isolamento de dados (multi-tenancy) e interface de alta performance.

## Leitura Inicial

A ordem oficial de leitura para agentes de IA vive em **`docs/architecture/ai-bootstrap.md`** — não repetida aqui.

Utilize português (pt-BR) para documentos e interações com o usuário, com acentuação correta e linguagem não técnica nas explicações.

> Cópias espelhadas em `apps/web/` existem para compatibilidade histórica. A fonte oficial fica na raiz do repositório — confirme o caminho ativo antes de editar (ver `CONTEXTO.md` → "Sinais de Atenção").

## Arquitetura do Sistema

Monorepo dividido em:
- **apps/web**: Interface Next.js 16 com shadcn/ui e Zustand.
- **apps/campo**: PWA de campo offline-first, extensão oficial do Caderno de Campo.
- **services/api**: Backend Python com FastAPI, SQLAlchemy e PostgreSQL.
- **packages/zod-schemas**: Contratos compartilhados (Shared Schemas).2

Inventário técnico completo (versões, libs, infra): `docs/architecture/architecture-inventory.md`.

## Módulos Implementados

- Identidade e Multi-Tenancy (auth, RBAC, onboarding, convites)
- Gestão Agrícola e Pecuária (talhões, safras, análise de solo, DRE por safra)
- Templates e Governança de fase de safra
- Alertas e Recomendações financeiras automáticas
- Suprimentos e Compras (reposição automática, cotações, análise de melhor fornecedor)
- Frota (manutenção preventiva, custos operacionais, benchmarks)
- Copiloto Financeiro e IA (simulação, plano de ação, autopilot adaptativo)
- Growth & A/B Testing, Telemetria de UX adaptativa
- Hedge de commodities (Mark-to-Market, exposição física × financeira)
- Vínculo territorial/fundiário (Propriedade ↔ Imóvel Rural)

Detalhamento de cada feature, decisões e histórico de implementação: `docs/CHANGELOG.md` (não faz parte da leitura padrão — consulte apenas quando precisar entender por que algo foi construído de determinada forma).

## Conceitos-Chave: Propriedade, Talhão e Unidade Produtiva

- **Propriedade / Unidade Produtiva**: cadastro mestre da fazenda (nome, tipo, documentos, endereço, áreas, geometria).
- **Área Rural / Talhão**: divisão física dentro da propriedade — base para solo, caderno de campo, NDVI etc.
- **Production Unit da safra**: vínculo `cultivo + área + participação` dentro de uma safra específica.
- **Fluxo**: cadastra-se a propriedade → gera/organiza talhões → a safra vincula em `production-units` → módulos agrícolas operam sobre esses vínculos.

Regras completas de fronteira territorial/fundiária: `docs/architecture/agrosaas-domain-map.md`.

## Referência Oficial FIELD-CORE

Arquitetura consolidada do Caderno de Campo (governança, cadeia documental, papel do PWA): `docs/architecture/field-core-final-governance.md`.

## Como Executar

### Backend
```bash
cd /opt/lampp/htdocs/farm/services/api
source .venv/bin/activate
./start_server.sh
# ou: uvicorn main:app --reload
```
Travado? `sudo lsof -i :8000` para listar, `sudo kill -9 PID` para matar.
Parar de forma limpa: `pkill -f "uvicorn main:app"`

### Worker de Automações (scheduler)
```bash
cd /opt/lampp/htdocs/farm
source .venv/bin/activate
python scripts/run_worker.py
```

### Frontend Web
```bash
cd /opt/lampp/htdocs/farm/apps/web
pnpm run dev
```
Roda em `http://localhost:3000`.

### PWA de Campo
```bash
cd /opt/lampp/htdocs/farm/apps/campo
pnpm run dev
```
Roda em `http://localhost:3002`, abre em `/home` após ativação do dispositivo.
Primeira ativação: fluxo `/activate` → `/pin`.

### Matar tudo
```bash
pkill -f "uvicorn|next dev"
```