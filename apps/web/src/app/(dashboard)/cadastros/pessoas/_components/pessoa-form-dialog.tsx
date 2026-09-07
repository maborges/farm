'use client';

import * as React from 'react';
import { useForm, useWatch } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { useQuery, useMutation } from '@tanstack/react-query';
import { apiFetch } from '@/lib/api';
import { isErpPeopleManaged } from '@/lib/erp-person-governance';
import { toast } from 'sonner';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogBody,
} from '@/components/ui/dialog';
import { CloudDownload, Loader2, Search, UserPlus, XCircle, Save } from "lucide-react";
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import { Checkbox } from '@/components/ui/checkbox';
import { Separator } from '@/components/ui/separator';
import {
  Form, FormField, FormItem, FormLabel, FormControl, FormMessage,
} from '@/components/ui/form';

interface TipoRel { id: string; nome: string; cor: string }
interface ErpStatus { configurado: boolean }
interface ErpPolicy {
  feature_code: string;
  feature_enabled: boolean;
  ativa: boolean;
  mode: string;
}
interface ErpPersonRecord {
  external_id: string;
  tipo: 'PF' | 'PJ';
  nome_exibicao: string;
  cpf?: string | null;
  cnpj?: string | null;
  razao_social?: string | null;
  nome_fantasia?: string | null;
  email?: string | null;
  telefone?: string | null;
  ativo_no_erp: boolean;
}

interface Props {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  onSuccess: () => void;
}

const schema = z.object({
  tipo: z.enum(['PF', 'PJ']),
  nome_exibicao: z.string().min(2, 'Mínimo 2 caracteres').max(200),
  base_legal: z.enum(['CONTRATO', 'CONSENTIMENTO', 'INTERESSE_LEGITIMO', 'OBRIGACAO_LEGAL']),
  // PJ
  cnpj: z.string().optional(),
  razao_social: z.string().optional(),
  nome_fantasia: z.string().optional(),
  // PF
  cpf: z.string().optional(),
  nome_completo: z.string().optional(),
  // Contato
  email: z.string().email().optional().or(z.literal('')),
  celular: z.string().optional(),
});

type FormData = z.infer<typeof schema>;

export function PessoaFormDialog({ open, onOpenChange, onSuccess }: Props) {
  const [selectedTipos, setSelectedTipos] = React.useState<string[]>([]);
  const [externalId, setExternalId] = React.useState('');
  const [erpRecord, setErpRecord] = React.useState<ErpPersonRecord | null>(null);

  const form = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: {
      tipo: 'PJ',
      base_legal: 'CONTRATO',
      nome_exibicao: '',
      cnpj: '',
      razao_social: '',
      nome_fantasia: '',
      cpf: '',
      nome_completo: '',
      email: '',
      celular: '',
    },
  });

  const tipo = useWatch({ control: form.control, name: 'tipo' });

  React.useEffect(() => {
    if (open) {
      form.reset({
        tipo: 'PJ', base_legal: 'CONTRATO', nome_exibicao: '',
        cnpj: '', razao_social: '', nome_fantasia: '',
        cpf: '', nome_completo: '', email: '', celular: '',
      });
      setSelectedTipos([]);
      setExternalId('');
      setErpRecord(null);
    }
  }, [open, form]);

  const { data: tiposRel = [] } = useQuery<TipoRel[]>({
    queryKey: ['tipos-relacionamento'],
    queryFn: () => apiFetch('/cadastros/tipos-relacionamento'),
    enabled: open,
  });
  const erpStatusQuery = useQuery<ErpStatus>({
    queryKey: ['erp-status', 'pessoa-form'],
    queryFn: () => apiFetch('/integracoes/erp/status'),
    enabled: open,
    retry: false,
  });
  const erpStatus = erpStatusQuery.data;
  const erpPoliciesQuery = useQuery<ErpPolicy[]>({
    queryKey: ['erp-sync-policies'],
    queryFn: () => apiFetch('/integracoes/erp/policies'),
    enabled: open && Boolean(erpStatus?.configurado),
    retry: false,
  });
  const erpPolicies = erpPoliciesQuery.data ?? [];
  const erpEnabled = isErpPeopleManaged(erpStatus, erpPolicies);
  const governanceLoading = erpStatusQuery.isLoading || (
    Boolean(erpStatus?.configurado) && erpPoliciesQuery.isLoading
  );
  const governanceError = erpStatusQuery.isError || erpPoliciesQuery.isError;

  // Pré-seleciona FORNECEDOR quando os tipos carregam
  React.useEffect(() => {
    if (tiposRel.length > 0 && selectedTipos.length === 0) {
      const fornecedor = tiposRel.find((t) => t.nome.toUpperCase().includes('FORNECEDOR'));
      if (fornecedor) setSelectedTipos([fornecedor.id]);
    }
  }, [tiposRel, selectedTipos.length]);

  const lookup = useMutation({
    mutationFn: () =>
      apiFetch<ErpPersonRecord>('/integracoes/erp/pessoas/lookup', {
        method: 'POST',
        body: { external_id: externalId },
      }),
    onSuccess: (record) => {
      setErpRecord(record);
      form.setValue('tipo', record.tipo, { shouldValidate: true });
      form.setValue('nome_exibicao', record.nome_exibicao, { shouldValidate: true });
      form.setValue('cpf', record.cpf || '');
      form.setValue('cnpj', record.cnpj || '');
      form.setValue('razao_social', record.razao_social || '');
      form.setValue('nome_fantasia', record.nome_fantasia || '');
      form.setValue('email', record.email || '', { shouldValidate: true });
      form.setValue('celular', record.telefone || '');
      toast.success('Pessoa encontrada no ERP');
    },
    onError: (err: Error) => {
      setErpRecord(null);
      toast.error(err.message || 'Pessoa não encontrada no ERP');
    },
  });

  const mutation = useMutation({
    mutationFn: (data: FormData) => {
      if (erpEnabled) {
        return apiFetch('/integracoes/erp/pessoas/import', {
          method: 'POST',
          body: {
            external_id: externalId,
            base_legal: data.base_legal,
            relacionamento_tipo_ids: selectedTipos,
          },
        });
      }
      const pii: Record<string, string> = {};
      if (data.tipo === 'PJ') {
        if (data.cnpj) pii.cnpj = data.cnpj;
        if (data.razao_social) pii.razao_social = data.razao_social;
        if (data.nome_fantasia) pii.nome_fantasia = data.nome_fantasia;
      } else {
        if (data.cpf) pii.cpf = data.cpf;
        if (data.nome_completo) pii.nome_completo = data.nome_completo;
      }

      const contatos = [];
      if (data.email) contatos.push({ tipo: 'EMAIL', valor: data.email, principal: true });
      if (data.celular) contatos.push({ tipo: 'CELULAR', valor: data.celular, principal: !data.email });

      return apiFetch('/cadastros/pessoas', {
        method: 'POST',
        body: JSON.stringify({
          tipo: data.tipo,
          nome_exibicao: data.nome_exibicao,
          base_legal: data.base_legal,
          pii: Object.keys(pii).length > 0 ? pii : undefined,
          contatos,
          relacionamentos: selectedTipos.map((id) => ({ tipo_id: id })),
        }),
      });
    },
    onSuccess: () => {
      toast.success(erpEnabled ? 'Pessoa importada do ERP' : 'Pessoa criada com sucesso');
      onOpenChange(false);
      onSuccess();
    },
    onError: (err: Error) => toast.error(err.message || 'Erro ao criar pessoa'),
  });

  const toggleTipo = (id: string) =>
    setSelectedTipos((prev) => prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="max-w-screen-sm p-0">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2.5">
              <div className="size-8 rounded-sm bg-primary/10 flex items-center justify-center shrink-0">
                <UserPlus className="size-4 text-primary" />
              </div>
              Nova Pessoa
            </DialogTitle>
          </DialogHeader>

          <Form {...form}>
            <form onSubmit={form.handleSubmit((d) => mutation.mutate(d))}>
              <DialogBody className="space-y-6">

            {governanceError ? (
              <Alert variant="destructive">
                <AlertDescription>
                  Não foi possível verificar se este cadastro é governado pelo ERP. Tente novamente antes de salvar.
                </AlertDescription>
              </Alert>
            ) : erpEnabled ? (
              <Alert className="rounded-sm border-primary/30 bg-primary/5">
                <CloudDownload className="size-4" />
                <AlertDescription className="space-y-3">
                  <div>
                    <p className="font-medium">Cadastro governado pelo ERP</p>
                    <p className="text-xs text-muted-foreground">
                      Informe o ID da pessoa no ERP. Os dados cadastrais serão preenchidos
                      exclusivamente pela API; vínculos e base legal continuam locais.
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <Input
                      value={externalId}
                      onChange={(event) => {
                        setExternalId(event.target.value);
                        setErpRecord(null);
                      }}
                      placeholder="ID da pessoa no ERP"
                      className="h-8 rounded-sm bg-background"
                      disabled={lookup.isPending || mutation.isPending}
                    />
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      disabled={!externalId.trim() || lookup.isPending || mutation.isPending}
                      onClick={() => lookup.mutate()}
                    >
                      {lookup.isPending ? (
                        <Loader2 className="size-3.5 animate-spin" />
                      ) : (
                        <Search className="size-3.5" />
                      )}
                      Buscar no ERP
                    </Button>
                  </div>
                  {erpRecord ? (
                    <p className="text-xs font-medium text-primary">
                      {erpRecord.nome_exibicao} · {erpRecord.tipo === 'PF' ? 'Pessoa física' : 'Pessoa jurídica'}
                      {!erpRecord.ativo_no_erp ? ' · Inativa no ERP' : ''}
                    </p>
                  ) : null}
                </AlertDescription>
              </Alert>
            ) : null}

            {/* Identificação — Tipo + Base Legal + Nome numa linha */}
            <div className="grid grid-cols-[160px_1fr_2fr] gap-3 items-start">
              <FormField
                control={form.control}
                name="tipo"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Tipo</FormLabel>
                    <Select onValueChange={field.onChange} value={field.value} disabled={mutation.isPending || erpEnabled}>
                      <FormControl>
                        <SelectTrigger className="h-8 rounded-sm"><SelectValue /></SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        <SelectItem value="PJ">Pessoa Jurídica</SelectItem>
                        <SelectItem value="PF">Pessoa Física</SelectItem>
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="base_legal"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Base Legal (LGPD)</FormLabel>
                    <Select onValueChange={field.onChange} value={field.value} disabled={mutation.isPending}>
                      <FormControl>
                        <SelectTrigger className="h-8 rounded-sm"><SelectValue /></SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        <SelectItem value="CONTRATO">Contrato</SelectItem>
                        <SelectItem value="CONSENTIMENTO">Consentimento</SelectItem>
                        <SelectItem value="INTERESSE_LEGITIMO">Int. Legítimo</SelectItem>
                        <SelectItem value="OBRIGACAO_LEGAL">Obrigação Legal</SelectItem>
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="nome_exibicao"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Nome de exibição</FormLabel>
                    <FormControl>
                      <Input
                        {...field}
                        placeholder={tipo === 'PJ' ? 'Razão social ou nome fantasia' : 'Nome completo ou apelido'}
                        disabled={mutation.isPending || erpEnabled}
                        className="h-8 rounded-sm"
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <Separator />

            {/* Campos PJ */}
            {tipo === 'PJ' && (
              <div className="space-y-3">
                <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">Dados da Empresa</p>
                <div className="grid grid-cols-[180px_1fr_1fr] gap-3">
                  <FormField
                    control={form.control}
                    name="cnpj"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>CNPJ</FormLabel>
                        <FormControl>
                          <Input {...field} placeholder="00.000.000/0000-00" disabled={mutation.isPending || erpEnabled} className="h-8 rounded-sm" />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name="razao_social"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Razão Social</FormLabel>
                        <FormControl>
                          <Input {...field} disabled={mutation.isPending || erpEnabled} className="h-8 rounded-sm" />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name="nome_fantasia"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Nome Fantasia</FormLabel>
                        <FormControl>
                          <Input {...field} disabled={mutation.isPending || erpEnabled} className="h-8 rounded-sm" />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>
              </div>
            )}

            {/* Campos PF */}
            {tipo === 'PF' && (
              <div className="space-y-3">
                <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">Dados Pessoais</p>
                <div className="grid grid-cols-[180px_1fr] gap-3">
                  <FormField
                    control={form.control}
                    name="cpf"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>CPF</FormLabel>
                        <FormControl>
                          <Input {...field} placeholder="000.000.000-00" disabled={mutation.isPending || erpEnabled} className="h-8 rounded-sm" />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name="nome_completo"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Nome Completo</FormLabel>
                        <FormControl>
                          <Input {...field} disabled={mutation.isPending || erpEnabled} className="h-8 rounded-sm" />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>
              </div>
            )}

            {/* Contato */}
            <div className="space-y-3">
              <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">Contato</p>
              <div className="grid grid-cols-2 gap-3">
                <FormField
                  control={form.control}
                  name="email"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>E-mail</FormLabel>
                      <FormControl>
                        <Input {...field} type="email" placeholder="email@empresa.com" disabled={mutation.isPending || erpEnabled} className="h-8 rounded-sm" />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="celular"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Celular / WhatsApp</FormLabel>
                      <FormControl>
                        <Input {...field} placeholder="(00) 90000-0000" disabled={mutation.isPending || erpEnabled} className="h-8 rounded-sm" />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
            </div>

            <Separator />

            {/* Vínculos */}
            <div className="space-y-2">
              <FormLabel>Vínculos</FormLabel>
              <div className="grid grid-cols-3 gap-1">
                {tiposRel.map((t) => (
                  <label key={t.id} className="flex items-center gap-2 cursor-pointer px-2 py-1.5 rounded hover:bg-muted/50 transition-colors">
                    <Checkbox
                      checked={selectedTipos.includes(t.id)}
                      onCheckedChange={() => toggleTipo(t.id)}
                      disabled={mutation.isPending}
                    />
                    <span className="px-1.5 py-0.5 rounded text-xs font-medium truncate" style={{ backgroundColor: t.cor + '22', color: t.cor }}>
                      {t.nome}
                    </span>
                  </label>
                ))}
              </div>
            </div>

              </DialogBody>

              <DialogFooter>
                <Button type="button" variant="outline" size="sm" className="rounded-sm" onClick={() => onOpenChange(false)} disabled={mutation.isPending}>
                  <XCircle className="size-3.5 mr-1.5" />
                  Cancelar
                </Button>
                <Button 
                  type="submit" 
                  variant="outline"
                  size="sm"
                  className="rounded-sm border-primary/50 text-primary hover:bg-primary/5"
                  disabled={
                    mutation.isPending ||
                    governanceLoading ||
                    governanceError ||
                    !form.formState.isValid ||
                    (erpEnabled && !erpRecord)
                  }
                >
                  <Save className="size-3.5 mr-1.5" />
                  {mutation.isPending ? 'Salvando...' : 'Criar Pessoa'}
                </Button>
              </DialogFooter>
            </form>
          </Form>
      </DialogContent>
    </Dialog>
  );
}
