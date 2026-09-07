'use client';

import { useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Download } from 'lucide-react';
import { getApiBaseUrl } from '@/lib/runtime-config';

interface ExportacaoContabil {
  id: number;
  tenant_id: string;
  integracao_id: number;
  tipo: string;
  periodo_inicio: string;
  periodo_fim: string;
  arquivo_nome?: string;
  arquivo_formato?: string;
  status: string;
  registros_exportados: number;
  created_at: string;
  processada_em?: string;
}

export function ExportacaoContabilList() {
  const [exportacoes, setExportacoes] = useState<ExportacaoContabil[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchExportacoes();
  }, []);

  const fetchExportacoes = async () => {
    try {
      const response = await fetch(
        `${getApiBaseUrl()}/contabilidade/exportacoes`,
        {
          credentials: 'include',
        }
      );
      if (response.ok) {
        const data = await response.json();
        setExportacoes(data);
      }
    } catch (error) {
      console.error('Erro ao buscar exportações:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = async (id: number) => {
    try {
      const response = await fetch(
        `${getApiBaseUrl()}/contabilidade/exportacoes/${id}/download`,
        {
          credentials: 'include',
        }
      );
      if (response.ok) {
        const data = await response.json();
        alert(`Arquivo disponível: ${data.arquivo} (${data.formato})`);
      }
    } catch (error) {
      console.error('Erro ao baixar arquivo:', error);
    }
  };

  const getStatusBadge = (status: string) => {
    const variants: Record<string, 'default' | 'secondary' | 'destructive'> = {
      pendente: 'secondary',
      processando: 'secondary',
      concluida: 'default',
      erro: 'destructive',
    };
    return variants[status] || 'secondary';
  };

  const getTipoLabel = (tipo: string) => {
    const labels: Record<string, string> = {
      lancamentos: 'Lançamentos',
      notas_fiscais: 'Notas Fiscais',
      folha: 'Folha de Pagamento',
    };
    return labels[tipo] || tipo;
  };

  if (loading) {
    return <div>Carregando...</div>;
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Exportações Contábeis</CardTitle>
        <CardDescription>
          Histórico de exportações para sistemas contábeis
        </CardDescription>
      </CardHeader>
      <CardContent>
        {exportacoes.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            Nenhuma exportação realizada
          </p>
        ) : (
          <div className="space-y-2">
            {exportacoes.map((exportacao) => (
              <div
                key={exportacao.id}
                className="flex items-center justify-between p-3 border rounded"
              >
                <div className="flex items-center gap-4">
                  <div>
                    <h4 className="font-medium">{getTipoLabel(exportacao.tipo)}</h4>
                    <p className="text-xs text-muted-foreground">
                      {new Date(exportacao.periodo_inicio).toLocaleDateString('pt-BR')} - {new Date(exportacao.periodo_fim).toLocaleDateString('pt-BR')}
                    </p>
                  </div>
                  <Badge variant={getStatusBadge(exportacao.status)}>
                    {exportacao.status}
                  </Badge>
                  <span className="text-xs text-muted-foreground">
                    {exportacao.registros_exportados} registros
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  {exportacao.status === 'concluida' && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleDownload(exportacao.id)}
                    >
                      <Download className="w-4 h-4 mr-2" />
                      {exportacao.arquivo_nome || 'Download'}
                    </Button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
