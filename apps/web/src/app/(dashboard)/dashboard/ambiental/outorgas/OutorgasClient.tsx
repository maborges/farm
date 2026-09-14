"use client";

import { useEffect, useState } from "react";
import { useAppStore } from "@/lib/stores/app-store";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { toast } from "sonner";
import { Droplets, Plus, Pencil, AlertTriangle, CheckCircle, Clock } from "lucide-react";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/shared/page-header";
import { Card, CardContent } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogBody, DialogDescription } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Skeleton } from "@/components/ui/skeleton";
import { PermissionGuard } from "@/components/auth/permission-guard";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

export interface Outorga {
    id: string;
    unidade_produtiva_id: string;
    fazenda_nome?: string;
    numero_outorga: string;
    orgao_emissor?: string;
    tipo_uso: string;
    corpo_hidrico?: string;
    vazao_outorgada_ls?: number;
    vazao_outorgada_m3h?: number;
    status: string;
    data_emissao?: string;
    data_vencimento?: string;
    observacoes?: string;
    unidade_nome?: string;
}

type OutorgaForm = {
    fazenda_nome: string; numero_outorga: string; orgao_emissor: string; tipo_uso: string;
    corpo_hidrico: string; vazao_outorgada_ls: string; vazao_outorgada_m3h: string;
    data_emissao: string; data_vencimento: string; observacoes: string; status: string;
};

type OutorgaPayload = Omit<OutorgaForm, "vazao_outorgada_ls" | "vazao_outorgada_m3h" | "data_emissao" | "data_vencimento" | "status"> & {
    unidade_produtiva_id: string;
    status?: string;
    data_emissao?: string; data_vencimento?: string;
    vazao_outorgada_ls?: number; vazao_outorgada_m3h?: number;
};

const STATUS_CFG: Record<string, { label: string; color: string; icon: React.ReactNode }> = {
    ATIVA:        { label: "Ativa",        color: "bg-green-100 text-green-700 border-green-200",   icon: <CheckCircle size={11} /> },
    VENCIDA:      { label: "Vencida",      color: "bg-red-100 text-red-700 border-red-200",         icon: <AlertTriangle size={11} /> },
    SUSPENSA:     { label: "Suspensa",     color: "bg-orange-100 text-orange-700 border-orange-200", icon: <AlertTriangle size={11} /> },
    CANCELADA:    { label: "Cancelada",    color: "bg-muted text-muted-foreground border-border",   icon: null },
    EM_RENOVACAO: { label: "Em Renovação", color: "bg-blue-100 text-blue-700 border-blue-200",      icon: <Clock size={11} /> },
};

const TIPOS_USO = [
    { value: "IRRIGACAO", label: "Irrigação" },
    { value: "DESSEDENTACAO", label: "Dessedentação Animal" },
    { value: "USO_INDUSTRIAL", label: "Uso Industrial" },
    { value: "AQUICULTURA", label: "Aquicultura" },
    { value: "OUTRO", label: "Outro" },
];

const EMPTY = { fazenda_nome: "", numero_outorga: "", orgao_emissor: "", tipo_uso: "IRRIGACAO", corpo_hidrico: "", vazao_outorgada_ls: "", vazao_outorgada_m3h: "", data_emissao: "", data_vencimento: "", observacoes: "", status: "ATIVA" };
const FILTER_KEY = "ambiental.outorgas.status";

function StatusBadge({ status }: { status: string }) {
    const cfg = STATUS_CFG[status] ?? { label: status, color: "bg-muted text-muted-foreground border-border", icon: null };
    return (
        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full border text-xs font-medium ${cfg.color}`}>
            {cfg.icon} {cfg.label}
        </span>
    );
}

function diasParaVencer(iso?: string): number | null {
    if (!iso) return null;
    return Math.round((new Date(iso).getTime() - Date.now()) / 86400000);
}

export function OutorgasClient({ initialData }: { initialData: Outorga[] }) {
    const activeFazendaId = useAppStore((state) => state.activeFazendaId);
    const unidadesAutorizadas = useAppStore((state) => state.unidadesProdutivasAutorizadas);
    const unidadeSelecionada = unidadesAutorizadas.find((unidade) => unidade.id === activeFazendaId);
    const qc = useQueryClient();
    const [filtroStatus, setFiltroStatus] = useState("todos");
    const [hydrated, setHydrated] = useState(false);
    const [showForm, setShowForm] = useState(false);
    const [editando, setEditando] = useState<Outorga | null>(null);
    const [form, setForm] = useState(EMPTY);

    useEffect(() => {
        const saved = window.localStorage.getItem(FILTER_KEY);
        // eslint-disable-next-line react-hooks/set-state-in-effect
        if (saved) setFiltroStatus(saved);
        setHydrated(true);
    }, []);

    useEffect(() => {
        if (!hydrated) return;
        window.localStorage.setItem(FILTER_KEY, filtroStatus);
    }, [filtroStatus, hydrated]);

    const qs = filtroStatus !== "todos" ? `?status=${filtroStatus}` : "";
    const { data: outorgas = [], isLoading, error: erroOutorgas } = useQuery<Outorga[]>({
        queryKey: ["ambiental", "outorgas", filtroStatus],
        queryFn: () => apiFetch(`/ambiental/outorgas${qs}`),
        initialData: filtroStatus === "todos" ? initialData : undefined,
    });

    const criarMut = useMutation({
        mutationFn: (d: OutorgaPayload) => apiFetch("/ambiental/outorgas", { method: "POST", body: JSON.stringify(d) }),
        onSuccess: () => { qc.invalidateQueries({ queryKey: ["ambiental", "outorgas"] }); fechar(); toast.success("Outorga cadastrada."); },
        onError: (e: Error) => toast.error(e.message),
    });
    const editarMut = useMutation({
        mutationFn: ({ id, d }: { id: string; d: OutorgaPayload }) => apiFetch(`/ambiental/outorgas/${id}`, { method: "PATCH", body: JSON.stringify(d) }),
        onSuccess: () => { qc.invalidateQueries({ queryKey: ["ambiental", "outorgas"] }); fechar(); toast.success("Outorga atualizada."); },
        onError: (e: Error) => toast.error(e.message),
    });

    function fechar() { setShowForm(false); setEditando(null); setForm(EMPTY); }
    function abrirNova() {
        if (!activeFazendaId || !unidadeSelecionada) {
            toast.error("Selecione uma unidade produtiva no topbar antes de cadastrar a outorga.");
            return;
        }
        setForm({ ...EMPTY, fazenda_nome: unidadeSelecionada.nome });
        setShowForm(true);
    }
    function abrirEditar(o: Outorga) {
        setEditando(o);
        setForm({ fazenda_nome: o.fazenda_nome ?? "", numero_outorga: o.numero_outorga, orgao_emissor: o.orgao_emissor ?? "", tipo_uso: o.tipo_uso, corpo_hidrico: o.corpo_hidrico ?? "", vazao_outorgada_ls: o.vazao_outorgada_ls?.toString() ?? "", vazao_outorgada_m3h: o.vazao_outorgada_m3h?.toString() ?? "", data_emissao: o.data_emissao ?? "", data_vencimento: o.data_vencimento ?? "", observacoes: o.observacoes ?? "", status: o.status });
    }
    function salvar() {
        if (!activeFazendaId && !editando) { toast.error("Selecione uma fazenda antes de cadastrar a outorga."); return; }
        if (!form.numero_outorga) { toast.error("Número da outorga é obrigatório."); return; }
        const p: OutorgaPayload = {
            unidade_produtiva_id: activeFazendaId,
            fazenda_nome: form.fazenda_nome || unidadeSelecionada?.nome || "", numero_outorga: form.numero_outorga,
            orgao_emissor: form.orgao_emissor, tipo_uso: form.tipo_uso,
            corpo_hidrico: form.corpo_hidrico, observacoes: form.observacoes,
            ...(editando ? { status: form.status } : {}),
            ...(form.data_emissao ? { data_emissao: form.data_emissao } : {}),
            ...(form.data_vencimento ? { data_vencimento: form.data_vencimento } : {}),
            ...(form.vazao_outorgada_ls ? { vazao_outorgada_ls: parseFloat(form.vazao_outorgada_ls) } : {}),
            ...(form.vazao_outorgada_m3h ? { vazao_outorgada_m3h: parseFloat(form.vazao_outorgada_m3h) } : {}),
        };
        if (editando) editarMut.mutate({ id: editando.id, d: p });
        else criarMut.mutate(p);
    }

    const ativas = outorgas.filter(o => o.status === "ATIVA").length;
    const vencidas = outorgas.filter(o => o.status === "VENCIDA").length;
    const vencendo = outorgas.filter(o => { const d = diasParaVencer(o.data_vencimento); return d !== null && d >= 0 && d <= 90; }).length;

    return (
        <div className="w-full p-6 flex flex-col gap-6">
            <PageHeader
                title="Outorgas Hídricas"
                description="Gestão de licenças para captação e uso de água."
                breadcrumbs={[
                    { label: "Dashboard", href: "/dashboard" },
                    { label: "Ambiental", href: "/dashboard/ambiental" },
                    { label: "Outorgas" },
                ]}
                icon={<Droplets />}
                actions={(
                    <PermissionGuard permission="ambiental:outorgas:create">
                        <Button size="sm" onClick={abrirNova}>
                            <Plus data-icon="inline-start" />
                            Nova Outorga
                        </Button>
                    </PermissionGuard>
                )}
            />

            <div role="status" className="rounded-sm border border-violet-500/20 bg-violet-500/10 px-3 py-2 text-sm text-violet-800 dark:text-violet-200">
                <strong>Visão consolidada:</strong> as outorgas exibidas pertencem a todas as unidades produtivas autorizadas. A unidade selecionada no topbar é usada para novos cadastros.
            </div>

            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                {[
                    { label: "Total", value: outorgas.length, icon: <Droplets />, color: "text-foreground" },
                    { label: "Ativas", value: ativas, icon: <CheckCircle />, color: "text-green-600" },
                    { label: "Vencendo (90d)", value: vencendo, icon: <Clock />, color: "text-yellow-600" },
                    { label: "Vencidas", value: vencidas, icon: <AlertTriangle />, color: "text-red-600" },
                ].map(k => (
                    <Card key={k.label}><CardContent className="flex items-center gap-3 py-4">{k.icon}<div>
                        <p className="text-xs text-muted-foreground">{k.label}</p>
                        <p className={`text-xl font-bold tabular-nums ${k.color}`}>{k.value}</p>
                    </div></CardContent></Card>
                ))}
            </div>

            <Card>
                <CardContent className="flex items-center gap-3 p-4">
                <Select value={filtroStatus} onValueChange={setFiltroStatus}>
                    <SelectTrigger className="h-9 w-[180px] text-sm"><SelectValue /></SelectTrigger>
                    <SelectContent>
                        <SelectItem value="todos">Todos</SelectItem>
                        {Object.entries(STATUS_CFG).map(([k, v]) => <SelectItem key={k} value={k}>{v.label}</SelectItem>)}
                    </SelectContent>
                </Select>
                </CardContent>
            </Card>

            <Card>
                <CardContent className="p-0">
                    {isLoading ? (
                        <div className="flex flex-col gap-2 p-4">{[1,2,3].map(i => <Skeleton key={i} className="h-10 w-full" />)}</div>
                    ) : erroOutorgas ? (
                        <div className="py-10 flex flex-col items-center gap-2 text-center">
                            <AlertTriangle size={32} className="text-destructive/70" />
                            <p className="text-sm font-medium">Não foi possível carregar as outorgas.</p>
                            <p className="text-xs text-muted-foreground">Atualize a página ou verifique sua sessão e o produtor selecionado.</p>
                        </div>
                    ) : outorgas.length === 0 ? (
                        <div className="py-10 flex flex-col items-center gap-2 text-center">
                            <Droplets className="text-muted-foreground/40" />
                            <p className="text-sm text-muted-foreground">Nenhuma outorga cadastrada.</p>
                            <Button size="sm" variant="outline" onClick={abrirNova}>
                                <Plus data-icon="inline-start" />
                                Cadastrar outorga
                            </Button>
                        </div>
                    ) : (
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead>Número / Órgão</TableHead>
                                    <TableHead>Fazenda</TableHead>
                                    <TableHead>Tipo Uso</TableHead>
                                    <TableHead>Corpo Hídrico</TableHead>
                                    <TableHead>Vazão</TableHead>
                                    <TableHead>Vencimento</TableHead>
                                    <TableHead>Status</TableHead>
                                    <TableHead></TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {outorgas.map(o => {
                                    const dias = diasParaVencer(o.data_vencimento);
                                    return (
                                        <TableRow key={o.id}>
                                            <TableCell>
                                                <div className="font-mono text-xs font-semibold">{o.numero_outorga}</div>
                                                {o.orgao_emissor && <div className="text-xs text-muted-foreground">{o.orgao_emissor}</div>}
                                            </TableCell>
                                            <TableCell className="text-sm"><div>{o.fazenda_nome ?? "—"}</div><div className="text-xs text-muted-foreground">{o.unidade_nome ?? unidadesAutorizadas.find((unidade) => unidade.id === o.unidade_produtiva_id)?.nome ?? "Unidade produtiva"}</div></TableCell>
                                            <TableCell className="text-xs">{TIPOS_USO.find(t => t.value === o.tipo_uso)?.label ?? o.tipo_uso}</TableCell>
                                            <TableCell className="text-xs text-muted-foreground">{o.corpo_hidrico ?? "—"}</TableCell>
                                            <TableCell className="text-xs tabular-nums">
                                                {o.vazao_outorgada_ls ? `${o.vazao_outorgada_ls} L/s` : o.vazao_outorgada_m3h ? `${o.vazao_outorgada_m3h} m³/h` : "—"}
                                            </TableCell>
                                            <TableCell>
                                                {o.data_vencimento ? (
                                                    <div>
                                                        <div className="text-xs">{new Date(o.data_vencimento).toLocaleDateString("pt-BR")}</div>
                                                        {dias !== null && dias >= 0 && dias <= 90 && (
                                                            <div className="text-xs text-yellow-600 font-medium">{dias}d restantes</div>
                                                        )}
                                                        {dias !== null && dias < 0 && (
                                                            <div className="text-xs text-red-600 font-medium">Vencida</div>
                                                        )}
                                                    </div>
                                                ) : "—"}
                                            </TableCell>
                                            <TableCell><StatusBadge status={o.status} /></TableCell>
                                            <TableCell>
                                                <PermissionGuard permission="ambiental:outorgas:edit">
                                                    <Button size="icon-sm" variant="ghost" onClick={() => abrirEditar(o)}>
                                                        <Pencil data-icon="inline-start" />
                                                    </Button>
                                                </PermissionGuard>
                                            </TableCell>
                                        </TableRow>
                                    );
                                })}
                            </TableBody>
                        </Table>
                    )}
                </CardContent>
            </Card>

            <Dialog open={showForm || !!editando} onOpenChange={o => !o && fechar()}>
                <DialogContent className="max-h-[90vh] overflow-hidden p-0 sm:max-w-2xl">
                    <DialogHeader className="border-b px-4 py-4">
                        <div className="flex items-start gap-3">
                            <div className="rounded-lg border bg-muted/40 p-2">
                                <Droplets />
                            </div>
                            <div className="flex flex-col gap-1">
                                <DialogTitle>{editando ? "Editar Outorga" : "Nova Outorga Hídrica"}</DialogTitle>
                                <DialogDescription>Informe os dados da licença para captação e uso de água.</DialogDescription>
                            </div>
                        </div>
                    </DialogHeader>
                    <DialogBody className="grid gap-4 overflow-y-auto px-4 py-3 md:grid-cols-2">
                        <div className="md:col-span-2 flex flex-col gap-2"><Label>Número da Outorga <span className="text-destructive">*</span></Label>
                            <Input placeholder="ex: 001/2024-IGAM" value={form.numero_outorga} onChange={e => setForm(f => ({ ...f, numero_outorga: e.target.value }))} /></div>
                        <div className="flex flex-col gap-2"><Label>Unidade produtiva selecionada</Label>
                            <Input placeholder="Selecione uma unidade no topbar" value={editando?.unidade_nome ?? unidadesAutorizadas.find((unidade) => unidade.id === editando?.unidade_produtiva_id)?.nome ?? unidadeSelecionada?.nome ?? ""} readOnly />
                            {!editando && !unidadeSelecionada && <p className="text-xs text-destructive">Selecione uma unidade produtiva no topbar.</p>}
                        </div>
                        <div className="flex flex-col gap-2"><Label>Órgão Emissor</Label>
                            <Input placeholder="IGAM, ANA, SEMARH..." value={form.orgao_emissor} onChange={e => setForm(f => ({ ...f, orgao_emissor: e.target.value }))} /></div>
                        <div className="flex flex-col gap-2"><Label>Tipo de Uso</Label>
                            <Select value={form.tipo_uso} onValueChange={v => setForm(f => ({ ...f, tipo_uso: v }))}>
                                <SelectTrigger><SelectValue /></SelectTrigger>
                                <SelectContent>{TIPOS_USO.map(t => <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>)}</SelectContent>
                            </Select>
                        </div>
                        <div className="flex flex-col gap-2"><Label>Corpo Hídrico</Label>
                            <Input placeholder="Rio, córrego, represa..." value={form.corpo_hidrico} onChange={e => setForm(f => ({ ...f, corpo_hidrico: e.target.value }))} /></div>
                        <div className="flex flex-col gap-2"><Label>Vazão (L/s)</Label>
                            <Input type="number" placeholder="0.00" value={form.vazao_outorgada_ls} onChange={e => setForm(f => ({ ...f, vazao_outorgada_ls: e.target.value }))} /></div>
                        <div className="flex flex-col gap-2"><Label>Vazão (m³/h)</Label>
                            <Input type="number" placeholder="0.00" value={form.vazao_outorgada_m3h} onChange={e => setForm(f => ({ ...f, vazao_outorgada_m3h: e.target.value }))} /></div>
                        <div className="flex flex-col gap-2"><Label>Data de Emissão</Label>
                            <Input type="date" value={form.data_emissao} onChange={e => setForm(f => ({ ...f, data_emissao: e.target.value }))} /></div>
                        <div className="flex flex-col gap-2"><Label>Vencimento</Label>
                            <Input type="date" value={form.data_vencimento} onChange={e => setForm(f => ({ ...f, data_vencimento: e.target.value }))} /></div>
                        {editando && <div className="flex flex-col gap-2"><Label>Status</Label>
                            <Select value={form.status} onValueChange={v => setForm(f => ({ ...f, status: v }))}>
                                <SelectTrigger><SelectValue /></SelectTrigger>
                                <SelectContent>{Object.entries(STATUS_CFG).map(([k, v]) => <SelectItem key={k} value={k}>{v.label}</SelectItem>)}</SelectContent>
                            </Select>
                        </div>}
                        <div className="md:col-span-2 flex flex-col gap-2"><Label>Observações</Label>
                            <Textarea rows={2} value={form.observacoes} onChange={e => setForm(f => ({ ...f, observacoes: e.target.value }))} /></div>
                    </DialogBody>
                    <DialogFooter className="border-t px-4 py-4">
                        <Button variant="outline" onClick={fechar}>Cancelar</Button>
                        <Button onClick={salvar} disabled={criarMut.isPending || editarMut.isPending}>
                            {criarMut.isPending || editarMut.isPending ? "Salvando..." : editando ? "Salvar" : "Cadastrar"}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}
