"use client";

import { useAppStore } from "@/lib/stores/app-store";
import { apiFetch } from "@/lib/api";
import { useRouter } from "next/navigation";
import { Building2, Trees } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { setContextCookies } from "@/app/actions/auth";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { useEffect } from "react";
import type { UnidadeProdutiva } from "@/types/global";
import { resolveAssetUrl } from "@/lib/runtime-config";

export function ContextSelector() {
    const router = useRouter();
    const { 
        grupos, 
        activeGrupoId, 
        activeFazendaId, 
        isVisaoGrupo, 
        setActiveFazenda, 
        setActiveGrupo, 
        tenant,
        tenantContexts,
        loadTenantContexts,
        unidadesProdutivasAutorizadas,
        token,
        _hasHydrated,
    } = useAppStore();

    // Carrega tenants/contextos ao montar componente
    useEffect(() => {
        if (tenantContexts.length === 0) {
            loadTenantContexts();
        }
    }, [tenantContexts.length, loadTenantContexts]);

    const grupoAtivo = grupos.find(g => g.id === activeGrupoId) ?? grupos[0];
    const multiGrupo = grupos.length > 1;
    const multiContexto = tenantContexts.length > 1;
    const fazendasDoGrupoAtivo = grupoAtivo?.fazendas ?? [];
    const activeFazendaValida = fazendasDoGrupoAtivo.some((f) => f.id === activeFazendaId);
    const fallbackFazendaId = fazendasDoGrupoAtivo[0]?.id ?? null;
    const effectiveFazendaId = activeFazendaValida ? activeFazendaId : fallbackFazendaId;
    const fazendaAtivaStore = unidadesProdutivasAutorizadas.find((f) => f.id === activeFazendaId);
    const fazendaFallbackStore = unidadesProdutivasAutorizadas.find((f) => f.id === fallbackFazendaId);
    const resolvedFazendaId = effectiveFazendaId ?? fazendaAtivaStore?.id ?? fazendaFallbackStore?.id ?? null;

    useEffect(() => {
        if (!tenant || !grupoAtivo || isVisaoGrupo) return;
        if (activeFazendaValida) return;
        if (fallbackFazendaId) {
            setActiveFazenda(fallbackFazendaId, false);
            void setContextCookies(tenant.id, fallbackFazendaId).then(() => {
                router.refresh();
            });
        }
    }, [
        tenant,
        grupoAtivo,
        isVisaoGrupo,
        activeFazendaValida,
        fallbackFazendaId,
        setActiveFazenda,
        router,
    ]);

    const { data: fazendaAtivaDetalhe } = useQuery<UnidadeProdutiva | null>({
        queryKey: ["contexto-ativo-fazenda", effectiveFazendaId],
        queryFn: async () => {
            if (!effectiveFazendaId) return null;
            if (!token) return fazendaAtivaStore ?? fazendaFallbackStore ?? null;
            try {
                return await apiFetch<UnidadeProdutiva>(`/unidades-produtivas/${effectiveFazendaId}`, { suppressErrorLog: true });
            } catch {
                return fazendaAtivaStore ?? fazendaFallbackStore ?? null;
            }
        },
        enabled: _hasHydrated && !!effectiveFazendaId && activeFazendaValida,
        retry: false,
        staleTime: 60_000,
    });

    const fazendaAtiva = fazendaAtivaDetalhe ?? fazendaAtivaStore ?? fazendaFallbackStore ?? null;
    const fazendaLogoSrc = (() => {
        return resolveAssetUrl(fazendaAtiva?.logo_url);
    })();

    // Valor do select: "TODOS" | "grupo:{id}" | "{unidade_produtiva_id}"
    const selectValue = isVisaoGrupo
        ? "TODOS"
        : (resolvedFazendaId || "");

    const refreshContextData = async (fazendaId: string | null) => {
        if (!tenant) return;
        await setContextCookies(tenant.id, fazendaId);
        router.refresh();
    };

    const handleChange = (val: string) => {
        if (val === "TODOS") {
            setActiveFazenda(activeFazendaId || "", true);
            void refreshContextData(null);
        } else if (val.startsWith("grupo:")) {
            const grupoId = val.replace("grupo:", "");
            const nextFazendaId = grupos.find((g) => g.id === grupoId)?.fazendas[0]?.id ?? null;
            setActiveGrupo(grupoId);
            void refreshContextData(nextFazendaId);
        } else {
            const isAuthorized = grupos.some((grupo) => grupo.fazendas.some((fazenda) => fazenda.id === val));
            if (!isAuthorized) return;
            setActiveFazenda(val, false);
            void refreshContextData(val);
        }
    };

    if (!tenant || grupos.length === 0 || !_hasHydrated) return null;

    // Se há múltiplos contextos, mostrar apenas o seletor de fazendas
    // (troca de tenant é responsabilidade do TenantSwitcher, no topbar)
    if (multiContexto) {
        return (
            <div className="flex items-center gap-2">
                {/* Seletor de fazendas do grupo ativo */}
                <Select value={selectValue} onValueChange={handleChange}>
                    <SelectTrigger className="w-auto min-w-[220px] max-w-[260px] rounded-full border border-border/60 bg-white/45 px-3 py-1.5 text-left shadow-sm backdrop-blur-sm transition-colors hover:bg-white/70 hover:text-foreground focus-visible:ring-2 focus-visible:ring-primary/20 aria-expanded:bg-white/70 aria-expanded:text-foreground dark:bg-white/10 dark:hover:bg-white/18">
                        <SelectValue placeholder="Selecionar contexto" />
                    </SelectTrigger>
                    <SelectContent className="w-[280px]">
                        {multiGrupo && (
                            <SelectItem value="TODOS" className="font-medium">
                                Visão Consolidada
                            </SelectItem>
                        )}

                        {grupos.filter((g) => g.id === activeGrupoId).map((grupo) => (
                            <div key={grupo.id} className="py-1">
                                <div className="px-2 pb-1 text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                                    {grupo.nome}
                                </div>
                                {grupo.fazendas.length === 0 ? (
                                    <SelectItem value={`grupo:${grupo.id}`} disabled className="italic text-muted-foreground">
                                        (sem fazendas cadastradas)
                                    </SelectItem>
                                ) : (
                                    grupo.fazendas.map((faz) => (
                                        <SelectItem key={faz.id} value={faz.id} className="pl-4">
                                            {faz.nome}
                                        </SelectItem>
                                    ))
                                )}
                            </div>
                        ))}
                    </SelectContent>
                </Select>
            </div>
        );
    }

    // Se há apenas um contexto, manter o seletor original
    return (
        <div className="flex items-center gap-3 relative group rounded-md border border-border/60 bg-white/45 px-3 py-1.5 text-sm shadow-sm backdrop-blur-sm transition-colors hover:bg-white/70 dark:bg-white/10 dark:hover:bg-white/18">
            <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-sm bg-primary/10 text-primary">
                {!isVisaoGrupo && fazendaLogoSrc ? (
                    <img src={fazendaLogoSrc} alt={fazendaAtiva?.nome ?? "Propriedade"} className="h-full w-full rounded-sm object-cover" />
                ) : isVisaoGrupo ? (
                    <Building2 size={16} />
                ) : (
                    <Trees size={16} />
                )}
            </div>

            <div className="flex flex-col">
                <span className="text-[10px] uppercase font-bold text-muted-foreground tracking-wider mb-0.5">Contexto Ativo</span>
                <Select value={selectValue} onValueChange={handleChange}>
                    <SelectTrigger className="h-auto border-0 bg-transparent p-0 text-sm font-medium shadow-none focus:ring-0 focus-visible:ring-0 focus-visible:ring-offset-0 w-full hover:bg-transparent justify-between gap-2 max-w-[150px] lg:max-w-[200px]">
                        <SelectValue placeholder={fazendaAtiva?.nome ?? tenant?.nome ?? "Selecionar contexto"} className="truncate" />
                    </SelectTrigger>
                    <SelectContent className="w-[280px]">
                        {multiGrupo && (
                            <SelectItem value="TODOS" className="font-bold">
                                🌐 Visão Consolidada
                            </SelectItem>
                        )}

                        {grupos.map((grupo) => (
                            <div key={grupo.id}>
                                <div className="px-2 py-1.5 text-[10px] font-semibold uppercase text-muted-foreground">
                                    {grupo.nome}
                                </div>
                                {grupo.fazendas.length === 0 && (
                                    <SelectItem disabled value={`grupo:${grupo.id}`} className="italic text-muted-foreground pl-4">
                                        (sem fazendas cadastradas)
                                    </SelectItem>
                                )}
                                {grupo.fazendas.map((faz) => (
                                    <SelectItem key={faz.id} value={faz.id} className="pl-4">
                                        {faz.nome}
                                    </SelectItem>
                                ))}
                            </div>
                        ))}
                    </SelectContent>
                </Select>
            </div>
        </div>
    );
}
