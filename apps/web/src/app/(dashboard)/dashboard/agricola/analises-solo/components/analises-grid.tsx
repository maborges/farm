"use client";

import { DataTable, type ColumnDef } from "@/components/ui/data-table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { FlaskConical, BookOpen, Trash2, Pencil } from "lucide-react";

interface AnaliseSolo {
    id: string;
    talhao_id: string;
    talhao_nome?: string | null;
    data_coleta: string;
    laboratorio?: string;
    profundidade_cm?: number;
    ph_agua?: number;
    v_pct?: number;
    fosforo_p?: number;
    created_at: string;
}

interface AnalisesGridProps {
    data: AnaliseSolo[];
    onView: (id: string) => void;
    onEdit: (id: string) => void;
    onDelete: (id: string) => void;
    getTalhaoNome: (id: string) => string;
}

export function AnalisesGrid({ data, onView, onEdit, onDelete, getTalhaoNome }: AnalisesGridProps) {
    // Calcula status baseado na idade da análise
    function getStatus(dataColeta: string) {
        const hoje = new Date();
        const data = new Date(dataColeta);
        const meses = (hoje.getFullYear() - data.getFullYear()) * 12 + (hoje.getMonth() - data.getMonth());

        if (meses <= 12) return { status: "Válida", color: "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/20 dark:text-emerald-400", badge: "🟢" };
        if (meses <= 18) return { status: "Atenção", color: "bg-yellow-50 text-yellow-700 dark:bg-yellow-950/20 dark:text-yellow-400", badge: "🟡" };
        return { status: "Inválida", color: "bg-red-50 text-red-700 dark:bg-red-950/20 dark:text-red-400", badge: "🔴" };
    }

    const columns: ColumnDef<AnaliseSolo>[] = [
        {
            id: "talhao",
            header: "Talhão / Área",
            accessorFn: (row) => row.talhao_nome ?? getTalhaoNome(row.talhao_id),
            cell: (value: string, row: AnaliseSolo) => {
                const vPct = row.v_pct ?? 0;
                const precisaCalagem = vPct > 0 && vPct < 60;
                const nomeTalhao = row.talhao_nome ?? value ?? "Talhão não informado";
                return (
                    <div className="flex items-center gap-3">
                        <div className={`size-7 rounded-sm shrink-0 flex items-center justify-center ${precisaCalagem ? "bg-red-50 text-red-600 dark:bg-red-950/20" : "bg-emerald-50 text-emerald-600 dark:bg-emerald-950/20"}`}>
                            <FlaskConical size={13} />
                        </div>
                        <div>
                            <p className="font-medium text-foreground text-sm">{nomeTalhao}</p>
                            <p className="text-xs text-muted-foreground">{row.laboratorio ?? "Laboratório não informado"}</p>
                        </div>
                    </div>
                );
            },
            sortable: true,
            filterable: true,
            filterPlaceholder: "Filtrar talhão...",
        },
        {
            id: "data_coleta",
            header: "Data de Coleta",
            accessorKey: "data_coleta",
            cell: (value: string, row: AnaliseSolo) => (
                <div>
                    <p className="text-sm tabular-nums">
                        {new Date(value).toLocaleDateString("pt-BR")}
                    </p>
                    {row.profundidade_cm && (
                        <p className="text-xs text-muted-foreground">{row.profundidade_cm} cm profundidade</p>
                    )}
                </div>
            ),
            sortable: true,
            exportFormat: (value: string) => new Date(value).toLocaleDateString("pt-BR"),
        },
        {
            id: "status",
            header: "Situação",
            accessorFn: (row) => getStatus(row.data_coleta).status,
            cell: (_value: string, row: AnaliseSolo) => {
                const { badge, status, color } = getStatus(row.data_coleta);
                return (
                    <Badge variant="secondary" className={`${color} border-transparent font-medium`}>
                        {badge} {status}
                    </Badge>
                );
            },
            sortable: true,
            filterable: true,
            exportFormat: (value: string) => value,
        },
        {
            id: "ph_agua",
            header: "pH (H₂O)",
            accessorKey: "ph_agua",
            cell: (value: number | undefined) => (
                <span className="font-mono text-sm">{value?.toFixed(1) ?? "-"}</span>
            ),
            sortable: true,
            exportFormat: (v: number | undefined) => v?.toFixed(1) ?? "-",
        },
        {
            id: "v_pct",
            header: "V% (Sat. Bases)",
            accessorKey: "v_pct",
            cell: (value: number | undefined) => {
                const precisaCalagem = (value ?? 0) > 0 && (value ?? 0) < 60;
                if (value == null) return <span className="text-muted-foreground">-</span>;
                return (
                    <Badge
                        variant="secondary"
                        className={
                            precisaCalagem
                                ? "bg-red-50 text-red-700 border-transparent dark:bg-red-950/20 dark:text-red-400"
                                : "bg-primary/10 text-primary border-transparent"
                        }
                    >
                        {value.toFixed(0)}%
                    </Badge>
                );
            },
            sortable: true,
            exportFormat: (v: number | undefined) => v != null ? `${v.toFixed(0)}%` : "-",
        },
        {
            id: "fosforo_p",
            header: "P (mg/dm³)",
            accessorKey: "fosforo_p",
            cell: (value: number | undefined) => (
                <span className="font-mono text-sm">{value?.toFixed(1) ?? "-"}</span>
            ),
            sortable: true,
            exportFormat: (v: number | undefined) => v?.toFixed(1) ?? "-",
        },
        {
            id: "acoes",
            header: "",
            accessorKey: "id",
            sortable: false,
            filterable: false,
            exportable: false,
            cell: (id: string, row: AnaliseSolo) => (
                <div className="flex items-center gap-0 justify-end">
                    <Button
                        variant="ghost"
                        size="icon"
                        className="size-7 text-primary hover:text-primary hover:bg-primary/10"
                        title="Visualizar Laudo"
                        onClick={(e) => { e.stopPropagation(); onView(id); }}
                    >
                        <BookOpen className="size-3.5" />
                    </Button>
                    <Button
                        variant="ghost"
                        size="icon"
                        className="size-7 text-primary hover:text-primary hover:bg-primary/10"
                        title="Editar"
                        onClick={(e) => { e.stopPropagation(); onEdit(id); }}
                    >
                        <Pencil className="size-3.5" />
                    </Button>
                    <Button
                        variant="ghost"
                        size="icon"
                        className="size-7 text-destructive hover:text-destructive hover:bg-destructive/10"
                        title="Excluir"
                        onClick={(e) => {
                            e.stopPropagation();
                            onDelete(id);
                        }}
                    >
                        <Trash2 className="size-4" />
                    </Button>
                </div>
            ),
        },
    ];

    return (
        <DataTable
            data={data}
            columns={columns}
            searchable
            searchPlaceholder="Buscar por talhão, laboratório..."
            exportable
            exportFileName="analises-solo"
            emptyMessage="Nenhum laudo encontrado. Registre uma nova amostragem."
        />
    );
}
