'use client';

import * as React from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiFetch } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from '@/components/ui/dialog';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import {
  Plus, Lock, Trash2,
  Truck, UserCheck, Handshake, Wrench, HardHat,
  Landmark, Building2, ClipboardCheck, User, Tag,
  type LucideIcon,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { PageHeader } from '@/components/shared/page-header';


interface TipoRel {
  id: string;
  codigo: string;
  nome: string;
  descricao: string | null;
  cor: string;
  icone: string;
  sistema: boolean;
  ativo: boolean;
  tenant_id: string | null;
}

const ICON_MAP: Record<string, LucideIcon> = {
  'truck': Truck,
  'truck-moving': Truck,
  'user-check': UserCheck,
  'handshake': Handshake,
  'wrench': Wrench,
  'hard-hat': HardHat,
  'landmark': Landmark,
  'building-2': Building2,
  'clipboard-check': ClipboardCheck,
  'user': User,
  'tag': Tag,
};

const SISTEMA_DESCRICOES: Record<string, string> = {
  FORNECEDOR: 'Empresas ou pessoas que fornecem insumos, produtos ou serviços',
  CLIENTE: 'Compradores de produtos ou serviços da fazenda',
  PARCEIRO: 'Parceiros comerciais, integradoras ou cooperativas',
  PRESTADOR: 'Prestadores de serviços contratados pontualmente',
  TRANSPORTADORA: 'Empresas de logística e transporte',
  COLABORADOR: 'Funcionários, diaristas ou trabalhadores rurais',
  PROPRIETARIO: 'Proprietários de terras arrendadas ou parceiros rurais',
  ORGAO: 'Órgãos públicos, instituições de pesquisa ou reguladoras',
  RESPONSAVEL_TECNICO: 'Agrônomos, veterinários e outros responsáveis técnicos',
};

function TipoIcon({ icone, cor }: { icone: string; cor: string }) {
  const Icon = ICON_MAP[icone] ?? Tag;
  return (
    <div
      className="size-9 rounded-lg flex items-center justify-center shrink-0"
      style={{ backgroundColor: cor + '20' }}
    >
      <Icon className="size-4" style={{ color: cor }} />
    </div>
  );
}

function CardSkeleton() {
  return (
    <div className="flex items-start gap-3 border rounded-lg px-4 py-3">
      <div className="size-9 rounded-lg bg-muted animate-pulse shrink-0" />
      <div className="flex-1 space-y-2 pt-0.5">
        <div className="h-3.5 w-28 rounded bg-muted animate-pulse" />
        <div className="h-3 w-40 rounded bg-muted animate-pulse" />
      </div>
    </div>
  );
}

export default function TiposRelacionamentoPage() {
  const qc = useQueryClient();
  const [open, setOpen] = React.useState(false);
  const [deleteTarget, setDeleteTarget] = React.useState<TipoRel | null>(null);
  const [form, setForm] = React.useState({ codigo: '', nome: '', cor: '#6B7280', icone: 'user' });

  const { data: tipos = [], isLoading } = useQuery<TipoRel[]>({
    queryKey: ['tipos-relacionamento'],
    queryFn: () => apiFetch('/cadastros/tipos-relacionamento'),
  });

  const criar = useMutation({
    mutationFn: (data: object) =>
      apiFetch('/cadastros/tipos-relacionamento', { method: 'POST', body: JSON.stringify(data) }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['tipos-relacionamento'] });
      setOpen(false);
      setForm({ codigo: '', nome: '', cor: '#6B7280', icone: 'user' });
    },
  });

  const desativar = useMutation({
    mutationFn: (id: string) =>
      apiFetch(`/cadastros/tipos-relacionamento/${id}`, { method: 'DELETE' }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['tipos-relacionamento'] });
      setDeleteTarget(null);
    },
  });

  const sistema = tipos.filter((t) => t.sistema);
  const custom = tipos.filter((t) => !t.sistema);

  return (
    <div className="p-6 space-y-8 max-w-4xl">
      <PageHeader
        title="Tipos de Relacionamento"
        description="Defina como pessoas e empresas se relacionam com sua operação"
        icon={<Handshake className="text-primary" size={22} />}
        actions={
          <Button size="sm" onClick={() => setOpen(true)}>
            <Plus size={15} className="mr-1" />
            Novo Tipo
          </Button>
        }
      />

      {/* Sistema */}
      <section className="space-y-3">
        <div className="flex items-center gap-2">
          <h2 className="text-sm font-semibold uppercase text-muted-foreground">
            Padrões do Sistema
          </h2>
          <Badge variant="secondary" className="text-xs gap-1">
            <Lock className="size-3" />
            Somente leitura
          </Badge>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {isLoading
            ? Array.from({ length: 9 }).map((_, i) => <CardSkeleton key={i} />)
            : sistema.map((t) => (
                <div
                  key={t.id}
                  className="flex items-start gap-3 border rounded-lg px-4 py-3 bg-muted/10"
                >
                  <TipoIcon icone={t.icone} cor={t.cor} />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold truncate">{t.nome}</p>
                    <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2 text-pretty">
                      {SISTEMA_DESCRICOES[t.codigo] ?? t.codigo}
                    </p>
                  </div>
                </div>
              ))}
        </div>
      </section>

      {/* Personalizados */}
      <section className="space-y-3">
        <h2 className="text-sm font-semibold uppercase text-muted-foreground">
          Personalizados
        </h2>

        {!isLoading && custom.length === 0 ? (
          <div className="border border-dashed rounded-lg p-8 text-center space-y-2">
            <Tag className="size-8 mx-auto text-muted-foreground/40" />
            <p className="text-sm text-muted-foreground text-balance">
              Nenhum tipo personalizado cadastrado.
            </p>
            <p className="text-xs text-muted-foreground text-pretty">
              Crie tipos específicos para a sua operação.
            </p>
            <Button variant="outline" size="sm" className="mt-2" onClick={() => setOpen(true)}>
              <Plus size={15} className="mr-1" />
              Criar primeiro tipo
            </Button>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {custom.map((t) => (
              <div key={t.id} className="flex items-start gap-3 border rounded-lg px-4 py-3 group">
                <TipoIcon icone={t.icone} cor={t.cor} />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold truncate">{t.nome}</p>
                  <p className="text-xs text-muted-foreground truncate">{t.codigo}</p>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  aria-label={`Remover tipo ${t.nome}`}
                  className="shrink-0 opacity-0 group-hover:opacity-100 text-destructive hover:text-destructive size-7"
                  onClick={() => setDeleteTarget(t)}
                >
                  <Trash2 className="size-3.5" />
                </Button>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* AlertDialog para deleção */}
      <AlertDialog open={!!deleteTarget} onOpenChange={(v) => !v && setDeleteTarget(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Remover tipo de relacionamento</AlertDialogTitle>
            <AlertDialogDescription>
              Tem certeza que deseja remover <strong>{deleteTarget?.nome}</strong>? Pessoas
              com este vínculo não serão afetadas, mas o tipo não estará mais disponível
              para novos cadastros.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              onClick={() => deleteTarget && desativar.mutate(deleteTarget.id)}
            >
              Remover
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Dialog novo tipo */}
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>Novo Tipo de Relacionamento</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <div className="space-y-1">
              <Label>
                Código{' '}
                <span className="text-muted-foreground text-xs font-normal">(único, sem espaços)</span>
              </Label>
              <Input
                placeholder="ex: REPRESENTANTE"
                value={form.codigo}
                onChange={(e) =>
                  setForm({ ...form, codigo: e.target.value.toUpperCase().replace(/\s/g, '_') })
                }
              />
            </div>
            <div className="space-y-1">
              <Label>Nome</Label>
              <Input
                placeholder="ex: Representante Comercial"
                value={form.nome}
                onChange={(e) => setForm({ ...form, nome: e.target.value })}
              />
            </div>
            <div className="space-y-1">
              <Label>Cor de identificação</Label>
              <div className="flex items-center gap-3">
                <input
                  type="color"
                  value={form.cor}
                  onChange={(e) => setForm({ ...form, cor: e.target.value })}
                  className="size-10 rounded-lg border cursor-pointer p-0.5"
                />
                <div
                  className="flex-1 h-10 rounded-lg border flex items-center px-3 text-sm font-medium truncate"
                  style={{
                    backgroundColor: form.cor + '20',
                    color: form.cor,
                    borderColor: form.cor + '40',
                  }}
                >
                  {form.nome || 'Prévia'}
                </div>
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)}>
              Cancelar
            </Button>
            <Button
              onClick={() => criar.mutate(form)}
              disabled={!form.codigo || !form.nome || criar.isPending}
            >
              {criar.isPending ? 'Salvando...' : 'Criar Tipo'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
