"use client";

import { useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { ArrowLeft, Loader2, Paperclip, Recycle } from "lucide-react";
import Link from "next/link";

import { apiFetch } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { PessoaSelect } from "@/components/cadastros/PessoaSelect";
import { WorkflowStatusBadge } from "@/components/ui/status-badge";
import { PageHeader } from "@/components/shared/page-header";
import { EmptyState } from "@/components/shared/empty-state";
import type { DevolucaoEmbalagem } from "@farm/zod-schemas";

function formatDate(value: string | null) {
    if (!value) return "—";
    return new Date(`${value}T00:00:00`).toLocaleDateString("pt-BR");
}

export function DevolucaoDetalheClient({ id, initialDevolucao }: { id: string; initialDevolucao: DevolucaoEmbalagem | null }) {
    const qc = useQueryClient();
    const fileInputRef = useRef<HTMLInputElement>(null);
    const [showDialog, setShowDialog] = useState(false);
    const [quantidade, setQuantidade] = useState<number>(0);
    const [destinoPessoaId, setDestinoPessoaId] = useState<string | undefined>();
    const [comprovante, setComprovante] = useState<File | null>(null);

    const { data: devolucao, isLoading } = useQuery<DevolucaoEmbalagem>({
        queryKey: ["agricola", "logistica-reversa-embalagens", id],
        queryFn: () => apiFetch<DevolucaoEmbalagem>(`/agricola/logistica-reversa-embalagens/${id}`),
        initialData: initialDevolucao ?? undefined,
    });

    const registrarMut = useMutation({
        mutationFn: () => {
            const params = new URLSearchParams({ quantidade_embalagens: String(quantidade) });
            if (destinoPessoaId) params.set("destino_pessoa_id", destinoPessoaId);
            const formData = new FormData();
            if (comprovante) formData.append("comprovante", comprovante);
            return apiFetch<DevolucaoEmbalagem>(`/agricola/logistica-reversa-embalagens/${id}/devolucao?${params.toString()}`, {
                method: "POST",
                body: formData,
            });
        },
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ["agricola", "logistica-reversa-embalagens"] });
            setShowDialog(false);
            setQuantidade(0);
            setComprovante(null);
            toast.success("Devolução registrada.");
        },
        onError: (error: Error) => toast.error(error.message || "Erro ao registrar devolução."),
    });

    if (isLoading && !devolucao) {
        return <div className="p-6"><Loader2 className="size-5 animate-spin text-muted-foreground" /></div>;
    }

    if (!devolucao) {
        return (
            <div className="p-6">
                <EmptyState title="Pendência não encontrada" description="Verifique se o link está correto." />
            </div>
        );
    }

    const restante = devolucao.quantidade_embalagens_compradas - devolucao.quantidade_embalagens_devolvidas;

    return (
        <div className="flex flex-col gap-5 p-4 sm:p-6">
            <PageHeader
                title={`Devolução — Produto ${devolucao.produto_id.slice(0, 8)}`}
                description={`Compra em ${formatDate(devolucao.data_compra)} — prazo legal até ${formatDate(devolucao.prazo_limite)}`}
                icon={<Recycle className="text-primary" size={22} />}
                breadcrumbs={[
                    { label: "Agricultura", href: "/dashboard/agricola" },
                    { label: "Logística Reversa de Embalagens", href: "/dashboard/agricola/logistica-reversa-embalagens" },
                    { label: devolucao.produto_id.slice(0, 8) },
                ]}
                actions={
                    <div className="flex items-center gap-2">
                        <WorkflowStatusBadge status={devolucao.status} />
                        <Button size="sm" variant="outline" asChild>
                            <Link href="/dashboard/agricola/logistica-reversa-embalagens">
                                <ArrowLeft className="size-4 mr-1.5" /> Voltar
                            </Link>
                        </Button>
                    </div>
                }
            />

            <Card className="rounded-sm max-w-xl">
                <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-bold">Resumo</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3 text-sm">
                    <div className="flex justify-between"><span className="text-muted-foreground">Compradas</span><span>{devolucao.quantidade_embalagens_compradas}</span></div>
                    <div className="flex justify-between"><span className="text-muted-foreground">Devolvidas</span><span>{devolucao.quantidade_embalagens_devolvidas}</span></div>
                    <div className="flex justify-between font-semibold"><span className="text-muted-foreground">Restante</span><span>{restante}</span></div>
                    {devolucao.comprovante_pdf_url && (
                        <a href={devolucao.comprovante_pdf_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-2 text-primary hover:underline">
                            <Paperclip className="size-4" /> Ver comprovante
                        </a>
                    )}
                    {devolucao.status === "PENDENTE" && (
                        <Button size="sm" onClick={() => { setQuantidade(restante); setShowDialog(true); }}>
                            Registrar devolução
                        </Button>
                    )}
                </CardContent>
            </Card>

            <Dialog open={showDialog} onOpenChange={setShowDialog}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Registrar devolução de embalagens</DialogTitle>
                        <DialogDescription>Pode ser parcial — o restante segue pendente até completar o total comprado.</DialogDescription>
                    </DialogHeader>
                    <div className="space-y-4">
                        <div className="grid gap-2">
                            <Label>Quantidade devolvida agora</Label>
                            <Input
                                type="number"
                                min={1}
                                max={restante}
                                value={quantidade}
                                onChange={(e) => setQuantidade(Number(e.target.value))}
                            />
                        </div>
                        <div className="grid gap-2">
                            <Label>Destino (posto de recebimento)</Label>
                            <PessoaSelect
                                value={destinoPessoaId}
                                onChange={(value) => setDestinoPessoaId(value ?? undefined)}
                                tiposRelacionamento={["POSTO_RECEBIMENTO", "FORNECEDOR"]}
                                placeholder="Opcional — usa o fornecedor da compra se vazio"
                            />
                        </div>
                        <div className="grid gap-2">
                            <Label>Comprovante (opcional)</Label>
                            <input
                                ref={fileInputRef}
                                type="file"
                                accept="application/pdf,image/*"
                                onChange={(e) => setComprovante(e.target.files?.[0] ?? null)}
                                className="text-sm"
                            />
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setShowDialog(false)}>Cancelar</Button>
                        <Button
                            disabled={quantidade <= 0 || quantidade > restante || registrarMut.isPending}
                            onClick={() => registrarMut.mutate()}
                        >
                            {registrarMut.isPending ? "Enviando..." : "Confirmar devolução"}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}
