"use client";

import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { toast } from "sonner";
import {
    Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
    User, Building2, CreditCard, Tractor, CheckCircle2, Plus, Trash2,
    Copy, AlertTriangle, Briefcase,
} from "lucide-react";
import { cn } from "@/lib/utils";

// ── tipos ─────────────────────────────────────────────────────────────────────

interface Lead {
    id: string;
    nome: string;
    email: string | null;
    telefone: string | null;
    empresa: string | null;
    documento: string | null;
    plano_interesse: string | null;
    qtd_fazendas: number | null;
    qtd_usuarios: number | null;
}

interface Plano {
    id: string;
    nome: string;
    descricao: string | null;
    preco_mensal: number;
    preco_anual: number;
    modulos_inclusos: string[];
    disponivel_crm: boolean;
    ativo: boolean;
}

interface ConvertLeadResponse {
    tenant_id: string;
    assinatura_id: string;
    activation_token: string;
    activation_expires_at: string;
    message: string;
}

interface Props {
    lead: Lead | null;
    open: boolean;
    onOpenChange: (v: boolean) => void;
    onSuccess: () => void;
}

// ── helpers ───────────────────────────────────────────────────────────────────

function maskDoc(v: string): string {
    const d = v.replace(/\D/g, "").slice(0, 14);
    if (d.length <= 11)
        return d.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, "$1.$2.$3-$4")
                .replace(/(\d{3})(\d{3})(\d{0,3})/, "$1.$2.$3")
                .replace(/(\d{3})(\d{0,3})/, "$1.$2")
                .replace(/^(\d{0,3})/, "$1");
    return d.replace(/(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})/, "$1.$2.$3/$4-$5")
            .replace(/(\d{2})(\d{3})(\d{3})(\d{0,4})/, "$1.$2.$3/$4")
            .replace(/(\d{2})(\d{3})(\d{0,3})/, "$1.$2.$3")
            .replace(/(\d{2})(\d{0,3})/, "$1.$2")
            .replace(/^(\d{0,2})/, "$1");
}

function formatCurrency(v: number) {
    return v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

const STEPS = [
    { id: 1, label: "Assinante", icon: User },
    { id: 2, label: "Plano", icon: CreditCard },
    { id: 3, label: "Fazendas", icon: Tractor },
];

// ── componente principal ──────────────────────────────────────────────────────

export function ConvertLeadWizard({ lead, open, onOpenChange, onSuccess }: Props) {
    const queryClient = useQueryClient();
    const [step, setStep] = useState(1);
    const [result, setResult] = useState<ConvertLeadResponse | null>(null);

    // Step 1 — dados do assinante
    const [nomeTenant, setNomeTenant] = useState("");
    const [documento, setDocumento] = useState("");
    const [emailResponsavel, setEmailResponsavel] = useState("");
    const [nomeCompleto, setNomeCompleto] = useState("");
    const [telefone, setTelefone] = useState("");

    // Step 2 — plano
    const [planoId, setPlanoId] = useState("");
    const [ciclo, setCiclo] = useState("MENSAL");
    const [usuarios, setUsuarios] = useState(5);

    // Step 3 — fazendas
    const [fazendas, setFazendas] = useState([{ nome: "" }]);

    // Buscar planos disponíveis no CRM
    const { data: planos } = useQuery<Plano[]>({
        queryKey: ["backoffice", "plans"],
        queryFn: () => apiFetch("/backoffice/plans"),
        enabled: open,
        select: (data) => data.filter((p) => p.ativo && p.disponivel_crm),
    });

    useEffect(() => {
        if (lead && open && !result) {
            setStep(1);
            setNomeTenant(lead.empresa || lead.nome || "");
            setDocumento(lead.documento || "");
            setEmailResponsavel(lead.email || "");
            setNomeCompleto(lead.nome || "");
            setTelefone(lead.telefone || "");
            setUsuarios(lead.qtd_usuarios || 5);
            setFazendas(
                lead.qtd_fazendas && lead.qtd_fazendas > 1
                    ? Array.from({ length: lead.qtd_fazendas }, () => ({ nome: "" }))
                    : [{ nome: "" }]
            );

            // Tentar pré-selecionar o plano baseado no interesse do lead
            // Se plano_interesse for um nome (como salvo no CRMPage), tentamos achar o ID
            if (lead.plano_interesse && planos) {
                const matchingPlan = planos.find(
                    p => p.id === lead.plano_interesse || p.nome === lead.plano_interesse
                );
                if (matchingPlan) {
                    setPlanoId(matchingPlan.id);
                }
            }
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [lead, open, planos]);

    const planoSelecionado = planos?.find((p) => p.id === planoId);

    const mutation = useMutation({
        mutationFn: (payload: object) =>
            apiFetch<ConvertLeadResponse>(`/backoffice/tenants/leads/${lead!.id}/converter`, {
                method: "POST",
                body: JSON.stringify(payload),
            }),
        onSuccess: (data: ConvertLeadResponse) => {
            setResult(data);
            queryClient.invalidateQueries({ queryKey: ["crm"] });
            onSuccess();
        },
        onError: (err: any) => toast.error(err.message || "Erro ao converter lead"),
    });

    function handleSubmit() {
        const fazendasValidas = fazendas.filter((f) => f.nome.trim());
        if (!fazendasValidas.length) {
            toast.error("Informe pelo menos uma fazenda.");
            return;
        }
        mutation.mutate({
            nome_tenant: nomeTenant,
            documento: documento.replace(/\D/g, ""),
            email_responsavel: emailResponsavel,
            nome_completo: nomeCompleto,
            telefone_responsavel: telefone || undefined,
            plano_id: planoId,
            ciclo_pagamento: ciclo,
            usuarios_contratados: usuarios,
            fazendas: fazendasValidas,
        });
    }

    function addFazenda() {
        setFazendas((prev) => [...prev, { nome: "" }]);
    }

    function removeFazenda(i: number) {
        setFazendas((prev) => prev.filter((_, idx) => idx !== i));
    }

    function updateFazenda(i: number, nome: string) {
        setFazendas((prev) => prev.map((f, idx) => (idx === i ? { nome } : f)));
    }

    function canNext() {
        if (step === 1) return nomeTenant.trim() && documento.trim() && emailResponsavel.trim() && nomeCompleto.trim();
        if (step === 2) return !!planoId;
        return true;
    }

    // ── tela de sucesso ───────────────────────────────────────────────────────
    if (result) {
        return (
            <Dialog open={open} onOpenChange={onOpenChange}>
                <DialogContent className="sm:max-w-md">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2 text-green-600">
                            <CheckCircle2 className="size-5" /> Conversão realizada!
                        </DialogTitle>
                    </DialogHeader>
                    <div className="space-y-4 py-2">
                        <p className="text-sm text-muted-foreground">{result.message}</p>
                        <div className="rounded-sm border bg-muted/40 p-3 space-y-2">
                            <p className="text-xs font-semibold uppercase text-muted-foreground">Link de ativação</p>
                            <div className="flex items-center gap-2">
                                <code className="flex-1 text-xs break-all font-mono bg-background border rounded px-2 py-1">
                                    {`${window.location.origin}/onboarding/ativar?token=${result.activation_token}`}
                                </code>
                                <Button
                                    size="icon"
                                    variant="outline"
                                    className="shrink-0"
                                    onClick={() => {
                                        navigator.clipboard.writeText(`${window.location.origin}/onboarding/ativar?token=${result.activation_token}`);
                                        toast.success("Link copiado!");
                                    }}
                                >
                                    <Copy className="size-4" />
                                </Button>
                            </div>
                            <p className="text-xs text-muted-foreground flex items-center gap-1">
                                <AlertTriangle className="size-3" />
                                Expira em 48 h. Envie este link ao assinante para que ele conclua o pagamento.
                            </p>
                        </div>
                    </div>
                    <DialogFooter>
                        <Button onClick={() => onOpenChange(false)}>Fechar</Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        );
    }

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-[620px] flex flex-col p-0 gap-0 overflow-hidden max-h-[90vh]">
                {/* Header */}
                <DialogHeader className="p-6 border-b shrink-0">
                    <DialogTitle className="flex items-center gap-2">
                        <Briefcase className="size-5 text-primary" />
                        Converter Lead em Assinante
                    </DialogTitle>
                    {lead && (
                        <p className="text-sm text-muted-foreground mt-1">
                            {lead.nome}{lead.empresa ? ` · ${lead.empresa}` : ""}
                        </p>
                    )}
                </DialogHeader>

                {/* Steps indicator */}
                <div className="flex items-center px-6 py-3 border-b bg-muted/30 shrink-0 gap-2">
                    {STEPS.map((s, i) => {
                        const Icon = s.icon;
                        const active = step === s.id;
                        const done = step > s.id;
                        return (
                            <div key={s.id} className="flex items-center gap-2">
                                <div className={cn(
                                    "flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-full border transition-colors",
                                    active && "bg-primary text-primary-foreground border-primary",
                                    done && "bg-green-500/10 text-green-600 border-green-200",
                                    !active && !done && "text-muted-foreground border-muted"
                                )}>
                                    <Icon className="size-3" />
                                    {s.label}
                                </div>
                                {i < STEPS.length - 1 && <div className="w-4 h-px bg-border" />}
                            </div>
                        );
                    })}
                </div>

                {/* Content */}
                <ScrollArea className="flex-1">
                    <div className="p-6 space-y-4">

                        {/* Step 1 — Dados do assinante */}
                        {step === 1 && (
                            <>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    <div className="space-y-1.5">
                                        <Label>Razão social / Nome *</Label>
                                        <Input value={nomeTenant} onChange={e => setNomeTenant(e.target.value)} placeholder="Nome da empresa ou produtor" />
                                    </div>
                                    <div className="space-y-1.5">
                                        <Label>CPF / CNPJ *</Label>
                                        <Input value={documento} onChange={e => setDocumento(maskDoc(e.target.value))} placeholder="000.000.000-00" />
                                    </div>
                                </div>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    <div className="space-y-1.5">
                                        <Label>Nome completo do responsável *</Label>
                                        <Input value={nomeCompleto} onChange={e => setNomeCompleto(e.target.value)} placeholder="Nome completo" />
                                    </div>
                                    <div className="space-y-1.5">
                                        <Label>Email de acesso *</Label>
                                        <Input type="email" value={emailResponsavel} onChange={e => setEmailResponsavel(e.target.value)} placeholder="email@empresa.com" />
                                    </div>
                                </div>
                                <div className="space-y-1.5">
                                    <Label>Telefone</Label>
                                    <Input value={telefone} onChange={e => setTelefone(e.target.value)} placeholder="(00) 00000-0000" />
                                </div>
                            </>
                        )}

                        {/* Step 2 — Plano */}
                        {step === 2 && (
                            <>
                                <div className="space-y-1.5">
                                    <Label>Plano *</Label>
                                    <Select value={planoId} onValueChange={setPlanoId}>
                                        <SelectTrigger>
                                            <SelectValue placeholder="Selecione o plano acordado" />
                                        </SelectTrigger>
                                        <SelectContent>
                                            {planos?.map((p) => (
                                                <SelectItem key={p.id} value={p.id}>
                                                    {p.nome} — {formatCurrency(p.preco_mensal)}/mês
                                                </SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                </div>

                                {planoSelecionado && (
                                    <div className="rounded-sm border bg-muted/30 p-3 space-y-2">
                                        <p className="text-xs font-semibold uppercase text-muted-foreground">Módulos inclusos</p>
                                        <div className="flex flex-wrap gap-1.5">
                                            {planoSelecionado.modulos_inclusos.map(m => (
                                                <Badge key={m} variant="secondary" className="text-[10px]">{m}</Badge>
                                            ))}
                                        </div>
                                    </div>
                                )}

                                <div className="grid grid-cols-2 gap-4">
                                    <div className="space-y-1.5">
                                        <Label>Ciclo de cobrança</Label>
                                        <Select value={ciclo} onValueChange={setCiclo}>
                                            <SelectTrigger>
                                                <SelectValue />
                                            </SelectTrigger>
                                            <SelectContent>
                                                <SelectItem value="MENSAL">Mensal</SelectItem>
                                                <SelectItem value="ANUAL">Anual</SelectItem>
                                            </SelectContent>
                                        </Select>
                                    </div>
                                    <div className="space-y-1.5">
                                        <Label>Usuários contratados</Label>
                                        <Input
                                            type="number"
                                            min={1}
                                            value={usuarios}
                                            onChange={e => setUsuarios(Number(e.target.value))}
                                        />
                                    </div>
                                </div>

                                {planoSelecionado && (
                                    <div className="rounded-sm border p-3 space-y-1 bg-primary/5">
                                        <p className="text-xs font-semibold text-muted-foreground uppercase">Resumo financeiro</p>
                                        <p className="text-sm font-medium">
                                            {planoSelecionado.nome} — {ciclo === "MENSAL"
                                                ? formatCurrency(planoSelecionado.preco_mensal) + "/mês"
                                                : formatCurrency(planoSelecionado.preco_anual) + "/ano"}
                                        </p>
                                        <p className="text-xs text-muted-foreground">
                                            Assinatura ativa somente após confirmação do pagamento via Stripe.
                                        </p>
                                    </div>
                                )}
                            </>
                        )}

                        {/* Step 3 — Fazendas */}
                        {step === 3 && (
                            <>
                                <p className="text-sm text-muted-foreground">
                                    Informe o nome de cada propriedade. O assinante poderá adicionar mais fazendas depois.
                                </p>
                                <div className="space-y-2">
                                    {fazendas.map((f, i) => (
                                        <div key={i} className="flex items-center gap-2">
                                            <Tractor className="size-4 text-muted-foreground shrink-0" />
                                            <Input
                                                value={f.nome}
                                                onChange={e => updateFazenda(i, e.target.value)}
                                                placeholder={`Nome da fazenda ${i + 1}`}
                                            />
                                            {fazendas.length > 1 && (
                                                <Button
                                                    variant="ghost"
                                                    size="icon"
                                                    className="shrink-0 text-muted-foreground hover:text-destructive"
                                                    onClick={() => removeFazenda(i)}
                                                >
                                                    <Trash2 className="size-4" />
                                                </Button>
                                            )}
                                        </div>
                                    ))}
                                </div>
                                <Button variant="outline" size="sm" onClick={addFazenda} className="gap-2">
                                    <Plus className="size-3.5" /> Adicionar fazenda
                                </Button>
                            </>
                        )}
                    </div>
                </ScrollArea>

                {/* Footer */}
                <DialogFooter className="p-6 border-t shrink-0 flex justify-between">
                    <Button
                        variant="outline"
                        onClick={() => step > 1 ? setStep(s => s - 1) : onOpenChange(false)}
                    >
                        {step > 1 ? "Voltar" : "Cancelar"}
                    </Button>
                    {step < 3 ? (
                        <Button disabled={!canNext()} onClick={() => setStep(s => s + 1)}>
                            Próximo
                        </Button>
                    ) : (
                        <Button
                            disabled={mutation.isPending}
                            onClick={handleSubmit}
                            className="gap-2"
                        >
                            <CheckCircle2 className="size-4" />
                            {mutation.isPending ? "Convertendo..." : "Confirmar conversão"}
                        </Button>
                    )}
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
