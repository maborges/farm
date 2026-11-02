import {
  Calculator,
  CloudSun,
  Home,
  TrendingUp,
  User,
  Users,
  type LucideIcon,
} from "lucide-react";

export interface AgroNavItem {
  href: string;
  label: string;
  shortLabel: string;
  pageTitle: string;
  pageSubtitle: string;
  icon: LucideIcon;
  group: "operacional" | "identidade";
  showInBottomDock: boolean;
  showInTopNav: boolean;
}

export const AGRO_NAV_ITEMS: AgroNavItem[] = [
  {
    href: "/",
    label: "Início",
    shortLabel: "Início",
    pageTitle: "DeepFarms Agro",
    pageSubtitle: "Central do Produtor",
    icon: Home,
    group: "operacional",
    showInBottomDock: true,
    showInTopNav: true,
  },
  {
    href: "/clima",
    label: "Clima",
    shortLabel: "Clima",
    pageTitle: "Clima & Pulverização",
    pageSubtitle: "Agrometeorologia horária",
    icon: CloudSun,
    group: "operacional",
    showInBottomDock: true,
    showInTopNav: true,
  },
  {
    href: "/mercado",
    label: "Mercado",
    shortLabel: "Mercado",
    pageTitle: "Mercado & Cotações",
    pageSubtitle: "PTAX, BCB, IBGE e DERAL",
    icon: TrendingUp,
    group: "operacional",
    showInBottomDock: true,
    showInTopNav: true,
  },
  {
    href: "/calculadoras",
    label: "Calculadoras",
    shortLabel: "Cálculos",
    pageTitle: "Calculadoras Rurais",
    pageSubtitle: "5 ferramentas 100% offline",
    icon: Calculator,
    group: "operacional",
    showInBottomDock: true,
    showInTopNav: true,
  },
  {
    href: "/comunidade",
    label: "Comunidade",
    shortLabel: "Rede",
    pageTitle: "Comunidade Agro",
    pageSubtitle: "Rede técnica de produtores",
    icon: Users,
    group: "identidade",
    showInBottomDock: false,
    showInTopNav: false,
  },
  {
    href: "/conta",
    label: "Conta",
    shortLabel: "Conta",
    pageTitle: "Minha Conta",
    pageSubtitle: "Identidade individual gratuita",
    icon: User,
    group: "identidade",
    showInBottomDock: true,
    showInTopNav: true,
  },
];

/**
 * Localiza o item de navegação correspondente à rota ativa.
 *
 * Args:
 *   pathname: Caminho da URL atual.
 *
 * Return:
 *   Item de navegação ativo ou o item inicial por padrão.
 *
 * Raises:
 *   Nenhuma exceção é lançada.
 */
export function getActiveNavItem(pathname: string): AgroNavItem {
  if (pathname === "/") {
    return AGRO_NAV_ITEMS[0];
  }
  const found = AGRO_NAV_ITEMS.find(
    (item) => item.href !== "/" && pathname.startsWith(item.href)
  );
  return found ?? AGRO_NAV_ITEMS[0];
}

