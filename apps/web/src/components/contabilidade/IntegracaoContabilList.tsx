'use client';

import { useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { StatusBadge } from '@/components/ui/status-badge';
import { Plus, Trash2, Download } from 'lucide-react';
import { getApiBaseUrl } from '@/lib/runtime-config';
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

interface IntegracaoContabil {
  id: number;
  tenant_id: string;
  sistema: string;
  nome: string;
  ativo: boolean;
  ultima_exportacao?: string;
  created_at: string;
}

export function IntegracaoContabilList() {
  const [integracoes, setIntegracoes] = useState<IntegracaoContabil[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchIntegracoes();
  }, []);

  const fetchIntegracoes = async () => {
    try {
      const response = await fetch(`${getApiBaseUrl()}/contabilidade/integracoes`, {
        credentials: 'include',
      });
      if (response.ok) {
        const data = await response.json();
        setIntegracoes(data);
      }
    } catch (error) {
      console.error('Erro ao buscar integrações:', error);
    } finally {
      setLoading(false);
    }
  };

  const [deleteId, setDeleteId] = useState<number | null>(null);

  const handleDelete = async (id: number) => {
    setDeleteId(id);
  };

  const handleConfirmDelete = async () => {
    if (deleteId === null) return;
    try {
      const response = await fetch(
        `${getApiBaseUrl()}/contabilidade/integracoes/${deleteId}`,
        {
          method: 'DELETE',
          credentials: 'include',
        }
      );
      if (response.ok) {
        fetchIntegracoes();
      }
    } catch (error) {
      console.error('Erro ao remover integração:', error);
    } finally {
      setDeleteId(null);
    }
  };

  const getSistemaLabel = (sistema: string) => {
    const labels: Record<string, string> = {
      dominio: 'Domínio Sistemas',
      fortes: 'Fortes Contábil',
      contmatic: 'Contmatic',
    };
    return labels[sistema] || sistema;
  };

  if (loading) {
    return <div>Carregando...</div>;
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Integrações Contábeis</CardTitle>
        <CardDescription>
          Sistemas contábeis integrados para exportação de lançamentos
        </CardDescription>
      </CardHeader>
      <CardContent>
        {integracoes.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            Nenhuma integração cadastrada
          </p>
        ) : (
          <div className="space-y-4">
            {integracoes.map((integracao) => (
              <div
                key={integracao.id}
                className="flex items-center justify-between p-4 border rounded-lg"
              >
                <div className="flex items-center gap-4">
                  <div>
                    <h3 className="font-semibold">{integracao.nome}</h3>
                    <p className="text-sm text-muted-foreground">
                      {getSistemaLabel(integracao.sistema)}
                    </p>
                  </div>
                  <StatusBadge status={integracao.ativo ? 'ativo' : 'inativo'} />
                </div>
                <div className="flex items-center gap-2">
                  {integracao.ultima_exportacao && (
                    <span className="text-xs text-muted-foreground">
                      Última: {new Date(integracao.ultima_exportacao).toLocaleDateString('pt-BR')}
                    </span>
                  )}
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => handleDelete(integracao.id)}
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
