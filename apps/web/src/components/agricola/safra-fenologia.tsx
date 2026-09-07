"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { Leaf, Plus, ChevronDown, ChevronRight, CheckCircle2, XCircle, MapPin, Layers } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter, DialogBody } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useState } from "react";
import { useForm, Controller } from "react-hook-form";
import { toast } from "sonner";
import { Skeleton } from "@/components/ui/skeleton";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";
import { cn } from "@/lib/utils";

interface Escala {
    id: string;
    codigo: string;
    nome: string;
    ordem: number;
}

interface FenologiaRegistro {
    id: string;
    talhao_id: string;
    grupo_id: string | null;
    escala_codigo: string;
    escala_nome: string;
    escala_ordem: number;
    data_observacao: string;
    observacao: string | null;
}

interface Grupo {
    id: string;
    nome: string;
    cor: string | null;
    itens: { talhao_id: string }[];
}

interface Talhao {
    id: string;
    nome: string;
}

interface SafraFenologiaProps {
    safraId: string;
    cultura: string | null;
    grupos: Grupo[];
    talhoes: Talhao[];
}

function fmt(d: string) {
    return format(new Date(d + "T12:00:00"), "dd/MM/yyyy", { locale: ptBR });
}

function TalhaoFenologiaCard({ talhaoId, talhaoNome, registros }: {
    talhaoId: string;
    talhaoNome: string;
    registros: FenologiaRegistro[];
}) {
    const [expanded, setExpanded] = useState(false);
    
    // Garante ordenação cronológica crescente para pegar o último correto
    const talhaoRegistros = [...registros]
        .filter(r => r.talhao_id === talhaoId)
        .sort((a, b) => new Date(a.data_observacao).getTime() - new Date(b.data_observacao).getTime());
        
    const ultimo = talhaoRegistros[talhaoRegistros.length - 1];

    return (
        <Card className={cn(
            "overflow-hidden transition-all duration-200",
            ultimo ? "border-l-[3px] border-l-emerald-500 shadow-sm" : "border-l-[3px] border-l-transparent"
        )}>
            <button
                className="w-full flex items-center gap-3 px-4 py-3 hover:bg-muted/40 transition-colors text-left"
                onClick={() => setExpanded(!expanded)}
            >
                {expanded ? (
                    <ChevronDown className="size-4 text-emerald-600 flex-shrink-0" />
                ) : (
                    <ChevronRight className="size-4 text-muted-foreground flex-shrink-0" />
                )}
                
                <span className="flex-1 text-sm font-semibold text-foreground">{talhaoNome}</span>
                
                <div className="flex items-center gap-3 flex-shrink-0">
                    {ultimo ? (
                        <>
                            <div className="text-right hidden sm:block">
                                <p className="text-xs font-medium text-emerald-700">{ultimo.escala_nome}</p>
                                <p className="text-[11px] text-muted-foreground">{fmt(ultimo.data_observacao)}</p>
                            </div>
                            <Badge className="text-xs px-2 py-0.5 bg-emerald-100 text-emerald-800 border-emerald-200 font-mono shadow-none">
                                {ultimo.escala_codigo}
                            </Badge>
                        </>
                    ) : (
                        <span className="text-xs text-muted-foreground bg-muted px-2 py-0.5 rounded-sm">
                            Sem registro
                        </span>
                    )}
                </div>
            </button>

            {expanded && talhaoRegistros.length > 0 && (
                <div className="border-t bg-muted/20 px-4 py-3">
                    <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-3">
                        Histórico Fenológico
                    </p>
                    <div className="space-y-3 relative before:absolute before:inset-0 before:ml-[11px] before:-translate-x-px md:before:mx-auto md:before:translate-x-0 before:h-full before:w-0.5 before:bg-gradient-to-b before:from-transparent before:via-slate-200 before:to-transparent">
                        {[...talhaoRegistros].reverse().map((r, i) => (
                            <div key={r.id} className="relative flex items-center justify-between md:justify-normal md:odd:flex-row-reverse group is-active">
                                <div className="flex items-center justify-center w-6 h-6 rounded-full border-2 border-white bg-slate-200 text-slate-500 shadow shrink-0 md:order-1 md:group-odd:-translate-x-1/2 md:group-even:translate-x-1/2 z-10">
                                    <Leaf className="size-3" />
                                </div>
                                <div className="w-[calc(100%-3rem)] md:w-[calc(50%-1.5rem)] bg-white p-2.5 rounded-md border shadow-sm flex flex-col gap-1">
                                    <div className="flex items-center justify-between">
                                        <Badge variant="outline" className="font-mono text-[10px] py-0 px-1.5 bg-slate-50">
                                            {r.escala_codigo}
                                        </Badge>
                                        <span className="text-[11px] text-muted-foreground font-medium">
                                            {fmt(r.data_observacao)}
                                        </span>
                                    </div>
                                    <span className="text-xs font-medium text-foreground">{r.escala_nome}</span>
                                    {r.observacao && (
                                        <p className="text-[11px] text-muted-foreground mt-1 italic line-clamp-2">
                                            {r.observacao}
                                        </p>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </Card>
    );
}

export function SafraFenologia({ safraId, cultura, grupos = [], talhoes = [] }: SafraFenologiaProps) {
    const queryClient = useQueryClient();
    const queryKey = ["fenologia", safraId];
    const [isOpen, setIsOpen] = useState(false);
    const [alvoTipo, setAlvoTipo] = useState<"talhao" | "grupo">("talhao");
    const [alvoId, setAlvoId] = useState<string>("");

    const { data: registros = [], isLoading } = useQuery<FenologiaRegistro[]>({
        queryKey,
        queryFn: () => apiFetch(`/safras/${safraId}/fenologia`),
    });

    const { data: escalas = [] } = useQuery<Escala[]>({
        queryKey: ["fenologia-escalas", cultura],
        queryFn: () => apiFetch(`/fenologia/escalas?cultura=${encodeURIComponent(cultura ?? "")}`),
    });

    const mutation = useMutation({
        mutationFn: (data: any) => {
            const url = alvoTipo === "grupo"
                ? `/safras/${safraId}/grupos-talhoes/${alvoId}/fenologia`
                : `/safras/${safraId}/talhoes/${alvoId}/fenologia`;
            return apiFetch(url, { method: "POST", body: JSON.stringify(data) });
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey });
            toast.success(alvoTipo === "grupo" ? "Estágio registrado para o grupo!" : "Estágio registrado!");
            setIsOpen(false);
            reset();
        },
        onError: (e: any) => toast.error(e?.message ?? "Erro ao registrar"),
    });

    const { register, handleSubmit, control, reset } = useForm({
        defaultValues: {
            data_observacao: new Date().toISOString().split("T")[0],
            escala_id: "",
            observacao: "",
        },
    });

    // Agrupa talhões por grupo para exibição
    const talhoesSemGrupo = talhoes.filter(t => !grupos.some(g => g.itens?.some(i => i.talhao_id === t.id)));

    if (isLoading) {
        return <div className="space-y-2">{[1, 2, 3].map(i => <Skeleton key={i} className="h-10 w-full" />)}</div>;
    }

    return (
        <div className="space-y-4">
            <div className="flex justify-end">
                <Button
                    size="sm" variant="outline"
                    onClick={() => setIsOpen(true)}
                >
                    <Plus className="size-3.5 mr-1.5" /> Registrar Estágio
                </Button>
            </div>

            {/* Por grupo */}
            {grupos.map(grupo => {
                const tGrupo = talhoes.filter(t => grupo.itens?.some(i => i.talhao_id === t.id));
                if (tGrupo.length === 0) return null;
                return (
                    <div key={grupo.id}>
                        <div className="flex items-center gap-2 mb-2">
                            {grupo.cor && <div className="size-2.5 rounded-full" style={{ backgroundColor: grupo.cor }} />}
                            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">{grupo.nome}</p>
                        </div>
                        <div className="space-y-1.5 pl-4">
                            {tGrupo.map(t => (
                                <TalhaoFenologiaCard key={t.id} talhaoId={t.id} talhaoNome={t.nome} registros={registros} />
                            ))}
                        </div>
                    </div>
                );
            })}

            {/* Talhões sem grupo */}
            {talhoesSemGrupo.length > 0 && (
                <div>
                    <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">Individuais</p>
                    <div className="space-y-1.5">
                        {talhoesSemGrupo.map(t => (
                            <TalhaoFenologiaCard key={t.id} talhaoId={t.id} talhaoNome={t.nome} registros={registros} />
                        ))}
                    </div>
                </div>
            )}

            {registros.length === 0 && talhoes.length === 0 && (
                <p className="text-sm text-muted-foreground text-center py-4">Nenhum talhão ou registro encontrado.</p>
            )}

            {/* Modal de registro */}
            <Dialog open={isOpen} onOpenChange={setIsOpen}>
                <DialogContent className="sm:max-w-[440px]">
                    <form onSubmit={handleSubmit(d => mutation.mutate(d))}>
                        <DialogHeader>
                            <DialogTitle>Registrar Estágio Fenológico</DialogTitle>
                            <DialogDescription>
                                Registre o estágio observado para um talhão ou grupo da safra.
                            </DialogDescription>
                        </DialogHeader>
                        <DialogBody className="space-y-4">
                            {/* Tipo de alvo */}
                            <div className="flex gap-2">
                                <Button
                                    type="button"
                                    size="sm"
                                    variant={alvoTipo === "talhao" ? "default" : "outline"}
                                    onClick={() => { setAlvoTipo("talhao"); setAlvoId(""); }}
                                >
                                    <MapPin className="size-4" />
                                    Por Talhão
                                </Button>
                                <Button
                                    type="button"
                                    size="sm"
                                    variant={alvoTipo === "grupo" ? "default" : "outline"}
                                    onClick={() => { setAlvoTipo("grupo"); setAlvoId(""); }}
                                    disabled={grupos.length === 0}
                                >
                                    <Layers className="size-4" />
                                    Por Grupo
                                </Button>
                            </div>

                            {/* Seletor talhão ou grupo */}
                            <div className="space-y-1.5">
                                <Label>{alvoTipo === "grupo" ? "Grupo" : "Talhão"}</Label>
                                <Select value={alvoId} onValueChange={setAlvoId}>
                                    <SelectTrigger>
                                        <SelectValue placeholder={alvoTipo === "talhao" ? talhoes.find(t => t.id === alvoId)?.nome || "Selecionar talhão..." : grupos.find(g => g.id === alvoId)?.nome || "Selecionar grupo..."} />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {alvoTipo === "talhao"
                                            ? talhoes.map(t => <SelectItem key={t.id} value={t.id}>{t.nome}</SelectItem>)
                                            : grupos.map(g => (
                                                <SelectItem key={g.id} value={g.id}>
                                                    <span className="flex items-center gap-2">
                                                        {g.cor && <span className="size-2.5 rounded-full inline-block" style={{ backgroundColor: g.cor }} />}
                                                        {g.nome} ({g.itens?.length ?? 0} talhões)
                                                    </span>
                                                </SelectItem>
                                            ))
                                        }
                                    </SelectContent>
                                </Select>
                            </div>

                            <div className="space-y-1.5">
                                <Label>Estágio</Label>
                                <Controller name="escala_id" control={control} rules={{ required: true }}
                                    render={({ field }) => (
                                        <Select onValueChange={field.onChange} value={field.value}>
                                            <SelectTrigger>
                                                <SelectValue placeholder={(() => {
                                                    const e = escalas.find(esc => esc.id === field.value);
                                                    return e ? `${e.codigo} - ${e.nome}` : "Selecionar estágio...";
                                                })()} />
                                            </SelectTrigger>
                                            <SelectContent>
                                                {escalas.map(e => (
                                                    <SelectItem key={e.id} value={e.id}>
                                                        <span className="font-mono font-semibold mr-2">{e.codigo}</span>{e.nome}
                                                    </SelectItem>
                                                ))}
                                            </SelectContent>
                                        </Select>
                                    )}
                                />
                            </div>

                            <div className="space-y-1.5">
                                <Label>Data de observação</Label>
                                <Input type="date" {...register("data_observacao", { required: true })} />
                            </div>

                            <div className="space-y-1.5">
                                <Label>Observação (opcional)</Label>
                                <Textarea placeholder="Ex: 80% das plantas em R1, uniformidade boa..." rows={2} {...register("observacao")} />
                            </div>
                        </DialogBody>
                        <DialogFooter>
                            <Button variant="outline" size="sm" type="button" onClick={() => setIsOpen(false)}>
                                <XCircle className="size-4" />
                                Cancelar
                            </Button>
                            <Button size="sm" type="submit" disabled={mutation.isPending}>
                                <CheckCircle2 className="size-4" />
                                Registrar Estágio
                            </Button>
                        </DialogFooter>
                    </form>
                </DialogContent>
            </Dialog>
        </div>
    );
}
