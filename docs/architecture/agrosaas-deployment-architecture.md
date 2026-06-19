# AGROSAAS DEPLOYMENT ARCHITECTURE

Este documento descreve a arquitetura de implantação da plataforma AgroSaaS, dividida por ambientes de execução, com base nas configurações e artefatos de infraestrutura presentes no repositório.

## DIAGRAMA GERAL DE IMPLANTAÇÃO (PRODUÇÃO / AWS)

```text
[ Usuário Final / Operador PWA ]
               │
               ▼
        [ DNS / SSL ] (NÃO IDENTIFICADO - Presumido Cloudflare/Route53)
               │
               ▼
        [ Load Balancer ]
               │
      ┌────────┴────────┐
      ▼                 ▼
[ Frontend Web ]   [ Frontend Campo ] (Next.js / Static/Vercel/S3+CloudFront)
      │                 │
      └────────┬────────┘
               ▼
     [ API Gateway / WAF ]
               │
               ▼
      [ Backend FastAPI ] (Monolito Modular - ECS/EKS/EC2)
               │
      ┌────────┼────────┐
      ▼        ▼        ▼
[ PostgreSQL ] [ Redis ] [ Celery Workers ]
  (RDS/Aurora) (ElastiCache) (Background Tasks)
      │
      ▼
[ S3 Storage ] (Arquivos Estáticos / Uploads)
```

---

## AMBIENTES

### # Ambiente Desenvolvimento
Destinado ao desenvolvimento local e testes rápidos.
- **Frontend**: Next.js Dev Server (`next dev --webpack`), porta 3000 (Web) e 3002 (Campo).
- **Backend**: Uvicorn rodando nativamente ou via script `start_backend.sh`, porta 8000.
- **Banco e Cache**: Subidos via `docker-compose.yml` (`postgres:16-alpine` e `redis:7-alpine`).
- **Storage**: Diretório local montado dinamicamente (`/static`).

### # Ambiente Homologação
NÃO IDENTIFICADO formalmente no repositório. Presume-se arquitetura espelho de Produção com instâncias menores.

### # Ambiente Produção
Destinado ao uso real (Referência: `AWS_DEPLOYMENT_CHECKLIST.md`).
- **PostgreSQL**: Instância dedicada garantindo performance para RLS e particionamento multi-tenant.
- **Redis**: Cluster dedicado para controle de Sessões e Filas do Celery.
- **Backend**: FastAPI otimizado via Gunicorn/Uvicorn workers.
- **Frontend**: Build otimizado (`next build`).

---

## ESTRATÉGIAS OPERACIONAIS

### Estratégia de Backup
- **PostgreSQL**: NÃO IDENTIFICADO detalhe técnico no repo, porém em AWS costuma ser snapshot automatizado (RDS) e point-in-time recovery.
- **Redis**: Efêmero para cache; Snapshot condicional se retiver outbox/sync queue.

### Estratégia de Disaster Recovery (DR)
- NÃO IDENTIFICADO (Falta evidência de multi-region configurada nos scripts do repo).

### Estratégia de Atualização
- **Frontend**: Deploy automatizado / Immutable build.
- **Backend**: Migrations gerenciadas pelo **Alembic** (`alembic upgrade head`) executadas isoladamente antes do swap da aplicação.

### Estratégia de Rollback
- **Banco de Dados**: Migrations do Alembic reversas (`alembic downgrade`), com ressalva para operações destrutivas.
- **Aplicação**: Reversão para a tag/imagem Docker anterior estabilizada.
