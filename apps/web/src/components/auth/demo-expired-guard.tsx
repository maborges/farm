"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, CalendarClock, CheckCircle2, LifeBuoy, Loader2, LogOut, Send, ShieldAlert } from "lucide-react";
import { toast } from "sonner";
import { useDemoAccess } from "@/hooks/use-demo-access";
import { useAppStore } from "@/lib/stores/app-store";
import { apiFetch } from "@/lib/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button, buttonVariants } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

interface SupportTicketSummary {
    id: string;
    assunto: string;
    categoria: string;
    status: string;
    created_at: string;
}

const DEMO_RESTRICTED_ROUTE_PREFIXES = [
    "/cadastros/pessoas",
    "/dashboard/settings/team",
    "/dashboard/settings/roles",
    "/dashboard/settings/seguranca",
    "/dashboard/settings/sessoes",
    "/dashboard/settings/tenant",
    "/dashboard/settings/billing",
    "/dashboard/settings/smtp",
    "/dashboard/settings/ia",
    "/dashboard/settings/integracoes",
    "/dashboard/implantacao/wizard",
    "/dashboard/configuracoes/globais",
] as const;

/**
 * Guard que bloqueia módulos operacionais quando a janela de 15 dias de demonstração expirou,
 * e impede acesso direto por URL a telas administrativas ou com dados de pessoas/outros usuários.
 */
export function DemoExpiredGuard({ children }: { children: React.ReactNode }) {
    const pathname = usePathname();
    const router = useRouter();
    const queryClient = useQueryClient();
    const logout = useAppStore((s) => s.logout);
    const { isReadOnly, isDemoVisitor, isDemoExpired, validadeAcesso, prorrogacoesCount } = useDemoAccess();
    const [mensagem, setMensagem] = useState(
        "Gostaria de solicitar a prorrogação de mais 15 dias corridos no ambiente de demonstração DeepFarms."
    );

    const isSupportPath = pathname === "/dashboard/settings/support" || pathname.startsWith("/dashboard/settings/support/");

    const { data: tickets, isLoading: loadingTickets } = useQuery<SupportTicketSummary[]>({
        queryKey: ["support-tickets-demo-guard"],
        queryFn: () => apiFetch<SupportTicketSummary[]>("/support/tickets", { suppressErrorLog: true }),
        enabled: isDemoExpired && !isSupportPath,
    });

    const openExtensionTicket = tickets?.find(
        (t) =>
            t.categoria === "PRORROGACAO_DEMO" &&
            ["ABERTO", "EM_ATENDIMENTO", "AGUARDANDO_CLIENTE"].includes(t.status)
    );

    const requestMutation = useMutation({
        mutationFn: () =>
            apiFetch<SupportTicketSummary>("/support/tickets", {
                method: "POST",
                body: {
                    assunto: "Solicitação de prorrogação de demonstração (+15 dias)",
                    categoria: "PRORROGACAO_DEMO",
                    prioridade: "ALTA",
                    mensagem_inicial: mensagem.trim() || "Solicito prorrogação de +15 dias no acesso de demonstração.",
                },
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["support-tickets-demo-guard"] });
            queryClient.invalidateQueries({ queryKey: ["my-tickets"] });
            toast.success("Solicitação enviada ao time comercial! Acompanhe pelo módulo de Suporte.");
        },
        onError: (err: Error) => {
            toast.error(err.message || "Não foi possível enviar a solicitação.");
        },
    });

    const isRestrictedDemoRoute =
        (isReadOnly || isDemoVisitor) &&
        !isDemoExpired &&
        DEMO_RESTRICTED_ROUTE_PREFIXES.some(
            (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`)
        );

    if (isRestrictedDemoRoute) {
        return (
            <div className="mx-auto flex min-h-[65vh] w-full max-w-lg items-center justify-center p-4 sm:p-6">
                <Card className="w-full rounded-sm border-border bg-card shadow-md">
                    <CardHeader className="border-b pb-4">
                        <Badge
                            variant="outline"
                            className="w-fit rounded-sm border-sky-500/40 bg-sky-500/10 text-sky-700 dark:text-sky-300"
                        >
                            Modo Demonstração
                        </Badge>
                        <CardTitle className="mt-2 flex items-center gap-2 text-lg">
                            <ShieldAlert className="size-5 text-amber-600 dark:text-amber-400" />
                            Área restrita na demonstração
                        </CardTitle>
                        <CardDescription className="text-xs">
                            Por segurança e privacidade (LGPD), informações de pessoas/usuários e configurações administrativas não ficam disponíveis para contas de demonstração.
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="flex flex-wrap items-center justify-between gap-2 pt-4">
                        <p className="text-xs text-muted-foreground">
                            Os módulos operacionais (Agrícola, Pecuária, Financeiro, Estoque, Frota e Ambiental) continuam liberados para consulta.
                        </p>
                        <Link
                            href="/dashboard"
                            className={cn(buttonVariants({ variant: "outline", size: "sm" }), "rounded-sm gap-1.5")}
                        >
                            <ArrowLeft className="size-3.5" />
                            <span>Voltar ao painel</span>
                        </Link>
                    </CardContent>
                </Card>
            </div>
        );
    }

    if (!isDemoExpired || isSupportPath) {
        return <>{children}</>;
    }

    return (
        <div className="mx-auto flex min-h-[70vh] w-full max-w-xl items-center justify-center p-4 sm:p-6">
            <Card className="w-full rounded-sm border-border bg-card shadow-md">
                <CardHeader className="border-b pb-4">
                    <div className="flex items-center justify-between gap-2">
                        <Badge variant="outline" className="border-amber-500/40 bg-amber-500/10 text-amber-700 dark:text-amber-300">
                            Demonstração Expirada
                        </Badge>
                        {prorrogacoesCount > 0 && (
                            <span className="text-xs text-muted-foreground">
                                Prorrogações anteriores: {prorrogacoesCount}
                            </span>
                        )}
                    </div>
                    <CardTitle className="mt-2 flex items-center gap-2 text-lg">
                        <CalendarClock className="size-5 text-amber-600 dark:text-amber-400" />
                        Período de demonstração encerrado
                    </CardTitle>
                    <CardDescription className="text-xs">
                        {validadeAcesso
                            ? `Seu acesso de 15 dias venceu em ${new Date(`${validadeAcesso}T12:00:00`).toLocaleDateString("pt-BR")}.`
                            : "Seu período de demonstração na plataforma venceu."}{" "}
                        Solicite mais 15 dias de acesso diretamente pelo módulo de Suporte para avaliação pelo time comercial.
                    </CardDescription>
                </CardHeader>

                <CardContent className="space-y-4 pt-5">
                    {loadingTickets ? (
                        <div className="flex items-center gap-2 text-xs text-muted-foreground">
                            <Loader2 className="size-4 animate-spin" />
                            <span>Verificando solicitações em andamento...</span>
                        </div>
                    ) : openExtensionTicket ? (
                        <div className="rounded-sm border border-emerald-500/30 bg-emerald-500/10 p-3.5 text-xs space-y-2">
                            <div className="flex items-center gap-2 font-semibold text-emerald-800 dark:text-emerald-200">
                                <CheckCircle2 className="size-4 shrink-0" />
                                <span>Solicitação já enviada ao time comercial</span>
                            </div>
                            <p className="text-muted-foreground">
                                Chamado <strong>{openExtensionTicket.assunto}</strong> ({openExtensionTicket.status.replace("_", " ")}).
                                Assim que aprovado pelo Comercial, recarregue a página para retomar o acesso.
                            </p>
                            <Link
                                href="/dashboard/settings/support"
                                className={cn(buttonVariants({ variant: "outline", size: "sm" }), "rounded-sm gap-1.5")}
                            >
                                <LifeBuoy className="size-3.5" />
                                <span>Acompanhar no Suporte</span>
                            </Link>
                        </div>
                    ) : (
                        <div className="space-y-3">
                            <div className="space-y-1.5">
                                <Label htmlFor="demo-extension-msg" className="text-xs">
                                    Mensagem para o time comercial
                                </Label>
                                <Textarea
                                    id="demo-extension-msg"
                                    rows={3}
                                    value={mensagem}
                                    onChange={(e) => setMensagem(e.target.value)}
                                    className="text-sm rounded-sm"
                                    placeholder="Informe brevemente o motivo ou módulos que deseja continuar avaliando..."
                                />
                            </div>
                            <div className="flex flex-wrap items-center gap-2">
                                <Button
                                    type="button"
                                    variant="outline"
                                    size="sm"
                                    disabled={requestMutation.isPending}
                                    onClick={() => requestMutation.mutate()}
                                    className="gap-1.5 border-primary/50 text-primary hover:bg-primary/10"
                                >
                                    {requestMutation.isPending ? (
                                        <Loader2 className="size-3.5 animate-spin" />
                                    ) : (
                                        <Send className="size-3.5" />
                                    )}
                                    <span>Solicitar prorrogação (+15 dias)</span>
                                </Button>

                                <Button
                                    type="button"
                                    variant="outline"
                                    size="sm"
                                    onClick={() => router.push("/dashboard/settings/support")}
                                    className="gap-1.5"
                                >
                                    <LifeBuoy className="size-3.5" />
                                    <span>Abrir módulo de Suporte</span>
                                </Button>
                            </div>
                        </div>
                    )}

                    <div className="border-t pt-3 flex justify-end">
                        <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            onClick={() => void logout()}
                            className="gap-1.5 text-muted-foreground"
                        >
                            <LogOut className="size-3.5" />
                            <span>Sair da conta</span>
                        </Button>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
