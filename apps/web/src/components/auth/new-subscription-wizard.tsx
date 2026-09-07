"use client";

import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { useAppStore } from "@/lib/stores/app-store";
import { apiFetch } from "@/lib/api";
import { extractTenantContextsFromToken } from "@/lib/jwt";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Card, CardContent } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { Building2, Check, ChevronLeft, ChevronRight, CreditCard, Loader2, Sparkles, Star } from "lucide-react";
import { toast } from "sonner";
import { setAuthCookies } from "@/app/actions/auth";
import { cn } from "@/lib/utils";

interface Plano {
    id: string;
    nome: string;
    descricao: string | null;
    preco_mensal: number;
    preco_anual: number;
    plan_tier: string;
    is_free: boolean;
    tem_trial: boolean;
    dias_trial: number;
    destaque: boolean;
    modulos_inclusos: string[];
    descricao_marketing: string | null;
}

interface AuthProfileResponse {
    tenants: Array<{
        tenant_id: string;
        nome_tenant: string;
        is_owner: boolean;
        perfil?: {
            nome: string;
        } | null;
        fazendas: Array<{
            unidade_produtiva_id: string;
            nome: string;
        }>;
    }>;
}

interface Props {
    open: boolean;
    onOpenChange: (open: boolean) => void;
}

const steps = [
    { id: 1, label: "Produtor" },
    { id: 2, label: "Plano" },
    { id: 3, label: "Confirmar" },
] as const;

const actionButtonClass = "rounded-sm font-medium";

export function NewSubscriptionWizard({ open, onOpenChange }: Props) {
    const { setSession, user } = useAppStore();
    const [step, setStep] = useState(1);
    const [nome, setNome] = useState("");
    const [cpfCnpj, setCpfCnpj] = useState("");
    const [planoSelecionado, setPlanoSelecionado] = useState<Plano | null>(null);
    const [ciclo, setCiclo] = useState<"MENSAL" | "ANUAL">("MENSAL");

    const { data: planos = [], isLoading: loadingPlanos } = useQuery<Plano[]>({
        queryKey: ["billing-plans"],
        queryFn: () => apiFetch("/billing/plans"),
        enabled: open && step === 2,
        staleTime: 300_000,
    });

    const mutation = useMutation({
        mutationFn: () =>
            apiFetch<{
                access_token: string;
                tenant_id: string;
                nome_tenant: string;
                is_trial: boolean;
                trial_expira_em: string | null;
                data_primeiro_vencimento: string | null;
            }>("/auth/create-subscription", {
                method: "POST",
                body: JSON.stringify({
                    nome,
                    cpf_cnpj: cpfCnpj || undefined,
                    plano_id: planoSelecionado!.id,
                    ciclo,
                }),
            }),
        onSuccess: (data) => {
            const grupos = extractTenantContextsFromToken(data.access_token);
            const store = useAppStore.getState();
            const novoTenant = {
                id: data.tenant_id,
                nome: data.nome_tenant,
                documento: cpfCnpj || "",
                slug: "",
                dominio_customizado: null,
                branding: { primaryColor: "15 64% 60%" },
            };
            // Adicionar novo tenant à lista e fazer switch
            const novoTenantEntry: AuthProfileResponse["tenants"][number] = {
                tenant_id: data.tenant_id,
                nome_tenant: data.nome_tenant,
                is_owner: true,
                perfil: { nome: "Owner" },
                fazendas: [],
            };
            const tenantsAtualizados = [...store.availableTenants, novoTenantEntry];
            void setAuthCookies(data.access_token, data.tenant_id);
            setSession(data.access_token, novoTenant, user, grupos, [], tenantsAtualizados);
            toast.success(`Conta "${data.nome_tenant}" criada com sucesso!`);
            onOpenChange(false);
            window.location.href = "/dashboard";
        },
        onError: (err: unknown) => {
            toast.error(err instanceof Error ? err.message : "Erro ao criar assinatura. Tente novamente.");
        },
    });

    const resetar = () => {
        setStep(1);
        setNome("");
        setCpfCnpj("");
        setPlanoSelecionado(null);
        setCiclo("MENSAL");
    };

    const handleClose = (open: boolean) => {
        if (!open) resetar();
        onOpenChange(open);
    };

    const precoExibido = (plano: Plano) =>
        ciclo === "ANUAL" ? plano.preco_anual / 12 : plano.preco_mensal;

    const stepTitle = step === 1 ? "Nova Conta de Produtor" : step === 2 ? "Selecionar Plano" : "Confirmar nova conta";
    const stepDescription =
        step === 1
            ? "Informe o nome do produtor, empresa ou grupo rural que será criado como uma nova conta."
            : step === 2
                ? "Escolha o plano e o ciclo de cobrança para esta nova conta de produtor."
                : "Revise os dados antes de criar a conta e alternar para o novo contexto.";
    const progressValue = ((step - 1) / (steps.length - 1)) * 100;

    return (
        <Dialog open={open} onOpenChange={handleClose}>
            <DialogContent className="w-[calc(100vw-2rem)] gap-0 overflow-hidden rounded-sm p-0 sm:max-w-[520px]">
                <DialogHeader className="border-b bg-muted/30 px-5 py-4">
                    <div className="flex items-start gap-3">
                        <div className="flex size-9 shrink-0 items-center justify-center rounded-sm bg-primary/10 text-primary">
                            {step === 1 ? <Building2 /> : step === 2 ? <CreditCard /> : <Check />}
                        </div>
                        <div className="min-w-0">
                            <DialogTitle className="text-base leading-tight">{stepTitle}</DialogTitle>
                            <DialogDescription className="mt-1 text-xs leading-relaxed">
                                {stepDescription}
                            </DialogDescription>
                        </div>
                    </div>
                </DialogHeader>

                <div className="border-b px-5 py-3">
                    <div className="flex items-center justify-between gap-3">
                        <div>
                            <p className="text-xs font-medium text-foreground">Etapa {step} de {steps.length}</p>
                            <p className="text-[11px] text-muted-foreground">{steps[step - 1]?.label}</p>
                        </div>
                        <Badge variant="secondary" className="h-5 text-[10px]">
                            {Math.round(progressValue)}%
                        </Badge>
                    </div>
                    <Progress value={progressValue} className="mt-3 !h-1" />
                    <div className="mt-2 flex items-center justify-between text-[10px] text-muted-foreground">
                        {steps.map((s) => (
                            <span
                                key={s.id}
                                className={cn(
                                    "font-medium",
                                    s.id === step && "text-primary",
                                    s.id < step && "text-foreground"
                                )}
                            >
                                {s.label}
                            </span>
                        ))}
                    </div>
                </div>

                <div className="max-h-[58vh] overflow-y-auto px-5 py-4">
                    {/* Step 1 — Dados do Produtor */}
                    {step === 1 && (
                        <div className="grid gap-4">
                            <Alert className="rounded-sm">
                                <Sparkles />
                                <AlertTitle>Nova conta separada</AlertTitle>
                                <AlertDescription className="text-xs text-muted-foreground">
                                    Use quando precisar operar uma nova empresa, produtor ou grupo rural separado do contexto atual.
                                </AlertDescription>
                            </Alert>

                            <div className="grid gap-4">
                                <div className="grid gap-1.5">
                                    <Label htmlFor="nome-produtor">Nome do Produtor / Empresa <span className="text-destructive">*</span></Label>
                                    <Input
                                        id="nome-produtor"
                                        placeholder="Ex: João da Silva ou Fazenda São José Ltda"
                                        value={nome}
                                        onChange={(e) => setNome(e.target.value)}
                                        autoFocus
                                        className="h-8 rounded-sm"
                                    />
                                    <p className="text-[11px] text-muted-foreground">
                                        Esse nome aparecerá no seletor de produtor/conta no topo do sistema.
                                    </p>
                                </div>

                                <div className="grid gap-1.5">
                                    <Label htmlFor="cpf-cnpj-produtor" className="flex items-center gap-2">
                                        CPF / CNPJ
                                        <Badge variant="secondary" className="h-5 text-[10px]">Opcional</Badge>
                                    </Label>
                                    <Input
                                        id="cpf-cnpj-produtor"
                                        placeholder="000.000.000-00 ou 00.000.000/0000-00"
                                        value={cpfCnpj}
                                        onChange={(e) => setCpfCnpj(e.target.value)}
                                        className="h-8 rounded-sm"
                                    />
                                    <p className="text-[11px] text-muted-foreground">
                                        Pode ser preenchido depois em <code>Configurações &gt; Meu Produtor</code>.
                                    </p>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Step 2 — Seleção de Plano */}
                    {step === 2 && (
                        <div className="grid gap-4">
                            <div className="flex flex-col gap-3 rounded-sm border bg-muted/20 p-3 sm:flex-row sm:items-center sm:justify-between">
                                <div>
                                    <p className="text-sm font-semibold">Ciclo de cobrança</p>
                                    <p className="text-xs text-muted-foreground">O ciclo anual aplica desconto quando disponível.</p>
                                </div>
                                <ToggleGroup
                                    type="single"
                                    value={ciclo}
                                    onValueChange={(value) => {
                                        if (value === "MENSAL" || value === "ANUAL") setCiclo(value);
                                    }}
                                    className="rounded-sm bg-background p-1"
                                >
                                    <ToggleGroupItem value="MENSAL" className="h-7 text-xs font-semibold">Mensal</ToggleGroupItem>
                                    <ToggleGroupItem value="ANUAL" className="h-7 text-xs font-semibold">Anual -20%</ToggleGroupItem>
                                </ToggleGroup>
                            </div>

                            {loadingPlanos ? (
                                <div className="flex items-center justify-center gap-2 rounded-sm border py-10 text-sm text-muted-foreground">
                                    <Loader2 className="size-4 animate-spin" />
                                    Carregando planos...
                                </div>
                            ) : (
                                <div className="grid gap-3">
                                    {planos.map((plano) => {
                                        const selected = planoSelecionado?.id === plano.id;
                                        return (
                                            <button
                                                key={plano.id}
                                                type="button"
                                                onClick={() => setPlanoSelecionado(plano)}
                                                className={cn(
                                                    "w-full rounded-sm border bg-background p-3 text-left transition-colors hover:border-primary/50 hover:bg-primary/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                                                    selected && "border-primary bg-primary/5"
                                                )}
                                            >
                                                <div className="flex items-start justify-between gap-4">
                                                    <div className="min-w-0 flex-1">
                                                        <div className="flex flex-wrap items-center gap-2">
                                                            <span className="text-sm font-semibold">{plano.nome}</span>
                                                            {plano.destaque && <Star className="size-3.5 fill-amber-500 text-amber-500" />}
                                                            {plano.is_free && <Badge variant="secondary" className="h-5 text-[10px]">Grátis</Badge>}
                                                            {!plano.is_free && plano.tem_trial && (
                                                                <Badge className="h-5 text-[10px]">{plano.dias_trial}d grátis</Badge>
                                                            )}
                                                        </div>
                                                        {plano.descricao_marketing && (
                                                            <p className="mt-1 line-clamp-2 text-xs leading-relaxed text-muted-foreground">
                                                                {plano.descricao_marketing}
                                                            </p>
                                                        )}
                                                    </div>
                                                    <div className="shrink-0 text-right">
                                                        {plano.is_free ? (
                                                            <span className="text-sm font-bold text-primary">R$ 0</span>
                                                        ) : (
                                                            <div>
                                                                <span className="text-sm font-bold">
                                                                    R$ {precoExibido(plano).toFixed(2).replace(".", ",")}
                                                                </span>
                                                                <span className="text-[10px] text-muted-foreground">/mês</span>
                                                            </div>
                                                        )}
                                                        {selected && (
                                                            <div className="mt-2 inline-flex items-center gap-1 text-[10px] font-semibold text-primary">
                                                                <Check className="size-3" />
                                                                Selecionado
                                                            </div>
                                                        )}
                                                    </div>
                                                </div>
                                            </button>
                                        );
                                    })}
                                </div>
                            )}
                        </div>
                    )}

                    {/* Step 3 — Confirmação */}
                    {step === 3 && planoSelecionado && (
                        <div className="grid gap-5">
                            <Card className="shadow-none">
                                <CardContent className="grid gap-3 p-4">
                                    <div className="flex items-center justify-between gap-4 text-sm">
                                        <span className="text-muted-foreground">Produtor</span>
                                        <span className="text-right font-medium">{nome}</span>
                                    </div>
                                    <Separator />
                                    <div className="flex items-center justify-between gap-4 text-sm">
                                        <span className="text-muted-foreground">Plano</span>
                                        <span className="text-right font-medium">{planoSelecionado.nome}</span>
                                    </div>
                                    <div className="flex items-center justify-between gap-4 text-sm">
                                        <span className="text-muted-foreground">Ciclo</span>
                                        <span className="text-right font-medium">{ciclo === "MENSAL" ? "Mensal" : "Anual"}</span>
                                    </div>
                                    <Separator />
                                    {planoSelecionado.is_free ? (
                                        <div className="flex items-center justify-between gap-4 text-sm font-semibold text-primary">
                                            <span>Total</span>
                                            <span>Gratuito</span>
                                        </div>
                                    ) : (
                                        <>
                                            <div className="flex items-center justify-between gap-4 text-sm text-primary">
                                                <span>Trial</span>
                                                <span>{planoSelecionado.dias_trial} dias grátis</span>
                                            </div>
                                            <div className="flex items-center justify-between gap-4 text-sm">
                                                <span className="text-muted-foreground">1º vencimento</span>
                                                <span className="font-medium">Após o trial</span>
                                            </div>
                                        </>
                                    )}
                                </CardContent>
                            </Card>

                            <div className="rounded-sm border border-primary/15 bg-primary/5 px-4 py-3 text-xs leading-relaxed text-muted-foreground">
                                Ao confirmar, a nova conta será criada e o sistema trocará automaticamente para esse produtor.
                            </div>
                        </div>
                    )}
                </div>

                <DialogFooter className="border-t bg-background px-5 py-3">
                    <div className="flex w-full flex-col-reverse gap-2 sm:flex-row sm:justify-between">
                        <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            className={actionButtonClass}
                            onClick={() => step === 1 ? handleClose(false) : setStep((current) => current - 1)}
                            disabled={mutation.isPending}
                        >
                            {step === 1 ? "Cancelar" : (
                                <>
                                    <ChevronLeft data-icon="inline-start" />
                                    Voltar
                                </>
                            )}
                        </Button>

                        {step < 3 ? (
                            <Button
                                type="button"
                                variant="default"
                                size="sm"
                                className={actionButtonClass}
                                onClick={() => setStep((current) => current + 1)}
                                disabled={step === 1 ? !nome.trim() : !planoSelecionado}
                            >
                                Próximo
                                <ChevronRight data-icon="inline-end" />
                            </Button>
                        ) : (
                            <Button
                                type="button"
                                variant="default"
                                size="sm"
                                className={actionButtonClass}
                                onClick={() => mutation.mutate()}
                                disabled={mutation.isPending}
                            >
                                {mutation.isPending ? (
                                    <>
                                        <Loader2 data-icon="inline-start" className="animate-spin" />
                                        Criando...
                                    </>
                                ) : (
                                    "Criar e acessar"
                                )}
                            </Button>
                        )}
                    </div>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
