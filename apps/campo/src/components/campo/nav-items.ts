import {
  Beef,
  BookText,
  ClipboardList,
  Dna,
  Home,
  RefreshCw,
  Scale,
  ShieldHalf,
  Sparkles,
  Sprout,
  Syringe,
  Wheat,
  type LucideIcon,
} from "lucide-react";

export interface CampoNavItem {
  id: string;
  label: string;
  shortLabel: string;
  href: string;
  icon: LucideIcon;
  description: string;
}

export interface CampoNavModuleGroup {
  id: "operacao-campo" | "modulo-agricola" | "modulo-pecuaria";
  label: string;
  contractKey?: "agricola" | "pecuaria";
  items: CampoNavItem[];
}

export interface CampoRouteMeta {
  title: string;
  subtitle: string;
  isRoot: boolean;
  backHref: string;
}

const OPERACAO_ITEMS: CampoNavItem[] = [
  {
    id: "home",
    label: "Início Operacional",
    shortLabel: "Início",
    href: "/home",
    icon: Home,
    description: "Visão do turno, clima e atalhos rápidos",
  },
  {
    id: "tarefas",
    label: "Tarefas Programadas",
    shortLabel: "Tarefas",
    href: "/tarefas",
    icon: ClipboardList,
    description: "Execução e acompanhamento de ordens de campo",
  },
  {
    id: "caderno",
    label: "Caderno de Campo",
    shortLabel: "Caderno",
    href: "/caderno",
    icon: BookText,
    description: "Registros oficiais com fotos e georreferenciamento",
  },
  {
    id: "recomendacoes",
    label: "Recomendações",
    shortLabel: "Alertas",
    href: "/recomendacoes",
    icon: Sparkles,
    description: "Orientações operacionais e inteligência de campo",
  },
  {
    id: "sync",
    label: "Sincronização Offline",
    shortLabel: "Sync",
    href: "/sync",
    icon: RefreshCw,
    description: "Fila local, conflitos e diagnóstico do dispositivo",
  },
];

const AGRICOLA_ITEMS: CampoNavItem[] = [
  {
    id: "agricultura",
    label: "Painel Agrícola",
    shortLabel: "Agrícola",
    href: "/agricultura",
    icon: Sprout,
    description: "Talhões, safras e atividades agrícolas do dia",
  },
  {
    id: "aplicacao",
    label: "Aplicação de Insumo",
    shortLabel: "Aplicação",
    href: "/campo/aplicacao",
    icon: Sprout,
    description: "Defensivos e fertilizantes com validação de clima",
  },
  {
    id: "colheita",
    label: "Registro de Colheita",
    shortLabel: "Colheita",
    href: "/campo/colheita",
    icon: Wheat,
    description: "Apontamento de cargas, umidade e produtividade",
  },
  {
    id: "epi",
    label: "Entrega de EPI",
    shortLabel: "EPI",
    href: "/campo/epi",
    icon: ShieldHalf,
    description: "Comprovante operacional de segurança individual",
  },
];

const PECUARIA_ITEMS: CampoNavItem[] = [
  {
    id: "pecuaria",
    label: "Painel Pecuária",
    shortLabel: "Pecuária",
    href: "/pecuaria",
    icon: Beef,
    description: "Manejo de lotes, sanidade e reprodução",
  },
  {
    id: "pesagem",
    label: "Pesagem de Rebanho",
    shortLabel: "Pesagem",
    href: "/campo/pesagem",
    icon: Scale,
    description: "Registro de peso individual ou por lote no curral",
  },
  {
    id: "vacinacao",
    label: "Vacinação e Sanidade",
    shortLabel: "Vacinação",
    href: "/campo/vacinacao",
    icon: Syringe,
    description: "Aplicação sanitária por lote com baixa de insumo",
  },
  {
    id: "reproducao",
    label: "Manejo Reprodutivo",
    shortLabel: "Reprodução",
    href: "/campo/reproducao/cobertura",
    icon: Dna,
    description: "Cobertura, diagnóstico, parto e desmama",
  },
];

/**
 * Verifica se uma rota de navegação está ativa considerando sub-rotas operacionais.
 *
 * Args:
 *   pathname (string): Caminho atual da URL.
 *   href (string): Caminho alvo do item de navegação.
 *
 * Return:
 *   boolean: Verdadeiro quando o item corresponde à rota ativa.
 *
 * Raises:
 *   Nenhuma exceção é lançada.
 */
export function isCampoRouteActive(pathname: string, href: string): boolean {
  if (pathname === href || pathname.startsWith(`${href}/`)) {
    return true;
  }
  if (href === "/tarefas" && pathname.startsWith("/campo/tarefa")) {
    return true;
  }
  if (
    href === "/agricultura" &&
    (pathname.startsWith("/campo/aplicacao") ||
      pathname.startsWith("/campo/colheita") ||
      pathname.startsWith("/campo/epi"))
  ) {
    return true;
  }
  if (
    href === "/pecuaria" &&
    (pathname.startsWith("/campo/pesagem") ||
      pathname.startsWith("/campo/vacinacao") ||
      pathname.startsWith("/campo/reproducao"))
  ) {
    return true;
  }
  return false;
}

/**
 * Filtra os grupos de módulos exibidos na sidebar conforme os módulos contratados na sessão.
 *
 * Args:
 *   contractedModules (readonly string[] | undefined): Lista de módulos habilitados no dispositivo.
 *
 * Return:
 *   CampoNavModuleGroup[]: Grupos de menu estruturados por módulo contratado.
 *
 * Raises:
 *   Nenhuma exceção é lançada.
 */
export function getContractedCampoModuleGroups(
  contractedModules?: readonly string[]
): CampoNavModuleGroup[] {
  const normalized = (contractedModules ?? []).map((m) => m.toLowerCase());
  const hasUnrestricted = normalized.length === 0;
  const hasAgricola = hasUnrestricted || normalized.includes("agricola") || normalized.includes("agricultura");
  const hasPecuaria = hasUnrestricted || normalized.includes("pecuaria");

  const groups: CampoNavModuleGroup[] = [
    {
      id: "operacao-campo",
      label: "Operação de Campo",
      items: OPERACAO_ITEMS,
    },
  ];

  if (hasAgricola) {
    groups.push({
      id: "modulo-agricola",
      label: "Módulo Agrícola",
      contractKey: "agricola",
      items: AGRICOLA_ITEMS,
    });
  }

  if (hasPecuaria) {
    groups.push({
      id: "modulo-pecuaria",
      label: "Módulo Pecuária",
      contractKey: "pecuaria",
      items: PECUARIA_ITEMS,
    });
  }

  return groups;
}

const ROUTE_META_MAP: Array<{ match: string; meta: CampoRouteMeta }> = [
  {
    match: "/agricultura",
    meta: { title: "Agricultura", subtitle: "Manejo de lavoura e safras", isRoot: false, backHref: "/home" },
  },
  {
    match: "/pecuaria",
    meta: { title: "Pecuária", subtitle: "Manejo de lotes e rebanho", isRoot: false, backHref: "/home" },
  },
  {
    match: "/tarefas",
    meta: { title: "Tarefas", subtitle: "Ordens programadas do turno", isRoot: false, backHref: "/home" },
  },
  {
    match: "/caderno",
    meta: { title: "Caderno de Campo", subtitle: "Registro técnico georreferenciado", isRoot: false, backHref: "/home" },
  },
  {
    match: "/recomendacoes",
    meta: { title: "Recomendações", subtitle: "Inteligência operacional offline", isRoot: false, backHref: "/home" },
  },
  {
    match: "/sync",
    meta: { title: "Sincronização", subtitle: "Fila offline e integridade", isRoot: false, backHref: "/home" },
  },
  {
    match: "/campo/aplicacao",
    meta: { title: "Aplicação de Insumo", subtitle: "Registro operacional agrícola", isRoot: false, backHref: "/agricultura" },
  },
  {
    match: "/campo/colheita",
    meta: { title: "Colheita", subtitle: "Apontamento de produção", isRoot: false, backHref: "/agricultura" },
  },
  {
    match: "/campo/epi",
    meta: { title: "Entrega de EPI", subtitle: "Segurança do trabalho", isRoot: false, backHref: "/agricultura" },
  },
  {
    match: "/campo/pesagem",
    meta: { title: "Pesagem de Rebanho", subtitle: "Manejo de curral", isRoot: false, backHref: "/pecuaria" },
  },
  {
    match: "/campo/vacinacao",
    meta: { title: "Vacinação", subtitle: "Controle sanitário", isRoot: false, backHref: "/pecuaria" },
  },
  {
    match: "/campo/reproducao",
    meta: { title: "Reprodução", subtitle: "Cobertura, prenhez, parto e desmama", isRoot: false, backHref: "/pecuaria" },
  },
  {
    match: "/campo/tarefa",
    meta: { title: "Execução de Tarefa", subtitle: "Ordem operacional em andamento", isRoot: false, backHref: "/tarefas" },
  },
];

/**
 * Resolve metadados contextuais da rota atual para exibição no App Bar adaptativo.
 *
 * Args:
 *   pathname (string): Caminho atual da URL.
 *
 * Return:
 *   CampoRouteMeta: Título, subtítulo, flag de rota raiz e destino de retorno.
 *
 * Raises:
 *   Nenhuma exceção é lançada.
 */
export function resolveCampoRouteMeta(pathname: string): CampoRouteMeta {
  if (pathname === "/home" || pathname === "/") {
    return {
      title: "Início Operacional",
      subtitle: "Operação offline-first no campo",
      isRoot: true,
      backHref: "/home",
    };
  }

  const matched = ROUTE_META_MAP.find(
    (entry) => pathname === entry.match || pathname.startsWith(`${entry.match}/`)
  );

  if (matched) {
    return matched.meta;
  }

  return {
    title: "Operação de Campo",
    subtitle: "AgroCampo PWA",
    isRoot: false,
    backHref: "/home",
  };
}

