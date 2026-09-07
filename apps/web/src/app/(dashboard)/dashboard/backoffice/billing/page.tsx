"use client";

import { useState, useMemo, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import {
    FileText, CheckCircle2, XCircle,
    ExternalLink, Settings2,
    AlertCircle, Clock, TrendingUp, RefreshCw,
    Zap, Info, Receipt
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { DataTable, ColumnDef } from "@/components/ui/data-table";
import { toast } from "sonner";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";
import { formatCurrency } from "@/lib/utils";
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogDescription,
    DialogBody,
    DialogFooter
} from "@/components/ui/dialog";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { PageHeader } from "@/components/shared/page-header";
import { StatCard } from "@/components/shared/stat-card";
import { WorkflowStatusBadge } from "@/components/ui/status-badge";

interface Invoice {
    id: string;
    tenant_id: string;
    tenant_nome: string;
    plano_nome: string;
    valor: number;
    data_vencimento: string;
    status: string;
    url_comprovante: string | null;
    data_envio_comprovante: string | null;
    justificativa_rejeicao: string | null;
    created_at: string;
}


export default function BillingBackofficePage() {
    const queryClient = useQueryClient();
    const [reviewingInvoice, setReviewingInvoice] = useState<Invoice | null>(null);
    const [rejectionReason, setRejectionReason] = useState("");
    const [statusFilter, setStatusFilter] = useState("TODOS");
    const [syncSessionId, setSyncSessionId] = useState("");
    const [syncDialogOpen, setSyncDialogOpen] = useState(false);

    const syncMutation = useMutation({
        mutationFn: (ref: string) => {
            const isPI = ref.startsWith("pi_");
            return apiFetch("/stripe/sync-session", {
                method: "POST",
                body: JSON.stringify(isPI ? { payment_intent_id: ref } : { session_id: ref }),
            });
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["backoffice", "invoices"] });
            toast.success("Sessão sincronizada com sucesso!");
            setSyncDialogOpen(false);
            setSyncSessionId("");
        },
        onError: (err: Error) => toast.error(err.message || "Erro ao sincronizar sessão."),
    });

    const { data: invoices = [], isLoading } = useQuery<Invoice[]>({
        queryKey: ["backoffice", "invoices"],
        queryFn: () => apiFetch("/backoffice/invoices"),
    });

    const reviewMutation = useMutation({
        mutationFn: ({ id, aprovado, justificativa }: { id: string; aprovado: boolean; justificativa?: string }) =>
            apiFetch(`/backoffice/invoices/${id}/review`, {
                method: "POST",
                body: JSON.stringify({ aprovado, justificativa }),
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["backoffice", "invoices"] });
            toast.success("Fatura processada com sucesso!");
            setReviewingInvoice(null);
            setRejectionReason("");
        },
        onError: (err: any) => toast.error(err.message || "Erro ao processar fatura."),
    });

    const stats = useMemo(() => {
        const abertas = invoices.filter((i) => i.status === "ABERTA");
        const pagas = invoices.filter((i) => i.status === "PAGA");
        const emAnalise = invoices.filter((i) => i.status === "EM_ANALISE");
        const mrr = pagas.reduce((acc, i) => acc + i.valor, 0);
        return {
            abertas: abertas.length,
            pagas: pagas.length,
            emAnalise: emAnalise.length,
            mrr,
        };
    }, [invoices]);

    const filtered = useMemo(() =>
        statusFilter === "TODOS" ? invoices : invoices.filter((i) => i.status === statusFilter),
        [invoices, statusFilter]
    );

    const columns: ColumnDef<Invoice>[] = [
        {
            id: "tenant_nome",
            header: "Cliente / Plano",
            accessorKey: "tenant_nome",
            cell: (_value, row) => (
                <div className="flex flex-col">
                    <span className="font-semibold text-foreground">{row.tenant_nome}</span>
                    <span className="text-[10px] text-muted-foreground">{row.plano_nome}</span>
                </div>
            ),
        },
        {
            id: "valor",
            header: "Valor",
            accessorKey: "valor",
            cell: (value) => (
                <span className="font-medium text-blue-600">{formatCurrency(value)}</span>
            ),
        },
        {
            id: "data_vencimento",
            header: "Vencimento",
            accessorKey: "data_vencimento",
            cell: (value) => format(new Date(value), "dd/MM/yyyy", { locale: ptBR }),
        },
        {
            id: "status",
            header: "Status",
            accessorKey: "status",
            cell: (value) => <WorkflowStatusBadge status={value} />,
        },
        {
            id: "url_comprovante",
            header: "Comprovante",
            accessorKey: "url_comprovante",
            sortable: false,
            filterable: false,
            cell: (value) =>
                value ? (
                    <a
                        href={value}
                        target="_blank"
                        rel="noreferrer"
                        className="flex items-center gap-1 text-primary hover:underline text-xs font-semibold"
                    >
                        <ExternalLink size={12} /> Ver PDF
                    </a>
                ) : (
                    <span className="text-[10px] text-muted-foreground italic">Não enviado</span>
                ),
        },
        {
            id: "actions",
            header: "",
            exportable: false,
            sortable: false,
            filterable: false,
            cell: (_value, row) => (
                <div className="flex items-center gap-1 justify-end">
                    <Button
                        variant="ghost"
                        size="sm"
                        className="h-8 text-xs gap-2"
                        disabled={row.status === "PAGA" || !row.url_comprovante}
                        onClick={() => setReviewingInvoice(row)}
                    >
                        <Settings2 className="h-3.5 w-3.5" /> Revisar
                    </Button>
                </div>
            ),
        },
    ];

    return (
        <div className="p-8 space-y-8 w-full max-w-full">
            <PageHeader
                title="Gestão Financeira SaaS"
                description="Conciliação de pagamentos e auditoria de faturas."
                icon={<Receipt className="text-primary" size={22} />}
                breadcrumbs={[{ label: "Backoffice" }, { label: "Financeiro" }]}
            />

            {/* Stats */}
            {isLoading ? (
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                    {Array.from({ length: 4 }).map((_, i) => (
                        <Skeleton key={i} className="h-24 w-full" />
                    ))}
                </div>
            ) : (
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                    <StatCard
                        icon={Clock}
                        label="Faturas Abertas"
                        value={stats.abertas}
                        subtitle="Aguardando pagamento"
                        color="warning"
                        onClick={() => setStatusFilter("ABERTA")}
                    />
                    <StatCard
                        icon={AlertCircle}
                        label="Em Análise"
                        value={stats.emAnalise}
                        subtitle="Comprovante enviado"
                        color="primary"
                        onClick={() => setStatusFilter("EM_ANALISE")}
                    />
                    <StatCard
                        icon={CheckCircle2}
                        label="Pagas"
                        value={stats.pagas}
                        subtitle="Este período"
                        color="success"
                        onClick={() => setStatusFilter("PAGA")}
                    />
                    <StatCard
                        icon={TrendingUp}
                        label="Receita Confirmada"
                        value={formatCurrency(stats.mrr)}
                        subtitle="Total de faturas pagas"
                        color="backoffice"
                    />
                </div>
            )}

            {/* Filtro + Tabela */}
            <div className="space-y-4">
                <div className="flex items-center justify-between gap-4">
                    <Select value={statusFilter} onValueChange={setStatusFilter}>
                        <SelectTrigger className="w-[180px]">
                            <SelectValue placeholder="Filtrar por status" />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="TODOS">Todos</SelectItem>
                            <SelectItem value="ABERTA">Abertas</SelectItem>
                            <SelectItem value="EM_ANALISE">Em Análise</SelectItem>
                            <SelectItem value="PAGA">Pagas</SelectItem>
                            <SelectItem value="REJEITADA">Rejeitadas</SelectItem>
                            <SelectItem value="VENCIDA">Vencidas</SelectItem>
                        </SelectContent>
                    </Select>
                    <Button variant="outline" size="sm" className="gap-2" onClick={() => setSyncDialogOpen(true)}>
                        <RefreshCw className="h-4 w-4" /> Sync Stripe
                    </Button>
                </div>

                {isLoading ? (
                    <Skeleton className="h-64 w-full" />
                ) : (
                    <DataTable
                        columns={columns}
                        data={filtered}
                        searchPlaceholder="Buscar por cliente..."
                    />
                )}
            </div>

            {/* Dialog de Sync Stripe */}
            <Dialog open={syncDialogOpen} onOpenChange={setSyncDialogOpen}>
                <DialogContent className="sm:max-w-md">
                    <DialogHeader className="pb-0">
                        <div className="flex items-center gap-3 mb-1">
                            <span className="flex items-center justify-center rounded-sm w-8 h-8 bg-violet-500/10 text-violet-600 shrink-0">
                                <Zap className="h-4 w-4" />
                            </span>
                            <DialogTitle className="text-base">Sincronizar Sessão Stripe</DialogTitle>
                        </div>
                        <DialogDescription className="text-xs text-muted-foreground">
                            Reprocesse um pagamento manualmente quando o webhook não for recebido.
                        </DialogDescription>
                    </DialogHeader>

                    <div className="space-y-3 pt-1 pb-1">
                        {/* Hint contextual */}
                        <div className="flex items-start gap-2 rounded-sm border border-muted bg-muted/40 px-3 py-2.5">
                            <Info className="h-3.5 w-3.5 mt-0.5 shrink-0 text-muted-foreground" />
                            <p className="text-[11px] text-muted-foreground leading-relaxed">
                                Acesse{" "}
                                <strong className="text-foreground">Stripe Dashboard → Payments</strong>,
                                selecione o pagamento e copie o{" "}
                                <code className="bg-muted px-1 py-0.5 rounded text-[10px] font-mono">ID do pagamento</code>{" "}
                                (começa com <code className="bg-muted px-1 py-0.5 rounded text-[10px] font-mono">pi_</code>).
                            </p>
                        </div>

                        {/* Input */}
                        <div className="space-y-1.5">
                            <label
                                htmlFor="syncSessionId"
                                className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground"
                            >
                                Session ID
                            </label>
                            <Input
                                id="syncSessionId"
                                size={14}
                                placeholder="pi_... ou cs_live_..."
                                value={syncSessionId}
                                onChange={(e) => setSyncSessionId(e.target.value)}
                                className="font-mono text-sm h-8 rounded-sm"
                                autoComplete="off"
                                spellCheck={false}
                            />
                            <p className="text-[10px] text-muted-foreground">
                                Aceita Payment Intent{" "}
                                <code className="font-mono">pi_...</code> ou Session ID{" "}
                                <code className="font-mono">cs_live_...</code> / <code className="font-mono">cs_test_...</code>
                            </p>
                        </div>
                    </div>

                    <DialogFooter className="gap-2 pt-2">
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={() => {
                                setSyncDialogOpen(false);
                                setSyncSessionId("");
                            }}
                        >
                            Cancelar
                        </Button>
                        <Button
                            variant="outline"
                            size="sm"
                            className="gap-1.5 border-violet-300 text-violet-700 hover:bg-violet-50 hover:text-violet-800 dark:border-violet-700 dark:text-violet-400 dark:hover:bg-violet-900/30"
                            disabled={!syncSessionId.trim() || syncMutation.isPending}
                            onClick={() => syncMutation.mutate(syncSessionId.trim())}
                        >
                            <RefreshCw className={`h-3.5 w-3.5 ${syncMutation.isPending ? "animate-spin" : ""}`} />
                            {syncMutation.isPending ? "Sincronizando..." : "Sincronizar"}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Dialog de Revisão */}
            <Dialog open={!!reviewingInvoice} onOpenChange={(o) => !o && setReviewingInvoice(null)}>
                <DialogContent className="max-w-md p-0">
                    <DialogHeader>
                        <div className="flex items-center gap-2.5">
                            <div className="size-8 rounded-sm bg-primary/10 flex items-center justify-center">
                                <Receipt className="size-4 text-primary" />
                            </div>
                            <DialogTitle>Revisão de Pagamento</DialogTitle>
                        </div>
                        <DialogDescription>
                            Auditoria financeira para <strong>{reviewingInvoice?.tenant_nome}</strong>.
                        </DialogDescription>
                    </DialogHeader>

                    <DialogBody className="flex flex-col gap-4">
                        <div className="flex items-center justify-between rounded-sm bg-muted/40 p-3 text-sm">
                            <span className="text-muted-foreground">Valor esperado</span>
                            <span className="font-bold">
                                {reviewingInvoice && formatCurrency(reviewingInvoice.valor)}
                            </span>
                        </div>

                        <div className="space-y-1.5">
                            <Label className="text-xs font-medium">Comprovante</Label>
                            <a
                                href={reviewingInvoice?.url_comprovante || "#"}
                                target="_blank"
                                rel="noreferrer"
                                className="flex items-center gap-3 rounded-sm border border-dashed border-primary/30 p-3 text-sm transition-colors hover:bg-primary/5"
                            >
                                <FileText className="size-6 shrink-0 text-primary" />
                                <span className="text-xs font-bold uppercase tracking-wide text-primary">
                                    Abrir documento de depósito
                                </span>
                            </a>
                        </div>

                        {reviewingInvoice?.status === "EM_ANALISE" && (
                            <div className="space-y-1.5">
                                <Label className="text-xs font-medium">Justificativa (caso rejeitado)</Label>
                                <Input
                                    className="h-8 text-xs rounded-sm"
                                    placeholder="Ex: Valor incorreto, comprovante ilegível..."
                                    value={rejectionReason}
                                    onChange={(e) => setRejectionReason(e.target.value)}
                                />
                            </div>
                        )}
                    </DialogBody>

                    <DialogFooter>
                        <Button
                            variant="outline"
                            size="sm"
                            className="rounded-sm"
                            disabled={reviewMutation.isPending}
                            onClick={() =>
                                reviewMutation.mutate({
                                    id: reviewingInvoice!.id,
                                    aprovado: false,
                                    justificativa: rejectionReason,
                                })
                            }
                        >
                            <XCircle data-icon="inline-start" className="size-3.5" />
                            Rejeitar
                        </Button>
                        <Button
                            size="sm"
                            className="rounded-sm"
                            disabled={reviewMutation.isPending}
                            onClick={() =>
                                reviewMutation.mutate({
                                    id: reviewingInvoice!.id,
                                    aprovado: true,
                                })
                            }
                        >
                            <CheckCircle2 data-icon="inline-start" className="size-3.5" />
                            Aprovar Pagamento
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}
