# DeepFarms Campo (`apps/campo`)

Aplicativo PWA offline-first para operação rural em campo (Caderno de Campo, Tarefas Programadas, Manejo Agrícola, Manejo Pecuário e Sincronização Resiliente).

## Features

### UI/UX Adaptativa por Ambiente de Execução (`mobile`, `tablet`, `desktop` e `standalone`)
- **Descrição curta:** Identificação automática do dispositivo e modo de execução para adaptar a navegação, diálogos/bottom-sheets, cabeçalhos contextuais e ergonomia de toque, eliminando aparência de site de navegador quando executado em celulares e tablets no campo.
- **Fluxo de funcionamento:**
  1. **Detecção Determinística (`src/lib/device/device-detection.ts`):** Classifica o dispositivo em `mobile` (`< 768px`), `tablet` (`768px–1023px` ou tablets touch em landscape) ou `desktop` (`>= 1024px` com ponteiro fino), além de detectar o modo `standalone` (PWA instalado) vs `browser` e o sistema operacional (`ios`, `android`, `other`).
  2. **Shell Nativo no Celular (`mobile`):**
     - `CampoTopAppBar` exibe botão de retorno contextual e título da rota ativa quando o operador entra em sub-rotas (`/agricultura`, `/pecuaria`, `/tarefas`, `/caderno`, `/recomendacoes`, `/sync`, `/campo/*`), mantendo o seletor de unidade produtiva, indicadores de rede/Sync/GPS e alternância de tema Claro/Escuro.
     - `CampoBottomNav` funciona como dock nativo exclusivo para smartphones (`md:hidden`) com botão central **+ Novo** que abre uma *Bottom Sheet* de lançamento rápido para qualquer apontamento agrícola ou pecuário contratado.
     - `BottomSheet` renderiza como folha deslizante inferior com alça tátil e respeito a `env(safe-area-inset-bottom)`.
  3. **Navigation Rail em Tablets e Sidebar Retrátil em Desktop (`tablet` / `desktop`):**
     - `AdaptiveCampoSidebar` (`hidden md:flex`) separa os itens por módulo contratado na sessão (`Operação de Campo`, `Módulo Agrícola`, `Módulo Pecuária`), iniciando retraída como *Navigation Rail* em tablets e expandida em desktops.
     - `BottomSheet` adapta sua apresentação automaticamente para modal centralizado (`centered-dialog`) com suporte à tecla `Escape`.

