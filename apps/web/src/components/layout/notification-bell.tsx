"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Bell, BellRing, CheckCheck, CloudRain, Satellite, Clock, Users, Beef, ShieldAlert, Loader2, ClipboardList, TriangleAlert, Lightbulb } from "lucide-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { useAppStore } from "@/lib/stores/app-store";
import { getWsBaseUrl } from "@/lib/runtime-config";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Separator } from "@/components/ui/separator";
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { formatDistanceToNow } from "date-fns";
import { ptBR } from "date-fns/locale";
import { toast } from "sonner";

// ── Types ─────────────────────────────────────────────────────────────────────

interface NotificacaoAcao {
    label: string;
    acao: string;
    endpoint: string;
    method?: string;
    body?: Record<string, unknown>;
}

interface Notificacao {
    id: string;
    tipo: string;
    titulo: string;
    mensagem: string;
    nivel: string;
    lida: boolean;
    origem: string | null;
    origem_id: string | null;
    meta: Record<string, unknown> & { acoes?: NotificacaoAcao[]; acao_executada?: string };
    created_at: string;
    read_at: string | null;
}

// ── Config per tipo ───────────────────────────────────────────────────────────

const TIPO_CONFIG: Record<string, { label: string; color: string; bg: string; icon: React.ComponentType<{ className?: string }> }> = {
    PREVISAO_CHUVA:       { label: "Clima",      color: "text-blue-600",   bg: "bg-blue-100 dark:bg-blue-950/40",   icon: CloudRain },
    NDVI_BAIXO:           { label: "NDVI",       color: "text-orange-600", bg: "bg-orange-100 dark:bg-orange-950/40", icon: Satellite },
    VENCIMENTO_APLICACAO: { label: "Carência",   color: "text-red-600",    bg: "bg-red-100 dark:bg-red-950/40",     icon: Clock },
    DIARIA_PENDENTE:      { label: "RH",         color: "text-yellow-600", bg: "bg-yellow-100 dark:bg-yellow-950/40", icon: Users },
    EMPREITADA_VENCENDO:  { label: "Empreitada", color: "text-purple-600", bg: "bg-purple-100 dark:bg-purple-950/40", icon: Beef },
    MANEJO_PENDENTE:      { label: "Pecuária",   color: "text-green-600",  bg: "bg-green-100 dark:bg-green-950/40", icon: ShieldAlert },
    // Financeiro
    PLANO_ACAO:           { label: "Ação",       color: "text-primary",    bg: "bg-primary/10",                     icon: ClipboardList },
    ALERTA_FINANCEIRO:    { label: "Financeiro", color: "text-destructive", bg: "bg-destructive/10",               icon: TriangleAlert },
    RECOMENDACAO:         { label: "Dica",       color: "text-amber-600",  bg: "bg-amber-100 dark:bg-amber-950/40", icon: Lightbulb },
    WORKFLOW_OPERACIONAL: { label: "Workflow",   color: "text-rose-600",   bg: "bg-rose-100 dark:bg-rose-950/40", icon: TriangleAlert },
    // alert_engine/ — todos os 5 domínios ativos desde 2026-08-14, ver
    // memória do projeto project_tres_sistemas_alertas_mapeados
    FINANCEIRO_VENCIMENTO_PROXIMO: { label: "Financeiro", color: "text-destructive", bg: "bg-destructive/10", icon: TriangleAlert },
    FINANCEIRO_VENCIDO:            { label: "Financeiro", color: "text-destructive", bg: "bg-destructive/10", icon: TriangleAlert },
    FINANCEIRO_FLUXO_CAIXA_CRITICO:{ label: "Financeiro", color: "text-destructive", bg: "bg-destructive/10", icon: TriangleAlert },
    FINANCEIRO_ORCAMENTO_EXCEDIDO: { label: "Financeiro", color: "text-destructive", bg: "bg-destructive/10", icon: TriangleAlert },
    AGRICULTURA_OPERACAO_ATRASADA:      { label: "Atraso",     color: "text-red-600",    bg: "bg-red-100 dark:bg-red-950/40",     icon: Clock },
    AGRICULTURA_SAFRA_SEM_MOVIMENTACAO: { label: "Safra",      color: "text-orange-600", bg: "bg-orange-100 dark:bg-orange-950/40", icon: Satellite },
    AGRICULTURA_TALHAO_SEM_ATUALIZACAO: { label: "Talhão",     color: "text-orange-600", bg: "bg-orange-100 dark:bg-orange-950/40", icon: Satellite },
    AGRICULTURA_CUSTO_ACIMA_PREVISTO:   { label: "Custo",      color: "text-destructive", bg: "bg-destructive/10",               icon: TriangleAlert },
    CAMPO_TAREFA_ATRASADA:  { label: "Campo", color: "text-red-600",   bg: "bg-red-100 dark:bg-red-950/40",   icon: Clock },
    CAMPO_TAREFA_INVALIDA:  { label: "Campo", color: "text-red-600",   bg: "bg-red-100 dark:bg-red-950/40",   icon: TriangleAlert },
    CAMPO_SYNC_FALHA:       { label: "Campo", color: "text-red-600",   bg: "bg-red-100 dark:bg-red-950/40",   icon: TriangleAlert },
    PECUARIA_LOTE_SEM_PESAGEM:                  { label: "Pecuária", color: "text-green-600", bg: "bg-green-100 dark:bg-green-950/40", icon: ShieldAlert },
    PECUARIA_VACINACAO_ATRASADA:                { label: "Pecuária", color: "text-green-600", bg: "bg-green-100 dark:bg-green-950/40", icon: ShieldAlert },
    PECUARIA_CUSTO_SANITARIO_ALTO:              { label: "Pecuária", color: "text-green-600", bg: "bg-green-100 dark:bg-green-950/40", icon: ShieldAlert },
    PECUARIA_REPRODUCAO_DIAGNOSTICO_PENDENTE:   { label: "Pecuária", color: "text-green-600", bg: "bg-green-100 dark:bg-green-950/40", icon: ShieldAlert },
    PECUARIA_REPRODUCAO_PARTO_PREVISTO:         { label: "Pecuária", color: "text-green-600", bg: "bg-green-100 dark:bg-green-950/40", icon: ShieldAlert },
    PECUARIA_REPRODUCAO_DESMAMA_PENDENTE:       { label: "Pecuária", color: "text-green-600", bg: "bg-green-100 dark:bg-green-950/40", icon: ShieldAlert },
    ESG_CERTIFICACAO_VENCIMENTO_PROXIMO: { label: "ESG", color: "text-amber-600", bg: "bg-amber-100 dark:bg-amber-950/40", icon: Lightbulb },
    ESG_CERTIFICACAO_VENCIDA:            { label: "ESG", color: "text-destructive", bg: "bg-destructive/10", icon: TriangleAlert },
    ESG_NAO_CONFORMIDADE_ABERTA:         { label: "ESG", color: "text-destructive", bg: "bg-destructive/10", icon: TriangleAlert },
    ESG_PLANO_ACAO_ATRASADO:             { label: "ESG", color: "text-rose-600", bg: "bg-rose-100 dark:bg-rose-950/40", icon: ClipboardList },
};

const DEFAULT_CONFIG = { label: "Alerta", color: "text-muted-foreground", bg: "bg-muted", icon: Bell };

function getTipoConfig(tipo: string) {
    return TIPO_CONFIG[tipo] ?? DEFAULT_CONFIG;
}

// Tela de lista correspondente a cada tipo de notificação real gerado em produção.
// Não existem páginas de detalhe por ID hoje (hedge/estoque/plano de ação são só
// listas) — o link leva à tela certa, não ao registro específico.
const ROTA_POR_TIPO: Record<string, string> = {
    ALERTA_FINANCEIRO: "/dashboard/financeiro",
    ALERTA_NDE: "/dashboard/agricola/monitoramento",
    ALERTA_AGRICOLA: "/dashboard/agricola",
    ESTOQUE_REPOSICAO: "/dashboard/operacional/estoque",
    ESTOQUE_BAIXO: "/dashboard/operacional/estoque",
    OPORTUNIDADE: "/dashboard/operacional/frota/inteligencia",
    HEDGE_CONTRACT_EXPIRING: "/dashboard/financeiro/hedge/contratos",
    HEDGE_MTM_PRICE_MISSING: "/dashboard/financeiro/hedge/mtm",
    HEDGE_CRITICAL_PNL: "/dashboard/financeiro/hedge/mtm",
    HEDGE_COBERTURA_INSUFICIENTE: "/dashboard/financeiro/hedge/exposicao",
    HEDGE_SOBRECOBERTURA: "/dashboard/financeiro/hedge/exposicao",
    HEDGE_VENDA_SEM_LASTRO: "/dashboard/financeiro/hedge/exposicao",
    VENCIMENTO_CONTAS_PAGAR: "/dashboard/financeiro/contas-pagar",
    VENCIMENTO_CONTAS_RECEBER: "/dashboard/financeiro/receitas",
    // gerados por alert_engine/generators/financeiro_generator.py (fonte única
    // de vencimentos desde 2026-08-14, ver memória project_tres_sistemas_alertas_mapeados)
    FINANCEIRO_VENCIMENTO_PROXIMO: "/dashboard/financeiro/contas-pagar",
    FINANCEIRO_VENCIDO: "/dashboard/financeiro/contas-pagar",
    CARENCIA_DEFENSIVO: "/dashboard/agricola/defensivos",
    // gerado por alert_engine/generators/agricultura_generator.py, substitui
    // o antigo tipo TAREFAS_ATRASADAS (aposentado)
    AGRICULTURA_OPERACAO_ATRASADA: "/dashboard/agricola/timeline",
    AGRICULTURA_SAFRA_SEM_MOVIMENTACAO: "/dashboard/agricola",
    AGRICULTURA_TALHAO_SEM_ATUALIZACAO: "/dashboard/agricola",
    AGRICULTURA_CUSTO_ACIMA_PREVISTO: "/dashboard/financeiro",
    CAMPO_TAREFA_ATRASADA: "/dashboard/operacional/campo/tarefas",
    CAMPO_TAREFA_INVALIDA: "/dashboard/operacional/campo/tarefas",
    CAMPO_SYNC_FALHA: "/dashboard/operacional/campo/tarefas",
    PECUARIA_LOTE_SEM_PESAGEM: "/dashboard/pecuaria/lotes",
    PECUARIA_VACINACAO_ATRASADA: "/dashboard/pecuaria/manejo",
    PECUARIA_CUSTO_SANITARIO_ALTO: "/dashboard/pecuaria/lotes",
    PECUARIA_REPRODUCAO_DIAGNOSTICO_PENDENTE: "/dashboard/pecuaria/manejo",
    PECUARIA_REPRODUCAO_PARTO_PREVISTO: "/dashboard/pecuaria/manejo",
    PECUARIA_REPRODUCAO_DESMAMA_PENDENTE: "/dashboard/pecuaria/manejo",
    ESG_CERTIFICACAO_VENCIMENTO_PROXIMO: "/dashboard/certificacoes-esg",
    ESG_CERTIFICACAO_VENCIDA: "/dashboard/certificacoes-esg",
    ESG_NAO_CONFORMIDADE_ABERTA: "/dashboard/certificacoes-esg",
    ESG_PLANO_ACAO_ATRASADO: "/dashboard/certificacoes-esg",
    PLANO_ACAO: "/dashboard/ia/plano-acao",
};

// ── Component ─────────────────────────────────────────────────────────────────

export function NotificationBell() {
    const router = useRouter();
    const { token, tenant } = useAppStore();
    const queryClient = useQueryClient();
    const [open, setOpen] = useState(false);
    const [wsNaoLidas, setWsNaoLidas] = useState<number | null>(null);
    const [wsConectado, setWsConectado] = useState(false);

    // ── REST queries ─────────────────────────────────────────────────────────
    const { data: notificacoes = [], isLoading } = useQuery<Notificacao[]>({
        queryKey: ["notificacoes"],
        queryFn: () => apiFetch<Notificacao[]>("/notificacoes/?limit=30"),
        enabled: open,
        staleTime: 30_000,
    });

    const marcarLidasMutation = useMutation({
        mutationFn: (ids?: string[]) =>
            apiFetch("/notificacoes/marcar-lidas", { method: "POST", body: JSON.stringify({ ids: ids ?? null }) }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["notificacoes"] });
            queryClient.invalidateQueries({ queryKey: ["notificacoes-nao-lidas-count"] });
            setWsNaoLidas(0);
        },
    });

    const demoMutation = useMutation({
        mutationFn: () => apiFetch("/notificacoes/demo", { method: "POST" }),
    });

    const [acaoConfirmando, setAcaoConfirmando] = useState<{ notif: Notificacao; item: NotificacaoAcao } | null>(null);

    const executarAcaoMutation = useMutation({
        mutationFn: async ({ notif, item }: { notif: Notificacao; item: NotificacaoAcao }) => {
            await apiFetch(item.endpoint, {
                method: item.method ?? "POST",
                body: item.body ? JSON.stringify(item.body) : undefined,
            });
            await apiFetch(`/notificacoes/${notif.id}/acao`, {
                method: "POST",
                body: JSON.stringify({ acao: item.acao }),
            });
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["notificacoes"] });
            queryClient.invalidateQueries({ queryKey: ["notificacoes-nao-lidas-count"] });
            toast.success("Ação executada");
            setAcaoConfirmando(null);
        },
        onError: () => {
            toast.error("Não foi possível executar a ação");
        },
    });

    // Fallback de polling: só é usado quando o WebSocket não está conectado
    // (falhou, token ausente, ainda reconectando). Evita ficar com a contagem
    // travada indefinidamente se o WS cair.
    const { data: pollingCount } = useQuery<{ count: number }>({
        queryKey: ["notificacoes-nao-lidas-count"],
        queryFn: () => apiFetch("/notificacoes/nao-lidas-count"),
        enabled: !!token && !!tenant && !wsConectado,
        refetchInterval: 60_000,
        staleTime: 30_000,
    });

    // ── WebSocket ─────────────────────────────────────────────────────────────
    useEffect(() => {
        if (!token || !tenant) return;

        let active = true;
        let ws: WebSocket | null = null;
        let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

        function connect() {
            if (!active || ws?.readyState === WebSocket.CONNECTING || ws?.readyState === WebSocket.OPEN) return;

            const wsBase = process.env.NEXT_PUBLIC_WS_URL ?? getWsBaseUrl().replace(/\/api\/v1$/, "");
            ws = new WebSocket(`${wsBase}/api/v1/notificacoes/ws?token=${token}`);

            ws.onopen = () => {
                if (active) setWsConectado(true);
            };

            ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    if (data.tipo === "ping") return;
                    if (data.tipo === "init" || data.tipo === "contagem_atualizada") {
                        setWsNaoLidas(data.nao_lidas ?? 0);
                    } else if (data.tipo === "nova_notificacao") {
                        setWsNaoLidas(prev => (prev ?? 0) + 1);
                        queryClient.invalidateQueries({ queryKey: ["notificacoes"] });
                    }
                } catch {
                    return;
                }
            };

            ws.onclose = (event) => {
                ws = null;
                if (active) setWsConectado(false);
                if (!active || event.code === 1008 || event.code === 1000) return;
                reconnectTimer = setTimeout(connect, 5000);
            };

            ws.onerror = () => {
                if (ws?.readyState === WebSocket.OPEN) ws.close();
            };
        }

        const connectTimer = setTimeout(connect, 0);

        return () => {
            active = false;
            setWsConectado(false);
            clearTimeout(connectTimer);
            if (reconnectTimer) clearTimeout(reconnectTimer);
            if (!ws) return;

            ws.onmessage = null;
            ws.onerror = null;
            ws.onclose = null;
            if (ws.readyState === WebSocket.OPEN) {
                ws.close(1000);
            } else if (ws.readyState === WebSocket.CONNECTING) {
                ws.onopen = () => ws.close(1000);
            }
        };
    }, [token, tenant, queryClient]);

    // Mark as read when opening sheet
    const handleOpenChange = useCallback((next: boolean) => {
        setOpen(next);
    }, []);

    const handleMarcarTodas = useCallback(() => {
        marcarLidasMutation.mutate(undefined);
    }, [marcarLidasMutation]);

    const handleClickNotificacao = useCallback((n: Notificacao) => {
        if (!n.lida) {
            marcarLidasMutation.mutate([n.id]);
        }
        const rota = ROTA_POR_TIPO[n.tipo];
        if (rota) {
            setOpen(false);
            router.push(rota);
        }
    }, [marcarLidasMutation, router]);

    const naoLidas = wsConectado
        ? (wsNaoLidas ?? notificacoes.filter(n => !n.lida).length)
        : (pollingCount?.count ?? notificacoes.filter(n => !n.lida).length);

    // ── Render ────────────────────────────────────────────────────────────────
    return (
        <>
            <Button
                variant="ghost"
                size="icon-sm"
                onClick={() => setOpen(true)}
                className="relative text-primary"
                aria-label="Notificações"
            >
                {naoLidas > 0 ? (
                    <BellRing className="size-4.5 animate-pulse text-primary" strokeWidth={2.5} />
                ) : (
                    <Bell className="size-4.5" strokeWidth={2} />
                )}
                {naoLidas > 0 && (
                    <span className="absolute -top-1 -right-1 flex h-4 min-w-4 items-center justify-center rounded-full border border-sidebar bg-primary px-1 text-[9px] font-bold leading-none text-sidebar shadow-sm ring-2 ring-sidebar">
                        {naoLidas > 9 ? "9+" : naoLidas}
                    </span>
                )}
            </Button>

            <Sheet open={open} onOpenChange={handleOpenChange}>
                <SheetContent className="w-[400px] flex flex-col p-0">
                    <SheetHeader className="px-4 pt-4 pb-3 border-b flex-shrink-0">
                        <div className="flex items-center justify-between">
                            <SheetTitle className="flex items-center gap-2 text-base">
                                <Bell className="size-4" />
                                Notificações
                                {naoLidas > 0 && (
                                    <Badge variant="destructive">
                                        {naoLidas}
                                    </Badge>
                                )}
                            </SheetTitle>
                            <div className="flex items-center gap-2">
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    className="h-7 text-xs"
                                    onClick={handleMarcarTodas}
                                    disabled={marcarLidasMutation.isPending || naoLidas === 0}
                                >
                                    <CheckCheck className="size-3.5 mr-1" />
                                    Marcar lidas
                                </Button>
                            </div>
                        </div>
                    </SheetHeader>

                    <div className="flex-1 overflow-y-auto">
                        {isLoading ? (
                            <div className="flex items-center justify-center py-12">
                                <Loader2 className="size-6 animate-spin text-muted-foreground" />
                            </div>
                        ) : notificacoes.length === 0 ? (
                            <div className="flex flex-col items-center justify-center py-16 text-center px-6">
                                <Bell className="size-10 text-muted-foreground/40 mb-3" />
                                <p className="font-medium text-sm">Sem notificações</p>
                                <p className="text-xs text-muted-foreground mt-1">Você está em dia com tudo!</p>
                                {process.env.NODE_ENV !== "production" && (
                                    <Button
                                        variant="outline"
                                        size="sm"
                                        className="mt-4 text-xs"
                                        onClick={() => demoMutation.mutate()}
                                        disabled={demoMutation.isPending}
                                    >
                                        {demoMutation.isPending ? (
                                            <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" />
                                        ) : null}
                                        Gerar alertas de demonstração
                                    </Button>
                                )}
                            </div>
                        ) : (
                            <div className="divide-y divide-border/50">
                                {notificacoes.map((n) => {
                                    const cfg = getTipoConfig(n.tipo);
                                    const Icon = cfg.icon;
                                    const timeAgo = formatDistanceToNow(new Date(n.created_at), {
                                        addSuffix: true,
                                        locale: ptBR,
                                    });

                                    const temRota = Boolean(ROTA_POR_TIPO[n.tipo]);

                                    const acoesDisponiveis = n.meta?.acoes ?? [];

                                    return (
                                        <div
                                            key={n.id}
                                            role="button"
                                            tabIndex={0}
                                            className={`w-full text-left px-4 py-3 flex gap-3 transition-colors hover:bg-muted/50 cursor-pointer ${!n.lida ? "bg-muted/20" : ""}`}
                                            onClick={() => handleClickNotificacao(n)}
                                            onKeyDown={(e) => { if (e.key === "Enter") handleClickNotificacao(n); }}
                                        >
                                            {/* Icon bubble */}
                                            <div className={`mt-0.5 flex-shrink-0 flex size-8 items-center justify-center rounded-full ${cfg.bg}`}>
                                                <Icon className={`size-4 ${cfg.color}`} />
                                            </div>

                                            {/* Content */}
                                            <div className="flex-1 min-w-0">
                                                <div className="flex items-start justify-between gap-2">
                                                    <span className={`text-sm font-medium leading-tight ${!n.lida ? "text-foreground" : "text-muted-foreground"}`}>
                                                        {n.titulo}
                                                    </span>
                                                    {!n.lida && (
                                                        <div className="size-2 rounded-full bg-primary shrink-0 mt-1.5" aria-hidden="true" />
                                                    )}
                                                </div>
                                                <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2 leading-relaxed">
                                                    {n.mensagem}
                                                </p>
                                                <div className="flex items-center gap-2 mt-1.5">
                                                    <Badge
                                                        variant="outline"
                                                        className={`${cfg.color} border-current`}
                                                    >
                                                        {cfg.label}
                                                    </Badge>
                                                    <span className="text-[10px] text-muted-foreground">{timeAgo}</span>
                                                    {!n.lida && <span className="sr-only">Não lida</span>}
                                                    {temRota && (
                                                        <span className="text-[10px] text-primary ml-auto">Ver detalhes →</span>
                                                    )}
                                                </div>
                                                {n.meta?.acao_executada && (
                                                    <p className="text-[10px] text-emerald-600 mt-1.5 flex items-center gap-1">
                                                        <CheckCheck className="size-3" /> Ação já executada
                                                    </p>
                                                )}
                                                {acoesDisponiveis.length > 0 && (
                                                    <div className="flex items-center gap-2 mt-2" onClick={(e) => e.stopPropagation()}>
                                                        {acoesDisponiveis.map((item) => (
                                                            <Button
                                                                key={item.acao}
                                                                size="sm"
                                                                variant={item.acao === "dismiss" ? "ghost" : "outline"}
                                                                className="h-7 text-xs"
                                                                onClick={() => setAcaoConfirmando({ notif: n, item })}
                                                            >
                                                                {item.label}
                                                            </Button>
                                                        ))}
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        )}
                    </div>

                    {notificacoes.length > 0 && process.env.NODE_ENV !== "production" && (
                        <div className="border-t px-4 py-3 flex-shrink-0">
                            <Button
                                variant="ghost"
                                size="sm"
                                className="w-full text-xs text-muted-foreground"
                                onClick={() => demoMutation.mutate()}
                                disabled={demoMutation.isPending}
                            >
                                {demoMutation.isPending ? <Loader2 className="h-3 w-3 mr-1 animate-spin" /> : null}
                                + Gerar alertas de demonstração
                            </Button>
                        </div>
                    )}
                </SheetContent>
            </Sheet>

            <AlertDialog open={!!acaoConfirmando} onOpenChange={(v) => { if (!v) setAcaoConfirmando(null); }}>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>{acaoConfirmando?.item.label}</AlertDialogTitle>
                        <AlertDialogDescription>
                            Confirma a ação &quot;{acaoConfirmando?.item.label}&quot; para &quot;{acaoConfirmando?.notif.titulo}&quot;?
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel disabled={executarAcaoMutation.isPending}>Cancelar</AlertDialogCancel>
                        <AlertDialogAction
                            disabled={executarAcaoMutation.isPending}
                            onClick={() => acaoConfirmando && executarAcaoMutation.mutate(acaoConfirmando)}
                        >
                            {executarAcaoMutation.isPending ? <Loader2 className="size-3.5 mr-1 animate-spin" /> : null}
                            Confirmar
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>
        </>
    );
}
