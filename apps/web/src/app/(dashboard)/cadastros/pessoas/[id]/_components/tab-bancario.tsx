'use client';

import * as React from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiFetch } from '@/lib/api';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Plus, Trash2, Landmark, Pencil, Check, X, Star, Zap } from 'lucide-react';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Form, FormField, FormItem, FormLabel, FormControl, FormMessage,
} from '@/components/ui/form';
import { useForm } from 'react-hook-form';
import * as z from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';

interface Bancario {
  id: string; tipo_conta: string; banco_nome?: string; banco_codigo?: string;
  agencia?: string; conta?: string; chave_pix?: string;
  titular_nome?: string; titular_cpf_cnpj?: string; principal: boolean; ativo: boolean;
}

const TIPO_LABEL: Record<string, string> = {
  CORRENTE: 'Corrente', POUPANCA: 'Poupança', SALARIO: 'Salário', PIX: 'PIX',
};

const bancarioSchema = z.object({
  tipo_conta: z.string(),
  banco_nome: z.string().default(''),
  banco_codigo: z.string().default(''),
  agencia: z.string().default(''),
  conta: z.string().default(''),
  chave_pix: z.string().default(''),
  titular_nome: z.string().default(''),
  titular_cpf_cnpj: z.string().default(''),
  principal: z.boolean().default(false),
});

type BancarioFormData = z.infer<typeof bancarioSchema>;

interface BancarioFormProps {
  initial?: Partial<BancarioFormData>;
  onSubmit: (data: BancarioFormData) => void;
  onCancel: () => void;
  isPending: boolean;
  submitLabel: string;
}

function BancarioForm({ initial, onSubmit, onCancel, isPending, submitLabel }: BancarioFormProps) {
  const form = useForm<BancarioFormData>({
    resolver: zodResolver(bancarioSchema),
    defaultValues: { tipo_conta: 'PIX', banco_nome: '', banco_codigo: '', agencia: '', conta: '', chave_pix: '', titular_nome: '', titular_cpf_cnpj: '', principal: false, ...initial },
  });

  const tipoConta = form.watch('tipo_conta');
  const isPix = tipoConta === 'PIX';

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="p-4 space-y-3">
        <div className="grid grid-cols-2 gap-3">
          <FormField
            control={form.control}
            name="tipo_conta"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Tipo de Conta</FormLabel>
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
          {isPix ? (
            <FormField
              control={form.control}
              name="chave_pix"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Chave PIX</FormLabel>
                  <FormControl><Input {...field} value={field.value ?? ''} placeholder="CPF, CNPJ, e-mail, telefone ou aleatória" /></FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
          ) : (
            <FormField
              control={form.control}
              name="banco_nome"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Banco</FormLabel>
                  <FormControl><Input {...field} value={field.value ?? ''} placeholder="Ex: Banco do Brasil" /></FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
          )}
        </div>
        {!isPix && (
          <div className="grid grid-cols-3 gap-3">
            <FormField
              control={form.control}
              name="banco_codigo"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Código</FormLabel>
                  <FormControl><Input {...field} value={field.value ?? ''} placeholder="001" /></FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="agencia"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Agência</FormLabel>
                  <FormControl><Input {...field} value={field.value ?? ''} placeholder="0001" /></FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="conta"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Conta</FormLabel>
                  <FormControl><Input {...field} value={field.value ?? ''} placeholder="12345-6" /></FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
          </div>
        )}
        <div className="grid grid-cols-2 gap-3">
          <FormField
            control={form.control}
            name="titular_nome"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Nome do Titular <span className="text-muted-foreground text-xs">(opcional)</span></FormLabel>
                <FormControl><Input {...field} value={field.value ?? ''} placeholder="Opcional" /></FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="titular_cpf_cnpj"
            render={({ field }) => (
              <FormItem>
                <FormLabel>CPF/CNPJ do Titular <span className="text-muted-foreground text-xs">(opcional)</span></FormLabel>
                <FormControl><Input {...field} value={field.value ?? ''} placeholder="Opcional" /></FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>
        <div className="flex items-center justify-between mt-4 pt-3 border-t">
          <FormField
            control={form.control}
            name="principal"
            render={({ field }) => (
              <FormItem className="flex items-center gap-2 space-y-0">
                <FormControl>
                  <Checkbox checked={field.value} onCheckedChange={field.onChange} />
                </FormControl>
                <FormLabel className="text-sm font-normal cursor-pointer select-none">
                  Conta principal para pagamentos
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

interface Props { pessoaId: string }

export function TabBancario({ pessoaId }: Props) {
  const qc = useQueryClient();
  const [adding, setAdding] = React.useState(false);
  const [editingId, setEditingId] = React.useState<string | null>(null);
  const [confirmDeleteId, setConfirmDeleteId] = React.useState<string | null>(null);

  const { data: bancario = [], isLoading } = useQuery<Bancario[]>({
    queryKey: ['pessoa-bancario', pessoaId],
    queryFn: () => apiFetch(`/cadastros/pessoas/${pessoaId}/bancario`),
  });

  const addMutation = useMutation({
    mutationFn: (data: BancarioFormData) => apiFetch(`/cadastros/pessoas/${pessoaId}/bancario`, {
      method: 'POST',
      body: JSON.stringify(Object.fromEntries(Object.entries(data).map(([k, v]) => [k, v === '' ? undefined : v]))),
    }),
    onSuccess: () => {
      toast.success('Dado bancário adicionado');
      qc.invalidateQueries({ queryKey: ['pessoa-bancario', pessoaId] });
      setAdding(false);
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const editMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<Bancario> }) => apiFetch(`/cadastros/pessoas/${pessoaId}/bancario/${id}`, {
      method: 'PATCH', body: JSON.stringify(data),
    }),
    onSuccess: () => {
      toast.success('Dado bancário atualizado');
      qc.invalidateQueries({ queryKey: ['pessoa-bancario', pessoaId] });
      setEditingId(null);
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const removeMutation = useMutation({
    mutationFn: (id: string) => apiFetch(`/cadastros/pessoas/${pessoaId}/bancario/${id}`, { method: 'DELETE' }),
    onSuccess: () => {
      toast.success('Dado bancário removido');
      qc.invalidateQueries({ queryKey: ['pessoa-bancario', pessoaId] });
      setConfirmDeleteId(null);
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const startEdit = (b: Bancario) => {
    setEditingId(b.id);
    setAdding(false);
  };

  if (isLoading) {
    return (
      <div className="py-8 space-y-2">
        {[1, 2].map((i) => <div key={i} className="h-16 rounded-lg bg-muted animate-pulse" />)}
      </div>
    );
  }

  return (
    <div className="space-y-3 py-4">
      {/* Add form */}
      {adding && (
        <div className="rounded-lg border bg-card shadow-sm overflow-hidden">
          <div className="flex items-center justify-between px-4 py-3 border-b bg-muted/40">
            <span className="text-sm font-medium">Nova conta / chave PIX</span>
            <Button variant="ghost" size="icon" className="size-7" onClick={() => setAdding(false)}>
              <X className="size-4" />
            </Button>
          </div>
          <BancarioForm
            onSubmit={(data) => addMutation.mutate(data)}
            onCancel={() => setAdding(false)}
            isPending={addMutation.isPending}
            submitLabel="Adicionar"
          />
        </div>
      )}

      {/* Empty state */}
      {bancario.length === 0 && !adding && (
        <div className="flex flex-col items-center justify-center py-12 text-center rounded-lg border border-dashed">
          <Landmark className="size-8 text-muted-foreground/40 mb-3" />
          <p className="text-sm font-medium text-muted-foreground">Nenhum dado bancário cadastrado</p>
          <p className="text-xs text-muted-foreground/70 mt-1 mb-4">Cadastre contas bancárias ou chaves PIX para pagamentos.</p>
          <Button size="sm" variant="outline" onClick={() => setAdding(true)}>
            <Plus className="size-4 mr-1.5" /> Adicionar conta
          </Button>
        </div>
      )}

      {/* List */}
      <div className="space-y-2">
        {bancario.map((b) => (
          <div key={b.id} className="rounded-lg border bg-card shadow-sm overflow-hidden">
            {editingId === b.id ? (
              <div>
                <div className="flex items-center justify-between px-4 py-3 border-b bg-muted/40">
                  <span className="text-sm font-medium">Editar dado bancário</span>
                  <Button variant="ghost" size="icon" className="size-7" onClick={() => setEditingId(null)}>
                    <X className="size-4" />
                  </Button>
                </div>
                <BancarioForm
                  initial={{ tipo_conta: b.tipo_conta, banco_nome: b.banco_nome, banco_codigo: b.banco_codigo, agencia: b.agencia, conta: b.conta, chave_pix: b.chave_pix, titular_nome: b.titular_nome, titular_cpf_cnpj: b.titular_cpf_cnpj, principal: b.principal }}
                  onSubmit={(data) => editMutation.mutate({ id: b.id, data })}
                  onCancel={() => setEditingId(null)}
                  isPending={editMutation.isPending}
                  submitLabel="Salvar"
                />
              </div>
            ) : confirmDeleteId === b.id ? (
              <div className="flex items-center justify-between px-4 py-3 bg-destructive/5">
                <p className="text-sm">Remover este dado bancário?</p>
                <div className="flex gap-2">
                  <Button size="sm" variant="ghost" onClick={() => setConfirmDeleteId(null)}>Cancelar</Button>
                  <Button size="sm" variant="destructive" onClick={() => removeMutation.mutate(b.id)}
                    disabled={removeMutation.isPending}>
                    {removeMutation.isPending ? 'Removendo...' : 'Remover'}
                  </Button>
                </div>
              </div>
            ) : (
              <div className="group flex items-start gap-3 px-4 py-3">
                <div className="shrink-0 mt-0.5">
                  {b.tipo_conta === 'PIX'
                    ? <Zap className="size-4 text-emerald-500" />
                    : <Landmark className="size-4 text-blue-500" />
                  }
                </div>
                <div className="flex-1 min-w-0 text-sm">
                  <div className="flex items-center gap-2 mb-1">
                    <Badge variant="secondary" className="text-xs h-4 px-1.5">{TIPO_LABEL[b.tipo_conta] ?? b.tipo_conta}</Badge>
                    {b.principal && <Star className="size-3 fill-amber-400 text-amber-400" />}
                  </div>
                  {b.tipo_conta === 'PIX' ? (
                    <p className="font-medium">{b.chave_pix || '—'}</p>
                  ) : (
                    <>
                      {b.banco_nome && (
                        <p className="font-medium">{b.banco_nome}{b.banco_codigo ? <span className="text-muted-foreground font-normal"> ({b.banco_codigo})</span> : ''}</p>
                      )}
                      {(b.agencia || b.conta) && (
                        <p className="text-muted-foreground text-xs mt-0.5">
                          {b.agencia ? `Ag: ${b.agencia}` : ''}{b.agencia && b.conta ? ' · ' : ''}{b.conta ? `CC: ${b.conta}` : ''}
                        </p>
                      )}
                    </>
                  )}
                  {b.titular_nome && (
                    <p className="text-xs text-muted-foreground mt-0.5">Titular: {b.titular_nome}</p>
                  )}
                </div>
                <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
                  <Button variant="ghost" size="icon" className="size-8 text-muted-foreground hover:text-foreground"
                    onClick={() => startEdit(b)}>
                    <Pencil className="size-3.5" />
                  </Button>
                  <Button variant="ghost" size="icon" className="size-8 text-muted-foreground hover:text-destructive"
                    onClick={() => setConfirmDeleteId(b.id)}>
                    <Trash2 className="size-3.5" />
                  </Button>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      {bancario.length > 0 && !adding && (
        <Button variant="outline" size="sm" className="w-full border-dashed text-muted-foreground"
          onClick={() => { setAdding(true); setEditingId(null); }}>
          <Plus className="size-4 mr-1.5" /> Adicionar conta
        </Button>
      )}
    </div>
  );
}
