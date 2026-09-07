// components/shared/fazendas-selector.tsx
// Componente para seleção de fazendas com checkboxes

"use client";

import { useEffect, useState } from "react";
import { Check, Loader2 } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ScrollArea } from "@/components/ui/scroll-area";
import type { UnidadeProdutiva } from "@/types/global";
import { apiFetch } from "@/lib/api";
import { useAppStore } from "@/lib/stores/app-store";

interface FazendasSelectorProps {
    /** IDs de fazendas pré-selecionadas */
    selectedIds?: string[];
    /** Callback quando seleção muda */
    onChange?: (fazendaIds: string[]) => void;
    /** Se deve desabilitar o componente */
    disabled?: boolean;
    /** Mostrar apenas fazendas não selecionadas */
    availableOnly?: boolean;
    /** Altura máxima do scroll area */
    maxHeight?: string;
}

/**
 * Componente de seleção múltipla de fazendas.
 * Permite busca e seleção com checkboxes.
 */
export function FazendaSelector({
    selectedIds = [],
    onChange,
    disabled = false,
    availableOnly = false,
    maxHeight = "300px",
}: FazendasSelectorProps) {
    const [fazendas, setFazendas] = useState<UnidadeProdutiva[]>([]);
    const [filteredFazendas, setFilteredFazendas] = useState<UnidadeProdutiva[]>([]);
    const [loading, setLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState("");
    const [selected, setSelected] = useState<Set<string>>(new Set(selectedIds));
    const tenantId = useAppStore((s) => s.tenant?.id);
    const hasHydrated = useAppStore((s) => s._hasHydrated);

    useEffect(() => {
        if (!hasHydrated || !tenantId) {
            setFazendas([]);
            setFilteredFazendas([]);
            setLoading(false);
            return;
        }

        const fetchFazendas = async () => {
            try {
                const data = await apiFetch<UnidadeProdutiva[]>("/unidades-produtivas");
                setFazendas(data);
            } finally {
                setLoading(false);
            }
        };

        fetchFazendas();
    }, [hasHydrated, tenantId]);

    useEffect(() => {
        setSelected(new Set(selectedIds));
    }, [selectedIds]);

    useEffect(() => {
        const filtered = fazendas.filter((f) => {
            const matchesSearch =
                f.nome.toLowerCase().includes(searchTerm.toLowerCase()) ||
                (f.municipio?.toLowerCase().includes(searchTerm.toLowerCase()) ?? false);

            const notSelected = availableOnly ? !selected.has(f.id) : true;

            return matchesSearch && notSelected;
        });

        setFilteredFazendas(filtered);
    }, [fazendas, searchTerm, selected, availableOnly]);

    const handleToggle = (fazendaId: string) => {
        const newSelected = new Set(selected);
        if (newSelected.has(fazendaId)) {
            newSelected.delete(fazendaId);
        } else {
            newSelected.add(fazendaId);
        }
        setSelected(newSelected);
        onChange?.(Array.from(newSelected));
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center py-8">
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
                Carregando fazendas...
            </div>
        );
    }

    return (
        <div className="space-y-3">
            <Input
                placeholder="Buscar fazendas..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                disabled={disabled}
                className="text-sm"
            />

            <ScrollArea style={{ maxHeight }} className="border rounded-sm p-3">
                <div className="space-y-2">
                    {filteredFazendas.length === 0 ? (
                        <p className="text-sm text-muted-foreground py-4 text-center">
                            Nenhuma fazenda encontrada.
                        </p>
                    ) : (
                        filteredFazendas.map((fazenda) => {
                            const isSelected = selected.has(fazenda.id);
                            return (
                                <label
                                    key={fazenda.id}
                                    className={`flex items-center gap-3 p-2 rounded-sm cursor-pointer transition-colors ${
                                        isSelected ? "bg-primary/10" : "hover:bg-muted/50"
                                    } ${disabled ? "opacity-50 cursor-not-allowed" : ""}`}
                                >
                                    <div
                                        className={`h-4 w-4 rounded border flex items-center justify-center transition-colors ${
                                            isSelected
                                                ? "bg-primary border-primary"
                                                : "border-muted-foreground"
                                        }`}
                                    >
                                        {isSelected && <Check size={12} className="text-primary-foreground" />}
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <p className="text-sm font-medium truncate">{fazenda.nome}</p>
                                        {fazenda.municipio && (
                                            <p className="text-xs text-muted-foreground truncate">
                                                {fazenda.municipio}
                                                {fazenda.uf ? ` - ${fazenda.uf}` : ""}
                                            </p>
                                        )}
                                    </div>
                                    <input
                                        type="checkbox"
                                        checked={isSelected}
                                        onChange={() => handleToggle(fazenda.id)}
                                        disabled={disabled}
                                        className="hidden"
                                    />
                                </label>
                            );
                        })
                    )}
                </div>
            </ScrollArea>

            {selected.size > 0 && (
                <p className="text-xs text-muted-foreground">
                    {selected.size} fazenda{selected.size !== 1 ? "s" : ""} selecionada{selected.size !== 1 ? "s" : ""}
                </p>
            )}
        </div>
    );
}
