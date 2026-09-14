"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { useAppStore } from "@/lib/stores/app-store";
import { toast } from "sonner";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";
import {
    Activity, Plus, Beef, Scale, Baby, Syringe,
    ArrowRightLeft, HeartPulse, ChevronRight, Calendar,
    X, Loader2, FileText, Scissors
} from "lucide-react";
import { PageHeader } from "@/components/shared/page-header";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

type TipoEvento = "NASCIMENTO" | "MORTE" | "PESAGEM" | "VACINACAO" | "TRANSFERENCIA" | "CASTRACAO";

const EVENTO_CONFIG: Record<TipoEvento, { label: string; color: string; icon: React.ReactNode }> = {
    NASCIMENTO: { label: "Nascimento", color: "text-green-600 bg-green-500/10 border-green-200", icon: <Baby size={14} /> },
    MORTE: { label: "Morte", color: "text-red-600 bg-red-500/10 border-red-200", icon: <HeartPulse size={14} /> },
    PESAGEM: { label: "Pesagem", color: "text-blue-600 bg-blue-500/10 border-blue-200", icon: <Scale size={14} /> },
    VACINACAO: { label: "Vacinação", color: "text-purple-600 bg-purple-500/10 border-purple-200", icon: <Syringe size={14} /> },
    TRANSFERENCIA: { label: "Transferência", color: "text-orange-600 bg-orange-500/10 border-orange-200", icon: <ArrowRightLeft size={14} /> },
    CASTRACAO: { label: "Castração", color: "text-pink-600 bg-pink-500/10 border-pink-200", icon: <Scissors size={14} /> },
};

interface RegistrarEventoPayload {
    lote_id: string;
    tipo_evento: TipoEvento;
    data_evento: string;
    quantidade_cabecas?: number;
    peso_total_kg?: number;
    observacoes?: string;
}

function RegistrarEventoModal({ lotes, onClose }: { lotes: any[]; onClose: () => void }) {
    const queryClient = useQueryClient();
    const [form, setForm] = useState<{
        lote_id: string;
        tipo_evento: TipoEvento | "";
        data_evento: string;
        quantidade_cabecas: string;
        peso_total_kg: string;
        observacoes: string;
    }>({
        lote_id: "",
        tipo_evento: "",
        data_evento: new Date().toISOString().split("T")[0],
        quantidade_cabecas: "",
        peso_total_kg: "",
        observacoes: "",
    });

    const mutation = useMutation({
        mutationFn: (payload: RegistrarEventoPayload) =>
            apiFetch("/pecuaria/manejos/", { method: "POST", body: JSON.stringify(payload) }),
        onSuccess: () => {
            toast.success("Evento registrado com sucesso!");
            queryClient.invalidateQueries({ queryKey: ["manejos"] });
            onClose();
        },
        onError: (err: Error) => toast.error(err.message || "Erro ao registrar evento."),
    });

    const tipo = form.tipo_evento as TipoEvento | "";
    const needsQtd = tipo === "NASCIMENTO" || tipo === "MORTE";
    const needsPeso = tipo === "PESAGEM";

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (!form.lote_id) return toast.error("Selecione um lote.");
        if (!form.tipo_evento) return toast.error("Selecione o tipo de evento.");

        const payload: RegistrarEventoPayload = {
            lote_id: form.lote_id,
            tipo_evento: form.tipo_evento as TipoEvento,
            data_evento: form.data_evento,
            observacoes: form.observacoes || undefined,
        };
        if (form.quantidade_cabecas) payload.quantidade_cabecas = Number(form.quantidade_cabecas);
        if (form.peso_total_kg) payload.peso_total_kg = Number(form.peso_total_kg);

        mutation.mutate(payload);
    };

    const inputClass =
        "w-full rounded-sm border border-border-subtle bg-transparent px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition-all placeholder:text-foreground/30";

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-in fade-in duration-200">
            <div className="bg-surface w-full max-w-lg rounded-sm shadow-2xl border border-border-subtle animate-in fade-in duration-200">
                {/* Header */}
                <div className="flex items-center justify-between px-6 py-5 border-b border-border-subtle">
                    <div className="flex items-center gap-3">
                        <div className="h-9 w-9 rounded-sm bg-primary/10 flex items-center justify-center">
                            <Activity size={18} className="text-primary" />
                        </div>
                        <div>
                            <h2 className="font-bold text-foreground text-[15px]">Registrar Evento de Manejo</h2>
                            <p className="text-xs text-foreground/50">Nascimento, pesagem, morte, vacinação...</p>
                        </div>
                    </div>
                    <button onClick={onClose} className="h-8 w-8 rounded-sm hover:bg-neutral-100 dark:hover:bg-white/10 flex items-center justify-center transition-colors">
                        <X size={16} className="text-foreground/60" />
                    </button>
                </div>

                <form onSubmit={handleSubmit} className="p-6 space-y-4">
                    {/* Tipo de Evento - cards visuais */}
                    <div>
                        <label className="text-xs font-semibold text-foreground/70 uppercase tracking-wider mb-2 block">
                            Tipo de Evento <span className="text-red-500">*</span>
                        </label>
                        <div className="grid grid-cols-5 gap-2">
                            {(Object.entries(EVENTO_CONFIG) as [TipoEvento, typeof EVENTO_CONFIG[TipoEvento]][]).map(([key, cfg]) => (
                                <button
                                    key={key}
                                    type="button"
                                    onClick={() => setForm(f => ({ ...f, tipo_evento: key }))}
                                    className={`flex flex-col items-center gap-1.5 p-3 rounded-sm border text-center transition-all
                                        ${form.tipo_evento === key
                                            ? `${cfg.color} border-current shadow-sm scale-[1.02]`
                                            : "border-border-subtle hover:bg-neutral-50 dark:hover:bg-white/5 text-foreground/60"
                                        }`}
                                >
                                    <div className={form.tipo_evento === key ? "" : "opacity-50"}>{cfg.icon}</div>
                                    <span className="text-[10px] font-bold leading-tight">{cfg.label}</span>
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Lote */}
                    <div className="flex flex-col gap-1.5">
                        <label className="text-xs font-semibold text-foreground/70 uppercase tracking-wider">
                            Lote <span className="text-red-500">*</span>
                        </label>
                        <select
                            required
                            className={inputClass}
                            value={form.lote_id}
                            onChange={e => setForm(f => ({ ...f, lote_id: e.target.value }))}
                        >
                            <option value="">Selecione o lote...</option>
                            {lotes.map((l: any) => (
                                <option key={l.id} value={l.id}>{l.identificacao} — {l.categoria}</option>
                            ))}
                        </select>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        {/* Data */}
                        <div className="flex flex-col gap-1.5">
                            <label className="text-xs font-semibold text-foreground/70 uppercase tracking-wider">Data</label>
                            <div className="relative">
                                <Calendar size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-foreground/40" />
                                <Input
                                    type="date"
                                    className={`${inputClass} pl-9`}
                                    value={form.data_evento}
                                    onChange={e => setForm(f => ({ ...f, data_evento: e.target.value }))}
                                />
                            </div>
                        </div>

                        {/* Qtd ou Peso conforme o tipo */}
                        {(needsQtd || needsPeso || (!needsQtd && !needsPeso && tipo !== "")) && (
                            <div className="flex flex-col gap-1.5">
                                <label className="text-xs font-semibold text-foreground/70 uppercase tracking-wider">
                                    {needsPeso ? "Peso Total (kg)" : "Qtd. Cabeças"}
                                </label>
                                <Input
                                    type="number"
                                    min={0}
                                    step={needsPeso ? 0.1 : 1}
                                    placeholder={needsPeso ? "Ex: 4520.5" : "Ex: 3"}
                                    className={inputClass}
                                    value={needsPeso ? form.peso_total_kg : form.quantidade_cabecas}
                                    onChange={e => setForm(f => needsPeso
                                        ? { ...f, peso_total_kg: e.target.value }
                                        : { ...f, quantidade_cabecas: e.target.value }
                                    )}
                                />
                            </div>
                        )}
                    </div>

                    {/* Observações */}
                    <div className="flex flex-col gap-1.5">
                        <label className="text-xs font-semibold text-foreground/70 uppercase tracking-wider">
                            Observações
                        </label>
                        <div className="relative">
                            <FileText size={14} className="absolute left-3 top-3 text-foreground/40" />
                            <textarea
                                rows={2}
                                placeholder="Produto aplicado, lote destino, veterinário..."
                                className={`${inputClass} pl-9 resize-none`}
                                value={form.observacoes}
                                onChange={e => setForm(f => ({ ...f, observacoes: e.target.value }))}
                            />
                        </div>
                    </div>

                    {/* Actions */}
                    <div className="flex justify-end gap-3 pt-2">
                        <button
                            type="button"
                            onClick={onClose}
                            className="px-4 py-2 rounded-sm text-sm font-medium text-foreground/70 hover:bg-neutral-100 dark:hover:bg-white/10 transition-colors"
                        >
                            Cancelar
                        </button>
                        <button
                            type="submit"
                            disabled={mutation.isPending}
                            className="flex items-center gap-2 px-5 py-2 rounded-sm bg-primary text-white text-sm font-semibold hover:brightness-110 active:scale-95 transition-all disabled:opacity-60 disabled:cursor-not-allowed shadow-[0_2px_8px_0_rgba(115,103,240,0.4)]"
                        >
                            {mutation.isPending ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />}
                            {mutation.isPending ? "Salvando..." : "Registrar Evento"}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}

export default function ManejoPage() {
    const [showModal, setShowModal] = useState(false);

    const { data: manejos = [], isLoading } = useQuery({
        queryKey: ["manejos"],
        queryFn: () => apiFetch<any[]>("/pecuaria/manejos/"),
    });

    const { data: lotes = [] } = useQuery({
        queryKey: ["lotes"],
        queryFn: () => apiFetch<any[]>("/pecuaria/lotes"),
    });

    const countByTipo = (tipo: string) => manejos.filter((m: any) => m.tipo_evento === tipo).length;

    return (
        <div className="p-6 space-y-6 animate-in fade-in duration-700">
            <PageHeader
                title="Manejo do Rebanho"
                description="Registro de eventos: nascimentos, pesagens, vacinações e transferências."
                icon={<Syringe className="text-primary" size={22} />}
                breadcrumbs={[
                    { label: "Pecuária", href: "#" },
                    { label: "Manejo" }
                ]}
                actions={
                    <Button
                        variant="outline"
                        size="sm"
                        className="rounded-sm"
                        onClick={() => setShowModal(true)}
                    >
                        <Plus className="size-3.5 mr-1.5" /> Registrar Evento
                    </Button>
                }
            />

            {/* KPI Cards por tipo */}
            <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                {(Object.entries(EVENTO_CONFIG) as [TipoEvento, typeof EVENTO_CONFIG[TipoEvento]][]).map(([tipo, cfg]) => (
                    <Card key={tipo}>
                        <CardContent className="pt-5 pb-4">
                            <div className="flex items-start justify-between gap-2">
                                <div>
                                    <div className="text-2xl font-bold leading-none">{countByTipo(tipo)}</div>
                                    <div className="text-xs text-muted-foreground mt-1.5 leading-tight">{cfg.label}</div>
                                </div>
                                <div className={`p-2 rounded-sm border ${cfg.color}`}>
                                    {cfg.icon}
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                ))}
            </div>

            {/* Timeline */}
            <Card className="shadow-sm">
                <CardHeader className="border-b border-border-subtle pb-4">
                    <CardTitle className="text-sm font-bold uppercase tracking-widest text-muted-foreground flex items-center gap-2">
                        <Calendar size={14} /> Timeline de Eventos
                    </CardTitle>
                </CardHeader>
                <CardContent className="p-0">
                    {isLoading ? (
                        <div className="p-8 text-center text-muted-foreground text-sm">Carregando eventos...</div>
                    ) : manejos.length === 0 ? (
                        <div className="p-12 text-center">
                            <Activity size={40} className="mx-auto text-muted-foreground/20 mb-4" />
                            <p className="font-black text-xl text-muted-foreground">Nenhum evento registrado</p>
                            <p className="text-sm text-muted-foreground/60 mt-1">Registre nascimentos, pesagens, vacinações e outros eventos do rebanho.</p>
                            <button
                                onClick={() => setShowModal(true)}
                                className="mt-4 text-sm text-primary hover:underline font-semibold"
                            >
                                + Registrar primeiro evento
                            </button>
                        </div>
                    ) : (
                        <div className="divide-y divide-border-subtle">
                            {manejos.map((m: any) => {
                                const cfg = EVENTO_CONFIG[m.tipo_evento as TipoEvento] ?? {
                                    label: m.tipo_evento,
                                    color: "text-gray-600 bg-gray-100 border-gray-200",
                                    icon: <Activity size={14} />,
                                };
                                return (
                                    <div key={m.id} className="flex items-center gap-4 px-6 py-4 hover:bg-primary/5 transition-colors group cursor-pointer">
                                        <div className={`h-9 w-9 rounded-sm flex items-center justify-center border shrink-0 ${cfg.color}`}>
                                            <div>{cfg.icon}</div>
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <p className="font-bold text-sm">{cfg.label}</p>
                                            <p className="text-xs text-muted-foreground truncate">{m.observacoes || "Sem observações"}</p>
                                        </div>
                                        <div className="text-right shrink-0">
                                            {m.quantidade_cabecas != null && (
                                                <p className="text-sm font-black">{m.quantidade_cabecas} <span className="text-xs font-normal opacity-50">cab.</span></p>
                                            )}
                                            {m.peso_total_kg != null && (
                                                <p className="text-sm font-black">{m.peso_total_kg} <span className="text-xs font-normal opacity-50">kg</span></p>
                                            )}
                                            <p className="text-[10px] text-muted-foreground mt-0.5">
                                                {m.data_evento ? format(new Date(m.data_evento), "dd MMM yyyy", { locale: ptBR }) : "—"}
                                            </p>
                                        </div>
                                        <ChevronRight size={14} className="text-muted-foreground/30 group-hover:text-primary transition-colors shrink-0" />
                                    </div>
                                );
                            })}
                        </div>
                    )}
                </CardContent>
            </Card>

            {showModal && (
                <RegistrarEventoModal lotes={lotes} onClose={() => setShowModal(false)} />
            )}
        </div>
    );
}
