# EXECUTION-03C — Plano Técnico para Saneamento do Grafo Alembic

## Objetivo
Definir o estado atual do grafo Alembic e a sequência segura para saneá-lo antes da criação da migration real de `propriedade_imovel`.

## Base de análise
Leituras e comandos executados:
- `alembic heads`
- `alembic branches`
- `alembic history --verbose`
- `rg -n "revision =|down_revision =" services/api/migrations/versions`
- inspeção direta das migrations duplicadas e dos heads relacionados

## 1. Estado atual do grafo

O grafo Alembic está inconsistente e não está pronto para receber uma nova migration de convergência.

### Evidências
- `alembic heads` retorna:
  - `ff59b3b71a2d (head)`
  - `c3d4e5f6a7b8 (head)`
  - `b1c2d3e4f5a6`
- O Alembic emite aviso:
  - `Revision b1c2d3e4f5a6 is present more than once`
- `alembic branches` e `alembic history --verbose` falham com:
  - `Requested revision ff59b3b71a2d overlaps with other requested revisions b1c2d3e4f5a6`

### Conclusão
Existe conflito estrutural no grafo. O problema não é apenas visual: o Alembic não consegue resolver a árvore de revisões com segurança porque a mesma revisão foi declarada em dois arquivos diferentes.

## 2. Revisão duplicada

### Arquivos envolvidos
- [`services/api/migrations/versions/b1c2d3e4f5a6_add_imoveis_avaliacoes.py`](/opt/lampp/htdocs/farm/services/api/migrations/versions/b1c2d3e4f5a6_add_imoveis_avaliacoes.py)
- [`services/api/migrations/versions/b1c2d3e4f5a6_add_plano_canais_comercializacao.py`](/opt/lampp/htdocs/farm/services/api/migrations/versions/b1c2d3e4f5a6_add_plano_canais_comercializacao.py)

### O que cada uma faz
- `b1c2d3e4f5a6_add_imoveis_avaliacoes.py`
  - cria `imoveis_avaliacoes`
  - revisa `43cdf769d080`
  - define `revision = "b1c2d3e4f5a6"`
- `b1c2d3e4f5a6_add_plano_canais_comercializacao.py`
  - altera `planos_assinatura`
  - revisa `a0a58168bc5b`
  - também define `revision = "b1c2d3e4f5a6"`

### Impacto
O mesmo revision id está representando duas linhas diferentes do grafo. Isso produz ambiguidade para:
- cálculo de heads
- cálculo de branches
- expansão de history
- resolução de dependências downstream

### Correção recomendada
Manter o revision id em `b1c2d3e4f5a6_add_plano_canais_comercializacao.py` e atribuir um novo revision id exclusivo a `b1c2d3e4f5a6_add_imoveis_avaliacoes.py`.

### Justificativa técnica
- `add_plano_canais_comercializacao.py` é a revisão mais antiga dos dois arquivos e já serve de base para dependentes diretos, como `add_is_default_to_plano_assinatura.py`.
- Renomear a migration de `imoveis_avaliacoes` minimiza a chance de ruptura em ambientes onde o ramo de planos já foi consumido.
- O arquivo de `imoveis_avaliacoes` não apareceu com descendentes diretos no inventário atual, então é o melhor candidato para receber novo revision id.

### Dependências downstream que devem ser reavaliadas depois da correção
- [`services/api/migrations/versions/add_is_default_to_plano_assinatura.py`](/opt/lampp/htdocs/farm/services/api/migrations/versions/add_is_default_to_plano_assinatura.py)
- [`services/api/migrations/versions/c3d4e5f6a7b8_add_rh_seguranca.py`](/opt/lampp/htdocs/farm/services/api/migrations/versions/c3d4e5f6a7b8_add_rh_seguranca.py)

Observação:
- Com a correção recomendada, esses arquivos podem continuar apontando para `b1c2d3e4f5a6` sem alteração, porque o revision id ficará preservado na migration de planos.
- Se a estratégia escolhida fosse o contrário, seria necessário atualizar os `down_revision` afetados, o que aumenta o risco.

## 3. Merge migration

### Situação
Hoje o grafo aparenta ter:
- `ff59b3b71a2d` como head
- `c3d4e5f6a7b8` como head
- um head ambíguo em torno de `b1c2d3e4f5a6` por causa da duplicidade

### Avaliação
A merge migration é **provavelmente necessária**, mas **somente depois** da correção da duplicidade.

### Motivo
Enquanto o revision id está duplicado, qualquer merge migration seria construída sobre uma base incerta. Isso pode apenas mascarar o problema e piorar a manutenção futura.

### Condição correta
Após o saneamento do revision duplicado, reexecutar `alembic heads`:
- se ainda houver mais de um head legítimo, criar merge migration
- se sobrar um único head, não criar merge migration

### Diretriz segura
Não criar merge migration antes de corrigir o revision duplicado.

## 4. Estratégia mais segura

Comparação das opções:

- **A) corrigir revision duplicada manualmente e depois criar merge migration**
  - melhor opção
  - reduz ambiguidade
  - preserva rastreabilidade
  - permite validar o grafo em duas etapas

- **B) criar merge migration sem corrigir duplicidade**
  - arriscada
  - mantém o grafo inconsistente
  - não resolve o erro de overlap

- **C) não corrigir grafo e anexar `propriedade_imovel` a um head específico**
  - inaceitável para implementação segura
  - prende a nova migration em uma base errada
  - aumenta chance de novo head inválido

- **D) gerar uma migration de compatibilidade**
  - útil apenas em um segundo momento, se houver necessidade de acomodar ambientes antigos
  - não substitui a correção do grafo

### Recomendação
Adotar a estratégia **A**.

## 5. Sequência segura antes da migration de `propriedade_imovel`

1. Limpar o worktree ou criar branch dedicada para a convergência.
   - Objetivo: reduzir ruído e evitar mistura com alterações não relacionadas.
   - Critério de aceite: `git status` sem alterações inesperadas no escopo da convergência.

2. Corrigir a duplicidade de revision.
   - Objetivo: remover o conflito estrutural.
   - Comando provável: edição manual do arquivo candidato para novo revision id.
   - Critério de aceite: nenhum revision id repetido em `services/api/migrations/versions`.

3. Validar o grafo.
   - Objetivo: confirmar que `alembic heads`, `branches` e `history` passam sem overlap.
   - Comando provável: `alembic heads`, `alembic branches`, `alembic history --verbose`.
   - Critério de aceite: comandos retornam grafo coerente.

4. Criar merge migration apenas se ainda houver múltiplos heads legítimos.
   - Objetivo: convergir o grafo para um ponto único de base.
   - Critério de aceite: todos os heads convergem para um head final ou uma única linha principal.

5. Revalidar heads e branches.
   - Objetivo: garantir que a nova base está estável.
   - Critério de aceite: sem erro de overlap.

6. Somente então criar a migration real de `propriedade_imovel`.
   - Objetivo: evitar acoplamento com grafo instável.
   - Critério de aceite: migration ancorada em um head válido e auditado.

## 6. Respostas objetivas

### 6.1 Qual é o estado atual do grafo?
Está inconsistente. Existe revisão duplicada e os comandos de inspeção do Alembic falham por overlap de revisions.

### 6.2 Qual é a revisão duplicada e quais arquivos estão envolvidos?
O revision id duplicado é `b1c2d3e4f5a6`, nos arquivos:
- `b1c2d3e4f5a6_add_imoveis_avaliacoes.py`
- `b1c2d3e4f5a6_add_plano_canais_comercializacao.py`

### 6.3 Qual é a correção recomendada?
Manter `b1c2d3e4f5a6` em `add_plano_canais_comercializacao.py` e atribuir novo revision id a `add_imoveis_avaliacoes.py`.

### 6.4 É necessário merge migration?
Sim, possivelmente, mas apenas após corrigir a duplicidade e revalidar o grafo. Não é seguro decidir antes disso.

### 6.5 Qual é a sequência segura antes da migration `propriedade_imovel`?
Limpar branch/worktree, corrigir duplicidade, validar grafo, criar merge migration se ainda houver múltiplos heads, revalidar heads e só então criar a migration de `propriedade_imovel`.

### 6.6 Pode avançar para implementação técnica após este relatório?
Não. Este relatório desbloqueia o plano, mas a implementação técnica só deve começar depois do saneamento do grafo e da validação final do Alembic.

## Conclusão
O grafo Alembic ainda não está apto para receber a migration de `propriedade_imovel`. A prioridade é corrigir a duplicidade de `b1c2d3e4f5a6`, validar novamente os heads e só então avaliar merge migration e a ancoragem da nova migration.
