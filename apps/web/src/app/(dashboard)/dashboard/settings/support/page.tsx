"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { useAppStore } from "@/lib/stores/app-store";
import {
    LifeBuoy, Plus, Send, ArrowLeft, MessageSquare,
    CheckCircle2, Clock, AlertCircle, Wifi, WifiOff, Loader2,
    ChevronRight, Tag, Zap
} from "lucide-react";
import { PageHeader } from "@/components/shared";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";
import { toast } from "sonner";
import { getWsBaseUrl } from "@/lib/runtime-config";

// ─── Types ─────────────────────────────────────────────────────────────────

interface Ticket {
    id: string;
    assunto: string;
    categoria: string;
    prioridade: string;
    status: string;
    created_at: string;
    updated_at: string;
}

interface Mensagem {
    id: string;
    conteudo: string;
    is_admin_reply: boolean;
    created_at: string;
    anexo_url?: string | null;
}

interface TicketDetail extends Ticket {
    mensagens: Mensagem[];
}

interface NewTicketForm {
    assunto: string;
    categoria: string;
    prioridade: string;
    mensagem_inicial: string;
}

// ─── WebSocket Hook ─────────────────────────────────────────────────────────

function useSupportWebSocket(ticketId: string | null, onMessage: (msg: Mensagem) => void) {
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
                // Ignora eventos de controle (connected, error)
                if (data.id && data.conteudo) {
                    onMessageRef.current(data as Mensagem);
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

// ─── Status helpers ─────────────────────────────────────────────────────────

const STATUS_CONFIG: Record<string, { label: string; color: string; icon: React.ReactNode }> = {
    ABERTO: { label: "Aberto", color: "bg-emerald-500/15 text-emerald-700 border-emerald-200", icon: <CheckCircle2 size={11} /> },
    EM_ATENDIMENTO: { label: "Em Atendimento", color: "bg-blue-500/15 text-blue-700 border-blue-200", icon: <Loader2 size={11} className="animate-spin" /> },
    AGUARDANDO_CLIENTE: { label: "Aguard. Resposta", color: "bg-amber-500/15 text-amber-700 border-amber-200", icon: <Clock size={11} /> },
    CONCLUIDO: { label: "Concluído", color: "bg-muted text-muted-foreground border-muted", icon: <CheckCircle2 size={11} /> },
    CANCELADO: { label: "Cancelado", color: "bg-red-500/15 text-red-700 border-red-200", icon: <AlertCircle size={11} /> },
};

const PRIORITY_COLOR: Record<string, string> = {
    BAIXA: "text-slate-500",
    MEDIA: "text-blue-500",
    ALTA: "text-orange-500",
    URGENTE: "text-red-600 font-bold",
};

// ─── Chat View ───────────────────────────────────────────────────────────────

function TicketChat({ ticket, onBack }: { ticket: Ticket; onBack: () => void }) {
    const queryClient = useQueryClient();
    const [messages, setMessages] = useState<Mensagem[]>([]);
    const [draft, setDraft] = useState("");
    const [isSending, setIsSending] = useState(false);
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const isClosed = ticket.status === "CONCLUIDO" || ticket.status === "CANCELADO";

    // Carrega histórico inicial via REST
    const { isLoading, data: ticketDetail } = useQuery<TicketDetail>({
        queryKey: ["support", "ticket", ticket.id],
        queryFn: (): Promise<TicketDetail> => apiFetch(`/support/tickets/${ticket.id}`),
    });

    useEffect(() => {
        if (ticketDetail?.mensagens) {
            setMessages(ticketDetail.mensagens);
        }
    }, [ticketDetail]);

    // WebSocket para mensagens em tempo real
    const { isConnected, send } = useSupportWebSocket(ticket.id, (msg) => {
        setMessages((prev) => {
            // Evita duplicata (se já foi adicionado via REST polling)
            if (prev.some((m) => m.id === msg.id)) return prev;
            return [...prev, msg];
        });
    });

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages]);

    const handleSend = async () => {
        if (!draft.trim() || isSending || isClosed) return;

        setIsSending(true);
        const text = draft.trim();
        setDraft("");

        const sent = send(text);

        if (!sent) {
            // Fallback REST se WS desconectado
            try {
                const msg = await apiFetch<Mensagem>(`/support/tickets/${ticket.id}/messages`, {
                    method: "POST",
                    body: JSON.stringify({ conteudo: text }),
                });
                setMessages((prev) => [...prev, msg]);
                queryClient.invalidateQueries({ queryKey: ["support", "tickets"] });
            } catch (e) {
                toast.error("Falha ao enviar mensagem.");
                setDraft(text);
            }
        }

        setIsSending(false);
    };

    const statusCfg = STATUS_CONFIG[ticket.status] ?? STATUS_CONFIG["ABERTO"];

    return (
        <div className="flex flex-col h-full animate-in slide-in-from-right-4 duration-300">
            {/* Header */}
            <div className="flex items-center gap-3 pb-4 border-b flex-shrink-0">
                <Button variant="ghost" size="sm" className="gap-1.5" onClick={onBack}>
                    <ArrowLeft size={14} />
                    <span className="hidden sm:inline">Voltar</span>
                </Button>
                <Separator orientation="vertical" className="h-5" />
                <div className="flex-1 min-w-0">
                    <h2 className="font-semibold text-sm truncate">{ticket.assunto}</h2>
                    <p className="text-[11px] text-muted-foreground">
                        #{ticket.id.slice(0, 8).toUpperCase()} · Aberto em {format(new Date(ticket.created_at), "dd/MM/yyyy")}
                    </p>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                    <span title={isConnected ? "Conectado em tempo real" : "Polling REST"}>
                        {isConnected
                            ? <Wifi size={14} className="text-emerald-500" />
                            : <WifiOff size={14} className="text-muted-foreground" />
                        }
                    </span>
                    <Badge variant="outline" className={`text-[10px] gap-1 ${statusCfg.color}`}>
                        {statusCfg.icon}
                        {statusCfg.label}
                    </Badge>
                </div>
            </div>

            {/* Messages */}
            <ScrollArea className="flex-1 py-4">
                {isLoading ? (
                    <div className="space-y-4 px-1">
                        {[1, 2, 3].map((i) => <Skeleton key={i} className="h-16 w-3/4" />)}
                    </div>
                ) : (
                    <div className="space-y-4 px-1">
                        {messages.map((msg) => (
                            <div key={msg.id} className={`flex ${msg.is_admin_reply ? "justify-end" : "justify-start"}`}>
                                <div className={`
                                    max-w-[78%] px-4 py-3 rounded-sm text-sm shadow-sm
                                    ${msg.is_admin_reply
                                        ? "bg-primary text-primary-foreground rounded-br-sm"
                                        : "bg-muted border border-border/50 rounded-bl-sm"
                                    }
                                `}>
                                    <div className={`text-[10px] font-semibold uppercase mb-1 opacity-60`}>
                                        {msg.is_admin_reply ? "Suporte AgroSaaS" : "Você"}
                                    </div>
                                    <p className="whitespace-pre-wrap leading-relaxed">{msg.conteudo}</p>
                                    <div className={`text-[9px] mt-1.5 opacity-50 text-right`}>
                                        {format(new Date(msg.created_at), "HH:mm, dd MMM", { locale: ptBR })}
                                    </div>
                                </div>
                            </div>
                        ))}
                        <div ref={messagesEndRef} />
                    </div>
                )}
            </ScrollArea>

            {/* Input */}
            {!isClosed ? (
                <div className="pt-3 border-t flex-shrink-0">
                    <div className="flex gap-2">
                        <Textarea
                            id="support-message-input"
                            placeholder="Digite sua mensagem..."
                            className="min-h-[80px] resize-none text-sm"
                            value={draft}
                            onChange={(e) => setDraft(e.target.value)}
                            onKeyDown={(e) => {
                                if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) handleSend();
                            }}
                        />
                        <Button
                            id="support-send-btn"
                            className="h-auto px-5 self-end"
                            disabled={!draft.trim() || isSending}
                            onClick={handleSend}
                        >
                            {isSending ? <Loader2 size={18} className="animate-spin" /> : <Send size={18} />}
                        </Button>
                    </div>
                    <p className="text-[10px] text-muted-foreground mt-1.5">
                        <kbd className="bg-muted px-1 py-0.5 rounded text-[9px] font-mono">Ctrl+Enter</kbd> para enviar
                    </p>
                </div>
            ) : (
                <div className="pt-3 border-t">
                    <p className="text-sm text-muted-foreground text-center py-3 bg-muted/40 rounded-sm">
                        Este chamado foi {ticket.status === "CONCLUIDO" ? "concluído" : "cancelado"}.
                    </p>
                </div>
            )}
        </div>
    );
}

// ─── New Ticket Form ─────────────────────────────────────────────────────────

function NewTicketForm({ onSuccess, onCancel }: { onSuccess: () => void; onCancel: () => void }) {
    const queryClient = useQueryClient();
    const [form, setForm] = useState<NewTicketForm>({
        assunto: "",
        categoria: "TECNICO",
        prioridade: "MEDIA",
        mensagem_inicial: "",
    });

    const createMutation = useMutation({
        mutationFn: (data: NewTicketForm) => apiFetch("/support/tickets", {
            method: "POST",
            body: JSON.stringify(data),
        }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["support", "tickets"] });
            toast.success("Chamado aberto com sucesso!");
            onSuccess();
        },
        onError: (e: Error) => toast.error(e.message),
    });

    return (
        <div className="animate-in slide-in-from-bottom-4 duration-300 space-y-5">
            <div className="flex items-center gap-3">
                <Button variant="ghost" size="sm" className="gap-1.5" onClick={onCancel}>
                    <ArrowLeft size={14} /> Cancelar
                </Button>
                <h2 className="font-semibold text-sm">Novo Chamado de Suporte</h2>
            </div>

            <div className="space-y-4">
                <div className="space-y-1.5">
                    <Label htmlFor="new-ticket-subject" className="text-xs font-semibold">Assunto *</Label>
                    <Input
                        id="new-ticket-subject"
                        placeholder="Descreva brevemente o problema..."
                        value={form.assunto}
                        onChange={(e) => setForm({ ...form, assunto: e.target.value })}
                        size={1}
                    />
                </div>

                <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-1.5">
                        <Label htmlFor="new-ticket-category" className="text-xs font-semibold">Categoria</Label>
                        <Select value={form.categoria} onValueChange={(v: string) => setForm({ ...form, categoria: v })}>
                            <SelectTrigger id="new-ticket-category" className="h-8 text-xs">
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="TECNICO">🔧 Técnico</SelectItem>
                                <SelectItem value="FINANCEIRO">💳 Financeiro</SelectItem>
                                <SelectItem value="DUVIDA">❓ Dúvida</SelectItem>
                                <SelectItem value="SUGESTAO">💡 Sugestão</SelectItem>
                            </SelectContent>
                        </Select>
                    </div>

                    <div className="space-y-1.5">
                        <Label htmlFor="new-ticket-priority" className="text-xs font-semibold">Prioridade</Label>
                        <Select value={form.prioridade} onValueChange={(v: string) => setForm({ ...form, prioridade: v })}>
                            <SelectTrigger id="new-ticket-priority" className="h-8 text-xs">
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="BAIXA">🟢 Baixa</SelectItem>
                                <SelectItem value="MEDIA">🔵 Média</SelectItem>
                                <SelectItem value="ALTA">🟠 Alta</SelectItem>
                                <SelectItem value="URGENTE">🔴 Urgente</SelectItem>
                            </SelectContent>
                        </Select>
                    </div>
                </div>

                <div className="space-y-1.5">
                    <Label htmlFor="new-ticket-msg" className="text-xs font-semibold">Descrição detalhada *</Label>
                    <Textarea
                        id="new-ticket-msg"
                        placeholder="Descreva o problema em detalhes. Inclua passos para reproduzir, se possível..."
                        className="min-h-[120px] text-sm resize-none"
                        value={form.mensagem_inicial}
                        onChange={(e) => setForm({ ...form, mensagem_inicial: e.target.value })}
                    />
                </div>

                <Button
                    id="submit-new-ticket-btn"
                    className="w-full gap-2"
                    disabled={!form.assunto.trim() || !form.mensagem_inicial.trim() || createMutation.isPending}
                    onClick={() => createMutation.mutate(form)}
                >
                    {createMutation.isPending
                        ? <><Loader2 size={16} className="animate-spin" /> Abrindo...</>
                        : <><Send size={16} /> Abrir Chamado</>
                    }
                </Button>
            </div>
        </div>
    );
}

// ─── Ticket List ─────────────────────────────────────────────────────────────

function TicketList({
    tickets,
    isLoading,
    onSelect,
    onNewTicket,
}: {
    tickets: Ticket[] | undefined;
    isLoading: boolean;
    onSelect: (t: Ticket) => void;
    onNewTicket: () => void;
}) {
    const open = tickets?.filter(t => t.status !== "CONCLUIDO" && t.status !== "CANCELADO") ?? [];
    const closed = tickets?.filter(t => t.status === "CONCLUIDO" || t.status === "CANCELADO") ?? [];

    return (
        <div className="space-y-6">            {/* Quick Help Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                {[
                    { icon: <Zap size={16} className="text-amber-500" />, title: "Base de Conhecimento", desc: "Artigos e tutoriais da plataforma", href: "/settings/kb" },
                    { icon: <MessageSquare size={16} className="text-blue-500" />, title: "Chat em Tempo Real", desc: "Respostas diretamente nas mensagens", href: "#" },
                    { icon: <Tag size={16} className="text-emerald-500" />, title: "SLA de Atendimento", desc: "Urgente: 2 h · Alta: 8 h · Normal: 48 h", href: "#" },
                ].map((item) => (
                    <Card key={item.title} className="bg-muted/20 border-border/50 hover:bg-muted/40 transition-colors cursor-default">
                        <CardContent className="p-4 flex gap-3 items-start">
                            <div className="mt-0.5">{item.icon}</div>
                            <div>
                                <p className="text-xs font-semibold">{item.title}</p>
                                <p className="text-[11px] text-muted-foreground mt-0.5">{item.desc}</p>
                            </div>
                        </CardContent>
                    </Card>
                ))}
            </div>

            {/* Open Tickets */}
            <div>
                <h3 className="text-xs font-bold uppercase text-muted-foreground mb-3 tracking-wider">
                    Chamados Abertos ({open.length})
                </h3>
                {isLoading ? (
                    <div className="space-y-2">
                        {[1, 2].map((i) => <Skeleton key={i} className="h-14 w-full rounded-sm" />)}
                    </div>
                ) : open.length === 0 ? (
                    <div className="text-center py-10 border border-dashed rounded-sm bg-muted/20">
                        <LifeBuoy size={28} className="mx-auto text-muted-foreground mb-2 opacity-50" />
                        <p className="text-sm text-muted-foreground">Nenhum chamado aberto.</p>
                        <Button variant="link" size="sm" className="mt-1" onClick={onNewTicket}>
                            Abrir um agora
                        </Button>
                    </div>
                ) : (
                    <div className="space-y-2">
                        {open.map((t) => <TicketRow key={t.id} ticket={t} onSelect={onSelect} />)}
                    </div>
                )}
            </div>

            {/* Closed Tickets */}
            {closed.length > 0 && (
                <div>
                    <h3 className="text-xs font-bold uppercase text-muted-foreground mb-3 tracking-wider">
                        Histórico ({closed.length})
                    </h3>
                    <div className="space-y-2 opacity-70">
                        {closed.map((t) => <TicketRow key={t.id} ticket={t} onSelect={onSelect} />)}
                    </div>
                </div>
            )}
        </div>
    );
}

function TicketRow({ ticket, onSelect }: { ticket: Ticket; onSelect: (t: Ticket) => void }) {
    const statusCfg = STATUS_CONFIG[ticket.status] ?? STATUS_CONFIG["ABERTO"];

    return (
        <button
            id={`ticket-row-${ticket.id.slice(0, 8)}`}
            className="w-full text-left p-4 rounded-sm border border-border/50 bg-card hover:bg-muted/30 hover:border-primary/30 transition-all group flex items-center gap-4"
            onClick={() => onSelect(ticket)}
        >
            <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                    <span className="text-sm font-semibold truncate">{ticket.assunto}</span>
                    <Badge variant="outline" className={`text-[9px] gap-1 flex-shrink-0 ${statusCfg.color}`}>
                        {statusCfg.icon}
                        {statusCfg.label}
                    </Badge>
                </div>
                <div className="flex items-center gap-3 text-[11px] text-muted-foreground">
                    <span className={PRIORITY_COLOR[ticket.prioridade]}>● {ticket.prioridade}</span>
                    <span>{ticket.categoria}</span>
                    <span>· {format(new Date(ticket.created_at), "dd MMM yyyy", { locale: ptBR })}</span>
                </div>
            </div>
            <ChevronRight size={16} className="text-muted-foreground group-hover:text-primary transition-colors flex-shrink-0" />
        </button>
    );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

type View = "list" | "chat" | "new";

export default function SupportPage() {
    const [view, setView] = useState<View>("list");
    const [selectedTicket, setSelectedTicket] = useState<Ticket | null>(null);

    const { data: tickets, isLoading } = useQuery<Ticket[]>({
        queryKey: ["support", "tickets"],
        queryFn: () => apiFetch("/support/tickets"),
        refetchInterval: view === "list" ? 30_000 : false,
    });

    const handleSelectTicket = (t: Ticket) => {
        setSelectedTicket(t);
        setView("chat");
    };

    return (
        <div className="space-y-6 p-6">
            <PageHeader
                title="Ajuda e Suporte"
                description="Abra chamados e acompanhe suas solicitações."
                breadcrumbs={[
                    { label: "Configurações", href: "/dashboard/settings" },
                    { label: "Suporte" },
                ]}
                icon={<LifeBuoy className="h-8 w-8 text-primary" />}
                actions={
                    view === "list" ? (
                        <Button
                            variant="outline"
                            size="sm"
                            className="rounded-sm border-primary text-primary hover:bg-primary/5 font-bold"
                            onClick={() => setView("new")}
                        >
                            <Plus size={16} className="mr-2" /> Novo Chamado
                        </Button>
                    ) : null
                }
            />

            <div>
                {view === "list" && (
                    <TicketList
                        tickets={tickets}
                        isLoading={isLoading}
                        onSelect={handleSelectTicket}
                        onNewTicket={() => setView("new")}
                    />
                )}
                {view === "new" && (
                    <div className="max-w-3xl">
                        <Card className="shadow-sm">
                            <CardContent className="p-6">
                                <NewTicketForm
                                    onSuccess={() => setView("list")}
                                    onCancel={() => setView("list")}
                                />
                            </CardContent>
                        </Card>
                    </div>
                )}
                {view === "chat" && selectedTicket && (
                    <div className="max-w-4xl h-[600px]">
                        <Card className="shadow-sm h-full flex flex-col">
                            <CardContent className="p-6 flex-1 flex flex-col min-h-0">
                                <TicketChat
                                    ticket={selectedTicket}
                                    onBack={() => {
                                        setView("list");
                                        setSelectedTicket(null);
                                    }}
                                />
                            </CardContent>
                        </Card>
                    </div>
                )}
            </div>
        </div>
    );
}
