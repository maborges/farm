import React from "react";
import {
    LayoutDashboard, MapPin, Landmark, Sprout, CloudSun, Warehouse,
    Tractor, Beef, Scale, Receipt, Users, HardHat, Trees, BrainCircuit,
    Smartphone, PlusCircle, CheckCircle2, AlertTriangle, FileText, Ruler,
    TrendingUp, Layers, Satellite, Calculator, Thermometer, Wind, Droplets,
    ShoppingCart, ClipboardList, RefreshCcw, Syringe, Milk, Dna, CreditCard,
    Wallet, BookOpen, Clock, ShieldCheck, Shield, Sparkles, Zap, Building2,
    Bell, Moon, Wrench, ShieldAlert, BadgeCheck, FileSpreadsheet, Lock,
    Settings, Key, UserPlus, SlidersHorizontal, Route, Settings2, ArrowLeftRight, Mail
} from "lucide-react";

export interface ModuloItem {
    id: string;
    numero: string;
    titulo: string;
    descricao: string;
    icone: React.ElementType;
    status: "disponivel" | "em_breve";
    rota: string;
    btnTexto: string;
    tags: string[];
    videoUrl?: string;
    imagemUrl?: string;
    legendaUrl?: string;
    etapasVisuais?: EtapaVisual[];
}

export interface EtapaVisual {
    id: string;
    titulo: string;
    descricao: string;
    imagemUrl: string;
    tipo: "listagem" | "dialog" | "detalhes";
}

export interface GuiaItem {
    id: string;
    numero: number;
    titulo: string;
    passos: string[];
    destaque?: {
        tipo: "dica" | "alerta";
        texto: string;
    };
    tags: string[];
}

export interface ElementoItem {
    id: string;
    icone: React.ElementType;
    label: string;
    local: "Barra Superior" | "Área Central";
    descricao: string;
    tags: string[];
}

export interface FaqItem {
    id: string;
    pergunta: string;
    resposta: string;
    tags: string[];
}

// ═══════════════════════════════════════════════════════════════════════════════
// LISTA DOS 15 MÓDULOS CANÔNICOS DA PLATAFORMA (TODOS DISPONÍVEIS)
// ═══════════════════════════════════════════════════════════════════════════════

export const MODULOS: ModuloItem[] = [
    {
        id: "00-navegacao",
        numero: "Módulo 00",
        titulo: "Visão Geral e Navegação",
        descricao: "Aprenda a fazer login, se localizar na tela e alternar entre fazendas com segurança.",
        icone: LayoutDashboard,
        status: "disponivel",
        rota: "/dashboard",
        btnTexto: "Ir para Visão do Dia",
        imagemUrl: "/manual/imagens/00-navegacao/01-tela-inicial-dashboard.png",
        tags: ["dashboard", "navegação", "login", "porteira", "fazenda", "maleta", "ações rápidas"],
    },
    {
        id: "01-cadastros",
        numero: "Módulo 01",
        titulo: "Cadastros & Propriedades",
        descricao: "Unidades produtivas, talhões e georreferenciamento, produtos, insumos e parceiros.",
        icone: MapPin,
        status: "disponivel",
        rota: "/cadastros/propriedades",
        btnTexto: "Ir para Unidades Produtivas",
        imagemUrl: "/manual/imagens/01-cadastros/01-tela-propriedades.png",
        etapasVisuais: [
            {
                id: "listagem",
                titulo: "1. Painel de Propriedades",
                descricao: "Visão geral das fazendas com indicadores de área total, área útil, status operacional e ações rápidas.",
                imagemUrl: "/manual/imagens/01-cadastros/01-tela-propriedades.png",
                tipo: "listagem"
            },
            {
                id: "dialog-nova-unidade",
                titulo: "2. Dialog de Cadastro (Nova Unidade)",
                descricao: "Formulário operacional completo com identificação, tipo de exploração, endereço da sede, coordenadas e dados patrimoniais.",
                imagemUrl: "/manual/imagens/01-cadastros/02-dialog-nova-unidade.png",
                tipo: "dialog"
            }
        ],
        tags: ["propriedade", "unidade produtiva", "talhões", "mapa", "geometria", "produtos", "fornecedores", "pessoas", "insumos"],
    },
    {
        id: "02-imoveis",
        numero: "Módulo 02",
        titulo: "Imóveis Rurais",
        descricao: "Cadastro fundiário e legal, matrículas, NIRF, INCRA e laudos de avaliação patrimonial.",
        icone: Landmark,
        status: "disponivel",
        rota: "/cadastros/imoveis",
        btnTexto: "Ir para Imóveis",
        imagemUrl: "/manual/imagens/02-imoveis/01-tela-imoveis.png",
        tags: ["imóveis", "matrícula", "nirf", "incra", "arrendamento", "avaliação", "patrimônio"],
    },
    {
        id: "03-agricultura",
        numero: "Módulo 03",
        titulo: "Agricultura & Safras",
        descricao: "Safras, planejamento operacional, solo, caderno de campo, pragas e romaneios de colheita.",
        icone: Sprout,
        status: "disponivel",
        rota: "/agricola",
        btnTexto: "Ir para Agricultura",
        imagemUrl: "/manual/imagens/03-agricultura/01-tela-agricultura.png",
        tags: ["safra", "cultura", "plantio", "caderno de campo", "pulverização", "colheita", "romaneio", "solo", "pragas"],
    },
    {
        id: "04-clima",
        numero: "Módulo 04",
        titulo: "Clima e Previsão",
        descricao: "Previsão do tempo agrícola e pecuária, alertas de chuva e modelos fitossanitários e zoossanitários.",
        icone: CloudSun,
        status: "disponivel",
        rota: "/dashboard/agricola/clima/monitoramento",
        btnTexto: "Ir para Clima",
        imagemUrl: "/manual/imagens/04-clima/01-tela-clima.png",
        tags: ["clima", "tempo", "chuva", "previsão", "temperatura", "vento", "umidade", "gdu", "ith", "ferrugem"],
    },
    {
        id: "05-estoque",
        numero: "Módulo 05",
        titulo: "Estoque & Suprimento",
        descricao: "Pedidos de compra, almoxarifado, saldos, lotes com validade e requisições para o campo.",
        icone: Warehouse,
        status: "disponivel",
        rota: "/suprimentos",
        btnTexto: "Ir para Estoque",
        imagemUrl: "/manual/imagens/05-estoque/01-tela-estoque.png",
        tags: ["estoque", "almoxarifado", "compras", "pedidos", "lotes", "validade", "adubo", "semente", "requisições"],
    },
    {
        id: "06-frota",
        numero: "Módulo 06",
        titulo: "Frota & Manutenção",
        descricao: "Controle de tratores e máquinas, abastecimento de combustível, preventivas e jornadas.",
        icone: Tractor,
        status: "disponivel",
        rota: "/operacional",
        btnTexto: "Ir para Frota",
        imagemUrl: "/manual/imagens/06-frota/01-tela-frota.png",
        tags: ["frota", "trator", "máquinas", "diesel", "abastecimento", "manutenção", "oficina", "horímetro", "jornada"],
    },
    {
        id: "07-pecuaria",
        numero: "Módulo 07",
        titulo: "Pecuária & Rebanho",
        descricao: "Controle de brincos, lotes de gado, piquetes, pesagens de ganho de peso, vacinas e leite.",
        icone: Beef,
        status: "disponivel",
        rota: "/dashboard/pecuaria",
        btnTexto: "Ir para Pecuária",
        imagemUrl: "/manual/imagens/07-pecuaria/01-tela-pecuaria.png",
        tags: ["gado", "rebanho", "animais", "brincos", "lotes", "piquetes", "pastos", "vacinas", "gmd", "confinamento", "leite"],
    },
    {
        id: "08-balanca",
        numero: "Módulo 08",
        titulo: "Balança & Pesagem (TARA)",
        descricao: "Pesagem de caminhões na colheita e pesagem de gado com funcionamento mesmo sem internet.",
        icone: Scale,
        status: "disponivel",
        rota: "/dashboard/operacional/balanca/pesagens",
        btnTexto: "Ir para Balança",
        imagemUrl: "/manual/imagens/08-balanca/01-tela-balanca.png",
        tags: ["balança", "tara", "pesagem", "estação", "operador", "caminhão", "peso bruto", "líquido", "romaneio"],
    },
    {
        id: "09-financeiro",
        numero: "Módulo 09",
        titulo: "Financeiro & Custos",
        descricao: "Contas a pagar e receber, conciliação bancária, fluxo de caixa, DRE da safra e livro fiscal LCDPR.",
        icone: Receipt,
        status: "disponivel",
        rota: "/dashboard/financeiro",
        btnTexto: "Ir para Financeiro",
        imagemUrl: "/manual/imagens/09-financeiro/01-tela-financeiro.png",
        tags: ["financeiro", "pagar", "receber", "banco", "conciliação", "fluxo de caixa", "dre", "custos", "lcdpr", "nfe"],
    },
    {
        id: "10-rh",
        numero: "Módulo 10",
        titulo: "Recursos Humanos",
        descricao: "Cadastro de colaboradores, departamentos, controle de ponto, folha de pagamento e eSocial.",
        icone: Users,
        status: "disponivel",
        rota: "/dashboard/rh/colaboradores",
        btnTexto: "Ir para RH",
        imagemUrl: "/manual/imagens/10-rh/01-tela-rh.png",
        tags: ["rh", "funcionários", "equipe", "colaboradores", "ponto", "folha", "salário", "esocial", "departamentos"],
    },
    {
        id: "11-seguranca",
        numero: "Módulo 11",
        titulo: "Segurança do Trabalho (SST)",
        descricao: "Painel SST, normas regulamentadoras do campo (NR-31), controle de EPIs e treinamentos da equipe.",
        icone: HardHat,
        status: "disponivel",
        rota: "/dashboard/rh/seguranca",
        btnTexto: "Ir para SST",
        imagemUrl: "/manual/imagens/11-seguranca/01-tela-seguranca.png",
        tags: ["sst", "segurança", "epi", "nr31", "nr-31", "acidentes", "treinamento", "saúde", "proteção"],
    },
    {
        id: "12-ambiental",
        numero: "Módulo 12",
        titulo: "Ambiental, CAR & ESG",
        descricao: "Gestão do CAR, áreas de preservação APP e Reserva Legal, outorgas de água e passaporte verde.",
        icone: Trees,
        status: "disponivel",
        rota: "/dashboard/ambiental",
        btnTexto: "Ir para Ambiental",
        imagemUrl: "/manual/imagens/12-ambiental/01-tela-ambiental.png",
        tags: ["ambiental", "car", "app", "reserva legal", "água", "outorga", "esg", "carbono", "certificações", "queimadas"],
    },
    {
        id: "13-ia",
        numero: "Módulo 13",
        titulo: "Copiloto IA",
        descricao: "Assistente inteligente que analisa a safra, sugere planos de economia e recomendações operacionais.",
        icone: BrainCircuit,
        status: "disponivel",
        rota: "/dashboard/ia",
        btnTexto: "Ir para Copiloto IA",
        imagemUrl: "/manual/imagens/13-ia/01-tela-copiloto-ia.png",
        tags: ["ia", "copiloto", "inteligência", "recomendações", "plano de ação", "insights", "automação"],
    },
    {
        id: "14-campo-pwa",
        numero: "Módulo 14",
        titulo: "Campo PWA (Offline)",
        descricao: "Aplicativo móvel para tratoristas e operadores anotarem atividades no campo sem sinal de internet.",
        icone: Smartphone,
        status: "disponivel",
        rota: "/dashboard/operacional/campo/tarefas",
        btnTexto: "Ir para Campo PWA",
        imagemUrl: "/manual/imagens/14-campo-pwa/01-tela-campo-pwa.png",
        tags: ["campo", "pwa", "celular", "tablet", "offline", "sem internet", "apontamento", "tarefas", "sincronização"],
    },
    {
        id: "15-gestao-acesso",
        numero: "Módulo 15",
        titulo: "Gestão de Acesso & Equipe",
        descricao: "Controle de usuários, convites de equipe, perfis com matriz de permissões e segurança 2FA.",
        icone: Users,
        status: "disponivel",
        rota: "/dashboard/settings/team",
        btnTexto: "Ir para Gestão de Acesso",
        imagemUrl: "/manual/imagens/15-gestao-acesso/01-tela-gestao-acesso.png",
        tags: ["acesso", "equipe", "usuários", "membros", "perfis", "permissões", "segurança", "2fa", "sessões", "senhas", "bloqueio"],
    },
    {
        id: "16-configuracoes",
        numero: "Módulo 16",
        titulo: "Configurações da Fazenda & Sistema",
        descricao: "Dados do produtor titular e logotipo oficial, wizard de implantação, parâmetros globais e integrações.",
        icone: Settings,
        status: "disponivel",
        rota: "/dashboard/settings/tenant",
        btnTexto: "Ir para Configurações",
        imagemUrl: "/manual/imagens/16-configuracoes/01-tela-configuracoes.png",
        tags: ["configurações", "produtor", "logotipo", "marca", "wizard", "implantação", "globais", "ano agrícola", "hectares", "alqueires", "integrações", "balança", "clima", "erp", "assinatura", "faturas", "plano", "ia", "smtp"],
    },
    {
        id: "17-jornadas",
        numero: "Módulo 17",
        titulo: "Jornadas Práticas do Dia a Dia",
        descricao: "Como os módulos operam integrados na rotina matinal da lavoura, no curral e na colheita.",
        icone: Route,
        status: "disponivel",
        rota: "/dashboard",
        btnTexto: "Ver Rotinas da Fazenda",
        imagemUrl: "/manual/imagens/17-jornadas/01-tela-jornadas.png",
        tags: ["jornadas", "rotina", "lavoura", "curral", "colheita", "escritório", "integração", "boas práticas", "dia a dia"],
    },
];

// ═══════════════════════════════════════════════════════════════════════════════
// GUIAS PASSO A PASSO POR MÓDULO (15 MÓDULOS)
// ═══════════════════════════════════════════════════════════════════════════════

export const GUIAS_POR_MODULO: Record<string, GuiaItem[]> = {
    "00-navegacao": [
        {
            id: "guia-login",
            numero: 1,
            titulo: "Como fazer login e o que fazer se esquecer a senha",
            passos: [
                "Abra o navegador de internet (Chrome, Edge ou Safari) no computador, tablet ou celular.",
                "Acesse o link do sistema fornecido pela sua equipe (ex: app.deepfarms.com.br).",
                "Digite o seu e-mail cadastrado e a sua senha nos campos indicados.",
                "Clique no botão verde 'Entrar' para carregar a página inicial.",
            ],
            destaque: {
                tipo: "dica",
                texto: "Esqueceu sua senha? Na tela de entrada, clique no texto azul 'Esqueci minha senha', informe seu e-mail e você receberá um link seguro para cadastrar uma nova senha.",
            },
            tags: ["login", "entrar", "acesso", "senha", "esqueci", "recuperar", "link"],
        },
        {
            id: "guia-porteira",
            numero: 2,
            titulo: "Como alternar entre fazendas (A Regra da Porteira)",
            passos: [
                "Olhe para o topo central da tela, onde aparece o nome da propriedade atual (ex: '> Terra Nostra ▾').",
                "Clique sobre o seletor da fazenda para abrir a lista completa das suas propriedades.",
                "Selecione a fazenda desejada. O sistema recarregará na hora mostrando apenas os dados dela.",
                "Para somar o total de todas as suas fazendas em um único painel, clique em 'Visão Consolidada'.",
            ],
            destaque: {
                tipo: "alerta",
                texto: "Atenção: Antes de registrar qualquer trator, semente ou despesa, verifique sempre se o seletor central está apontando para a fazenda correta!",
            },
            tags: ["porteira", "fazenda", "propriedade", "terra nostra", "contexto", "seletor", "trocar", "consolidada"],
        },
        {
            id: "guia-busca",
            numero: 3,
            titulo: "Como achar qualquer tela em 3 segundos com a busca de menu",
            passos: [
                "No canto superior esquerdo da barra lateral, localize o campo 'Pesquisar menu...'.",
                "Digite apenas as primeiras letras do que deseja (ex: digite 'rom' para Romaneios).",
                "O menu filtra na hora somente os itens correspondentes ao termo digitado.",
                "Clique no resultado para ir diretamente para a tela, sem precisar abrir várias pastas.",
            ],
            destaque: {
                tipo: "dica",
                texto: "Atalhos rápidos: digite 'vac' para vacinas e manejos, 'desp' para despesas financeiras ou 'estoq' para saldos do almoxarifado.",
            },
            tags: ["busca", "pesquisa", "procurar", "achar", "atalho", "menu lateral", "filtro"],
        },
        {
            id: "guia-menu-estilo",
            numero: 4,
            titulo: "Como escolher entre Barra Lateral e Mega Menu",
            passos: [
                "Clique na sua foto ou iniciais no canto superior direito da tela.",
                "No menu suspenso, localize a seção 'Navegação'.",
                "Escolha 'Usar Mega Menu' se quiser que o menu se abra horizontalmente no topo, liberando mais espaço lateral na tela.",
                "Para retornar ao formato tradicional, clique novamente no seu perfil e selecione 'Usar barra lateral'.",
            ],
            tags: ["mega menu", "barra lateral", "estilo", "layout", "perfil", "navegação", "formato"],
        },
    ],

    "01-cadastros": [
        {
            id: "guia-unidade-produtiva",
            numero: 1,
            titulo: "Como cadastrar sua Unidade Produtiva (A Fazenda)",
            passos: [
                "No menu lateral esquerdo, acesse: Cadastros > Minha Propriedade > Unidades Produtivas.",
                "No canto superior direito, clique no botão com contorno verde '+ Nova Unidade'.",
                "Preencha o Nome da Propriedade (ex: Fazenda Terra Nostra) e selecione o Tipo (Fazenda, Sítio, Chácara, Arrendamento ou Parceria).",
                "Informe a Área Total em hectares (ha), e se desejar, as áreas de preservação (APP) e Reserva Legal (RL).",
                "Preencha o endereço (CEP, Município, UF) e clique no botão verde 'Salvar'.",
            ],
            destaque: {
                tipo: "dica",
                texto: "Assim que a fazenda for salva, ela ficará imediatamente disponível no Seletor de Contexto Ativo no topo da tela para você alternar quando quiser!",
            },
            tags: ["fazenda", "unidade produtiva", "propriedade", "nova unidade", "cadastrar fazenda", "área total", "hectares"],
        },
        {
            id: "guia-talhoes",
            numero: 2,
            titulo: "Como cadastrar e desenhar seus Talhões no Mapa",
            passos: [
                "No menu lateral, acesse: Cadastros > Minha Propriedade > Georreferenciamento.",
                "Certifique-se de que a fazenda correta está selecionada no topo central.",
                "Clique no botão '+ Novo Talhão'. Preencha o nome (ex: Talhão 01 - Baixada) e a área em hectares.",
                "No mapa por satélite, utilize a ferramenta de desenho (polígono) para contornar a cerca do talhão. A área é calculada automaticamente ao fechar o desenho.",
                "Clique em 'Salvar Talhão' para gravar o perímetro e o tamanho.",
            ],
            destaque: {
                tipo: "alerta",
                texto: "Atenção: A soma da área de todos os seus talhões não pode ser maior do que a área total cadastrada na fazenda.",
            },
            tags: ["talhão", "talhoes", "desenhar", "mapa", "satélite", "georreferenciamento", "polígono", "área", "divisão"],
        },
        {
            id: "guia-produtos-insumos",
            numero: 3,
            titulo: "Como cadastrar Insumos e Produtos (Catálogo de Produtos)",
            passos: [
                "No menu lateral, acesse: Cadastros > Insumos & Ativos > Catálogo de Produtos.",
                "Clique no botão '+ Novo Produto'.",
                "Preencha o Nome Comercial (ex: 'Adubo NPK 04-14-08' ou 'Óleo Diesel S10').",
                "Selecione a Categoria: Fertilizante, Defensivo, Semente, Combustível, Pecuária, Peça, etc.",
                "Selecione a Unidade de Medida correspondente: 'kg' ou 't' para adubos, 'L' para líquidos e diesel, 'sc' para sementes.",
                "Defina um Estoque Mínimo se desejar receber avisos automáticos de compra quando o galpão estiver esvaziando.",
                "Clique em 'Salvar'.",
            ],
            destaque: {
                tipo: "dica",
                texto: "Tudo o que a fazenda compra e consome (adubo, veneno, semente, sal mineral, diesel) deve ser cadastrado aqui.",
            },
            tags: ["produto", "insumo", "adubo", "semente", "diesel", "defensivo", "catálogo", "unidade de medida", "estoque mínimo"],
        },
        {
            id: "guia-equipamentos-frota",
            numero: 4,
            titulo: "Como cadastrar Máquinas, Tratores e Implementos",
            passos: [
                "No menu lateral, acesse: Cadastros > Insumos & Ativos > Equipamentos & Frota.",
                "Clique no botão '+ Novo Equipamento'.",
                "Identifique a máquina (ex: 'Trator John Deere 6110M #01').",
                "Selecione o Tipo (Trator, Colheitadeira, Pulverizador, Caminhão, Implemento) e preencha Marca e Modelo.",
                "Informe o Horímetro Inicial atual (quantas horas a máquina já trabalhou até hoje).",
                "Clique em 'Salvar'.",
            ],
            destaque: {
                tipo: "dica",
                texto: "Com a máquina cadastrada, os operadores poderão apontar suas horas de trabalho no campo e a oficina saberá a hora exata da troca de óleo preventiva!",
            },
            tags: ["trator", "máquina", "equipamento", "frota", "horímetro", "colheitadeira", "implemento", "oficina"],
        },
        {
            id: "guia-pessoas-parceiros",
            numero: 5,
            titulo: "Como cadastrar Fornecedores, Clientes e Colaboradores",
            passos: [
                "No menu lateral, acesse: Cadastros > Pessoas & Parceiros > Pessoas & Parceiros.",
                "Clique no botão '+ Nova Pessoa'.",
                "Escolha o Tipo de Relacionamento: Fornecedor (loja de adubo, posto), Cliente (cooperativa, trading), Colaborador (tratorista, encarregado) ou Prestador de Serviço.",
                "Preencha Nome / Razão Social, CPF ou CNPJ, Telefone/WhatsApp e Cidade.",
                "Clique em 'Salvar'.",
            ],
            tags: ["pessoa", "fornecedor", "cliente", "colaborador", "funcionário", "parceiro", "revenda", "cooperativa"],
        },
    ],

    "02-imoveis": [
        {
            id: "guia-cadastro-imovel",
            numero: 1,
            titulo: "Como cadastrar a Matrícula e dados do Cartório de Imóveis (CRI)",
            passos: [
                "No menu lateral esquerdo, acesse: Imóveis Rurais > Visão Geral > Imóveis Rurais.",
                "Clique no botão com contorno verde '+ Novo Imóvel'.",
                "Informe o Nome do Imóvel (ex: Gleba Santa Maria) e o Número da Matrícula no Cartório (CRI).",
                "Preencha a Comarca/Cartório, o Livro e a Folha de registro constante na certidão de inteiro teor.",
                "Informe as áreas da escritura em hectares (ha): Área Total, Área Aproveitável, APP e Reserva Legal.",
                "Selecione a Situação Documental (Regular, Pendente ou Irregular) e clique em 'Salvar Imóvel'.",
            ],
            destaque: {
                tipo: "dica",
                texto: "Este cadastro representa o documento legal e a escritura da terra perante a lei e o cartório de registro de imóveis, separando a matrícula da fazenda operacional.",
            },
            tags: ["imóvel", "matrícula", "cartório", "cri", "escritura", "gleba", "reserva legal", "app", "fundiário"],
        },
        {
            id: "guia-governo-nirf-ccir",
            numero: 2,
            titulo: "Como cadastrar números oficiais: NIRF (Receita Federal) e CCIR (INCRA)",
            passos: [
                "Abra o cadastro do Imóvel Rural em modo de edição (ícone do lápis).",
                "No campo 'NIRF', digite o código de 8 dígitos atribuído pela Receita Federal para este imóvel.",
                "No campo 'CCIR', informe o código de 13 dígitos emitido pelo INCRA que comprova a regularidade cadastral.",
                "Informe o número do recibo do CAR (Cadastro Ambiental Rural) e o código de certificação SIGEF, se possuir.",
                "Clique em 'Salvar'.",
            ],
            destaque: {
                tipo: "alerta",
                texto: "Atenção: O NIRF informado aqui é o número exigido pela Receita Federal para a emissão automática do Livro Caixa Digital do Produtor Rural (LCDPR) no financeiro!",
            },
            tags: ["nirf", "ccir", "incra", "receita federal", "car", "sigef", "governo", "lcdpr", "impostos"],
        },
        {
            id: "guia-arrendamentos",
            numero: 3,
            titulo: "Como gerenciar Contratos de Arrendamento e Parceria Agrícola",
            passos: [
                "Na tela de Imóveis Rurais, clique na aba superior 'Arrendamentos & Parcerias'.",
                "Clique no botão verde '+ Novo Contrato'.",
                "Selecione o Tipo de Contrato: Arrendamento Rural (aluguel de terra) ou Parceria Agrícola.",
                "Selecione o Arrendador (dono da terra) e o Imóvel Rural vinculado.",
                "Defina a forma de pagamento: Valor fixo em Reais (R$/ha) ou em Sacas de Grãos (ex: 12 sacas de soja/ha/ano).",
                "Informe as datas de início, término do contrato e o vencimento do pagamento anual.",
                "Clique em 'Salvar Contrato'.",
            ],
            destaque: {
                tipo: "dica",
                texto: "O sistema gera automaticamente as previsões de pagamento no Módulo Financeiro e rateia esse custo na safra correspondente.",
            },
            tags: ["arrendamento", "parceria", "contrato", "sacas de soja", "aluguel", "vencimento", "terceiros"],
        },
        {
            id: "guia-avaliacao-patrimonial",
            numero: 4,
            titulo: "Como registrar Laudos de Avaliação Patrimonial da Terra (VTN)",
            passos: [
                "No menu lateral, acesse: Imóveis Rurais > Visão Geral > Avaliação Patrimonial.",
                "Clique no botão verde '+ Nova Avaliação'.",
                "Selecione o Imóvel Rural que foi vistoriado e a Data do Laudo.",
                "Informe o Valor da Terra Nua (VTN) por hectare e o valor das benfeitorias construídas (sede, silos, cercas, represas).",
                "Anexe o laudo em PDF emitido pelo engenheiro ou corretor com CREA/CNAI.",
                "Clique em 'Salvar Avaliação'.",
            ],
            destaque: {
                tipo: "dica",
                texto: "Mantenha o histórico de laudos atualizado para comprovar patrimônio líquido em bancos e agilizar aprovações de crédito rural (CPR e Plano Safra).",
            },
            tags: ["avaliação", "patrimônio", "laudo", "terra nua", "vtn", "benfeitorias", "garantia", "banco", "crédito rural"],
        },
    ],

    "03-agricultura": [
        {
            id: "guia-criar-safra",
            numero: 1,
            titulo: "Como criar uma nova Safra e definir metas de produtividade",
            passos: [
                "No menu lateral esquerdo, acesse: Agricultura > Safras e Contexto > Safras e Painel da Safra.",
                "Clique no botão verde '+ Nova Safra'.",
                "Preencha o Nome da Safra (ex: Safra Soja Verão 2024/2025 ou Safrinha Milho 2025).",
                "Selecione a Cultura Principal (Soja, Milho, Algodão, Trigo, Café, Cana, etc.).",
                "Defina as datas previstas de início do preparo e término da colheita.",
                "Informe a Meta de Produtividade em sacas por hectare (ex: 72 sc/ha) e clique em 'Salvar'.",
            ],
            destaque: {
                tipo: "dica",
                texto: "Ao criar a safra, ela fica disponível como filtro em todas as telas agrícolas e no planejamento de custos.",
            },
            tags: ["safra", "nova safra", "cultura", "produtividade", "soja", "milho", "ciclo", "planejamento"],
        },
        {
            id: "guia-receitas-calda",
            numero: 2,
            titulo: "Como montar Receitas de Aplicação de calda no tanque (doses por hectare)",
            passos: [
                "No menu lateral, acesse: Agricultura > Planejamento > Receitas de Aplicação.",
                "Clique no botão '+ Nova Receita'.",
                "Nomeie a calda (ex: 'Dessecação Pré-Plantio' ou 'Fungicida 1ª Aplicação').",
                "Adicione os defensivos e adubos foliares com suas respectivas doses por hectare (ex: 3 L/ha de glifosato, 0,5 L/ha de óleo mineral).",
                "Defina a vazão do pulverizador (Volume de Calda em L/ha, ex: 100 L/ha).",
                "Clique em 'Salvar Receita'.",
            ],
            destaque: {
                tipo: "dica",
                texto: "Com a receita pronta, o operador na cabine do trator sabe exatamente quanto veneno colocar no tanque sem errar a dosagem!",
            },
            tags: ["receita", "calda", "pulverização", "dose", "hectare", "defensivo", "tanque", "bula"],
        },
        {
            id: "guia-caderno-campo",
            numero: 3,
            titulo: "Como registrar operações no Caderno de Campo eletrônico",
            passos: [
                "No menu lateral, acesse: Agricultura > Execução > Caderno de Campo.",
                "Clique no botão '+ Nova Operação'.",
                "Selecione o Talhão onde a operação foi realizada e a Safra correspondente.",
                "Escolha o Tipo de Atividade: Dessecação, Plantio, Adubação de Cobertura ou Pulverização.",
                "Informe o Trator utilizado, o Operador e os Insumos gastos.",
                "Registre o Horímetro da máquina (horas trabalhadas) e clique em 'Confirmar Operação'.",
            ],
            destaque: {
                tipo: "alerta",
                texto: "Atenção: Cada operação lançada no caderno dá baixa imediata no estoque de insumos e atualiza o horímetro da oficina!",
            },
            tags: ["caderno de campo", "operação", "pulverização", "plantio", "adubação", "horímetro", "trator", "diário"],
        },
        {
            id: "guia-romaneio-colheita",
            numero: 4,
            titulo: "Como emitir Romaneios de Colheita de caminhão com descontos de umidade e impureza",
            passos: [
                "No menu lateral, acesse: Agricultura > Produção > Romaneios de Colheita.",
                "Clique no botão '+ Novo Romaneio'.",
                "Selecione o Talhão de Origem da colheita e a placa do caminhão.",
                "Digite o Peso Bruto (caminhão cheio) e a Tara (caminhão vazio) medidos na balança.",
                "Informe o percentual de Umidade (%) e Impureza (%) apurados na amostragem.",
                "O sistema calcula o Peso Líquido e o total de sacas limpas e secas na hora.",
                "Selecione o destino (Silo próprio, Cooperativa ou Cerealista) e clique em 'Emitir Romaneio'.",
            ],
            destaque: {
                tipo: "dica",
                texto: "Os romaneios geram o saldo colhido da fazenda e alimentam as contas a receber no financeiro.",
            },
            tags: ["romaneio", "colheita", "caminhão", "peso bruto", "tara", "líquido", "umidade", "impureza", "sacas", "grãos"],
        },
        {
            id: "guia-ndvi-satelite",
            numero: 5,
            titulo: "Como consultar o mapa de vigor vegetativo da lavoura por satélite (NDVI)",
            passos: [
                "No menu lateral, acesse: Agricultura > Diagnóstico > Índices de Vegetação (NDVI).",
                "Selecione a Safra e o Talhão que deseja analisar.",
                "Escolha a data da passagem do satélite no calendário de imagens.",
                "Observe o mapa de calor: tons de verde escuro indicam plantas saudáveis; tons de amarelo ou vermelho indicam estresse hídrico, ataque de pragas ou falha de plantio.",
            ],
            destaque: {
                tipo: "dica",
                texto: "Use o mapa de satélite antes de ir a campo para ir direto nos pontos críticos do talhão!",
            },
            tags: ["ndvi", "satélite", "vigor", "mapa", "vegetação", "falha", "seca", "estresse", "visão aérea"],
        },
    ],

    "04-clima": [
        {
            id: "guia-janela-pulverizacao",
            numero: 1,
            titulo: "Como consultar a Previsão Agrícola e identificar Janelas Seguras de Pulverização",
            passos: [
                "No menu lateral, acesse: Clima e Previsão > Visão Geral > Previsão Agrícola.",
                "Olhe para o cartão de 'Recomendações Operacionais' no topo da tela.",
                "Verifique o Vento: deve estar entre 3 km/h e 10 km/h (acima de 10 km/h há risco grave de deriva).",
                "Verifique a Umidade do Ar: deve estar acima de 55% para o veneno não evaporar antes de tocar a folha.",
                "Verifique a Temperatura: não aplique se o mostrador indicar mais de 30°C.",
            ],
            destaque: {
                tipo: "dica",
                texto: "Se o indicador estiver verde 'Condição Excelente', aproveite para puxar a pulverização sem perda de calda!",
            },
            tags: ["clima", "pulverização", "janela", "vento", "deriva", "umidade", "temperatura", "evaporação"],
        },
        {
            id: "guia-estresse-termico-ith",
            numero: 2,
            titulo: "Como monitorar o Índice de Estresse Térmico (ITH) para proteger o gado do calor",
            passos: [
                "No menu lateral, acesse: Clima e Previsão > Visão Geral > Previsão Pecuária.",
                "Observe o mostrador do ITH: valores até 71 indicam conforto térmico.",
                "Se o ITH estiver entre 72 e 78 (Alerta Amarelo), aumente a oferta de água nos bebedouros e garanta sombra nos piquetes.",
                "Se o ITH passar de 79 (Alerta Vermelho), cancele manejos no curral nas horas mais quentes do dia para evitar perda de peso e abortos.",
            ],
            destaque: {
                tipo: "alerta",
                texto: "Atenção: Em vacas leiteiras, ITH acima de 72 pode derrubar a produção de leite em até 20% no mesmo dia!",
            },
            tags: ["ith", "estresse térmico", "gado", "pecuária", "calor", "leite", "bebedouro", "sombra"],
        },
        {
            id: "guia-gdu-graus-dia",
            numero: 3,
            titulo: "Como acompanhar os Graus-Dia Acumulados (GDU) e o estágio da lavoura",
            passos: [
                "No menu lateral, acesse: Clima e Previsão > Inteligência Agrícola > Painel Fitossanitário.",
                "Selecione a Safra e o Talhão correspondente.",
                "Veja a régua de GDU acumulada desde o plantio.",
                "O sistema avisa automaticamente a fase fenológica da planta (ex: R1 Florescimento, R5 Enchimento de Grãos).",
            ],
            destaque: {
                tipo: "dica",
                texto: "Os Graus-Dia mostram o relógio biológico real da planta pelo calor acumulado, muito mais preciso do que contar dias no calendário.",
            },
            tags: ["gdu", "graus-dia", "estágio", "fenologia", "desenvolvimento", "florescimento", "enchimento"],
        },
        {
            id: "guia-alerta-doencas",
            numero: 4,
            titulo: "Como interpretar alertas de risco de doenças foliares (Ferrugem e Manchas)",
            passos: [
                "Na tela de Inteligência Agrícola, observe a seção 'Risco de Doenças'.",
                "O sistema monitora o tempo de 'Folha Molhada' (orvalho e chuva) somado à temperatura ideal do fungo.",
                "Se o indicador apontar 'Risco Alto', o fungo da ferrugem ou mancha-alvo encontrou o clima perfeito para germinar.",
                "Planeje a entrada do fungicida preventivo antes que os sintomas apareçam na lavoura.",
            ],
            destaque: {
                tipo: "dica",
                texto: "Aplicar fungicida na hora certa pelo modelo de risco economiza aplicações desnecessárias e protege o potencial produtivo.",
            },
            tags: ["doenças", "ferrugem", "fungo", "molhamento", "orvalho", "mancha alvo", "prevenção"],
        },
    ],

    "05-estoque": [
        {
            id: "guia-pedido-compra",
            numero: 1,
            titulo: "Como emitir um Pedido de Compra e registrar itens negociados",
            passos: [
                "No menu lateral, acesse: Estoque & Suprimento > Compras > Pedidos de Compra.",
                "Clique no botão verde '+ Novo Pedido'.",
                "Selecione o Fornecedor (revenda, posto ou cooperativa) negociado.",
                "Adicione os produtos com quantidade e preço unitário acordado (ex: 200 L de diesel, 10 t de adubo).",
                "Defina as condições de pagamento e a previsão de entrega na fazenda.",
                "Clique em 'Salvar Pedido'.",
            ],
            destaque: {
                tipo: "dica",
                texto: "O pedido registrado serve como comprovante do que foi negociado, evitando cobranças com valores errados na nota fiscal.",
            },
            tags: ["compras", "pedido", "fornecedor", "cotação", "preço", "adubo", "diesel", "negociação"],
        },
        {
            id: "guia-receber-mercadoria",
            numero: 2,
            titulo: "Como receber mercadorias no galpão com conferência de nota fiscal e lote",
            passos: [
                "Quando a carga descarregar na fazenda, abra a tela de Pedidos de Compra.",
                "Localize o pedido correspondente e clique no botão 'Receber Mercadoria'.",
                "Confira a quantidade física entregue contra o número da Nota Fiscal.",
                "Informe o Número do Lote e a Data de Validade impressos nas embalagens.",
                "Escolha em qual Depósito o produto será guardado (Galpão Central, Tanque Diesel, etc.).",
                "Clique em 'Confirmar Recebimento'.",
            ],
            destaque: {
                tipo: "alerta",
                texto: "Ao confirmar o recebimento, o estoque sobe na hora e a conta a pagar é gerada automaticamente no financeiro!",
            },
            tags: ["receber", "conferência", "nota fiscal", "lote", "validade", "depósito", "galpão"],
        },
        {
            id: "guia-consultar-saldos",
            numero: 3,
            titulo: "Como consultar saldos de estoque por depósito e custo médio",
            passos: [
                "No menu lateral, acesse: Estoque & Suprimento > Estoque > Saldos de Estoque.",
                "Utilize os filtros para selecionar o Depósito ou a Categoria de produto.",
                "Veja a quantidade física disponível em estoque.",
                "Consulte o Custo Médio Unitário (R$) apurado pelo sistema para cada item.",
            ],
            destaque: {
                tipo: "dica",
                texto: "O custo médio é calculado automaticamente a cada nova compra, mantendo a contabilidade da safra sempre exata.",
            },
            tags: ["saldos", "estoque", "depósito", "custo médio", "disponível", "almoxarifado"],
        },
        {
            id: "guia-lotes-validade",
            numero: 4,
            titulo: "Como controlar lotes com data de validade para evitar produtos vencidos",
            passos: [
                "No menu lateral, acesse: Estoque & Suprimento > Estoque > Lotes de Estoque.",
                "Veja a lista de lotes organizada pela data de expiração.",
                "Lotes próximos ao vencimento (menos de 60 dias) são destacados em amarelo.",
                "Ao apontar o uso no campo, priorize a regra PEPS: use sempre o lote mais antigo primeiro!",
            ],
            destaque: {
                tipo: "dica",
                texto: "Evite prejuízos: nunca deixe defensivos ou vacinas vencerem no fundo do barracão sem uso.",
            },
            tags: ["lotes", "validade", "vencimento", "peps", "defensivos", "vacinas", "rastreabilidade"],
        },
        {
            id: "guia-requisicoes-campo",
            numero: 5,
            titulo: "Como atender requisições internas de insumos para o campo",
            passos: [
                "No menu lateral, acesse: Estoque & Suprimento > Estoque > Requisições Internas.",
                "Veja a lista de requisições pendentes abertas pelos encarregados de plantio ou oficina.",
                "Confira os itens solicitados (ex: 4 galões de óleo motor, 8 sacos de semente).",
                "Separe os produtos, anote o operador que está retirando e clique em 'Aprovar e Entregar'.",
                "O sistema debita a quantidade do galpão imediatamente.",
            ],
            destaque: {
                tipo: "dica",
                texto: "A requisição interna acaba com os sumiços de peças e galões sem responsável identificado na fazenda.",
            },
            tags: ["requisição", "entrega", "baixa", "retirada", "responsável", "almoxarife", "controle"],
        },
    ],

    "06-frota": [
        {
            id: "guia-abastecimento-diesel",
            numero: 1,
            titulo: "Como registrar Abastecimentos de Combustível e apurar o Consumo (L/h)",
            passos: [
                "No menu lateral, acesse: Frota & Manutenção > Operação > Consumo & Eficiência.",
                "Clique no botão verde '+ Novo Abastecimento'.",
                "Selecione o trator, colheitadeira ou caminhão.",
                "Informe o Horímetro Atual marcado no painel e a quantidade de Litros abastecidos.",
                "Selecione o tanque de origem (Tanque Fixo da Sede ou Caminhão Comboio) e o operador.",
                "Clique em 'Salvar Abastecimento'. O consumo em L/h é calculado instantaneamente.",
            ],
            destaque: {
                tipo: "dica",
                texto: "Se o consumo subir repentinamente sem justificativa de solo pesado, investigue vazamentos ou bicos injetores desregulados.",
            },
            tags: ["abastecimento", "diesel", "consumo", "litros por hora", "horímetro", "comboio", "combustível"],
        },
        {
            id: "guia-manutencao-preventiva",
            numero: 2,
            titulo: "Como acompanhar o plano de Manutenção Preventiva (Trocas de Óleo e Filtros)",
            passos: [
                "No menu lateral, acesse: Frota & Manutenção > Operação > Preventiva.",
                "Consulte o semáforo de cada máquina: Verde (em dia), Amarelo (faltam menos de 20h) e Vermelho (vencida).",
                "Ao realizar a revisão de 250h ou 500h, clique em 'Registrar Revisão'.",
                "Marque os itens trocados (óleo motor, filtro combustível, filtro de ar, engraxamento).",
                "O sistema zera o contador da preventiva e programa a próxima revisão automaticamente.",
            ],
            destaque: {
                tipo: "alerta",
                texto: "Fazer a preventiva em dia evita paradas catastróficas de motor no auge da janela de plantio ou colheita!",
            },
            tags: ["preventiva", "revisão", "troca de óleo", "filtro", "engraxar", "oficina", "horímetro"],
        },
        {
            id: "guia-ordem-servico-oficina",
            numero: 3,
            titulo: "Como abrir e encerrar Ordens de Serviço na oficina da fazenda",
            passos: [
                "No menu lateral, acesse: Frota & Manutenção > Operação > Manutenções.",
                "Clique em '+ Nova Manutenção' quando uma máquina quebrar ou apresentar folga.",
                "Descreva o defeito diagnosticado e selecione as peças necessárias do estoque.",
                "Aponte as horas gastas pelo mecânico da fazenda ou o valor do mecânico terceirizado.",
                "Ao finalizar o conserto, clique em 'Concluir O.S.' para liberar a máquina para o campo.",
            ],
            destaque: {
                tipo: "dica",
                texto: "O custo das peças e do serviço é somado automaticamente no custo total daquela máquina.",
            },
            tags: ["ordem de serviço", "conserto", "oficina", "peças", "mecânico", "quebra", "reparo"],
        },
    ],

    "07-pecuaria": [
        {
            id: "guia-cadastro-animais-brincos",
            numero: 1,
            titulo: "Como cadastrar animais no rebanho com brincos visuais e eletrônicos (RFID)",
            passos: [
                "No menu lateral, acesse: Pecuária > Rebanho > Meus Animais.",
                "Clique no botão verde '+ Novo Animal' (ou '+ Entrada em Lote' para muitos animais).",
                "Informe o Brinco Visual (ex: BR-1042) e o chip RFID se possuir.",
                "Selecione a Categoria (Bezerro, Garrote, Novilha, Vaca Parida, Boi Gordo) e a Raça.",
                "Preencha a data de nascimento ou idade em meses e o peso inicial em quilos.",
                "Selecione o Lote e o Piquete onde o animal ficará alojado e clique em 'Salvar'.",
            ],
            destaque: {
                tipo: "dica",
                texto: "Cada animal ganha um prontuário digital único com histórico de pesagens, vacinas e genealogia.",
            },
            tags: ["animais", "gado", "brinco", "rfid", "bezerro", "rebanho", "nelore", "angus"],
        },
        {
            id: "guia-pesagem-gmd",
            numero: 2,
            titulo: "Como registrar pesagens no brete e apurar o Ganho Médio Diário (GMD)",
            passos: [
                "Passe os animais pela balança do tronco no curral.",
                "Na tela de Meus Animais (ou na Balança TARA), registre o peso atual do animal.",
                "O sistema puxa o peso anterior e o número de dias decorridos.",
                "O Ganho Médio Diário (GMD em kg/dia) é calculado automaticamente na hora.",
            ],
            destaque: {
                tipo: "dica",
                texto: "Animais com GMD abaixo da média do lote são destacados para verificação de verminose ou troca de suplemento mineral.",
            },
            tags: ["pesagem", "gmd", "ganho de peso", "brete", "tronco", "curral", "desempenho"],
        },
        {
            id: "guia-manejos-vacinas-carencia",
            numero: 3,
            titulo: "Como lançar manejos sanitários e controlar o período de carência de remédios",
            passos: [
                "No menu lateral, acesse: Pecuária > Saúde & Nutrição > Manejos Sanitários.",
                "Clique em '+ Novo Manejo' e selecione o Lote vacinado.",
                "Selecione o Medicamento (ex: Vacina Clostridiose ou Vermífugo) e informe a dose aplicada.",
                "O sistema calcula a Data de Término da Carência sanitária do produto.",
                "Animais em período de carência ficam com alerta amarelo, bloqueando a emissão de guia de abate.",
            ],
            destaque: {
                tipo: "alerta",
                texto: "Respeitar a carência de medicamentos é exigência sanitária rigorosa do MAPA para evitar contaminação da carne e leite.",
            },
            tags: ["vacina", "manejo sanitário", "carência", "abate", "remédio", "clostridiose", "aftosa"],
        },
    ],

    "08-balanca": [
        {
            id: "guia-pesagem-caminhao-tara",
            numero: 1,
            titulo: "Como realizar a pesagem de caminhões em 2 passos (Peso Bruto e Tara)",
            passos: [
                "No menu lateral, acesse: Balança > Operação > Pesagens.",
                "O caminhão carregado sobe na plataforma rodoviária da fazenda.",
                "Quando o indicador da balança estabilizar, o sistema libera a captura do Peso Bruto.",
                "Selecione a Placa, o Motorista e o Talhão de Origem e clique em 'Gravar 1ª Pesagem'.",
                "Após o caminhão descarregar, ele retorna à balança vazio para capturar a Tara.",
                "O sistema desconta a tara e calcula o Peso Líquido da carga automaticamente.",
            ],
            destaque: {
                tipo: "dica",
                texto: "O operador não precisa digitar pesos na mão: a leitura vem direto do visor da balança física sem erro de digitação!",
            },
            tags: ["balança", "pesagem", "peso bruto", "tara", "líquido", "caminhão", "grãos", "toledo", "coimma"],
        },
        {
            id: "guia-ticket-pesagem",
            numero: 2,
            titulo: "Como emitir o Ticket de Pesagem Oficial e integrar ao Romaneio",
            passos: [
                "Ao concluir a pesagem da tara, clique em 'Emitir Ticket'.",
                "O sistema gera o comprovante oficial com número de controle, carimbo de data/hora e peso líquido.",
                "Imprima a via física para o motorista ou envie o PDF por WhatsApp.",
                "O peso líquido é enviado automaticamente para o Romaneio de Colheita (Agricultura) ou Estoque.",
            ],
            destaque: {
                tipo: "dica",
                texto: "Funciona mesmo se a fazenda ficar sem internet: as pesagens ficam na memória local e sincronizam ao restabelecer o sinal.",
            },
            tags: ["ticket", "comprovante", "romaneio", "impressão", "offline", "sincronização"],
        },
    ],

    "09-financeiro": [
        {
            id: "guia-contas-pagar-receber",
            numero: 1,
            titulo: "Como gerenciar Contas a Pagar e Contas a Receber da fazenda",
            passos: [
                "No menu lateral, acesse: Financeiro > Despesas & Custos > Minhas Despesas (ou Minhas Receitas).",
                "Acompanhe o painel de vencimentos diários para nunca pagar juros ou multas bancárias.",
                "Para despesas avulsas, clique em '+ Nova Despesa', preencha valor, vencimento, fornecedor e categoria.",
                "Ao pagar o boleto ou receber a venda de grãos/gado, clique em 'Dar Baixa' e informe a conta bancária.",
            ],
            destaque: {
                tipo: "dica",
                texto: "Boletos de compras de insumos e peças de trator entram aqui automaticamente assim que chegam na fazenda!",
            },
            tags: ["contas a pagar", "contas a receber", "despesas", "receitas", "boletos", "vencimento", "baixa"],
        },
        {
            id: "guia-conciliacao-bancaria",
            numero: 2,
            titulo: "Como fazer a Conciliação Bancária importando extratos OFX",
            passos: [
                "No menu lateral, acesse: Financeiro > Bancário > Conciliação Bancária.",
                "Baixe o arquivo de extrato no formato .OFX no Internet Banking da sua conta rural.",
                "Clique em 'Importar Extrato OFX' e selecione o arquivo baixado.",
                "O sistema compara as linhas do banco com os lançamentos da fazenda e encontra os pares automaticamente.",
                "Clique em 'Conciliar Tudo' para fechar o caixa no centavo com a realidade bancária.",
            ],
            destaque: {
                tipo: "dica",
                texto: "A conciliação bancária garante que nenhum dinheiro suma sem explicação e comprova saldos para o banco.",
            },
            tags: ["conciliação", "ofx", "extrato", "banco", "batimento", "saldo real", "conferência"],
        },
        {
            id: "guia-dre-safra-lcdpr",
            numero: 3,
            titulo: "Como emitir o DRE da Safra e gerar o arquivo do LCDPR da Receita Federal",
            passos: [
                "No menu lateral, acesse: Financeiro > Gestão Financeira > DRE Operacional.",
                "Selecione a Safra para apurar o Lucro Líquido Real (Receita Bruta - Custos Operacionais).",
                "Para a Receita Federal, acesse: Financeiro > Fiscal & Obrigações > LCDPR.",
                "Clique em 'Gerar Arquivo LCDPR'. O sistema valida as contas com o NIRF e gera o arquivo oficial para o contador.",
            ],
            destaque: {
                tipo: "alerta",
                texto: "O LCDPR é obrigatório por lei. Com as contas amarradas ao NIRF da fazenda, o arquivo é gerado sem erros em minutos.",
            },
            tags: ["dre", "lucro", "safra", "lcdpr", "livro caixa", "receita federal", "imposto de renda", "contador"],
        },
    ],

    "10-rh": [
        {
            id: "guia-cadastro-colaboradores",
            numero: 1,
            titulo: "Como cadastrar colaboradores e organizar por departamentos",
            passos: [
                "No menu lateral, acesse: Recursos Humanos > Estrutura > Colaboradores.",
                "Clique no botão verde '+ Novo Colaborador'.",
                "Preencha o Nome Completo, CPF, Cargo (Tratorista, Campeiro, Mecânico, etc.) e Salário Base.",
                "Vincule ao Departamento (Lavoura, Pecuária, Máquinas, Sede) e informe se reside na fazenda.",
                "Clique em 'Salvar Colaborador'.",
            ],
            tags: ["colaborador", "funcionário", "rh", "departamento", "tratorista", "equipe", "salário"],
        },
        {
            id: "guia-registro-ponto-folha",
            numero: 2,
            titulo: "Como controlar o Ponto diário e fechar a Folha de Pagamento",
            passos: [
                "No menu lateral, acesse: Recursos Humanos > Operação Diária > Registro de Ponto.",
                "Acompanhe as entradas, intervalos de almoço e horas extras trabalhadas pela equipe.",
                "Ao final do mês, acesse 'Folha de Pagamento' e clique em 'Processar Folha'.",
                "O sistema apura horas normais, extras, adicionais noturnos e desconta vales.",
                "Emita os holerites e envie o total líquido para o Contas a Pagar do Financeiro.",
            ],
            destaque: {
                tipo: "dica",
                texto: "O controle de ponto rural evita processos trabalhistas e comprova descansos previstos pela CLT rural.",
            },
            tags: ["ponto", "horas extras", "folha de pagamento", "holerite", "salário", "esocial"],
        },
    ],

    "11-seguranca": [
        {
            id: "guia-entrega-epis",
            numero: 1,
            titulo: "Como emitir a Ficha de Entrega de EPIs com Certificado de Aprovação (CA)",
            passos: [
                "No menu lateral, acesse: Segurança do Trabalho > Visão Geral > Painel SST.",
                "Selecione o colaborador e clique em 'Nova Entrega de EPI'.",
                "Selecione os equipamentos (Kit aplicador de veneno, botas, óculos, protetor auricular) com número do CA.",
                "Imprima a ficha digital para colher a assinatura física ou digital do trabalhador.",
                "O sistema monitora a vida útil dos filtros de respirador e avisa a hora da troca.",
            ],
            destaque: {
                tipo: "alerta",
                texto: "A ficha de EPI com CA assinada é o principal documento exigido pela fiscalização da NR-31 no campo.",
            },
            tags: ["epi", "nr-31", "nr31", "segurança", "máscara", "filtro", "ca", "fiscalização"],
        },
        {
            id: "guia-exames-aso-treinamentos",
            numero: 2,
            titulo: "Como controlar Exames Médicos (ASO) e Treinamentos Obrigatórios",
            passos: [
                "No Painel SST, acompanhe a coluna de Exames Ocupacionais (ASO).",
                "Monitore a data dos exames periódicos e dos testes de colinesterase para aplicadores de defensivos.",
                "Cadastre os certificados dos cursos obrigatórios: NR-31.12 (Tratores) e NR-31.7 (Agrotóxicos).",
                "O sistema impede que operadores sem curso válido sejam escalados para máquinas perigosas.",
            ],
            tags: ["aso", "exame médico", "colinesterase", "treinamento", "nr-31.12", "capacitação", "saúde"],
        },
    ],

    "12-ambiental": [
        {
            id: "guia-importar-car",
            numero: 1,
            titulo: "Como importar o CAR e gerenciar o balanço de APP e Reserva Legal",
            passos: [
                "No menu lateral, acesse: Ambiental > CAR & Áreas > Importar CAR.",
                "Envie o arquivo digital do CAR emitido pelo órgão ambiental ou informe o número do recibo.",
                "O sistema faz a leitura geométrica e preenche a Área Total, APP, Reserva Legal e Área Consolidada.",
                "Acompanhe o balanço de vegetação para garantir que a propriedade atenda às exigências do Código Florestal.",
            ],
            tags: ["car", "código florestal", "app", "reserva legal", "meio ambiente", "recibo sicar"],
        },
        {
            id: "guia-outorgas-satelite",
            numero: 2,
            titulo: "Como controlar Outorgas de Água e monitorar Alertas de Queimadas",
            passos: [
                "No menu lateral, acesse: Ambiental > CAR & Áreas > Outorgas Hídricas.",
                "Cadastre a licença de captação de água para pivôs centrais ou confinamento com a data de vencimento.",
                "Em 'Monitoramento', visualize o mapa por satélite com alertas do INPE (focos de calor e desmatamento).",
                "Emita o Passaporte Verde da fazenda para comprovar conformidade com tradings e compradores europeus (EUDR).",
            ],
            destaque: {
                tipo: "dica",
                texto: "O Passaporte Verde comprova que a fazenda está livre de embargos e apta para vender com melhores preços de mercado.",
            },
            tags: ["outorga", "água", "irrigação", "satélite", "queimadas", "inpe", "passaporte verde", "eudr", "esg"],
        },
    ],

    "13-ia": [
        {
            id: "guia-copiloto-perguntas",
            numero: 1,
            titulo: "Como conversar com o Copiloto IA e fazer perguntas sobre a fazenda",
            passos: [
                "No menu lateral, acesse: Copiloto IA > Dashboard > Painel de IA.",
                "No campo de mensagem, digite dúvidas operacionais como se falasse com um consultor sênior.",
                "Exemplos: 'Qual talhão teve o maior custo de diesel?', 'Quantas sacas faltam colher?', 'Quais vacinas vencem no mês?'.",
                "O Copiloto analisa os dados oficiais da sua fazenda e responde com tabelas, gráficos e conclusões diretas.",
            ],
            destaque: {
                tipo: "dica",
                texto: "A IA enxerga apenas os dados da sua propriedade com total sigilo e segurança jurídica.",
            },
            tags: ["copiloto", "ia", "inteligência artificial", "perguntas", "assistente", "análise de dados"],
        },
        {
            id: "guia-recomendacoes-resumo-safra",
            numero: 2,
            titulo: "Como analisar Recomendações de Economia e gerar o Resumo da Safra",
            passos: [
                "Acesse 'Recomendações Operacionais' para ver oportunidades de corte de custos detectadas pela IA.",
                "Ao final da safra, acesse 'Resumo IA Safra' e clique em 'Gerar Resumo Executivo'.",
                "O sistema redige um relatório completo com o desempenho produtivo e financeiro da safra pronto para apresentar a sócios e bancos.",
            ],
            tags: ["recomendações", "economia", "resumo executivo", "relatório", "planejamento"],
        },
    ],

    "14-campo-pwa": [
        {
            id: "guia-instalar-campo-pwa",
            numero: 1,
            titulo: "Como instalar o aplicativo Campo PWA no celular ou tablet",
            passos: [
                "Abra o navegador do celular (Chrome no Android ou Safari no iPhone) e acesse o endereço da fazenda.",
                "Toque no aviso 'Adicionar à tela inicial' ou 'Instalar Aplicativo'.",
                "O ícone da DeepFarms aparecerá na grade de aplicativos do celular, pronto para abrir em tela cheia.",
                "Faça login uma única vez conectado ao Wi-Fi da sede para descer os dados iniciais.",
            ],
            destaque: {
                tipo: "dica",
                texto: "Não precisa de senha de loja da Google Play ou Apple Store: instala em 5 segundos!",
            },
            tags: ["campo pwa", "celular", "tablet", "instalar", "aplicativo", "tela inicial", "app"],
        },
        {
            id: "guia-operar-offline-sincronizar",
            numero: 2,
            titulo: "Como apontar atividades 100% sem internet e sincronizar na volta",
            passos: [
                "No meio da roça sem internet, abra o aplicativo e selecione sua tarefa ou aponte o serviço executado.",
                "Anote o trator, o talhão, os litros de diesel ou o gado vacinado.",
                "O aplicativo grava tudo no armazenamento interno seguro do aparelho com o aviso 'Modo Offline'.",
                "Ao retornar ao barracão da sede ou aproximar do roteador Wi-Fi, o aplicativo sincroniza tudo sozinho com o escritório!",
            ],
            destaque: {
                tipo: "dica",
                texto: "Se a bateria do celular acabar no campo, nenhuma anotação se perde: tudo fica salvo na memória do aparelho.",
            },
            tags: ["offline", "sem internet", "sincronizar", "apontamento", "roça", "campo", "tratorista"],
        },
    ],

    "15-gestao-acesso": [
        {
            id: "guia-convidar-equipe",
            numero: 1,
            titulo: "Como convidar novos membros para a equipe e definir fazendas autorizadas",
            passos: [
                "No menu lateral, acesse: Gestão de Acesso > Equipe (ou acesse /dashboard/settings/team).",
                "Clique no botão verde no canto superior '+ Convidar Membro'.",
                "Preencha o Nome Completo e o E-mail de trabalho do colaborador.",
                "Selecione o Perfil de Acesso (Administrador, Gerente, Agrônomo, Encarregado, Operador ou Contador).",
                "Em 'Fazendas Autorizadas', marque apenas a fazenda onde ele trabalha ou marque 'Todas as Fazendas'.",
                "Clique em 'Enviar Convite'. O membro receberá um e-mail com link de ativação para cadastrar sua senha.",
            ],
            destaque: {
                tipo: "dica",
                texto: "Se um colaborador for desligado da fazenda, clique em 'Suspender Acesso' na lista. O acesso dele no computador e no celular é bloqueado no mesmo instante!",
            },
            tags: ["convite", "equipe", "usuário", "membro", "adicionar", "acesso", "fazendas autorizadas", "bloqueio"],
        },
        {
            id: "guia-perfis-permissoes",
            numero: 2,
            titulo: "Como gerenciar Perfis e a Matriz de Permissões (quem pode ver custos e quem só anota)",
            passos: [
                "No menu lateral, acesse: Gestão de Acesso > Perfis & Permissões (/dashboard/settings/roles).",
                "Consulte os perfis existentes (Administrador, Gerente, Operador de Balança, Almoxarife, etc.).",
                "Para criar um novo papel, clique em '+ Novo Perfil' e defina o nome (ex: 'Operador de Trator').",
                "Na matriz de caixas de seleção, marque exatamente o que esse perfil pode Ver, Criar, Editar ou Excluir.",
                "Exemplo de segurança: desmarque 'Financeiro' para que o operador registre serviços sem ver extratos bancários.",
                "Clique em 'Salvar Perfil'.",
            ],
            destaque: {
                tipo: "alerta",
                texto: "A Regra da Chave Certa: cada colaborador só enxerga os módulos necessários para o seu trabalho, protegendo o sigilo financeiro da fazenda.",
            },
            tags: ["perfil", "permissões", "matriz", "papel", "restringir", "sigilo", "financeiro", "segurança"],
        },
        {
            id: "guia-seguranca-2fa",
            numero: 3,
            titulo: "Como ativar a Autenticação em 2 Fatores (2FA) no celular",
            passos: [
                "No menu de configurações do usuário, acesse: Segurança (/dashboard/settings/seguranca).",
                "Em 'Autenticação em Duas Etapas (2FA)', clique em 'Ativar 2FA'.",
                "Abra o aplicativo autenticador no celular (Google Authenticator ou Microsoft Authenticator) e escaneie o QR Code.",
                "Digite o código de 6 dígitos gerado no celular para confirmar a ativação.",
            ],
            destaque: {
                tipo: "dica",
                texto: "Com o 2FA ativo, mesmo que alguém descubra a sua senha, não conseguirá entrar na fazenda sem o código do seu celular.",
            },
            tags: ["2fa", "dois fatores", "segurança", "qr code", "invasão", "celular", "autenticador"],
        },
        {
            id: "guia-sessoes-ativas",
            numero: 4,
            titulo: "Como monitorar Sessões Ativas e desconectar aparelhos antigos à distância",
            passos: [
                "No menu lateral, acesse: Gestão de Acesso > Sessões Ativas (/dashboard/settings/sessoes).",
                "Veja a lista com todos os computadores, tablets e celulares conectados com horário e cidade.",
                "Se esqueceu o sistema logado em outro local ou perdeu um celular, clique em 'Desconectar Todas as Outras Sessões'.",
                "O sistema encerra imediatamente todos os logins ativos, exigindo nova senha.",
            ],
            tags: ["sessões", "desconectar", "remoto", "aparelhos", "segurança", "lan house"],
        },
    ],

    "16-configuracoes": [
        {
            id: "guia-dados-produtor-logotipo",
            numero: 1,
            titulo: "Como cadastrar dados do Produtor Titular e incluir o Logotipo Oficial em relatórios",
            passos: [
                "No menu lateral, acesse: Configurações > Meu Produtor (/dashboard/settings/tenant).",
                "Preencha o Nome Fantasia da Fazenda ou do Grupo Agropecuário (ex: 'Grupo AgroSaaS — Fazendas Reunidas').",
                "Informe a Razão Social, CNPJ ou CPF do titular e o número da Inscrição Estadual (IE).",
                "No campo 'Logotipo Oficial', envie uma imagem nítida com fundo transparente ou branco (.png ou .jpg).",
                "Clique em 'Salvar Alterações'.",
            ],
            destaque: {
                tipo: "dica",
                texto: "O logotipo enviado aparecerá automaticamente no topo dos Romaneios de Colheita, Tickets da Balança TARA, Ordens de Serviço e Relatórios em PDF!",
            },
            tags: ["produtor", "logotipo", "logo", "marca", "cnpj", "cpf", "inscrição estadual", "relatórios", "cabeçalho"],
        },
        {
            id: "guia-wizard-implantacao",
            numero: 2,
            titulo: "Como utilizar o Wizard de Implantação Assistida para parametrizar a fazenda do zero",
            passos: [
                "No menu lateral, acesse: Configurações > Wizard de Implantação (/dashboard/implantacao/wizard).",
                "Siga o fluxo guiado em 5 etapas rápidas:",
                "1) Confirme os dados cadastrais da propriedade sede.",
                "2) Desenhe ou informe os primeiros talhões produtivos.",
                "3) Cadastre as máquinas principais e horímetros iniciais.",
                "4) Crie a primeira Safra ativa.",
                "5) Convide os primeiros operadores da equipe.",
                "Ao concluir, a fazenda estará 100% pronta para registrar operações de campo e estoque!",
            ],
            destaque: {
                tipo: "dica",
                texto: "O Wizard é o caminho mais rápido para novas fazendas que acabaram de contratar a DeepFarms.",
            },
            tags: ["wizard", "implantação", "primeiros passos", "assistente", "configuração inicial"],
        },
        {
            id: "guia-configuracoes-globais",
            numero: 3,
            titulo: "Como definir as Configurações Globais (Ano Agrícola, Unidade ha/alqueire e Moeda)",
            passos: [
                "No menu lateral, acesse: Configurações > Configurações Globais (/dashboard/configuracoes/globais).",
                "Selecione o Ano Agrícola Padrão ativo da fazenda (ex: '2024/2025').",
                "Defina a Unidade de Área Padrão: Hectares (ha), Alqueire Paulista (2,42 ha), Mineiro/Goiano (4,84 ha) ou Baiano (9,68 ha).",
                "Configure o padrão de moeda e casas decimais para relatórios.",
                "Clique em 'Salvar Configurações'.",
            ],
            tags: ["globais", "ano agrícola", "hectares", "alqueires", "moeda", "decimais", "parâmetros"],
        },
        {
            id: "guia-integracoes-externas",
            numero: 4,
            titulo: "Como configurar Integrações Externas (Balança TARA, Radar Climático OpenWeather e ERP)",
            passos: [
                "Acesse a seção de Integrações correspondente no menu de Configurações.",
                "Para Balança TARA (/dashboard/settings/integracoes/tara): configure o IP ou porta serial do indicador da balança física.",
                "Para Clima OpenWeather (/dashboard/settings/integracoes/clima/openweather): insira a chave de API para atualização dos radares.",
                "Para ERP Contábil (/dashboard/settings/integracoes/erp): ative o conector com seu sistema contábil para sincronização de notas.",
                "Clique em 'Testar Conexão' para validar a estabilidade da comunicação.",
            ],
            destaque: {
                tipo: "alerta",
                texto: "A integração com a Balança TARA opera com buffer de contingência offline: mesmo sem internet, nenhuma pesagem se perde!",
            },
            tags: ["integrações", "balança", "tara", "clima", "openweather", "erp", "conector", "api"],
        },
        {
            id: "guia-plano-faturas-ia",
            numero: 5,
            titulo: "Como gerenciar o Plano de Assinatura, Faturas e Acompanhar Limites de Consumo",
            passos: [
                "No menu lateral, acesse: Configurações > Assinatura e Pagamentos (/dashboard/settings/billing).",
                "Consulte o plano contratado (Básico, Profissional ou Enterprise) e limites de hectares e usuários.",
                "Baixe as faturas mensais, boletos bancários e notas fiscais de serviço emitidas.",
                "Em 'Uso de IA' (/dashboard/settings/ia), consulte o saldo de créditos e consumo do Copiloto IA da sua fazenda.",
            ],
            tags: ["plano", "assinatura", "fatura", "boleto", "limite", "hectares", "créditos ia", "copiloto"],
        },
        {
            id: "guia-configuracao-smtp",
            numero: 6,
            titulo: "Como configurar o servidor de E-mail (SMTP) com o domínio da fazenda",
            passos: [
                "No menu lateral, acesse: Configurações > Configuração de E-mail (/dashboard/settings/smtp).",
                "Preencha o servidor SMTP, porta, usuário e senha do e-mail da sua fazenda (ex: contato@fazendasantamaria.com.br).",
                "Clique em 'Enviar E-mail de Teste' para verificar a autenticação.",
                "Com isso, todos os relatórios e romaneios enviados aos clientes sairão com o seu próprio e-mail corporativo!",
            ],
            tags: ["smtp", "e-mail", "servidor", "notificações", "domínio", "envio"],
        },
    ],

    "17-jornadas": [
        {
            id: "guia-jornada-lavoura",
            numero: 1,
            titulo: "Jornada Matinal na Lavoura — Da checagem do clima à saída das máquinas",
            passos: [
                "06h00: O gerente abre a Previsão Agrícola (Módulo 04) e valida vento e umidade para a janela de pulverização.",
                "06h30: O tratorista retira o defensivo no Almoxarifado via Requisição Interna (Módulo 05).",
                "06h45: Abastece o trator na bomba da sede e anota o horímetro e litros no Módulo 06 (Frota).",
                "07h00 às 17h00: Aplica no talhão anotando tudo no aplicativo Campo PWA (Módulo 14) sem precisar de internet.",
                "17h30: Na volta à sede, o celular conecta ao Wi-Fi: o Caderno de Campo (Módulo 03) atualiza e o estoque é baixado sozinho!",
            ],
            destaque: {
                tipo: "dica",
                texto: "O fluxo integrado garante que nenhum defensivo suma do galpão e que o custo do talhão reflita o diesel e a calda reais.",
            },
            tags: ["jornada", "lavoura", "rotina", "pulverização", "diesel", "caderno de campo", "dia a dia"],
        },
        {
            id: "guia-jornada-curral",
            numero: 2,
            titulo: "Jornada de Manejo no Curral — Da apartação à balança TARA e vacinas",
            passos: [
                "07h00: O capataz reúne o lote no piquete (Módulo 07) e conduz a tropa para o mangueiro.",
                "08h00: O gado passa pela Balança TARA (Módulo 08). O peso entra direto no sistema e calcula o GMD (kg/dia) na hora.",
                "09h30: O veterinário aplica o vermífugo. O sistema dá baixa nas doses no Estoque (Módulo 05) e calcula a carência de abate.",
                "11h00: O lote retorna ao pasto descansado com prontuário digital 100% atualizado sem papelada.",
            ],
            tags: ["jornada", "curral", "pesagem", "gmd", "vacina", "carência", "piquete", "pecuária"],
        },
        {
            id: "guia-jornada-colheita",
            numero: 3,
            titulo: "Jornada de Expedição de Grãos — Do bitrem na roça ao romaneio e financeiro",
            passos: [
                "O caminhão carregado na roça sobe na Balança Rodoviária TARA (Módulo 08) para capturar o Peso Bruto.",
                "O classificador mede umidade (15%) e impureza (1,5%).",
                "Após descarregar na moega, o caminhão retorna vazio para aferir a Tara.",
                "O sistema calcula as sacas limpas e secas e gera o Romaneio de Colheita (Módulo 03).",
                "O romaneio sobe o saldo colhido e gera a previsão de recebimento no Financeiro (Módulo 09)!",
            ],
            tags: ["jornada", "colheita", "expedição", "grãos", "caminhão", "balança", "romaneio", "financeiro"],
        },
        {
            id: "guia-jornada-escritorio",
            numero: 4,
            titulo: "Fechamento do Dia no Escritório — Da conciliação bancária aos relatórios da safra",
            passos: [
                "17h00: O administrativo confere as contas que vencem hoje e dá baixa nos pagamentos efetuados.",
                "17h30: Importa o extrato OFX do banco rural para conciliar as linhas com 1 clique.",
                "18h00: Emite o DRE da safra para acompanhar a margem de lucro por hectare e por saca colhida.",
                "18h15: Consulta o Copiloto IA (Módulo 13) para receber o resumo das operações do dia e alertas para amanhã.",
            ],
            tags: ["jornada", "escritório", "fechamento", "conciliação", "dre", "copiloto", "gestão"],
        },
    ],
};

// ═══════════════════════════════════════════════════════════════════════════════
// ELEMENTOS VISUAIS DA TELA POR MÓDULO (LUCIDE ICONS OFICIAIS)
// ═══════════════════════════════════════════════════════════════════════════════

export const ELEMENTOS_POR_MODULO: Record<string, ElementoItem[]> = {
    "00-navegacao": [
        { id: "produtor-ativo", icone: Building2, label: "Produtor Ativo (Grupo AgroSaaS)", local: "Barra Superior", descricao: "O ícone da maleta mostra a empresa ou conta titular conectada. Clicando nela, você troca de titular sem deslogar.", tags: ["maleta", "produtor", "empresa", "titular"] },
        { id: "fazenda-ativa", icone: MapPin, label: "Fazenda Ativa (> Terra Nostra)", local: "Barra Superior", descricao: "Indica a propriedade rural em operação física. Permite alternar fazendas ou escolher a 'Visão Consolidada'.", tags: ["fazenda", "terra nostra", "contexto", "unidade"] },
        { id: "acoes-rapidas", icone: PlusCircle, label: "Botão '+ Adicionar' (Ações Rápidas)", local: "Barra Superior", descricao: "Botão com contorno verde no topo para criar novos registros imediatos sem procurar no menu.", tags: ["adicionar", "atalho", "novo", "botão verde"] },
        { id: "clima-widget", icone: CloudSun, label: "Clima ao Vivo (26°C / 58% Umidade)", local: "Barra Superior", descricao: "Temperatura, umidade relativa do ar e probabilidade de chuva ao vivo baseadas na localização exata da fazenda.", tags: ["clima", "tempo", "temperatura", "chuva"] },
        { id: "tema-escuro", icone: Moon, label: "Modo Noturno / Tema Escuro", local: "Barra Superior", descricao: "Alterna as cores para fundo escuro ou claro, garantindo conforto visual no escritório ou no campo à noite.", tags: ["tema", "escuro", "claro", "noturno"] },
        { id: "notificacoes-bell", icone: Bell, label: "Notificações & Alertas (Badge 9+)", local: "Barra Superior", descricao: "Avisa sobre tarefas pendentes, vacinas a vencer e notas fiscais.", tags: ["notificação", "sino", "alerta"] },
        { id: "visao-dia-parou", icone: Clock, label: "Continuar de onde parou", local: "Área Central", descricao: "Mostra as últimas páginas visitadas na fazenda para você retornar a elas com um único clique.", tags: ["continuar", "histórico", "recentes"] },
        { id: "visao-dia-painel", icone: BookOpen, label: "Meu Painel (Personalizável)", local: "Área Central", descricao: "Cartões de acesso rápido que você pode clicar e arrastar para organizar como preferir.", tags: ["meu painel", "personalizar", "arrastar"] },
        { id: "visao-dia-copiloto", icone: Sparkles, label: "Configure seu Copiloto IA", local: "Área Central", descricao: "Atalho para o assistente de inteligência artificial da fazenda.", tags: ["copiloto", "ia", "assistente"] },
        { id: "visao-dia-acoes", icone: Zap, label: "Ações Rápidas Centrais", local: "Área Central", descricao: "Botões de acesso direto aos módulos mais movimentados da fazenda.", tags: ["ações", "botões", "módulos"] },
        { id: "visao-dia-atencao", icone: AlertTriangle, label: "Precisa de Atenção (Alertas)", local: "Área Central", descricao: "Monitor oficial de alertas em tempo real indicando severidade máxima e o domínio mais crítico da fazenda.", tags: ["atenção", "alertas", "crítico"] },
    ],

    "01-cadastros": [
        { id: "btn-nova-unidade", icone: PlusCircle, label: "Botão '+ Nova Unidade'", local: "Barra Superior", descricao: "Abre o formulário para registrar uma nova propriedade, sítio ou área arrendada na sua conta.", tags: ["nova unidade", "adicionar fazenda"] },
        { id: "mapa-talhoes", icone: MapPin, label: "Mapa de Georreferenciamento", local: "Área Central", descricao: "Visualização por satélite em alta definição com ferramentas para desenhar e medir os talhões da fazenda.", tags: ["mapa", "satélite", "desenho", "talhões"] },
        { id: "catalogo-categorias", icone: Warehouse, label: "Categorias de Produtos", local: "Área Central", descricao: "Abas de separação para Fertilizantes, Defensivos, Sementes, Combustíveis, Pecuária e Peças.", tags: ["categorias", "adubo", "semente", "produtos"] },
        { id: "frota-horimetro", icone: Tractor, label: "Controle de Horímetro da Máquina", local: "Área Central", descricao: "Mostrador do total de horas acumuladas de cada trator para alimentar as manutenções da oficina.", tags: ["horímetro", "horas", "trator", "oficina"] },
        { id: "pessoas-tipos", icone: Users, label: "Vínculos de Relacionamento", local: "Área Central", descricao: "Separação clara entre Fornecedores de insumos, Clientes compradores da colheita e Colaboradores.", tags: ["fornecedor", "cliente", "equipe"] },
    ],

    "02-imoveis": [
        { id: "btn-novo-imovel", icone: PlusCircle, label: "Botão '+ Novo Imóvel'", local: "Barra Superior", descricao: "Abre o formulário para registrar uma nova matrícula ou certidão de cartório com NIRF e INCRA.", tags: ["novo imóvel", "matrícula", "cartório"] },
        { id: "situacao-documental", icone: CheckCircle2, label: "Situação Documental (Regular / Pendente)", local: "Área Central", descricao: "Sinalizador visual indicando se a documentação da matrícula está 100% em dia ou se há pendências.", tags: ["regular", "pendente", "situação"] },
        { id: "aba-arrendamentos", icone: FileText, label: "Aba Arrendamentos & Parcerias", local: "Área Central", descricao: "Tabela de controle dos contratos de aluguel de terra com valores fixos em R$ ou sacas de soja por hectare.", tags: ["arrendamento", "parceria", "contratos"] },
        { id: "areas-escritura", icone: Ruler, label: "Quadro de Áreas (Total, Aproveitável, APP e RL)", local: "Área Central", descricao: "Demonstrativo detalhado em hectares das áreas produtivas e de preservação legal daquela matrícula.", tags: ["área total", "app", "reserva legal"] },
        { id: "laudo-vtn", icone: TrendingUp, label: "Histórico de Avaliação Patrimonial", local: "Área Central", descricao: "Gráfico e lista de evolução do valor por hectare da terra ao longo dos anos para fins de garantia bancária.", tags: ["avaliação", "patrimônio", "vtn"] },
    ],

    "03-agricultura": [
        { id: "seletor-safra", icone: Layers, label: "Seletor de Safra Ativa", local: "Barra Superior", descricao: "Filtro principal que define o ciclo de produção em análise em todos os relatórios da fazenda.", tags: ["safra", "ciclo", "filtro"] },
        { id: "btn-nova-operacao", icone: PlusCircle, label: "Botão '+ Nova Operação'", local: "Área Central", descricao: "Abre a tela de apontamento de plantio, adubação ou pulverização no Caderno de Campo.", tags: ["nova operação", "caderno de campo", "adicionar"] },
        { id: "badge-caderno-atrasado", icone: AlertTriangle, label: "Aviso de Caderno Desatualizado", local: "Área Central", descricao: "Sinalizador que acende em vermelho caso a fazenda fique mais de 7 dias sem lançamentos na safra.", tags: ["caderno atrasado", "alerta", "vermelho"] },
        { id: "mapa-ndvi", icone: Satellite, label: "Mapa de Vigor NDVI por Satélite", local: "Área Central", descricao: "Visualização espacial da lavoura em alta resolução com cores indicando a saúde das plantas.", tags: ["ndvi", "satélite", "vigor"] },
        { id: "calculadora-romaneio", icone: Calculator, label: "Cálculo de Descontos (Umidade & Impureza)", local: "Área Central", descricao: "Mecanismo oficial que desconta a água e sujeira do caminhão para achar o peso líquido de grãos.", tags: ["romaneio", "desconto", "umidade", "peso líquido"] },
        { id: "custo-saca-rentabilidade", icone: TrendingUp, label: "Painel de Custo por Saca (R$/sc)", local: "Área Central", descricao: "Indicador que divide todo o gasto da lavoura pelas sacas colhidas, mostrando a margem de lucro.", tags: ["custo por saca", "rentabilidade", "margem"] },
    ],

    "04-clima": [
        { id: "recomendacoes-ao-vivo", icone: CheckCircle2, label: "Recomendações Operacionais ao Vivo", local: "Barra Superior", descricao: "Sinalizador em tempo real (Excelente, Marginal ou Inadequado) para pulverização, plantio e colheita.", tags: ["recomendações", "ao vivo", "pulverização"] },
        { id: "termometro-umidade", icone: Thermometer, label: "Termômetro & Umidade Relativa do Ar", local: "Área Central", descricao: "Leitura instantânea da temperatura (°C) e umidade (%) captadas nas coordenadas da fazenda.", tags: ["temperatura", "umidade", "calor"] },
        { id: "vento-anemometro", icone: Wind, label: "Velocidade e Risco de Deriva do Vento", local: "Área Central", descricao: "Velocidade do vento em km/h e aviso se as rajadas impedem a operação segura do pulverizador.", tags: ["vento", "deriva", "anemômetro"] },
        { id: "monitor-ith-pecuaria", icone: Droplets, label: "Monitor ITH de Conforto Bovino", local: "Área Central", descricao: "Índice de Temperatura e Umidade que monitora o risco de estresse térmico em gado de corte e leite.", tags: ["ith", "estresse térmico", "gado"] },
        { id: "btn-sync-clima", icone: RefreshCcw, label: "Botão 'Sincronizar Agora' (Satélite & Radar)", local: "Barra Superior", descricao: "Força a atualização imediata dos dados de previsão com os modelos meteorológicos mais recentes.", tags: ["sincronizar", "atualizar", "radar"] },
    ],

    "05-estoque": [
        { id: "btn-novo-pedido", icone: PlusCircle, label: "Botão '+ Novo Pedido de Compra'", local: "Barra Superior", descricao: "Abre a tela de emissão de ordem de compra formal com cotação e prazos de entrega.", tags: ["novo pedido", "compras", "adicionar"] },
        { id: "painel-saldos-deposito", icone: Warehouse, label: "Saldos por Depósito (Almoxarifado & Tanque)", local: "Área Central", descricao: "Cartões de visualização rápida da quantidade de insumos disponíveis em cada barracão.", tags: ["saldos", "depósito", "galpão", "tanque"] },
        { id: "badge-estoque-minimo", icone: AlertTriangle, label: "Badge de Ponto de Reposição (Estoque Mínimo)", local: "Área Central", descricao: "Aviso em vermelho indicando que o saldo do galpão ficou abaixo do limite seguro para a operação.", tags: ["estoque mínimo", "repor", "alerta"] },
        { id: "tabela-lotes-validade", icone: Layers, label: "Tabela de Lotes com Validade", local: "Área Central", descricao: "Lista de rastreabilidade de cada lote de semente, defensivo ou vacina com data de expiração.", tags: ["lotes", "validade", "expiração"] },
        { id: "requisicoes-pendentes", icone: ClipboardList, label: "Painel de Requisições Internas", local: "Área Central", descricao: "Lista de pedidos de materiais feitos pelas equipes de campo para liberação pelo almoxarife.", tags: ["requisições", "pedidos internos", "liberação"] },
    ],

    "06-frota": [
        { id: "status-frota", icone: Tractor, label: "Indicador de Disponibilidade da Frota (%)", local: "Barra Superior", descricao: "Percentual de máquinas prontas para trabalhar versus máquinas imobilizadas na oficina.", tags: ["disponibilidade", "frota", "status"] },
        { id: "btn-abastecimento", icone: Droplets, label: "Botão '+ Novo Abastecimento'", local: "Área Central", descricao: "Lançamento rápido de litros de diesel e horímetro captado na bomba ou caminhão comboio.", tags: ["abastecimento", "diesel", "litros"] },
        { id: "semaforo-preventiva", icone: Wrench, label: "Semáforo da Manutenção Preventiva", local: "Área Central", descricao: "Alertas coloridos para troca de óleo e filtros aos 50h, 250h e 500h de trabalho.", tags: ["preventiva", "revisão", "troca de óleo"] },
        { id: "ordens-servico", icone: ShieldAlert, label: "Painel de Ordens de Serviço (O.S.)", local: "Área Central", descricao: "Histórico de quebras, peças trocadas e tempo de máquina parada para reparo.", tags: ["ordem de serviço", "reparo", "quebra"] },
    ],

    "07-pecuaria": [
        { id: "contador-rebanho", icone: Beef, label: "Total de Cabeças & Taxa de Lotação (UA/ha)", local: "Barra Superior", descricao: "Contagem oficial de animais por categoria e pressão de pastejo nos piquetes da fazenda.", tags: ["cabeças", "rebanho", "lotação", "ua"] },
        { id: "btn-novo-animal", icone: PlusCircle, label: "Botão '+ Novo Animal' / Entrada em Lote", local: "Área Central", descricao: "Ficha cadastral de bovinos com número de brinco visual, chip RFID e genealogia.", tags: ["brinco", "novo animal", "rfid"] },
        { id: "alerta-carencia", icone: Syringe, label: "Painel de Carência de Medicamentos", local: "Área Central", descricao: "Alerta de segurança sanitária com contagem regressiva de dias até a liberação do abate.", tags: ["carência", "remédio", "vacina", "abate"] },
        { id: "gmd-pesagem", icone: TrendingUp, label: "Calculadora de GMD (Ganho Médio Diário)", local: "Área Central", descricao: "Desempenho zootécnico em quilos por dia apurado entre duas passagens pela balança.", tags: ["gmd", "ganho de peso", "zootécnico"] },
        { id: "tanque-leite", icone: Milk, label: "Controle do Tanque de Leite", local: "Área Central", descricao: "Litros diários resfriados no tanque e indicadores de qualidade bacteriológica (CCS/CBT).", tags: ["leite", "tanque", "ccs", "cbt"] },
    ],

    "08-balanca": [
        { id: "indicador-estabilidade", icone: Scale, label: "Visor de Peso Estabilizado", local: "Barra Superior", descricao: "Sinalizador que valida se a carga parou de oscilar na plataforma antes de autorizar a gravação.", tags: ["peso", "visor", "estabilidade"] },
        { id: "captura-bruto-tara", icone: Calculator, label: "Botoeira 'Capturar Bruto' e 'Capturar Tara'", local: "Área Central", descricao: "Comandos de 1 clique que leem a balança física e apuram o peso líquido da carga de grãos.", tags: ["bruto", "tara", "captura", "balança"] },
        { id: "ticket-digital", icone: FileText, label: "Gerador de Ticket de Pesagem Oficial", local: "Área Central", descricao: "Emissor do comprovante com número sequencial inviolável e carimbo de data e hora.", tags: ["ticket", "comprovante", "pesagem"] },
        { id: "status-offline-tara", icone: RefreshCcw, label: "Buffer de Contingência Offline", local: "Barra Superior", descricao: "Garante pesagens contínuas na safra mesmo que a internet da sede esteja fora do ar.", tags: ["offline", "contingência", "sem internet"] },
    ],

    "09-financeiro": [
        { id: "saldo-bancario-consolidado", icone: Wallet, label: "Saldos em Contas e Fluxo de Caixa", local: "Barra Superior", descricao: "Total líquido disponível somando todas as contas bancárias e aplicações da fazenda.", tags: ["saldo", "banco", "fluxo de caixa"] },
        { id: "radar-vencimentos", icone: Clock, label: "Radar de Contas a Pagar e Receber", local: "Área Central", descricao: "Separador de contas que vencem hoje, na semana e no mês com alertas de juros.", tags: ["vencimentos", "contas a pagar", "receber"] },
        { id: "importador-ofx", icone: FileSpreadsheet, label: "Conciliação Bancária OFX Automática", local: "Área Central", descricao: "Ferramenta de batimento de extratos bancários com inteligência de cruzamento de boletos.", tags: ["ofx", "extrato", "conciliação"] },
        { id: "painel-dre-safra", icone: TrendingUp, label: "DRE Oficial por Safra e Hectare", local: "Área Central", descricao: "Demonstrativo com receita bruta, custos operacionais e margem líquida por saca colhida.", tags: ["dre", "lucro", "margem", "resultado"] },
        { id: "exportador-lcdpr", icone: BookOpen, label: "Exportador Oficial LCDPR (Receita Federal)", local: "Área Central", descricao: "Gerador do arquivo fiscal pronto para validação contábil amarrado ao NIRF da propriedade.", tags: ["lcdpr", "livro caixa", "receita federal"] },
    ],

    "10-rh": [
        { id: "quadro-equipe", icone: Users, label: "Quadro Geral de Colaboradores", local: "Barra Superior", descricao: "Contagem de funcionários ativos por departamento (Lavoura, Máquinas, Pecuária, Sede).", tags: ["colaboradores", "equipe", "quadro"] },
        { id: "espelho-ponto", icone: Clock, label: "Espelho de Ponto e Banco de Horas", local: "Área Central", descricao: "Controle de jornadas diárias, cálculo de horas extras e adicional noturno no campo.", tags: ["ponto", "jornada", "horas extras"] },
        { id: "holerite-folha", icone: Receipt, label: "Processador de Folha e Holerites", local: "Área Central", descricao: "Fechamento mensal com cálculo de proventos, encargos sociais e recibos de pagamento.", tags: ["folha", "holerite", "salário"] },
        { id: "eventos-esocial", icone: CheckCircle2, label: "Central de Eventos do eSocial", local: "Área Central", descricao: "Geração de lotes de admissão, remuneração e rescisão padronizados para o governo.", tags: ["esocial", "governo", "eventos"] },
    ],

    "11-seguranca": [
        { id: "status-conformidade-nr31", icone: ShieldCheck, label: "Painel de Conformidade NR-31", local: "Barra Superior", descricao: "Sinalizador geral do nível de atendimento às normas de segurança do trabalho rural.", tags: ["nr31", "nr-31", "conformidade"] },
        { id: "ficha-epi-ca", icone: HardHat, label: "Ficha de Entrega de EPI com Certificado (CA)", local: "Área Central", descricao: "Documento digital com assinatura do trabalhador para macacões, máscaras e botas.", tags: ["epi", "ca", "máscara", "proteção"] },
        { id: "radar-aso-medico", icone: Syringe, label: "Radar de Exames Médicos Ocupacionais (ASO)", local: "Área Central", descricao: "Controle de vencimentos de exames periódicos e dosagem semestral de colinesterase.", tags: ["aso", "exame", "colinesterase"] },
        { id: "certificados-treinamentos", icone: BadgeCheck, label: "Certificados de Cursos Obrigatórios", local: "Área Central", descricao: "Comprovação de capacitação para operação de tratores (31.12) e agrotóxicos (31.7).", tags: ["cursos", "treinamento", "capacitação"] },
    ],

    "12-ambiental": [
        { id: "balanco-car", icone: Trees, label: "Balanço de Áreas do CAR (APP & Reserva)", local: "Barra Superior", descricao: "Distribuição exata em hectares das áreas produtivas e matas nativas preservadas.", tags: ["car", "app", "reserva legal"] },
        { id: "gestor-outorgas", icone: Droplets, label: "Controle de Outorgas Hídricas", local: "Área Central", descricao: "Monitoramento de licenças de captação de água para pivôs centrais e poços artesianos.", tags: ["outorga", "água", "irrigação"] },
        { id: "mapa-satelite-inpe", icone: Satellite, label: "Mapa de Queimadas e Desmatamento (INPE)", local: "Área Central", descricao: "Camadas DETER e PRODES para alertas imediatos de fogo e blindagem contra embargos.", tags: ["satélite", "queimadas", "inpe", "embargos"] },
        { id: "passaporte-verde", icone: Shield, label: "Emissor do Passaporte Verde ESG", local: "Área Central", descricao: "Laudo oficial comprovando que a soja e o gado da fazenda cumprem a lei antidesmatamento EUDR.", tags: ["passaporte verde", "esg", "eudr"] },
    ],

    "13-ia": [
        { id: "chat-copiloto", icone: BrainCircuit, label: "Terminal de Conversa com o Copiloto IA", local: "Área Central", descricao: "Campo para fazer perguntas em linguagem natural sobre custos, safras e produtividade.", tags: ["chat", "copiloto", "ia", "perguntas"] },
        { id: "feed-recomendacoes", icone: Sparkles, label: "Feed de Recomendações e Economia", local: "Barra Superior", descricao: "Alertas inteligentes sugerindo correções de consumo de diesel e momentos ideais de venda.", tags: ["recomendações", "economia", "insights"] },
        { id: "gerador-resumo-safra", icone: FileText, label: "Gerador do Resumo Executivo da Safra", local: "Área Central", descricao: "Redator automático de relatórios completos para apresentação a bancos e conselho da fazenda.", tags: ["resumo", "executivo", "relatório"] },
    ],

    "14-campo-pwa": [
        { id: "status-offline", icone: Smartphone, label: "Indicador de Conectividade e Fila Offline", local: "Barra Superior", descricao: "Mostra se o aparelho está gravando dados na memória local ou sincronizando via Wi-Fi.", tags: ["offline", "conexão", "sincronização"] },
        { id: "lista-tarefas-operador", icone: ClipboardList, label: "Painel de Ordens de Serviço do Campo", local: "Área Central", descricao: "Tarefas atribuídas ao operador com botões de Iniciar, Anotar Insumos e Concluir.", tags: ["tarefas", "ordens de serviço", "operador"] },
        { id: "gestao-dispositivos", icone: Lock, label: "Gerenciador de Dispositivos e Permissões", local: "Área Central", descricao: "Cadastro de celulares e tablets autorizados a acessar os dados da fazenda no campo.", tags: ["dispositivos", "permissões", "segurança"] },
    ],

    "15-gestao-acesso": [
        { id: "btn-convidar-membro", icone: UserPlus, label: "Botão '+ Convidar Membro'", local: "Barra Superior", descricao: "Abre o formulário para enviar convite seguro por e-mail com perfil e fazendas autorizadas.", tags: ["convidar", "membro", "adicionar", "usuário"] },
        { id: "seletor-fazendas-autorizadas", icone: Building2, label: "Seletor de Fazendas Autorizadas", local: "Área Central", descricao: "Permite restringir o acesso do colaborador a apenas uma propriedade ou liberar o grupo todo.", tags: ["fazendas", "restrição", "propriedade", "autorização"] },
        { id: "matriz-permissoes-perfil", icone: Key, label: "Matriz de Permissões por Módulo", local: "Área Central", descricao: "Grade com caixas de seleção para definir quem pode Ver, Criar, Editar ou Deletar dados na fazenda.", tags: ["matriz", "permissões", "chave", "regras"] },
        { id: "autenticacao-2fa", icone: ShieldCheck, label: "Autenticação em 2 Etapas (2FA)", local: "Área Central", descricao: "Proteção com código temporário no celular impedindo invasões e acessos indevidos.", tags: ["2fa", "dois fatores", "segurança", "autenticação"] },
        { id: "gerenciador-sessoes", icone: Lock, label: "Monitor de Sessões e Desconexão Remota", local: "Área Central", descricao: "Lista computadores e celulares conectados com opção de deslogar tudo à distância com 1 clique.", tags: ["sessões", "desconectar", "remoto", "aparelhos"] },
    ],

    "16-configuracoes": [
        { id: "upload-logotipo", icone: FileText, label: "Upload de Logotipo Oficial da Fazenda", local: "Área Central", descricao: "Imagem que estampa automaticamente cabeçalhos de romaneios, tickets e laudos em PDF.", tags: ["logotipo", "logo", "marca", "pdf", "cabeçalho"] },
        { id: "wizard-assistido", icone: Settings2, label: "Wizard de Implantação Operacional", local: "Área Central", descricao: "Assistente guiado em 5 passos para parametrizar fazenda, frota, safra e equipe rapidamente.", tags: ["wizard", "implantação", "assistente", "passo a passo"] },
        { id: "parametros-globais", icone: SlidersHorizontal, label: "Parâmetros Globais da Fazenda", local: "Área Central", descricao: "Definição do Ano Agrícola ativo, Unidade de Área padrão (Hectares ou Alqueires) e decimais.", tags: ["parâmetros", "ano agrícola", "hectare", "alqueire", "moeda"] },
        { id: "conector-integracoes", icone: ArrowLeftRight, label: "Hub de Integrações (Balança, Clima & ERP)", local: "Área Central", descricao: "Conexão com indicador físico da Balança TARA, API OpenWeather e ERP contábil.", tags: ["integrações", "balança", "tara", "clima", "erp"] },
        { id: "painel-billing", icone: CreditCard, label: "Painel do Plano, Consumo e Faturas", local: "Área Central", descricao: "Acompanhamento do limite de hectares, usuários ativos e download de faturas e boletos mensais.", tags: ["assinatura", "plano", "faturas", "limites", "hectares"] },
        { id: "configurador-smtp", icone: Mail, label: "Servidor de E-mail Próprio (SMTP)", local: "Área Central", descricao: "Configuração de servidor de e-mail corporativo para envio de relatórios aos clientes.", tags: ["smtp", "e-mail", "servidor", "notificações"] },
        { id: "painel-ia-creditos", icone: BrainCircuit, label: "Monitor de Créditos e Uso de IA", local: "Área Central", descricao: "Painel de controle de tokens e requisições consumidas pelo Copiloto IA.", tags: ["ia", "créditos", "copiloto", "tokens"] },
    ],

    "17-jornadas": [
        { id: "fluxo-operacional", icone: Route, label: "Linha do Tempo da Fazenda Conectada", local: "Área Central", descricao: "Guia passo a passo ilustrando o caminho dos dados desde o preparo do solo até o balanço final.", tags: ["linha do tempo", "fluxo", "jornada", "rotina"] },
        { id: "painel-integrado", icone: RefreshCcw, label: "Efeito Dominó dos Dados Rurais", local: "Área Central", descricao: "Painel que demonstra visualmente como uma anotação no campo alimenta estoque e financeiro simultaneamente.", tags: ["efeito dominó", "integração", "dados rurais"] },
        { id: "regras-de-ouro", icone: BadgeCheck, label: "Painel das Regras de Ouro da Gestão", local: "Barra Superior", descricao: "Práticas recomendadas para manter o sistema atualizado com menos de 15 minutos diários de dedicação.", tags: ["regras de ouro", "boas práticas", "sucesso"] },
    ],
};

// ═══════════════════════════════════════════════════════════════════════════════
// PERGUNTAS FREQUENTES (FAQS) POR MÓDULO (15 MÓDULOS)
// ═══════════════════════════════════════════════════════════════════════════════

export const FAQS_POR_MODULO: Record<string, FaqItem[]> = {
    "00-navegacao": [
        { id: "faq-dados-sumiram", pergunta: "Cadastrei um dado (trator, animal ou talhão) e agora a tabela diz que está vazia. O que aconteceu?", resposta: "Na grande maioria dos casos, você está com a fazenda errada selecionada no topo da tela. Olhe para o seletor central da barra superior: certifique-se de que está na fazenda correta (ex: Terra Nostra) ou selecione 'Visão Consolidada' para ver os dados de todo o grupo somados.", tags: ["sumiu", "vazio", "fazenda", "seletor"] },
        { id: "faq-tela-apertada", pergunta: "A tela está muito apertada e as tabelas estão cortando no meu monitor ou notebook.", resposta: "Clique no ícone de recolher menu (ao lado do logo, no canto superior esquerdo). Isso esconderá a barra lateral esquerda e expandirá a área de trabalho imediatamente.", tags: ["apertada", "monitor", "recolher", "menu"] },
        { id: "faq-modo-escuro", pergunta: "Como trocar o fundo da tela para modo escuro ou claro?", resposta: "Na barra superior, clique no ícone da Lua ou do Sol. O modo escuro é perfeito para trabalhar à noite ou no campo sem cansar a visão; já o modo claro é ideal para o escritório durante o dia.", tags: ["escuro", "claro", "tema", "lua", "sol"] },
        { id: "faq-botao-adicionar", pergunta: "O que faz o botão com contorno verde '+ Adicionar' no topo da tela?", resposta: "É o menu de Ações Rápidas. Em vez de procurar opções em menus e submenus, clique em '+ Adicionar' para criar imediatamente um novo talhão, nova safra, novo animal ou romaneio de qualquer tela em que você estiver.", tags: ["adicionar", "atalho", "novo", "botão verde"] },
    ],

    "01-cadastros": [
        { id: "faq-area-excedida", pergunta: "Tento salvar um talhão mas o sistema mostra 'Erro: Área total excedida'. O que fazer?", resposta: "Isso acontece quando a área do talhão (ou a soma de todos os talhões cadastrados) ultrapassa a área total que você informou no cadastro da Fazenda. Verifique os hectares digitados em cada talhão ou edite a Unidade Produtiva para corrigir a área total da propriedade.", tags: ["área excedida", "erro", "hectares", "talhão"] },
        { id: "faq-trator-duas-fazendas", pergunta: "Tenho um trator que trabalha em duas fazendas diferentes. Onde devo cadastrar?", resposta: "Cadastre o trator na fazenda onde ele fica guardado (sede principal). Quando ele for prestar serviço na outra fazenda, o operador pode apontar o serviço informando em qual fazenda o trabalho foi executado.", tags: ["trator", "duas fazendas", "máquina", "frota"] },
        { id: "faq-produto-insumo", pergunta: "Qual a diferença entre Produto e Insumo na DeepFarms?", resposta: "Nenhuma! Na DeepFarms, tudo o que você compra para aplicar na lavoura, alimentar o gado ou abastecer o trator (adubo, semente, veneno, sal, diesel) fica reunido no 'Catálogo de Produtos'.", tags: ["diferença", "produto", "insumo", "catálogo"] },
        { id: "faq-desenho-mapa-errado", pergunta: "Errei o desenho do talhão no mapa por satélite. Como consertar?", resposta: "Na tela de Georreferenciamento, clique sobre o talhão na lista e selecione 'Editar'. Você poderá clicar nos pontos do mapa para arrastá-los para a cerca correta ou clicar em 'Redesenhar' para contornar novamente.", tags: ["desenho", "mapa", "errado", "ajustar"] },
    ],

    "02-imoveis": [
        { id: "faq-diferenca-unidade-imovel", pergunta: "Qual a diferença entre Unidade Produtiva (Módulo 01) e Imóvel Rural (Módulo 02)?", resposta: "A Unidade Produtiva é a fazenda operacional onde as máquinas trabalham e as safras acontecem. Já o Imóvel Rural é a escritura e a certidão do cartório (com matrícula, NIRF e INCRA). Uma única fazenda operacional pode ser formada por 2 ou 3 matrículas de cartório vizinhas!", tags: ["diferença", "unidade produtiva", "imóvel rural", "matrícula"] },
        { id: "faq-nirf-obrigatorio", pergunta: "Por que o número do NIRF é obrigatório no cadastro do imóvel?", resposta: "O NIRF é o número do imóvel na Receita Federal. O DeepFarms utiliza esse código para preencher automaticamente o Livro Caixa Digital do Produtor Rural (LCDPR), garantindo que suas notas fiscais e custos sejam declarados sem divergência com o fisco.", tags: ["nirf", "receita federal", "lcdpr", "imposto"] },
        { id: "faq-arrendamento-sacas", pergunta: "Como o sistema calcula o pagamento do arrendamento em sacas de soja?", resposta: "Ao cadastrar o contrato de arrendamento em sacas, no dia do vencimento o sistema consulta a cotação oficial da soja e calcula o valor equivalente em Reais automaticamente, gerando a conta a pagar no Módulo Financeiro sem você precisar fazer contas manuais.", tags: ["arrendamento", "sacas de soja", "cotação", "pagamento"] },
        { id: "faq-area-matricula-errada", pergunta: "Cadastrei a área da matrícula errada e o total não confere com a certidão. O que fazer?", resposta: "Na lista de Imóveis Rurais, clique no ícone do lápis (Editar) ao lado da matrícula correspondente. Você poderá ajustar a Área Total e as divisões de APP e Reserva Legal para que fiquem idênticas à escritura do cartório.", tags: ["área errada", "corrigir", "editar", "matrícula"] },
    ],

    "03-agricultura": [
        { id: "faq-caderno-badge-vermelho", pergunta: "O Caderno de Campo está com um badge vermelho no menu. O que significa e como apagar?", resposta: "Significa que o sistema identificou que a sua fazenda está em período de safra ativa, mas faz mais de 7 dias que nenhuma atividade de campo foi registrada. Para apagar o aviso, basta lançar a última operação de pulverização, plantio ou trator realizada.", tags: ["caderno", "badge", "vermelho", "atrasado"] },
        { id: "faq-produto-nao-aparece-caderno", pergunta: "Tentei lançar uma pulverização no caderno mas não achei o defensivo na lista. O que fazer?", resposta: "O produto ainda não foi incluído no Catálogo de Produtos. Acesse 'Cadastros > Insumos & Ativos > Catálogo de Produtos' (Módulo 01) e cadastre o veneno ou adubo foliar com a unidade correta (L ou kg). Ele aparecerá imediatamente no caderno de campo.", tags: ["produto", "não aparece", "caderno", "defensivo"] },
        { id: "faq-peso-liquido-menor", pergunta: "Por que o peso líquido do romaneio de colheita veio menor do que o peso da balança?", resposta: "Isso é totalmente normal! O sistema desconta o excesso de umidade dos grãos acima do padrão comercial (geralmente 14%) e as impurezas (cascas, terra e palha). O peso líquido resultante é exatamente a quantidade pela qual a cooperativa ou armazém pagará você.", tags: ["romaneio", "peso líquido", "balança", "desconto", "umidade"] },
        { id: "faq-ndvi-cinza", pergunta: "O mapa de satélite NDVI está aparecendo todo cinza ou sem imagem. Por quê?", resposta: "O satélite óptico não consegue enxergar a lavoura quando o dia está com nuvens densas sobre a fazenda. No calendário de passagens de satélite da tela de NDVI, clique em uma data anterior em que o céu estivesse claro para carregar a imagem.", tags: ["ndvi", "satélite", "cinza", "nuvens"] },
    ],

    "04-clima": [
        { id: "faq-previsao-celular-diferente", pergunta: "Por que a previsão do DeepFarms é diferente da previsão do aplicativo padrão do celular?", resposta: "Os aplicativos comuns mostram a previsão média da cidade inteira (geralmente colhida na estação do aeroporto a dezenas de quilômetros). O DeepFarms calcula a previsão exatamente nas coordenadas de GPS da sua fazenda, refletindo o microclima real da sua terra.", tags: ["previsão", "celular", "diferença", "gps", "microclima"] },
        { id: "faq-o-que-e-deriva", pergunta: "O que significa 'Risco de Deriva' e qual a velocidade máxima de vento para aplicar?", resposta: "Deriva acontece quando o vento arrasta as gotas do veneno para longe do talhão que você queria tratar. A velocidade máxima recomendada para pulverização é de 10 km/h.", tags: ["deriva", "vento", "velocidade", "limite"] },
        { id: "faq-gado-estresse-termico", pergunta: "Como saber se o gado está sofrendo com estresse térmico pelo ITH?", resposta: "Se o ITH estiver acima de 72, os animais já sentem desconforto com respiração ofegante e menor consumo no cocho. Mantenha os bebedouros sempre limpos e cheios e evite vacinações no meio do dia.", tags: ["ith", "estresse", "gado", "calor"] },
        { id: "faq-previsao-nao-atualizou", pergunta: "A previsão do tempo parece não ter atualizado hoje. O que fazer?", resposta: "No canto superior da tela de Clima, clique no botão 'Sincronizar Agora' (ícone de setas circulares). O sistema se conectará aos radares e atualizará a previsão de 5 dias e a curva horária na hora.", tags: ["atualizar", "sincronizar", "radar", "previsão"] },
    ],

    "05-estoque": [
        { id: "faq-saldo-insuficiente-saida", pergunta: "O sistema diz 'Saldo Insuficiente' e não deixa dar saída no produto. Por quê?", resposta: "O sistema bloqueia saídas negativas para garantir que o estoque seja real. Se você tem o produto fisicamente no galpão, é porque a compra ainda não teve o recebimento confirmado no sistema. Vá em Compras > Pedidos de Compra e confirme a entrega da mercadoria.", tags: ["saldo insuficiente", "erro", "saída", "recebimento"] },
        { id: "faq-preco-diferente-nota", pergunta: "Recebi a carga com preço diferente do que fechei na compra. Como ajustar?", resposta: "Na tela de conferência de recebimento, altere o valor unitário para o valor exato que consta na Nota Fiscal emitida pelo fornecedor. O sistema ajustará o custo médio do estoque e gerará a fatura correta no financeiro.", tags: ["preço diferente", "nota fiscal", "ajustar", "conferência"] },
        { id: "faq-transferir-entre-fazendas", pergunta: "Como transferir defensivos de uma fazenda sede para outra fazenda do grupo?", resposta: "Acesse Estoque > Almoxarifado e clique em 'Transferência entre Depósitos'. Selecione o depósito de origem (Fazenda Sede) e o depósito de destino (Fazenda Vizinha). O sistema transfere o saldo sem duplicar custos.", tags: ["transferência", "outra fazenda", "depósitos"] },
        { id: "faq-o-que-e-peps", pergunta: "O que é a regra PEPS e por que o sistema sugere o lote mais antigo?", resposta: "PEPS significa 'Primeiro que Entra, Primeiro que Sai'. O sistema sugere consumir primeiro os lotes comprados antes para que nenhum produto vença na prateleira esquecido no fundo do galpão.", tags: ["peps", "lote antigo", "validade", "regra"] },
    ],

    "06-frota": [
        { id: "faq-horimetro-errado", pergunta: "O operador digitou o horímetro errado no abastecimento e o consumo médio ficou distorcido. Como corrigir?", resposta: "Acesse Operação > Consumo & Eficiência, localize o registro de abastecimento na tabela e clique no ícone do lápis (Editar). Altere o horímetro para o número correto e salve. O sistema recalcula o consumo histórico imediatamente.", tags: ["horímetro", "abastecimento", "errado", "corrigir"] },
        { id: "faq-implemento-sem-motor", pergunta: "Posso cadastrar implementos sem motor (como plantadeiras e grades aradoras)?", resposta: "Sim! Cadastre o equipamento com o Tipo 'Implemento'. Ele não terá horímetro de motor, mas registrará as manutenções periódicas de graxa, rolamentos e troca de discos de corte.", tags: ["implemento", "plantadeira", "grade", "motor"] },
        { id: "faq-disponibilidade-mecanica", pergunta: "O que é a taxa de 'Disponibilidade Mecânica' mostrada no painel?", resposta: "É a porcentagem de tempo em que a sua frota esteve apta para trabalhar sem estar parada por defeito mecânico. Uma fazenda de alta eficiência mantém a disponibilidade acima de 92%.", tags: ["disponibilidade", "oficina", "indicador", "parada"] },
    ],

    "07-pecuaria": [
        { id: "faq-entrada-lote-animais", pergunta: "Comprei um lote de 100 bezerros. Preciso cadastrar a ficha de cada um individualmente?", resposta: "Não! Na tela de Meus Animais, utilize o botão '+ Entrada em Lote'. Você informa a quantidade de cabeças, a faixa de peso médio e a numeração sequencial dos brincos (ex: BR-100 a BR-200), e o sistema cadastra todos em segundos.", tags: ["lote", "bezerros", "cadastro em massa", "brincos"] },
        { id: "faq-carencia-abate-leite", pergunta: "O que acontece se eu tentar vender um animal que tomou remédio recentemente?", resposta: "O sistema mantém um sinalizador amarelo de 'Período de Carência Ativo' na ficha do bovino e emite um alerta se você tentar incluir esse animal em uma guia de abate ou lote de venda para frigorífico.", tags: ["carência", "abate", "remédio", "alerta"] },
        { id: "faq-pecuaria-sem-internet", pergunta: "Como anotar pesagens e vacinas no curral se lá não pega sinal de celular?", resposta: "Utilize o aplicativo Campo PWA no celular ou a Balança TARA no tablet no modo offline. As pesagens e vacinações são gravadas na memória do aparelho e sobem automaticamente para a nuvem quando você retornar ao Wi-Fi da sede.", tags: ["curral", "offline", "sem internet", "sincronização"] },
    ],

    "08-balanca": [
        { id: "faq-balanca-caiu-internet", pergunta: "A internet da fazenda caiu durante a colheita. A balança rodoviária para de pesar?", resposta: "Não! O sistema TARA possui contingência offline automática. Todas as pesagens de caminhões continuam sendo gravadas na memória local do computador da balança e os tickets são emitidos normalmente. Ao restabelecer a conexão, tudo sincroniza com a nuvem.", tags: ["internet", "offline", "contingência", "tara"] },
        { id: "faq-peso-oscilando-plataforma", pergunta: "O caminhão subiu na balança mas o botão de captura não fica verde. Por quê?", resposta: "O sistema só libera a captura de peso quando o indicador envia o sinal de 'Peso Estabilizado'. Peça para o motorista desligar o motor e aguarde rajadas fortes de vento passarem para estabilizar a plataforma.", tags: ["peso oscilando", "estabilizado", "captura", "balança"] },
    ],

    "09-financeiro": [
        { id: "faq-conciliacao-sobra-linhas", pergunta: "Importei o extrato OFX do banco mas algumas linhas não encontraram boletos correspondentes.", resposta: "Isso acontece com tarifas bancárias, saques ou transferências particulares. Basta clicar sobre a linha sem par no extrato e selecionar 'Criar Lançamento Rápido'. O sistema concilia a linha na hora.", tags: ["ofx", "extrato", "conciliação", "tarifa"] },
        { id: "faq-lcdpr-erro-receita", pergunta: "O validador da Receita Federal rejeitou meu arquivo do LCDPR. O que pode ser?", resposta: "A causa mais comum é a falta do número do NIRF cadastrado no imóvel rural ou CPF/CNPJ de fornecedores incompleto. Revise o Módulo 02 (Imóveis Rurais) e certifique-se de que o NIRF de 8 dígitos de cada matrícula esteja preenchido.", tags: ["lcdpr", "rejeição", "receita federal", "nirf"] },
    ],

    "10-rh": [
        { id: "faq-ajuste-ponto-esquecido", pergunta: "O tratorista esqueceu de registrar a saída do almoço. Como consertar?", resposta: "O gerente ou responsável pelo RH pode acessar a tela de Registro de Ponto, clicar no botão de 'Ajuste Manual' daquele dia, preencher o horário correto e informar a justificativa. O sistema grava o ajuste mantendo o histórico legal para auditoria.", tags: ["ponto", "esquecimento", "ajuste manual", "justificativa"] },
        { id: "faq-adiantamento-vale-folha", pergunta: "Como funciona o adiantamento salarial (vale) no fechamento da folha?", resposta: "Lance o vale durante o mês na categoria 'Adiantamento Salarial'. Quando você clicar em 'Processar Folha do Mês', o sistema abate o valor do vale do salário líquido a pagar automaticamente.", tags: ["vale", "adiantamento", "desconto", "folha"] },
    ],

    "11-seguranca": [
        { id: "faq-fiscalizacao-trabalho-auditoria", pergunta: "A fiscalização do Ministério do Trabalho chegou na fazenda. Onde encontro os documentos exigidos?", resposta: "Acesse o Painel SST (Módulo 11) e clique em 'Imprimir Prontuário Geral'. O sistema gera o dossiê completo com fichas de entrega de EPI assinadas, laudos de exames médicos ASO e certificados de treinamentos NR-31 dos trabalhadores.", tags: ["fiscalização", "ministério do trabalho", "auditoria", "prontuário"] },
    ],

    "12-ambiental": [
        { id: "faq-passaporte-verde-exportacao", pergunta: "O que é o Passaporte Verde e como ele me ajuda a vender a safra?", resposta: "O Passaporte Verde é o laudo digital emitido pelo sistema comprovando que a sua produção não provém de áreas desmatadas recentemente, terras indígenas ou áreas embargadas pelo IBAMA. Ele é exigido por tradings e cooperativas para cumprir as regras europeias (EUDR).", tags: ["passaporte verde", "eudr", "exportação", "trading"] },
        { id: "faq-alerta-fogo-acidental", pergunta: "Apareceu um alerta de foco de queimada no meu mapa, mas foi fogo acidental que veio da rodovia.", resposta: "No histórico de alertas ambientais, clique na ocorrência e selecione 'Registrar Evidência / Boletim de Ocorrência'. Anexe fotos do aceiro ou o B.O. dos bombeiros. Isso comprova que você não praticou desmatamento nem queima criminosa.", tags: ["queimada", "fogo", "evidência", "boletim"] },
    ],

    "13-ia": [
        { id: "faq-ia-faz-pagamento-sozinha", pergunta: "O Copiloto IA pode fazer pagamentos ou deletar registros da fazenda sozinho?", resposta: "Não! O Copiloto IA funciona exclusivamente em modo consultivo e analítico. Ele analisa números, dá dicas e gera relatórios, mas nunca executa transferências, pagamentos ou baixas sem a sua autorização expressa.", tags: ["ia", "segurança", "autonomia", "pagamento"] },
    ],

    "14-campo-pwa": [
        { id: "faq-celular-descarregou-campo", pergunta: "Se o celular do tratorista descarregar a bateria no meio do talhão, ele perde as anotações?", resposta: "Não! O aplicativo Campo PWA grava cada clique na memória física permanente do aparelho. Quando o celular for recarregado, todos os apontamentos estarão intactos e subirão para o sistema assim que ele conectar ao Wi-Fi.", tags: ["bateria", "descarregou", "memória", "offline"] },
    ],

    "15-gestao-acesso": [
        { id: "faq-convite-nao-chegou", pergunta: "Enviei o convite por e-mail para o funcionário mas ele diz que não recebeu. O que fazer?", resposta: "Peça para ele checar a caixa de Spam / Lixo Eletrônico. Se mesmo assim não localizar, acesse Gestão de Acesso > Equipe, localize o nome dele e clique no botão 'Reenviar Convite' ou copie o link direto de ativação e envie pelo WhatsApp dele.", tags: ["convite", "não chegou", "spam", "reenviar", "whatsapp"] },
        { id: "faq-ocultar-valores-campo", pergunta: "Como impedir que tratoristas ou operadores do campo vejam os valores em dinheiro e relatórios financeiros?", resposta: "Ao cadastrar ou editar o usuário, atribua a ele o perfil 'Operador' ou crie um perfil personalizado onde o módulo 'Financeiro & Custos' esteja desmarcado. Ele conseguirá anotar abastecimentos e serviços sem ver notas fiscais ou faturamento.", tags: ["ocultar", "valores", "financeiro", "tratorista", "operador", "sigilo"] },
        { id: "faq-demissao-bloqueio-imediato", pergunta: "Um colaborador foi demitido hoje. Como bloquear o acesso dele imediatamente no celular e no computador?", resposta: "Acesse Gestão de Acesso > Equipe, localize o colaborador e clique em 'Suspender Acesso'. O sistema derruba a sessão dele na hora em todos os computadores, tablets e no aplicativo Campo PWA do celular.", tags: ["demissão", "bloqueio", "suspender", "imediato", "desligamento"] },
        { id: "faq-acesso-contador-externo", pergunta: "Posso dar acesso ao meu contador externo sem que ele veja as operações de máquinas ou mexa na lavoura?", resposta: "Sim! Crie um usuário com o perfil 'Contador / Fiscal'. Ele terá acesso exclusivo às notas fiscais, contas a pagar/receber, conciliação e gerador do LCDPR, sem acesso para alterar defensivos ou safras.", tags: ["contador", "fiscal", "lcdpr", "acesso externo", "consultor"] },
    ],

    "16-configuracoes": [
        { id: "faq-logotipo-relatorios-pdf", pergunta: "O logotipo da fazenda cadastrado sai automaticamente em romaneios e ordens de serviço em PDF?", resposta: "Sim! Qualquer relatório impresso ou emitido em PDF (Romaneios, Tickets da Balança, Ordens de Serviço, DRE da Safra e Fichas de EPI) inclui o logotipo oficial no topo ao lado dos dados fiscais do produtor.", tags: ["logotipo", "pdf", "romaneio", "ticket", "ordem de serviço", "impressão"] },
        { id: "faq-alqueires-conversao", pergunta: "Como alterar a unidade de medida padrão de Hectares para Alqueires (Paulista, Mineiro ou Baiano)?", resposta: "Acesse Configurações > Configurações Globais (/dashboard/configuracoes/globais) e altere o campo 'Unidade de Área Padrão'. O sistema converte automaticamente a exibição em todas as telas sem distorcer o cálculo interno em metros quadrados.", tags: ["alqueire", "hectare", "conversão", "paulista", "mineiro", "baiano"] },
        { id: "faq-testar-balanca-clima", pergunta: "Como testar se a integração com a Balança TARA ou estação de clima está funcionando?", resposta: "Nas telas de integração em Configurações, clique no botão 'Testar Conexão'. O sistema enviará um sinal de ping e confirmará se a balança física ou a API meteorológica estão respondendo em tempo real.", tags: ["teste", "balança", "tara", "clima", "conexão", "ping"] },
        { id: "faq-limite-hectares-plano", pergunta: "O que acontece se eu ultrapassar o limite de hectares ou usuários do meu plano?", resposta: "O sistema emite um aviso amigável na tela de Assinatura (/dashboard/settings/billing) e permite fazer o upgrade com 1 clique para a faixa seguinte sem interromper nenhum lançamento na fazenda.", tags: ["limite", "hectares", "plano", "upgrade", "assinatura"] },
        { id: "faq-para-que-serve-wizard", pergunta: "Para que serve o Wizard de Implantação?", resposta: "O Wizard é um guia passo a passo em 5 etapas para quem está começando agora. Ele ajuda você a cadastrar sua primeira fazenda, talhões, tratores e safra sem precisar caçar menus individuais.", tags: ["wizard", "implantação", "início", "ajuda"] },
        { id: "faq-smtp-dominio-proprio", pergunta: "Como configurar o envio automático de avisos por e-mail com o domínio da própria fazenda?", resposta: "Acesse Configurações > Configuração de E-mail (/dashboard/settings/smtp) e insira as credenciais SMTP do seu provedor de e-mail. Os relatórios enviados por e-mail sairão com o remetente oficial da fazenda.", tags: ["smtp", "e-mail", "domínio", "remetente"] },
    ],

    "17-jornadas": [
        { id: "faq-ordem-comecar-zero", pergunta: "Qual é a ordem recomendada para começar a usar a DeepFarms do zero na minha fazenda?", resposta: "Comece na seguinte ordem: 1) Cadastre suas Fazendas e Talhões (Módulo 01); 2) Cadastre seus Tratores e Máquinas (Módulo 01); 3) Crie a Safra atual (Módulo 03); 4) Convide sua equipe com as devidas permissões (Módulo 15). Em menos de 1 hora sua fazenda já estará pronta para operar!", tags: ["começar do zero", "ordem", "primeiros passos", "início"] },
        { id: "faq-o-que-e-efeito-domino", pergunta: "O que é o efeito dominó dos dados rurais na plataforma?", resposta: "Significa que nenhuma informação precisa ser digitada duas vezes. Uma única anotação de pulverização no campo atualiza o Caderno de Campo, dá baixa no galpão de venenos, soma horas no trator e projeta o custo da safra no financeiro.", tags: ["efeito dominó", "integração", "automação", "produtividade"] },
        { id: "faq-lancamento-fim-de-semana", pergunta: "Preciso fazer todos os lançamentos no mesmo dia ou posso lançar tudo no fim de semana?", resposta: "Você pode lançar no momento que for mais conveniente! No entanto, recomendamos manter ao menos os abastecimentos de diesel e pesagens de caminhão diárias para que o estoque e a colheita nunca fiquem defasados.", tags: ["rotina", "fim de semana", "lançamentos", "atraso"] },
    ],
};
