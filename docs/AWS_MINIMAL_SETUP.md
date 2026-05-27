# AgroSaaS - Configuração Mínima na AWS

Data: 2026-05-27  
Objetivo: descrever a configuração mínima para rodar a aplicação com segurança na AWS, preservando compatibilidade com o ambiente local da WSL.

## 1. Arquitetura mínima

- `Route 53` para DNS
- `ACM` para certificado TLS
- `ALB` para entrada HTTPS
- `Frontend` Next.js em serviço separado
- `Backend` FastAPI em serviço separado
- `Worker` separado para jobs em background
- `RDS PostgreSQL 16` em subnet privada
- `ElastiCache Redis` em subnet privada
- `S3` para uploads e arquivos gerados
- `CloudWatch` para logs e alarmes
- `Secrets Manager` para segredos
- `SES` ou SMTP externo para e-mail

## 2. Requisitos do aplicativo

O backend atual já suporta os dois modos abaixo:

- `run_embedded_jobs=true`: jobs executam junto com a API, adequado para desenvolvimento local
- `run_embedded_jobs=false`: jobs rodam em processo separado, adequado para AWS

O storage também é parametrizável:

- `storage_backend=local` para desenvolvimento
- `storage_backend=s3` para produção
- `storage_backend=minio` para cenários equivalentes a S3 em laboratório
- `storage_public_base_url` para resolver URLs públicas de arquivos quando houver bucket/CDN

## 3. Variáveis essenciais por ambiente

### Desenvolvimento local

```env
DATABASE_URL=postgresql+asyncpg://usuario:senha@IP_DO_WSL_DO_BANCO:5432/agrosaas
REDIS_URL=redis://127.0.0.1:6379/0
FRONTEND_URL=http://127.0.0.1:3000
ALLOW_ORIGINS=["http://127.0.0.1:3000","http://localhost:3000"]
storage_backend=local
storage_local_path=/tmp/agrosaas_uploads
run_embedded_jobs=true
```

### Produção AWS

```env
DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@rds-endpoint:5432/agrosaas
REDIS_URL=redis://elasticache-endpoint:6379/0
FRONTEND_URL=https://app.seudominio.com
ALLOW_ORIGINS=["https://app.seudominio.com"]
storage_backend=s3
storage_public_base_url=https://cdn.seudominio.com
run_embedded_jobs=false
```

## 4. Recomendações de rede e segurança

- Banco e Redis em subnets privadas
- Frontend e backend atrás de HTTPS
- CORS restrito ao domínio oficial
- Segredos fora do código
- Backups automáticos do RDS
- Logs centralizados no CloudWatch
- Acesso mínimo por IAM

## 5. Ordem prática de provisionamento

1. Criar VPC, subnets e security groups
2. Provisionar `RDS PostgreSQL`
3. Provisionar `ElastiCache Redis`
4. Criar bucket `S3`
5. Criar certificado `ACM`
6. Publicar backend e frontend
7. Desativar jobs embutidos na API
8. Subir worker separado
9. Configurar domínio no `Route 53`
10. Validar health checks em `/health` e `/health/ready`

## 6. Observação importante

Não é necessário mudar o código entre dev e produção. O comportamento é controlado por variáveis de ambiente, o que permite:

- continuar desenvolvendo na WSL com storage local e jobs no mesmo processo
- rodar na AWS com storage em S3, banco em RDS, Redis gerenciado e worker separado
