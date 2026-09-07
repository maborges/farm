"use client";

import { ReactNode } from "react";
import { useHasModule } from "@/hooks/use-has-module";
import { ModuloId, ModuloMetadata } from "@/lib/constants/modulos";
import Link from "next/link";
import { Lock, Sparkles } from "lucide-react";

interface ModuleGateProps {
    moduleId?: ModuloId | string;
    children: ReactNode;
    fallback?: ReactNode; // O que mostrar se ele NÃO tiver o módulo (ex: Tela de Upgrade)
    showUpgradePrompt?: boolean; // Se true, mostra prompt de upgrade padrão
}

/**
 * HOC (Higher Order Component) para "Feature Flags" do SaaS.
 * Você envelopa qualquer pedaço de tela que custa dinheiro por trás de um ModuleGate.
 * Se o Tenant logado não possui esse pacote na Store, ele sequer renderiza.
 *
 * @example
 * ```tsx
 * import { ModuleGate } from "@/components/shared/module-gate";
 * import { Modulos } from "@/lib/constants/modulos";
 *
 * <ModuleGate moduleId={Modulos.AGRICOLA_PLANEJAMENTO}>
 *   <ConteudoDoModulo />
 * </ModuleGate>
 * ```
 */
export function ModuleGate({
    moduleId,
    children,
    fallback,
    showUpgradePrompt = false,
}: ModuleGateProps) {
    const hasModule = useHasModule(moduleId as any);

    if (!moduleId) {
        return <>{children}</>;
    }

    if (!hasModule) {
        // Se foi fornecido um fallback customizado, usar ele
        if (fallback !== undefined) {
            return <>{fallback}</>;
        }

        // Se showUpgradePrompt, mostrar tela de upgrade
        if (showUpgradePrompt) {
            const modulo = ModuloMetadata[moduleId];
            return (
                <div className="flex items-center justify-center min-h-[400px] p-8">
                    <div className="max-w-md text-center space-y-4">
                        <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-yellow-100 dark:bg-yellow-900/20">
                            <Lock className="w-8 h-8 text-yellow-600 dark:text-yellow-400" />
                        </div>
                        <h2 className="text-2xl font-bold">Módulo não contratado</h2>
                        <p className="text-muted-foreground">
                            O módulo <strong>{modulo?.nome || moduleId}</strong> não está
                            incluído no seu plano atual. Compare Planejamento, Profissional e Enterprise
                            para liberar este recurso.
                        </p>
                        {modulo?.precoMensal && (
                            <p className="text-sm text-muted-foreground">
                                A partir de{" "}
                                <span className="font-semibold text-foreground">
                                    R$ {modulo.precoMensal.toFixed(2)}/mês
                                </span>
                            </p>
                        )}
                        <div className="pt-4">
                            <Link
                                href="/settings/billing"
                                className="inline-flex items-center gap-2 px-6 py-3 bg-primary text-primary-foreground rounded-sm hover:bg-primary/90 transition-colors font-medium"
                            >
                                <Sparkles className="w-4 h-4" />
                                Fazer Upgrade do Plano
                            </Link>
                        </div>
                    </div>
                </div>
            );
        }

        // Por padrão, não renderiza nada
        return null;
    }

    return <>{children}</>;
}

/**
 * Componente inline para mostrar badge de módulo
 */
export function ModuleBadge({ moduleId }: { moduleId: ModuloId | string }) {
    const modulo = ModuloMetadata[moduleId];
    const hasModule = useHasModule(moduleId);

    if (!modulo) return null;

    return (
        <span
            className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${
                hasModule
                    ? "bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400"
                    : "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400"
            }`}
        >
            {modulo.icone && <span>{modulo.icone}</span>}
            <span>{modulo.nome}</span>
            {!hasModule && <Lock className="w-3 h-3 ml-1" />}
        </span>
    );
}
