# OPS-CHECKOUT-01 — Auditoria e Higienização Segura do Checkout de Produção

## 1. SHAs e estado geral

- Servidor: `ec2-56-126-104-183.sa-east-1.compute.amazonaws.com` (`ip-172-31-18-82`).
- Usuário: `ubuntu`.
- Checkout: `/opt/deepfarms/farm`.
- Branch: `main`.
- SHA atual do checkout: `27f4410349b663187e0805743d8566ecc985c4d3`.
- `origin/main` após `git fetch origin`: `991fe1f0e966593fed2bd04ee6c04c94a8815e49`.
- O checkout está atrás de `origin/main` por dois commits e pode receber fast-forward, mas a working tree não está limpa.

## 2. Inventário exato

### Tracked modificado

| Caminho | Classificação | Evidência | Ação nesta fase |
|---|---|---|---|
| `apps/web/next-env.d.ts` | ARQUIVO GERADO | Importa `./.next/types/routes.d.ts` localmente, enquanto `origin/main` importa `./.next/dev/types/routes.d.ts`; diff de uma linha | Não restaurado |

### Untracked

| Caminho | Classificação | Observação |
|---|---|---|
| `apps/campo/.env.production` | SEGREDO/CONFIGURAÇÃO LOCAL | Não tracked; arquivo de ambiente específico da produção |
| `apps/web/.env.production` | SEGREDO/CONFIGURAÇÃO LOCAL | Não tracked; arquivo de ambiente específico da produção |
| `services/api/.env.production` | SEGREDO/CONFIGURAÇÃO LOCAL | Não tracked; arquivo de ambiente específico da produção |
| `services/api/.env.production.bak-storage-20260911` | BACKUP | Cópia de configuração local; não expor conteúdo |
| `services/api/events/outbox_worker.py.bak-20260910` | BACKUP | Cópia de código operacional, 38.312 bytes |
| `services/api/events/outbox_worker.py.bak-before-fix` | BACKUP | Cópia de código operacional, 38.270 bytes |
| `services/api/integracoes/openweather/worker.py.bak-before-final-fix` | BACKUP | Cópia de código operacional, 4.616 bytes |
| `services/api/integracoes/openweather/worker.py.bak-before-greenlet-fix` | BACKUP | Cópia de código operacional, 4.581 bytes |

### Ignorados

Os demais itens ignorados são artefatos normais de execução, incluindo `.next/`, `node_modules/`, `tsconfig.tsbuildinfo`, `.venv/` e `__pycache__/`. Não foram alterados nem removidos.

## 3. `.env.production`

Os três `.env.production` são untracked e não foram reconhecidos como ignored por `git check-ignore`. Não são tracked e devem ser considerados configuração local/segredo necessária à produção. O conteúdo não foi exibido nem copiado para Git.

Eles podem ser preservados durante uma atualização somente se a estratégia for fast-forward sem remoção de untracked e se nenhum arquivo versionado futuro colidir com esses caminhos. Devem permanecer fora do versionamento.

## 4. `apps/web/next-env.d.ts`

O arquivo é tracked. O diff local altera somente o import de `./.next/dev/types/routes.d.ts` para `./.next/types/routes.d.ts`. A versão em `origin/main` mantém o caminho `./.next/dev/types/routes.d.ts`, igual ao SHA atualmente implantado.

A diferença é compatível com arquivo gerado automaticamente por build do Next. Não há alteração funcional de aplicação identificada. Não foi restaurado nesta auditoria, para respeitar a instrução de não tomar ação antes da classificação formal.

## 5. Backups operacionais

Todos os backups estão dentro do checkout, são untracked, não são ignored e não foram removidos ou movidos. Metadados observados:

- `.env.production.bak-storage-20260911`: 233 bytes, 11/09/2026.
- `outbox_worker.py.bak-20260910`: 38.312 bytes, 10/09/2026.
- `outbox_worker.py.bak-before-fix`: 38.270 bytes, 10/09/2026.
- `worker.py.bak-before-final-fix`: 4.616 bytes, 10/09/2026.
- `worker.py.bak-before-greenlet-fix`: 4.581 bytes, 10/09/2026.

Comparações somente de conteúdo indicaram que `outbox_worker.py.bak-before-fix` é idêntico ao arquivo ativo; os demais backups de código são diferentes do arquivo ativo. Isso confirma que são históricos/operacionais e exige preservação, não limpeza automática.

## 6. Alterações de código

Não há alteração manual de código tracked ativa. O único tracked modificado é o arquivo gerado `next-env.d.ts`. Os backups de código são cópias untracked e não estão sendo carregados pelo serviço por seus nomes `.bak`.

Não foi encontrado hotfix ativo não commitado no caminho versionado. Ainda assim, os backups diferentes devem ser mantidos e revisados pelo responsável operacional antes de qualquer política de arquivamento.

## 7. Riscos

- sobrescrever ou limpar o checkout pode remover configurações e histórico operacional;
- um fast-forward normalmente preserva untracked, mas colisões futuras de caminho devem ser verificadas;
- restaurar `next-env.d.ts` é provavelmente seguro, porém deve ser feito somente na etapa de higienização autorizada;
- backups diferentes podem conter histórico de correções operacionais e não devem ser descartados;
- `.env.production` contém configuração sensível e não deve ser versionado.

## 8. Estratégia segura recomendada

1. Manter cópia externa/backup operacional dos `.env.production` e backups antes de qualquer limpeza.
2. Confirmar com o responsável que os oito untracked são preservados e não representam hotfix ativo.
3. Restaurar somente `apps/web/next-env.d.ts` para o conteúdo de `origin/main`, caso confirmado como artefato gerado.
4. Executar `git pull --ff-only` ou equivalente no checkout, sem `reset --hard` e sem `git clean`.
5. Confirmar novamente `git status`, SHA e existência dos arquivos de ambiente/backups.
6. Só depois repetir os gates de deploy.

Nenhuma etapa de higienização foi executada nesta auditoria.

## 9. Veredicto

**OPS-CHECKOUT-01 — STATUS: GO COM RESSALVAS**

Não há código tracked manual não commitado; os arquivos operacionais e backups estão identificados e preserváveis. Contudo, o checkout não deve ser atualizado até que a preservação formal dos `.env.production` e backups seja confirmada e a diferença gerada do `next-env.d.ts` seja tratada em etapa autorizada. Não executar deploy, reset, clean, remoção, restauração ou build nesta fase.
