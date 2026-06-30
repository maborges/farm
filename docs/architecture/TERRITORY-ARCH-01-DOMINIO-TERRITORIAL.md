# TERRITORY-ARCH-01 — Domínio Territorial e Operacional do AgroSaaS

## 1. Resumo executivo

Conclusão objetiva: o AgroSaaS já possui uma arquitetura territorial e operacional canônica parcialmente consolidada, mas ela ainda não é a única arquitetura em execução na codebase.

O desenho que emerge do código é:

```text
Tenant
  ↓
UnidadeProdutiva
  ↓
AreaRural (árvore espacial canônica)
  ├── AREA_RURAL
  │   └── GLEBA
  │       ├── TALHAO
  │       │   └── AREA_OPERACIONAL
  │       │       ├── PIQUETE
  │       │       ├── ZONA_MANEJO
  │       │       └── SUBTALHAO
  │       └── AREA_AMBIENTAL
  │           ├── APP
  │           └── RESERVA_LEGAL
  └── INFRAESTRUTURA
      ├── SEDE
      ├── ARMAZEM
      ├── CURRAL
      └── OUTROS
```

Em paralelo, o código já definiu uma separação patrimonial/fundiária:

```text
Propriedade
  ↔ ExploracaoRural ↔ UnidadeProdutiva

Propriedade
  ↔ PropriedadeImovel ↔ ImovelRural
```

E, para agricultura:

```text
Safra
  ↓
Cultivo
  ↓
CultivoArea
  ↓
ProductionUnit
```

O problema é que ainda coexistem sobreposições relevantes:

- `UnidadeProdutiva` continua armazenando campos fundiários legados (`codigo_car`, `nirf`, `ccir`, `sigef_codigo`, `numero_matricula`).
- `AreaRural` já é a árvore espacial canônica, mas `pecuaria.models.Piquete` ainda existe como entidade paralela.
- `AreaOperacional` existe no código como `TipoArea.AREA_OPERACIONAL`, mas também aparece em alguns fluxos e telas como apelido conceitual.
- `Propriedade` e `AreaRural` ainda carregam parte de responsabilidades de suporte documental/patrimonial.
- Frontend e PWA ainda usam linguagem híbrida (`fazenda`, `unidade_produtiva`, `talhao`, `piquete`, `area operacional`) em diferentes níveis.

Classificação final: **Modelo C**.

Existe uma arquitetura territorial canônica clara para orientar novos desenvolvimentos, mas ainda há sobreposições suficientes para exigir consolidação antes da v1.0.

## 2. Inventário territorial

| Conceito | Model/Tabela | Owner | Função | É canônico? | Consumidores | Risco |
| --- | --- | --- | --- | ---: | --- | --- |
| Tenant | `tenants` | Core SaaS | Fronteira de isolamento/RLS | Sim | Todos os módulos | Baixo |
| UnidadeProdutiva | `core.models.unidade_produtiva.UnidadeProdutiva` / `unidades_produtivas` | Core | Unidade operacional mínima do tenant | Sim | Agricultura, pecuária, estoque, frota, Campo, imóveis | Alto por carregar legado fundiário |
| Propriedade | `core.cadastros.propriedades.propriedade_models.Propriedade` / `cadastros_propriedades` | Core Propriedades | Entidade patrimonial/organizacional/econômica | Sim | Exploração rural, visão territorial, vínculo com imóvel | Médio |
| ImovelRural | `imoveis.models.imovel.ImovelRural` / `imoveis_rurais` | Imóveis Rurais | Entidade legal/fundiária/documental | Sim | Visão fundiária, vínculo canônico, validações legais | Médio |
| PropriedadeImovel | `core.cadastros.propriedade_imovel.models.PropriedadeImovel` / `propriedade_imovel` | Core Territorial | Ponte N:N canônica entre Propriedade e ImovelRural | Sim | Visão territorial/fundiária, auto-vínculo EXEC-37/39 | Baixo |
| AreaRural | `core.cadastros.propriedades.models.AreaRural` / `cadastros_areas_rurais` | Core Propriedades | Árvore espacial canônica | Sim | Agricultura, pecuária, infraestrutura, Campo, rastreabilidade | Crítico |
| AreaOperacional | `TipoArea.AREA_OPERACIONAL` dentro de `AreaRural` | Core Propriedades | Subdivisão operacional de talhão | Sim, como tipo | Árvore de áreas, telas de piquete, pecuária | Médio |
| Talhao | `AreaRural.tipo = TALHAO` | Core Propriedades / Agrícola | Referência agrícola operacional | Sim | Safra, CultivoArea, Campo, operações, relatórios | Baixo |
| Piquete | `AreaRural.tipo = PIQUETE` e legado `pec_piquetes` | Pecuária | Referência pecuária operacional | Parcial | LoteAnimal, manejo, tela de piquetes, sync pecuária | Crítico por duplicidade |
| Infraestrutura | `Infraestrutura` vinculada a `AreaRural` + `AreaRural.tipo = INFRAESTRUTURA/SEDE/ARMAZEM/CURRAL` | Core Propriedades | Benfeitorias e estrutura física operacional | Parcial | Cadastro de infraestrutura, visão territorial | Médio por sobreposição entre nó e subrecurso |
| CultivoArea | `agricola.cultivos.models.CultivoArea` / `cultivo_areas` | Agrícola | Vínculo cultivo × área | Sim | Safra, Cultivo, ProductionUnit | Baixo |
| ProductionUnit | `agricola.production_units.models.ProductionUnit` / `production_units` | Agrícola | Unidade agrícola de safra/cultivo/área | Sim | DRE, rentabilidade, benchmark, prioridades, operações | Baixo |
| LoteAnimal | `pecuaria.animal.models.LoteAnimal` / `pec_lotes` | Pecuária | Agrupamento operacional de animais por unidade/área | Sim | Manejos, indicadores, sync Campo | Médio |
| Depósito | `operacional.models.estoque.Deposito` / `estoque_depositos` | Operacional Estoque | Estrutura física logística por unidade produtiva | Sim | Estoque, requisições, custos | Baixo |
| Equipamento | `core.cadastros.equipamentos.models.Equipamento` / `cadastros_equipamentos` | Core Equipamentos / Frota | Ativo operacional do tenant, com alocação por unidade | Sim | Frota, abastecimento, apontamentos, manutenção | Médio por fallback legado em `unidade_produtiva_id` |

## 3. Entidades canônicas

### 3.1 UnidadeProdutiva

Função definida pelo código: **unidade operacional mínima da plataforma**.

Evidência:

- `services/api/core/models/unidade_produtiva.py` define `UnidadeProdutiva` em `unidades_produtivas`.
- `services/api/core/routers/unidades_produtivas.py` cria a unidade e dispara `AreaRuralService.criar_estrutura_base()`.
- `services/api/core/operational_context.py` usa `unidade_produtiva_id` como contexto operacional transversal.
- `services/api/campo/service.py` e `apps/campo/src/lib/db.ts` ainda expõem o mesmo conceito também como `fazenda`.

Decisão:

- `UnidadeProdutiva` **não é imóvel legal nem entidade fiscal**.
- `UnidadeProdutiva` **é o contexto operacional, de autorização e de agrupamento espacial/logístico**.
- A plataforma ainda usa “fazenda” como alias de UX/compatibilidade para `UnidadeProdutiva`.

### 3.2 Propriedade

Função definida pelo código: **camada patrimonial/organizacional/econômica que se relaciona tanto com UnidadeProdutiva quanto com ImovelRural**.

Evidência:

- `Propriedade` vive em `cadastros_propriedades`.
- `ExploracaoRural` liga `Propriedade` a `UnidadeProdutiva`.
- `PropriedadeImovel` liga `Propriedade` a `ImovelRural`.

Decisão:

- `Propriedade` **não é sinônimo técnico de fazenda/unidade operacional**.
- `Propriedade` **é a entidade de domínio que representa a exploração/patrimônio/organização**.

### 3.3 ImovelRural

Função definida pelo código: **camada legal/fundiária/documental**.

Evidência:

- `imoveis.models.imovel.ImovelRural` concentra `nirf`, `car_numero`, `ccir_numero`, `sigef_codigo`, matrícula, cartório e documentos legais.
- `ImovelService` implementa validações fundiárias e cadastrais.

Decisão:

- `ImovelRural` **não é unidade produtiva**.
- `ImovelRural` **é a referência jurídica e documental do território**.

### 3.4 PropriedadeImovel

Função definida pelo código: **ponte N:N canônica entre Propriedade e ImovelRural**.

Evidência:

- `core/cadastros/propriedade_imovel/models.py`
- migration `add_propriedade_imovel.py`
- testes `test_territorial_compatibility.py`, `test_territorial_anticorruption.py`

Decisão:

- `PropriedadeImovel` **representa o vínculo jurídico/operacional entre os domínios**, com vigência, tipo de vínculo, percentual e área vinculada.
- Não deve virar repositório documental nem entidade operacional.

## 4. Entidades patrimoniais/fundiárias

Arquitetura patrimonial/fundiária confirmada pela codebase:

```text
Propriedade
  ↓
ExploracaoRural
  ↓
UnidadeProdutiva

Propriedade
  ↔ PropriedadeImovel
  ↔ ImovelRural
```

Pontos importantes:

- `ExploracaoRural` resolve “qual propriedade explora qual unidade produtiva”.
- `PropriedadeImovel` resolve “qual propriedade se vincula a qual imóvel rural”.
- `UnidadeProdutivaService` ainda auto-sincroniza vínculos fundiários e aplica overlay de leitura a partir de `ImovelRural`.

Risco:

- `UnidadeProdutiva` ainda é usada como entrada de dados fundiários e como ponto de auto-criação de `ImovelRural`, o que preserva compatibilidade, mas mistura camadas.

## 5. Entidades operacionais

### 5.1 AreaRural

Função definida pelo código: **árvore territorial/operacional canônica**.

Evidência:

- `TipoArea` define a taxonomia.
- `FILHOS_PERMITIDOS` define a hierarquia válida.
- `AreaRuralService` valida tipo pai/filho e cria a estrutura base da unidade.

Decisão:

- `AreaRural` é a **camada genérica e canônica** para representar território, subdivisão operacional, áreas ambientais e infraestrutura.

### 5.2 Talhão

Função definida pelo código: **tipo de área, não entidade própria nova**.

Evidência:

- `Talhão` aparece como `AreaRural.tipo == "TALHAO"`.
- `AgricolaTalhaoService` consulta `AreaRural` filtrando `tipo="TALHAO"`.
- migrations `step1_migrate_talhoes_to_areas_rurais.py` e `6f813e2a6f13_safra_talhoes_nn.py` confirmam a migração para `AreaRural`.

Decisão:

- **Talhão é tipo de `AreaRural`**.

### 5.3 Piquete

Função definida pelo código: **deveria ser tipo de área canônico, mas ainda convive com entidade pecuária legada**.

Evidência:

- `TipoArea.PIQUETE` existe em `AreaRural`.
- `LoteAnimal.area_id` comenta explicitamente “piquete ou pastagem atual (cadastros_areas_rurais)”.
- `LoteBovinoService` valida `AreaRural.tipo == PIQUETE`.
- `test_lote_service_area_rural.py` garante que `pec_piquetes` não precisa mais ser usado.
- Porém `pecuaria.models.Piquete` e `PiqueteService` ainda existem.

Decisão:

- **Piquete canônico = `AreaRural.tipo = PIQUETE`**.
- `pec_piquetes` é compatibilidade legada paralela.

### 5.4 AreaOperacional

Função definida pelo código: **tipo de `AreaRural`, não entidade separada**.

Evidência:

- `TipoArea.AREA_OPERACIONAL` em `core/cadastros/propriedades/models.py`.
- Frontend usa o termo como resumo/label (`AreaOperacionalResumo`), mas não existe model separado com esse nome.

Decisão:

- `AreaOperacional` **existe como camada canônica, mas como tipo dentro de `AreaRural`**.
- Não é uma tabela/autonomia própria.

### 5.5 Infraestrutura

Função encontrada:

- nó de árvore espacial (`AreaRural.tipo = INFRAESTRUTURA`, `SEDE`, `ARMAZEM`, `CURRAL`, `OUTROS`);
- subrecurso estruturado `Infraestrutura` vinculado a `AreaRural`.

Decisão:

- A camada espacial canônica é a árvore `AreaRural`.
- O subrecurso `Infraestrutura` complementa metadados físicos de uma área.

Risco:

- existe sobreposição entre “infraestrutura como nó/tipo de área” e “infraestrutura como entidade filha com atributos específicos”.

## 6. Agricultura

Arquitetura agrícola real:

```text
UnidadeProdutiva
  ↓
AreaRural (Talhão)
  ↓
Safra
  ↓
Cultivo
  ↓
CultivoArea
  ↓
ProductionUnit
  ↓
Operações / Caderno / DRE / Rentabilidade
```

Evidência:

- `SafraTalhao` ainda existe como compatibilidade N:N.
- `CultivoArea` é a fonte de verdade para a ocupação área × cultivo.
- `ProductionUnit` é first-class e nasce do par `(cultivo, área)`.
- `ProductionUnitService` resolve e até cria `CultivoArea` quando necessário.

Decisão:

- A agricultura oficial deve usar:
  - `UnidadeProdutiva` como contexto operacional macro;
  - `AreaRural.TALHAO` como recorte espacial agrícola;
  - `CultivoArea` como ocupação do cultivo na área;
  - `ProductionUnit` como unidade operacional/econômica da safra.

## 7. Pecuária

Arquitetura pecuária real:

```text
UnidadeProdutiva
  ↓
AreaRural (PIQUETE)
  ↓
LoteAnimal
  ↓
Animal
  ↓
Pesagem / Sanidade / Reprodução
```

Evidência:

- `LoteAnimal.area_id` aponta para `cadastros_areas_rurais`.
- `LoteBovinoService` só aceita `AreaRural.tipo == PIQUETE`.
- Sync e dashboards de pecuária operam por `unidade_produtiva_id` e `lote_id`.

Problema:

- `pec_piquetes` ainda existe como entidade própria.
- A UI de piquetes já está parcialmente migrada para criar `AreaRural` tipo `PIQUETE`, mas o backend legado de `piquetes` continua exposto.

Decisão:

- A pecuária oficial deve usar `AreaRural.PIQUETE`.
- `pec_piquetes` deve permanecer apenas como compatibilidade.

## 8. Campo PWA

Estrutura usada pelo Campo PWA:

- autorização e escopo por `fazenda_ids` do dispositivo;
- sync traz `fazendas`, `talhoes`, `lotes`, `animais`, `tarefas_pendentes`;
- tarefa armazena `unidade_produtiva_id`, `area_rural_id` e `lote_id`;
- no IndexedDB local a UI ainda usa `fazenda_id` e `talhao_id`.

Decisão:

- O PWA usa:
  - `UnidadeProdutiva` como contexto principal;
  - `AreaRural.TALHAO` para agricultura;
  - `LoteAnimal` para pecuária;
  - ainda não opera nativamente com `AreaRural.PIQUETE` como entidade cacheada de primeiro nível.

## 9. Estoque / Máquinas

Fluxos confirmados:

- `Deposito.unidade_produtiva_id` ancora logística por unidade.
- `Equipamento` tem `unidade_produtiva_id` legado e `EquipamentoAlocacao` como camada mais robusta.
- `core/cadastros/equipamentos/alocacao_service.py` trata a alocação como fonte preferencial e o campo direto como fallback legado.

Decisão:

- Estoque e frota pertencem ao contexto de `UnidadeProdutiva`, não ao de `Propriedade` nem `ImovelRural`.

## 10. Fluxos reais

### 10.1 Implantação

```text
Tenant
  ↓
UnidadeProdutiva
  ↓
AreaRuralService.criar_estrutura_base()
  ↓
Nós raiz AREA_RURAL + INFRAESTRUTURA
```

### 10.2 Patrimonial / Fundiário

```text
Propriedade
  ↓
ExploracaoRural
  ↓
UnidadeProdutiva

Propriedade
  ↔ PropriedadeImovel
  ↔ ImovelRural
  ↔ Cartório / Matrículas / CAR / CCIR / NIRF / SIGEF
```

### 10.3 Agricultura

```text
UnidadeProdutiva
  ↓
AreaRural.TALHAO
  ↓
Safra
  ↓
Cultivo
  ↓
CultivoArea
  ↓
ProductionUnit
```

### 10.4 Pecuária

```text
UnidadeProdutiva
  ↓
AreaRural.PIQUETE
  ↓
LoteAnimal
  ↓
Animal
```

### 10.5 Campo PWA

```text
Dispositivo
  ↓
fazenda_ids autorizadas
  ↓
talhoes / lotes / animais / tarefas
  ↓
execução offline
  ↓
sync
```

### 10.6 Estoque / Máquinas

```text
UnidadeProdutiva
  ↓
Depósito / Equipamento
  ↓
Operações
```

## 11. Duplicidades

Duplicidades relevantes identificadas:

### 11.1 UnidadeProdutiva × Propriedade × ImovelRural

- `UnidadeProdutiva` é operacional, mas ainda armazena dados fundiários.
- `Propriedade` é econômica/patrimonial/organizacional.
- `ImovelRural` é jurídico/documental.

Risco:

- uso incorreto de `UnidadeProdutiva` como se fosse a própria entidade fundiária.

### 11.2 AreaRural × Talhão

- A codebase já migrou `Talhão` para `AreaRural.tipo = TALHAO`.
- Ainda existe linguagem legada e migrations de convergência.

Risco:

- baixo; arquitetura aqui já está quase consolidada.

### 11.3 AreaRural × Piquete

- canônico: `AreaRural.tipo = PIQUETE`;
- legado: `pec_piquetes`.

Risco:

- crítico; ainda há dois caminhos estruturais possíveis.

### 11.4 AreaRural × AreaOperacional

- `AreaOperacional` não é entidade separada;
- alguns contratos/UI tratam como conceito de tela.

Risco:

- médio; pode induzir nova modelagem paralela se não houver documentação clara.

### 11.5 CultivoArea × ProductionUnit

- `CultivoArea` = ocupação cultivo × área;
- `ProductionUnit` = unidade operacional/econômica de safra.

Risco:

- médio; são entidades distintas, mas próximas semanticamente.

## 12. Compatibilidades legadas

Compatibilidades relevantes encontradas:

- alias `Fazenda = UnidadeProdutiva` em `core/models/unidade_produtiva.py`;
- PWA e vários fluxos ainda usam `fazenda_id` como nome de payload/local state;
- `UnidadeProdutiva` ainda guarda `codigo_car`, `nirf`, `ccir`, `sigef_codigo`, `numero_matricula`;
- `pec_piquetes` continua existindo;
- `SafraTalhao` permanece como compatibilidade enquanto `CultivoArea` e `ProductionUnit` assumem o fluxo novo;
- migrations ainda referenciam tabelas/nomes antigos (`fazendas`, `areas_rurais`, `talhoes`).

## 13. Arquitetura alvo oficial

Arquitetura oficial recomendada pela codebase:

```text
Tenant
  ↓
UnidadeProdutiva
  ↓
AreaRural
  ├── AREA_RURAL
  │   └── GLEBA
  │       ├── TALHAO
  │       │   └── AREA_OPERACIONAL
  │       │       ├── PIQUETE
  │       │       ├── ZONA_MANEJO
  │       │       └── SUBTALHAO
  │       └── AREA_AMBIENTAL
  │           ├── APP
  │           └── RESERVA_LEGAL
  └── INFRAESTRUTURA
      ├── SEDE
      ├── ARMAZEM
      ├── CURRAL
      └── OUTROS
```

Em paralelo:

```text
Propriedade
  ↔ ExploracaoRural ↔ UnidadeProdutiva

Propriedade
  ↔ PropriedadeImovel ↔ ImovelRural
```

E, para agricultura:

```text
Safra
  ↓
Cultivo
  ↓
CultivoArea
  ↓
ProductionUnit
```

Regras oficiais:

- `UnidadeProdutiva` = contexto operacional.
- `Propriedade` = camada patrimonial/organizacional.
- `ImovelRural` = camada fundiária/legal.
- `PropriedadeImovel` = ponte N:N obrigatória.
- `AreaRural` = árvore espacial canônica.
- `Talhão` = tipo de `AreaRural`.
- `Piquete` = tipo de `AreaRural`.
- `AreaOperacional` = tipo de `AreaRural`.
- `ProductionUnit` = unidade agrícola de safra/cultivo/área.

## 14. Decisão

**Modelo C**.

Motivo:

- a arquitetura canônica já existe e é suficientemente clara;
- porém ainda existem sobreposições estruturais relevantes demais para afirmar consistência total antes da v1.0.

## 15. O que entra na v1.0

Deve entrar na v1.0 como regra oficial:

- `UnidadeProdutiva` como unidade operacional mínima.
- `AreaRural` como árvore territorial/operacional oficial.
- `Talhão` e `Piquete` como tipos de `AreaRural`.
- `Propriedade` ↔ `ExploracaoRural` ↔ `UnidadeProdutiva`.
- `Propriedade` ↔ `PropriedadeImovel` ↔ `ImovelRural`.
- `CultivoArea` + `ProductionUnit` como base oficial da agricultura.
- `LoteAnimal.area_id` apontando para `AreaRural.PIQUETE`.

## 16. O que pode ficar para v1.1

- eliminação ou encapsulamento definitivo de `pec_piquetes`;
- remoção dos campos fundiários legados de `UnidadeProdutiva`;
- unificação total da linguagem `fazenda` → `unidade_produtiva` em payloads e UI;
- revisão da sobreposição `AreaRural` + subrecurso `Infraestrutura`;
- limpeza de migrations e aliases históricos (`talhoes`, `areas_rurais`, `fazendas`).

## 17. Plano recomendado

1. Congelar a criação de novas entidades territoriais fora de `AreaRural`.
2. Definir `AreaRural.PIQUETE` como único caminho aceito para novos fluxos pecuários.
3. Tratar `pec_piquetes` e campos fundiários de `UnidadeProdutiva` como compatibilidade explícita.
4. Exigir `ProductionUnit` para novos fluxos analíticos/agronômicos por safra.
5. Não permitir novos vínculos diretos `Propriedade ↔ ImovelRural` sem `PropriedadeImovel`.

