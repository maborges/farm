"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogDescription,
    DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { formatCurrency } from "@/lib/utils";
import { Loader2, Check, ArrowUpRight, ArrowDownRight, AlertCircle } from "lucide-react";
import { toast } from "sonner";

interface Plano {
    id: string;
    nome: string;
    descricao: string | null;
    preco_mensal: number;
    preco_anual: number;
    plan_tier: string;
    modulos_inclusos: string[];
    destaque: boolean;
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
    const [ciclo, setCiclo] = useState<"MENSAL" | "ANUAL">("MENSAL");
    const [showConfirm, setShowConfirm] = useState(false);

    // Buscar planos disponíveis
    const { data: planos, isLoading } = useQuery<Plano[]>({
        queryKey: ["billing-plans"],
        queryFn: () => apiFetch("/billing/plans"),
        enabled: open
    });

    // Simular mudança de plano
    const simulacaoMutation = useMutation({
        mutationFn: async (data: { plano_destino_id: string; usuarios_destino: number }) => {
            const response = await apiFetch("/billing/mudancas-plano/simular", {
                method: "POST",
                body: JSON.stringify(data)
            });
            return response;
        }
    });

    // Solicitar mudança de plano
    const solicitarMutation = useMutation({
        mutationFn: async (data: { plano_destino_id: string; usuarios_destino: number }) => {
            const response = await apiFetch("/billing/mudancas-plano/solicitar", {
                method: "POST",
                body: JSON.stringify(data)
            });
            return response;
        },
        onSuccess: (data: any) => {
            toast.success("Solicitação criada com sucesso!");
            
            // Se tiver URL de pagamento, abrir em nova aba
            if (data.url_pagamento) {
                window.open(data.url_pagamento, "_blank");
            }
            
            // Atualizar dados do tenant
            queryClient.invalidateQueries({ queryKey: ["tenant-data"] });
            onOpenChange(false);
            setShowConfirm(false);
            setPlanoSelecionado(null);
        },
        onError: (error: any) => {
            toast.error(error.detail || "Erro ao solicitar mudança de plano");
        }
    });

    const planoAtual = planos?.find(p => p.nome === currentTenant?.assinatura?.plano);
    const planoSelecionadoObj = planos?.find(p => p.id === planoSelecionado);

    function handleSelecionarPlano(planoId: string) {
        setPlanoSelecionado(planoId);
    }

    async function handleContinuar() {
        if (!planoSelecionado || !currentTenant?.assinatura) return;

        // Buscar assinatura atual para obter o ID
        const usuariosAtual = currentTenant.tenant.max_usuarios || 1;

        try {
            // Simular primeiro para ver os detalhes
            const simulacao = await simulacaoMutation.mutateAsync({
                plano_destino_id: planoSelecionado,
                usuarios_destino: usuariosAtual
            });

            // Mostrar confirmação
            setShowConfirm(true);
        } catch (error: any) {
            toast.error(error.detail || "Erro ao simular mudança");
        }
    }

    async function handleConfirmar() {
        if (!planoSelecionado) return;

        const usuariosAtual = currentTenant?.tenant.max_usuarios || 1;

        solicitarMutation.mutate({
            plano_destino_id: planoSelecionado,
            usuarios_destino: usuariosAtual
        });
    }

    function handleCancelar() {
        setShowConfirm(false);
        setPlanoSelecionado(null);
    }

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
                {!showConfirm ? (
                    <>
                        <DialogHeader>
                            <DialogTitle>Alterar Plano</DialogTitle>
                            <DialogDescription>
                                Escolha um novo plano para sua conta. A mudança será aplicada conforme as condições abaixo.
                            </DialogDescription>
                        </DialogHeader>

                        <div className="space-y-6">
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
                                        onClick={() => setCiclo("MENSAL")}
                                        className={`flex-1 p-3 rounded-lg border-2 transition-all ${
                                            ciclo === "MENSAL"
                                                ? "border-primary bg-primary/5"
                                                : "border-border hover:border-primary/50"
                                        }`}
                                    >
                                        <p className="font-bold">Mensal</p>
                                    </button>
                                    <button
                                        onClick={() => setCiclo("ANUAL")}
                                        className={`flex-1 p-3 rounded-lg border-2 transition-all ${
                                            ciclo === "ANUAL"
                                                ? "border-primary bg-primary/5"
                                                : "border-border hover:border-primary/50"
                                        }`}
                                    >
                                        <p className="font-bold">Anual</p>
                                        <Badge variant="secondary" className="text-xs mt-1">2 meses grátis</Badge>
                                    </button>
                                </div>
                            </div>

                            {/* Lista de Planos */}
                            <div className="space-y-3">
                                <Label className="text-sm font-bold">Planos Disponíveis</Label>
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
                                                <div
                                                    key={plano.id}
                                                    className={`p-4 rounded-lg border-2 cursor-pointer transition-all ${
                                                        isSelected
                                                            ? "border-primary bg-primary/5"
                                                            : isCurrent
                                                            ? "border-muted bg-muted/30"
                                                            : "border-border hover:border-primary/50"
                                                    }`}
                                                    onClick={() => !isCurrent && handleSelecionarPlano(plano.id)}
                                                >
                                                    <div className="flex items-start justify-between gap-4">
                                                        <div className="flex-1">
                                                            <div className="flex items-center gap-2">
                                                                <h3 className="font-bold text-lg">{plano.nome}</h3>
                                                                {isCurrent && (
                                                                    <Badge variant="secondary" className="text-xs">Atual</Badge>
                                                                )}
                                                                {plano.destaque && (
                                                                    <Badge className="bg-primary text-primary-foreground text-xs">Mais Popular</Badge>
                                                                )}
                                                            </div>
                                                            {plano.descricao && (
                                                                <p className="text-sm text-muted-foreground mt-1">{plano.descricao}</p>
                                                            )}
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
                                                            <p className="text-xs text-muted-foreground">/{ciclo === "MENSAL" ? "mês" : "ano"}</p>
                                                        </div>
                                                    </div>
                                                    {isSelected && (
                                                        <div className="mt-3 flex items-center gap-2 text-sm text-primary font-medium">
                                                            <Check size={14} /> Plano selecionado
                                                        </div>
                                                    )}
                                                </div>
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
                            {/* Resumo da Mudança */}
                            <div className="p-4 bg-muted/50 rounded-lg border space-y-3">
                                <div className="flex justify-between items-center">
                                    <span className="text-sm text-muted-foreground">De:</span>
                                    <span className="font-bold">{currentTenant?.assinatura?.plano}</span>
                                </div>
                                <div className="flex justify-between items-center">
                                    <span className="text-sm text-muted-foreground">Para:</span>
                                    <span className="font-bold text-primary">{planoSelecionadoObj?.nome}</span>
                                </div>
                                <Separator />
                                <div className="flex justify-between items-center">
                                    <span className="text-sm text-muted-foreground">Valor atual:</span>
                                    <span className="font-bold">{formatCurrency(currentTenant?.assinatura?.valor || 0)}/mês</span>
                                </div>
                                <div className="flex justify-between items-center">
                                    <span className="text-sm text-muted-foreground">Novo valor:</span>
                                    <span className="font-bold text-primary">
                                        {formatCurrency(ciclo === "MENSAL" ? planoSelecionadoObj?.preco_mensal || 0 : planoSelecionadoObj?.preco_anual || 0)}/{ciclo === "MENSAL" ? "mês" : "ano"}
                                    </span>
                                </div>
                            </div>

                            {/* Aviso */}
                            <div className="flex gap-3 p-4 bg-amber-500/10 border border-amber-500/20 rounded-lg">
                                <AlertCircle className="text-amber-500 shrink-0 mt-0.5" size={18} />
                                <div className="text-sm">
                                    <p className="font-bold text-amber-700">Importante</p>
                                    <p className="text-muted-foreground mt-1">
                                        {(() => {
                                            const precoAtual = planoAtual?.preco_mensal || 0;
                                            const precoNovo = ciclo === "MENSAL" ? planoSelecionadoObj?.preco_mensal || 0 : planoSelecionadoObj?.preco_anual || 0;
                                            const isUpgrade = precoNovo > precoAtual;
                                            
                                            if (isUpgrade) {
                                                return "Você será redirecionado para o pagamento da diferença proporcional do plano. A mudança será aplicada após a confirmação do pagamento.";
                                            } else {
                                                return "O downgrade será aplicado no próximo ciclo de faturamento. Você manterá acesso ao plano atual até lá.";
                                            }
                                        })()}
                                    </p>
                                </div>
                            </div>
                        </div>

                        <DialogFooter className="gap-2">
                            <Button variant="outline" onClick={handleCancelar}>
                                Voltar
                            </Button>
                            <Button
                                onClick={handleConfirmar}
                                disabled={solicitarMutation.isPending}
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
