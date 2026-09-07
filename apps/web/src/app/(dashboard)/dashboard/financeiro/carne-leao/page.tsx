"use client";

import { useState } from "react";
import { apiFetch } from "@/lib/api";
import { useAppStore } from "@/lib/stores/app-store";
import { toast } from "sonner";
import { FileDown, BookOpen, Loader2, Info } from "lucide-react";
import { PageHeader } from "@/components/shared/page-header";
import { getApiBaseUrl } from "@/lib/runtime-config";

export default function CarneLeaoPage() {
    const { activeFazendaId, isVisaoGrupo } = useAppStore();
    const currentYear = new Date().getFullYear();
    const [ano, setAno] = useState(currentYear);
    const [downloading, setDownloading] = useState(false);

    const anos = Array.from({ length: 6 }, (_, i) => currentYear - i);

    const handleDownload = async () => {
        setDownloading(true);
        try {
            const params = new URLSearchParams({ ano: String(ano) });
            if (!isVisaoGrupo && activeFazendaId) {
                params.set("unidade_produtiva_id", activeFazendaId);
            }

            const { token } = useAppStore.getState();
            const response = await fetch(
                `${getApiBaseUrl()}/financeiro/integracao/carne-leao/exportar?${params}`,
                {
                    headers: {
                        Authorization: `Bearer ${token ?? ""}`,
                    },
                }
            );

            if (!response.ok) {
                const err = await response.json().catch(() => ({}));
                throw new Error(err.detail || "Erro ao gerar arquivo.");
            }

            const blob = await response.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `carne_leao_${ano}.csv`;
            a.click();
            URL.revokeObjectURL(url);
            toast.success(`Carnê-Leão ${ano} exportado com sucesso!`);
        } catch (err: any) {
            toast.error(err.message || "Erro ao exportar.");
        } finally {
            setDownloading(false);
        }
    };

    return (
        <div className="max-w-[800px] w-full pt-4 animate-in fade-in slide-in-from-bottom-2 duration-500">
            <PageHeader
                title="Carnê-Leão / Livro Caixa"
                description="Exporte o Livro Caixa do Produtor Rural no formato compatível com a Receita Federal (RFB)."
                icon={<BookOpen className="h-8 w-8 text-primary" />}
            />

            {/* Info box */}
            <div className="flex gap-3 p-4 rounded-sm bg-blue-50 dark:bg-blue-950/30 border border-blue-200 dark:border-blue-900/50 mb-6">
                <Info size={16} className="text-blue-500 mt-0.5 shrink-0" />
                <div className="text-sm text-blue-700 dark:text-blue-300">
                    <p className="font-semibold mb-1">Sobre o Carnê-Leão</p>
                    <p>
                        O arquivo gerado é um CSV separado por ponto e vírgula contendo todas as receitas recebidas e
                        despesas pagas no ano, classificadas por categoria RFB. Use para preencher o GCAP ou entregar
                        ao contador.
                    </p>
                </div>
            </div>

            <div className="bg-surface rounded-sm shadow-[0_2px_6px_0_rgba(67,89,113,0.12)] dark:shadow-[0_2px_6px_0_rgba(0,0,0,0.16)] p-6 space-y-6">
                <div className="flex flex-col gap-1.5">
                    <label className="text-xs font-semibold text-foreground/70 uppercase tracking-wider">
                        Ano de Competência
                    </label>
                    <select
                        value={ano}
                        onChange={e => setAno(Number(e.target.value))}
                        className="w-40 rounded-sm border border-border-subtle bg-transparent px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition-all"
                    >
                        {anos.map(a => (
                            <option key={a} value={a}>{a}</option>
                        ))}
                    </select>
                </div>

                {!isVisaoGrupo && !activeFazendaId && (
                    <p className="text-sm text-amber-600 dark:text-amber-400">
                        ⚠ Selecione uma fazenda no topo da página para filtrar por propriedade, ou deixe sem filtro para exportar todas.
                    </p>
                )}

                <div className="border-t border-border-subtle pt-4">
                    <p className="text-sm text-foreground/60 mb-4">
                        Serão incluídos: receitas com status <strong>RECEBIDO</strong> e despesas com status <strong>PAGO</strong>
                        {!isVisaoGrupo && activeFazendaId ? " da fazenda selecionada" : " de todas as fazendas"} no ano de <strong>{ano}</strong>.
                    </p>

                    <button
                        onClick={handleDownload}
                        disabled={downloading}
                        className="flex items-center gap-2 px-6 py-2.5 rounded-sm bg-primary text-white text-sm font-semibold hover:brightness-110 active:scale-95 transition-all disabled:opacity-60 shadow-[0_2px_8px_0_rgba(115,103,240,0.4)]"
                    >
                        {downloading
                            ? <Loader2 size={16} className="animate-spin" />
                            : <FileDown size={16} />
                        }
                        {downloading ? "Gerando arquivo..." : `Baixar Carnê-Leão ${ano} (.csv)`}
                    </button>
                </div>
            </div>

            {/* Columns preview */}
            <div className="mt-6 bg-surface rounded-sm shadow-[0_2px_6px_0_rgba(67,89,113,0.12)] dark:shadow-[0_2px_6px_0_rgba(0,0,0,0.16)] p-5">
                <p className="text-xs font-semibold text-foreground/70 uppercase tracking-wider mb-3">Colunas do arquivo CSV</p>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                    {["Competência", "Tipo (RECEITA/DESPESA)", "Categoria RFB", "Descrição", "Valor (R$)", "NF / Documento", "Pagador/Recebedor"].map(col => (
                        <div key={col} className="px-2.5 py-1.5 rounded bg-neutral-100 dark:bg-neutral-800 text-xs font-mono text-foreground/70">
                            {col}
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}
