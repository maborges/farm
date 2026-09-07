"use client";

import { useRef, useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { ArrowLeft, Ban, FileSignature, FileUp, Loader2, Paperclip } from "lucide-react";

import { apiFetch } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import { WorkflowStatusBadge } from "@/components/ui/status-badge";
import { PageHeader } from "@/components/shared/page-header";
import { EmptyState } from "@/components/shared/empty-state";
import type { ReceituarioAgronomico } from "@farm/zod-schemas";

function formatDate(value: string | null) {
    if (!value) return "—";
    return new Date(`${value}T00:00:00`).toLocaleDateString("pt-BR");
}

export function ReceituarioDetalheClient({ id, initialReceituario }: { id: string; initialReceituario: ReceituarioAgronomico | null }) {
    const qc = useQueryClient();
    const fileInputRef = useRef<HTMLInputElement>(null);
    const [showCancelar, setShowCancelar] = useState(false);
    const [motivo, setMotivo] = useState("");

    const { data: receituario, isLoading } = useQuery<ReceituarioAgronomico>({
        queryKey: ["agricola", "receituarios", id],
        queryFn: () => apiFetch<ReceituarioAgronomico>(`/agricola/receituarios/${id}`),
        initialData: initialReceituario ?? undefined,
    });

    const uploadMut = useMutation({
        mutationFn: (file: File) => {
            const formData = new FormData();
            formData.append("arquivo", file);
            return apiFetch<{ arquivo_pdf_url: string; status: string }>(`/agricola/receituarios/${id}/anexo-pdf`, {
                method: "POST",
                body: formData,
            });
        },
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ["agricola", "receituarios"] });
            toast.success("PDF anexado — receituário emitido.");
        },
        onError: (error: Error) => toast.error(error.message || "Erro ao anexar PDF."),
    });

    const cancelarMut = useMutation({
        mutationFn: () => apiFetch(`/agricola/receituarios/${id}/cancelar`, { method: "POST", body: { motivo } }),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ["agricola", "receituarios"] });
            setShowCancelar(false);
            toast.success("Receituário cancelado.");
        },
        onError: (error: Error) => toast.error(error.message || "Erro ao cancelar receituário."),
    });

    if (isLoading && !receituario) {
        return <div className="p-6"><Loader2 className="size-5 animate-spin text-muted-foreground" /></div>;
    }

    if (!receituario) {
        return (
            <div className="p-6">
                <EmptyState title="Receituário não encontrado" description="Verifique se o link está correto." />
            </div>
        );
    }

    return (
        <div className="flex flex-col gap-5 p-4 sm:p-6">
            <PageHeader
                title={receituario.numero ?? `Receituário ${receituario.id.slice(0, 8)}`}
                description={`CREA ${receituario.crea_numero}/${receituario.crea_uf} — emitido em ${formatDate(receituario.data_emissao)}, válido até ${formatDate(receituario.data_validade)}`}
                icon={<FileSignature className="text-primary" size={22} />}
                breadcrumbs={[
                    { label: "Agricultura", href: "/dashboard/agricola" },
                    { label: "Receituário Agronômico", href: "/dashboard/agricola/receituarios" },
                    { label: receituario.numero ?? receituario.id.slice(0, 8) },
                ]}
                actions={
                    <div className="flex items-center gap-2">
                        <WorkflowStatusBadge status={receituario.status} />
                        <Button size="sm" variant="outline" asChild>
                            <Link href="/dashboard/agricola/receituarios">
                                <ArrowLeft className="size-4 mr-1.5" /> Voltar
                            </Link>
                        </Button>
                    </div>
                }
            />

            <div className="grid gap-4 lg:grid-cols-3">
                <Card className="rounded-sm lg:col-span-2">
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-bold">Produtos receitados</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead>Produto</TableHead>
                                    <TableHead>Dose</TableHead>
                                    <TableHead>Cultura</TableHead>
                                    <TableHead>Praga-alvo</TableHead>
                                    <TableHead>Carência</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {receituario.itens.length === 0 ? (
                                    <TableRow>
                                        <TableCell colSpan={5} className="text-center text-muted-foreground text-sm">
                                            Nenhum item.
                                        </TableCell>
                                    </TableRow>
                                ) : receituario.itens.map((item) => (
                                    <TableRow key={item.id}>
                                        <TableCell>{item.produto_id.slice(0, 8)}</TableCell>
                                        <TableCell>{item.dose} {item.unidade_dose}</TableCell>
                                        <TableCell>{item.cultura ?? "—"}</TableCell>
                                        <TableCell>{item.praga_alvo ?? "—"}</TableCell>
                                        <TableCell>{item.carencia_dias != null ? `${item.carencia_dias} dias` : "—"}</TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    </CardContent>
                </Card>

                <Card className="rounded-sm">
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-bold">Documento assinado</CardTitle>
                    </CardHeader>
                    <CardContent className="flex flex-col gap-3">
                        {receituario.arquivo_pdf_url ? (
                            <a
                                href={receituario.arquivo_pdf_url}
                                target="_blank"
                                rel="noreferrer"
                                className="inline-flex items-center gap-2 text-sm text-primary hover:underline"
                            >
                                <Paperclip className="size-4" /> Ver PDF anexado
                            </a>
                        ) : (
                            <p className="text-sm text-muted-foreground">Nenhum PDF anexado ainda.</p>
                        )}

                        {receituario.status !== "CANCELADO" && (
                            <>
                                <input
                                    ref={fileInputRef}
                                    type="file"
                                    accept="application/pdf"
                                    className="hidden"
                                    onChange={(e) => {
                                        const file = e.target.files?.[0];
                                        if (file) uploadMut.mutate(file);
                                        e.target.value = "";
                                    }}
                                />
                                <Button
                                    size="sm"
                                    variant="outline"
                                    disabled={uploadMut.isPending}
                                    onClick={() => fileInputRef.current?.click()}
                                >
                                    <FileUp className="size-4 mr-1.5" />
                                    {uploadMut.isPending ? "Enviando..." : "Anexar PDF assinado"}
                                </Button>
                            </>
                        )}

                        {receituario.status !== "CANCELADO" && (
                            <Button
                                size="sm"
                                variant="ghost"
                                className="text-destructive hover:text-destructive"
                                onClick={() => setShowCancelar(true)}
                            >
                                <Ban className="size-4 mr-1.5" /> Cancelar receituário
                            </Button>
                        )}

                        {receituario.status === "CANCELADO" && receituario.motivo_cancelamento && (
                            <p className="text-xs text-muted-foreground">Motivo: {receituario.motivo_cancelamento}</p>
                        )}
                    </CardContent>
                </Card>
            </div>

            <Dialog open={showCancelar} onOpenChange={setShowCancelar}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Cancelar receituário</DialogTitle>
                        <DialogDescription>Informe o motivo do cancelamento — essa ação não pode ser desfeita.</DialogDescription>
                    </DialogHeader>
                    <div className="grid gap-2">
                        <Label>Motivo</Label>
                        <Textarea value={motivo} onChange={(e) => setMotivo(e.target.value)} rows={3} />
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setShowCancelar(false)}>Voltar</Button>
                        <Button
                            variant="destructive"
                            disabled={motivo.trim().length < 3 || cancelarMut.isPending}
                            onClick={() => cancelarMut.mutate()}
                        >
                            Confirmar cancelamento
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}
