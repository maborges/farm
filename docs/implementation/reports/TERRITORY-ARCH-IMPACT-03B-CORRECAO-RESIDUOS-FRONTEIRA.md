# TERRITORY-ARCH-IMPACT-03B — Correção dos Resíduos de Fronteira Territorial

## 1. Resumo executivo

Os resíduos R-01 e R-03 foram corrigidos sem alterar o modelo territorial oficial. A via fundiária `cadastros_areas_matriculas`, ligada a `AreaRural`, foi classificada como `LEGADO_SEM_USO` e removida com migration reversível e proteção contra perda de dados. As análises de solo passaram a resolver o nome pelo ID oficial de `UnidadeProdutiva`, e não por `Propriedade.id`.

R-02 não recebeu sincronismo novo. Sua semântica foi formalizada e o fluxo bidirecional permanece proibido. R-04 foi apenas documentado, sem migration.

## 2. Classificação do R-01

```text
LEGADO_SEM_USO
```

Evidências:

- zero registros no PostgreSQL real;
- zero dados fundiários preenchidos;
- zero consumidores Web/Campo;
- zero integrações, workers ou relatórios de runtime;
- nenhuma dependência física externa;
- nenhuma ligação com `ImovelRural`;
- CRUD backend constituía a única superfície ativa.

## 3. Consumidores e dados

O backend expunha GET, POST, PATCH e DELETE em `/cadastros/areas-rurais/{area_id}/matriculas`. Não foi encontrada chamada para essas rotas fora do próprio módulo. A documentação histórica do piloto foi classificada como referência desatualizada, pois não corresponde a uso ou dado físico atual.

Contagem física:

```text
total=0
ativos=0
com_matricula=0
com_car=0
com_nirf=0
com_ccir=0
com_itr=0
tenants=0
orfaos=0
```

## 4. Divergências e migração

Não existem divergências nem dados exclusivos a migrar. Não houve backfill.

A migration `20260717_remove_area_matriculas_legacy`:

- verifica se a tabela contém linhas;
- aborta com exceção explícita se houver qualquer registro;
- remove a tabela somente quando vazia;
- recria as 16 colunas, FK e índice no downgrade.

Essa proteção impede perda silenciosa em ambientes não auditados.

## 5. Correção aplicada no backend

Foram removidos:

- `MatriculaCreate`, `MatriculaUpdate`, `MatriculaResponse` do contexto de `AreaRural`;
- `MatriculaImovel` e `AreaRural.matriculas`;
- `MatriculaService`;
- endpoints `/{area_id}/matriculas`;
- registro do model na metadata ativa.

Permanecem oficiais e inalterados:

```text
ImovelRural
MatriculaImovelRural
DocumentoLegal
PropriedadeImovel
```

## 6. Correção do frontend R-03

A tela precisa exibir o nome da Unidade Produtiva que contém o Talhão. `AreaRural/Talhao.unidade_produtiva_id` referencia diretamente `UnidadeProdutiva`, portanto não há necessidade de resolver `Propriedade` nem passar por `ExploracaoRural` para esse rótulo.

Correção:

```text
antes: GET /cadastros/propriedades + Propriedade.id == talhao.unidade_produtiva_id
depois: GET /unidades-produtivas/ + UnidadeProdutiva.id == talhao.unidade_produtiva_id
```

Os dois componentes afetados usam agora `formatTalhaoLabel`, com fallback apenas para o nome do Talhão quando a associação não está disponível. Não há fallback por nome nem cast `as unknown as`.

## 7. Guardrails e testes

Guardrails adicionados:

- schemas de escrita de UP, Propriedade, AreaRural e Piquete não aceitam campos fundiários;
- `MatriculaCreate`, `MatriculaUpdate` e `MatriculaImovel` não podem reaparecer no módulo territorial;
- `AreaRural` não pode possuir relação `matriculas`;
- as rotas legadas não podem reaparecer;
- os componentes auditados não podem consultar `Propriedade[]` para resolver `unidade_produtiva_id`;
- o service de Imóvel não pode depender de `UnidadeProdutivaService` nem criar sincronismo inverso.

Testes comportamentais do frontend cobrem duas UPs e associação ausente. O empty state retorna o nome do Talhão sem crash.

## 8. Matriz semântica R-02

| Campo | UP representa | ImovelRural representa | Mesmo significado? | Deve sincronizar? | Fonte de verdade | Decisão |
|---|---|---|---|---|---|---|
| municipio | endereço/localização operacional | município oficial do imóvel | Não necessariamente | Não automaticamente | cada entidade em seu contexto | MANTER_SEPARADO |
| uf | UF operacional/postal | UF oficial fundiária | Não necessariamente | Não automaticamente | cada entidade em seu contexto | MANTER_SEPARADO |
| código IBGE | município operacional | município oficial do imóvel | Só quando as localizações coincidem | Não automaticamente | cada entidade em seu contexto | MANTER_SEPARADO |
| area_total_ha | extensão operacional gerida | área fundiária oficial | Não | Não | UP operacional; Imóvel fundiário | MANTER_SEPARADO |
| area_app_ha | referência operacional histórica | APP fundiária/ambiental oficial | Parcial | Não | ImovelRural/estrutura ambiental oficial | AUDITAR_CONSUMIDORES |
| area_rl_ha | referência operacional histórica | Reserva Legal oficial | Parcial | Não | ImovelRural/estrutura ambiental oficial | AUDITAR_CONSUMIDORES |
| geometria | agregado/perímetro operacional | perímetro oficial do imóvel | Não | Não copiar | cada entidade em seu contexto | MANTER_SEPARADO |
| coordenadas_sede | ponto operacional da sede | não aplicável | Não | Não | UnidadeProdutiva | MANTER_SEPARADO |
| latitude/longitude | não aplicável | referência/centroide fundiário | Não | Não | ImovelRural | MANTER_SEPARADO |

O método `_sincronizar_imovel_principal_com_unidade` permanece como compatibilidade unidirecional e lazy preexistente. Ele não foi ampliado nesta fase. A próxima ação recomendada é auditar seus consumidores e restringi-lo a defaults explícitos de criação, eliminando a atualização automática de campos semanticamente distintos.

## 9. R-04 — Código IBGE

Não foi criada migration. A nomenclatura futura recomendada para contratos novos é `codigo_municipio_ibge`. Uma alteração física deverá usar expand-contract, com backfill e retirada posterior do nome antigo. A uniformização do nome não implica equivalência entre localização operacional e fundiária.

## 10. Arquivos alterados

Backend:

- `core/cadastros/propriedades/schemas.py`
- `core/cadastros/propriedades/models.py`
- `core/cadastros/propriedades/service.py`
- `core/cadastros/propriedades/router.py`
- `core/models/__init__.py`
- `migrations/env.py`
- `migrations/versions/20260717_remove_area_matriculas_legacy.py`
- testes de governança e 03B

Frontend:

- `analises-client.tsx`
- `nova-analise-modal.tsx`
- `territory-labels.ts`
- teste Playwright de vínculo territorial

## 11. Validação PostgreSQL

O ciclo foi executado no PostgreSQL real:

```text
upgrade head: tabela removida
verificação: table_exists=false
downgrade -1: tabela recriada
verificação: table_exists=true, rows=0, columns=16
upgrade head: tabela removida novamente
```

Nenhum UPDATE ou backfill foi executado.

## 12. Riscos residuais e próximo passo

- O sincronismo lazy UP → Imóvel ainda pode confundir campos de semânticas diferentes; deve ser tratado em fase própria após auditoria de consumidores.
- APP/RL na UP ainda possuem consumidores de interface e exigem inventário antes de depreciação.
- Documentos históricos que recomendam `MatriculaImovel` ligado a AreaRural devem ser marcados como superados em uma revisão documental ampla.

Próximo passo recomendado: fase específica para retirar o sincronismo automático e converter campos compartilhados em entradas independentes ou projeções de leitura, sem sincronismo bidirecional.

## 13. Checklist final

```text
R-01 foi classificado? SIM
Há dados reais na estrutura legada? NÃO
Há dados exclusivos fora de ImovelRural? NÃO
Houve backfill? NÃO
Conflitos foram sobrescritos? NÃO
Nova gravação fundiária por AreaRural foi bloqueada? SIM
MatriculaCreate ainda aceita NIRF/CAR/CCIR/ITR? NÃO
R-03 foi corrigido? SIM
IDs de Propriedade e UP continuam sendo comparados? NÃO
Guardrail foi criado? SIM
Sincronismo bidirecional foi criado? NÃO
Semântica dos campos UP × Imóvel foi documentada? SIM
Migration foi necessária? SIM
PostgreSQL real foi validado? SIM
Piloto foi preservado? SIM
```

## 14. Veredicto

```text
GO
```

Os resíduos comprovados foram corrigidos sem criar nova fonte fundiária, sem backfill e sem sincronismo bidirecional.
