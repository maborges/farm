# FITO-RISK-05 — Avaliação de fontes gratuitas para dados climáticos históricos

**Data:** 2026-10-30
**Escopo:** complemento à análise de viabilidade do FITO-RISK-04. Avalia AGROMET, Agritempo e INMET para obter dados climáticos históricos, sem integração, contratação, sincronização ou alteração de banco.

## 1. Resultado executivo

**Recomendação: manter o INMET como primeira opção para a prova histórica**, por disponibilizar arquivos anuais horários de estações automáticas e consultas históricas em CSV. Isso favorece a construção de uma série rastreável de temperatura e umidade para retrospectiva, sujeita à inspeção de cobertura e qualidade de cada estação. Os próprios avisos do INMET dizem que os dados automáticos são brutos e não passam por consistência; faltas e valores sentinela devem ser tratados.

O **Agritempo** é a alternativa de pesquisa mais próxima em cobertura e apresentação de históricos diários: a plataforma informa mais de 1.600 estações e séries de 30 a 100 anos, e o formulário estadual permite pesquisar temperatura mínima e umidade relativa mínima/máxima por estação e intervalo. Porém, não foi confirmado acesso por API ou download em lote, a umidade média diária necessária ao candidato Hinnah não aparece como variável no formulário inspecionado, e os termos proíbem uso comercial dos conteúdos e restringem dados brutos sem autorização. Para um SaaS, ainda que gratuito ao produtor, é necessária autorização expressa antes de reutilizar dados/conteúdo.

O **AGROMET do INMET/CONAB** é uma ferramenta gratuita para produtores, útil para previsão e consulta de observações recentes, com representação de culturas incluindo café. A documentação consultada não confirma histórico longo, API pública ou arquivos para backfill. “Gratuito para o produtor” descreve o acesso ao aplicativo, não licença de republicação ou consumo automatizado dentro de um SaaS.

**Decisão:** GO COM RESSALVAS para a preparação retrospectiva pelo INMET, como proposto no FITO-RISK-04. Agritempo pode ser consultado como fonte exploratória ou comparativa somente após resolver termos e confirmar série média de RH/exportação. AGROMET não substitui o arquivo histórico. Esta decisão não homologa modelo fitossanitário e não deve bloquear o lançamento do Agro PWA.

## 2. Desambiguação de “AGROMET”

O nome é usado por produtos diferentes. Neste relatório, **AGROMET** refere-se principalmente ao produto do INMET, em parceria com a CONAB, acessível pelos mapas do INMET e aplicativo. Há também um aplicativo chamado **Agromet** da Embrapa Clima Temperado, que exibe dados em tempo real de uma estação da Embrapa em Pelotas/RS e resumos mensais desde 2009. Este segundo produto tem cobertura local e não é uma série nacional para as regiões de café arábica; não foi tratado como alternativa ao INMET.

O INMET descreve o AGROMET como mapas de previsão de chuva, temperatura e umidade relativa até sete dias, dados em tempo real de estações, imagens e camadas de culturas, incluindo café; informa também que o aplicativo não tem custo para o produtor. [Descrição oficial do AGROMET pelo INMET](https://portal.inmet.gov.br/noticias/no-dia-do-produtor-rural-conhe%C3%A7a-um-pouco-mais-sobre-as-plataformas-desenvolvidas-pelo-inmet-voltadas-para-o-agricultor). A Embrapa descreve o homônimo regional como dados de uma estação automática na sede em Pelotas, com resumos mensais a partir de janeiro de 2009. [Aplicativo Agromet da Embrapa Clima Temperado](https://www.embrapa.br/en/web/clima-temperado/busca-de-solucoes-tecnologicas/-/produto-servico/4317/aplicativo-agromet-dados-meteorologicos-de-pelotas-rs-em-tempo-real).

## 3. Comparativo objetivo

| Critério | AGROMET (INMET/CONAB) | Agritempo (Embrapa/CEPAGRI-Unicamp) | INMET — BDMEP/arquivos históricos |
|---|---|---|---|
| **Responsável e endereço oficial** | Produto do INMET em parceria com a CONAB; mapas em [mapas.inmet.gov.br](https://mapas.inmet.gov.br/) e acesso pelo app/portal INMET. | Desenvolvido e mantido pela Embrapa Agricultura Digital com CEPAGRI/Unicamp; [agritempo.gov.br](https://www.agritempo.gov.br/). | Instituto Nacional de Meteorologia; [BDMEP](https://bdmep.inmet.gov.br/) e [arquivos anuais](https://portal.inmet.gov.br/dadoshistoricos/). |
| **Histórico de Tmin** | **Não confirmado** para uma série histórica de pesquisa/backfill. A documentação localizada descreve previsão de até sete dias e observações em tempo real. | **Sim, interface de consulta:** formulário diário oferece temperatura mínima por estação e intervalo selecionável. A série exata depende da estação. | **Sim:** arquivos horários de automáticas desde 2000 permitem calcular Tmin diária após controle de completude; BDMEP também oferece dados diários/horários selecionáveis por estação. |
| **Umidade relativa histórica** | Observações recentes em tempo real e previsão mencionadas; histórico retroativo **não confirmado**. | O formulário público apresenta umidade relativa mínima e máxima; RH média diária **não confirmada** na interface. Não assumir que min/max equivalham à média diária requerida pelo modelo. | Registros horários de RH estão disponíveis em arquivos/consultas conforme estação; média diária pode ser calculada de observações válidas com método e completude documentados. |
| **Cobertura de café arábica** | Camadas de mapa identificam café e o produto é destinado a áreas produtoras brasileiras, mas isso não comprova arquivo histórico local por fazenda. | O sistema declara cobertura nacional, >1.600 estações e séries de 30–100 anos. Páginas de pesquisa estão disponíveis para MG e SP, estados produtores; não foi verificada densidade/completude estação a estação nem cobertura de todas as fazendas. | Rede nacional e arquivos de todas as estações automáticas; ainda é necessário verificar distância, período ativo e adequação de estações a cada lavoura. |
| **API ou arquivos** | **Não confirmados** para série histórica no escopo consultado. O portal é uma interface de mapas/app; não foi localizada documentação de API pública para extração histórica. | Consulta histórica via páginas web com data e estação. Não foi localizada documentação oficial de API pública nem confirmação de exportação/download em lote. | **Sim:** pacotes anuais de todas as estações automáticas e requisições CSV no BDMEP; dados horários, diários ou mensais. Para alguns pedidos curtos, o próprio sistema direciona à tabela TEMPO. |
| **Gratuidade / limites** | INMET informa app sem custo ao produtor. Limite histórico/API não aplicável ou não confirmado; o uso gratuito do app não comprova acesso programático. | A consulta web é acessível sem cobrança informada, mas termos distinguem acesso de direitos de reutilização. Limites de consulta/exportação não documentados. | Arquivos públicos estão disponíveis sem tarifa indicada; solicitações selecionadas têm fluxo de fila/e-mail e links temporários no BDMEP. Cotas de API não se aplicam. |
| **Uso em SaaS comercial gratuito ao produtor** | **Não confirmado.** A gratuidade do aplicativo/produtor não autoriza automaticamente extração, armazenamento ou redistribuição em outro produto. Solicitar confirmação ao INMET/CONAB antes de integração/redistribuição. | **Não autorizado pelos termos atuais sem permissão expressa:** uso comercial de conteúdo é proibido, e dados brutos são restritos sem autorização dos titulares. O SaaS ser gratuito ao produtor não elimina o caráter comercial da plataforma. Pedir autorização formal. | Os documentos consultados confirmam acesso público, mas não resolvem expressamente licença de redistribuição/uso em SaaS. Para prova analítica interna, não há tarifa indicada; para incorporar/publicar dados, confirmar termos com INMET. |
| **Vantagem/limitação frente ao INMET** | Visão agrícola simples e camada de café; útil para contexto atual e previsão. Não há evidência de histórico retroativo necessário. | Maior conveniência para consultar agregados diários e histórico longo potencial; perde em transparência/viabilidade operacional sem exportação/API, RH média não confirmada e restrição comercial explícita. | Melhor evidência de séries históricas observadas, arquivos exportáveis e processo já identificado para análise independente. Exige processamento de dados brutos, inspeção de falhas e mapeamento de estação. |

### Evidências do Agritempo

O portal informa que recebe dados diários de mais de 1.600 estações e dispõe de séries entre 30 e 100 anos. [Sobre o Agritempo](https://www.agritempo.gov.br/br/sobre-nos/). A página de pesquisa de MG, assim como as páginas de SP e PR, expõe campos para cidade, estação, datas, temperatura mínima e umidade relativa mínima/máxima; isto comprova a consulta na interface, mas não prova API, exportação em lote ou presença de RH média. [Pesquisa MG](https://www.agritempo.gov.br/br/estado/MG/pesquisa/), [Pesquisa SP](https://www.agritempo.gov.br/br/estado/SP/pesquisa/), [Pesquisa PR](https://www.agritempo.gov.br/br/estado/PR/pesquisa/).

Os termos do Agritempo atribuem aos mantenedores direitos de propriedade intelectual dos conteúdos processados e dados brutos fornecidos, vedam usos comerciais dos conteúdos salvo autorização expressa e dizem que dados brutos restritos não podem ser usados sem autorização do titular. [Termo de Uso Agritempo, seção 4](https://www.agritempo.gov.br/br/termo-de-uso/). Como os termos não definem especificamente o enquadramento de um SaaS gratuito ao produtor, não se pode concluir que esse cenário esteja liberado; obter autorização escrita e delimitar dados e formas de uso antes da reutilização.

### Evidências do INMET

O INMET mantém pacotes horários anuais das estações automáticas desde 2000. O BDMEP descreve seleção de período, estações e variáveis e envio de resultado CSV, além de pacotes anuais para download imediato. [Dados históricos anuais](https://portal.inmet.gov.br/dadoshistoricos/), [BDMEP e fluxo de CSV](https://bdmep.inmet.gov.br/). O portal também documenta observações automáticas recentes de hora em hora para os últimos 90 dias. [Serviço de estações automáticas](https://portal.inmet.gov.br/servicos/esta%C3%A7%C3%B5es-autom%C3%A1ticas).

Há limitações de qualidade: o INMET alerta que os dados automáticos publicados são brutos, sem consistência, e que valores ausentes podem aparecer como `9999`, `Null` ou vazio. [Orientação oficial sobre consulta e qualidade dos dados](https://portal.inmet.gov.br/noticias/saiba-como-acessar-os-dados-meteorol%C3%B3gicos-dispon%C3%ADveis-no-site-do-inmet). Portanto, exportar não equivale a ter uma série pronta para o modelo; cada estação e janela devem passar por QC e critérios de completude previamente definidos.

## 4. Recomendação para a prova histórica

1. **Usar INMET como fonte primária da prova**, por ter histórico observacional e meio de exportação documentados. Selecionar fazendas-piloto, identificar estações próximas e verificar coordenadas, altitude, datas de operação, variáveis, dias faltantes e integridade horária antes de calcular agregados.
2. **Manter a extração e análise fora do banco de produção.** Preservar os arquivos originais, metadados, fonte/estação, fuso (INMET informa horários UTC), valores sentinela e relatório de qualidade. Não preencher lacunas por conveniência.
3. **Não usar AGROMET como backfill** até haver prova oficial de histórico, endpoint/exportação e autorização de uso. Pode continuar sendo consultado pelo produtor para o propósito oferecido pelo INMET.
4. **Não incorporar dados Agritempo a um SaaS sem autorização expressa.** Se a Embrapa/CEPAGRI autorizar a prova, confirmar também exportação dos registros e disponibilidade do RH diário médio na estação/período escolhidos. Até lá, é apenas referência de cobertura/consulta exploratória.
5. **Não combinar fontes como se fossem equivalentes.** Se Agritempo ou qualquer outra fonte for usado como comparação com INMET, marcar explicitamente fonte, natureza e agregação; comparar a mesma janela e variável após validação sem misturar na série principal.

## 5. Limites da conclusão

- A cobertura de estações em torno das fazendas DeepFarms ainda não foi avaliada com coordenadas reais; cobertura nacional declarada não garante estação representativa para cada lavoura.
- Não foi executada coleta de amostra, consulta autenticada ou inspeção de dados por fazenda, portanto não se afirma completude real das séries.
- API/download não encontrado significa **não confirmado na documentação pública consultada**, não prova de inexistência de interfaces privadas ou mecanismos internos.
- O uso de INMET em produto comercial, republicação ou armazenamento persistente ainda requer confirmação adequada dos termos/licenças.
- A comparação de fontes não valida a equação de Hinnah ou regra fitossanitária. O resultado climático, caso futuramente validado, não é diagnóstico nem recomendação de defensivos.
- Esta avaliação não bloqueia o lançamento do Agro PWA: recomendações se aplicam somente à preparação da futura prova fitossanitária histórica.

## 6. Veredicto

**GO COM RESSALVAS** para iniciar prova histórica analítica, não operacional, usando INMET como primeira opção e começando por estudo de cobertura/qualidade das estações próximas às fazendas piloto. **AGROMET: insuficiente para backfill histórico com a evidência atual. Agritempo: tecnicamente interessante para consulta diária, mas uso no SaaS depende de autorização expressa e de confirmação de RH média/exportação.**

**NO-GO** para usar qualquer uma dessas fontes para publicar alerta fitossanitário ou declarar o modelo homologado. Não se exige alteração no Agro PWA nem integração meteorológica para seu lançamento.

## 7. Fontes oficiais

- [INMET — AGROMET gratuito e camadas de café](https://portal.inmet.gov.br/noticias/no-dia-do-produtor-rural-conhe%C3%A7a-um-pouco-mais-sobre-as-plataformas-desenvolvidas-pelo-inmet-voltadas-para-o-agricultor)
- [INMET — mapa de estações e camada AgroMet](https://portal.inmet.gov.br/servicos/mapa-de-esta%C3%A7%C3%B5es-meteorol%C3%B3gicas)
- [Agritempo — instituição, cobertura e séries](https://www.agritempo.gov.br/br/sobre-nos/)
- [Agritempo — consulta de dados para MG](https://www.agritempo.gov.br/br/estado/MG/pesquisa/)
- [Agritempo — termos de uso](https://www.agritempo.gov.br/br/termo-de-uso/)
- [INMET — pacotes históricos anuais](https://portal.inmet.gov.br/dadoshistoricos/)
- [INMET — BDMEP](https://bdmep.inmet.gov.br/)
- [INMET — observações automáticas recentes](https://portal.inmet.gov.br/servicos/esta%C3%A7%C3%B5es-autom%C3%A1ticas)
- [INMET — qualidade e valores ausentes](https://portal.inmet.gov.br/noticias/saiba-como-acessar-os-dados-meteorol%C3%B3gicos-dispon%C3%ADveis-no-site-do-inmet)
