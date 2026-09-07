'use client';

import * as React from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { apiFetch } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { StatusBadge } from '@/components/ui/status-badge';
import { DataTable, ColumnDef } from '@/components/ui/data-table';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import { UserPlus, User, Building2, Eye, Users } from 'lucide-react';
import Link from 'next/link';
import { PessoaFormDialog } from './_components/pessoa-form-dialog';
import { PageHeader } from '@/components/shared/page-header';

export interface TipoRel { id: string; nome: string; cor: string }
export interface Pessoa {
  id: string;
  tipo: 'PF' | 'PJ';
  nome_exibicao: string;
  base_legal: string;
  ativo: boolean;
  anonimizado_em: string | null;
  relacionamentos: { id: string; tipo: TipoRel }[];
}

const BASE_LEGAL_LABEL: Record<string, string> = {
  CONTRATO: 'Contrato',
  CONSENTIMENTO: 'Consentimento',
  INTERESSE_LEGITIMO: 'Int. Legítimo',
  OBRIGACAO_LEGAL: 'Obrigação Legal',
  EXECUCAO_POLITICAS: 'Políticas Públicas',
};

export function PessoasClient({ initialPessoas }: { initialPessoas: Pessoa[] }) {
  const qc = useQueryClient();
  const [tipo, setTipo] = React.useState<string>('all');
  const [open, setOpen] = React.useState(false);

  const { data: pessoas = [], isLoading } = useQuery<Pessoa[]>({
    queryKey: ['pessoas', tipo],
    queryFn: () => {
      const qs = tipo !== 'all' ? `?tipo=${tipo}` : '';
      return apiFetch(`/cadastros/pessoas${qs}`);
    },
    initialData: tipo === 'all' ? initialPessoas : undefined,
  });

  const columns: ColumnDef<Pessoa>[] = [
    {
      id: 'nome',
      header: 'Nome',
      accessorKey: 'nome_exibicao',
      cell: (value, row) => (
        <div className="flex items-center gap-2">
          {row.tipo === 'PF' ? (
            <User className="size-4 text-muted-foreground" />
          ) : (
            <Building2 className="size-4 text-muted-foreground" />
          )}
          {row.anonimizado_em ? (
            <span className="italic text-muted-foreground font-medium">{value}</span>
          ) : (
            <span className="font-medium">{value}</span>
          )}
        </div>
      ),
    },
    {
      id: 'tipo',
      header: 'Tipo de Pessoa',
      accessorFn: (row) => (row.tipo === 'PF' ? 'Física' : 'Jurídica'),
      filterOptions: [
        { label: 'Física', value: 'Física' },
        { label: 'Jurídica', value: 'Jurídica' },
      ],
      cell: (value) => (
        <Badge variant="outline" className="rounded-sm">
          {value}
        </Badge>
      ),
      exportFormat: (value) => value,
    },
    {
      id: 'vinculos',
      header: 'Vínculos',
      accessorFn: (row) => row.relacionamentos.map((r) => r.tipo.nome).join(', '),
      cell: (_, row) => (
        <div className="flex flex-wrap gap-1">
          {row.relacionamentos.map((r) => (
            <Badge
              key={r.id}
              style={{
                backgroundColor: r.tipo.cor + '22',
                color: r.tipo.cor,
                borderColor: r.tipo.cor + '55',
              }}
              variant="outline"
              className="text-xs rounded-sm"
            >
              {r.tipo.nome}
            </Badge>
          ))}
        </div>
      ),
    },
    {
      id: 'base_legal',
      header: 'Base Legal',
      accessorFn: (row) => BASE_LEGAL_LABEL[row.base_legal] ?? row.base_legal,
      filterOptions: Object.entries(BASE_LEGAL_LABEL).map(([val, label]) => ({
        label,
        value: label,
      })),
      cell: (value) => (
        <span className="text-sm text-muted-foreground">
          {value}
        </span>
      ),
      exportFormat: (value) => value,
    },
    {
      id: 'status',
      header: 'Status',
      accessorFn: (row) =>
        row.anonimizado_em ? 'anonimizado' : row.ativo ? 'ativo' : 'inativo',
      cell: (_, row) =>
        row.anonimizado_em ? (
          <StatusBadge status="inativo" label="Anonimizado" />
        ) : (
          <StatusBadge status={row.ativo ? 'ativo' : 'inativo'} />
        ),
      exportFormat: (_, row) =>
        row.anonimizado_em ? 'Anonimizado' : row.ativo ? 'Ativo' : 'Inativo',
    },
    {
      id: 'acoes',
      header: '',
      exportable: false,
      sortable: false,
      filterable: false,
      cell: (_, row) => (
        <div className="flex items-center gap-0 justify-end">
          <Button
            size="icon"
            variant="ghost"
            className="size-7 text-primary hover:text-primary"
            asChild
          >
            <Link href={`/cadastros/pessoas/${row.id}`}>
              <Eye className="size-3.5" />
            </Link>
          </Button>
        </div>
      ),
    },
  ];

  return (
    <div className="p-6 space-y-6">
      <PageHeader
        title="Pessoas & Parceiros"
        description="Fornecedores, clientes, colaboradores e outros vínculos"
        icon={<Users className="text-primary" size={22} />}
        breadcrumbs={[{ label: "Cadastros", href: "/cadastros" }, { label: "Pessoas & Parceiros" }]}
        actions={
          <Button size="sm" variant="outline" onClick={() => setOpen(true)}>
            <UserPlus className="size-4 mr-2" />
            Nova Pessoa
          </Button>
        }
      />

      <div className="flex gap-3">
        <Select value={tipo} onValueChange={setTipo}>
          <SelectTrigger className="w-36">
            <SelectValue placeholder="Tipo" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todos</SelectItem>
            <SelectItem value="PF">Pessoa Física</SelectItem>
            <SelectItem value="PJ">Pessoa Jurídica</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {isLoading ? (
        <div className="text-center py-12 text-muted-foreground">
          Carregando...
        </div>
      ) : (
        <DataTable
          data={pessoas}
          columns={columns}
          searchPlaceholder="Buscar por nome ou vínculo..."
          exportFileName="pessoas"
          emptyMessage="Nenhuma pessoa encontrada"
        />
      )}

      <PessoaFormDialog
        open={open}
        onOpenChange={setOpen}
        onSuccess={() => {
          setOpen(false);
          qc.invalidateQueries({ queryKey: ['pessoas'] });
        }}
      />
    </div>
  );
}
