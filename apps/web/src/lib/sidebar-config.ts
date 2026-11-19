import React from 'react';
import type { PlanTierId } from "@/types/global";
import {
  LayoutDashboard, Users, MapPin, Tractor, Sprout, Package, Home,
  Beaker, Calculator, Wallet, Activity, Bug, ShieldAlert, FileSignature, Recycle,
  Satellite, CloudSun, Pickaxe, ClipboardList, BookOpen,
  Beef, Syringe, Receipt, CreditCard, Landmark, FileText,
  Layers, Target, Tag, Table2, FolderTree, BookmarkCheck,
  LifeBuoy, Book, BarChart3, ShieldCheck, Shield, Settings,
  MessageSquare, Mail, Settings2, Wrench, ShoppingCart, Clock, CalendarClock,
  Trees, Droplets, AlertTriangle, Upload, FileCheck, CheckCircle2,
  Ruler, ArrowLeftRight, Cpu, Warehouse, BrainCircuit, Zap, Smartphone, TrendingUp, Leaf, Dna, Milk, RefreshCcw, ClipboardCheck, FlaskConical, Wheat, LayoutTemplate,
  Lock, UserCircle, Hash, HardHat, LineChart, Thermometer, Scale
} from 'lucide-react';

export interface SidebarMenuItem {
  href: string;
  icon: React.ElementType;
  label: string;
  tip?: string;
  permission?: string;
  minimumTier?: PlanTierId;
  /** ID do módulo necessário para ver este item (ex: "A1_PLANEJAMENTO") */
  module?: string;
  /** Exibe badge de alerta (ex: caderno desatualizado) */
  alertBadge?: boolean;
  /** Se verdadeiro, só ativa se a rota for exatamente igual ao href */
  exact?: boolean;
}

export interface SidebarSection {
  key: string;
  label: string;
  icon: React.ElementType;
  /** Módulo específico da seção quando difere do gate-base do grupo. */
  moduleId?: string;
  items: SidebarMenuItem[];
}

export interface SidebarModuleGroup {
  key: string;
  label: string;
  icon: React.ElementType;
  moduleId?: string; // ex: "A1_PLANEJAMENTO", "P1_REBANHO", "F1_TESOURARIA"
  sections: SidebarSection[];
}

// ═══════════════════════════════════════════════════════════════════════════════
// CORE: Cadastros e Tabelas Compartilhadas (sempre visível)
// Ordem de workflow: primeiro onde trabalha → com o quê → quem → tabelas aux.
// ═══════════════════════════════════════════════════════════════════════════════

export const CORE_CADASTROS: SidebarSection[] = [
  {
    key: 'core-propriedade',
    label: 'Minha Propriedade',
    icon: MapPin,
    items: [
      { href: '/cadastros/propriedades', icon: Trees, label: 'Unidades Produtivas', tip: 'Cadastro operacional, sede e estrutura das suas fazendas', permission: 'tenant:fazendas:view', exact: true },
      { href: '/cadastros/propriedades/talhoes', icon: MapPin, label: 'Georreferenciamento', tip: 'Mapa e geometria dos talhões', permission: 'agricola:talhoes:view' },
      { href: '/cadastros/commodities', icon: Sprout, label: 'Commodities', tip: 'Produtos agropecuários', permission: 'cadastros:commodities:view' },
    ],
  },
  {
    key: 'core-insumos',
    label: 'Insumos & Ativos',
    icon: Package,
    items: [
      { href: '/cadastros/produtos', icon: Package, label: 'Catálogo de Produtos', tip: 'Catálogo', permission: 'cadastros:produtos:view' },
      { href: '/cadastros/equipamentos', icon: Tractor, label: 'Equipamentos & Frota', tip: 'Ativos', permission: 'operacional:frota:view' },
      { href: '/cadastros/tipos-servico', icon: Wrench, label: 'Tipos de Serviço', tip: 'Serviços terceirizados', permission: 'cadastros:produtos:view' },
    ],
  },
  {
    key: 'core-pessoas',
    label: 'Pessoas & Parceiros',
    icon: Users,
    items: [
      { href: '/cadastros/pessoas', icon: Users, label: 'Pessoas & Parceiros', tip: 'Contatos', permission: 'cadastros:pessoas:view' },
    ],
  },
  {
    key: 'core-tabelas',
    label: 'Tabelas Auxiliares',
    icon: Table2,
    items: [
      { href: '/cadastros/tabelas/marcas', icon: BookmarkCheck, label: 'Marcas', tip: 'Marcas', permission: 'cadastros:marcas:view' },
      { href: '/cadastros/tabelas/modelos', icon: Layers, label: 'Modelos', tip: 'Modelos', permission: 'cadastros:modelos:view' },
      { href: '/cadastros/tabelas/categorias-produto', icon: FolderTree, label: 'Categorias de Produto', tip: 'Categorias', permission: 'cadastros:categorias_produto:view' },
    ],
  },
];

// ═══════════════════════════════════════════════════════════════════════════════
// MÓDULOS OPERACIONAIS (contratáveis)
// ═══════════════════════════════════════════════════════════════════════════════

// Ordem dos módulos segue o workflow operacional:
// ① Agricultura (núcleo produtivo)
// ② Operacional (suporta agricultura e pecuária — compras/estoque/frota)
// ③ Pecuária (rebanho usa estoque e frota)
// ④ Financeiro (resultado das operações)
// ⑤ RH (suporte à equipe)
// ⑥ Ambiental (compliance)

export const MODULOS_OPERACIONAIS: SidebarModuleGroup[] = [
  // ⓪ IMÓVEIS — cadastro → arrendamento → avaliação
  {
    key: 'I1',
    label: 'Imóveis Rurais',
    icon: Landmark,
    moduleId: 'IMOVEIS_CADASTRO',
    sections: [
      {
        key: 'I1-visao-geral',
        label: 'Visão Geral',
        icon: LayoutDashboard,
        items: [
          { href: '/cadastros/imoveis', icon: Home, label: 'Imóveis Rurais', tip: 'Cadastro legal', permission: 'imoveis:propriedades:view', exact: true },
          { href: '/cadastros/imoveis/avaliacoes', icon: TrendingUp, label: 'Avaliação Patrimonial', tip: 'Laudos e histórico', permission: 'imoveis:avaliacoes:view' },
        ],
      },
      {
        key: 'I1-operacao',
        label: 'Gestão',
        icon: FileText,
        items: [
        ],
      },
    ],
  },

  // ① AGRICULTURA — Safras definem o contexto; a jornada segue planejamento →
  // diagnóstico → execução → produção → resultados.
  {
    key: 'A1',
    label: 'Agricultura',
    icon: Sprout,
    moduleId: 'A1_PLANEJAMENTO',
    sections: [
      {
        key: 'A1-visao-geral',
        label: 'Safras e Contexto',
        icon: LayoutDashboard,
        items: [
          { href: '/agricola', icon: LayoutDashboard, label: 'Painel Agrícola', tip: 'Dashboard', permission: 'agricola:dashboard:view', exact: true },
          { href: '/agricola/safras', icon: ClipboardList, label: 'Safras e Painel da Safra', tip: 'Liste, crie ou selecione a safra em operação', permission: 'agricola:safras:view', exact: true },
        ],
      },
      {
        key: 'A1-planejamento',
        label: '① Planejamento',
        icon: Calculator,
        items: [
          { href: '/agricola/safras?redirect=planejamento-operacional', icon: ClipboardCheck, label: 'Planejamento Operacional', tip: 'Selecione a safra para acessar o planejamento operacional', permission: 'agricola:planejamento_operacional:visualizar' },
          { href: '/agricola/safras?redirect=orcamento', icon: Calculator, label: 'Orçamento de Safra', tip: 'Selecione a safra para acessar o orçamento', permission: 'agricola:planejamento:view' },
          { href: '/agricola/cadastros/culturas', icon: Sprout, label: 'Culturas e Variedades', tip: 'Culturas', permission: 'agricola:cadastros:view' },
          { href: '/agricola/cadastros/receitas-aplicacao', icon: FlaskConical, label: 'Receitas de Aplicação', tip: 'Receitas', permission: 'agricola:receita_aplicacao:visualizar' },
          { href: '/agricola/custos', icon: Wallet, label: 'Custeio Agrícola', tip: 'Custos', permission: 'agricola:custos:view' },
          { href: '/agricola/templates', icon: LayoutTemplate, label: 'Templates de Operação', tip: 'Modelos de fase e operação reutilizáveis', permission: 'agricola:template:listar' },
        ],
      },
      {
        key: 'A1-monitoramento',
        label: '② Diagnóstico',
        icon: Satellite,
        items: [
          { href: '/agricola/analises-solo', icon: Beaker, label: 'Análises de Solo', tip: 'Solo', permission: 'agricola:analises_solo:view' },
          { href: '/agricola/monitoramento', icon: Bug, label: 'Pragas & Doenças', tip: 'Sanidade', permission: 'agricola:monitoramento:view' },
          { href: '/agricola/defensivos', icon: ShieldAlert, label: 'Fitossanitário', tip: 'Defensivos', permission: 'agricola:monitoramento:view' },
          { href: '/dashboard/agricola/receituarios', icon: FileSignature, label: 'Receituário Agronômico', tip: 'Receituários e CREA', permission: 'agricola:receituario:ler' },
          { href: '/dashboard/agricola/logistica-reversa-embalagens', icon: Recycle, label: 'Logística Reversa', tip: 'Devolução de embalagens', permission: 'agricola:logistica_reversa:ler' },
          { href: '/agricola/fenologia', icon: Sprout, label: 'Fenologia', tip: 'Desenvolvimento', permission: 'agricola:fenologia:view' },
          { href: '/agricola/ndvi', icon: Satellite, label: 'Índices de Vegetação (NDVI)', tip: 'NDVI', permission: 'agricola:ndvi:view' },
          { href: '/agricola/mapa', icon: MapPin, label: 'Mapa de Prescrições', tip: 'Mapa', permission: 'agricola:prescricoes:view' },
        ],
      },
      {
        key: 'A1-execucao',
        label: '③ Execução',
        icon: Tractor,
        items: [
          { href: '/agricola/operacoes', icon: Tractor, label: 'Operações Consolidadas', tip: 'Operações', permission: 'agricola:operacoes:view' },
          {
            href: '/agricola/caderno',
            icon: BookOpen,
            label: 'Caderno de Campo',
            tip: 'Caderno',
            alertBadge: true, // habilita badge de alerta de caderno desatualizado
            permission: 'agricola:operacoes:view',
          },
          { href: '/agricola/timeline', icon: Activity, label: 'Timeline Operacional', tip: 'Timeline', permission: 'agricola:operacoes:view' },
        ],
      },
      {
        key: 'A1-colheita',
        label: '④ Produção',
        icon: ClipboardList,
        items: [
          { href: '/agricola/romaneios', icon: Wheat, label: 'Romaneios de Colheita', tip: 'Colheita', permission: 'agricola:colheita:view' },
          { href: '/dashboard/agricola/produtos-colhidos', icon: Wallet, label: 'Produtos Colhidos', tip: 'Custo e margem por lote', permission: 'agricola:colheita:view' },
          { href: '/agricola/safras?redirect=beneficiamento', icon: Pickaxe, label: 'Beneficiamento', tip: 'Selecione a safra para acessar o beneficiamento', permission: 'agricola:beneficiamento:view' },
        ],
      },
      {
        key: 'A1-resultados',
        label: '⑤ Resultados',
        icon: TrendingUp,
        items: [
          { href: '/dashboard/agricola/rentabilidade', icon: TrendingUp, label: 'Rentabilidade Agrícola', tip: 'Rentabilidade e Margem', minimumTier: 'PROFISSIONAL', permission: 'agricola:relatorios:view' },
          { href: '/dashboard/agricola/dre', icon: FileText, label: 'DRE Agrícola v1', tip: 'Visão oficial econômica', minimumTier: 'PROFISSIONAL', permission: 'agricola:relatorios:view' },
          { href: '/agricola/relatorios', icon: FileText, label: 'Relatórios', tip: 'Relatórios', permission: 'agricola:relatorios:view' },
          { href: '/dashboard/agricola', icon: Sprout, label: 'Ciclos de Produção', tip: 'Safras e desempenho produtivo', minimumTier: 'PROFISSIONAL', permission: 'agricola:dashboard:view', exact: true },
        ],
      },
      {
        key: 'A1-gestao',
        label: '⑥ Suporte',
        icon: BarChart3,
        items: [
          { href: '/agricola/ajuda', icon: LifeBuoy, label: 'Central de Ajuda', tip: 'Ajuda' },
        ],
      },
    ],
  },

  // ── CLIMA E PREVISÃO ──
  {
    key: 'C1',
    label: 'Clima e Previsão',
    icon: CloudSun,
    sections: [
      {
        key: 'C1-visao-geral',
        label: 'Visão Geral',
        icon: CloudSun,
        items: [
          { href: '/dashboard/agricola/clima/monitoramento', icon: CloudSun, label: 'Previsão Agrícola', tip: 'Dados Climáticos e Previsão 5 dias', permission: 'agricola:climatico:view', exact: true },
          { href: '/dashboard/pecuaria/clima/monitoramento', icon: Thermometer, label: 'Previsão Pecuária', tip: 'Dados Climáticos e ventos para gado', permission: 'pecuaria:climatico:view', exact: true },
        ],
      },
      {
        key: 'C1-intel-agricola',
        label: 'Inteligência Agrícola',
        icon: Sprout,
        items: [
          { href: '/dashboard/agricola/clima/inteligencia', icon: BrainCircuit, label: 'Painel Fitossanitário', tip: 'GDU, Riscos e Gráficos Históricos', permission: 'agricola:climatico:view', exact: true },
          { href: '/dashboard/agricola/clima/inteligencia/modelos', icon: Target, label: 'Modelos Fitossanitários', tip: 'Gestão de regras de risco', permission: 'agricola:climatico:view' },
        ],
      },
      {
        key: 'C1-intel-pecuaria',
        label: 'Inteligência Pecuária',
        icon: Beef,
        items: [
          { href: '/dashboard/pecuaria/clima/inteligencia', icon: BrainCircuit, label: 'Painel Zoossanitário', tip: 'ITH e Riscos', permission: 'pecuaria:climatico:view', exact: true },
          { href: '/dashboard/pecuaria/clima/inteligencia/modelos', icon: Target, label: 'Modelos Zoossanitários', tip: 'Gestão de regras de risco', permission: 'pecuaria:climatico:view' },
        ],
      },
    ],
  },

  // ② ESTOQUE & SUPRIMENTO — compras → estoque
  {
    key: 'O1',
    label: 'Estoque & Suprimento',
    icon: Warehouse,
    moduleId: 'O2_ESTOQUE',
    sections: [
      {
        key: 'O1-dashboard',
        label: 'Dashboard',
        icon: LayoutDashboard,
        items: [
          { href: '/suprimentos', icon: LayoutDashboard, label: 'Painel de Suprimentos', tip: 'Dashboard', permission: 'estoque:saldo:view', exact: true },
        ],
      },
      {
        key: 'O1-compras',
        label: '① Compras',
        icon: ShoppingCart,
        moduleId: 'O3_COMPRAS',
        items: [
          { href: '/suprimentos/compras/solicitacoes', icon: ClipboardList, label: 'Solicitações de Compra', tip: 'Gestão de Solicitações', permission: 'operacional:compras:view' },
          { href: '/suprimentos/compras', icon: ShoppingCart, label: 'Pedidos de Compra', tip: 'POs', permission: 'operacional:compras:view', exact: true },
          { href: '/dashboard/operacional/fornecedores', icon: Users, label: 'Fornecedores', tip: 'Suppliers', permission: 'estoque:fornecedores:view' },
        ],
      },
      {
        key: 'O1-estoque',
        label: '② Estoque',
        icon: Package,
        items: [
          { href: '/suprimentos/saldos', icon: Activity, label: 'Saldos de Estoque', tip: 'Saldos', permission: 'estoque:saldo:view' },
          { href: '/suprimentos/estoque', icon: Package, label: 'Almoxarifado', tip: 'Inventário', permission: 'estoque:movimentacoes:view' },
          { href: '/suprimentos/lotes', icon: Layers, label: 'Lotes de Estoque', tip: 'Lotes', permission: 'estoque:lotes:view' },
          { href: '/suprimentos/requisicoes', icon: FileCheck, label: 'Requisições', tip: 'Requisições', permission: 'estoque:movimentacoes:view' },
        ],
      },
    ],
  },

  // ③ FROTA & MANUTENÇÃO
  {
    key: 'O1-FROTA',
    label: 'Frota & Manutenção',
    icon: Tractor,
    moduleId: 'O1_FROTA',
    sections: [
      {
        key: 'O1-frota-dashboard',
        label: 'Dashboard',
        icon: LayoutDashboard,
        items: [
          { href: '/operacional', icon: LayoutDashboard, label: 'Painel da Frota', tip: 'Dashboard', permission: 'operacional:frota:view', exact: true },
        ],
      },
      {
        key: 'O1-manutencao',
        label: '① Operação',
        icon: Wrench,
        items: [
          { href: '/dashboard/operacional/frota', icon: Tractor, label: 'Frota de Máquinas', tip: 'Veículos', permission: 'operacional:frota:view', exact: true },
          { href: '/dashboard/operacional/manutencoes', icon: Wrench, label: 'Manutenções', tip: 'Manutencao', permission: 'operacional:oficina:view' },
          { href: '/dashboard/operacional/frota/manutencao-preventiva', icon: CalendarClock, label: 'Preventiva', tip: 'Preventiva', minimumTier: 'PROFISSIONAL', permission: 'operacional:oficina:view' },
          { href: '/dashboard/operacional/frota/consumo', icon: Droplets, label: 'Consumo & Eficiência', tip: 'Consumo', minimumTier: 'PROFISSIONAL', permission: 'operacional:abastecimento:view' },
          { href: '/dashboard/operacional/frota/custos', icon: Wallet, label: 'Custos Totais', tip: 'Custos', minimumTier: 'PROFISSIONAL', permission: 'operacional:relatorios:view' },
          { href: '/dashboard/operacional/frota/jornadas', icon: Clock, label: 'Jornadas', tip: 'Uso', minimumTier: 'PROFISSIONAL', permission: 'operacional:apontamento:view' },
          { href: '/dashboard/operacional/mao-obra/apontamentos', icon: HardHat, label: 'Apontamento de Mão de Obra', tip: 'Trabalho manual', permission: 'operacional:apontamento:view' },
          { href: '/dashboard/operacional/frota/inteligencia', icon: BrainCircuit, label: 'Inteligência', tip: 'Risco', minimumTier: 'ENTERPRISE', permission: 'operacional:inteligencia:view' },
          { href: '/dashboard/operacional/frota/agricultura', icon: Sprout, label: 'Uso Agrícola', tip: 'Agricultura', minimumTier: 'ENTERPRISE', permission: 'operacional:apontamento:view' },
          { href: '/dashboard/operacional/frota/disponibilidade', icon: ShieldAlert, label: 'Disponibilidade', tip: 'Disponibilidade', minimumTier: 'PROFISSIONAL', permission: 'operacional:frota:view' },
        ],
      },
    ],
  },

  // ③ PECUÁRIA — estrutura → rebanho → saúde → resultados
  {
    key: 'P1',
    label: 'Pecuária',
    icon: Beef,
    moduleId: 'P1_REBANHO',
    sections: [
      {
        key: 'P1-dashboard',
        label: 'Dashboard',
        icon: LayoutDashboard,
        items: [
          { href: '/dashboard/pecuaria', icon: LayoutDashboard, label: 'Painel de Rebanhos', tip: 'Dashboard', permission: 'pecuaria:dashboard:view', exact: true },
          { href: '/dashboard/pecuaria/sync-campo', icon: RefreshCcw, label: 'Sync Campo', tip: 'Monitoramento de Sincronização', permission: 'pecuaria:sync_campo:view' },
        ],
      },
      {
        key: 'P1-estrutura',
        label: '① Estrutura',
        icon: MapPin,
        items: [
          { href: '/dashboard/pecuaria/piquetes', icon: MapPin, label: 'Piquetes & Pastos', tip: 'Pastos', permission: 'pecuaria:piquetes:view' },
        ],
      },
      {
        key: 'P1-rebanho',
        label: '② Rebanho',
        icon: Beef,
        items: [
          { href: '/dashboard/pecuaria/animais', icon: Beef, label: 'Meus Animais', tip: 'Animais', permission: 'pecuaria:animais:view' },
          { href: '/dashboard/pecuaria/lotes', icon: ClipboardList, label: 'Lotes', tip: 'Lotes', permission: 'pecuaria:lotes:view' },
          { href: '/dashboard/pecuaria/manejos/planejamento', icon: CalendarClock, label: 'Planejamento de Manejos', tip: 'Planejamento', permission: 'pecuaria:manejos:view' },
          { href: '/dashboard/pecuaria/genetica', icon: Dna, label: 'Genética', tip: 'DEP e acasalamentos', permission: 'pecuaria:reproducao:view' },
        ],
      },
      {
        key: 'P1-saude',
        label: '③ Saúde & Nutrição',
        icon: Syringe,
        items: [
          { href: '/dashboard/pecuaria/manejo', icon: Syringe, label: 'Manejos Sanitários', tip: 'Tratamentos', permission: 'pecuaria:manejos:view' },
          { href: '/dashboard/pecuaria/confinamento', icon: Warehouse, label: 'Confinamento', tip: 'TMR e cochos', permission: 'pecuaria:confinamento:view' },
        ],
      },
      {
        key: 'P1-leite',
        label: '④ Leite',
        icon: Milk,
        items: [
          { href: '/dashboard/pecuaria/leite', icon: Milk, label: 'Produção de Leite', tip: 'Qualidade e destino', permission: 'pecuaria:leite:view' },
        ],
      },
    ],
  },
  {
    key: 'O4-BALANCA',
    label: 'Balança',
    icon: Scale,
    moduleId: 'O4_BALANCA',
    sections: [
      {
        key: 'O4-balanca-integracao',
        label: 'Operação',
        icon: Scale,
        items: [
          { href: '/dashboard/operacional/balanca/operadores', icon: Users, label: 'Operadores', tip: 'Operadores integrados ao Pondaxis', permission: 'balanca:operador:view' },
          { href: '/dashboard/operacional/balanca/estacoes', icon: Smartphone, label: 'Estações', tip: 'Estações do Pondaxis', permission: 'balanca:dispositivo:view' },
          { href: '/dashboard/operacional/balanca/pesagens', icon: Scale, label: 'Pesagens', tip: 'Consulta de pesagens', permission: 'balanca:pesagem:view' },
        ],
      },
    ],
  },

  // ④ FINANCEIRO — receitas → despesas → bancário → gestão → fiscal
  {
    key: 'F1',
    label: 'Financeiro',
    icon: Receipt,
    moduleId: 'F1_TESOURARIA',
    sections: [
      {
        key: 'F1-dashboard',
        label: 'Dashboard',
        icon: LayoutDashboard,
        items: [
          { href: '/dashboard/financeiro', icon: LayoutDashboard, label: 'Painel Financeiro', tip: 'Dashboard', permission: 'financeiro:dashboard:view', exact: true },
        ],
      },
      {
        key: 'F1-receitas',
        label: '① Receitas & Vendas',
        icon: CreditCard,
        items: [
          { href: '/dashboard/financeiro/receitas', icon: CreditCard, label: 'Minhas Receitas', tip: 'Vendas', permission: 'financeiro:receitas:view' },
          { href: '/dashboard/financeiro/romaneios', icon: Wheat, label: 'Romaneios de Colheita', tip: 'Romaneios', permission: 'agricola:colheita:view' },
        ],
      },
      {
        key: 'F1-despesas',
        label: '② Despesas & Custos',
        icon: Wallet,
        items: [
          { href: '/dashboard/financeiro/despesas', icon: Wallet, label: 'Minhas Despesas', tip: 'Gastos', permission: 'financeiro:despesas:view' },
          { href: '/dashboard/financeiro/ordens-pagamento', icon: ClipboardList, label: 'Ordens de Pagamento', tip: 'Remessas e homologação', permission: 'financeiro:despesas:view' },
        ],
      },
      {
        key: 'F1-bancario',
        label: '③ Bancário',
        icon: Landmark,
        items: [
          { href: '/dashboard/financeiro/contas-bancarias', icon: Landmark, label: 'Contas Bancárias', tip: 'Bancos', permission: 'financeiro:contas:view' },
          { href: '/dashboard/financeiro/conciliacao', icon: CheckCircle2, label: 'Conciliação Bancária', tip: 'Conciliação', permission: 'financeiro:contas:view' },
        ],
      },
      {
        key: 'F1-gestao',
        label: '④ Gestão Financeira',
        icon: Calculator,
        items: [
          { href: '/dashboard/financeiro/planos-conta', icon: Landmark, label: 'Planos de Conta', tip: 'Contas', permission: 'financeiro:categorias:view' },
          { href: '/dashboard/financeiro/custos', icon: Wallet, label: 'Custos ABC', tip: 'Rateio e centro de custos', minimumTier: 'PROFISSIONAL', permission: 'financeiro:centro_custo:view' },
          { href: '/dashboard/financeiro/fluxo-caixa', icon: BarChart3, label: 'Fluxo de Caixa', tip: 'Caixa', permission: 'financeiro:fluxo_caixa:view' },
          { href: '/dashboard/financeiro/lancamentos', icon: ClipboardList, label: 'Lançamentos Operacionais', tip: 'Análise por Safra', permission: 'financeiro:lancamentos:view' },
          { href: '/dashboard/financeiro/dre', icon: FileText, label: 'DRE Operacional', tip: 'Resultado por Safra', permission: 'financeiro:dre:view' },
          { href: '/dashboard/financeiro/viabilidade', icon: TrendingUp, label: 'Viabilidade (VPL/TIR)', tip: 'Payback, VPL, TIR e TMA', permission: 'financeiro:dre:view' },
        ],
      },
      {
        key: 'F1-hedge',
        label: '⑤ Hedging & Futuros',
        icon: ShieldCheck,
        items: [
          { href: '/dashboard/financeiro/hedge/exposicao', icon: BarChart3, label: 'Exposição Física × Financeira', tip: 'Dashboard de Cobertura Comercial', permission: 'financeiro:hedge:view' },
          { href: '/dashboard/financeiro/hedge/painel', icon: Shield, label: 'Painel de Exposição', tip: 'Exposição de Preço por Safra', permission: 'financeiro:hedge:view' },
          { href: '/dashboard/financeiro/hedge/contratos', icon: BookmarkCheck, label: 'Contratos Futuros', tip: 'Contratos B3/CBOT', permission: 'financeiro:hedge:view' },
          { href: '/dashboard/financeiro/hedge/registros', icon: ClipboardList, label: 'Registros de Operação', tip: 'Aberturas e Rolagens', permission: 'financeiro:hedge:view' },
          { href: '/dashboard/financeiro/hedge/mtm', icon: Calculator, label: 'Mark-to-Market', tip: 'MTM Diário', permission: 'financeiro:hedge:view' },
        ],
      },
      {
        key: 'F1-fiscal',
        label: '⑤ Fiscal & Obrigações',
        icon: FileCheck,
        items: [
          { href: '/dashboard/financeiro/nf-e', icon: FileText, label: 'NFP-e/NF-e', tip: 'Notas', permission: 'financeiro:fiscal:view' },
          { href: '/dashboard/financeiro/lcdpr', icon: BookOpen, label: 'LCDPR', tip: 'Livro Caixa', permission: 'financeiro:fiscal:view' },
          { href: '/dashboard/financeiro/esocial', icon: CheckCircle2, label: 'eSocial', tip: 'eSocial', permission: 'financeiro:fiscal:view' },
        ],
      },
    ],
  },

  // ⑤ RH — estrutura → operação → obrigações
  {
    key: 'RH',
    label: 'Recursos Humanos',
    icon: Users,
    moduleId: 'RH1_REMUNERACAO',
    sections: [
      {
        key: 'RH-estrutura',
        label: '① Estrutura',
        icon: Landmark,
        items: [
          { href: '/dashboard/rh/departamentos', icon: Landmark, label: 'Departamentos', tip: 'Depto', permission: 'pessoas:colaboradores:view' },
          { href: '/dashboard/rh/colaboradores', icon: Users, label: 'Colaboradores', tip: 'Equipe', permission: 'pessoas:colaboradores:view' },
        ],
      },
      {
        key: 'RH-operacao',
        label: '② Operação Diária',
        icon: Clock,
        items: [
          { href: '/dashboard/rh/ponto', icon: Clock, label: 'Registro de Ponto', tip: 'Ponto', permission: 'pessoas:ponto:view' },
        ],
      },
      {
        key: 'RH-obrigacoes',
        label: '③ Obrigações',
        icon: FileCheck,
        items: [
          { href: '/dashboard/rh/folha-pagamento', icon: Wallet, label: 'Folha de Pagamento', tip: 'Folha', permission: 'pessoas:folha:view' },
          { href: '/dashboard/rh/esocial', icon: FileCheck, label: 'eSocial', tip: 'eSocial', permission: 'pessoas:esocial:view' },
        ],
      },
    ],
  },

  // ⑤.1 RH — Segurança do Trabalho
  {
    key: 'RH2',
    label: 'Segurança do Trabalho',
    icon: Shield,
    moduleId: 'RH2_SEGURANCA',
    sections: [
      {
        key: 'RH2-dashboard',
        label: 'Visão Geral',
        icon: LayoutDashboard,
        items: [
          { href: '/dashboard/rh/seguranca', icon: LayoutDashboard, label: 'Painel SST', tip: 'Resumo e alertas', permission: 'sst:seguranca:view' },
        ],
      },
    ],
  },

  // ⑥ AMBIENTAL — setup → monitoramento → compliance
  {
    key: 'AM1',
    label: 'Ambiental',
    icon: Trees,
    moduleId: 'AM1_COMPLIANCE',
    sections: [
      {
        key: 'AM1-dashboard',
        label: 'Dashboard',
        icon: LayoutDashboard,
        items: [
          { href: '/dashboard/ambiental', icon: LayoutDashboard, label: 'Painel Ambiental', tip: 'Dashboard', permission: 'ambiental:dashboard:view', exact: true },
        ],
      },
      {
        key: 'AM1-car',
        label: '① CAR & Áreas',
        icon: FileText,
        items: [
          { href: '/dashboard/ambiental/car/importar', icon: Upload, label: 'Importar CAR', tip: 'SNA', permission: 'ambiental:car:view' },
          { href: '/dashboard/ambiental/car/lista', icon: ClipboardList, label: 'Meus CARs', tip: 'CARs', permission: 'ambiental:car:view' },
          { href: '/dashboard/ambiental/car/areas', icon: BarChart3, label: 'Dashboard de Áreas', tip: 'Áreas', permission: 'ambiental:car:view' },
          { href: '/dashboard/ambiental/outorgas', icon: Droplets, label: 'Outorgas Hídricas', tip: 'Água', permission: 'ambiental:outorgas:view' },
          { href: '/dashboard/ambiental/carbono', icon: Leaf, label: 'Gestão de Carbono', tip: 'MRV e créditos', permission: 'ambiental:carbono:view' },
          { href: '/dashboard/certificacoes-esg', icon: ShieldCheck, label: 'Certificações & ESG', tip: 'Evidências, NCs e planos', permission: 'ambiental:certificacoes:view' },
          { href: '/dashboard/certificacoes-esg/relatorios-passaportes', icon: FileText, label: 'Relatórios & Passaportes', tip: 'ESG e Passaportes', permission: 'ambiental:certificacoes:view' },
        ],
      },
      {
        key: 'AM1-monitoramento',
        label: '② Monitoramento',
        icon: Satellite,
        items: [
          { href: '/dashboard/ambiental/monitoramento/mapa', icon: MapPin, label: 'Mapa de Monitoramento', tip: 'Mapa', permission: 'ambiental:monitoramento:view' },
          { href: '/dashboard/ambiental/monitoramento/alertas', icon: AlertTriangle, label: 'Alertas de Desmatamento', tip: 'Alertas', permission: 'ambiental:monitoramento:view' },
          { href: '/dashboard/ambiental/monitoramento/historico', icon: BookOpen, label: 'Histórico de Alertas', tip: 'Histórico', permission: 'ambiental:monitoramento:view' },
        ],
      },
    ],
  },

  // ⑦ INTELIGÊNCIA ARTIFICIAL — autopilot → performance → insights
  {
    key: 'IA1',
    label: 'Copiloto IA',
    icon: BrainCircuit,
    moduleId: 'EXT_IA',
    sections: [
      {
        key: 'IA-dashboard',
        label: 'Dashboard',
        icon: LayoutDashboard,
        items: [
          { href: '/dashboard/ia', icon: LayoutDashboard, label: 'Painel de IA', tip: 'Dashboard', permission: 'ia:dashboard:view', exact: true },
          { href: '/dashboard/inteligencia-operacional/recomendacoes', icon: BrainCircuit, label: 'Recomendações Operacionais', tip: 'Engine global', permission: 'ia:recomendacoes:view' },
        ],
      },
      {
        key: 'IA-performance',
        label: '① Performance',
        icon: Activity,
        items: [
          { href: '/dashboard/ia/performance', icon: Activity, label: 'Performance & Eficiência', tip: 'Métricas', permission: 'ia:performance:view' },
        ],
      },
      {
        key: 'IA-plano',
        label: '② Estratégia',
        icon: Zap,
        items: [
          { href: '/dashboard/ia/plano-acao', icon: Zap, label: 'Plano de Ação', tip: 'Plano', permission: 'ia:plano:view' },
          { href: '/dashboard/ia/resumo', icon: FileText, label: 'Resumo IA Safra', tip: 'Resumo', permission: 'ia:plano:view' },
        ],
      },
    ],
  },
  // CAMPO PWA — dispositivos e tarefas móveis
  {
    key: 'CAMPO',
    label: 'Campo PWA',
    icon: Sprout,
    moduleId: 'A2_CAMPO',
    sections: [
      {
        key: 'CAMPO-dispositivos',
        label: 'Dispositivos',
        icon: Smartphone,
        items: [
          { href: '/dashboard/operacional/campo/dispositivos', icon: Smartphone, label: 'Dispositivos', tip: 'Tablets & Celulares', permission: 'campo:dispositivos:view' },
          { href: '/dashboard/operacional/campo/tarefas', icon: ClipboardList, label: 'Tarefas de Campo', tip: 'Tarefas', permission: 'campo:tarefas:view' },
        ],
      },
    ],
  },
];

// ═══════════════════════════════════════════════════════════════════════════════
// BACKOFFICE (apenas para admins)
// ═══════════════════════════════════════════════════════════════════════════════

export interface BackofficeSection {
  key: string;
  label: string;
  icon: React.ElementType;
  items: SidebarMenuItem[];
}

export const BACKOFFICE_SECTIONS: BackofficeSection[] = [
  {
    key: 'backoffice-visao',
    label: 'Visão Geral',
    icon: BarChart3,
    items: [
      { href: '/dashboard/backoffice/dashboard', icon: LayoutDashboard, label: 'Dashboard Executivo', tip: 'Dashboard', permission: 'backoffice:dashboard:view' },
      { href: '/dashboard/backoffice/bi', icon: BarChart3, label: 'Business Intelligence', tip: 'BI', permission: 'backoffice:bi:view' },
    ],
  },
  {
    key: 'backoffice-comercial',
    label: 'Comercial',
    icon: ShoppingCart,
    items: [
      { href: '/dashboard/backoffice/assinantes', icon: Users, label: 'Assinantes', tip: 'Gestão de Assinantes', permission: 'backoffice:tenants:view' },
      { href: '/dashboard/backoffice/plans', icon: Package, label: 'Planos & Preços', tip: 'Planos', permission: 'backoffice:plans:view' },
      { href: '/dashboard/backoffice/modules', icon: Layers, label: 'Catálogo de Módulos', tip: 'Módulos', permission: 'backoffice:plans:view' },
      { href: '/dashboard/backoffice/cupons', icon: Tag, label: 'Cupons & Promoções', tip: 'Cupons', permission: 'backoffice:cupons:view' },
      { href: '/dashboard/backoffice/crm', icon: Target, label: 'CRM', tip: 'CRM', permission: 'backoffice:crm:view' },
      { href: '/dashboard/backoffice/ia-creditos/solicitacoes', icon: Cpu, label: 'Solicitações de IA', tip: 'Créditos de IA', permission: 'backoffice:ia:view' },
    ],
  },
  {
    key: 'backoffice-agro',
    label: 'DeepFarms Agro',
    icon: Wheat,
    items: [
      { href: '/dashboard/backoffice/agro', icon: LayoutDashboard, label: 'Painel Executivo', tip: 'Métricas executivas, observabilidade e governança', permission: 'backoffice:agro:view', exact: true },
      { href: '/dashboard/backoffice/agro/usuarios', icon: Users, label: 'Produtores Agro', tip: 'Gestão de produtores rurais e cofre BYOK', permission: 'backoffice:agro:view' },
      { href: '/dashboard/backoffice/agro/bibliotecas', icon: BookOpen, label: 'Bibliotecas Globais', tip: 'Catálogos canônicos de commodities, culturas e unidades', permission: 'backoffice:agro:view' },
      { href: '/dashboard/backoffice/agro/provedores', icon: CloudSun, label: 'Provedores Climáticos', tip: 'Gestão de adaptadores meteorológicos, credenciais e contingência', permission: 'backoffice:agro:config:view' },
      { href: '/dashboard/backoffice/agro/mercado', icon: TrendingUp, label: 'Mercado & Fontes Oficiais', tip: 'Governança de PTAX, SGS, SIDRA e snapshots DERAL', permission: 'backoffice:agro:market:view' },
      { href: '/dashboard/backoffice/agro/configuracoes', icon: Settings, label: 'Configurações Globais', tip: 'Parâmetros dinâmicos, avisos legais e feature flags', permission: 'backoffice:agro:config:view' },
    ],
  },
  {
    key: 'backoffice-financeiro',
    label: 'Financeiro',
    icon: Receipt,
    items: [
      { href: '/dashboard/backoffice/billing', icon: Receipt, label: 'Faturamento & Cobranças', tip: 'Faturamento', permission: 'backoffice:billing:view' },
    ],
  },
  {
    key: 'backoffice-suporte',
    label: 'Suporte',
    icon: LifeBuoy,
    items: [
      { href: '/dashboard/backoffice/support', icon: LifeBuoy, label: 'Chamados', tip: 'Chamados', permission: 'backoffice:support:view' },
      { href: '/dashboard/backoffice/kb', icon: Book, label: 'Base de Conhecimento', tip: 'KB', permission: 'backoffice:kb:view' },
    ],
  },
  {
    key: 'backoffice-cadastros-auxiliares',
    label: 'Cadastros Auxiliares',
    icon: Table2,
    items: [
      { href: '/backoffice/tabelas', icon: Table2, label: 'Tabelas Padrão', tip: 'Gerenciar Tabelas e Templates Globais', permission: 'backoffice:tabelas:view' },
      { href: '/dashboard/backoffice/cadastros-auxiliares/marcas', icon: BookmarkCheck, label: 'Marcas', tip: 'Gerenciar Marcas Globais', permission: 'backoffice:tabelas:view' },
      { href: '/dashboard/backoffice/cadastros-auxiliares/modelos', icon: Layers, label: 'Modelos', tip: 'Gerenciar Modelos Globais', permission: 'backoffice:tabelas:view' },
      { href: '/dashboard/backoffice/cadastros-auxiliares/categorias', icon: FolderTree, label: 'Categorias de Produto', tip: 'Gerenciar Categorias Globais', permission: 'backoffice:tabelas:view' },
      { href: '/dashboard/backoffice/cadastros-auxiliares/culturas', icon: Sprout, label: 'Culturas e Variedades', tip: 'Gerenciar Culturas Globais', permission: 'backoffice:tabelas:view' },
      { href: '/backoffice/clima/modelos', icon: Target, label: 'Modelos Fitossanitários', tip: 'Gestão de modelos base da plataforma', permission: 'backoffice:tabelas:view' },
      { href: '/dashboard/backoffice/cadastros-auxiliares/unidades-medida', icon: Ruler, label: 'Unidades de Medida', tip: 'Gerenciar Unidades Globais', permission: 'backoffice:uom:view' },
      { href: '/dashboard/backoffice/cadastros-auxiliares/unidades-conversoes', icon: ArrowLeftRight, label: 'Conversões de Unidade', tip: 'Fatores de Conversão entre Unidades', permission: 'backoffice:uom:view' },
    ],
  },
  {
    key: 'backoffice-configuracao',
    label: 'Configuração',
    icon: Settings,
    items: [
      { href: '/dashboard/backoffice/configuracoes', icon: Settings, label: 'Configurações do Sistema', tip: 'Config', permission: 'backoffice:config:view' },
      { href: '/dashboard/backoffice/integracoes/erp', icon: ArrowLeftRight, label: 'Integrações ERP', tip: 'Observabilidade e suporte das integrações', permission: 'backoffice:integrations:observe' },
      { href: '/dashboard/backoffice/usuarios', icon: Users, label: 'Usuários da Plataforma', tip: 'Usuários', permission: 'backoffice:usuarios:view' },
      { href: '/dashboard/backoffice/profiles', icon: Shield, label: 'Perfis Padrão do Sistema', tip: 'Perfis', permission: 'backoffice:profiles:view' },
    ],
  },
];

// ═══════════════════════════════════════════════════════════════════════════════
// Gestão de Acessos e Configurações (footer do tenant — sidebar e mega menu)
// ═══════════════════════════════════════════════════════════════════════════════

export const ACCESS_ITEMS: SidebarMenuItem[] = [
  { href: '/dashboard/settings/team', icon: Users, label: 'Equipe', tip: 'Equipe', permission: 'tenant:users:view' },
  { href: '/dashboard/settings/roles', icon: Shield, label: 'Perfis e Permissões', tip: 'Perfis', permission: 'tenant:permissions:view' },
  { href: '/dashboard/settings/seguranca', icon: Lock, label: 'Segurança', tip: 'Segurança', permission: 'tenant:settings:view' },
  { href: '/dashboard/settings/sessoes', icon: Clock, label: 'Sessões Ativas', tip: 'Sessões', permission: 'tenant:settings:view' },
];

export const SETTINGS_ITEMS: SidebarMenuItem[] = [
  { href: '/dashboard/settings/account', icon: UserCircle, label: 'Meu Perfil', tip: 'Meu Perfil' },
  { href: '/dashboard/settings/tenant', icon: Landmark, label: 'Meu Produtor', tip: 'Dados do Produtor', permission: 'tenant:settings:view' },
  { href: '/dashboard/implantacao/wizard', icon: Settings2, label: 'Wizard de Implantação', tip: 'Implantação operacional assistida', permission: 'tenant:settings:view' },
  { href: '/dashboard/configuracoes/globais', icon: Hash, label: 'Configurações Globais', tip: 'Ano agrícola, unidades, categorias e códigos de referência', permission: 'tenant:settings:view' },
  { href: '/dashboard/settings/integracoes/erp', icon: ArrowLeftRight, label: 'Integrações ERP', tip: 'Configuração ERP do produtor', permission: 'integrations:view' },
  { href: '/dashboard/settings/integracoes/clima/openweather', icon: CloudSun, label: 'OpenWeather', tip: 'Configuração climática', permission: 'integrations:view' },
  { href: '/dashboard/settings/integracoes/tara', icon: Scale, label: 'Balança Pondaxis', tip: 'Configuração da conexão com o Pondaxis', permission: 'integrations:view' },
  { href: '/dashboard/settings/billing', icon: CreditCard, label: 'Assinatura e Pagamentos', tip: 'Assinatura', permission: 'tenant:billing:view' },
  { href: '/dashboard/settings/ia', icon: BrainCircuit, label: 'Uso de IA', tip: 'Inteligência Artificial', permission: 'tenant:billing:view' },
  { href: '/dashboard/settings/kb', icon: Book, label: 'Base de Conhecimento', tip: 'Wiki' },
  { href: '/dashboard/settings/smtp', icon: Mail, label: 'Configuração de E-mail', tip: 'E-mail', permission: 'tenant:settings:view' },
  { href: '/dashboard/settings/support', icon: MessageSquare, label: 'Ajuda e Suporte', tip: 'Suporte' },
];
