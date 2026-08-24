# Roadmap: Módulo Premium de Inteligência Climática Pecuária (P6_INTELIGENCIA)

Este documento guarda o registro das próximas grandes funcionalidades a serem implementadas no módulo premium de Inteligência Climática Pecuária. Na nova sessão de agente, utilize este documento como base para planejamento e desenvolvimento.

## Funcionalidades a serem desenvolvidas:

### 1. Previsão da Janela de IATF (Estação de Monta)
- **Objetivo**: O estresse térmico afeta drasticamente a taxa de prenhez das vacas. Criar um algoritmo que cruza a previsão estendida com os dados reprodutivos para recomendar as melhores semanas (janelas climáticas) para realizar a Inseminação Artificial em Tempo Fixo (IATF), maximizando a concepção.
- **Integração necessária**: Previsão do OpenWeather (15 dias se possível, ou base 5 dias) cruzada com os lotes de reprodução.

### 2. Algoritmo de Rotação de Pasto Baseado no Clima
- **Objetivo**: Ajudar o produtor a evitar degradação de pastagens por falta de chuvas x alta lotação. O motor deve cruzar o volume de chuvas (mm) recente com a Taxa de Lotação (UA/ha) atual e a evapotranspiração para calcular a Capacidade de Suporte e gerar alertas preventivos de troca de pasto.
- **Integração necessária**: Histórico pluviométrico, módulo de Pastagens (UA/ha) e lotes de animais.

### 3. Alerta Precoce de Parasitas (Carrapatos e Mosca do Chifre)
- **Objetivo**: Semelhante à previsão de fungos na agricultura, esse modelo vai cruzar Graus-Dia (GDU) e Umidade para calcular o ciclo biológico de parasitas.
- **Entregável**: Painel alertando a janela exata de eclosão de parasitas, recomendando o momento ideal do banho carrapaticida preventivo, antes de o rebanho ser infestado.

### 4. Predição de Prejuízo no Ganho Médio Diário (GMD)
- **Objetivo**: Converter impacto climático em impacto financeiro. 
- **Regra**: O sistema vai cruzar o ITH (Índice de Temperatura e Umidade) com o modelo de engorda do gado, predizendo a quebra do consumo de matéria seca e calculando a perda diária de peso estimada (e o prejuízo financeiro atrelado).
- **Indicador**: O sistema calcularia, por exemplo: *"Nesta onda de calor de 3 dias, o lote A deixará de ganhar X kg, gerando um prejuízo de R$ Y."*
