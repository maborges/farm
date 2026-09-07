"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter,
  DialogBody,
} from "@/components/ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { toast } from "sonner";
import { Plus, Trash2, Lock } from "lucide-react";
import { apiFetch } from "@/lib/api";

const TIPOS = [
  { value: "despesa", label: "Despesas" },
  { value: "receita", label: "Receitas" },
  { value: "operacao", label: "Operações" },
  { value: "produto", label: "Produtos" },
  { value: "insumo", label: "Insumos" },
];

interface Categoria {
  id: string;
  tipo: string;
  nome: string;
  slug: string;
  parent_id: string | null;
  is_system: boolean;
  is_active: boolean;
  ordem: number;
  cor_hex: string | null;
  icone: string | null;
}

interface NovaCategoriaForm {
  nome: string;
  parent_id: string;
  cor_hex: string;
}

export function CategoriasManager() {
  const queryClient = useQueryClient();
  const [tipoAtivo, setTipoAtivo] = useState("despesa");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [novaCategoria, setNovaCategoria] = useState<NovaCategoriaForm>({
    nome: "",
    parent_id: "",
    cor_hex: "",
  });

  const { data: categorias = [], isLoading } = useQuery<Categoria[]>({
    queryKey: ["categorias", tipoAtivo],
    queryFn: () => apiFetch(`config/categorias/${tipoAtivo}?apenas_ativas=false`),
  });

  const criarMutation = useMutation({
    mutationFn: (data: Record<string, unknown>) =>
      apiFetch("config/categorias", {
        method: "POST",
        body: JSON.stringify({ tipo: tipoAtivo, ...data }),
      }),
    onSuccess: () => {
      toast.success("Categoria criada");
      queryClient.invalidateQueries({ queryKey: ["categorias", tipoAtivo] });
      setDialogOpen(false);
      setNovaCategoria({ nome: "", parent_id: "", cor_hex: "" });
    },
    onError: (e: Error) => toast.error(e.message || "Erro ao criar categoria"),
  });

  const removerMutation = useMutation({
    mutationFn: (id: string) =>
      apiFetch(`config/categorias/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      toast.success("Categoria inativada");
      queryClient.invalidateQueries({ queryKey: ["categorias", tipoAtivo] });
    },
    onError: (e: Error) => toast.error(e.message || "Erro ao remover categoria"),
  });

  // Separar raízes e filhos
  const raizes = categorias.filter((c) => !c.parent_id);
  const filhos = (parentId: string) => categorias.filter((c) => c.parent_id === parentId);

  return (
    <div className="space-y-4">
      {/* Seletor de tipo */}
      <div className="flex gap-2 flex-wrap">
        {TIPOS.map((t) => (
          <Button
            key={t.value}
            size="sm"
            variant={tipoAtivo === t.value ? "default" : "outline"}
            onClick={() => setTipoAtivo(t.value)}
            className="rounded-sm"
          >
            {t.label}
          </Button>
        ))}
      </div>

      {/* Lista de categorias */}
      <div className="border rounded-sm divide-y">
        {isLoading ? (
          <div className="p-4 animate-pulse h-32 bg-muted rounded-sm" />
        ) : raizes.length === 0 ? (
          <div className="p-8 text-center text-muted-foreground text-sm">
            Nenhuma categoria cadastrada. Clique em "Nova Categoria" para começar.
          </div>
        ) : (
          raizes.map((cat) => (
            <div key={cat.id}>
              <CategoriaRow
                categoria={cat}
                onRemover={() => removerMutation.mutate(cat.id)}
              />
              {filhos(cat.id).map((filho) => (
                <CategoriaRow
                  key={filho.id}
                  categoria={filho}
                  nivel={1}
                  onRemover={() => removerMutation.mutate(filho.id)}
                />
              ))}
            </div>
          ))
        )}
      </div>

      {/* Botão nova categoria */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogTrigger asChild>
          <Button variant="outline" size="sm" className="rounded-sm">
            <Plus className="w-4 h-4 mr-1" />
            Nova Categoria
          </Button>
        </DialogTrigger>
        <DialogContent className="sm:max-w-[425px] rounded-sm p-0">
          <DialogHeader className="border-b px-4 py-2.5">
            <DialogTitle>Nova Categoria de {TIPOS.find((t) => t.value === tipoAtivo)?.label}</DialogTitle>
          </DialogHeader>
          <DialogBody className="space-y-4 px-4 py-3">
            <div className="space-y-1.5">
              <Label>Nome</Label>
              <Input
                value={novaCategoria.nome}
                onChange={(e) => setNovaCategoria((f) => ({ ...f, nome: e.target.value }))}
                placeholder="Ex: Energia Elétrica"
                className="h-8 rounded-sm"
              />
            </div>
            <div className="space-y-1.5">
              <Label>Categoria Pai (opcional)</Label>
              <Select
                value={novaCategoria.parent_id || "none"}
                onValueChange={(v) => setNovaCategoria((f) => ({ ...f, parent_id: v === "none" ? "" : v }))}
              >
                <SelectTrigger className="h-8 rounded-sm">
                  <SelectValue placeholder="Categoria raiz" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">— Categoria raiz —</SelectItem>
                  {raizes
                    .filter((c) => c.is_active)
                    .map((c) => (
                      <SelectItem key={c.id} value={c.id}>
                        {c.nome}
                      </SelectItem>
                    ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label>Cor (opcional)</Label>
              <div className="flex gap-2 items-center">
                <Input
                  type="color"
                  value={novaCategoria.cor_hex || "#6366f1"}
                  onChange={(e) => setNovaCategoria((f) => ({ ...f, cor_hex: e.target.value }))}
                  className="w-12 h-8 p-1 cursor-pointer rounded-sm"
                />
                <Input
                  value={novaCategoria.cor_hex}
                  onChange={(e) => setNovaCategoria((f) => ({ ...f, cor_hex: e.target.value }))}
                  placeholder="#6366f1"
                  className="h-8 rounded-sm font-mono"
                />
              </div>
            </div>
          </DialogBody>
          <DialogFooter className="border-t px-4 py-2.5">
            <div className="flex justify-end gap-2 w-full">
              <Button variant="outline" size="sm" onClick={() => setDialogOpen(false)}>
                Cancelar
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() =>
                  criarMutation.mutate({
                    nome: novaCategoria.nome,
                    parent_id: novaCategoria.parent_id || null,
                    cor_hex: novaCategoria.cor_hex || null,
                  })
                }
                disabled={!novaCategoria.nome || criarMutation.isPending}
              >
                {criarMutation.isPending ? "Criando..." : "Criar"}
              </Button>
            </div>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function CategoriaRow({
  categoria,
  nivel = 0,
  onRemover,
}: {
  categoria: Categoria;
  nivel?: number;
  onRemover: () => void;
}) {
  return (
    <div
      className={`flex items-center justify-between p-3 ${nivel > 0 ? "pl-8 bg-muted/30" : ""} ${!categoria.is_active ? "opacity-50" : ""}`}
    >
      <div className="flex items-center gap-2">
        {categoria.cor_hex && (
          <span
            className="w-3 h-3 rounded-full flex-shrink-0"
            style={{ backgroundColor: categoria.cor_hex }}
          />
        )}
        <span className="text-sm">{categoria.nome}</span>
        {categoria.is_system && (
          <Badge variant="secondary" className="text-xs gap-1">
            <Lock className="w-2.5 h-2.5" />
            Sistema
          </Badge>
        )}
        {!categoria.is_active && (
          <Badge variant="outline" className="text-xs text-muted-foreground">
            Inativa
          </Badge>
        )}
      </div>
      {!categoria.is_system && categoria.is_active && (
        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7 text-muted-foreground hover:text-destructive"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Inativar categoria?</AlertDialogTitle>
              <AlertDialogDescription>
                Tem certeza que deseja inativar a categoria "{categoria.nome}"? Ela não será mais exibida nas novas seleções.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancelar</AlertDialogCancel>
              <AlertDialogAction onClick={onRemover}>
                Inativar
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      )}
    </div>
  );
}
