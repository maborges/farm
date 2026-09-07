"use client";

import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Search, Sprout } from "lucide-react";
import { cn } from "@/lib/utils";

export interface CulturaComboboxItem {
  id: string;
  nome: string;
  grupo?: string | null;
}

/**
 * Combobox de cultura — busca no catálogo canônico de culturas do tenant
 * (`cadastros_culturas`, exposto via GET /cadastros/culturas). Diferente do
 * ProdutoCombobox, o valor selecionado aqui é o NOME da cultura (string),
 * não o id, pois campos como PhaseTemplate.cultura/OperationTemplate.cultura
 * armazenam o nome livre para permitir "aplica a todas as culturas" (null).
 */
export function CulturaCombobox({ value, onChange, className }: {
  value: string;
  onChange: (nomeCultura: string) => void;
  className?: string;
}) {
  const [aberto, setAberto] = useState(false);
  const [termo, setTermo] = useState("");
  const containerRef = useRef<HTMLDivElement>(null);

  const { data: culturas = [], isFetching } = useQuery<CulturaComboboxItem[]>({
    queryKey: ["culturas-busca", termo],
    queryFn: () => apiFetch(`/cadastros/culturas?q=${encodeURIComponent(termo)}`),
    enabled: aberto,
    staleTime: 30_000,
  });

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
          placeholder="Buscar cultura por nome"
          className="h-9 rounded-sm text-xs pl-7"
          value={aberto ? termo : (value ?? "")}
          onFocus={() => { setAberto(true); setTermo(""); }}
          onChange={e => { setTermo(e.target.value); onChange(e.target.value); }}
        />
      </div>
      {aberto && (
        <div className="absolute z-50 mt-1 w-full rounded-sm border bg-popover shadow-md">
          <ScrollArea className="max-h-48">
            {isFetching && (
              <p className="px-3 py-2 text-xs text-muted-foreground">Buscando...</p>
            )}
            {!isFetching && culturas.length === 0 && (
              <p className="px-3 py-2 text-xs text-muted-foreground">
                Nenhuma cultura encontrada.
              </p>
            )}
            {culturas.map(c => (
              <button
                key={c.id}
                type="button"
                className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs hover:bg-accent"
                onClick={() => { onChange(c.nome); setAberto(false); }}
              >
                <Sprout className="size-3.5 text-muted-foreground shrink-0" />
                <span className="truncate">{c.nome}</span>
              </button>
            ))}
          </ScrollArea>
        </div>
      )}
    </div>
  );
}
