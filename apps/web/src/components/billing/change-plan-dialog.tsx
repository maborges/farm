"use client";

import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Loader2, Check, ArrowUpRight, ArrowDownRight, AlertCircle, Users, Tractor, ExternalLink, XCircle } from "lucide-react";
import { toast } from "sonner";
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogDescription,
    DialogFooter,
} from "@/components/ui/dialog";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { apiFetch } from "@/lib/api";
import { formatCurrency } from "@/lib/utils";

interface Plano {
    id: string;
    nome: string;
    descricao: string | null;
    preco_mensal: number;
    preco_anual: number;
    limite_usuarios_minimo?: number;
    limite_usuarios_maximo?: number | null;
    limite_hectares?: number | null;
    plan_tier?: string;
    modulos_inclusos: string[];
    destaque?: boolean;
}

interface SimulacaoDetalheFaixa {
    tipo?: string;
    faixa_inicio: number;
    faixa_fim: number | null;
    usuarios_nesta_faixa: number;
    preco_unitario: number;
    valor_faixa: number;
}

interface SimulacaoResponse {
    tipo_mudanca?: string;
    ciclo?: string;
    valor_atual?: number;
    valor_novo?: number;
    valor_atual_mensal?: number;
    valor_novo_mensal?: number;
    diferenca_mensal: number;
    dias_restantes_ciclo?: number;
    valor_proporcional?: number | null;
    detalhes_atual?: SimulacaoDetalheFaixa[];
    detalhes_novo?: SimulacaoDetalheFaixa[];
    requer_pagamento?: boolean;
    mensagem: string;
}

interface SolicitarResponse {
    status?: string;
    url_pagamento?: string | null;
}

interface MudancaPlanoItem {
    id: string;
    tipo_mudanca: string;
    plano_destino_id: string;
    usuarios_destino: number;
    valor_proporcional: number | string;
    status: string;
    url_pagamento?: string | null;
    agendado_para?: string | null;
    created_at: string;
}

interface ListarMudancasPlanoResponse {
    mudancas: MudancaPlanoItem[];
    total: number;
    pagina: number;
    por_pagina: number;
}

const MUDANCA_STATUS_LABELS: Record<string, string> = {
    pendente_pagamento: "aguardando pagamento",
    agendado: "agendada para o próximo ciclo",
    liberado_manualmente: "liberada manualmente (aguardando regularização)",
};

function PendingPlanChangeBanner({
    mudanca,
    planoNome,
    canceling,
    onCancel,
}: {
    mudanca: MudancaPlanoItem;
    planoNome?: string;
    canceling: boolean;
    onCancel: (id: string) => void;
}) {
    const statusLabel = MUDANCA_STATUS_LABELS[mudanca.status] ?? mudanca.status;
    const podeCancelar = mudanca.status === "pendente_pagamento" || mudanca.status === "agendado";

    return (
        <Alert variant="warning">
            <AlertCircle />
            <div className="space-y-2.5 flex-1 text-xs sm:text-sm">
                <div>
                    <AlertTitle className="font-semibold">Existe uma alteração de plano pendente</AlertTitle>
                    <AlertDescription className="mt-1 text-xs sm:text-sm">
                        Solicitação para <strong>{planoNome ?? "outro pacote"}</strong> ({mudanca.usuarios_destino}{" "}
                        acesso(s)) encontra-se {statusLabel}. Conclua ou cancele a solicitação pendente antes de enviar uma nova.
                    </AlertDescription>
                </div>
                {(mudanca.url_pagamento || podeCancelar) && (
                    <div className="flex flex-wrap gap-2">
                        {mudanca.url_pagamento && (
                            <Button
                                type="button"
                                variant="outline"
                                size="sm"
                                className="rounded-sm"
                                onClick={() => window.open(mudanca.url_pagamento!, "_blank", "noopener,noreferrer")}
                            >
                                <ExternalLink className="size-3.5 mr-1.5" />
                                Concluir Pagamento
                            </Button>
                        )}
                        {podeCancelar && (
                            <Button
                                type="button"
                                variant="outline"
                                size="sm"
                                className="rounded-sm text-destructive hover:text-destructive"
                                disabled={canceling}
                                onClick={() => onCancel(mudanca.id)}
                            >
                                {canceling ? (
                                    <Loader2 className="size-3.5 mr-1.5 animate-spin" />
                                ) : (
                                    <XCircle className="size-3.5 mr-1.5" />
                                )}
                                Cancelar solicitação pendente
                            </Button>
                        )}
                    </div>
                )}
            </div>
        </Alert>
    );
}

interface TenantData {
    tenant: {
        id: string;
        nome: string;
        documento: string;
        modulos_ativos: string[];
        max_usuarios: number;
    };
    assinatura: {
        plano: string;
        valor: number;
        status: string;
        data_inicio: string;
        proximo_vencimento: string | null;
        limite_hectares?: number | null;
        usuarios_inclusos?: number;
        usuarios_contratados?: number;
    } | null;
}

interface ChangePlanDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    currentTenant: TenantData | undefined;
}

export function ChangePlanDialog({ open, onOpenChange, currentTenant }: ChangePlanDialogProps) {
    const queryClient = useQueryClient();
    const [planoSelecionado, setPlanoSelecionado] = useState<string | null>(null);
    const [usuariosDestino, setUsuariosDestino] = useState<number>(currentTenant?.tenant.max_usuarios || 1);
    const [simulacaoData, setSimulacaoData] = useState<SimulacaoResponse | null>(null);
    const [ciclo, setCiclo] = useState<"MENSAL" | "ANUAL">("MENSAL");
    const [showConfirm, setShowConfirm] = useState(false);

    useEffect(() => {
        if (currentTenant?.tenant.max_usuarios) {
            setUsuariosDestino(currentTenant.tenant.max_usuarios);
        }
    }, [currentTenant?.tenant.max_usuarios]);

    // Buscar planos disponíveis
    const { data: planos, isLoading } = useQuery<Plano[]>({
        queryKey: ["billing-plans"],
        queryFn: () => apiFetch("/billing/plans"),
        enabled: open
    });

    // Buscar mudanças de plano pendentes para alertar o usuário e permitir cancelamento
    const { data: mudancasData, refetch: refetchMudancas } = useQuery<ListarMudancasPlanoResponse>({
        queryKey: ["billing-mudancas-plano"],
        queryFn: () => apiFetch("/billing/mudancas-plano", { params: { por_pagina: 20 } }),
        enabled: open,
    });

    const isPrePagamento = ["TRIAL", "PENDENTE_PAGAMENTO", "PENDENTE"].includes(
        currentTenant?.assinatura?.status ?? ""
    );

    const mudancaPendente = mudancasData?.mudancas?.find((m) =>
        ["pendente_pagamento", "agendado", "liberado_manualmente"].includes(m.status)
    );

    const cancelarPendenteMutation = useMutation({
        mutationFn: async (mudancaId: string) => {
            await apiFetch(`/billing/mudancas-plano/${mudancaId}`, {
                method: "DELETE",
                body: JSON.stringify({ motivo: "Cancelado pelo usuário para solicitar nova alteração" }),
            });
        },
        onSuccess: () => {
            toast.success("Alteração de plano pendente cancelada com sucesso.");
            queryClient.invalidateQueries({ queryKey: ["billing-mudancas-plano"] });
            queryClient.invalidateQueries({ queryKey: ["tenant-data"] });
        },
        onError: (error: { detail?: string; message?: string }) => {
            toast.error(error.detail || error.message || "Erro ao cancelar solicitação pendente");
        },
    });

    // Simular mudança de plano ou contratação de mais acessos simultâneos
    const simulacaoMutation = useMutation({
        mutationFn: async (data: { plano_destino_id: string; usuarios_destino: number; ciclo_destino: string }) => {
            const response = await apiFetch<SimulacaoResponse>("/billing/mudancas-plano/simular", {
                method: "POST",
                body: JSON.stringify(data)
            });
            return response;
        }
    });

    // Solicitar mudança de plano ou contratação de mais acessos
    const solicitarMutation = useMutation({
        mutationFn: async (data: { plano_destino_id: string; usuarios_destino: number; ciclo_destino: string }) => {
            const response = await apiFetch<SolicitarResponse>("/billing/mudancas-plano/solicitar", {
                method: "POST",
                body: JSON.stringify(data)
            });
            return response;
        },
        onSuccess: (data: SolicitarResponse) => {
                if (data.status === "aplicado") {
                    toast.success(
                        "Plano atualizado com sucesso! A cobrança anterior foi cancelada e uma nova fatura foi gerada com o valor do novo plano."
                    );
                } else if (data.status === "agendado") {
                    toast.success("Alteração agendada para o próximo ciclo de faturamento.");
                } else {
                    toast.success("Solicitação registrada com sucesso!");
                    if (data.url_pagamento) {
                        window.open(data.url_pagamento, "_blank");
                    }
                }


                queryClient.invalidateQueries({ queryKey: ["billing-mudancas-plano"] });
                queryClient.invalidateQueries({ queryKey: ["tenant-data"] });
                queryClient.invalidateQueries({ queryKey: ["billing", "invoices"] });
                queryClient.invalidateQueries({ queryKey: ["tenant-invoices"] });
                onOpenChange(false);
                setShowConfirm(false);
                setPlanoSelecionado(null);
                setSimulacaoData(null);
            },
            onError: (error: { detail?: string; message?: string }) => {
                void refetchMudancas();
                toast.error(error.detail || error.message || "Erro ao solicitar alteração da assinatura");
            }
        });

    const planoAtual = planos?.find(p => p.nome === currentTenant?.assinatura?.plano);
    const planoSelecionadoObj = planos?.find(p => p.id === planoSelecionado);

    function handleSelecionarPlano(planoId: string) {
        setPlanoSelecionado(planoId);
        const targetPlan = planos?.find(p => p.id === planoId);
        if (targetPlan?.limite_usuarios_minimo && usuariosDestino < targetPlan.limite_usuarios_minimo) {
            setUsuariosDestino(targetPlan.limite_usuarios_minimo);
        }
    }

    async function handleContinuar() {
        if (!planoSelecionado || !currentTenant?.assinatura) return;

        try {
            const simulacao = await simulacaoMutation.mutateAsync({
                plano_destino_id: planoSelecionado,
                usuarios_destino: usuariosDestino,
                ciclo_destino: ciclo,
            });
            setSimulacaoData(simulacao);
            setShowConfirm(true);
        } catch (error) {
            const err = error as { detail?: string; message?: string };
            toast.error(err.detail || err.message || "Erro ao simular composição da mensalidade");
        }
    }

    async function handleConfirmar() {
        if (!planoSelecionado) return;

        solicitarMutation.mutate({
            plano_destino_id: planoSelecionado,
            usuarios_destino: usuariosDestino,
            ciclo_destino: ciclo,
        });
    }

    const planoPendenteNome = mudancaPendente
        ? planos?.find((p) => p.id === mudancaPendente.plano_destino_id)?.nome
        : undefined;

    function handleCancelar() {
        setShowConfirm(false);
        setSimulacaoData(null);
    }

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto rounded-sm">
                {!showConfirm ? (
                    <>
                        <DialogHeader>
                            <DialogTitle>Alterar Plano</DialogTitle>
                            <DialogDescription>
                                Escolha um novo plano para sua conta. A mudança será aplicada conforme as condições abaixo.
                            </DialogDescription>
                        </DialogHeader>

                        <div className="space-y-6">
                            {mudancaPendente && (
                                <PendingPlanChangeBanner
                                    mudanca={mudancaPendente}
                                    planoNome={planoPendenteNome}
                                    canceling={cancelarPendenteMutation.isPending}
                                    onCancel={(id) => cancelarPendenteMutation.mutate(id)}
                                />
                            )}

                            {/* Plano Atual */}
                            {currentTenant?.assinatura && (
                                <div className="p-4 bg-muted/50 rounded-lg border">
                                    <div className="flex items-center justify-between">
                                        <div>
                                            <p className="text-xs font-bold text-muted-foreground uppercase tracking-wider">Plano Atual</p>
                                            <p className="text-lg font-bold mt-1">{currentTenant.assinatura.plano}</p>
                                        </div>
                                        <Badge variant="outline" className="bg-primary/5 text-primary border-primary/20">
                                            {formatCurrency(currentTenant.assinatura.valor)}/mês
                                        </Badge>
                                    </div>
                                </div>
                            )}

                            {/* Seleção de Ciclo */}
                            <div className="space-y-3">
                                <Label className="text-sm font-bold">Ciclo de Faturamento</Label>
                                <div className="flex gap-3">
                                    <button
                                        type="button"
                                        onClick={() => setCiclo("MENSAL")}
                                        aria-pressed={ciclo === "MENSAL"}
                                        className={`flex-1 p-3 rounded-lg border-2 transition-all ${ciclo === "MENSAL"
                                                ? "border-primary bg-primary/5"
                                                : "border-border hover:border-primary/50"
                                            }`}
                                    >
                                        <p className="font-bold">Mensal</p>
                                    </button>
                                    <button
                                        type="button"
                                        onClick={() => setCiclo("ANUAL")}
                                        aria-pressed={ciclo === "ANUAL"}
                                        className={`flex-1 p-3 rounded-sm border-2 transition-all ${ciclo === "ANUAL"
                                                ? "border-primary bg-primary/5"
                                                : "border-border hover:border-primary/50"
                                            }`}
                                    >
                                        <p className="font-bold">Anual</p>
                                        <Badge variant="secondary" className="text-xs mt-1 rounded-sm">2 meses grátis + 20% OFF em acessos extras</Badge>
                                    </button>
                                </div>
                            </div>

                            {/* Quantidade de Acessos Simultâneos */}
                            <div className="p-4 border rounded-sm bg-muted/20 space-y-2">
                                <div className="flex items-center justify-between gap-4">
                                    <div>
                                        <Label htmlFor="usuarios_destino" className="text-sm font-bold flex items-center gap-1.5">
                                            <Users className="size-4 text-primary" />
                                            Quantidade de Acessos Simultâneos Contratados (Web)
                                        </Label>
                                        <p className="text-xs text-muted-foreground mt-0.5">
                                            Cadastre quantos usuários precisar na equipe. O valor é composto pelo pacote base + acessos simultâneos adicionais na Web. O uso no <strong>Aplicativo Campo é 100% isento</strong> e não consome acesso simultâneo.
                                        </p>
                                    </div>
                                    <Input
                                        id="usuarios_destino"
                                        type="number"
                                        min={planoSelecionadoObj?.limite_usuarios_minimo || 1}
                                        max={planoSelecionadoObj?.limite_usuarios_maximo || undefined}
                                        className="w-24 h-8 text-xs rounded-sm text-center font-bold"
                                        value={usuariosDestino}
                                        onChange={e => setUsuariosDestino(Math.max(1, Number(e.target.value) || 1))}
                                    />
                                </div>
                            </div>

                            {/* Lista de Planos */}
                            <div className="space-y-3">
                                <Label className="text-sm font-bold">Pacotes Disponíveis</Label>
                                {isLoading ? (
                                    <div className="flex items-center justify-center py-8">
                                        <Loader2 className="h-6 w-6 animate-spin text-primary" />
                                    </div>
                                ) : (
                                    <div className="grid gap-3">
                                        {planos?.map((plano) => {
                                            const isCurrent = plano.nome === currentTenant?.assinatura?.plano;
                                            const isSelected = plano.id === planoSelecionado;
                                            const price = ciclo === "MENSAL" ? plano.preco_mensal : plano.preco_anual;

                                            return (
                                                <button
                                                    type="button"
                                                    key={plano.id}
                                                    aria-pressed={isSelected}
                                                    className={`w-full p-4 rounded-sm border-2 text-left transition-all ${isSelected
                                                            ? "border-primary bg-primary/5"
                                                            : "border-border hover:border-primary/50"
                                                        }`}
                                                    onClick={() => handleSelecionarPlano(plano.id)}
                                                >
                                                    <div className="flex items-start justify-between gap-4">
                                                        <div className="flex-1">
                                                            <div className="flex items-center gap-2 flex-wrap">
                                                                <h3 className="font-bold text-lg">{plano.nome}</h3>
                                                                {isCurrent && (
                                                                    <Badge variant="secondary" className="text-xs">Pacote Atual</Badge>
                                                                )}
                                                                {plano.destaque && (
                                                                    <Badge className="bg-primary text-primary-foreground text-xs">Mais Popular</Badge>
                                                                )}
                                                            </div>
                                                            {plano.descricao && (
                                                                <p className="text-sm text-muted-foreground mt-1">{plano.descricao}</p>
                                                            )}
                                                            <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground">
                                                                <span className="flex items-center gap-1">
                                                                    <Tractor className="size-3.5 text-primary" />
                                                                    {plano.limite_hectares
                                                                        ? `Até ${plano.limite_hectares.toLocaleString("pt-BR")} ha`
                                                                        : "Área ilimitada"}
                                                                </span>
                                                                <span className="flex items-center gap-1">
                                                                    <Users className="size-3.5 text-primary" />
                                                                    {plano.limite_usuarios_minimo || 1} acesso(s) simultâneo(s) incluso(s)
                                                                </span>
                                                            </div>
                                                            <div className="flex flex-wrap gap-2 mt-3">
                                                                {plano.modulos_inclusos?.map((mod) => (
                                                                    <Badge key={mod} variant="outline" className="text-xs">
                                                                        {mod}
                                                                    </Badge>
                                                                ))}
                                                            </div>
                                                        </div>
                                                        <div className="text-right">
                                                            <p className="text-2xl font-bold">{formatCurrency(price)}</p>
                                                            <p className="text-xs text-muted-foreground">base /{ciclo === "MENSAL" ? "mês" : "ano"}</p>
                                                        </div>
                                                    </div>
                                                    {isSelected && (
                                                        <div className="mt-3 flex items-center gap-2 text-sm text-primary font-medium">
                                                            <Check size={14} /> Pacote selecionado
                                                        </div>
                                                    )}
                                                </button>
                                            );
                                        })}
                                    </div>
                                )}
                            </div>
                        </div>

                        <DialogFooter className="gap-2">
                            <Button variant="outline" onClick={() => onOpenChange(false)}>
                                Cancelar
                            </Button>
                            <Button
                                onClick={handleContinuar}
                                disabled={!planoSelecionado || simulacaoMutation.isPending}
                            >
                                {simulacaoMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                                Continuar
                            </Button>
                        </DialogFooter>
                    </>
                ) : (
                    <>
                        <DialogHeader>
                            <DialogTitle className="flex items-center gap-2">
                                {planoSelecionadoObj?.nome && (
                                    <>
                                        Confirmar Mudança para {planoSelecionadoObj.nome}
                                        {(() => {
                                            const precoAtual = planoAtual?.preco_mensal || 0;
                                            const precoNovo = ciclo === "MENSAL" ? planoSelecionadoObj.preco_mensal : planoSelecionadoObj.preco_anual;
                                            const isUpgrade = precoNovo > precoAtual;
                                            return isUpgrade ? (
                                                <ArrowUpRight className="text-emerald-500" size={20} />
                                            ) : (
                                                <ArrowDownRight className="text-amber-500" size={20} />
                                            );
                                        })()}
                                    </>
                                )}
                            </DialogTitle>
                            <DialogDescription>
                                Revise os detalhes da mudança e confirme para prosseguir.
                            </DialogDescription>
                        </DialogHeader>

                        <div className="space-y-4 py-4">
                            {mudancaPendente && (
                                <PendingPlanChangeBanner
                                    mudanca={mudancaPendente}
                                    planoNome={planoPendenteNome}
                                    canceling={cancelarPendenteMutation.isPending}
                                    onCancel={(id) => cancelarPendenteMutation.mutate(id)}
                                />
                            )}

                            {/* Resumo da Mudança */}
                            <div className="p-4 bg-muted/50 rounded-sm border space-y-3">
                                <div className="flex justify-between items-center">
                                    <span className="text-sm text-muted-foreground">Pacote:</span>
                                    <span className="font-bold text-primary">{planoSelecionadoObj?.nome}</span>
                                </div>
                                <div className="flex justify-between items-center">
                                    <span className="text-sm text-muted-foreground">Acessos simultâneos contratados:</span>
                                    <span className="font-bold">{usuariosDestino} acesso(s)</span>
                                </div>
                                <Separator />
                                {simulacaoData?.detalhes_novo && simulacaoData.detalhes_novo.length > 0 && (
                                    <div className="space-y-1 text-xs">
                                        <p className="font-semibold text-muted-foreground">Composição da mensalidade:</p>
                                        {simulacaoData.detalhes_novo.map((faixa, idx) => (
                                            <div key={idx} className="flex justify-between">
                                                <span>
                                                    {faixa.tipo === "PACOTE_BASE"
                                                        ? `Pacote Base (inclui até ${faixa.faixa_fim} acesso(s))`
                                                        : `Acessos extras (+${faixa.usuarios_nesta_faixa} na faixa ${faixa.faixa_inicio}-${faixa.faixa_fim ?? "∞"})`}
                                                </span>
                                                <span className="font-medium">{formatCurrency(faixa.valor_faixa)}</span>
                                            </div>
                                        ))}
                                        <Separator className="my-1" />
                                    </div>
                                )}
                                <div className="flex justify-between items-center">
                                    <span className="text-sm text-muted-foreground">Valor atual:</span>
                                    <span className="font-bold">
                                        {formatCurrency(
                                            simulacaoData?.valor_atual_mensal ??
                                            simulacaoData?.valor_atual ??
                                            currentTenant?.assinatura?.valor ??
                                            0
                                        )}/{ciclo === "MENSAL" ? "mês" : "ano"}
                                    </span>
                                </div>
                                <div className="flex justify-between items-center">
                                    <span className="text-sm text-muted-foreground">Novo valor composto:</span>
                                    <span className="font-bold text-primary">
                                        {formatCurrency(
                                            simulacaoData?.valor_novo_mensal ??
                                            simulacaoData?.valor_novo ??
                                            (ciclo === "MENSAL" ? planoSelecionadoObj?.preco_mensal || 0 : planoSelecionadoObj?.preco_anual || 0)
                                        )}/{ciclo === "MENSAL" ? "mês" : "ano"}
                                    </span>
                                </div>
                                {simulacaoData && (
                                    <>
                                        <div className="flex justify-between items-center text-xs">
                                            <span className="text-muted-foreground">
                                                Diferença na {ciclo === "MENSAL" ? "mensalidade" : "anuidade"}:
                                            </span>
                                            <span className="font-semibold">
                                                {simulacaoData.diferenca_mensal >= 0 ? "+" : ""}
                                                {formatCurrency(simulacaoData.diferenca_mensal)}/{ciclo === "MENSAL" ? "mês" : "ano"}
                                            </span>
                                        </div>
                                        {simulacaoData.valor_proporcional !== undefined &&
                                            simulacaoData.valor_proporcional !== null &&
                                            simulacaoData.valor_proporcional > 0 && (
                                                <div className="flex justify-between items-center pt-2 border-t text-sm">
                                                    <span className="font-semibold text-foreground">
                                                        Fatura de ajuste atual ({simulacaoData.dias_restantes_ciclo ?? 30} dias):
                                                    </span>
                                                    <span className="font-bold text-emerald-600 dark:text-emerald-400">
                                                        {formatCurrency(simulacaoData.valor_proporcional)}
                                                    </span>
                                                </div>
                                            )}
                                    </>
                                )}
                            </div>

                            {/* Aviso */}
                            <div className="flex gap-3 p-4 bg-amber-500/10 border border-amber-500/20 rounded-sm">
                                <AlertCircle className="text-amber-500 shrink-0 mt-0.5" size={18} />
                                <div className="text-sm">
                                    <p className="font-bold text-amber-700 dark:text-amber-300">Importante</p>
                                    <p className="text-muted-foreground mt-1">
                                            {
                                                simulacaoData?.mensagem || (() => {
                                                    const precoAtual = planoAtual?.preco_mensal || 0;
                                                    const precoNovo = ciclo === "MENSAL" ? planoSelecionadoObj?.preco_mensal || 0 : planoSelecionadoObj?.preco_anual || 0;
                                                    const isUpgrade = precoNovo > precoAtual;

                                                    if (isUpgrade) {
                                                        return "Você será redirecionado para o pagamento da diferença proporcional do plano. A mudança será aplicada após a confirmação do pagamento.";
                                                    } else {
                                                        return "O downgrade será aplicado no próximo ciclo de faturamento. Você manterá acesso ao plano atual até lá.";
                                                    }
                                                })()
                                            }
                                    </p>
                                </div>
                            </div>
                        </div>

                        <DialogFooter className="gap-2">
                            <Button variant="outline" size="sm" className="rounded-sm" onClick={handleCancelar}>
                                Voltar
                            </Button>
                            <Button
                                variant="outline"
                                size="sm"
                                className="rounded-sm"
                                onClick={handleConfirmar}
                                disabled={
                                    solicitarMutation.isPending ||
                                    (!!mudancaPendente && !isPrePagamento && simulacaoData?.requer_pagamento !== false)
                                }
                            >
                                {solicitarMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                                Confirmar Mudança
                            </Button>
                        </DialogFooter>
                    </>
                )}
            </DialogContent>
        </Dialog>
    );
}
