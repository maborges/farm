"use client";

import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { toast } from "sonner";
import { useAppStore } from "@/lib/stores/app-store";
import { Loader2, Shield } from "lucide-react";
import {
    Sheet, SheetContent, SheetDescription, SheetFooter, SheetHeader, SheetTitle,
} from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { RoleSelect } from "./role-select";
import { VigenciaBadge } from "./vigencia-badge";
import { Skeleton } from "@/components/ui/skeleton";
import type { UnidadeProdutiva, FazendaAccess } from "@/types/global";

interface AcessoDrawerProps {
    open: boolean;
    onOpenChange: (v: boolean) => void;
    usuarioId: string;
    usuarioNome: string;
    tenantId?: string;
}

interface AcessoItem {
    unidade_produtiva_id: string;
    fazenda_nome: string;
    tem_acesso: boolean;
    perfil_unidade_produtiva_id: string | null;
    vigencia_inicio: string | null;
    vigencia_fim: string | null;
}

// Referência estável — evita recriar um array novo a cada render enquanto a
// query ainda não resolveu, o que causaria loop infinito no useEffect abaixo
// (dependências [fazendas, acessosAtuais] "mudando" a cada render).
const EMPTY_ARRAY: never[] = [];

export function AcessoDrawer({ open, onOpenChange, usuarioId, usuarioNome }: AcessoDrawerProps) {
    const queryClient = useQueryClient();
    const token = useAppStore((s) => s.token);
    const tenantId = useAppStore((s) => s.tenant?.id);
    const hasHydrated = useAppStore((s) => s._hasHydrated);

    const { data: fazendas = EMPTY_ARRAY, isLoading: loadingFazendas } = useQuery<UnidadeProdutiva[]>({
        queryKey: ["unidades-produtivas"],
        queryFn: () => apiFetch("/unidades-produtivas"),
        enabled: open && hasHydrated && !!token && !!tenantId,
    });

    const { data: acessosAtuais = EMPTY_ARRAY, isLoading: loadingAcessos } = useQuery<FazendaAccess[]>({
        queryKey: ["usuario-acessos", usuarioId],
        queryFn: () => apiFetch(`/team/members/${usuarioId}/fazendas`),
        enabled: open && hasHydrated && !!token && !!usuarioId,
    });

    const [itens, setItens] = useState<AcessoItem[]>([]);

    useEffect(() => {
        if (fazendas.length > 0) {
            setItens(fazendas.map((f) => {
                const acesso = acessosAtuais.find((a) => a.id === f.id);
                return {
                    unidade_produtiva_id: f.id,
                    fazenda_nome: f.nome,
                    tem_acesso: !!acesso,
                    perfil_unidade_produtiva_id: acesso?.perfil_fazenda_id ?? null,
                    vigencia_inicio: acesso?.vigencia_inicio ?? null,
                    vigencia_fim: acesso?.vigencia_fim ?? null,
                };
            }));
        }
    }, [fazendas, acessosAtuais]);

    const saveMutation = useMutation({
        mutationFn: async () => {
            const comAcesso = itens.filter((i) => i.tem_acesso);
            await apiFetch(`/team/members/${usuarioId}/fazendas`, {
                method: "PUT",
                body: JSON.stringify({
                    fazendas: comAcesso.map((i) => ({
                        unidade_produtiva_id: i.unidade_produtiva_id,
                        perfil_fazenda_id: i.perfil_unidade_produtiva_id || null,
                        vigencia_inicio: i.vigencia_inicio || null,
                        vigencia_fim: i.vigencia_fim || null,
                    })),
                }),
            });
        },
        onSuccess: () => {
            toast.success("Acessos atualizados com sucesso!");
            queryClient.invalidateQueries({ queryKey: ["team-members"] });
            queryClient.invalidateQueries({ queryKey: ["usuario-acessos", usuarioId] });
            onOpenChange(false);
        },
        onError: (err: Error) => toast.error(err.message || "Erro ao salvar acessos"),
    });

    const isLoading = loadingFazendas || loadingAcessos;

    function toggle(unidade_produtiva_id: string) {
        setItens((prev) => prev.map((i) =>
            i.unidade_produtiva_id === unidade_produtiva_id ? { ...i, tem_acesso: !i.tem_acesso } : i
        ));
    }

    function setVigencia(unidade_produtiva_id: string, field: "vigencia_inicio" | "vigencia_fim", value: string) {
        setItens((prev) => prev.map((i) =>
            i.unidade_produtiva_id === unidade_produtiva_id ? { ...i, [field]: value || null } : i
        ));
    }

    function setPerfil(unidade_produtiva_id: string, perfilId: string) {
        setItens((prev) => prev.map((i) =>
            i.unidade_produtiva_id === unidade_produtiva_id ? { ...i, perfil_unidade_produtiva_id: perfilId || null } : i
        ));
    }

    return (
        <Sheet open={open} onOpenChange={onOpenChange}>
            <SheetContent className="w-full sm:max-w-lg overflow-y-auto">
                <SheetHeader>
                    <SheetTitle className="flex items-center gap-2">
                        <Shield className="size-4" /> Gerenciar Acessos
                    </SheetTitle>
                    <SheetDescription>
                        Defina quais propriedades <strong>{usuarioNome}</strong> pode acessar e por quanto tempo.
                    </SheetDescription>
                </SheetHeader>

                <div className="space-y-3 py-4">
                    {isLoading ? (
                        Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-16 rounded-lg" />)
                    ) : fazendas.length === 0 ? (
                        <p className="text-sm text-muted-foreground text-center py-6">Nenhuma propriedade cadastrada.</p>
                    ) : (
                        itens.map((item) => (
                            <div key={item.unidade_produtiva_id} className="border rounded-lg p-3 space-y-3">
                                <div className="flex items-center gap-3">
                                    <Checkbox
                                        id={`acesso-${item.unidade_produtiva_id}`}
                                        checked={item.tem_acesso}
                                        onCheckedChange={() => toggle(item.unidade_produtiva_id)}
                                    />
                                    <Label htmlFor={`acesso-${item.unidade_produtiva_id}`} className="font-medium cursor-pointer flex-1">
                                        {item.fazenda_nome}
                                    </Label>
                                    {item.tem_acesso && (item.vigencia_inicio || item.vigencia_fim) && (
                                        <VigenciaBadge
                                            vigencia_inicio={item.vigencia_inicio}
                                            vigencia_fim={item.vigencia_fim}
                                        />
                                    )}
                                </div>

                                {item.tem_acesso && (
                                    <div className="grid grid-cols-2 gap-2 pl-7">
                                        <div className="col-span-2 space-y-1">
                                            <Label className="text-xs text-muted-foreground">Perfil nesta propriedade</Label>
                                            <RoleSelect
                                                value={item.perfil_unidade_produtiva_id ?? undefined}
                                                onChange={(roleId) => setPerfil(item.unidade_produtiva_id, roleId)}
                                                placeholder="Usar perfil padrão do membro"
                                            />
                                        </div>
                                        <div className="space-y-1">
                                            <Label className="text-xs text-muted-foreground">Início da vigência</Label>
                                            <Input
                                                type="date"
                                                value={item.vigencia_inicio ?? ""}
                                                onChange={(e) => setVigencia(item.unidade_produtiva_id, "vigencia_inicio", e.target.value)}
                                                className="h-8 text-xs"
                                            />
                                        </div>
                                        <div className="space-y-1">
                                            <Label className="text-xs text-muted-foreground">Fim da vigência</Label>
                                            <Input
                                                type="date"
                                                value={item.vigencia_fim ?? ""}
                                                onChange={(e) => setVigencia(item.unidade_produtiva_id, "vigencia_fim", e.target.value)}
                                                className="h-8 text-xs"
                                            />
                                        </div>
                                        <p className="col-span-2 text-[10px] text-muted-foreground">
                                            Deixe em branco para acesso permanente.
                                        </p>
                                    </div>
                                )}
                            </div>
                        ))
                    )}
                </div>

                <SheetFooter className="pt-4 border-t">
                    <Button variant="outline" onClick={() => onOpenChange(false)} disabled={saveMutation.isPending}>
                        Cancelar
                    </Button>
                    <Button onClick={() => saveMutation.mutate()} disabled={saveMutation.isPending || isLoading}>
                        {saveMutation.isPending ? <><Loader2 className="size-4 animate-spin mr-2" />Salvando...</> : "Salvar acessos"}
                    </Button>
                </SheetFooter>
            </SheetContent>
        </Sheet>
    );
}
