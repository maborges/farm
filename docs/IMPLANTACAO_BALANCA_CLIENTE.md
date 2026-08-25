# Implantação do Módulo Balança no Cliente

> A Balança é instalada como serviço independente em
> `/opt/lampp/htdocs/balanca-platform`. Não execute migrations de Balança no
> banco do AgroSaaS. O AgroSaaS apenas configura o conector HTTP e consome os
> eventos publicados pelo serviço.

Este documento descreve a implantação do módulo Balança em um tenant do AgroSaaS.

## 1. Preparar o ambiente AgroSaaS

Antes de iniciar a implantação no cliente:

1. Publicar o backend, `apps/web` e `balanca-platform/station`.
2. Configurar no AgroSaaS `BALANCA_SERVICE_URL`,
   `BALANCA_SERVICE_CLIENT_ID` e `BALANCA_SERVICE_CLIENT_SECRET`.
   As migrations e o banco da Balança são executados separadamente conforme o
   manual do projeto independente.
3. Confirmar que o plano do cliente possui o módulo `O4_BALANCA`.

O módulo é comercializado separadamente e exige plano Profissional ou superior. Em instalações antigas, conferir se `O4_BALANCA` foi incluído no plano, pois o backfill histórico não é automático.

4. Garantir que o worker de outbox esteja rodando em produção.

Esse worker entrega o evento `balanca.pesagem.concluida` aos módulos de Colheita, Pecuária, Compras e Vendas. Sem ele, a pesagem fica registrada na Balança, mas o módulo de origem não é atualizado automaticamente.

## 2. Levantar informações no cliente

Coletar antes da instalação:

- quantidade de estações;
- localização de cada estação;
- fazendas atendidas por cada estação;
- tipo de uso: caminhões, animais ou ambos;
- marca e modelo do indicador;
- conexão disponível: RS232 ou TCP/Ethernet;
- capacidade da balança;
- número de série;
- certificado e validade da aferição;
- operadores da estação;
- processos que utilizarão a pesagem: Colheita, Compras, Vendas e/ou Pecuária.

A balança física e o terminal são cadastros diferentes. O terminal pode ser trocado ou funcionar como backup, enquanto o equipamento físico mantém seu histórico de aferições.

## 3. Cadastrar a balança no painel administrativo

No `apps/web`, com um usuário administrador:

1. Acessar **Balança → Balanças Físicas**.
2. Cadastrar fabricante, modelo, número de série, capacidade e fazenda.
3. Registrar a aferição vigente, informando data, validade, órgão aferidor, certificado e resultado.
4. Acessar **Balança → Estações de Balança**.
5. Criar a estação, informando nome e fazendas permitidas.
6. Associar a estação à balança física, se aplicável.
7. Gerar o código de ativação.

O código é temporário e válido por 30 minutos. Se expirar, usar a opção **Reativar**.

## 4. Instalar e ativar o terminal

No computador ou tablet próximo à balança:

1. Abrir a URL do PWA `balanca-platform/station`.
2. Informar o código de ativação.
3. Definir o PIN da estação.
4. Instalar o PWA pelo Chrome ou Edge.
5. Configurar o navegador ou o sistema para modo kiosk, se necessário.

Cada terminal recebe um token próprio. Em caso de troca ou perda do equipamento, revogar o dispositivo antigo e ativar o novo.

## 5. Cadastrar os operadores

No painel administrativo:

1. Acessar **Balança → Operadores**.
2. Selecionar uma Pessoa já cadastrada no sistema.
3. Definir um PIN pessoal de 4 a 8 dígitos.
4. Revogar operadores que deixarem de trabalhar na estação.

Na estação, o operador seleciona seu nome e informa o PIN. O primeiro login exige internet, pois a validação ocorre no servidor. Depois disso, a pesagem pode continuar offline.

## 6. Instalar a ponte de hardware

A ponte é necessária para leitura eletrônica do indicador. Recomenda-se usar um Raspberry Pi ou computador dedicado próximo ao equipamento.

```bash
cd balanca-platform/bridge
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
cp config.yaml.example config.yaml
```

Configurar no `config.yaml`:

- `connection_type`: `SERIAL` ou `TCP`;
- porta serial ou endereço IP;
- velocidade da serial;
- expressão regular do peso;
- separador decimal;
- unidade;
- fator de escala;
- token de acesso, se utilizado.

Em produção, executar a ponte como serviço permanente, preferencialmente via `systemd`. Ela ficará disponível em:

```text
http://IP_DA_PONTE:8321
```

No PWA, usar **Configurar ponte** e informar essa URL.

A ponte foi validada com simulador, mas deve ser testada com o indicador físico do cliente. O formato real do frame pode exigir ajuste da regex.

## 7. Validar a conectividade

```text
Indicador da balança
        ↓ RS232 ou TCP
Ponte local
        ↓ rede local
PWA da estação
        ↓ internet, somente para sincronização
Backend AgroSaaS
```

Validar separadamente:

- indicador → ponte;
- ponte → PWA;
- PWA → backend;
- backend → worker de outbox;
- backend → módulos de origem.

A leitura do peso não depende da internet. A internet é necessária para sincronizar ordens, fazer login de operador e enviar os resultados ao servidor.

## 8. Executar o piloto

Começar com uma estação e um fluxo operacional:

1. cadastrar a estação;
2. cadastrar pelo menos dois operadores;
3. testar pesagem manual;
4. testar a operação sem internet;
5. verificar a sincronização posterior;
6. testar a pesagem eletrônica;
7. criar uma ordem de Colheita, Compra, Venda ou Pecuária;
8. confirmar que o módulo de origem recebeu o peso;
9. gerar e conferir o ticket PDF;
10. testar uma pesagem avulsa e sua reconciliação.

## 9. Treinar o operador

O fluxo diário é:

1. fazer login com o PIN pessoal;
2. selecionar a ordem pendente;
3. conferir veículo, animal, documento e etapa;
4. informar o peso declarado, quando aplicável;
5. capturar o peso aferido pela ponte ou digitá-lo manualmente;
6. confirmar a etapa;
7. repetir a segunda etapa, quando for pesagem dupla;
8. baixar ou imprimir o ticket;
9. conferir o horário da última sincronização.

Usar **Pesagem avulsa** quando não houver ordem disponível. Ela cria uma ordem sombra, que pode ser associada posteriormente pelo escritório em **Balança → Reconciliação**.

## 10. Critérios de aceite

A implantação pode ser considerada concluída quando:

- a estação está ativada e identificada;
- os operadores conseguem entrar;
- a pesagem manual funciona offline;
- a leitura eletrônica funciona, se contratada;
- a sincronização não duplica pesagens;
- o peso chega ao módulo de origem;
- o ticket PDF é gerado;
- a aferição da balança está registrada;
- o worker de outbox está ativo;
- a equipe sabe revogar e reativar uma estação;
- existe procedimento para reconciliação de pesagens avulsas.

## Observação sobre a documentação

O documento `MODULO_BALANCA.md`, atualizado em 17/08/2026, indica que as integrações com Colheita, Pecuária, Compras e Vendas já estão implementadas. O `brainstorm-modulo-balanca.md`, de 16/08/2026, ainda tratava algumas integrações como piloto pendente. Para a implantação, deve-se seguir o documento mais recente e validar os fluxos no ambiente do cliente.
