"use client";

import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Search, Package } from "lucide-react";
import { cn } from "@/lib/utils";

export interface ProdutoComboboxItem {
  id: string;
  nome: string;
  preco_medio?: number | null;
  unidade_medida?: string | null;
}

export function ProdutoCombobox({ value, onChange, onSelectProduto, className }: {
  value: string;
  onChange: (produtoId: string) => void;
  onSelectProduto?: (produto: ProdutoComboboxItem) => void;
  className?: string;
}) {
  const [aberto, setAberto] = useState(false);
  const [termo, setTermo] = useState("");
  const containerRef = useRef<HTMLDivElement>(null);

  const { data: produtos = [], isFetching } = useQuery<ProdutoComboboxItem[]>({
    queryKey: ["produtos-busca", termo],
    queryFn: () => apiFetch(`/cadastros/produtos?q=${encodeURIComponent(termo)}&incluir_sistema=true`),
    enabled: aberto,
    staleTime: 30_000,
  });

  const selecionado = produtos.find(p => p.id === value);

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
          placeholder="Buscar produto por nome"
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
            {!isFetching && produtos.length === 0 && (
              <p className="px-3 py-2 text-xs text-muted-foreground">
                Nenhum produto encontrado.
              </p>
            )}
            {produtos.map(p => (
              <button
                key={p.id}
                type="button"
                className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs hover:bg-accent"
                onClick={() => { onChange(p.id); onSelectProduto?.(p); setAberto(false); }}
              >
                <Package className="size-3.5 text-muted-foreground shrink-0" />
                <span className="truncate">{p.nome}</span>
                {p.preco_medio != null && (
                  <span className="ml-auto text-muted-foreground shrink-0">
                    {p.preco_medio.toLocaleString("pt-BR", { style: "currency", currency: "BRL" })}
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
