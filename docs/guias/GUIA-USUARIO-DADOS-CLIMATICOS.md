# Guia do Usuário — Dados Climáticos

## Objetivo

Este guia explica como configurar o OpenWeather, testar a conexão, atualizar os dados climáticos e consultar as informações de cada unidade produtiva.

A configuração é feita por unidade produtiva. Portanto, antes de executar qualquer ação, confirme qual unidade está selecionada no sistema.

## Pré-requisitos

Antes de começar:

1. Acesse o sistema com seu usuário.
2. Selecione o tenant correto.
3. Selecione a unidade produtiva no seletor global de fazenda/unidade.
4. Confirme que a unidade possui coordenadas cadastradas.
5. Tenha em mãos uma API key válida do OpenWeather.

## 1. Configurar o OpenWeather

No menu, acesse:

**Dashboard → Configurações → Integrações → Clima → OpenWeather**

Também é possível acessar diretamente:

`/dashboard/settings/integracoes/clima/openweather`

### Passo a passo

1. Confirme a unidade produtiva exibida no contexto ativo.
2. Informe a **API Key** do OpenWeather.
3. Confira a **Base URL**:

   `https://api.openweathermap.org`

4. Confirme o ambiente como `production`.
5. Se necessário, ajuste unidade de medida, idioma, timeout e cache.
6. Clique em **Salvar configuração**.
7. Aguarde a mensagem de confirmação.

### Importante

A mesma API key pode ser utilizada por várias unidades produtivas do mesmo tenant. A configuração, o status e os dados climáticos permanecem separados por unidade.

## 2. Testar a conexão

1. Permaneça em:

   **Dashboard → Configurações → Integrações → Clima → OpenWeather**

2. Confirme a unidade ativa.
3. Clique em **Testar conexão**.
4. Aguarde o resultado.

Uma conexão bem-sucedida deverá apresentar temperatura, umidade, condição climática e localização consultada.

Se a unidade não possuir coordenadas válidas, o teste será interrompido e uma mensagem de orientação será exibida.

## 3. Consultar o clima atual

1. Selecione a unidade produtiva desejada.
2. Abra o console OpenWeather pelo menu:

   **Dashboard → Configurações → Integrações → Clima → OpenWeather**

3. Clique em **Consultar clima atual**.
4. Aguarde a confirmação da sincronização.

A consulta atualiza os dados da unidade selecionada. Ela não altera os dados de outras unidades.

## 4. Consultar o dashboard climático

No menu, acesse:

**Dashboard → Agrícola → Climático**

Também é possível acessar diretamente:

`/dashboard/agricola/climatico`

O dashboard apresenta, quando disponíveis:

- temperatura atual, mínima e máxima;
- precipitação;
- umidade relativa;
- velocidade do vento;
- data do último registro;
- fonte dos dados;
- status operacional;
- alertas climáticos;
- recomendações operacionais.

## 5. Trocar de unidade produtiva

1. Use o seletor global de fazenda/unidade.
2. Escolha outra unidade produtiva.
3. Aguarde o carregamento da tela.
4. Retorne ao console OpenWeather ou ao dashboard climático.

Após a troca, a configuração, o status, os jobs e os dados exibidos devem corresponder à nova unidade.

## 6. Unidade sem dados climáticos

Quando a unidade ainda não possui uma sincronização válida, o dashboard exibirá:

**Nenhum Dado Climático Encontrado**

Nesse caso:

1. Confirme se a API key foi configurada.
2. Confirme se a unidade correta está selecionada.
3. Verifique se existem coordenadas cadastradas.
4. Abra o console OpenWeather.
5. Execute **Testar conexão**.
6. Em caso de sucesso, execute **Consultar clima atual**.
7. Retorne ao dashboard climático.

## 7. Unidade sem coordenadas

Uma unidade sem latitude e longitude não pode consultar o clima por localização precisa.

Nesse caso:

1. Acesse o cadastro da unidade produtiva.
2. Informe as coordenadas da sede no formato aceito pelo sistema.
3. Salve o cadastro.
4. Retorne ao console OpenWeather.
5. Teste a conexão novamente.

Enquanto as coordenadas não forem corrigidas, a unidade permanecerá sem sincronização climática.

## 8. Verificar status e histórico operacional

No console OpenWeather, consulte os cartões:

- **Health e prontidão**: situação atual da integração;
- **Último sync**: último sincronismo da unidade;
- **Última leitura climática**: dado retornado pelo provider;
- **Diagnóstico rápido**: resumo de falhas e recomendações;
- **Últimos jobs**: execuções realizadas;
- **Linha do tempo operacional**: eventos e resultados da integração.

Os dados apresentados devem corresponder somente à unidade produtiva ativa.

## 9. Troca de unidade durante a operação

Não mantenha uma tela aberta esperando dados de uma unidade enquanto troca a unidade pelo seletor global. Depois de trocar:

1. aguarde a atualização da tela;
2. confirme o nome ou contexto da unidade;
3. só então execute uma nova configuração ou sincronização.

Isso evita salvar uma configuração no contexto errado.

## 10. Problemas comuns

### “OpenWeather não configurado para a unidade”

A unidade selecionada ainda não possui configuração unitária. Salve a configuração no console OpenWeather com essa unidade ativa.

### “Nenhum Dado Climático Encontrado”

Ainda não existe registro climático válido para a unidade. Teste a conexão e execute uma sincronização.

### API key inválida

Confirme a chave no painel do OpenWeather, verifique se ela está ativa e salve novamente a configuração.

### Unidade sem coordenadas

Cadastre latitude e longitude válidas para a unidade produtiva e repita o teste.

### Dados de outra unidade aparecem

1. Confirme o tenant ativo.
2. Confirme a unidade selecionada no seletor global.
3. Atualize a página.
4. Se o problema continuar, registre a unidade, o horário e a tela em que ocorreu.

## 11. Fluxo resumido

```text
Selecionar tenant
→ selecionar unidade produtiva
→ abrir OpenWeather
→ salvar configuração
→ testar conexão
→ consultar clima atual
→ abrir Dashboard → Agrícola → Climático
→ validar resumo, alertas e recomendações
```

## Resultado esperado

Cada unidade produtiva deve possuir seu próprio contexto climático:

- configuração independente;
- status independente;
- último sincronismo independente;
- histórico independente;
- alertas e recomendações relacionados à unidade selecionada.
