"use client";

import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Search, User } from "lucide-react";
import { cn } from "@/lib/utils";

export interface ColaboradorComboboxItem {
  id: string;
  pessoa_id: string;
  nome: string;
  tipo_contrato?: string | null;
}

export function ColaboradorCombobox({ value, onChange, onSelectColaborador, valueKey = "id", className }: {
  value: string;
  onChange: (colaboradorId: string) => void;
  onSelectColaborador?: (colaborador: ColaboradorComboboxItem) => void;
  valueKey?: "id" | "pessoa_id";
  className?: string;
}) {
  const [aberto, setAberto] = useState(false);
  const [termo, setTermo] = useState("");
  const containerRef = useRef<HTMLDivElement>(null);

  const { data: colaboradores = [], isFetching } = useQuery<ColaboradorComboboxItem[]>({
    queryKey: ["colaboradores-busca", termo],
    queryFn: () => apiFetch(`/rh/colaboradores?q=${encodeURIComponent(termo)}`),
    enabled: aberto,
    staleTime: 30_000,
  });

  const selecionado = colaboradores.find(c => c[valueKey] === value);

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
          placeholder="Buscar pessoa por nome"
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
            {!isFetching && colaboradores.length === 0 && (
              <p className="px-3 py-2 text-xs text-muted-foreground">
                Nenhuma pessoa encontrada.
              </p>
            )}
            {colaboradores.map(c => (
              <button
                key={c.id}
                type="button"
                className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs hover:bg-accent"
                onClick={() => { onChange(c[valueKey]); onSelectColaborador?.(c); setAberto(false); }}
              >
                <User className="size-3.5 text-muted-foreground shrink-0" />
                <span className="truncate">{c.nome}</span>
                {c.tipo_contrato && (
                  <span className="ml-auto text-muted-foreground shrink-0">{c.tipo_contrato}</span>
                )}
              </button>
            ))}
          </ScrollArea>
        </div>
      )}
    </div>
  );
}
