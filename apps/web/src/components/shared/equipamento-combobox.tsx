"use client";

import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Search, Tractor } from "lucide-react";
import { cn } from "@/lib/utils";

export interface EquipamentoComboboxItem {
  id: string;
  nome: string;
  tipo?: string | null;
}

export function EquipamentoCombobox({ value, onChange, onSelectEquipamento, tiposPermitidos, placeholder, className }: {
  value: string;
  onChange: (equipamentoId: string) => void;
  onSelectEquipamento?: (equipamento: EquipamentoComboboxItem) => void;
  tiposPermitidos?: string[];
  placeholder?: string;
  className?: string;
}) {
  const [aberto, setAberto] = useState(false);
  const [termo, setTermo] = useState("");
  const containerRef = useRef<HTMLDivElement>(null);

  const { data: todosEquipamentos = [], isFetching } = useQuery<EquipamentoComboboxItem[]>({
    queryKey: ["equipamentos-busca", termo],
    queryFn: () => apiFetch(`/cadastros/equipamentos?q=${encodeURIComponent(termo)}`),
    enabled: aberto,
    staleTime: 30_000,
  });

  // Filtro por tipo é feito no cliente: o endpoint só aceita um `tipo` por vez,
  // e aqui precisamos permitir mais de um tipo simultaneamente (ex: máquina
  // aceita TRATOR + COLHEDORA + PULVERIZADOR + PLANTADEIRA).
  const equipamentos = tiposPermitidos?.length
    ? todosEquipamentos.filter(e => e.tipo && tiposPermitidos.includes(e.tipo))
    : todosEquipamentos;

  const selecionado = equipamentos.find(e => e.id === value);

  useEffect(() => {
    function handleClickFora(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setAberto(false);
      }
    }
    document.addEventListener("mousedown", handleClickFora);
    return () => document.removeEventListener("mousedown", handleClickFora);
  }, []);

  return (
    <div ref={containerRef} className={cn("relative", className)}>
      <div className="relative">
        <Search className="absolute left-2 top-1/2 -translate-y-1/2 size-3.5 text-muted-foreground" />
        <Input
          placeholder={placeholder ?? "Buscar máquina por nome"}
          className="h-9 rounded-sm text-xs pl-7"
          value={aberto ? termo : (selecionado?.nome ?? "")}
          onFocus={() => { setAberto(true); setTermo(""); }}
          onChange={e => setTermo(e.target.value)}
        />
      </div>
      {aberto && (
        <div className="absolute z-50 mt-1 w-full rounded-sm border bg-popover shadow-md">
          <ScrollArea className="max-h-48">
            {isFetching && (
              <p className="px-3 py-2 text-xs text-muted-foreground">Buscando...</p>
            )}
            {!isFetching && equipamentos.length === 0 && (
              <p className="px-3 py-2 text-xs text-muted-foreground">
                Nenhuma máquina encontrada.
              </p>
            )}
            {equipamentos.map(e => (
              <button
                key={e.id}
                type="button"
                className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs hover:bg-accent"
                onClick={() => { onChange(e.id); onSelectEquipamento?.(e); setAberto(false); }}
              >
                <Tractor className="size-3.5 text-muted-foreground shrink-0" />
                <span className="truncate">{e.nome}</span>
                {e.tipo && (
                  <span className="ml-auto text-muted-foreground shrink-0">{e.tipo}</span>
                )}
              </button>
            ))}
          </ScrollArea>
        </div>
      )}
    </div>
  );
}
