# FITO-RISK-01 — Especificação e validação das regras fitossanitárias

**Escopo:** análise do motor existente, dos contratos e das referências técnicas. Nenhum código foi alterado; nenhum seed ou banco foi executado/acessado.
**Decisão:** o recurso não deve ser homologado como estimativa probabilística até corrigir a semântica de dados ausentes, delimitar o que é “risco climático” e validar um modelo por cultura/região com dados independentes.

## 1. Diagnóstico do motor atual

### 1.1 Dados climáticos que chegam ao cálculo

`RegistroClima` (`services/api/agricola/climatico/models.py:11-42`) guarda, por tenant/unidade e dia, precipitação em mm, temperaturas mínima/máxima/média em °C, umidade relativa em %, evapotranspiração em mm e vento em km/h. `PrevisaoClima` guarda temperatura mínima/máxima, chuva em mm e probabilidade de chuva, mas não é usada pelo método fitossanitário.

`ClimaService.get_analise_avancada()` seleciona registros históricos em ordem cronológica, dentro da janela pedida (`service.py:139-159`). `_calcular_risco_doencas()` usa as culturas de safras ativas e os registros históricos (`:261-300`). O motor reduz os últimos sete registros a médias simples de `temp_media_c`, `temp_max_c`, `temp_min_c`, `umidade_rel_pct` e `precipitacao_mm` (`:329-366`). Evapotranspiração e vento não entram no cálculo fitossanitário. A precipitação também é média de observações diárias, não duração de chuva ou molhamento foliar.

Não há no contrato horário, sensor de molhamento foliar, duração de molhamento, radiação/insolação, cobertura do dossel, carga de frutos, estádio fenológico, inóculo ou confirmação de doença. Médias de estação/unidade são aproximações do microclima no dossel e não equivalem às condições na superfície foliar.

### 1.2 Contrato JSON aceito hoje

O único exemplo comentado no modelo (`models.py:89-90`) é:

```json
{
  "condicoes": [
    {"variavel": "temp_media_c", "operador": ">=", "valor": 20, "peso": 0.6},
    {"variavel": "umidade_rel_pct", "operador": ">=", "valor": 85, "peso": 0.4}
  ],
  "nivel_medio_pct": 35,
  "nivel_alto_pct": 60,
  "nivel_critico_pct": 80
}
```

O exemplo acima apenas ilustra o formato; seus números **não são uma regra aprovada**.

O avaliador (`service.py:368-430`) aceita, em cada condição:

| Campo | Comportamento implementado |
|---|---|
| `variavel` | Chave literal do dicionário de estatísticas. Na prática: `temp_media_c`, `temp_min_c`, `temp_max_c`, `umidade_rel_pct`, `precipitacao_mm`. |
| `operador` | `>=`, `<=`, `>`, `<` ou `between`; `between` usa `min` e `max`. |
| `valor` | Limite numérico para os quatro operadores simples. |
| `peso` | Peso positivo; padrão 1. Condições sem peso positivo ou sem variável no dicionário são ignoradas pelo avaliador. |
| `nivel_medio_pct`, `nivel_alto_pct`, `nivel_critico_pct` | Limites de classe; se omitidos, o código usa 35, 60 e 80, respectivamente. |

A pontuação é `(soma dos pesos das condições satisfeitas / soma dos pesos considerados) × 100`, arredondada para inteiro. O nome do campo de saída é `probabilidade_pct`, mas o valor não é uma probabilidade calibrada: é a fração ponderada de condições verdadeiras. A classificação é `critico`, `alto`, `medio` ou `baixo` (`service.py:414-430`). Se não houver condição utilizável, a pontuação é zero.

O schema Pydantic aceita `regras_risco: dict` sem validar os nomes de variáveis, operadores, limites, unidades, pesos ou limiares (`schemas.py:121-142`). Também não há campos de proveniência tipados na tabela (`models.py:71-93`). Portanto, o banco aceita JSON arbitrário e o contrato é mais permissivo do que o avaliador.

### 1.3 Problema de dados ausentes

O teste unitário atual prova que `_avaliar_modelo()` ignora uma variável se ela não existir no dicionário (`tests/unit/agricola/test_clima_inteligencia_rules.py:7-10`). Porém, no caminho real, `_calcular_stats_climaticas()` cria todas as cinco chaves e atribui **0.0** quando todos os valores daquele campo estão ausentes (`service.py:361-366`). Assim, `temp_min_c` ausente pode ser interpretada como 0°C e `precipitacao_mm` ausente como 0 mm, disparando condições como `<=`, `<` ou `between`. O teste isolado do avaliador não cobre esse caso integrado.

É um bloqueador para homologação: ausência de medição precisa continuar sendo ausência (ou fazer a regra retornar “dados insuficientes”), nunca ser convertida em evidência de frio/seca.

### 1.4 Seleção e precedência de modelos

O motor primeiro busca modelos daquele tenant para as culturas ativas; depois busca modelos globais somente para culturas que não tenham **nenhum** modelo do tenant (`service.py:302-324`). Isso faz um modelo do tenant para uma única doença da cultura excluir todas as regras globais das outras doenças da mesma cultura. Já `ModeloFitossanitarioService.get_all()` combina os dois escopos e resolve precedência pela chave exata `(cultura, doenca)` (`service.py:446-486`). Há, portanto, divergência entre a listagem e o cálculo.

A intenção explícita dos comentários/serviço é priorizar tenant sobre global. A precedência apropriada ao dado exposto é por combinação `(cultura, doença)`, preservando outros modelos globais da cultura sem modelo local. Isso necessita ajuste mínimo e teste antes de seed; nenhum teste foi executado nesta análise.

### 1.5 Comportamento sem modelo

Se não encontra modelo aplicável, `_calcular_risco_doencas()` retorna `[]` (`service.py:326-327`). A resposta coloca essa lista em `agricultura.risco_doencas`, mas `agricultura` inteira só existe quando há registros climáticos (`service.py:231-240`). Portanto, a API distingue indiretamente “sem registros” (`agricultura: null`) de “com registros, sem modelos” (`risco_doencas: []`), mas não informa o motivo nem separa “não calculado” de “baixo risco”. A resposta não deve permitir que lista vazia seja lida como risco baixo.

## 2. Culturas e doenças candidatas

O seed de culturas contém Café (`services/api/scripts/initial_load/seed_culturas.py:357`), além de Soja, Milho e Trigo. O seed de `monitoramento_catalogo` tem doenças de Soja, Trigo e Milho, mas não há doença do café nesse catálogo (`services/api/scripts/initial_load/seed_catalogo_monitoramento.py:30-40`). `ModeloFitossanitario.doenca` é texto livre, então esse catálogo não é uma FK/dependência do motor.

| Cultura / doença candidata | Agente causal | Evidência ambiental encontrada | O que também importa / limitações | Aderência ao motor atual | Estado para homologação |
|---|---|---|---|---|---|
| Café — ferrugem do cafeeiro | *Hemileia vastatrix* | Literatura consultada associa favorabilidade a temperatura amena e umidade/molhamento. Manual de boas práticas da Embrapa para MG indica faixa de 20–24°C junto com umidade/ambiente sombreado; estudo de conilon encontrou 21,6–23,6°C com molhamento foliar e UR >80% como condição mais favorável. | Inóculo, cultivar/espécie, carga de frutos, época/safra, dossel e duração do molhamento são relevantes. A faixa observada em conilon não deve ser generalizada automaticamente a arábica ou outras regiões. | **ADAPTAÇÃO MÍNIMA** para um indicador de favorabilidade condicionado a dados; **NÃO SUPORTADA** como reprodução do modelo de aviso validado sem janela, calibração e validação. Sem molhamento foliar no contrato. | **PENDENTE DE VALIDAÇÃO AGRONÔMICA.** Melhor candidata para piloto; não aprovada para score/probabilidade de produção. |
| Café — cercosporiose / mancha-do-olho-pardo | *Cercospora coffeicola* | Fontes descrevem correlação com nutrição e clima; baixa temperatura, alta umidade, excesso de insolação, desequilíbrio nutricional e estresse hídrico podem favorecer a doença. | Nutrição, água, insolação, estágio/frutificação e desenvolvimento radicular são fatores importantes; vários não existem nos dados climáticos do motor. As fontes consultadas não estabelecem um limiar quantitativo universal para a regra deste produto. | **NÃO SUPORTADA** com o conjunto atual para estimar risco específico. O JSON poderia exprimir alguns predicados climáticos, mas não as condições determinantes completas nem o efeito de interação. | **NÃO APROVADA.** Exige validação agronômica e dados complementares; nenhuma regra numérica proposta. |
| Soja — ferrugem asiática | *Phakopsora pachyrhizi* | Embrapa descreve infecção dependente de água livre, mínimo de 6 horas, com maior infecção entre 10–12 horas, e 18–26,5°C favoráveis. | Molhamento foliar e presença/dispersão de inóculo são críticos; período de molhamento não é equivalente a UR média ou precipitação diária. Epidemiologia varia com cultivar, ciclo, região e época. | **NÃO SUPORTADA** para a regra epidemiológica completa; temperatura está disponível, molhamento não. Poderia virar indicador de favorabilidade após adicionar a variável e validar. | **PENDENTE DE VALIDAÇÃO AGRONÔMICA.** Não aprovada para seed atual. |

### Fontes técnicas consultadas e limites da evidência

1. **Embrapa, Boas práticas agrícolas aplicadas à lavoura cafeeira para o estado de Minas Gerais**, seção Ferrugem do cafeeiro, aponta condições favoráveis e faixa de 20–24°C, além de época do ciclo, carga pendente, nutrição e manejo. É orientação regional e descritiva; não define score probabilístico universal. [Documento Embrapa, seção do cafeeiro](https://www.infoteca.cnptia.embrapa.br/infoteca/bitstream/doc/1148365/1/Sistemas-de-Producao-1-Cafe.pdf#page=59).
2. **Capucho et al., Climate favourability to leaf rust in Conilon coffee**, ensaio de temperatura/molhamento em *C. canephora*: 21,6–23,6°C, molhamento e UR >80% foram favoráveis. É evidência experimental para conilon e condições estudadas, não valida transferência direta para café arábica/regiões diferentes. [Repositório UFV](https://locus.ufv.br/items/a65da3a1-2883-4760-bdc1-1a37cd0950b7) / [DOI](https://doi.org/10.1007/s13313-012-0187-6).
3. **Hinnah et al., Weather-based coffee leaf rust apparent infection rate modeling**, estudo baseado em 88 site-seasons; escolheu temperatura mínima e umidade relativa para modelos de taxa aparente e reporta desempenho dependente de condição/carga/espaçamento. Evidencia que é possível construir alerta com dados meteorológicos, mas requer modelo empírico calibrado e janela temporal própria. [PubMed](https://pubmed.ncbi.nlm.nih.gov/30051219/) e estudo relacionado que explicita médias de 30–60 dias e índice cumulativo de risco [Plant Disease](https://apsjournals.apsnet.org/doi/10.1094/PDIS-01-19-0207-SR). A equação completa não foi validada nesta especificação; não deve ser reconstruída a partir apenas do resumo.
4. **Embrapa, Sistemas de Produção 1 — Café**, descreve cercosporiose, agente *C. coffeicola*, e a associação a clima, nutrição, baixa temperatura, alta umidade, insolação e estresse hídrico, sem oferecer limiar universal para implementar no JSON atual. [Documento Embrapa, seção Cercóspora](https://www.infoteca.cnptia.embrapa.br/infoteca/bitstream/doc/1148365/1/Sistemas-de-Producao-1-Cafe.pdf#page=61).
5. **Embrapa, Ferrugem-asiática (*Phakopsora pachyrhizi*)**, descreve necessidade de água livre por pelo menos 6 h, ótimo de 10–12 h de molhamento, e faixa de temperatura favorável 18–26,5°C. É uma condição de infecção, não probabilidade da epidemia nem diagnóstico. [Documento Embrapa, capítulo da doença](https://www.infoteca.cnptia.embrapa.br/infoteca/bitstream/doc/1158639/1/Doc-256-2023OL-1.pdf#page=16).
6. **UFV, Infectário — doenças do cafeeiro**, confirma *Cercospora coffeicola* e destaca maior incidência em solos de baixa fertilidade e necessidade de manejo nutricional/irrigação; a página é referência de diagnóstico e não fornece limiar climático para este motor. [Departamento de Fitopatologia da UFV](https://www.infectario.ufv.br/doencas-do-cafeeiro/).

As fontes dão fundamentos para escolher variáveis e condições de favorabilidade, mas não fornecem automaticamente parâmetros válidos para o score atual. As faixas publicadas divergem segundo espécie de café, região, escala temporal, microclima e variável usada. Os valores acima são transcrição contextual de fonte, não parâmetros liberados para o seed.

## 3. Compatibilidade e proposta inicial

### Regras aprováveis nesta etapa

**Nenhuma regra de risco probabilístico está aprovada para carga.** Há evidência técnica para priorizar ferrugem do café como primeiro caso de estudo, e existe evidência publicada de condições favoráveis quantificadas. Porém, o motor atual não mede duração de molhamento, usa média dos últimos sete dias, não inclui o contexto epidemiológico e transforma proporção de predicados em `probabilidade_pct`. Isso não é equivalente a nenhum dos modelos citados.

Uma versão limitada intitulada **“favorabilidade climática observada”** poderia ser especificada para homologação somente depois de responsável agronômico escolher a fonte/modelo aplicável a espécie e região e validar a janela e a comparação com ocorrências de campo. O resultado não deve ser chamado de probabilidade de doença, alerta de tratamento ou diagnóstico. Mesmo este indicador não deve usar valor zero para substituir observação ausente.

### Pendências priorizadas

1. **Café — ferrugem:** melhor candidata inicial. Obter a publicação/equação completa do sistema de aviso, confirmar licença/condições de uso, espécie/região-alvo, janela temporal e variáveis; definir fonte de dados de molhamento ou assumir formalmente modelo meteorológico alternativo; validação por agrônomo e em conjunto independente de ocorrências locais.
2. **Café — cercosporiose:** não aprovar regras no motor atual. Seria necessário considerar ao menos nutrição/água/insolação e separar fases/órgãos suscetíveis; as fontes levantadas não sustentam thresholds numéricos universais.
3. **Soja — ferrugem asiática:** caso técnico relevante e já citado no catálogo de monitoramento, mas não homologável com os dados atuais sem molhamento foliar e validação temporal/regional. A duração mínima de molhamento publicada não deve ser substituída por UR média.

Não incluir outras combinações no seed desta fase. O seed do catálogo de monitoramento ter uma doença cadastrada não demonstra que exista regra validada para o motor climático.

## 4. Especificação para futuro seed global

Esta seção define requisitos, não cria o arquivo nem os registros.

### 4.1 Forma e semântica

O formato mínimo atualmente consumido pelo serviço seria:

```json
{
  "condicoes": [
    {"variavel": "temp_min_c", "operador": "between", "min": "VALOR_FONTE", "max": "VALOR_FONTE", "peso": "PESO_VALIDADO"}
  ],
  "nivel_medio_pct": "LIMIAR_VALIDADO",
  "nivel_alto_pct": "LIMIAR_VALIDADO",
  "nivel_critico_pct": "LIMIAR_VALIDADO",
  "metadados": {
    "tipo_resultado": "favorabilidade_climatica",
    "fonte_id": "REFERENCIA_BIBLIOGRAFICA",
    "fonte_url": "URL_DA_FONTE",
    "versao_regra": "VERSAO_REVISTA",
    "validado_em": "AAAA-MM-DD",
    "escopo": "CULTIVAR_REGIAO_E_JANELA",
    "responsavel_validacao": "IDENTIFICACAO_REGISTRADA"
  }
}
```

Os valores em maiúsculas são marcadores, não valores a carregar. O avaliador ignora `metadados` hoje; a presença deles serve para rastreabilidade e não muda o cálculo. Os thresholds de classificação e pesos também precisam de base específica, não devem herdar cegamente os defaults 35/60/80.

O motor deve antes validar variáveis/unidades/operadores e preservar ausências. Só calcular quando todas as entradas essenciais para a regra estiverem disponíveis; caso contrário retornar estado explícito de dados insuficientes. Se a meta for probabilidade, será necessário modelo calibrado e validado, não o atual score de condições.

### 4.2 Identidade, escopo, idempotência e atualização

- **Escopo:** `tenant_id = NULL` para regra publicada pela plataforma; não gravar regra global com `tenant_id` do cliente. `is_global` é computado a partir do escopo no serviço, apesar de existir coluna no modelo.
- **Chave lógica:** `(tenant_id IS NULL, cultura, doenca normalizada)`. Para globais, usar chave de negócio `(cultura, doenca)`; a migration `20260823_clima_inteligencia_integrity.py` prevê índice único parcial para globais e outro para tenant.
- **Idempotência:** inserir somente quando a chave global não existir. Não substituir regras existentes durante execução automática. O serviço de CRUD global permite atualização e exclusão, portanto o seed não deve fazer upsert destrutivo.
- **Alteração de regra:** mudança de limiar/fonte deve ser revisão explícita com aprovação agronômica e registro de versão. O schema só guarda a regra atual; metadata no JSON preserva a referência e versão publicada, mas **não fornece histórico imutável**. Se for necessário auditar versões passadas dentro do banco, isso exige decisão/estrutura específica posterior (fora desta etapa).
- **Transação e ORM:** registrar os modelos pelo mecanismo oficial antes de consultar, gravar todos os registros do lote numa transação e fazer rollback integral se qualquer validação/inserção falhar. Respeitar RLS e o processo de conexão usado para carga global.
- **Conteúdo:** não inserir uma regra para combinação sem fonte identificável, escopo de aplicabilidade, revisão técnica, variáveis existentes e critério de avaliação testável.

### 4.3 Validações automáticas possíveis

- `cultura` e `doenca` não vazias e correspondentes à nomenclatura canônica de cultura/agente;
- `condicoes` não vazia; variável em allowlist; operador conhecido; `valor` ou par `min/max` presente e numérico; intervalo `min <= max`;
- pesos finitos e positivos, limites percentuais dentro de `[0,100]` e ordenados (`medio <= alto <= critico`);
- unidade e escala da variável coerentes com o registro: temperatura °C, umidade %, precipitação mm;
- metadados com referência/URL, versão e escopo de validade;
- rejeitar regra que usa variável ausente ou estatística sem quantidade mínima/recência de observações definida;
- verificar unicidade da chave global e garantir que o seed não atualize/delete modelo do tenant.

## 5. Critérios de homologação

| Critério | Comprovação exigida |
|---|---|
| Cálculo conhecido | Casos de entrada/saída baseados na publicação/modelo selecionado; incluir fronteiras (`<`, `<=`, `between`) e confirmar unidade. |
| Regra não é diagnóstico | Interface/API nomeia o resultado como favorabilidade/risco climático estimado; não afirma doença presente nem recomenda defensivo automaticamente. Mensagens mostram que confirmação exige observação de campo. |
| Dados insuficientes | Ausência de cada variável obrigatória, histórico abaixo do mínimo, dados antigos e valores inválidos não podem ser convertidos em zero nem gerar baixo/alto risco falso; resposta indica “dados insuficientes/não calculado”. |
| Isolamento de tenant | Consulta usa tenant corrente e, quando autorizado, regra global; nenhum modelo de tenant A aparece para B. Testar sob RLS e pelo serviço. |
| Precedência | Para mesma `(cultura, doença)`, regra do tenant prevalece sobre global; regra local de outra doença não elimina regra global restante da cultura. Resultado coerente entre endpoint de listagem e cálculo. |
| Seed idempotente | Duas execuções em banco de teste resultam no mesmo conjunto/IDs e não duplicam chave global. |
| Não sobrescrita | Seed repetido não atualiza regras globais já revisadas e jamais altera regras tenant; conflito de conteúdo deve ser reportado e tratado deliberadamente. |
| Acurácia/validação externa | Avaliação retrospectiva e prospectiva com observações de doença e métricas adequadas (sensibilidade, especificidade, falsos negativos, calibração quando houver probabilidade), em regiões/espécies-alvo. Definir limites de aceitação com responsável agronômico antes do teste. |
| API e interface sem modelo | Distinguir “sem modelo”, “sem cultura ativa”, “sem clima suficiente” e “resultado sem risco detectado”; lista vazia não pode ser interpretada como `baixo`. |
| Sem regressão | Testes para relatório climático, demais riscos e resposta `agricultura=null` versus `risco_doencas=[]`, sem mudar análises alheias. |

Testes unitários existentes em `services/api/tests/unit/agricola/test_clima_inteligencia_rules.py` cobrem operador/modelo em parte, peso zero, classificação e balanço hídrico. Eles não cobrem o caminho integrado que transforma variáveis integralmente ausentes em `0.0`, o escopo/preferência por tenant, o motor com banco isolado ou a semântica da API sem modelo. Não foram executados nesta especificação.

## 6. Veredicto

**NO-GO para carregar regras ou homologar como probabilidade/diagnóstico nesta etapa.** O motor atual tem uma pontuação heurística com nome de probabilidade, trata ausência real como zero no cálculo integrado e contém discrepância de precedência entre serviço de listagem e cálculo. Além disso, as doenças candidatas prioritárias dependem de variáveis/contexto ausentes.

**Pode avançar como candidata de especificação, ainda sem carga:** ferrugem do cafeeiro (*Hemileia vastatrix*), pela relevância e literatura encontrada sobre temperatura e umidade/molhamento. A fonte deve ser selecionada para espécie/região e regra, em conjunto com a validação agronômica; os parâmetros aqui citados não estão aprovados para produção.

**Dependem de validação adicional e não devem entrar em seed agora:** ferrugem do café como regra operacional/score, cercosporiose do café e ferrugem asiática da soja. Para cercosporiose e soja, além da validação, há incompatibilidade relevante com dados/variáveis atuais. Nenhuma outra combinação foi aprovada.

Para mudar o veredicto, o mínimo anterior a qualquer carga é: (1) corrigir ausência de dados e precedência tenant/global; (2) definir semântica explícita de “favorabilidade” versus probabilidade; (3) escolher regra/publicação aplicável e obter aprovação agronômica; (4) validar com casos e dados independentes; (5) só então implementar seed global idempotente e seus testes. Nada disso foi implementado nesta tarefa.
