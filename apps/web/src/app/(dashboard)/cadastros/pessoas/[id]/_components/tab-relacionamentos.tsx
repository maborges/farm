'use client';

import * as React from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiFetch } from '@/lib/api';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Plus, X } from 'lucide-react';

interface TipoRel { id: string; nome: string; cor: string }
interface UnidadeProdutiva { id: string; nome: string }
interface Relacionamento {
  id: string;
  tipo: TipoRel;
  unidade_produtiva_id?: string | null;
  unidade_produtiva?: UnidadeProdutiva | null;
  observacoes?: string;
}

interface Props {
  pessoaId: string;
  relacionamentos: Relacionamento[];
}

export function TabRelacionamentos({ pessoaId, relacionamentos }: Props) {
  const qc = useQueryClient();
  const [adding, setAdding] = React.useState(false);
  const [selectedTipoId, setSelectedTipoId] = React.useState<string | null>(null);
  const [selectedUnidadeId, setSelectedUnidadeId] = React.useState<string | null>(null);

  const { data: tiposRel = [] } = useQuery<TipoRel[]>({
    queryKey: ['tipos-relacionamento'],
    queryFn: () => apiFetch('/cadastros/tipos-relacionamento'),
    enabled: adding,
  });

  const { data: unidadesProdutivas = [] } = useQuery<UnidadeProdutiva[]>({
    queryKey: ['unidades-produtivas'],
    queryFn: () => apiFetch('/unidades-produtivas'),
    enabled: adding,
  });

  const addMutation = useMutation({
    mutationFn: ({ tipo_id, unidade_produtiva_id }: { tipo_id: string; unidade_produtiva_id: string }) => apiFetch(`/cadastros/pessoas/${pessoaId}/relacionamentos`, {
      method: 'POST',
      body: JSON.stringify({ tipo_id, unidade_produtiva_id }),
    }),
    onSuccess: () => {
      toast.success('Vínculo adicionado');
      qc.invalidateQueries({ queryKey: ['pessoa', pessoaId] });
      setAdding(false);
      setSelectedTipoId(null);
      setSelectedUnidadeId(null);
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const removeMutation = useMutation({
    mutationFn: (relId: string) => apiFetch(`/cadastros/pessoas/${pessoaId}/relacionamentos/${relId}`, { method: 'DELETE' }),
    onSuccess: () => {
      toast.success('Vínculo removido');
      qc.invalidateQueries({ queryKey: ['pessoa', pessoaId] });
    },
    onError: (err: Error) => toast.error(err.message),
  });

  // Tipos que ainda não foram adicionados
  const tiposDisponiveis = tiposRel.filter(
    (t) => !relacionamentos.some((r) => r.tipo.id === t.id)
  );

  return (
    <div className="space-y-4 pt-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">{relacionamentos.length} vínculo(s)</p>
        <Button size="sm" variant="outline" onClick={() => setAdding(!adding)}>
          <Plus className="size-4 mr-1" /> Adicionar
        </Button>
      </div>

      {adding && (
        <div className="border rounded-sm p-4 space-y-3 bg-muted/20">
          <p className="text-sm font-medium">Selecione o tipo de vínculo:</p>
          <div className="flex flex-wrap gap-2">
            {tiposDisponiveis.map((t) => (
              <button
                key={t.id}
                onClick={() => setSelectedTipoId(t.id)}
                className="px-3 py-1.5 rounded-sm border text-sm font-medium transition-colors"
                style={{
                  backgroundColor: selectedTipoId === t.id ? t.cor + '33' : t.cor + '11',
                  borderColor: t.cor + '66',
                  color: t.cor,
                  outline: selectedTipoId === t.id ? `2px solid ${t.cor}` : 'none',
                }}
              >
                {t.nome}
              </button>
            ))}
            {tiposDisponiveis.length === 0 && (
              <p className="text-sm text-muted-foreground">Todos os vínculos disponíveis já foram adicionados.</p>
            )}
          </div>
          <div className="space-y-1.5">
            <p className="text-sm font-medium">Unidade produtiva</p>
            <Select value={selectedUnidadeId ?? ''} onValueChange={setSelectedUnidadeId}>
              <SelectTrigger className="h-8 rounded-sm">
                <SelectValue placeholder="Selecione a unidade produtiva" />
              </SelectTrigger>
              <SelectContent className="rounded-sm">
                {unidadesProdutivas.map((unidade) => (
                  <SelectItem key={unidade.id} value={unidade.id} className="rounded-sm">
                    {unidade.nome}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {unidadesProdutivas.length === 0 && (
              <p className="text-xs text-muted-foreground">Nenhuma unidade produtiva disponível neste produtor.</p>
            )}
          </div>
          <div className="flex justify-end gap-2 pt-1">
            <Button size="sm" variant="ghost" onClick={() => { setAdding(false); setSelectedTipoId(null); }}>Cancelar</Button>
            <Button
              size="sm"
              disabled={!selectedTipoId || !selectedUnidadeId || addMutation.isPending}
              onClick={() => selectedTipoId && selectedUnidadeId && addMutation.mutate({ tipo_id: selectedTipoId, unidade_produtiva_id: selectedUnidadeId })}
            >
              {addMutation.isPending ? 'Salvando...' : 'Adicionar'}
            </Button>
          </div>
        </div>
      )}

      {relacionamentos.length === 0 && !adding && (
        <p className="text-sm text-muted-foreground">Nenhum vínculo cadastrado.</p>
      )}

      <div className="flex flex-wrap gap-2">
        {relacionamentos.map((r) => (
          <div
            key={r.id}
            className="flex items-center gap-1.5 pl-3 pr-1.5 py-1 rounded-full border text-sm font-medium"
            style={{ backgroundColor: r.tipo.cor + '18', borderColor: r.tipo.cor + '55', color: r.tipo.cor }}
          >
            <span>{r.tipo.nome}</span>
            {r.unidade_produtiva?.nome && (
              <Badge variant="secondary" className="h-5 rounded-full px-2 text-[10px]">
                {r.unidade_produtiva.nome}
              </Badge>
            )}
            {!r.unidade_produtiva?.nome && r.unidade_produtiva_id && (
              <Badge variant="secondary" className="h-5 rounded-full px-2 text-[10px]">
                {r.unidade_produtiva_id.slice(0, 8)}
              </Badge>
            )}
            <button
              onClick={() => removeMutation.mutate(r.id)}
              className="rounded-full p-0.5 hover:bg-black/10 transition-colors"
              disabled={removeMutation.isPending}
            >
              <X className="size-3" />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
