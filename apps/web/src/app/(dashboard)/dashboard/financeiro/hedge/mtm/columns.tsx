"use client";

import { ColumnDef } from "@/components/ui/data-table";
import { HedgePositionSnapshot } from "../types";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";

export type EnrichedSnapshot = HedgePositionSnapshot & {
    nome_safra: string;
    nome_contrato: string;
    nome_commodity: string;
};

export const columns: ColumnDef<EnrichedSnapshot>[] = [
    {
        id: "data_referencia",
        accessorKey: "data_referencia",
        header: "Data (D-0)",
        cell: ({ row }) => format(new Date(row.original.data_referencia), "dd/MM/yyyy")
    },
    {
        id: "nome_contrato",
        accessorKey: "nome_contrato",
        header: "Contrato",
    },
    {
        id: "nome_safra",
        accessorKey: "nome_safra",
        header: "Safra",
    },
    {
        id: "quantidade_aberta",
        accessorKey: "quantidade_aberta",
        header: "Qtd. Aberta",
        cell: ({ row }) => `${row.original.quantidade_aberta.toLocaleString("pt-BR")} ${row.original.unidade}`
    },
    {
        id: "preco_contratado",
        accessorKey: "preco_contratado",
        header: "Preço Travado",
        cell: (val, row) => row.preco_contratado.toLocaleString("pt-BR", { style: "currency", currency: row.moeda })
    },
    {
        id: "preco_mercado",
        accessorKey: "preco_mercado",
        header: "Mercado (Fechamento)",
        cell: (val, row) => row.preco_mercado.toLocaleString("pt-BR", { style: "currency", currency: row.moeda })
    },
    {
        id: "mtm_valor",
        accessorKey: "mtm_valor",
        header: "MtM (PnL)",
        cell: (val, row) => {
            const isNegative = row.mtm_valor < 0;
            return (
                <span className={`font-semibold ${isNegative ? "text-red-600" : "text-emerald-600"}`}>
                    {row.mtm_valor.toLocaleString("pt-BR", { style: "currency", currency: row.moeda })}
                </span>
            );
        }
    },
    {
        id: "fonte_preco",
        accessorKey: "fonte_preco",
        header: "Fonte",
    }
];
