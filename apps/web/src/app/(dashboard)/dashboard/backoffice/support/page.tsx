"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { useAppStore } from "@/lib/stores/app-store";
import {
    Send, CheckCircle,
    ArrowLeft, User, Building, LifeBuoy,
    Clock, Wifi, WifiOff, Loader2, LogIn, CalendarPlus,
} from "lucide-react";
import { ImpersonateTenantDialog } from "@/components/backoffice/impersonate-tenant-dialog";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { DataTable, ColumnDef } from "@/components/ui/data-table";
import { useState, useEffect, useRef, useCallback } from "react";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";
import { toast } from "sonner";
import { ScrollArea } from "@/components/ui/scroll-area";
import { PageHeader } from "@/components/shared/page-header";
import { getWsBaseUrl } from "@/lib/runtime-config";

// ─── Types ────────────────────────────────────────────────────────────────────

interface AdminTicket {
    id: string;
    tenant_id?: string;
    tenant_nome: string;
    usuario_nome: string;
    usuario_email?: string | null;
    assunto: string;
    categoria: string;
    status: string;
    prioridade: string;
    created_at: string;
    is_demo_tenant?: boolean;
    data_validade_acesso?: string | null;
    demo_prorrogacoes_count?: number;
}

interface AdminMessage {
    id: string;
    conteudo: string;
    is_admin_reply: boolean;
    created_at: string;
}

interface AdminTicketDetail extends AdminTicket {
    mensagens: AdminMessage[];
}

// ─── WebSocket Hook (Admin) ───────────────────────────────────────────────────

function useAdminSupportWS(ticketId: string | null, onMessage: (msg: AdminMessage) => void) {
    const wsRef = useRef<WebSocket | null>(null);
    const [isConnected, setIsConnected] = useState(false);
    const { token } = useAppStore.getState();
    const onMessageRef = useRef(onMessage);
    onMessageRef.current = onMessage;

    useEffect(() => {
        if (!ticketId || !token) return;

        const WS_BASE = getWsBaseUrl();

        const ws = new WebSocket(`${WS_BASE}/ws/tickets/${ticketId}?token=${token}`);
        wsRef.current = ws;

        ws.onopen = () => setIsConnected(true);
        ws.onclose = () => setIsConnected(false);
        ws.onerror = () => setIsConnected(false);

        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                if (data.id && data.conteudo) {
                    onMessageRef.current(data as AdminMessage);
                }
            } catch { /* silent */ }
        };

        return () => {
            ws.close();
            wsRef.current = null;
        };
    }, [ticketId, token]);

    const send = useCallback((conteudo: string) => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({ conteudo }));
            return true;
        }
        return false;
    }, []);

    return { isConnected, send };
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function AdminSupportPage() {
    const queryClient = useQueryClient();
    const user = useAppStore((s) => s.user);
    const canApproveDemoExtension = Boolean(
        user?.is_superuser || ["super_admin", "admin", "comercial"].includes(user?.role ?? "")
    );
    const [selectedTicketId, setSelectedTicketId] = useState<string | null>(null);
    const [impersonateTarget, setImpersonateTarget] = useState<{ id: string; nome: string; documento?: string | null } | null>(null);
    const [replyContent, setReplyContent] = useState("");
    const [liveMessages, setLiveMessages] = useState<AdminMessage[]>([]);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    const { data: tickets, isLoading: isLoadingTickets } = useQuery<AdminTicket[]>({
        queryKey: ["backoffice", "tickets"],
        queryFn: (): Promise<AdminTicket[]> => apiFetch("/backoffice/tickets"),
    });

    const { data: activeTicket, isLoading: isLoadingDetail } = useQuery<AdminTicketDetail>({
        queryKey: ["backoffice", "ticket", selectedTicketId],
        queryFn: (): Promise<AdminTicketDetail> => apiFetch(`/backoffice/tickets/${selectedTicketId}`),
        enabled: !!selectedTicketId,
    });

    // Sincroniza mensagens históricas ao carregar ticket
    useEffect(() => {
        if (activeTicket?.mensagens) {
            setLiveMessages(activeTicket.mensagens);
        }
    }, [activeTicket]);

    // Scroll automático
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [liveMessages]);

    // ─── WebSocket ──────────────────────────────────────────────────────────

    const { isConnected, send: wsSend } = useAdminSupportWS(selectedTicketId, (msg) => {
        setLiveMessages((prev) => {
            if (prev.some((m) => m.id === msg.id)) return prev;
            return [...prev, msg];
        });
    });

    const requesterName = activeTicket?.usuario_nome?.trim() || activeTicket?.tenant_nome?.trim() || "Usuário";
    const requesterInitial = requesterName.charAt(0).toUpperCase() || "?";

    // ─── Mutations ──────────────────────────────────────────────────────────

    const replyMutation = useMutation({
        mutationFn: (content: string): Promise<AdminMessage> =>
            apiFetch(`/backoffice/tickets/${selectedTicketId}/reply`, {
                method: "POST",
                body: JSON.stringify({ conteudo: content }),
            }),
        onSuccess: (msg: AdminMessage) => {
            setLiveMessages((prev) => {
                if (prev.some((m) => m.id === msg.id)) return prev;
                return [...prev, msg];
            });
            queryClient.invalidateQueries({ queryKey: ["backoffice", "tickets"] });
            setReplyContent("");
            toast.success("Resposta enviada!");
        },
        onError: (e: Error) => toast.error(e.message),
    });

    const closeMutation = useMutation({
        mutationFn: () => apiFetch(`/backoffice/tickets/${selectedTicketId}/close`, { method: "POST" }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["backoffice", "ticket", selectedTicketId] });
            queryClient.invalidateQueries({ queryKey: ["backoffice", "tickets"] });
            toast.success("Chamado finalizado!");
        },
    });

    const extendDemoMutation = useMutation({
        mutationFn: () =>
            apiFetch<{ data_validade_acesso?: string; demo_prorrogacoes_count?: number }>(
                `/backoffice/tickets/${selectedTicketId}/aprovar-prorrogacao-demo`,
                {
                    method: "POST",
                    body: JSON.stringify({}),
                }
            ),
        onSuccess: (res) => {
            queryClient.invalidateQueries({ queryKey: ["backoffice", "ticket", selectedTicketId] });
            queryClient.invalidateQueries({ queryKey: ["backoffice", "tickets"] });
            toast.success("Prorrogação de demonstração aprovada!", {
                description: res?.data_validade_acesso
                    ? `Novo prazo de acesso válido até ${res.data_validade_acesso}.`
                    : "Acesso de demonstração prorrogado com sucesso.",
            });
        },
        onError: (e: Error) => toast.error(e.message),
    });

    const isDemoTicket = Boolean(
        activeTicket?.is_demo_tenant || activeTicket?.categoria === "PRORROGACAO_DEMO"
    );

    // ─── Helpers ────────────────────────────────────────────────────────────

    const handleSendReply = async () => {
        if (!replyContent.trim()) return;

        const content = replyContent.trim();
        setReplyContent("");

        // Tenta WebSocket primeiro
        const sent = wsSend(content);
        if (!sent) {
            // Fallback REST
            replyMutation.mutate(content);
        } else {
            // Via WS a mensagem voltará pelo onmessage; só invalida a lista
            queryClient.invalidateQueries({ queryKey: ["backoffice", "tickets"] });
        }
    };

    const handleSelectTicket = (id: string) => {
        setSelectedTicketId(id);
        setLiveMessages([]);
    };

    // ─── Columns Definition ───────────────────────────────────────────────────

    const columns: ColumnDef<AdminTicket>[] = [
        {
            id: "prioridade",
            header: "Prioridade",
            accessorKey: "prioridade",
            cell: (value) => (
                <Badge variant="ghost" className={`
                    ${value === "URGENTE" ? "bg-red-500/10 text-red-700 border-red-200 font-bold dark:bg-red-500/20 dark:text-red-100 dark:border-red-400/30" : ""}
                    ${value === "ALTA" ? "bg-orange-500/10 text-orange-700 border-orange-200 dark:bg-orange-500/20 dark:text-orange-100 dark:border-orange-400/30" : ""}
                `}>
                    {value}
                </Badge>
            ),
            exportFormat: (value) => value as string,
        },
        {
            id: "assunto",
            header: "Assunto",
            accessorKey: "assunto",
            cell: (value) => <span className="font-bold">{value}</span>,
        },
        {
            id: "cliente",
            header: "Cliente / Empresa",
            accessorFn: (row) => `${row.usuario_nome} - ${row.tenant_nome}`,
            cell: (_, row) => (
                <div className="flex flex-col">
                    <span className="text-sm font-medium">{row.usuario_nome}</span>
                    <span className="text-[11px] text-muted-foreground">{row.tenant_nome}</span>
                </div>
            ),
            exportFormat: (_, row) => `${row.usuario_nome} - ${row.tenant_nome}`,
        },
        {
            id: "status",
            header: "Status",
            accessorKey: "status",
            cell: (value) => (
                <Badge className={`
                    uppercase text-[10px] font-black
                    ${value === "ABERTO" ? "bg-emerald-500/10 text-emerald-700 border-emerald-200 dark:bg-emerald-500/20 dark:text-emerald-100 dark:border-emerald-400/30" : ""}
                    ${value === "EM_ANDAMENTO" ? "bg-blue-500/10 text-blue-700 border-blue-200 dark:bg-blue-500/20 dark:text-blue-100 dark:border-blue-400/30" : ""}
                    ${value === "CONCLUIDO" ? "bg-muted text-muted-foreground border-muted dark:bg-zinc-800 dark:text-zinc-300 dark:border-zinc-700" : ""}
                `}>
                    {(value as string).replace("_", " ")}
                </Badge>
            ),
            exportFormat: (value) => (value as string).replace("_", " "),
        },
        {
            id: "abertura",
            header: "Abertura",
            accessorKey: "created_at",
            cell: (value) => (
                <span className="text-xs text-muted-foreground">
                    {format(new Date(value as string), "dd/MM HH:mm")}
                </span>
            ),
            exportFormat: (value) => format(new Date(value as string), "dd/MM/yyyy HH:mm"),
        },
        {
            id: "acao",
            header: "Ação",
            accessorKey: "id",
            cell: (value, row) => (
                <div className="flex items-center gap-1 justify-end">
                    {row.tenant_id && (
                        <Button
                            variant="ghost"
                            size="sm"
                            className="h-7 w-7 p-0 text-emerald-600 hover:text-emerald-700 hover:bg-emerald-50 dark:hover:bg-emerald-950/30"
                            title="Acessar como Assinante"
                            onClick={(e) => {
                                e.stopPropagation();
                                setImpersonateTarget({
                                    id: row.tenant_id!,
                                    nome: row.tenant_nome,
                                });
                            }}
                        >
                            <LogIn className="h-3.5 w-3.5" />
                        </Button>
                    )}
                    <Button variant="ghost" size="sm" onClick={() => handleSelectTicket(value as string)}>
                        Atender
                    </Button>
                </div>
            ),
            sortable: false,
            filterable: false,
            exportable: false,
        },
    ];

    // ─── Loading ─────────────────────────────────────────────────────────────

    if (isLoadingTickets) {
        return (
            <div className="p-6 space-y-6">
                <Skeleton className="h-10 w-48" />
                <Skeleton className="h-96 w-full" />
            </div>
        );
    }

    // ─── Render ───────────────────────────────────────────────────────────────

    return (
        <div className="p-6 space-y-6">
            {!selectedTicketId ? (
                <>
                    <PageHeader
                        title="Chamados"
                        description="Atenda os usuários e resolva pendências da plataforma."
                        icon={<LifeBuoy className="text-primary" size={22} />}
                        breadcrumbs={[
                            { label: "Backoffice", href: "/dashboard/backoffice/dashboard" },
                            { label: "Suporte Técnico" },
                        ]}
                    />

                    <DataTable
                        data={tickets || []}
                        columns={columns}
                        searchable={true}
                        searchPlaceholder="Buscar por assunto ou empresa..."
                        exportable={true}
                        exportFileName="chamados-suporte"
                        emptyMessage="Nenhum chamado encontrado."
                    />
                </>
            ) : (
                <>
                    <PageHeader
                        title="Detalhes do Chamado"
                        description={`Visualize e responda o ticket de ${activeTicket?.usuario_nome ?? "este usuário"}`}
                        icon={<LifeBuoy className="text-primary" size={22} />}
                        breadcrumbs={[
                            { label: "Backoffice", href: "/dashboard/backoffice/dashboard" },
                            { label: "Suporte Técnico", href: "/dashboard/backoffice/support" },
                            { label: "Atendimento" },
                        ]}
                        actions={
                            <Button variant="outline" size="sm" className="gap-2 rounded-sm" onClick={() => setSelectedTicketId(null)}>
                                <ArrowLeft size={16} /> Voltar para lista
                            </Button>
                        }
                    />

                    <div className="grid gap-6 md:grid-cols-12">
                        {/* Chat */}
                        <Card className="md:col-span-8 lg:col-span-9 flex flex-col overflow-hidden">
                            <CardHeader className="border-b py-4 flex flex-row items-center justify-between">
                                <div className="flex items-center gap-4">
                                    <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center text-primary">
                                        <LifeBuoy size={20} />
                                    </div>
                                    <div className="min-w-0">
                                        <CardTitle className="text-base font-semibold">{activeTicket?.assunto}</CardTitle>
                                        <CardDescription className="text-xs flex items-center gap-2 mt-1">
                                            <User size={12} className="text-muted-foreground" />
                                            <span className="truncate max-w-[200px] md:max-w-md">
                                                {activeTicket?.usuario_nome} @ {activeTicket?.tenant_nome}
                                            </span>
                                            <span title={isConnected ? "Tempo real ativo" : "Polling REST"}>
                                                {isConnected
                                                    ? <Wifi size={11} className="text-emerald-500" />
                                                    : <WifiOff size={11} className="text-muted-foreground" />
                                                }
                                            </span>
                                        </CardDescription>
                                    </div>
                                </div>
                                <div className="flex items-center gap-2">
                                    {activeTicket?.tenant_id && (
                                        <Button
                                            variant="outline"
                                            size="sm"
                                            className="text-emerald-700 border-emerald-300 hover:bg-emerald-50 dark:text-emerald-400 dark:border-emerald-600/30 dark:hover:bg-emerald-950/20"
                                            onClick={() => {
                                                setImpersonateTarget({
                                                    id: activeTicket.tenant_id!,
                                                    nome: activeTicket.tenant_nome,
                                                });
                                            }}
                                        >
                                            <LogIn size={14} className="mr-1.5" /> Acessar como Assinante
                                        </Button>
                                    )}
                                    {canApproveDemoExtension && isDemoTicket && activeTicket?.status !== "CONCLUIDO" && (
                                        <Button
                                            variant="outline"
                                            size="sm"
                                            disabled={extendDemoMutation.isPending}
                                            className="rounded-sm text-amber-700 border-amber-300 hover:bg-amber-50 dark:text-amber-300 dark:border-amber-600/40 dark:hover:bg-amber-950/20"
                                            onClick={() => extendDemoMutation.mutate()}
                                        >
                                            {extendDemoMutation.isPending ? (
                                                <Loader2 size={14} className="mr-1.5 animate-spin" />
                                            ) : (
                                                <CalendarPlus size={14} className="mr-1.5" />
                                            )}
                                            Aprovar Prorrogação
                                        </Button>
                                    )}
                                    {activeTicket?.status !== "CONCLUIDO" && (
                                        <Button
                                            variant="outline"
                                            size="sm"
                                            className="text-emerald-700 border-emerald-300 hover:bg-emerald-50 dark:text-emerald-100 dark:border-emerald-400/30 dark:hover:bg-emerald-500/10"
                                            onClick={() => closeMutation.mutate()}
                                        >
                                            <CheckCircle size={14} className="mr-1.5" /> Finalizar
                                        </Button>
                                    )}
                                    <Badge variant="secondary" className="text-xs font-medium bg-blue-500/10 text-blue-700 border border-blue-200 dark:bg-blue-500/20 dark:text-blue-100 dark:border-blue-400/30">
                                        {activeTicket?.status?.replace("_", " ")}
                                    </Badge>
                                </div>
                            </CardHeader>

                            <ScrollArea className="flex-1 p-6">
                                {isLoadingDetail ? (
                                    <div className="space-y-4">
                                        {[1, 2, 3].map((i) => <Skeleton key={i} className="h-16 w-3/4" />)}
                                    </div>
                                ) : (
                                    <div className="space-y-4">
                                        {liveMessages.map((msg) => (
                                            <div key={msg.id} className={`flex ${msg.is_admin_reply ? "justify-end" : "justify-start"}`}>
                                                <div className={`max-w-[85%] md:max-w-[75%] p-4 rounded-lg shadow-sm ${msg.is_admin_reply
                                                    ? "bg-blue-600 text-white"
                                                    : "bg-muted text-foreground border"
                                                    }`}>
                                                    <div className={`flex items-center gap-2 mb-2 ${msg.is_admin_reply ? "opacity-80" : "opacity-70"}`}>
                                                        {msg.is_admin_reply ? <Building size={12} /> : <User size={12} />}
                                                        <span className="text-[10px] font-bold uppercase tracking-wide">
                                                            {msg.is_admin_reply ? "Você (Suporte)" : activeTicket?.usuario_nome}
                                                        </span>
                                                    </div>
                                                    <p className="text-sm whitespace-pre-wrap leading-relaxed">{msg.conteudo}</p>
                                                    <div className={`text-[9px] mt-2 ${msg.is_admin_reply ? "opacity-70" : "opacity-50"} text-right`}>
                                                        {format(new Date(msg.created_at), "dd/MM/yyyy HH:mm")}
                                                    </div>
                                                </div>
                                            </div>
                                        ))}
                                        <div ref={messagesEndRef} />
                                    </div>
                                )}
                            </ScrollArea>

                            {activeTicket?.status !== "CONCLUIDO" && (
                                <div className="p-4 border-t bg-muted/20">
                                    <div className="flex gap-2">
                                        <Textarea
                                            placeholder="Digite sua resposta de suporte... (Ctrl+Enter para enviar)"
                                            className="min-h-[80px] text-sm resize-none"
                                            value={replyContent}
                                            onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setReplyContent(e.target.value)}
                                            onKeyDown={(e: React.KeyboardEvent<HTMLTextAreaElement>) => {
                                                if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) handleSendReply();
                                            }}
                                        />
                                        <Button
                                            className="h-auto px-6"
                                            disabled={!replyContent.trim() || replyMutation.isPending}
                                            onClick={handleSendReply}
                                        >
                                            {replyMutation.isPending
                                                ? <Loader2 size={20} className="animate-spin" />
                                                : <Send size={20} />
                                            }
                                        </Button>
                                    </div>
                                </div>
                            )}
                        </Card>

                        {/* Ticket Info */}
                        <Card className="md:col-span-4 lg:col-span-3 h-fit">
                            <CardHeader className="py-4 border-b">
                                <CardTitle className="text-sm font-semibold flex items-center gap-2">
                                    <LifeBuoy size={16} className="text-primary" />
                                    Informações do Ticket
                                </CardTitle>
                            </CardHeader>
                            <CardContent className="space-y-4 p-4">
                                <div className="space-y-1">
                                    <p className="text-[10px] font-bold uppercase text-muted-foreground tracking-wide">Protocolo</p>
                                    <p className="text-xs font-mono font-semibold bg-muted/50 px-2 py-1 rounded truncate">
                                        {activeTicket?.id}
                                    </p>
                                </div>
                                <div className="space-y-1">
                                    <p className="text-[10px] font-bold uppercase text-muted-foreground tracking-wide">Empresa</p>
                                    <p className="text-sm font-semibold">{activeTicket?.tenant_nome}</p>
                                </div>
                                <div className="space-y-1">
                                    <p className="text-[10px] font-bold uppercase text-muted-foreground tracking-wide">Solicitante</p>
                                    <div className="flex items-center gap-2">
                                        <div className="h-7 w-7 rounded-full bg-primary/10 flex items-center justify-center text-xs font-semibold text-primary">
                                            {requesterInitial}
                                        </div>
                                        <p className="text-sm">{requesterName}</p>
                                    </div>
                                </div>
                                <div className="space-y-1">
                                    <p className="text-[10px] font-bold uppercase text-muted-foreground tracking-wide">Categoria</p>
                                    <Badge variant="secondary" className="text-xs font-medium">
                                        {activeTicket?.categoria}
                                    </Badge>
                                </div>
                                <div className="space-y-1">
                                    <p className="text-[10px] font-bold uppercase text-muted-foreground tracking-wide">Prioridade</p>
                                    <Badge variant="outline" className={`text-xs font-semibold ${
                                        activeTicket?.prioridade === "URGENTE"
                                            ? "bg-red-50 text-red-700 border-red-200 dark:bg-red-500/10 dark:text-red-100 dark:border-red-400/30"
                                            : activeTicket?.prioridade === "ALTA"
                                            ? "bg-orange-50 text-orange-700 border-orange-200 dark:bg-orange-500/10 dark:text-orange-100 dark:border-orange-400/30"
                                            : ""
                                    }`}>
                                        {activeTicket?.prioridade}
                                    </Badge>
                                </div>
                                {isDemoTicket && (
                                    <div className="space-y-2 rounded-sm border border-amber-200 bg-amber-50/70 p-3 dark:border-amber-700/40 dark:bg-amber-950/20">
                                        <p className="text-[10px] font-bold uppercase text-amber-800 dark:text-amber-300 tracking-wide">
                                            Conta em Demonstração
                                        </p>
                                        {activeTicket?.usuario_email && (
                                            <p className="text-xs text-muted-foreground break-all">
                                                E-mail: <span className="font-medium text-foreground">{activeTicket.usuario_email}</span>
                                            </p>
                                        )}
                                        <p className="text-xs text-muted-foreground">
                                            Validade atual:{" "}
                                            <span className="font-medium text-foreground">
                                                {activeTicket?.data_validade_acesso || "Não definida"}
                                            </span>
                                        </p>
                                        <p className="text-xs text-muted-foreground">
                                            Prorrogações concedidas:{" "}
                                            <span className="font-medium text-foreground">
                                                {activeTicket?.demo_prorrogacoes_count ?? 0}
                                            </span>
                                        </p>
                                    </div>
                                )}
                                <div className="pt-4 border-t border-dashed">
                                    <p className="text-[11px] text-muted-foreground flex items-center gap-2">
                                        <Clock size={12} />
                                        <span>Aberto em</span>
                                        <span className="font-medium">
                                            {format(
                                                new Date(activeTicket?.created_at || new Date()),
                                                "dd/MM/yyyy 'às' HH:mm",
                                                { locale: ptBR }
                                            )}
                                        </span>
                                    </p>
                                </div>
                            </CardContent>
                        </Card>
                    </div>
                </>
            )}

            <ImpersonateTenantDialog
                open={!!impersonateTarget}
                onOpenChange={(open) => {
                    if (!open) setImpersonateTarget(null);
                }}
                tenant={impersonateTarget}
            />
        </div>
    );
}
