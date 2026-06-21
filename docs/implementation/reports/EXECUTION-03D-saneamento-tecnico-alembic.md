# EXECUTION-03D — Saneamento Técnico do Grafo Alembic

## Objetivo
Executar o saneamento mínimo do grafo Alembic antes da futura migration de `propriedade_imovel`, eliminando a duplicidade de revision e convergindo os heads legítimos com uma merge migration vazia.

## Escopo executado
- correção da revision duplicada em uma migration existente relacionada ao conflito
- criação de merge migration vazia para convergir os heads
- validação do grafo por introspecção e por `alembic heads`
- sem alteração de schema de negócio
- sem criação da migration de `propriedade_imovel`

## 1. Arquivos alterados

### Alterados
- [`services/api/migrations/versions/b1c2d3e4f5a7_add_imoveis_avaliacoes.py`](/opt/lampp/htdocs/farm/services/api/migrations/versions/b1c2d3e4f5a7_add_imoveis_avaliacoes.py)
- [`services/api/migrations/versions/merge_heads_before_propriedade_imovel.py`](/opt/lampp/htdocs/farm/services/api/migrations/versions/merge_heads_before_propriedade_imovel.py)

### Movido / substituído
- [`services/api/migrations/versions/b1c2d3e4f5a6_add_imoveis_avaliacoes.py`](/opt/lampp/htdocs/farm/services/api/migrations/versions/b1c2d3e4f5a6_add_imoveis_avaliacoes.py)

### Não alterado
- [`services/api/migrations/versions/b1c2d3e4f5a6_add_plano_canais_comercializacao.py`](/opt/lampp/htdocs/farm/services/api/migrations/versions/b1c2d3e4f5a6_add_plano_canais_comercializacao.py)

## 2. Revision antiga e nova

### Revision antiga
- `b1c2d3e4f5a6` no arquivo de `imoveis_avaliacoes`

### Revision nova
- `b1c2d3e4f5a7` no arquivo de `imoveis_avaliacoes`

### Observação
- O `revision = "b1c2d3e4f5a6"` foi preservado no arquivo de plano de canais de comercialização.
- Nenhum `down_revision` downstream precisou ser alterado.

## 3. Heads antes e depois

### Antes
- `b1c2d3e4f5a6`
- `c3d4e5f6a7b8`
- `ff59b3b71a2d`

### Depois da correção e da merge migration
- `merge_heads_before_propriedade_imovel`

### Evidência
- `alembic heads` passou a retornar apenas:
  - `merge_heads_before_propriedade_imovel (head)`

## 4. Merge migration

### Foi criada?
Sim.

### Nome
- [`services/api/migrations/versions/merge_heads_before_propriedade_imovel.py`](/opt/lampp/htdocs/farm/services/api/migrations/versions/merge_heads_before_propriedade_imovel.py)

### Conteúdo
- migration vazia
- sem operações de schema
- `down_revision` com:
  - `b1c2d3e4f5a7`
  - `c3d4e5f6a7b8`
  - `ff59b3b71a2d`

### Finalidade
Convergir os três heads legítimos em um único head estável antes da futura migration de `propriedade_imovel`.

## 5. Resultado de `alembic heads`

Resultado obtido:
```text
merge_heads_before_propriedade_imovel (head)
```

## 6. Resultado de `alembic branches`

Resultado:
- o comando não concluiu dentro do timeout de execução no ambiente
- a validação estrutural foi complementada por introspecção direta do grafo com `ScriptDirectory`

### Observação técnica
Após a merge migration, o grafo ficou com um único head. Isso reduz a necessidade prática de branches remanescentes no topo.

## 7. Resultado de `alembic history --verbose`

Resultado:
- o comando não concluiu dentro do timeout de execução no ambiente
- a inspeção do grafo por `ScriptDirectory` confirmou que a merge migration virou o único head e que a cadeia de revisões está conectada sem duplicidade de revision

### Evidência complementar
- `ScriptDirectory.get_heads()` retornou:
  - `['merge_heads_before_propriedade_imovel']`
- a merge aponta para:
  - `('b1c2d3e4f5a7', 'c3d4e5f6a7b8', 'ff59b3b71a2d')`

## 8. Situação do grafo

### Antes
- revision duplicada `b1c2d3e4f5a6`
- três heads legítimos/derivados na árvore
- comandos de inspeção inconsistentes por overlap

### Depois
- nenhuma revision duplicada
- um único head no topo
- merge migration vazia criada para consolidar os ramos

## 9. Validação final

### Confirmado
- não existe revision duplicada no diretório após o saneamento
- `alembic heads` retorna apenas um head
- a migration de `imoveis_avaliacoes` recebeu revision novo e único
- a migration de plano de canais permaneceu intacta
- a merge migration é vazia e documentada

### Ponto ainda não executado
- não foi criada a migration de `propriedade_imovel`

## 10. Conclusão

O grafo Alembic foi saneado no nível mínimo necessário:
- a duplicidade de revision foi removida
- os heads legítimos foram convergidos com merge migration vazia
- o topo do grafo está controlado

## Respostas objetivas

### Saneamento aprovado?
Sim.

### Pode avançar para Fase 2 técnica da `propriedade_imovel`?
Sim, com o grafo já saneado e a merge migration consolidando os heads.

### É necessário algum ajuste adicional antes?
Não para o grafo. O próximo passo é criar a migration real de `propriedade_imovel` a partir do head consolidado.
