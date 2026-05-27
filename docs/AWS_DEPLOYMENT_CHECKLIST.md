# AgroSaaS - Checklist de Deploy na AWS

Data: 2026-05-27  
Objetivo: lista curta e executável para subir a aplicação na AWS sem quebrar o modo local da WSL.

## 1. Antes de publicar

- [ ] Confirmar domínio e zona no `Route 53`
- [ ] Emitir certificado no `ACM`
- [ ] Criar segredos no `Secrets Manager`
- [ ] Provisionar `RDS PostgreSQL 16`
- [ ] Provisionar `ElastiCache Redis`
- [ ] Criar bucket `S3`
- [ ] Definir `ALB`
- [ ] Preparar `CloudWatch`
- [ ] Definir variáveis de ambiente da produção

## 2. Variáveis de produção

```env
DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@rds-endpoint:5432/agrosaas
REDIS_URL=redis://elasticache-endpoint:6379/0
FRONTEND_URL=https://app.seudominio.com
ALLOW_ORIGINS=["https://app.seudominio.com"]
storage_backend=s3
storage_public_base_url=https://cdn.seudominio.com
run_embedded_jobs=false
```

## 3. Publicação da aplicação

- [ ] Publicar o frontend `apps/web`
- [ ] Publicar o backend `services/api`
- [ ] Publicar o worker separado para jobs periódicos
- [ ] Garantir que a API não execute os jobs embutidos em produção
- [ ] Configurar health checks em `/health` e `/health/ready`
- [ ] Validar upload e leitura de arquivos pelo S3
- [ ] Validar conexão com banco e Redis
- [ ] Validar e-mail transacional

## 4. Ordem recomendada

1. Subir infraestrutura base
2. Subir banco e Redis
3. Publicar backend
4. Publicar worker
5. Publicar frontend
6. Configurar DNS
7. Validar fluxos principais

## 5. Validações mínimas

- [ ] Login funciona
- [ ] Dashboard carrega
- [ ] API responde em `/health`
- [ ] API responde em `/health/ready`
- [ ] Upload de arquivo grava no S3
- [ ] Worker executa os jobs planejados
- [ ] E-mails saem com `FRONTEND_URL` correto

## 6. Regras de operação

- Não usar `localhost` em URLs de produção
- Não manter jobs embutidos quando houver mais de uma réplica da API
- Não usar storage local em produção
- Não expor banco e Redis publicamente
- Não versionar segredos no repositório
