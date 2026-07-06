# EXECUTION-03B — Saneamento do Alembic e Estratégia de RLS

Data de execução: 2026-06-21

## Base de análise

Referências revisadas:

- [EXECUTION-03](/opt/lampp/htdocs/farm/docs/implementation/reports/EXECUTION-03-fase-2-migration-documental-propriedades-imoveis.md)
- [EXECUTION-02](/opt/lampp/htdocs/farm/docs/implementation/reports/EXECUTION-02-fase-1-data-model-propriedades-imoveis.md)
- [EXECUTION-01B](/opt/lampp/htdocs/farm/docs/implementation/reports/EXECUTION-01B-saneamento-fase-0-propriedades-imoveis.md)
- [ADR-00XX](/opt/lampp/htdocs/farm/docs/architecture/adr/ADR-00XX-convergencia-propriedades-imoveis.md)
- [AGRI-DOMAIN-001](/opt/lampp/htdocs/farm/docs/architecture/standards/AGRI-DOMAIN-001-territorial-fundiario.md)
- [AGRI-DOMAIN-002](/opt/lampp/htdocs/farm/docs/architecture/standards/AGRI-DOMAIN-002-propriedade-imovel.md)
- [AGROSAAS Data Model](/opt/lampp/htdocs/farm/docs/architecture/agrosaas-data-model.md)

---

## 1. Grafo Alembic

### Heads atuais identificados

Leitura obtida por `alembic heads`:

- `b1c2d3e4f5a6` com aviso de revisão duplicada
- `c3d4e5f6a7b8 (head)`
- `ff59b3b71a2d (head)`

### Observação crítica

- O grafo atual tem **múltiplos heads**.
- Existe também **aviso de revisão duplicada** para `b1c2d3e4f5a6`.
- O binário do Alembic foi localizado em `/opt/lampp/htdocs/farm/.venv/bin/alembic`, mas a tentativa de ler `current` falhou por limitação do ambiente com `PermissionError` ao tentar conectar ao banco.

### Ordem e relação já compreendidas

- `b1c2d3e4f5a6` é a revisão de `imoveis_avaliacoes`.
- `c3d4e5f6a7b8` e `ff59b3b71a2d` são heads paralelos.
- A árvore histórica já contém módulos independentes que convergiram em ramos distintos.

### Existe necessidade de merge migration?

- **Sim, recomendada antes da migration real da convergência.**

### A futura migration deve depender de qual head?

- **Após uma merge migration**, a futura migration deve depender do head de merge resultante.
- **Sem merge migration**, ela precisaria escolher um head arbitrariamente e criaria novo head paralelo, o que é indesejável neste momento.

### Há risco de criar novo head paralelo?

- **Sim, alto.**

### O grafo atual permite avanço seguro?

- **Não para a migration real.**
- Permite apenas avanço documental e de planejamento.

---

## 2. Revisão duplicada

### Arquivos que usam a mesma revision id

Foi identificada duplicidade de `revision = 'b1c2d3e4f5a6'` em:

- `services/api/migrations/versions/b1c2d3e4f5a6_add_imoveis_avaliacoes.py`
- `services/api/migrations/versions/b1c2d3e4f5a6_add_plano_canais_comercializacao.py`

### Natureza do problema

- Não são stubs.
- São duas migrations reais com a mesma revision id.
- Isso gera ambiguidade no grafo e é compatível com o warning observado ao carregar o revision map.

### Impacto

- A leitura do grafo pode ficar ambígua.
- A resolução de dependências futuras pode se tornar instável.
- A adição de uma nova migration de convergência pode herdar fragilidade estrutural.

### Proposta de correção segura

- Corrigir a duplicidade em branch controlada, não nesta tarefa documental.
- Reatribuir uma das revisões para id único.
- Atualizar os `down_revision` downstream afetados.
- Se a revisão já estiver aplicada em algum ambiente, tratar o ajuste por revisão de compatibilidade ou merge controlado.

### Status documental

- Duplicidade identificada e compreendida.
- Não alterada.

---

## 3. Estratégia de RLS físico

### Opções avaliadas

#### A) Aplicar RLS físico apenas em `propriedade_imovel`

- Vantagem:
  - menor risco inicial;
  - escopo reduzido;
  - compatível com a estratégia atual de middleware;
  - permite começar pela entidade nova e oficial.
- Desvantagem:
  - não endurece imediatamente o legado.

#### B) Aplicar RLS físico em `propriedade_imovel` e mapear plano separado para tabelas existentes

- Vantagem:
  - segurança imediata na entidade nova;
  - preserva compatibilidade com o legado;
  - permite hardening posterior por etapas.
- Desvantagem:
  - exige disciplina de governança para o segundo plano não ficar indefinido.

#### C) Criar uma ADR específica para RLS físico

- Vantagem:
  - formaliza a decisão de segurança;
  - ajuda a coordenar hardening em múltiplas tabelas.
- Desvantagem:
  - não resolve o problema de escopo da migration por si só.

### Recomendação oficial

- **Adotar a estratégia B como caminho operacional**
  - aplicar RLS físico na futura `propriedade_imovel`;
  - manter um plano separado para endurecimento das tabelas existentes;
  - registrar o hardening legado em documentação complementar/ADR se necessário.

### Compatibilidade com o middleware atual

- Compatível.
- O middleware atual continua responsável pelo isolamento em camada de aplicação.
- O RLS físico entra como camada adicional de proteção, não como substituição imediata de tudo.

### Como tratar `app.current_tenant_id` ausente

- Fail-closed.
- Sem tenant ativo no contexto, não deve haver acesso.

### Como impedir escrita cross-tenant

- Todas as operações devem comparar `tenant_id` da linha com `current_setting('app.current_tenant_id')::uuid`.
- Escreitas fora do tenant devem ser negadas pela policy física.

---

## 4. Enum PostgreSQL versus check constraint

### PostgreSQL enum

- Vantagens:
  - expressa fortemente o domínio;
  - validação nativa;
  - boa clareza semântica.
- Desvantagens:
  - evolução mais rígida;
  - rollback e alteração futura mais custosos;
  - maior fricção para expansão de valores.

### Check constraint textual

- Vantagens:
  - mais flexível;
  - mais simples para evoluir com Alembic;
  - rollback mais previsível;
  - menor acoplamento ao tipo do banco.
- Desvantagens:
  - semântica menos forte que enum nativo;
  - precisa de disciplina para não virar texto solto.

### Recomendação oficial

- **Check constraint textual** para `tipo_vinculo`.

### Justificativa

- O projeto já usa vários enums no banco, mas a convergência atual precisa priorizar flexibilidade, simplicidade de rollback e baixo risco de migração.
- O conjunto de valores é estável o suficiente para ser controlado por constraint sem perder a semântica de domínio.

---

## 5. Escopo seguro da futura migration

### Recomendação documental

A futura migration real deve conter:

1. Tabela `propriedade_imovel`
2. Constraints da tabela
3. Índices da tabela
4. RLS físico da tabela
5. Comentários de schema e colunas

### O que não deve entrar nessa migration

- Políticas RLS de tabelas legadas existentes.
- Migração de dados históricos.
- Depreciação dos campos legados.
- Ajustes em APIs.
- Ajustes em frontend.
- Remediação do legado fundiário duplicado.

### Racional

- O menor pacote seguro é aquele que cria a entidade oficial com sua proteção física básica.
- Tudo o que for retrocompatibilidade, saneamento legado ou migração de dados deve ser separado.

---

## 6. Plano de desbloqueio

### Antes da migration real

- Resolver a duplicidade de revisão `b1c2d3e4f5a6`.
- Reduzir o grafo para uma base de heads controlável.
- Confirmar a estratégia documental de RLS físico para a nova tabela.
- Manter o escopo da migration restrito à nova entidade.

### Pode ficar para fase posterior

- Policies físicas para tabelas legadas.
- Migração de dados fundiários históricos.
- Depreciação dos campos duplicados.
- Refatoração de backend e frontend.

### Bloqueante

- Múltiplos heads sem decisão de merge.
- Revisão duplicada não saneada.
- RLS físico não definido para a nova entidade.
- Escopo excessivo tentando incluir legado na mesma migration.

### Recomendável

- Usar check constraint para `tipo_vinculo`.
- Aplicar RLS físico apenas à nova tabela nesta primeira migration.
- Separar saneamento do legado em roadmap posterior.

### Sequência que reduz risco

1. Saneamento do grafo Alembic.
2. Merge migration, se necessária.
3. Confirmação do escopo mínimo da futura migration.
4. Criação da migration real da `propriedade_imovel`.
5. Endurecimento posterior do legado.

---

## 7. Respostas objetivas

### 1. O grafo Alembic permite criar a migration real agora?

- **Não.**

### 2. Existe revision duplicada? Qual o impacto?

- **Sim.**
- Impacto: ambiguidade no grafo, risco de leitura errada do revision map e fragilidade para futuras dependências.

### 3. É necessária merge migration antes?

- **Sim, recomendada.**

### 4. Qual estratégia de RLS físico deve ser adotada?

- **Estratégia B**:
  - RLS físico em `propriedade_imovel`;
  - plano separado para tabelas existentes.

### 5. Enum PostgreSQL ou check constraint?

- **Check constraint textual**.

### 6. Qual escopo seguro da futura migration?

- Apenas `propriedade_imovel` com constraints, índices, RLS físico e comentários.

### 7. Pode avançar para Fase 2 técnica?

- **Não ainda.**
- Só após sanear a duplicidade de revisão, decidir o merge do grafo e formalizar o escopo mínimo da migration real.

---

## 8. Conclusão

- O grafo do Alembic está funcional para leitura documental, mas ainda não está saudável o suficiente para receber a migration real da convergência sem saneamento adicional.
- A estratégia segura é reduzir o risco: resolver a duplicidade de revisão, evitar novos heads paralelos, usar check constraint para `tipo_vinculo` e limitar a futura migration à nova tabela com seu RLS físico.

