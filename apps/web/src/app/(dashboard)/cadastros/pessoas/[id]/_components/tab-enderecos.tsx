'use client';

import * as React from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiFetch } from '@/lib/api';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Plus, Trash2, MapPin, Loader2, Pencil, Check, X, Star } from 'lucide-react';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Form, FormField, FormItem, FormLabel, FormControl, FormMessage,
} from '@/components/ui/form';
import { useForm } from 'react-hook-form';
import * as z from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';

interface Endereco {
  id: string; tipo: string; cep?: string; logradouro?: string; numero?: string;
  complemento?: string; bairro?: string; cidade?: string; estado?: string;
  pais: string; principal: boolean; ativo: boolean;
}

const TIPO_LABEL: Record<string, string> = {
  PRINCIPAL: 'Principal', ENTREGA: 'Entrega', COBRANCA: 'Cobrança', RURAL: 'Rural',
};
const TIPO_COLOR: Record<string, string> = {
  PRINCIPAL: 'text-blue-500', ENTREGA: 'text-green-500',
  COBRANCA: 'text-orange-500', RURAL: 'text-emerald-600',
};

function formatarCep(cep: string): string {
  const clean = cep.replace(/\D/g, '');
  if (clean.length <= 5) return clean;
  return `${clean.slice(0, 5)}-${clean.slice(5, 8)}`;
}

const enderecoSchema = z.object({
  tipo: z.string(),
  cep: z.string().default(''),
  logradouro: z.string().default(''),
  numero: z.string().default(''),
  complemento: z.string().default(''),
  bairro: z.string().default(''),
  cidade: z.string().default(''),
  estado: z.string().default(''),
  principal: z.boolean().default(false),
});

type EnderecoFormData = z.infer<typeof enderecoSchema>;

interface AddressFormProps {
  initial?: Partial<EnderecoFormData>;
  onSubmit: (data: EnderecoFormData) => void;
  onCancel: () => void;
  isPending: boolean;
  submitLabel: string;
  cepValues: { cep: string };
  onCepChange: (cep: string) => void;
  isCepLoading: boolean;
}

function AddressForm({ initial, onSubmit, onCancel, isPending, submitLabel, cepValues, onCepChange, isCepLoading }: AddressFormProps) {
  const form = useForm<EnderecoFormData>({
    resolver: zodResolver(enderecoSchema),
    defaultValues: { tipo: 'PRINCIPAL', cep: '', logradouro: '', numero: '', complemento: '', bairro: '', cidade: '', estado: '', principal: false, ...initial },
  });

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="p-4 space-y-3">
        <div className="grid grid-cols-3 gap-3">
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
          <div className="col-span-2">
            <FormItem>
              <FormLabel>CEP</FormLabel>
              <div className="relative">
                <Input value={cepValues.cep ?? ''} placeholder="00000-000"
                  onChange={(e) => { const formatted = formatarCep(e.target.value); onCepChange(formatted); }} />
                {isCepLoading && <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 size-4 animate-spin text-muted-foreground" />}
              </div>
            </FormItem>
          </div>
        </div>
        <div className="grid grid-cols-3 gap-3">
          <FormField
            control={form.control}
            name="logradouro"
            render={({ field }) => (
              <FormItem className="col-span-2">
                <FormLabel>Logradouro</FormLabel>
                <FormControl><Input {...field} value={field.value ?? ''} placeholder="Rua, Av., Estrada..." /></FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="numero"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Número</FormLabel>
                <FormControl><Input {...field} value={field.value ?? ''} placeholder="123" /></FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <FormField
            control={form.control}
            name="complemento"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Complemento</FormLabel>
                <FormControl><Input {...field} value={field.value ?? ''} placeholder="Apto, Sala..." /></FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="bairro"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Bairro</FormLabel>
                <FormControl><Input {...field} value={field.value ?? ''} /></FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>
        <div className="grid grid-cols-3 gap-3">
          <FormField
            control={form.control}
            name="cidade"
            render={({ field }) => (
              <FormItem className="col-span-2">
                <FormLabel>Cidade</FormLabel>
                <FormControl><Input {...field} value={field.value ?? ''} /></FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="estado"
            render={({ field }) => (
              <FormItem>
                <FormLabel>UF</FormLabel>
                <FormControl><Input {...field} value={field.value ?? ''} maxLength={2} placeholder="SP" className="uppercase" /></FormControl>
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
                  Endereço principal
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

export function TabEnderecos({ pessoaId }: Props) {
  const qc = useQueryClient();
  const [adding, setAdding] = React.useState(false);
  const [editingId, setEditingId] = React.useState<string | null>(null);
  const [confirmDeleteId, setConfirmDeleteId] = React.useState<string | null>(null);
  const [loadingCep, setLoadingCep] = React.useState(false);
  const [addCep, setAddCep] = React.useState('');
  const [editCep, setEditCep] = React.useState('');
  const cepTimeoutRef = React.useRef<NodeJS.Timeout | undefined>(undefined);

  const { data: enderecos = [], isLoading } = useQuery<Endereco[]>({
    queryKey: ['pessoa-enderecos', pessoaId],
    queryFn: () => apiFetch(`/cadastros/pessoas/${pessoaId}/enderecos`),
  });

  const buscarCep = async (cep: string, target: 'add' | 'edit') => {
    const clean = cep.replace(/\D/g, '');
    if (clean.length !== 8) return;
    setLoadingCep(true);
    try {
      const res = await fetch(`https://viacep.com.br/ws/${clean}/json/`);
      const data = await res.json();
      if (!data.erro) {
        // Returns the data to be merged by the caller
        return data;
      }
    } catch { /* silencia */ } finally { setLoadingCep(false); }
    return null;
  };

  const handleAddCepChange = (cep: string) => {
    setAddCep(cep);
    const clean = cep.replace(/\D/g, '');
    if (cepTimeoutRef.current) clearTimeout(cepTimeoutRef.current);
    if (clean.length === 8) {
      cepTimeoutRef.current = setTimeout(async () => {
        const data = await buscarCep(cep, 'add');
        if (data) setLoadingCep(false);
      }, 500);
    }
  };

  const handleEditCepChange = (cep: string) => {
    setEditCep(cep);
    const clean = cep.replace(/\D/g, '');
    if (cepTimeoutRef.current) clearTimeout(cepTimeoutRef.current);
    if (clean.length === 8) {
      cepTimeoutRef.current = setTimeout(async () => {
        const data = await buscarCep(cep, 'edit');
        if (data) setLoadingCep(false);
      }, 500);
    }
  };

  const addMutation = useMutation({
    mutationFn: (data: EnderecoFormData) => apiFetch(`/cadastros/pessoas/${pessoaId}/enderecos`, {
      method: 'POST',
      body: JSON.stringify(Object.fromEntries(Object.entries(data).map(([k, v]) => [k, v === '' ? undefined : v]))),
    }),
    onSuccess: () => {
      toast.success('Endereço adicionado');
      qc.invalidateQueries({ queryKey: ['pessoa-enderecos', pessoaId] });
      setAdding(false);
      setAddCep('');
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const editMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<Endereco> }) => apiFetch(`/cadastros/pessoas/${pessoaId}/enderecos/${id}`, {
      method: 'PATCH', body: JSON.stringify(data),
    }),
    onSuccess: () => {
      toast.success('Endereço atualizado');
      qc.invalidateQueries({ queryKey: ['pessoa-enderecos', pessoaId] });
      setEditingId(null);
      setEditCep('');
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const removeMutation = useMutation({
    mutationFn: (id: string) => apiFetch(`/cadastros/pessoas/${pessoaId}/enderecos/${id}`, { method: 'DELETE' }),
    onSuccess: () => {
      toast.success('Endereço removido');
      qc.invalidateQueries({ queryKey: ['pessoa-enderecos', pessoaId] });
      setConfirmDeleteId(null);
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const startEdit = (e: Endereco) => {
    setEditingId(e.id);
    setAdding(false);
    setEditCep(e.cep ?? '');
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
            <span className="text-sm font-medium">Novo endereço</span>
            <Button variant="ghost" size="icon" className="size-7" onClick={() => setAdding(false)}>
              <X className="size-4" />
            </Button>
          </div>
          <AddressForm
            onSubmit={(data) => addMutation.mutate(data)}
            onCancel={() => { setAdding(false); setAddCep(''); }}
            isPending={addMutation.isPending}
            submitLabel="Adicionar"
            cepValues={{ cep: addCep }}
            onCepChange={handleAddCepChange}
            isCepLoading={loadingCep}
          />
        </div>
      )}

      {/* Empty state */}
      {enderecos.length === 0 && !adding && (
        <div className="flex flex-col items-center justify-center py-12 text-center rounded-lg border border-dashed">
          <MapPin className="size-8 text-muted-foreground/40 mb-3" />
          <p className="text-sm font-medium text-muted-foreground">Nenhum endereço cadastrado</p>
          <p className="text-xs text-muted-foreground/70 mt-1 mb-4">Adicione endereços para entrega, cobrança ou localização.</p>
          <Button size="sm" variant="outline" onClick={() => setAdding(true)}>
            <Plus className="size-4 mr-1.5" /> Adicionar endereço
          </Button>
        </div>
      )}

      {/* List */}
      <div className="space-y-2">
        {enderecos.map((e) => (
          <div key={e.id} className="rounded-lg border bg-card shadow-sm overflow-hidden">
            {editingId === e.id ? (
              <div>
                <div className="flex items-center justify-between px-4 py-3 border-b bg-muted/40">
                  <span className="text-sm font-medium">Editar endereço</span>
                  <Button variant="ghost" size="icon" className="size-7" onClick={() => setEditingId(null)}>
                    <X className="size-4" />
                  </Button>
                </div>
                <div className="p-4">
                  <AddressForm
                    initial={{ tipo: e.tipo, cep: e.cep, logradouro: e.logradouro, numero: e.numero, complemento: e.complemento, bairro: e.bairro, cidade: e.cidade, estado: e.estado, principal: e.principal }}
                    onSubmit={(data) => editMutation.mutate({ id: e.id, data })}
                    onCancel={() => { setEditingId(null); setEditCep(''); }}
                    isPending={editMutation.isPending}
                    submitLabel="Salvar"
                    cepValues={{ cep: editCep }}
                    onCepChange={handleEditCepChange}
                    isCepLoading={loadingCep}
                  />
                </div>
              </div>
            ) : confirmDeleteId === e.id ? (
              <div className="flex items-center justify-between px-4 py-3 bg-destructive/5">
                <p className="text-sm">Remover este endereço?</p>
                <div className="flex gap-2">
                  <Button size="sm" variant="ghost" onClick={() => setConfirmDeleteId(null)}>Cancelar</Button>
                  <Button size="sm" variant="destructive" onClick={() => removeMutation.mutate(e.id)}
                    disabled={removeMutation.isPending}>
                    {removeMutation.isPending ? 'Removendo...' : 'Remover'}
                  </Button>
                </div>
              </div>
            ) : (
              <div className="group flex items-start gap-3 px-4 py-3">
                <MapPin className={`size-4 mt-0.5 shrink-0 ${TIPO_COLOR[e.tipo] ?? 'text-muted-foreground'}`} />
                <div className="flex-1 min-w-0 text-sm">
                  <div className="flex items-center gap-2 mb-1">
                    <Badge variant="secondary" className="text-xs h-4 px-1.5">{TIPO_LABEL[e.tipo] ?? e.tipo}</Badge>
                    {e.principal && <Star className="size-3 fill-amber-400 text-amber-400" />}
                  </div>
                  {e.logradouro && (
                    <p className="font-medium text-foreground">
                      {e.logradouro}{e.numero ? `, ${e.numero}` : ''}{e.complemento ? ` — ${e.complemento}` : ''}
                    </p>
                  )}
                  <p className="text-muted-foreground text-xs mt-0.5">
                    {[e.bairro, e.cidade, e.estado].filter(Boolean).join(', ')}{e.cep ? ` · CEP ${e.cep}` : ''}
                  </p>
                </div>
                <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
                  <Button variant="ghost" size="icon" className="size-8 text-muted-foreground hover:text-foreground"
                    onClick={() => startEdit(e)}>
                    <Pencil className="size-3.5" />
                  </Button>
                  <Button variant="ghost" size="icon" className="size-8 text-muted-foreground hover:text-destructive"
                    onClick={() => setConfirmDeleteId(e.id)}>
                    <Trash2 className="size-3.5" />
                  </Button>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      {enderecos.length > 0 && !adding && (
        <Button variant="outline" size="sm" className="w-full border-dashed text-muted-foreground"
          onClick={() => { setAdding(true); setEditingId(null); }}>
          <Plus className="size-4 mr-1.5" /> Adicionar endereço
        </Button>
      )}
    </div>
  );
}
