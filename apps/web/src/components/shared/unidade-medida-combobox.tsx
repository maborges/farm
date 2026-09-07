"use client";

import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Search, Ruler } from "lucide-react";
import { cn } from "@/lib/utils";

export interface UnidadeMedidaComboboxItem {
  id: string;
  codigo: string;
  nome: string;
  dimensao: string;
}

/**
 * Combobox de unidade de medida — busca no catálogo canônico
 * (`unidades_medida`, exposto via GET /unidades-medida), incluindo unidades
 * globais do sistema (tenant_id NULL) e unidades específicas do tenant.
 * Diferente do CulturaCombobox, aqui o valor selecionado é o ID (UUID) da
 * unidade, pois os campos de destino têm FK real (unidade_medida_id).
 */
export function UnidadeMedidaCombobox({
  value,
  onChange,
  dimensao,
  className,
  placeholder = "Buscar unidade por nome ou código",
  fallbackLabel,
}: {
  value: string | null | undefined;
  onChange: (unidadeId: string, unidade?: UnidadeMedidaComboboxItem) => void;
  dimensao?: string;
  className?: string;
  placeholder?: string;
  /** Texto legado (campo string livre) exibido quando ainda não há unidade_medida_id salvo. */
  fallbackLabel?: string;
}) {
  const [aberto, setAberto] = useState(false);
  const [termo, setTermo] = useState("");
  const containerRef = useRef<HTMLDivElement>(null);

  const { data: unidades = [], isFetching } = useQuery<UnidadeMedidaComboboxItem[]>({
    queryKey: ["unidades-medida-busca", termo, dimensao],
    queryFn: () => {
      const params = new URLSearchParams();
      if (termo) params.set("q", termo);
      if (dimensao) params.set("dimensao", dimensao);
      return apiFetch(`/unidades-medida?${params.toString()}`);
    },
    enabled: aberto,
    staleTime: 30_000,
  });

  // Resolve o nome da unidade já salva mesmo sem o dropdown estar aberto
  // (a busca acima só roda com aberto=true, então sozinha não recupera o valor persistido).
  const { data: unidadeSelecionada } = useQuery<UnidadeMedidaComboboxItem>({
    queryKey: ["unidade-medida", value],
    queryFn: () => apiFetch(`/unidades-medida/${value}`),
    enabled: !!value,
    staleTime: 60_000,
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

  const selecionada = unidades.find(u => u.id === value) ?? unidadeSelecionada;
  const labelExibido = aberto ? termo : (selecionada?.nome ?? "");
  const placeholderExibido = !value && fallbackLabel ? `${placeholder} (atual: ${fallbackLabel})` : placeholder;

  return (
    <div ref={containerRef} className={cn("relative", className)}>
      <div className="relative">
        <Search className="absolute left-2 top-1/2 -translate-y-1/2 size-3.5 text-muted-foreground" />
        <Input
          placeholder={placeholderExibido}
          className="h-9 rounded-sm text-xs pl-7"
          value={labelExibido}
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
            {!isFetching && unidades.length === 0 && (
              <p className="px-3 py-2 text-xs text-muted-foreground">
                Nenhuma unidade encontrada.
              </p>
            )}
            {unidades.map(u => (
              <button
                key={u.id}
                type="button"
                className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs hover:bg-accent"
                onClick={() => { onChange(u.id, u); setAberto(false); }}
              >
                <Ruler className="size-3.5 text-muted-foreground shrink-0" />
                <span className="truncate">{u.nome}</span>
                <span className="ml-auto text-muted-foreground">{u.codigo}</span>
              </button>
            ))}
          </ScrollArea>
        </div>
      )}
    </div>
  );
}
