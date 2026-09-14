"use client";

import { useEffect, useState } from "react";
import { useAppStore } from "@/lib/stores/app-store";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { toast } from "sonner";
import { AlertTriangle, Plus, CheckCircle, Clock, XCircle, Flame, Waves, Eye } from "lucide-react";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/shared/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogBody, DialogDescription } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { PermissionGuard } from "@/components/auth/permission-guard";

export interface Alerta {
    id: string;
    unidade_produtiva_id: string;
    fazenda_nome?: string;
    tipo: string;
    severidade: string;
    status: string;
    area_ha?: number;
    descricao?: string;
    fonte?: string;
    talhao_nome?: string;
    data_deteccao: string;
    data_resolucao?: string;
    unidade_nome?: string;
}

type Talhao = { id: string; nome: string; area_hectares?: number | null };

type AlertaForm = {
    fazenda_nome: string; tipo: string; severidade: string; area_ha: string;
    descricao: string; fonte: string; talhao_nome: string; data_deteccao: string;
};

type AlertaPayload = Omit<AlertaForm, "area_ha" | "data_deteccao"> & { area_ha?: number; data_deteccao?: string; unidade_produtiva_id: string };

const SEV_CFG: Record<string, string> = {
    BAIXA:  "bg-green-100 text-green-700 border-green-200",
    MEDIA:  "bg-yellow-100 text-yellow-700 border-yellow-200",
    ALTA:   "bg-orange-100 text-orange-700 border-orange-200",
    CRITICA:"bg-red-100 text-red-700 border-red-200",
};

const STATUS_CFG: Record<string, { label: string; color: string }> = {
    NOVO:       { label: "Novo",        color: "bg-red-100 text-red-700 border-red-200" },
    EM_ANALISE: { label: "Em Análise",  color: "bg-blue-100 text-blue-700 border-blue-200" },
    RESOLVIDO:  { label: "Resolvido",   color: "bg-green-100 text-green-700 border-green-200" },
    IGNORADO:   { label: "Ignorado",    color: "bg-muted text-muted-foreground border-border" },
};

const TIPO_ICONS: Record<string, React.ReactNode> = {
    DESMATAMENTO: <AlertTriangle size={14} className="text-red-500" />,
    QUEIMADA:     <Flame size={14} className="text-orange-500" />,
    INUNDACAO:    <Waves size={14} className="text-blue-500" />,
    EROSAO:       <AlertTriangle size={14} className="text-amber-500" />,
    OUTRO:        <Eye size={14} className="text-muted-foreground" />,
};

const EMPTY = { fazenda_nome: "", tipo: "DESMATAMENTO", severidade: "MEDIA", area_ha: "", descricao: "", fonte: "", talhao_nome: "", data_deteccao: "" };
const FILTER_KEY = "ambiental.monitoramento.alertas.status";

export function AlertasClient({ initialData }: { initialData: Alerta[] }) {
    const activeFazendaId = useAppStore((state) => state.activeFazendaId);
    const unidadesAutorizadas = useAppStore((state) => state.unidadesProdutivasAutorizadas);
    const unidadeSelecionada = unidadesAutorizadas.find((unidade) => unidade.id === activeFazendaId);
    const qc = useQueryClient();
    const [filtroStatus, setFiltroStatus] = useState("abertos");
    const [hydrated, setHydrated] = useState(false);
    const [showForm, setShowForm] = useState(false);
    const [resolvendo, setResolvendo] = useState<Alerta | null>(null);
    const [resolucao, setResolucao] = useState("");
    const [form, setForm] = useState(EMPTY);

    function abrirNovoAlerta() {
        if (!activeFazendaId || !unidadeSelecionada) {
            toast.error("Selecione uma unidade produtiva no topbar antes de registrar o alerta.");
            return;
        }
        setForm({ ...EMPTY, fazenda_nome: unidadeSelecionada.nome });
        setShowForm(true);
    }

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

    const statusQs = filtroStatus === "abertos" ? "status=NOVO&status=EM_ANALISE" : filtroStatus !== "todos" ? `status=${filtroStatus}` : "";

    const { data: alertas = [], isLoading, error: erroAlertas } = useQuery<Alerta[]>({
        queryKey: ["ambiental", "alertas", filtroStatus],
        queryFn: () => apiFetch(`/ambiental/alertas${statusQs ? `?${statusQs}` : ""}`),
        initialData: filtroStatus === "abertos" ? initialData : undefined,
    });
    const { data: talhoes = [], isLoading: carregandoTalhoes } = useQuery<Talhao[]>({
        queryKey: ["ambiental", "alertas", "talhoes", activeFazendaId],
        queryFn: () => apiFetch("/cadastros/areas-rurais/", { params: { tipo: "TALHAO", unidade_produtiva_id: activeFazendaId } }),
        enabled: !!activeFazendaId && showForm,
    });

    const criarMut = useMutation({
        mutationFn: (d: AlertaPayload) => apiFetch("/ambiental/alertas", { method: "POST", body: JSON.stringify(d) }),
        onSuccess: () => { qc.invalidateQueries({ queryKey: ["ambiental", "alertas"] }); setShowForm(false); setForm(EMPTY); toast.success("Alerta registrado."); },
        onError: (e: Error) => toast.error(e.message),
    });

    const resolverMut = useMutation({
        mutationFn: ({ id, desc }: { id: string; desc: string }) => apiFetch(`/ambiental/alertas/${id}`, { method: "PATCH", body: JSON.stringify({ status: "RESOLVIDO", data_resolucao: new Date().toISOString().split("T")[0], resolucao_descricao: desc }) }),
        onSuccess: () => { qc.invalidateQueries({ queryKey: ["ambiental", "alertas"] }); setResolvendo(null); setResolucao(""); toast.success("Alerta resolvido."); },
        onError: (e: Error) => toast.error(e.message),
    });

    function salvar() {
        if (!activeFazendaId) { toast.error("Selecione uma fazenda antes de registrar o alerta."); return; }
        if (!form.tipo || !form.severidade) { toast.error("Tipo e severidade obrigatórios."); return; }
        const p: AlertaPayload = {
            unidade_produtiva_id: activeFazendaId,
            fazenda_nome: form.fazenda_nome || unidadeSelecionada?.nome || undefined, tipo: form.tipo, severidade: form.severidade,
            descricao: form.descricao, fonte: form.fonte, talhao_nome: form.talhao_nome,
            ...(form.data_deteccao ? { data_deteccao: form.data_deteccao } : {}),
            ...(form.area_ha ? { area_ha: parseFloat(form.area_ha) } : {}),
        };
        criarMut.mutate(p);
    }

    const abertos = alertas.filter(a => a.status === "NOVO" || a.status === "EM_ANALISE").length;
    const criticos = alertas.filter(a => a.severidade === "CRITICA").length;

    return (
        <div className="w-full p-6 flex flex-col gap-6">
            <PageHeader
                title="Alertas de Desmatamento"
                description="Monitoramento de eventos ambientais em suas propriedades."
                breadcrumbs={[
                    { label: "Dashboard", href: "/dashboard" },
                    { label: "Ambiental", href: "/dashboard/ambiental" },
                    { label: "Monitoramento" },
                    { label: "Alertas" },
                ]}
                icon={<AlertTriangle />}
                actions={(
                    <PermissionGuard permission="ambiental:monitoramento:create">
                        <Button size="sm" onClick={abrirNovoAlerta}>
                            <Plus data-icon="inline-start" />
                            Registrar Alerta
                        </Button>
                    </PermissionGuard>
                )}
            />

            <div role="status" className="rounded-sm border border-violet-500/20 bg-violet-500/10 px-3 py-2 text-sm text-violet-800 dark:text-violet-200">
                <strong>Visão consolidada:</strong> os alertas exibidos pertencem a todas as unidades produtivas autorizadas. A unidade selecionada no topbar é usada apenas para novos registros.
            </div>

            <Card>
                <CardContent className="flex flex-wrap items-center gap-x-6 gap-y-2 p-4 text-sm">
                    <span><strong>{unidadesAutorizadas.length}</strong> unidade(s) monitorada(s)</span>
                    <span className="text-muted-foreground">{alertas.length === 0 ? "Nenhum alerta foi registrado ainda." : `${alertas.length} alerta(s) no filtro atual.`}</span>
                </CardContent>
            </Card>

            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                {[
                    { label: "Abertos", value: abertos, icon: <Clock />, color: "text-yellow-600" },
                    { label: "Críticos", value: criticos, icon: <AlertTriangle />, color: "text-red-600" },
                    { label: "Total", value: alertas.length, icon: <Eye />, color: "text-foreground" },
                    { label: "Resolvidos", value: alertas.filter(a => a.status === "RESOLVIDO").length, icon: <CheckCircle />, color: "text-green-600" },
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
                        <SelectItem value="abertos">Abertos</SelectItem>
                        {Object.entries(STATUS_CFG).map(([k, v]) => <SelectItem key={k} value={k}>{v.label}</SelectItem>)}
                    </SelectContent>
                </Select>
                </CardContent>
            </Card>

            <Card>
                <CardHeader className="pb-2"><CardTitle className="text-sm font-medium text-muted-foreground">Alertas</CardTitle></CardHeader>
                <CardContent className="p-0">
                    {isLoading ? (
                        <div className="flex flex-col gap-2 p-4">{[1,2,3].map(i => <Skeleton key={i} className="h-10 w-full" />)}</div>
                    ) : erroAlertas ? (
                        <div className="py-10 flex flex-col items-center gap-2 text-center">
                            <XCircle size={32} className="text-destructive/70" />
                            <p className="text-sm font-medium">Não foi possível carregar os alertas.</p>
                            <p className="text-xs text-muted-foreground">Atualize a página ou verifique sua sessão e o produtor selecionado.</p>
                        </div>
                    ) : alertas.length === 0 ? (
                        <div className="py-10 flex flex-col items-center gap-2">
                            <CheckCircle size={32} className="text-green-400" />
                            <p className="text-sm text-muted-foreground">Nenhum alerta encontrado.</p>
                        </div>
                    ) : (
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead>Tipo</TableHead>
                                    <TableHead>Fazenda / Talhão</TableHead>
                                    <TableHead>Severidade</TableHead>
                                    <TableHead>Área (ha)</TableHead>
                                    <TableHead>Status</TableHead>
                                    <TableHead>Detecção</TableHead>
                                    <TableHead></TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {alertas.map(a => (
                                    <TableRow key={a.id}>
                                        <TableCell><div className="flex items-center gap-1.5">{TIPO_ICONS[a.tipo]}<span className="text-xs">{a.tipo}</span></div></TableCell>
                                        <TableCell className="text-sm"><div>{a.fazenda_nome ?? "—"}</div><div className="text-xs text-muted-foreground">{a.unidade_nome ?? unidadesAutorizadas.find((unidade) => unidade.id === a.unidade_produtiva_id)?.nome ?? "Unidade produtiva"}</div>{a.talhao_nome && <div className="text-xs text-muted-foreground">Talhão: {a.talhao_nome}</div>}</TableCell>
                                        <TableCell><span className={`inline-flex items-center px-2 py-0.5 rounded-full border text-xs font-medium ${SEV_CFG[a.severidade] ?? ""}`}>{a.severidade}</span></TableCell>
                                        <TableCell className="tabular-nums text-sm">{a.area_ha ?? "—"}</TableCell>
                                        <TableCell>
                                            {(() => { const s = STATUS_CFG[a.status]; return s ? <span className={`inline-flex items-center px-2 py-0.5 rounded-full border text-xs font-medium ${s.color}`}>{s.label}</span> : null; })()}
                                        </TableCell>
                                        <TableCell className="text-xs text-muted-foreground">{new Date(a.data_deteccao).toLocaleDateString("pt-BR")}</TableCell>
                                        <TableCell>{(a.status === "NOVO" || a.status === "EM_ANALISE") && (
                                            <PermissionGuard permission="ambiental:monitoramento:edit">
                                                <Button size="sm" variant="outline" className="h-7 text-xs" onClick={() => setResolvendo(a)}>
                                                    <CheckCircle data-icon="inline-start" />
                                                    Resolver
                                                </Button>
                                            </PermissionGuard>
                                        )}</TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    )}
                </CardContent>
            </Card>

            <Dialog open={showForm} onOpenChange={o => { if (!o) { setShowForm(false); setForm(EMPTY); } }}>
                <DialogContent className="max-h-[90vh] overflow-hidden p-0 sm:max-w-2xl">
                    <DialogHeader className="border-b px-4 py-4">
                        <div className="flex items-start gap-3">
                            <div className="rounded-lg border bg-muted/40 p-2">
                                <AlertTriangle />
                            </div>
                            <div className="flex flex-col gap-1">
                                <DialogTitle>Registrar Alerta Ambiental</DialogTitle>
                                <DialogDescription>Cadastre um evento ambiental para acompanhar severidade, fonte e localização.</DialogDescription>
                            </div>
                        </div>
                    </DialogHeader>
                    <DialogBody className="flex flex-col gap-4 overflow-y-auto px-4 py-3">
                        <div className="grid gap-3 md:grid-cols-2">
                            <div className="flex flex-col gap-2"><Label>Tipo <span className="text-destructive">*</span></Label>
                                <Select value={form.tipo} onValueChange={v => setForm(f => ({ ...f, tipo: v }))}>
                                    <SelectTrigger><SelectValue /></SelectTrigger>
                                    <SelectContent>{["DESMATAMENTO","QUEIMADA","INUNDACAO","EROSAO","OUTRO"].map(t => <SelectItem key={t} value={t}>{t}</SelectItem>)}</SelectContent>
                                </Select>
                            </div>
                            <div className="flex flex-col gap-2"><Label>Severidade <span className="text-destructive">*</span></Label>
                                <Select value={form.severidade} onValueChange={v => setForm(f => ({ ...f, severidade: v }))}>
                                    <SelectTrigger><SelectValue /></SelectTrigger>
                                    <SelectContent>{["BAIXA","MEDIA","ALTA","CRITICA"].map(s => <SelectItem key={s} value={s}>{s}</SelectItem>)}</SelectContent>
                                </Select>
                            </div>
                        </div>
                        <div className="grid gap-3 md:grid-cols-2">
                            <div className="flex flex-col gap-2"><Label>Unidade produtiva selecionada</Label>
                                <Input placeholder="Selecione uma unidade no topbar" value={unidadeSelecionada?.nome ?? ""} readOnly />
                                {!unidadeSelecionada && <p className="text-xs text-destructive">Selecione uma unidade produtiva no topbar.</p>}
                            </div>
                            <div className="flex flex-col gap-2"><Label>Talhão</Label>
                                <Select value={form.talhao_nome} onValueChange={v => setForm(f => ({ ...f, talhao_nome: v }))} disabled={!activeFazendaId || carregandoTalhoes || talhoes.length === 0}>
                                    <SelectTrigger><SelectValue placeholder={carregandoTalhoes ? "Carregando talhões..." : talhoes.length === 0 ? "Nenhum talhão cadastrado" : "Selecione o talhão"} /></SelectTrigger>
                                    <SelectContent>{talhoes.map(t => <SelectItem key={t.id} value={t.nome}>{t.nome}{t.area_hectares != null ? ` — ${t.area_hectares} ha` : ""}</SelectItem>)}</SelectContent>
                                </Select>
                            </div>
                        </div>
                        <div className="grid gap-3 md:grid-cols-2">
                            <div className="flex flex-col gap-2"><Label>Área (ha)</Label>
                                <Input type="number" placeholder="0.00" value={form.area_ha} onChange={e => setForm(f => ({ ...f, area_ha: e.target.value }))} /></div>
                            <div className="flex flex-col gap-2"><Label>Data Detecção</Label>
                                <Input type="date" value={form.data_deteccao} onChange={e => setForm(f => ({ ...f, data_deteccao: e.target.value }))} /></div>
                        </div>
                        <div className="flex flex-col gap-2"><Label>Fonte</Label>
                            <Input placeholder="PRODES, DETER, SICAR, Manual..." value={form.fonte} onChange={e => setForm(f => ({ ...f, fonte: e.target.value }))} /></div>
                        <div className="flex flex-col gap-2"><Label>Descrição</Label>
                            <Textarea rows={2} value={form.descricao} onChange={e => setForm(f => ({ ...f, descricao: e.target.value }))} /></div>
                    </DialogBody>
                    <DialogFooter className="border-t px-4 py-4">
                        <Button variant="outline" onClick={() => setShowForm(false)}>Cancelar</Button>
                        <Button onClick={salvar} disabled={criarMut.isPending}>
                            <Plus data-icon="inline-start" />
                            {criarMut.isPending ? "Salvando..." : "Registrar"}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            <Dialog open={!!resolvendo} onOpenChange={o => { if (!o) { setResolvendo(null); setResolucao(""); } }}>
                <DialogContent className="max-h-[90vh] overflow-hidden p-0 sm:max-w-lg">
                    <DialogHeader className="border-b px-4 py-4">
                        <div className="flex items-start gap-3">
                            <div className="rounded-lg border bg-muted/40 p-2">
                                <CheckCircle />
                            </div>
                            <div className="flex flex-col gap-1">
                                <DialogTitle>Resolver Alerta</DialogTitle>
                                <DialogDescription>Registre o encerramento com as ações executadas e a data de resolução.</DialogDescription>
                            </div>
                        </div>
                    </DialogHeader>
                    <DialogBody className="flex flex-col gap-3 overflow-y-auto px-4 py-3">
                        <p className="text-sm text-muted-foreground">Descreva as ações tomadas para resolver o alerta <strong>{resolvendo?.tipo}</strong> em <strong>{resolvendo?.fazenda_nome ?? "fazenda não informada"}</strong>.</p>
                        <Textarea rows={3} placeholder="Medidas adotadas, órgãos acionados..." value={resolucao} onChange={e => setResolucao(e.target.value)} />
                    </DialogBody>
                    <DialogFooter className="border-t px-4 py-4">
                        <Button variant="outline" onClick={() => setResolvendo(null)}>Cancelar</Button>
                        <Button onClick={() => resolvendo && resolverMut.mutate({ id: resolvendo.id, desc: resolucao })} disabled={resolverMut.isPending}>
                            {resolverMut.isPending ? "Resolvendo..." : "Marcar como Resolvido"}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}
