# FITO-RISK-03 — Validação científica da ferrugem do café arábica

**Data:** 2026-10-30  
**Escopo:** avaliação documental e de aderência dos dados disponíveis no repositório. Não foram implementadas regras, seeds ou alterações de código.

## 1. Decisão executiva

**Recomendação: alternativa C — adiar o cálculo fitossanitário operacional.** Hinnah et al. (2018) é o candidato quantitativo mais recente e parsimonioso entre as fontes analisadas, e um artigo subsequente reproduz sua equação para uma aplicação regional. Porém, o artigo original não está integralmente acessível na página pública consultada; o conjunto climático persistido pelo DeepFarms não contém as séries diárias necessárias; o motor atual agrega sete datas, em vez da janela de 30–60 dias; e não há validação local independente.

O boletim de Meira e Rodrigues (Embrapa, 2009) tem texto completo aberto e é diretamente sobre *Coffea arabica* em Varginha, MG. Sua árvore depende de atributos horários transformados em períodos de infecção/incubação e de carga de frutos. Portanto, também não é implementável com segurança no motor atual. Ele é uma referência útil para planejar coleta e validação em campo.

**Veredicto: NO-GO para implementar ou carregar a regra-piloto neste momento.** Há viabilidade para uma futura reprodução de modelo publicado, mas não aprovação agronômica nem dados atuais suficientes. Não se recomenda substituir o modelo por um indicador climático ad hoc apenas porque alguns campos semelhantes existem.

## 2. Modelos científicos avaliados

### A. Hinnah et al. (2018) — regressão meteorológica de taxa aparente de infecção

Artigo original: Fernando Dill Hinnah, Paulo Cesar Sentelhas, Carlos Alberto Alves Meira e Rodrigo Naves Paiva, “Weather-based coffee leaf rust apparent infection rate modeling”, *International Journal of Biometeorology*, 62, 1847–1860, DOI [10.1007/s00484-018-1587-2](https://doi.org/10.1007/s00484-018-1587-2). A página do editor fornece resumo e prévia, mas informa que o texto é conteúdo por assinatura; não foi possível verificar o texto integral do artigo nesta pesquisa. O resumo informa análise de 88 combinações local-safra, melhor ajuste Gompertz das curvas de progresso, seleção de temperatura mínima e umidade relativa, e melhor desempenho para lavouras de alta produção e espaçamento estreito, com 9,4% de falsos negativos no conjunto de meses avaliado. [Página do artigo e resumo](https://link.springer.com/article/10.1007/s00484-018-1587-2)

Um artigo subsequente de Hinnah et al. em *Plant Disease* (2020), disponível no repositório da USP, aplica e identifica explicitamente o modelo de 2018 para municípios produtores de arábica no Brasil. Nele, a equação reproduzida para a condição de alta carga e espaçamento estreito é:

```text
r_HN = -1.293 + 0.019 × Tmin_(30–60d) + 0.017 × RH_(30–60d)
```

`Tmin` e `RH` são as médias de temperatura mínima diária e umidade relativa média diária durante o período de 30 a 60 dias anterior à data estimada. O estudo de 2020 reporta correlação entre taxas observadas e estimadas `r = 0,516` (`p < 0,01`) e 73,83% de acertos na validação independente para um limite de taxa de infecção de 5%. O texto explicita que a taxa acumulada é um índice de avaliação de risco, não necessariamente a quantidade da doença. Esses resultados pertencem ao estudo/modelo e validação descritos na publicação, não são expectativa de desempenho para o DeepFarms. [Artigo completo no repositório da USP](https://repositorio.usp.br/directbitstream/4bfdb12d-f12f-40d9-981f-0b5f813d6974/3042186-Assessing%20Biogeography%20of%20Coffee%20Rust%20Risk%20in%20Brazil....pdf)

**Importante:** a equação acima foi transcrita da publicação completa de 2020, que atribui o modelo a Hinnah et al. (2018); não foi inferida do resumo. Ainda assim, sem o texto integral de 2018 não foi possível auditar todas as definições, seleção de janela, tratamento dos dados, coeficientes, validação e limitações da publicação original. Não é recomendável codificar a fórmula a partir apenas dessa reprodução secundária. O modelo prevê taxa aparente de infecção, não diretamente probabilidade de ocorrência ou favorabilidade percentual.

### B. Meira e Rodrigues / Embrapa (2009) — árvores de decisão

O boletim completo de 24 páginas está disponível em acesso aberto: [Árvores de decisão aplicadas na análise e no alerta da ferrugem do cafeeiro](https://www.infoteca.cnptia.embrapa.br/infoteca/bitstream/doc/662782/1/cnptiabp221.pdf). O estudo foi feito na fazenda experimental da Fundação Procafé, em Varginha, MG, com lavouras adultas de *Coffea arabica*, cultivares Catuaí e Mundo Novo, 6–20 anos, acompanhadas de outubro de 1998 a outubro de 2006. A incidência foi avaliada mensalmente; as condições de produção foram separadas por carga pendente de frutos alta/baixa e espaçamento adensado/largo. [Métodos e população do estudo](https://www.infoteca.cnptia.embrapa.br/infoteca/bitstream/doc/662782/1/cnptiabp221.pdf)

Os atributos meteorológicos vieram de estação próxima e de registros horários, processados em janelas de infecção e incubação. Incluíram temperatura durante períodos de umidade relativa `>=95%` (usada como proxy de molhamento), horas de umidade alta total/noturna, temperatura mínima/média/máxima, precipitação, médias/somas e variáveis da incubação. O conjunto também incluiu carga de frutos e espaçamento. A classificação foi baseada na mudança mensal da incidência, com classes de progresso da doença e, para alertas, taxa de progresso de pelo menos 5 pontos percentuais.

O texto completo descreve regras da árvore e métricas. Um caminho da árvore exploratória é `THUR95_PINF < 17 °C` e `TMAX_PI_PINF >= 25,95 °C` levando à classe de taxa `<=0`; para o alerta de alta carga, um dos caminhos reportados é `THUR95_PINF >= 16,5 °C`, `UR_PINF >= 78%` e `TMED_PI_PINF < 22,35 °C`, levando à classe positiva. Esses são exemplos de caminhos de modelos treinados naquela população, não thresholds transferíveis para as fazendas do DeepFarms. O modelo de alerta de alta carga teve acurácia estimada de `81,3 ± 4,8%`, sensibilidade `79,9 ± 6,9%` e especificidade `82,6 ± 4,3%`; para baixa carga, sensibilidade foi `46,3 ± 6,9%`, ilustrando desempenho inferior e desbalanceamento. A avaliação reportada usou validação cruzada estratificada de 10 partições. Os autores recomendam restringir o uso à região de coleta ou ambiente semelhante e realizar validação antes da adoção. [Resultados, variáveis e limitações no boletim](https://www.infoteca.cnptia.embrapa.br/infoteca/bitstream/doc/662782/1/cnptiabp221.pdf)

O artigo relacionado em *Tropical Plant Pathology* também descreve avaliações mensais, coleta de 100 folhas por talhão e estação automática com dados meteorológicos a cada 30 minutos. [Artigo SciELO](https://www.scielo.br/j/tpp/a/gwhNLwQB58hkwJSSWdJ7gbB/)

### Comparação resumida

| Aspecto | Hinnah et al. (2018) | Meira e Rodrigues / Embrapa (2009) |
|---|---|---|
| Café | Modelo reproduzido para municípios produtores de arábica no estudo subsequente; auditar composição exata do estudo original depende do texto integral | *C. arabica*, Catuaí e Mundo Novo |
| Região | Principal região produtora brasileira; estudo de aplicação de 2020 cobre municípios produtores em sete estados | Fazenda experimental em Varginha, MG; condições ambientais semelhantes são limite de extrapolação declarado |
| Desfecho | Taxa aparente de infecção / índice derivado | Classes da taxa mensal de progresso e classe binária de alerta |
| Janela | Média diária de Tmin e RH em 30–60 dias anteriores, conforme reprodução integral de 2020 | Períodos de infecção/incubação derivados de avaliações mensais; atributos meteorológicos construídos de dados horários |
| Campo/manejo | Condição de referência de alta carga e espaçamento estreito para equação reproduzida | Carga pendente explícita; árvores distintas por carga; inclui espaçamento como atributo candidato |
| Validação publicada | Resumo do original reporta 9,4% falsos negativos na condição melhor; estudo de 2020 reporta avaliação independente e 73,83% de acertos no limiar de 5% | 10-fold cross-validation; métricas detalhadas, com sensibilidade muito diferente por carga |
| Reprodução | Fórmula disponível em estudo posterior, mas artigo original integral não verificado; licença/termos para incorporar no produto não confirmados | Artigo integral aberto; autorização para incorporar a árvore/regra em software comercial não está especificada pela indicação “open access” |
| Aderência atual | Baixa: dados diários necessários não são efetivamente persistidos como médias diárias e janela atual é sete dias | Muito baixa: faltam dados horários/atributos de molhamento, janela e carga da lavoura |

## 3. Aderência aos dados do DeepFarms

### O que o código efetivamente oferece

`RegistroClima` (`services/api/agricola/climatico/models.py`) guarda uma linha por data/unidade/fonte, com `precipitacao_mm`, `temp_min_c`, `temp_max_c`, `temp_media_c`, `umidade_rel_pct`, evapotranspiração e vento. Isso é a estrutura do registro, não garantia de que cada variável seja populada.

Na integração OpenWeather, a sincronização de clima atual lê temperatura atual, umidade, precipitação de 1h/3h e vento e publica `ClimaSyncRealizado`. `ClimaEventSubscriber` persiste temperatura atual em `temp_media_c`, umidade e precipitação; não preenche temperatura mínima/máxima diária, nem armazena série horária histórica ou `raw_payload` em `RegistroClima`. O evento traz payload bruto, mas ele não é usado pelo subscriber para construir dados históricos diários.

A integração de previsão agrega dados de 3 em 3 horas em previsões futuras, incluindo períodos que carregam temperatura e umidade. Esses dados são armazenados em `PrevisaoClima.periodos`, por horizonte curto; não são observações históricas. O serviço de risco fitossanitário lê `RegistroClima` e reduz os sete dias mais recentes a médias; não usa períodos de previsão. A rota de histórico é somente leitura. O código consultado não fornece ingestão de observações horárias históricas para o motor.

O repositório contém campos de lavoura em `Safra`/`Cultivo`, inclusive cultivar e espaçamento, mas o cálculo fitossanitário atual seleciona apenas o nome da cultura ativa. Não há carga pendente de frutos integrada ao cálculo. Campos existentes em outro domínio não devem ser assumidos como dados observados/preenchidos sem auditoria das rotinas que os alimentam.

### Matriz de variáveis

| Variável científica | Hinnah 2018 / uso publicado | Meira–Rodrigues 2009 | Situação no DeepFarms |
|---|---|---|---|
| Temperatura mínima diária | Média em janela de 30–60 dias | Médias mínimas em períodos de infecção/incubação | **DISPONÍVEL NO MODELO DE DADOS, AUSENTE NO FLUXO ATUAL DE SINCRONIZAÇÃO**; previsão futura tem mínimas, mas não substitui histórico observado |
| Umidade relativa média diária | Média em janela de 30–60 dias | Média diária e horas `>=95%` | **AUSENTE COMO MÉDIA DIÁRIA CONFIÁVEL**; ingestão atual persiste uma leitura pontual diária. Não equivale automaticamente à média diária |
| Frequência horária de umidade `>=95%` | Não indicada na equação reproduzida | Proxy temporal de molhamento foliar | **AUSENTE** no histórico climático persistido |
| Duração de molhamento foliar | Não aparece explicitamente na equação reproduzida | Estimada por horas em UR elevada, processadas em períodos contínuos e noturnos | **AUSENTE; EXIGE SENSOR OU MÉTODO DE ESTIMATIVA VALIDADO**. UR diária isolada não é equivalente a molhamento |
| Temperatura durante molhamento / horas úmidas | Não aparece na equação reproduzida | THUR95 e horas noturnas são atributos centrais | **AUSENTE** como série horária histórica pareada |
| Temperaturas médias/máximas na incubação | Não aparecem na equação reproduzida | Atributos do período de incubação | **PARCIALMENTE DISPONÍVEL NO SCHEMA, AUSENTE NO HISTÓRICO INGESTADO** e sem janela de incubação derivada |
| Precipitação acumulada/frequência de dias chuvosos | Não aparece na equação reproduzida | Usada com outras variáveis, incluindo precipitação `>=1 mm` | **PARCIALMENTE DISPONÍVEL** como dado atual/diário; integração do snapshot salva precipitação de janela 1h/3h, não um total observado diário consolidado confiável |
| Carga pendente de frutos | A equação divulgada em 2020 é para alta carga e espaçamento estreito | Necessária para escolher modelo de alerta (alta/baixa) | **EXIGE MEDIÇÃO DE CAMPO**; não há variável consumida pelo motor |
| Cultivar / resistência | Relevante à aplicabilidade e extrapolação; equação não identifica cultivar no termo | Estudo usou Catuaí e Mundo Novo | **PARCIAL**: cadastro Safra permite cultivar, mas motor não consulta nem valida esse dado |
| Espaçamento | Condição estreita na versão da equação publicada em 2020 | Considerado nos exemplos, mas não apareceu como nó na árvore exploratória; alertas separados por carga | **PARCIAL** em Safra, não considerado no motor; definição de “estreito” precisa seguir protocolo da fonte, não novo valor inventado |
| Incidência de ferrugem no campo | Usada para ajustar/validar taxas do modelo original | Avaliações mensais da incidência foram o alvo | **AUSENTE do fluxo do motor**; não há observação fitopatológica vinculada para validação |
| Janela temporal | 30–60 dias antes da data de estimativa | Horária → diária → períodos de infecção/incubação, alvo mensal | **INCOMPATÍVEL**: cálculo atual usa sete datas distintas; integração atual não mantém séries históricas intradiárias |

## 4. Alternativa recomendada

| Alternativa | Avaliação |
|---|---|
| **A. Reproduzir modelo publicado** | Melhor para rastreabilidade científica. Hinnah tem expressão concisa, mas exige médias diárias de Tmin/RH por janela correta, condição de produção declarada e texto integral/licença verificados. A árvore Embrapa é aberta e mais contextualizada a arábica, porém requer variáveis horárias, carga e processamento temporal; transplantar regras seria inadequado. |
| **B. Criar indicador limitado de favorabilidade** | Não recomendado agora. O contrato suporta score heurístico, mas faltam séries confiáveis e validação que justifique quais condições e classificação usar. Um score simples de médias atuais com limiares improvisados não reproduziria os estudos e poderia induzir falsa segurança. |
| **C. Adiar cálculo** | **Recomendado.** Manter o estado explícito de dados/modelo insuficientes do FITO-RISK-02 até selecionar um modelo reproduzível, instrumentar os dados necessários e executar validação local independente. |

## 5. Ficha técnica da regra-piloto (especificação; parâmetros não aprovados)

| Campo | Definição / situação |
|---|---|
| Cultura | Café arábica — *Coffea arabica* |
| Doença | Ferrugem do cafeeiro |
| Agente | *Hemileia vastatrix* |
| Modelo candidato | Hinnah et al. (2018), regressão de taxa aparente de infecção, em condição de alta carga de frutos e espaçamento estreito, conforme equação reproduzida no estudo de 2020 |
| Região de validade demonstrada | Estudo-base informado como 88 site-seasons na principal região brasileira produtora; a publicação de aplicação de 2020 contempla municípios produtores de arábica em PR, SP, RJ, ES, MG, GO e BA. Validade para outras regiões ou fazendas não demonstrada automaticamente |
| Variáveis requeridas | Média de temperatura mínima diária e média diária de umidade relativa, calculadas com dados observados e completos na janela de 30–60 dias anterior à data estimada |
| Frequência | Dados diários; o protocolo da média de umidade precisa ser reproduzido exatamente da fonte (estudo de aplicação cita média de três medições diárias às 9h, 15h e 21h) |
| Equação | `r_HN = -1.293 + 0.019 × Tmin_(30–60d) + 0.017 × RH_(30–60d)`, transcrita de artigo completo de 2020 que cita o modelo de 2018. **Pendente de auditoria no artigo original e confirmação de unidades/definições e condições de reprodução.** |
| Semântica de saída | Taxa aparente de infecção conforme definição/modelo original; não chamar de probabilidade, diagnóstico, incidência observada, severidade, nem converter para `% de favorabilidade` sem validação |
| Dados insuficientes | Pendente definir com a fonte/profissional protocolo de completude, lacunas, fontes misturadas, recência e bloqueio. Não calcular se janela, escala diária ou contexto aplicável estiverem incompletos |
| Dependências agronômicas | Alta carga pendente e espaçamento estreito na equação reproduzida; cultivar, local, estação e epidemiologia devem ser registrados para avaliar transferência. Confirmação de ferrugem em campo continua distinta do resultado climático |
| Limitações | Modelo empírico regional; artigo original integral não verificado nesta pesquisa; coeficientes não calibrados para dados/provedores/talhões DeepFarms; não inclui confirmação de inóculo nem observação da doença no campo |
| Uso em produto | Não aprovado até acesso/revisão da publicação integral, confirmação dos termos para implementação e avaliação por agrônomo/fitopatologista habilitado |

Não se recomenda colocar esta ficha em `regras_risco` ainda. Os parâmetros acima servem apenas para especificar o que precisa ser verificado, não como autorização para seed.

## 6. Pendências científicas e agronômicas

1. Obter e arquivar acesso legítimo ao texto integral de Hinnah et al. (2018); conferir fórmula, variável resposta, períodos correlacionados, preparação, exclusões, validação e condições de uso. Não replicar de segunda mão antes dessa revisão.
2. Verificar com editor/autores os termos de reprodução dos coeficientes/regra em software DeepFarms. O registro “open access” do boletim Embrapa permite consulta, mas não especifica por si só licença para transcrever a árvore para um produto.
3. Um profissional habilitado precisa delimitar região, cultivares, condição de produção (carga/espaçamento) e interpretação de saída apropriadas ao piloto.
4. Definir uma fonte histórica diária com proveniência e granularidade adequada para Tmin e RH. Se for usada estação próxima ou dado reanalisado, avaliar distância, resolução espacial, lacunas, correção e diferença para medições no dossel.
5. Decidir se se reproduzirá o modelo Hinnah de dois preditores ou a árvore Embrapa com atributos de período de infecção/incubação. Não combinar limiares/modelos de fontes diferentes em uma regra híbrida sem desenvolvimento e validação próprios.
6. Estabelecer antes do teste o que será “evento positivo”, horizonte de previsão, lead time, completude, sensibilidade mínima e tolerância de falsos negativos, com responsáveis agronômicos e produto.

## 7. Plano mínimo de validação independente

1. **Protocolo antes dos dados:** assinar plano com hipótese, unidade de análise (talhão-safra-mês ou janela), definição de ferrugem observada, regra de amostragem, janela de predição, critério de positivo e limiares de aceitação. Definir o que conta como falso negativo antes de avaliar.
2. **Coleta pareada:** para cada talhão/safra, armazenar identificador de fazenda/região, coordenadas ou zona climática, altitude se disponível, cultivar, idade, sistema/espaçamento, carga pendente, manejo relevante e observação fitopatológica. A avaliação de incidência deve usar protocolo constante e responsável treinado; clima deve guardar fonte, estação, timestamps, variáveis horárias/diárias e flags de qualidade.
3. **Série climática:** obter, no mínimo, as variáveis e a janela requeridas exatamente pelo candidato. Não imputar medições ausentes sem procedimento explicitamente validado; não substituir molhamento por UR média. Registros usados na previsão devem preceder temporalmente a data de avaliação.
4. **Separação independente:** dividir por safra e, quando o uso pretendido exigir transferência geográfica, por região/fazenda (não apenas linhas aleatórias do mesmo talhão). Ajuste/desenvolvimento fica no conjunto de treino; decisões de parâmetro e seleção de modelo não podem olhar o teste. Manter validação externa temporal/geográfica lacrada.
5. **Comparadores e métricas:** comparar com baseline de prevalência/estação e reportar matriz de confusão, sensibilidade (prioridade para falsos negativos), especificidade, precisão/valor preditivo positivo, acurácia balanceada, taxa de falsos negativos, cobertura de janelas calculáveis e intervalos de confiança. Se o output for realmente uma taxa/probabilidade contínua, avaliar erro/calibração em separado; não renomear o score para probabilidade sem calibração.
6. **Critérios de aceitação pré-fixados:** o responsável agronômico e o produto devem definir metas numéricas de sensibilidade/falso-negativo aceitável, desempenho mínimo frente ao baseline, completude e estabilidade por região/cultivar. Não há base nesta etapa para inventar valores de corte. Reprovar se falsos negativos excederem limite pré-fixado ou se desempenho depender de dados indisponíveis no uso real.
7. **Revisão habilitada e prospectiva:** agrônomo/fitopatologista independente revisa protocolo, resultados, extrapolação e mensagens. Depois da avaliação retrospectiva, fazer piloto prospectivo em modo sombra, sem recomendar manejo, antes de exibir qualquer alerta operacional.
8. **Separação de semântica:** a saída climática deve ser apresentada como estimativa do modelo e não como diagnóstico. Confirmar doença por observação de campo e manter a decisão de controle sob orientação agronômica; este relatório não aprova recomendação automática de defensivos.

## 8. Referências principais

- Hinnah, F. D. et al. (2018). [Weather-based coffee leaf rust apparent infection rate modeling](https://link.springer.com/article/10.1007/s00484-018-1587-2). *International Journal of Biometeorology*, 62, 1847–1860. DOI: 10.1007/s00484-018-1587-2. Página pública consultada apresenta resumo/prévia; texto integral original não verificado.
- Hinnah, F. D. et al. (2020). [Assessing Biogeography of Coffee Rust Risk in Brazil as Affected by the El Niño](https://repositorio.usp.br/directbitstream/4bfdb12d-f12f-40d9-981f-0b5f813d6974/3042186-Assessing%20Biogeography%20of%20Coffee%20Rust%20Risk%20in%20Brazil....pdf). *Plant Disease*, 104, 1013–1018. DOI: 10.1094/PDIS-01-19-0207-SR. Fonte consultada para conferir a equação que atribui a Hinnah et al. (2018) e a avaliação aplicada.
- Meira, C. A. A.; Rodrigues, L. H. A. (2009). [Árvores de decisão aplicadas na análise e no alerta da ferrugem do cafeeiro](https://www.infoteca.cnptia.embrapa.br/infoteca/bitstream/doc/662782/1/cnptiabp221.pdf). Embrapa Informática Agropecuária, Boletim de Pesquisa e Desenvolvimento 22.
- Meira, C. A. A.; Rodrigues, L. H. A.; Moraes, S. A. (2008). [Análise da epidemia da ferrugem do cafeeiro com árvore de decisão](https://www.scielo.br/j/tpp/a/gwhNLwQB58hkwJSSWdJ7gbB/). *Tropical Plant Pathology*, 33, 114–124.

## 9. Resultado final

- **Modelo candidato para avaliação documental adicional:** Hinnah et al. (2018), pela equação compacta e pela avaliação subsequente em regiões brasileiras de arábica. A reprodução exata deve aguardar a auditoria do texto integral original e das condições/licença.
- **Referência útil para coleta e validação:** árvore de Meira–Rodrigues/Embrapa, por ter dados arábica e contexto regional explícitos; não é compatível com os dados persistidos atuais.
- **Implementação agora:** **NO-GO**. Não há uma regra que possa ser colocada em produção com evidência, dados e validação suficientes.
- **Viabilidade futura:** condicional à obtenção dos dados diários corretos, dos atributos de campo necessários e validação externa independente, com revisão de profissional habilitado.
- **Aprovação agronômica:** não concedida. Nenhum resultado desta investigação autoriza diagnóstico, alerta operacional ou aplicação de defensivos.
