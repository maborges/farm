'use client';

import * as React from 'react';
import { useParams } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiFetch } from '@/lib/api';
import { isErpPeopleManaged } from '@/lib/erp-person-governance';
import { toast } from 'sonner';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import {
  Form, FormField, FormItem, FormLabel, FormControl, FormMessage,
} from '@/components/ui/form';
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem,
  DropdownMenuSeparator, DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel,
  AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { useForm } from 'react-hook-form';
import {
  ArrowLeft, ShieldAlert, Eye, Pencil, Check, X,
  Phone, MapPin, CreditCard, Link2, User,
  MoreVertical, PowerOff, Power, AlertTriangle, CloudDownload, Loader2, Search,
} from 'lucide-react';
import Link from 'next/link';
import { TabContatos } from './_components/tab-contatos';
import { TabEnderecos } from './_components/tab-enderecos';
import { TabBancario } from './_components/tab-bancario';
import { TabRelacionamentos } from './_components/tab-relacionamentos';
import { StatusBadge } from "@/components/ui/status-badge";

interface TipoRel { id: string; nome: string; cor: string }
interface Relacionamento { id: string; tipo: TipoRel }
interface PessoaResponse {
  id: string; tipo: 'PF' | 'PJ'; nome_exibicao: string;
  base_legal: string; ativo: boolean; anonimizado_em: string | null;
  relacionamentos: Relacionamento[];
}
interface PII {
  nome_completo?: string; cpf?: string; rg?: string; data_nascimento?: string; nome_mae?: string;
  razao_social?: string; cnpj?: string; ie?: string; nome_fantasia?: string; data_fundacao?: string;
  updated_at?: string;
}
interface ErpStatus { configurado: boolean }
interface ErpPolicy {
  feature_code: string; feature_enabled: boolean; ativa: boolean; mode: string;
}
interface ErpPersonRecord {
  external_id: string; tipo: 'PF' | 'PJ'; nome_exibicao: string;
  cpf?: string | null; cnpj?: string | null; email?: string | null; telefone?: string | null;
}
interface ErpAssociation {
  local_entity_id?: string | null; external_id: string; last_sync_at?: string | null;
}
interface ErpAssociationsResponse { items: ErpAssociation[] }

const BASE_LEGAL_LABEL: Record<string, string> = {
  CONTRATO: 'Contrato', CONSENTIMENTO: 'Consentimento',
  INTERESSE_LEGITIMO: 'Int. Legítimo', OBRIGACAO_LEGAL: 'Obrigação Legal',
};

function getInitials(nome: string) {
  return nome.split(' ').slice(0, 2).map((n) => n[0]).join('').toUpperCase();
}

export default function PessoaDetailPage() {
  const { id } = useParams<{ id: string }>();
  const qc = useQueryClient();

  const [editingHeader, setEditingHeader] = React.useState(false);

  const [piiVisible, setPiiVisible] = React.useState(false);
  const [editingPii, setEditingPii] = React.useState(false);
  const [motivoPII, setMotivoPII] = React.useState('');
  const [piiEdit, setPiiEdit] = React.useState<PII>({});
  const [anonDialogOpen, setAnonDialogOpen] = React.useState(false);
  const [externalId, setExternalId] = React.useState('');
  const [erpPreview, setErpPreview] = React.useState<ErpPersonRecord | null>(null);

  const { data: pessoa, isLoading, isError, error, refetch } = useQuery<PessoaResponse>({
    queryKey: ['pessoa', id],
    queryFn: () => apiFetch(`/cadastros/pessoas/${id}`),
    enabled: !!id,
  });

  const { data: pii, refetch: fetchPII, isFetching: piiLoading } = useQuery<PII>({
    queryKey: ['pessoa-pii', id],
    queryFn: async () => {
      try {
        return await apiFetch<PII>(
          `/cadastros/pessoas/${id}/pii?motivo=${encodeURIComponent(motivoPII || 'Visualização manual')}`,
          { suppressErrorLog: true }
        );
      } catch (err) {
        if (err instanceof Error && err.message.includes('PII não encontrada')) {
          return {};
        }
        throw err;
      }
    },
    enabled: false,
  });

  const erpStatusQuery = useQuery<ErpStatus>({
    queryKey: ['erp-status', 'pessoa-detail'],
    queryFn: () => apiFetch('/integracoes/erp/status'),
    retry: false,
  });
  const erpStatus = erpStatusQuery.data;
  const erpPoliciesQuery = useQuery<ErpPolicy[]>({
    queryKey: ['erp-sync-policies'],
    queryFn: () => apiFetch('/integracoes/erp/policies'),
    enabled: Boolean(erpStatus?.configurado),
    retry: false,
  });
  const erpPolicies = erpPoliciesQuery.data ?? [];
  const erpManaged = isErpPeopleManaged(erpStatus, erpPolicies);
  const governanceLoading = erpStatusQuery.isLoading || (
    Boolean(erpStatus?.configurado) && erpPoliciesQuery.isLoading
  );
  const governanceError = erpStatusQuery.isError || erpPoliciesQuery.isError;
  const governanceResolved = !governanceLoading && !governanceError;
  const { data: associationData } = useQuery<ErpAssociationsResponse>({
    queryKey: ['erp-person-association', id],
    queryFn: () => apiFetch(
      `/integracoes/erp/associacoes?feature_code=pessoas&entity_type=Pessoa&search=${encodeURIComponent(id)}&limit=10`,
    ),
    enabled: erpManaged && Boolean(id),
    retry: false,
  });
  const personAssociation = associationData?.items.find((item) => item.local_entity_id === id);

  React.useEffect(() => {
    if (personAssociation?.external_id) setExternalId(personAssociation.external_id);
  }, [personAssociation?.external_id]);

  const lookupErp = useMutation({
    mutationFn: () => apiFetch<ErpPersonRecord>('/integracoes/erp/pessoas/lookup', {
      method: 'POST', body: JSON.stringify({ external_id: externalId.trim() }),
    }),
    onSuccess: (record) => setErpPreview(record),
    onError: (err: Error) => { setErpPreview(null); toast.error(err.message); },
  });

  const importErp = useMutation({
    mutationFn: () => apiFetch('/integracoes/erp/pessoas/import', {
      method: 'POST',
      body: JSON.stringify({ external_id: externalId.trim(), pessoa_id: id }),
    }),
    onSuccess: async () => {
      toast.success('Pessoa atualizada com os dados do ERP');
      setErpPreview(null);
      await Promise.all([
        qc.invalidateQueries({ queryKey: ['pessoa', id] }),
        qc.invalidateQueries({ queryKey: ['pessoa-pii', id] }),
        qc.invalidateQueries({ queryKey: ['pessoa-contatos', id] }),
        qc.invalidateQueries({ queryKey: ['erp-person-association', id] }),
      ]);
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const updatePessoa = useMutation({
    mutationFn: (data: { nome_exibicao?: string; base_legal?: string; ativo?: boolean }) =>
      apiFetch(`/cadastros/pessoas/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
    onSuccess: () => {
      toast.success('Dados atualizados');
      qc.invalidateQueries({ queryKey: ['pessoa', id] });
      setEditingHeader(false);
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const updatePii = useMutation({
    mutationFn: (data: PII) =>
      apiFetch(`/cadastros/pessoas/${id}/pii`, { method: 'PATCH', body: JSON.stringify(data) }),
    onSuccess: () => {
      toast.success('Dados pessoais atualizados');
      qc.invalidateQueries({ queryKey: ['pessoa-pii', id] });
      setEditingPii(false);
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const anonimizar = useMutation({
    mutationFn: () => apiFetch(`/cadastros/pessoas/${id}/anonimizar`, { method: 'POST' }),
    onSuccess: () => { toast.success('Pessoa anonimizada'); qc.invalidateQueries({ queryKey: ['pessoa', id] }); },
    onError: (err: Error) => toast.error(err.message),
  });

  const startEditHeader = () => {
    if (!pessoa || !governanceResolved) return;
    setEditingHeader(true);
  };

  const handleVerPII = () => {
    setPiiVisible(true);
    fetchPII().then((res) => {
      setPiiEdit({ ...(res.data ?? {}) });
    });
  };

  const startEditPII = () => {
    setPiiEdit({ ...(pii ?? {}) });
    setEditingPii(true);
  };

  const cancelEditPII = () => {
    setPiiEdit({ ...(pii ?? {}) });
    setEditingPii(false);
  };

  if (isLoading) {
    return (
      <div className="p-6 max-w-7xl space-y-6">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-10 w-full" />
      </div>
    );
  }

  if (isError || !pessoa) {
    return (
      <div className="p-6 max-w-3xl">
        <Alert variant="destructive">
          <AlertTriangle className="size-4" />
          <AlertTitle>Não foi possível carregar a pessoa</AlertTitle>
          <AlertDescription>
            {error instanceof Error ? error.message : 'Verifique o contexto ativo, a conexão com o banco ou tente novamente.'}
          </AlertDescription>
        </Alert>
        <div className="mt-4 flex flex-wrap gap-2">
          <Button variant="outline" onClick={() => refetch()}>
            Tentar novamente
          </Button>
          <Button asChild variant="ghost">
            <Link href="/cadastros/pessoas">
              Voltar para Pessoas
            </Link>
          </Button>
        </div>
      </div>
    );
  }

  const isAnon = !!pessoa.anonimizado_em;
  const hasPiiData = Boolean(
    pii?.nome_completo ||
    pii?.cpf ||
    pii?.rg ||
    pii?.data_nascimento ||
    pii?.nome_mae ||
    pii?.razao_social ||
    pii?.cnpj ||
    pii?.ie ||
    pii?.nome_fantasia ||
    pii?.data_fundacao
  );

  return (
    <div className="p-6 space-y-6 max-w-7xl">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Button asChild variant="ghost" size="icon-sm" aria-label="Voltar para pessoas" title="Voltar">
          <Link href="/cadastros/pessoas">
            <ArrowLeft />
          </Link>
        </Button>
        <span className="text-muted-foreground text-sm">Cadastros</span>
        <span className="text-muted-foreground text-sm">/</span>
        <Link href="/cadastros/pessoas" className="text-sm text-muted-foreground hover:text-foreground hover:underline">
          Pessoas
        </Link>
      </div>

      {/* Person card */}
      <Card className="shadow-sm">
        <CardContent className="p-5">
          {editingHeader ? (
            <HeaderEditForm
              pessoa={pessoa}
              erpManaged={erpManaged}
              onCancel={() => setEditingHeader(false)}
              onSave={(data) => updatePessoa.mutate(data)}
              isPending={updatePessoa.isPending}
            />
          ) : (
            <div className="flex items-start gap-4">
              {/* Avatar */}
              <div className={`size-12 rounded-full flex items-center justify-center text-lg font-bold shrink-0 ${isAnon
                  ? 'bg-muted text-muted-foreground'
                  : pessoa.tipo === 'PJ'
                    ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300'
                    : 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300'
                }`}>
                {isAnon ? '?' : getInitials(pessoa.nome_exibicao)}
              </div>

              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <h1 className="text-lg font-semibold">{pessoa.nome_exibicao}</h1>
                  {!pessoa.ativo && !isAnon && (
                    <StatusBadge status="inativo" />
                  )}
                  {isAnon && (
                    <Badge variant="secondary" className="text-xs bg-orange-100 text-orange-700 border-orange-200">Anonimizado</Badge>
                  )}
                </div>
                <div className="flex items-center gap-2 mt-1.5 flex-wrap">
                  <Badge variant="outline" className="text-xs">
                    {pessoa.tipo === 'PF' ? 'Pessoa Física' : 'Pessoa Jurídica'}
                  </Badge>
                  <Badge variant="outline" className="text-xs text-muted-foreground">
                    LGPD: {BASE_LEGAL_LABEL[pessoa.base_legal] ?? pessoa.base_legal}
                  </Badge>
                </div>
              </div>

              {!isAnon && (
                <DropdownMenu>
                  <DropdownMenuTrigger render={
                    <Button variant="ghost" size="icon-sm" aria-label="Ações da pessoa" title="Ações">
                      <MoreVertical />
                    </Button>
                  } />
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem
                      onClick={startEditHeader}
                      className="gap-2"
                      disabled={!governanceResolved}
                    >
                      <Pencil className="size-4" />
                      {erpManaged ? 'Editar base legal' : 'Editar dados'}
                    </DropdownMenuItem>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem
                      className="gap-2"
                      onClick={() => updatePessoa.mutate({ ativo: !pessoa.ativo })}
                      disabled={updatePessoa.isPending}
                    >
                      {pessoa.ativo
                        ? <><PowerOff className="size-4 text-orange-500" /> Desativar</>
                        : <><Power className="size-4 text-green-500" /> Reativar</>
                      }
                    </DropdownMenuItem>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem
                      className="gap-2 text-destructive focus:text-destructive"
                      onClick={() => setAnonDialogOpen(true)}
                      disabled={anonimizar.isPending}
                    >
                      <AlertTriangle className="size-4" /> Anonimizar (LGPD)
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {governanceError && (
        <Alert variant="destructive">
          <AlertTitle>Não foi possível verificar a governança do ERP</AlertTitle>
          <AlertDescription>
            A edição de campos cadastrais foi bloqueada por segurança. Recarregue a página e tente novamente.
          </AlertDescription>
        </Alert>
      )}

      {erpManaged && !isAnon && (
        <Card className="border-primary/20 shadow-sm">
          <CardHeader className="pb-3">
            <div className="flex items-center gap-2">
              <CloudDownload className="size-4 text-primary" />
              <div>
                <p className="text-sm font-semibold">Atualização pelo ERP</p>
                <p className="text-xs text-muted-foreground">
                  Informe o ID da pessoa no ERP para consultar e atualizar os dados cadastrais.
                </p>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex flex-col gap-2 sm:flex-row">
              <Input
                value={externalId}
                onChange={(event) => { setExternalId(event.target.value); setErpPreview(null); }}
                placeholder="ID da pessoa no ERP"
                className="sm:max-w-xs"
              />
              <Button
                type="button"
                variant="outline"
                onClick={() => lookupErp.mutate()}
                disabled={!externalId.trim() || lookupErp.isPending}
              >
                {lookupErp.isPending ? <Loader2 className="animate-spin" /> : <Search />}
                Consultar no ERP
              </Button>
            </div>
            {personAssociation && !erpPreview && (
              <p className="text-xs text-muted-foreground">
                Vínculo atual: ID {personAssociation.external_id}
                {personAssociation.last_sync_at
                  ? ` · atualizado em ${new Date(personAssociation.last_sync_at).toLocaleString('pt-BR')}`
                  : ''}
              </p>
            )}
            {erpPreview && (
              <Alert>
                <AlertTitle>{erpPreview.nome_exibicao}</AlertTitle>
                <AlertDescription className="space-y-2">
                  <p>
                    {erpPreview.tipo === 'PF' ? 'Pessoa física' : 'Pessoa jurídica'}
                    {' · '}{erpPreview.cpf || erpPreview.cnpj || 'sem documento informado'}
                  </p>
                  <Button
                    size="sm"
                    onClick={() => importErp.mutate()}
                    disabled={importErp.isPending}
                  >
                    {importErp.isPending && <Loader2 className="animate-spin" />}
                    Aplicar atualização
                  </Button>
                </AlertDescription>
              </Alert>
            )}
          </CardContent>
        </Card>
      )}

      {/* Tabs */}
      <Tabs defaultValue="dados">
        <TabsList className="w-full justify-start h-auto gap-1 bg-transparent p-0 border-b rounded-none">
          <TabsTrigger value="dados"
            className="rounded-none border-b-2 border-transparent data-[selected]:border-primary data-[selected]:bg-accent transition-all hover:bg-accent gap-1.5 px-3 py-2">
            <User className="size-3.5" /> Dados Pessoais
          </TabsTrigger>
          <TabsTrigger value="contatos"
            className="rounded-none border-b-2 border-transparent data-[selected]:border-primary data-[selected]:bg-accent transition-all hover:bg-accent gap-1.5 px-3 py-2">
            <Phone className="size-3.5" /> Contatos
          </TabsTrigger>
          <TabsTrigger value="enderecos"
            className="rounded-none border-b-2 border-transparent data-[selected]:border-primary data-[selected]:bg-accent transition-all hover:bg-accent gap-1.5 px-3 py-2">
            <MapPin className="size-3.5" /> Endereços
          </TabsTrigger>
          <TabsTrigger value="bancario"
            className="rounded-none border-b-2 border-transparent data-[selected]:border-primary data-[selected]:bg-accent transition-all hover:bg-accent gap-1.5 px-3 py-2">
            <CreditCard className="size-3.5" /> Bancário
          </TabsTrigger>
          <TabsTrigger value="vinculos"
            className="rounded-none border-b-2 border-transparent data-[selected]:border-primary data-[selected]:bg-accent transition-all hover:bg-accent gap-1.5 px-3 py-2">
            <Link2 className="size-3.5" /> Vínculos
          </TabsTrigger>
        </TabsList>

        {/* Tab — Dados Pessoais (PII) */}
        <TabsContent value="dados" className="pt-4">
          {!piiVisible ? (
            <Card className="border-dashed bg-muted/20 shadow-none">
              <CardContent className="flex flex-col items-center gap-4 p-8 text-center">
              <div className="size-12 rounded-full bg-muted flex items-center justify-center">
                <ShieldAlert className="size-5 text-muted-foreground" />
              </div>
              <div>
                <p className="text-sm font-medium">Dados protegidos (LGPD)</p>
                <p className="text-xs text-muted-foreground mt-1 max-w-xs">
                  O acesso a dados pessoais sensíveis é registrado conforme o Art. 37 da LGPD.
                </p>
              </div>
              <div className="flex items-center gap-2">
                <Input
                  placeholder="Motivo do acesso (opcional)"
                  value={motivoPII}
                  onChange={(e) => setMotivoPII(e.target.value)}
                  className="w-60 text-sm h-8"
                  onKeyDown={(e) => e.key === 'Enter' && handleVerPII()}
                />
                <Button size="sm" onClick={handleVerPII} disabled={piiLoading}>
                  <Eye data-icon="inline-start" /> {piiLoading ? 'Carregando...' : 'Ver Dados'}
                </Button>
              </div>
              </CardContent>
            </Card>
          ) : (
            <Card className="overflow-hidden shadow-sm">
              <CardHeader className="border-b bg-muted/30 px-5 py-3">
                <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-2 text-sm">
                  <ShieldAlert className="size-4 text-orange-500" />
                  <span className="font-medium">Dados pessoais sensíveis</span>
                  {pii?.updated_at && (
                    <span className="text-xs text-muted-foreground">
                      · atualizado em {new Date(pii.updated_at).toLocaleDateString('pt-BR')}
                    </span>
                  )}
                </div>
                <div className="flex gap-2">
                  {editingPii ? (
                    <>
                      <Button size="sm" variant="outline" onClick={cancelEditPII}>
                        <X data-icon="inline-start" /> Cancelar
                      </Button>
                      <Button size="sm" type="submit" form="pessoa-pii-edit-form" disabled={updatePii.isPending}>
                        <Check data-icon="inline-start" /> {updatePii.isPending ? 'Salvando...' : 'Salvar'}
                      </Button>
                    </>
                  ) : (
                    !isAnon && governanceResolved && (
                      <Button size="sm" variant="outline" onClick={startEditPII}>
                        <Pencil data-icon="inline-start" /> Editar
                      </Button>
                    )
                  )}
                </div>
                </div>
              </CardHeader>
              <CardContent className="p-5">
                {editingPii ? (
                  <PiiEditForm
                    pessoa={pessoa}
                    erpManaged={erpManaged}
                    initial={piiEdit}
                    onSave={(data) => updatePii.mutate(data)}
                    onCancel={cancelEditPII}
                    isPending={updatePii.isPending}
                  />
                ) : !hasPiiData ? (
                  <Alert>
                    <ShieldAlert className="size-4" />
                    <AlertTitle>Nenhum dado pessoal cadastrado</AlertTitle>
                    <AlertDescription>
                      {erpManaged
                        ? 'Use a atualização pelo ID do ERP no topo da página para carregar CPF/CNPJ e os demais dados cadastrais.'
                        : 'Use a ação “Editar” para cadastrar CPF/CNPJ, RG, razão social ou demais informações.'}
                    </AlertDescription>
                  </Alert>
                ) : (
                  <div className="grid grid-cols-3 gap-4">
                    {pessoa.tipo === 'PJ' ? (
                      <>
                        <FieldView label="CNPJ" value={pii?.cnpj} />
                        <FieldView label="Razão Social" value={pii?.razao_social} className="col-span-2" />
                        <FieldView label="Nome Fantasia" value={pii?.nome_fantasia} className="col-span-2" />
                        <FieldView label="Inscrição Estadual" value={pii?.ie} />
                        <FieldView label="Data de Fundação" value={pii?.data_fundacao ? new Date(pii.data_fundacao).toLocaleDateString('pt-BR') : undefined} />
                      </>
                    ) : (
                      <>
                        <FieldView label="Nome Completo" value={pii?.nome_completo} className="col-span-2" />
                        <FieldView label="CPF" value={pii?.cpf} />
                        <FieldView label="RG" value={pii?.rg} />
                        <FieldView label="Nome da Mãe" value={pii?.nome_mae} className="col-span-2" />
                        <FieldView label="Data de Nascimento" value={pii?.data_nascimento ? new Date(pii.data_nascimento).toLocaleDateString('pt-BR') : undefined} />
                      </>
                    )}
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="contatos">
          <TabContatos
            pessoaId={id}
            readOnly={erpManaged || !governanceResolved}
            readOnlyMessage={!governanceResolved
              ? 'A edição foi bloqueada até que a governança do ERP seja verificada.'
              : undefined}
          />
        </TabsContent>

        <TabsContent value="enderecos">
          <TabEnderecos pessoaId={id} />
        </TabsContent>

        <TabsContent value="bancario">
          <TabBancario pessoaId={id} />
        </TabsContent>

        <TabsContent value="vinculos">
          <TabRelacionamentos pessoaId={id} relacionamentos={pessoa.relacionamentos} />
        </TabsContent>
      </Tabs>

      {/* Anonimizar Confirmation Dialog */}
      <AlertDialog open={anonDialogOpen} onOpenChange={setAnonDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Anonimizar pessoa?</AlertDialogTitle>
            <AlertDialogDescription>
              Esta ação é <strong>irreversível</strong>. Todos os dados pessoais serão permanentemente removidos conforme o direito ao esquecimento (LGPD Art. 17).
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              variant="destructive"
              onClick={() => anonimizar.mutate()}
              disabled={anonimizar.isPending}
            >
              {anonimizar.isPending ? 'Anonimizando...' : 'Anonimizar'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

function FieldView({ label, value, className }: { label: string; value?: string | null; className?: string }) {
  return (
    <div className={`space-y-1 ${className ?? ''}`}>
      <p className="text-xs text-muted-foreground font-medium uppercase tracking-wide">{label}</p>
      <p className="text-sm">{value || <span className="text-muted-foreground/50">—</span>}</p>
    </div>
  );
}

/* ── Header Edit Form (usando Form padrão) ── */
interface HeaderEditFormProps {
  pessoa: PessoaResponse;
  erpManaged: boolean;
  onCancel: () => void;
  onSave: (data: { nome_exibicao: string; base_legal: string }) => void;
  isPending: boolean;
}

type HeaderFormData = { nome_exibicao: string; base_legal: string };

function HeaderEditForm({ pessoa, erpManaged, onCancel, onSave, isPending }: HeaderEditFormProps) {
  const form = useForm<HeaderFormData>({
    defaultValues: { nome_exibicao: pessoa.nome_exibicao, base_legal: pessoa.base_legal },
  });

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSave)} className="space-y-4">
        <div className="grid grid-cols-[2fr_1fr] gap-4">
          <FormField
            control={form.control}
            name="nome_exibicao"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Nome de exibição</FormLabel>
                <FormControl>
                  <Input {...field} autoFocus={!erpManaged} disabled={erpManaged} />
                </FormControl>
                {erpManaged && (
                  <p className="text-xs text-muted-foreground">Nome mantido pelo ERP.</p>
                )}
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
                <Select onValueChange={field.onChange} value={field.value}>
                  <FormControl>
                    <SelectTrigger><SelectValue /></SelectTrigger>
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
        </div>
        <div className="flex gap-2 justify-end">
          <Button size="sm" variant="outline" type="button" onClick={onCancel}>
            <X data-icon="inline-start" /> Cancelar
          </Button>
          <Button size="sm" type="submit" disabled={isPending}>
            <Check data-icon="inline-start" /> {isPending ? 'Salvando...' : 'Salvar'}
          </Button>
        </div>
      </form>
    </Form>
  );
}

/* ── PII Edit Form (usando Form padrão) ── */
interface PiiEditFormProps {
  pessoa: PessoaResponse;
  erpManaged: boolean;
  initial: PII;
  onSave: (data: PII) => void;
  onCancel: () => void;
  isPending: boolean;
}

function PiiEditForm({ pessoa, erpManaged, initial, onSave, onCancel, isPending }: PiiEditFormProps) {
  const form = useForm<PII>({ defaultValues: initial });

  React.useEffect(() => {
    form.reset(initial);
  }, [initial, form]);

  return (
    <Form {...form}>
      <form id="pessoa-pii-edit-form" onSubmit={form.handleSubmit(onSave)} className="p-5">
        <div className="grid grid-cols-3 gap-4">
          {pessoa.tipo === 'PJ' ? (
            <>
              <FormField control={form.control} name="cnpj" render={({ field }) => (
                <FormItem>
                  <FormLabel>CNPJ</FormLabel>
                  <FormControl><Input {...field} value={field.value ?? ''} disabled={erpManaged} className="h-8 text-sm" /></FormControl>
                  <FormMessage />
                </FormItem>
              )} />
              <FormField control={form.control} name="razao_social" render={({ field }) => (
                <FormItem className="col-span-2">
                  <FormLabel>Razão Social</FormLabel>
                  <FormControl><Input {...field} value={field.value ?? ''} disabled={erpManaged} className="h-8 text-sm" /></FormControl>
                  <FormMessage />
                </FormItem>
              )} />
              <FormField control={form.control} name="nome_fantasia" render={({ field }) => (
                <FormItem className="col-span-2">
                  <FormLabel>Nome Fantasia</FormLabel>
                  <FormControl><Input {...field} value={field.value ?? ''} disabled={erpManaged} className="h-8 text-sm" /></FormControl>
                  <FormMessage />
                </FormItem>
              )} />
              <FormField control={form.control} name="ie" render={({ field }) => (
                <FormItem>
                  <FormLabel>Inscrição Estadual</FormLabel>
                  <FormControl><Input {...field} value={field.value ?? ''} disabled={erpManaged} className="h-8 text-sm" /></FormControl>
                  <FormMessage />
                </FormItem>
              )} />
              <FormField control={form.control} name="data_fundacao" render={({ field }) => (
                <FormItem>
                  <FormLabel>Data de Fundação</FormLabel>
                  <FormControl><Input type="date" {...field} value={field.value ?? ''} className="h-8 text-sm" /></FormControl>
                  <FormMessage />
                </FormItem>
              )} />
            </>
          ) : (
            <>
              <FormField control={form.control} name="nome_completo" render={({ field }) => (
                <FormItem className="col-span-2">
                  <FormLabel>Nome Completo</FormLabel>
                  <FormControl><Input {...field} value={field.value ?? ''} disabled={erpManaged} className="h-8 text-sm" /></FormControl>
                  <FormMessage />
                </FormItem>
              )} />
              <FormField control={form.control} name="cpf" render={({ field }) => (
                <FormItem>
                  <FormLabel>CPF</FormLabel>
                  <FormControl><Input {...field} value={field.value ?? ''} disabled={erpManaged} className="h-8 text-sm" /></FormControl>
                  <FormMessage />
                </FormItem>
              )} />
              <FormField control={form.control} name="rg" render={({ field }) => (
                <FormItem>
                  <FormLabel>RG</FormLabel>
                  <FormControl><Input {...field} value={field.value ?? ''} className="h-8 text-sm" /></FormControl>
                  <FormMessage />
                </FormItem>
              )} />
              <FormField control={form.control} name="nome_mae" render={({ field }) => (
                <FormItem className="col-span-2">
                  <FormLabel>Nome da Mãe</FormLabel>
                  <FormControl><Input {...field} value={field.value ?? ''} className="h-8 text-sm" /></FormControl>
                  <FormMessage />
                </FormItem>
              )} />
              <FormField control={form.control} name="data_nascimento" render={({ field }) => (
                <FormItem>
                  <FormLabel>Data de Nascimento</FormLabel>
                  <FormControl><Input type="date" {...field} value={field.value ?? ''} className="h-8 text-sm" /></FormControl>
                  <FormMessage />
                </FormItem>
              )} />
            </>
          )}
        </div>
        <div className="flex gap-2 justify-end mt-4">
          <Button size="sm" variant="outline" type="button" onClick={onCancel}>
            <X data-icon="inline-start" /> Cancelar
          </Button>
          <Button size="sm" type="submit" disabled={isPending}>
            <Check data-icon="inline-start" /> {isPending ? 'Salvando...' : 'Salvar'}
          </Button>
        </div>
      </form>
    </Form>
  );
}
