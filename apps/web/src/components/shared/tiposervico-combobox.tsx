"use client";

import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Search, Wrench } from "lucide-react";
import { cn } from "@/lib/utils";

export interface TipoServicoComboboxItem {
  id: string;
  nome: string;
  unidade_medida?: string | null;
  custo_referencia?: number | null;
}

export function TipoServicoCombobox({ value, onChange, onSelectTipoServico, className }: {
  value: string;
  onChange: (tipoServicoId: string) => void;
  onSelectTipoServico?: (tipoServico: TipoServicoComboboxItem) => void;
  className?: string;
}) {
  const [aberto, setAberto] = useState(false);
  const [termo, setTermo] = useState("");
  const containerRef = useRef<HTMLDivElement>(null);

  const { data: tiposServico = [], isFetching } = useQuery<TipoServicoComboboxItem[]>({
    queryKey: ["tipos-servico-busca", termo],
    queryFn: () => apiFetch(`/cadastros/tipos-servico?q=${encodeURIComponent(termo)}`),
    enabled: aberto,
    staleTime: 30_000,
  });

  const selecionado = tiposServico.find(t => t.id === value);

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
          placeholder="Buscar tipo de serviço por nome"
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
            {!isFetching && tiposServico.length === 0 && (
              <p className="px-3 py-2 text-xs text-muted-foreground">
                Nenhum tipo de serviço encontrado.
              </p>
            )}
            {tiposServico.map(t => (
              <button
                key={t.id}
                type="button"
                className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs hover:bg-accent"
                onClick={() => { onChange(t.id); onSelectTipoServico?.(t); setAberto(false); }}
              >
                <Wrench className="size-3.5 text-muted-foreground shrink-0" />
                <span className="truncate">{t.nome}</span>
                {t.custo_referencia != null && (
                  <span className="ml-auto text-muted-foreground shrink-0">
                    {t.custo_referencia.toLocaleString("pt-BR", { style: "currency", currency: "BRL" })}
                  </span>
                )}
              </button>
            ))}
          </ScrollArea>
        </div>
      )}
    </div>
  );
}
