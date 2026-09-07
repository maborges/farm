'use client';

import * as React from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiFetch } from '@/lib/api';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Plus, Trash2, Pencil, Check, X, Phone, Mail, MessageCircle, Globe, Star } from 'lucide-react';
import { Checkbox } from '@/components/ui/checkbox';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Form, FormField, FormItem, FormLabel, FormControl, FormMessage,
} from '@/components/ui/form';
import { useForm, useWatch } from 'react-hook-form';
import * as z from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';

interface Contato {
  id: string; tipo: string; valor: string;
  descricao?: string; principal: boolean; verificado: boolean; ativo: boolean;
}

const TIPO_ICON: Record<string, React.ReactNode> = {
  EMAIL: <Mail className="size-4" />,
  CELULAR: <Phone className="size-4" />,
  TELEFONE: <Phone className="size-4" />,
  WHATSAPP: <MessageCircle className="size-4" />,
  SITE: <Globe className="size-4" />,
};
const TIPO_LABEL: Record<string, string> = {
  CELULAR: 'Celular', TELEFONE: 'Telefone', EMAIL: 'E-mail',
  WHATSAPP: 'WhatsApp', SITE: 'Site', OUTRO: 'Outro',
};
const TIPO_COLOR: Record<string, string> = {
  EMAIL: 'text-blue-500', CELULAR: 'text-green-500',
  TELEFONE: 'text-slate-500', WHATSAPP: 'text-emerald-500',
  SITE: 'text-purple-500', OUTRO: 'text-slate-400',
};

const contatoSchema = z.object({
  tipo: z.string(),
  valor: z.string().min(1, 'Valor é obrigatório'),
  descricao: z.string().optional(),
  principal: z.boolean().default(false),
});

type ContatoFormData = z.infer<typeof contatoSchema>;

interface ContatoFormProps {
  initial?: Partial<ContatoFormData>;
  onSubmit: (data: ContatoFormData) => void;
  onCancel: () => void;
  isPending: boolean;
  submitLabel: string;
}

function ContatoForm({ initial, onSubmit, onCancel, isPending, submitLabel }: ContatoFormProps) {
  const form = useForm<ContatoFormData>({
    resolver: zodResolver(contatoSchema),
    defaultValues: { tipo: 'CELULAR', valor: '', descricao: '', principal: false, ...initial },
  });

  const tipo = useWatch({ control: form.control, name: 'tipo' });

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="p-4 space-y-3">
        <div className="grid grid-cols-2 gap-3">
          <FormField
            control={form.control}
            name="tipo"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Tipo</FormLabel>
                <Select onValueChange={field.onChange} value={field.value}>
                  <FormControl>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    {Object.entries(TIPO_LABEL).map(([k, v]) => <SelectItem key={k} value={k}>{v}</SelectItem>)}
                  </SelectContent>
                </Select>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="valor"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Valor</FormLabel>
                <FormControl>
                  <Input
                    {...field}
                    placeholder={tipo === 'EMAIL' ? 'email@exemplo.com' : '(00) 90000-0000'}
                    autoFocus
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>
        <FormField
          control={form.control}
          name="descricao"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Descrição <span className="text-muted-foreground text-xs">(opcional)</span></FormLabel>
              <FormControl>
                <Input {...field} placeholder="Ex: Contato financeiro, WhatsApp pessoal" />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <div className="flex items-center justify-between pt-1">
          <FormField
            control={form.control}
            name="principal"
            render={({ field }) => (
              <FormItem className="flex items-center gap-2 space-y-0">
                <FormControl>
                  <Checkbox checked={field.value} onCheckedChange={field.onChange} />
                </FormControl>
                <FormLabel className="text-sm font-normal cursor-pointer select-none">
                  Marcar como principal
                </FormLabel>
              </FormItem>
            )}
          />
          <div className="flex gap-2">
            <Button size="sm" variant="ghost" type="button" onClick={onCancel}>Cancelar</Button>
            <Button size="sm" type="submit" disabled={isPending}>
              {isPending ? 'Salvando...' : submitLabel}
            </Button>
          </div>
        </div>
      </form>
    </Form>
  );
}

interface Props { pessoaId: string; readOnly?: boolean; readOnlyMessage?: string }

export function TabContatos({ pessoaId, readOnly = false, readOnlyMessage }: Props) {
  const qc = useQueryClient();
  const [adding, setAdding] = React.useState(false);
  const [editingId, setEditingId] = React.useState<string | null>(null);
  const [confirmDeleteId, setConfirmDeleteId] = React.useState<string | null>(null);

  const { data: contatos = [], isLoading } = useQuery<Contato[]>({
    queryKey: ['pessoa-contatos', pessoaId],
    queryFn: () => apiFetch(`/cadastros/pessoas/${pessoaId}/contatos`),
  });

  const addMutation = useMutation({
    mutationFn: (data: ContatoFormData) => apiFetch(`/cadastros/pessoas/${pessoaId}/contatos`, {
      method: 'POST',
      body: JSON.stringify({ ...data, descricao: data.descricao || undefined }),
    }),
    onSuccess: () => {
      toast.success('Contato adicionado');
      qc.invalidateQueries({ queryKey: ['pessoa-contatos', pessoaId] });
      setAdding(false);
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const editMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<Contato> }) => apiFetch(`/cadastros/pessoas/${pessoaId}/contatos/${id}`, {
      method: 'PATCH', body: JSON.stringify(data),
    }),
    onSuccess: () => {
      toast.success('Contato atualizado');
      qc.invalidateQueries({ queryKey: ['pessoa-contatos', pessoaId] });
      setEditingId(null);
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const removeMutation = useMutation({
    mutationFn: (id: string) => apiFetch(`/cadastros/pessoas/${pessoaId}/contatos/${id}`, { method: 'DELETE' }),
    onSuccess: () => {
      toast.success('Contato removido');
      qc.invalidateQueries({ queryKey: ['pessoa-contatos', pessoaId] });
      setConfirmDeleteId(null);
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const startEdit = (c: Contato) => {
    setEditingId(c.id);
    setAdding(false);
  };

  if (isLoading) {
    return (
      <div className="py-8 space-y-2">
        {[1, 2].map((i) => (
          <div key={i} className="h-14 rounded-lg bg-muted animate-pulse" />
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-3 py-4">
      {readOnly && (
        <Alert>
          <AlertDescription>
            {readOnlyMessage || 'E-mail e telefone são mantidos pelo ERP. Use a atualização pelo ID do ERP no topo da página.'}
          </AlertDescription>
        </Alert>
      )}
      {/* Add form */}
      {adding && !readOnly && (
        <div className="rounded-lg border bg-card shadow-sm overflow-hidden">
          <div className="flex items-center justify-between px-4 py-3 border-b bg-muted/40">
            <span className="text-sm font-medium">Novo contato</span>
            <Button variant="ghost" size="icon" className="size-7" onClick={() => setAdding(false)}>
              <X className="size-4" />
            </Button>
          </div>
          <ContatoForm
            onSubmit={(data) => addMutation.mutate(data)}
            onCancel={() => setAdding(false)}
            isPending={addMutation.isPending}
            submitLabel="Adicionar"
          />
        </div>
      )}

      {/* Empty state */}
      {contatos.length === 0 && !adding && (
        <div className="flex flex-col items-center justify-center py-12 text-center rounded-lg border border-dashed">
          <Phone className="size-8 text-muted-foreground/40 mb-3" />
          <p className="text-sm font-medium text-muted-foreground">Nenhum contato cadastrado</p>
          <p className="text-xs text-muted-foreground/70 mt-1 mb-4">Adicione telefones, e-mails ou outros canais de contato.</p>
          {!readOnly && (
            <Button size="sm" variant="outline" onClick={() => setAdding(true)}>
              <Plus className="size-4 mr-1.5" /> Adicionar contato
            </Button>
          )}
        </div>
      )}

      {/* List */}
      <div className="space-y-2">
        {contatos.map((c) => (
          <div key={c.id} className="rounded-lg border bg-card shadow-sm overflow-hidden">
            {editingId === c.id ? (
              <div>
                <div className="flex items-center justify-between px-4 py-3 border-b bg-muted/40">
                  <span className="text-sm font-medium">Editar contato</span>
                  <Button variant="ghost" size="icon" className="size-7" onClick={() => setEditingId(null)}>
                    <X className="size-4" />
                  </Button>
                </div>
                <ContatoForm
                  initial={{ tipo: c.tipo, valor: c.valor, descricao: c.descricao, principal: c.principal }}
                  onSubmit={(data) => editMutation.mutate({ id: c.id, data })}
                  onCancel={() => setEditingId(null)}
                  isPending={editMutation.isPending}
                  submitLabel="Salvar"
                />
              </div>
            ) : confirmDeleteId === c.id ? (
              <div className="flex items-center justify-between px-4 py-3 bg-destructive/5">
                <p className="text-sm">Remover <strong>{c.valor}</strong>?</p>
                <div className="flex gap-2">
                  <Button size="sm" variant="ghost" onClick={() => setConfirmDeleteId(null)}>Cancelar</Button>
                  <Button size="sm" variant="destructive" onClick={() => removeMutation.mutate(c.id)}
                    disabled={removeMutation.isPending}>
                    {removeMutation.isPending ? 'Removendo...' : 'Remover'}
                  </Button>
                </div>
              </div>
            ) : (
              <div className="group flex items-center gap-3 px-4 py-3">
                <span className={`shrink-0 ${TIPO_COLOR[c.tipo] ?? 'text-muted-foreground'}`}>
                  {TIPO_ICON[c.tipo] ?? <Phone className="size-4" />}
                </span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="text-sm font-medium truncate">{c.valor}</p>
                    {c.principal && (
                      <Star className="size-3 fill-amber-400 text-amber-400 shrink-0" />
                    )}
                  </div>
                  <div className="flex items-center gap-2 mt-0.5">
                    <Badge variant="secondary" className="text-xs h-4 px-1.5">{TIPO_LABEL[c.tipo] ?? c.tipo}</Badge>
                    {c.descricao && <span className="text-xs text-muted-foreground truncate">{c.descricao}</span>}
                  </div>
                </div>
                {!readOnly && (
                <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                  <Button variant="ghost" size="icon" className="size-8 text-muted-foreground hover:text-foreground"
                    onClick={() => startEdit(c)}>
                    <Pencil className="size-3.5" />
                  </Button>
                  <Button variant="ghost" size="icon" className="size-8 text-muted-foreground hover:text-destructive"
                    onClick={() => setConfirmDeleteId(c.id)}>
                    <Trash2 className="size-3.5" />
                  </Button>
                </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Bottom add button (when list has items) */}
      {contatos.length > 0 && !adding && !readOnly && (
        <Button variant="outline" size="sm" className="w-full border-dashed text-muted-foreground"
          onClick={() => { setAdding(true); setEditingId(null); }}>
          <Plus className="size-4 mr-1.5" /> Adicionar contato
        </Button>
      )}
    </div>
  );
}
