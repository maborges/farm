"use client";

import Link from "next/link";
import { Eye, LifeBuoy } from "lucide-react";
import { useDemoAccess } from "@/hooks/use-demo-access";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

/**
 * Faixa discreta no topo exibida apenas para usuários em ambiente de demonstração somente consulta.
 */
export function DemoModeBanner() {
    const { isDemoVisitor, isReadOnly, isDemoExpired, diasRestantes } = useDemoAccess();

    if ((!isDemoVisitor && !isReadOnly) || isDemoExpired) {
        return null;
    }

    const prazoLabel =
        typeof diasRestantes === "number"
            ? diasRestantes === 0
                ? "Último dia de acesso"
                : `${diasRestantes} dia(s) restante(s)`
            : "Acesso temporário";

    return (
        <div
            role="status"
            data-testid="demo-mode-banner"
            className="w-full border-b border-sky-500/30 bg-sky-500/10 px-4 py-1.5 text-xs text-sky-950 dark:text-sky-100"
        >
            <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2 min-w-0">
                    <Eye className="size-3.5 shrink-0 text-sky-600 dark:text-sky-400" />
                    <span className="font-semibold">Modo Demonstração (Somente Consulta)</span>
                    <span className="hidden sm:inline text-muted-foreground">
                        · Navegue livremente pelos módulos; alterações de dados estão desabilitadas.
                    </span>
                    <span className="rounded-sm border border-sky-500/30 bg-background/70 px-1.5 py-0.5 text-[11px] font-medium">
                        {prazoLabel}
                    </span>
                </div>

                <Link
                    href="/dashboard/settings/support"
                    className={cn(
                        buttonVariants({ variant: "outline", size: "sm" }),
                        "h-7 gap-1.5 rounded-sm border-sky-500/40 text-xs"
                    )}
                >
                    <LifeBuoy className="size-3.5 text-sky-600 dark:text-sky-400" />
                    <span>Suporte / Prorrogação</span>
                </Link>
            </div>
        </div>
    );
}
