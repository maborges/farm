import Link from "next/link";
import { Building2, Smartphone } from "lucide-react";

interface ProductSwitcherProps {
  active: "gestao" | "agro";
  className?: string;
}

/**
 * Seletor segmentado de produtos (DeepFarms Gestão vs DeepFarms Agro).
 * Permite alternar de forma intuitiva e imediata entre os dois módulos/páginas da plataforma.
 */
export function ProductSwitcher({ active, className = "" }: ProductSwitcherProps) {
  const isGestao = active === "gestao";
  const isAgro = active === "agro";

  return (
    <nav
      aria-label="Alternar entre produtos DeepFarms"
      className={`inline-flex items-center gap-1 rounded-full border border-border/70 bg-muted/60 p-1 shadow-xs backdrop-blur-xs ${className}`}
    >
      <Link
        href="/"
        aria-current={isGestao ? "page" : undefined}
        className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-medium transition-colors ${
          isGestao
            ? "bg-background text-foreground shadow-xs ring-1 ring-border/50"
            : "text-muted-foreground hover:bg-background/50 hover:text-foreground"
        }`}
      >
        <Building2 className={`size-3.5 shrink-0 ${isGestao ? "text-primary" : "text-muted-foreground/70"}`} />
        <span>Gestão Rural</span>
      </Link>

      <Link
        href="/agro"
        aria-current={isAgro ? "page" : undefined}
        className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-medium transition-colors ${
          isAgro
            ? "bg-background text-foreground shadow-xs ring-1 ring-border/50"
            : "text-muted-foreground hover:bg-background/50 hover:text-foreground"
        }`}
      >
        <Smartphone className={`size-3.5 shrink-0 ${isAgro ? "text-primary" : "text-muted-foreground/70"}`} />
        <span>Agro Ferramentas</span>
        <span
          className={`rounded-full px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wider ${
            isAgro
              ? "bg-primary/15 text-primary"
              : "bg-muted-foreground/15 text-muted-foreground"
          }`}
        >
          Grátis
        </span>
      </Link>
    </nav>
  );
}

