"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogBody, DialogDescription } from "@/components/ui/dialog";
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from "@/components/ui/alert-dialog";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { ProdutoCombobox } from "@/components/shared/produto-combobox";
import { TipoServicoCombobox } from "@/components/shared/tiposervico-combobox";
import { useForm } from "react-hook-form";
import { Plus, Trash2, FlaskConical, PackageSearch, Users2, Save, XCircle, Pencil, HelpCircle } from "lucide-react";

function FieldHelp({ text }: { text: string }) {
    return (
        <TooltipProvider>
            <Tooltip>
                <TooltipTrigger tabIndex={-1} className="outline-none">
                    <HelpCircle className="size-3.5 text-muted-foreground cursor-help shrink-0" aria-hidden />
                </TooltipTrigger>
                <TooltipContent side="top" className="max-w-xs text-xs">
                    {text}
                </TooltipContent>
            </Tooltip>
        </TooltipProvider>
    );
}

function FieldLabel({ htmlFor, label, help }: { htmlFor?: string; label: string; help: string }) {
    return (
        <Label htmlFor={htmlFor} className="gap-1.5">
            {label}
            <FieldHelp text={help} />
        </Label>
    );
}

interface ReceitaInsumo {
    id?: string;
    produto_id: string;
    dose_ha: number;
    unidade_dose: string;
}

interface ReceitaMaoObra {
    id?: string;
    tipo_servico_id: string;
    funcao: string;
    quantidade_pessoas: number;
    horas_fixas: number;
    horas_por_hectare: number;
}

export interface ReceitaAplicacao {
    id: string;
    nome: string;
    tipo_operacao: string | null;
    ativo: boolean;
    insumos: ReceitaInsumo[];
    mao_obra: ReceitaMaoObra[];
}

function novoInsumo(): ReceitaInsumo {
    return { produto_id: "", dose_ha: 0, unidade_dose: "L" };
}

function novaMaoObra(): ReceitaMaoObra {
    return { tipo_servico_id: "", funcao: "", quantidade_pessoas: 1, horas_fixas: 0, horas_por_hectare: 0 };
}

// ── Criar/Editar Receita ────────────────────────────────────────────────────

function ReceitaFormDialog({ open, onClose, receita }: { open: boolean; onClose: () => void; receita?: ReceitaAplicacao }) {
    const qc = useQueryClient();
    const editando = !!receita;
    const { register, handleSubmit, reset } = useForm({
        defaultValues: { nome: receita?.nome ?? "", tipo_operacao: receita?.tipo_operacao ?? "" },
    });
    const [insumos, setInsumos] = useState<ReceitaInsumo[]>(receita?.insumos.length ? receita.insumos : [novoInsumo()]);
    const [maoObra, setMaoObra] = useState<ReceitaMaoObra[]>(receita?.mao_obra ?? []);

    const save = useMutation({
        mutationFn: (data: { nome: string; tipo_operacao: string }) => {
            const body = {
                nome: data.nome,
                tipo_operacao: data.tipo_operacao || null,
                insumos: insumos
                    .filter((i) => i.produto_id)
                    .map((i) => ({ produto_id: i.produto_id, dose_ha: Number(i.dose_ha), unidade_dose: i.unidade_dose })),
                mao_obra: maoObra
                    .filter((m) => m.tipo_servico_id)
                    .map((m) => ({
                        tipo_servico_id: m.tipo_servico_id,
                        funcao: m.funcao || null,
                        quantidade_pessoas: Number(m.quantidade_pessoas) || 1,
                        horas_fixas: Number(m.horas_fixas) || 0,
                        horas_por_hectare: Number(m.horas_por_hectare) || 0,
                    })),
            };
            return editando
                ? apiFetch(`/agricola/cadastros/receitas-aplicacao/${receita!.id}`, { method: "PATCH", body: JSON.stringify(body) })
                : apiFetch(`/agricola/cadastros/receitas-aplicacao/`, { method: "POST", body: JSON.stringify(body) });
        },
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ["receitas-aplicacao"] });
            reset();
            onClose();
        },
    });

    return (
        <Dialog open={open} onOpenChange={onClose}>
            <DialogContent className="!max-w-[32rem]">
                <form onSubmit={handleSubmit((data) => save.mutate(data))}>
                    <DialogHeader>
                        <div className="flex items-center gap-2.5">
                            <div className="size-8 rounded-sm bg-primary/10 flex items-center justify-center">
                                <FlaskConical className="size-4 text-primary" />
                            </div>
                            <div className="space-y-0.5">
                                <DialogTitle>{editando ? "Editar receita de aplicação" : "Nova receita de aplicação"}</DialogTitle>
                                <DialogDescription>
                                    Produtos com dose por hectare e mão de obra padrão, reutilizáveis em qualquer plano operacional.
                                </DialogDescription>
                            </div>
                        </div>
                    </DialogHeader>
                    <DialogBody className="flex flex-col gap-5 max-h-[65vh] overflow-y-auto">
                        <div className="grid grid-cols-2 gap-3">
                            <div className="grid gap-1.5">
                                <FieldLabel
                                    htmlFor="nome"
                                    label="Nome da receita"
                                    help="Nome pelo qual a receita será encontrada ao aplicá-la em um plano operacional. Ex: 'Pulverização Fungicida Soja'."
                                />
                                <Input id="nome" {...register("nome", { required: true })} placeholder="Ex: Pulverização Fungicida Soja" />
                            </div>
                            <div className="grid gap-1.5">
                                <FieldLabel
                                    htmlFor="tipo_operacao"
                                    label="Tipo de operação (opcional)"
                                    help="Etiqueta livre para classificar a receita (não valida contra nenhuma lista fixa). Aparece como badge na listagem. Ex: PULVERIZACAO, ADUBACAO, CALAGEM."
                                />
                                <Input id="tipo_operacao" {...register("tipo_operacao")} placeholder="Ex: PULVERIZACAO, ADUBACAO..." />
                            </div>
                        </div>

                        <div className="flex flex-col gap-2">
                            <div className="flex items-center justify-between">
                                <h4 className="text-sm font-medium flex items-center gap-1.5"><PackageSearch className="size-3.5" /> Insumos (dose por hectare)</h4>
                                <Button type="button" size="sm" variant="outline" onClick={() => setInsumos([...insumos, novoInsumo()])}>
                                    <Plus className="size-4 mr-1.5" /> Adicionar
                                </Button>
                            </div>
                            {insumos.map((insumo, idx) => (
                                <div key={idx} className="flex flex-col gap-2 rounded-sm border p-2">
                                    <div className="flex items-center justify-between">
                                        <Label className="text-[11px] text-muted-foreground">Insumo {idx + 1}</Label>
                                        <Button
                                            type="button" size="icon" variant="ghost" className="size-7 text-destructive hover:text-destructive"
                                            aria-label="Remover insumo"
                                            onClick={() => setInsumos(insumos.filter((_, j) => j !== idx))}
                                        >
                                            <Trash2 className="size-3.5" />
                                        </Button>
                                    </div>
                                    <div className="grid gap-1.5">
                                        <FieldLabel
                                            label="Produto"
                                            help="Produto do catálogo (cadastros/produtos) que será usado como insumo. A busca considera produtos do sistema e do seu produtor."
                                        />
                                        <ProdutoCombobox
                                            value={insumo.produto_id}
                                            onChange={(id) => setInsumos(insumos.map((i, j) => (j === idx ? { ...i, produto_id: id } : i)))}
                                        />
                                    </div>
                                    <div className="grid grid-cols-2 gap-2">
                                        <div className="grid gap-1.5">
                                            <FieldLabel
                                                label="Dose/ha"
                                                help="Quantidade do produto por hectare. Ao aplicar a receita numa tarefa, o sistema multiplica esta dose pela área do talhão para obter a quantidade total."
                                            />
                                            <Input
                                                type="number" step="0.01"
                                                value={insumo.dose_ha}
                                                onChange={(e) => setInsumos(insumos.map((i, j) => (j === idx ? { ...i, dose_ha: Number(e.target.value) } : i)))}
                                            />
                                        </div>
                                        <div className="grid gap-1.5">
                                            <FieldLabel
                                                label="Unidade"
                                                help="Unidade de medida da dose informada (ex: L, KG, T, SC). Deve corresponder à unidade de estoque do produto para o cálculo de disponibilidade funcionar corretamente."
                                            />
                                            <Input
                                                value={insumo.unidade_dose}
                                                onChange={(e) => setInsumos(insumos.map((i, j) => (j === idx ? { ...i, unidade_dose: e.target.value } : i)))}
                                            />
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>

                        <div className="flex flex-col gap-2">
                            <div className="flex items-center justify-between">
                                <h4 className="text-sm font-medium flex items-center gap-1.5"><Users2 className="size-3.5" /> Mão de obra padrão (opcional)</h4>
                                <Button type="button" size="sm" variant="outline" onClick={() => setMaoObra([...maoObra, novaMaoObra()])}>
                                    <Plus className="size-4 mr-1.5" /> Adicionar
                                </Button>
                            </div>
                            {maoObra.map((mo, idx) => (
                                <div key={idx} className="flex flex-col gap-2 rounded-sm border p-2">
                                    <div className="flex items-center justify-between">
                                        <Label className="text-[11px] text-muted-foreground">Mão de obra {idx + 1}</Label>
                                        <Button
                                            type="button" size="icon" variant="ghost" className="size-7 text-destructive hover:text-destructive"
                                            aria-label="Remover mão de obra"
                                            onClick={() => setMaoObra(maoObra.filter((_, j) => j !== idx))}
                                        >
                                            <Trash2 className="size-3.5" />
                                        </Button>
                                    </div>
                                    <div className="grid gap-1.5">
                                        <FieldLabel
                                            label="Tipo de serviço"
                                            help="Serviço do cadastro de Tipos de Serviço usado para referenciar o custo/hora de mercado quando não há colaborador específico alocado."
                                        />
                                        <TipoServicoCombobox
                                            value={mo.tipo_servico_id}
                                            onChange={(id) => setMaoObra(maoObra.map((m, j) => (j === idx ? { ...m, tipo_servico_id: id } : m)))}
                                        />
                                    </div>
                                    <div className="grid gap-1.5">
                                        <FieldLabel
                                            label="Função (opcional)"
                                            help="Papel da pessoa na tarefa, só descritivo (não afeta cálculo de custo). Ex: 'Tratorista', 'Auxiliar de campo'."
                                        />
                                        <Input
                                            value={mo.funcao}
                                            onChange={(e) => setMaoObra(maoObra.map((m, j) => (j === idx ? { ...m, funcao: e.target.value } : m)))}
                                        />
                                    </div>
                                    <div className="grid grid-cols-3 gap-2">
                                        <div className="grid gap-1.5">
                                            <FieldLabel
                                                label="Qtd. pessoas"
                                                help="Quantas pessoas são necessárias simultaneamente para esta função. Multiplica o custo total estimado."
                                            />
                                            <Input
                                                type="number" min={1}
                                                value={mo.quantidade_pessoas}
                                                onChange={(e) => setMaoObra(maoObra.map((m, j) => (j === idx ? { ...m, quantidade_pessoas: Number(e.target.value) } : m)))}
                                            />
                                        </div>
                                        <div className="grid gap-1.5">
                                            <FieldLabel
                                                label="Horas fixas"
                                                help="Horas que não dependem do tamanho do talhão (ex: deslocamento, preparo) — somadas uma única vez, independente da área."
                                            />
                                            <Input
                                                type="number" step="0.5"
                                                value={mo.horas_fixas}
                                                onChange={(e) => setMaoObra(maoObra.map((m, j) => (j === idx ? { ...m, horas_fixas: Number(e.target.value) } : m)))}
                                            />
                                        </div>
                                        <div className="grid gap-1.5">
                                            <FieldLabel
                                                label="Horas/ha"
                                                help="Horas de trabalho por hectare. Ao aplicar a receita, o sistema calcula: horas totais = horas fixas + (horas/ha × área do talhão)."
                                            />
                                            <Input
                                                type="number" step="0.01"
                                                value={mo.horas_por_hectare}
                                                onChange={(e) => setMaoObra(maoObra.map((m, j) => (j === idx ? { ...m, horas_por_hectare: Number(e.target.value) } : m)))}
                                            />
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </DialogBody>
                    <DialogFooter>
                        <Button variant="outline" size="sm" onClick={onClose} type="button">
                            <XCircle className="size-3.5 mr-1.5" />
                            Cancelar
                        </Button>
                        <Button size="sm" type="submit" disabled={save.isPending}>
                            <Save className="size-3.5 mr-1.5" />
                            {save.isPending ? "Salvando…" : "Salvar receita"}
                        </Button>
                    </DialogFooter>
                </form>
            </DialogContent>
        </Dialog>
    );
}

// ── Lista de Receitas ─────────────────────────────────────────────────────

export function ReceitasAplicacao() {
    const qc = useQueryClient();
    const [showForm, setShowForm] = useState(false);
    const [editando, setEditando] = useState<ReceitaAplicacao | undefined>(undefined);
    const [removerId, setRemoverId] = useState<string | null>(null);

    const { data: receitas = [], isLoading } = useQuery<ReceitaAplicacao[]>({
        queryKey: ["receitas-aplicacao"],
        queryFn: () => apiFetch(`/agricola/cadastros/receitas-aplicacao/`),
    });

    const remover = useMutation({
        mutationFn: (id: string) => apiFetch(`/agricola/cadastros/receitas-aplicacao/${id}`, { method: "DELETE" }),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ["receitas-aplicacao"] });
            setRemoverId(null);
        },
    });

    return (
        <div className="flex flex-col gap-4">
            <div className="flex items-center justify-between">
                <p className="text-sm text-muted-foreground">
                    Cadastre pacotes de produto + dose/ha e mão de obra padrão para aplicar em lote no planejamento operacional.
                </p>
                <Button size="sm" onClick={() => { setEditando(undefined); setShowForm(true); }}>
                    <Plus className="size-4 mr-1.5" /> Nova receita
                </Button>
            </div>

            {isLoading ? (
                <p className="text-sm text-muted-foreground text-center py-6">Carregando…</p>
            ) : receitas.length === 0 ? (
                <div className="flex flex-col items-center gap-3 rounded-sm border border-dashed px-6 py-10 text-center">
                    <FlaskConical className="size-8 text-muted-foreground/50" />
                    <div className="space-y-1">
                        <p className="text-sm font-medium">Nenhuma receita de aplicação cadastrada</p>
                        <p className="text-sm text-muted-foreground">
                            Crie uma receita para reaproveitar o mesmo pacote de insumos em vários planos.
                        </p>
                    </div>
                    <Button variant="outline" size="sm" onClick={() => setShowForm(true)}>
                        <Plus className="size-4 mr-1.5" /> Criar primeira receita
                    </Button>
                </div>
            ) : (
                <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                    {receitas.map((r) => (
                        <Card key={r.id}>
                            <CardHeader className="pb-2">
                                <div className="flex items-start justify-between gap-2">
                                    <CardTitle className="text-base text-balance">{r.nome}</CardTitle>
                                    {r.tipo_operacao && <Badge variant="outline">{r.tipo_operacao}</Badge>}
                                </div>
                                <CardDescription>
                                    {r.insumos.length} insumo(s) · {r.mao_obra.length} mão de obra
                                </CardDescription>
                            </CardHeader>
                            <CardContent className="flex items-center justify-end gap-0.5 pt-0">
                                <Button
                                    size="icon" variant="ghost" className="size-7 text-primary"
                                    aria-label="Editar"
                                    onClick={() => { setEditando(r); setShowForm(true); }}
                                >
                                    <Pencil className="size-3.5" />
                                </Button>
                                <Button
                                    size="icon" variant="ghost" className="size-7 text-destructive hover:text-destructive"
                                    aria-label="Excluir"
                                    onClick={() => setRemoverId(r.id)}
                                >
                                    <Trash2 className="size-3.5" />
                                </Button>
                            </CardContent>
                        </Card>
                    ))}
                </div>
            )}

            {showForm && (
                <ReceitaFormDialog open={showForm} onClose={() => { setShowForm(false); setEditando(undefined); }} receita={editando} />
            )}

            <AlertDialog open={!!removerId} onOpenChange={() => setRemoverId(null)}>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>Excluir receita de aplicação?</AlertDialogTitle>
                        <AlertDialogDescription>
                            Esta ação não pode ser desfeita. Planos que já aplicaram esta receita não são afetados.
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel onClick={() => setRemoverId(null)}>Cancelar</AlertDialogCancel>
                        <AlertDialogAction
                            variant="destructive"
                            onClick={() => removerId && remover.mutate(removerId)}
                            disabled={remover.isPending}
                        >
                            Excluir
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>
        </div>
    );
}
