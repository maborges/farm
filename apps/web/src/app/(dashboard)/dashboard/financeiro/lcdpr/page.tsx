"use client";

import { useState } from "react";
import { apiFetch } from "@/lib/api";
import { useAppStore } from "@/lib/stores/app-store";
import { BookOpen, Download, Info } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { getApiBaseUrl } from "@/lib/runtime-config";
import { Label } from "@/components/ui/label";
import { PageHeader } from "@/components/shared/page-header";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";

const anoAtual = new Date().getFullYear();
const anos = Array.from({ length: 5 }, (_, i) => anoAtual - i);

export default function LcdprPage() {
    const { activeFazendaId } = useAppStore();
    const [ano, setAno] = useState(String(anoAtual));
    const [loading, setLoading] = useState(false);

    async function exportar() {
        setLoading(true);
        try {
            const qs = new URLSearchParams({ ano });
            if (activeFazendaId) qs.set("unidade_produtiva_id", activeFazendaId);

            // Usa fetch diretamente para baixar arquivo binário
            const baseUrl = getApiBaseUrl();
            const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
            const res = await fetch(`${baseUrl}/financeiro/carne-leao/exportar?${qs}`, {
                headers: token ? { Authorization: `Bearer ${token}` } : {},
            });
            if (!res.ok) throw new Error("Erro ao exportar.");
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `carne_leao_${ano}.csv`;
            a.click();
            URL.revokeObjectURL(url);
            toast.success(`Arquivo carne_leao_${ano}.csv baixado.`);
        } catch (e: any) {
            toast.error(e.message || "Erro ao exportar.");
        } finally {
            setLoading(false);
        }
    }

    return (
        <div className="space-y-6 p-6">
            <PageHeader
                title="LCDPR"
                description="Exportação do Carnê-Leão e relatórios fiscais para o produtor rural"
                icon={<BookOpen className="text-primary" size={22} />}
                breadcrumbs={[
                    { label: "Financeiro", href: "/dashboard/financeiro" },
                    { label: "Fiscal e Contábil" },
                    { label: "LCDPR" }
                ]}
            />

            <div className="grid md:grid-cols-2 gap-6">
                <Card>
                    <CardHeader>
                        <CardTitle className="text-sm flex items-center gap-2">
                            <Download className="size-4" />Exportar Carnê-Leão (CSV)
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <p className="text-sm text-muted-foreground">
                            Gera o arquivo CSV com os rendimentos tributáveis do produtor rural para declaração do IRPF / Carnê-Leão.
                        </p>
                        <div className="flex items-center gap-3">
                            <Label className="whitespace-nowrap">Ano de Competência</Label>
                            <Select value={ano} onValueChange={setAno}>
                                <SelectTrigger className="w-32">
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    {anos.map(a => <SelectItem key={a} value={String(a)}>{a}</SelectItem>)}
                                </SelectContent>
                            </Select>
                        </div>
                        <Button onClick={exportar} disabled={loading} className="w-full">
                            <Download className="size-4 mr-2" />
                            {loading ? "Gerando arquivo…" : `Exportar ${ano} (CSV)`}
                        </Button>
                    </CardContent>
                </Card>

                <Card variant="info">
                    <CardHeader>
                        <CardTitle className="text-sm flex items-center gap-2">
                            <Info className="size-4 text-alert-info-icon" />Sobre o LCDPR
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="text-sm text-card-description space-y-2">
                        <p>O <strong>Livro Caixa Digital do Produtor Rural (LCDPR)</strong> é obrigatório para produtores rurais pessoa física que obtiveram receita bruta acima de R$ 3,8 milhões no ano-calendário.</p>
                        <ul className="list-disc pl-4 space-y-1 text-xs">
                            <li>Entregue via e-CAC à Receita Federal</li>
                            <li>Substitui o livro caixa em papel</li>
                            <li>Prazo: mesmo da declaração IRPF (abril)</li>
                        </ul>
                        <p className="text-xs text-alert-info-icon mt-2">O arquivo exportado contém os lançamentos do período conforme padrão da RFB.</p>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
