"use client";

import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { Skeleton } from "@/components/ui/skeleton";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Search, User2, Building2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface TipoRel {
  id: string;
  nome: string;
  cor: string;
}

interface Pessoa {
  id: string;
  tipo: "PF" | "PJ";
  nome_exibicao: string;
  base_legal: string;
  ativo: boolean;
  anonimizado_em: string | null;
  relacionamentos: { id: string; tipo: TipoRel }[];
}

interface Props {
  value?: string | null;
  onChange: (value: string | null) => void;
  disabled?: boolean;
  placeholder?: string;
  unidadeProdutivaId?: string;
  dataReferencia?: string;
  tiposRelacionamento?: string[];
  className?: string;
}

export function PessoaSelect({ 
  value, 
  onChange, 
  disabled, 
  placeholder = "Selecione a pessoa...", 
  unidadeProdutivaId, 
  dataReferencia,
  tiposRelacionamento,
  className
}: Props) {
  const [aberto, setAberto] = React.useState(false);
  const [termo, setTermo] = React.useState("");
  const containerRef = React.useRef<HTMLDivElement>(null);

  const queryParams = new URLSearchParams();
  queryParams.append("ativo", "true");
  if (unidadeProdutivaId) {
    queryParams.append("unidade_produtiva_id", unidadeProdutivaId);
  }
  if (dataReferencia) {
    queryParams.append("data_referencia", dataReferencia);
  }

  const { data: pessoas = [], isLoading } = useQuery<Pessoa[]>({
    queryKey: ["pessoas", "ativo", unidadeProdutivaId, dataReferencia],
    queryFn: () => apiFetch(`/cadastros/pessoas?${queryParams.toString()}`),
  });

  const pessoasElegiveis = React.useMemo(() => {
    let filtradas = pessoas.filter((p) => !p.anonimizado_em);
    
    if (tiposRelacionamento && tiposRelacionamento.length > 0) {
       filtradas = filtradas.filter(p => 
         p.relacionamentos?.some(r => tiposRelacionamento.map(t => t.toLowerCase()).includes(r.tipo.nome.toLowerCase()))
       );
    }

    if (termo) {
       filtradas = filtradas.filter(p => p.nome_exibicao.toLowerCase().includes(termo.toLowerCase()));
    }
    
    return filtradas;
  }, [pessoas, tiposRelacionamento, termo]);

  const selecionado = pessoas.find(p => p.id === value);

  React.useEffect(() => {
    function handleClickFora(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setAberto(false);
      }
    }
    document.addEventListener("mousedown", handleClickFora);
    return () => document.removeEventListener("mousedown", handleClickFora);
  }, []);

  if (isLoading) {
    return <Skeleton className="h-8 w-full rounded-sm" />;
  }

  return (
    <div ref={containerRef} className={cn("relative", className)}>
      <div className="relative">
        <Search className="absolute left-2 top-1/2 -translate-y-1/2 size-3.5 text-muted-foreground" />
        <Input
          placeholder={placeholder}
          className="h-8 rounded-sm text-xs pl-7"
          value={aberto ? termo : (selecionado?.nome_exibicao ?? "")}
          onFocus={() => { setAberto(true); setTermo(""); }}
          onChange={e => setTermo(e.target.value)}
          disabled={disabled}
        />
      </div>
      {aberto && !disabled && (
        <div className="absolute z-50 mt-1 w-full rounded-sm border bg-popover shadow-md">
          <ScrollArea className="max-h-48">
            <button
              type="button"
              className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs hover:bg-accent text-muted-foreground italic"
              onClick={() => { onChange(null); setAberto(false); }}
            >
              Não informado / Limpar seleção
            </button>
            {pessoasElegiveis.length === 0 && (
              <p className="px-3 py-2 text-xs text-muted-foreground">
                Nenhuma pessoa encontrada.
              </p>
            )}
            {pessoasElegiveis.map(p => (
              <button
                key={p.id}
                type="button"
                className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs hover:bg-accent"
                onClick={() => { onChange(p.id); setAberto(false); }}
              >
                {p.tipo === "PJ" ? (
                  <Building2 className="size-3.5 text-muted-foreground shrink-0" />
                ) : (
                  <User2 className="size-3.5 text-muted-foreground shrink-0" />
                )}
                <span className="truncate">{p.nome_exibicao}</span>
              </button>
            ))}
          </ScrollArea>
        </div>
      )}
    </div>
  );
}
