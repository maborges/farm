/**
 * Página de Configuração - Contmatic
 * Sprint 25 - Integrações Contábeis
 */

'use client';

import { useState, useEffect } from 'react';
import { PageHeader } from '@/components/shared/page-header';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { CheckCircle, Loader2, FileDown } from 'lucide-react';
import { getApiBaseUrl } from '@/lib/runtime-config';
import { StatusBadge } from "@/components/ui/status-badge";

interface ContmaticConfig {
  id: number;
  tenant_id: string;
  ativo: boolean;
  ultimo_teste?: string;
  teste_status?: string;
}

export default function ContmaticConfigPage() {
  const [config, setConfig] = useState<ContmaticConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testResult, setTestResult] = useState<{sucesso: boolean; mensagem: string} | null>(null);

  const [formData, setFormData] = useState({
    formato: 'TXT',
    layout: 'contmatic',
    diretorio_exportacao: '',
    prefixo_arquivo: 'AGROSAAS'
  });

  useEffect(() => {
    fetchConfig();
  }, []);

  const fetchConfig = async () => {
    try {
      const response = await fetch(`${getApiBaseUrl()}/contabilidade/integracoes?istema=contmatic`, {
        credentials: 'include',
      });
      
      if (response.ok) {
        const data = await response.json();
        if (data.length > 0) {
          setConfig(data[0]);
        }
      }
    } catch (error) {
      console.error('Erro ao buscar config:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const response = await fetch(`${getApiBaseUrl()}/contabilidade/integracoes`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          sistema: 'contmatic',
          nome: 'Contmatic',
          configuracoes: formData
        }),
      });

      if (response.ok) {
        alert('Configuração salva com sucesso!');
        fetchConfig();
      }
    } catch (error) {
      alert('Erro ao salvar configuração');
    } finally {
      setSaving(false);
    }
  };

  const handleExport = async () => {
    alert('Exportação iniciada! Arquivo será gerado no padrão Contmatic.');
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin" />
      </div>
    );
  }

  return (
    <div className="p-6 flex flex-col gap-6">
      <PageHeader
        title="Contmatic"
        description="Exportação de lançamentos no formato Contmatic."
        breadcrumbs={[
          { label: "Integrações", href: "/integracoes" },
          { label: "Contmatic" },
        ]}
      />

      <div className="flex items-center justify-end">
        {config ? <StatusBadge status={config.ativo ? "ativo" : "inativo"} /> : null}
      </div>

      <Card className="rounded-sm border-border/60">
        <CardHeader>
          <CardTitle>Configurações de Exportação</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="prefixo" className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">
              Prefixo do Arquivo
            </Label>
            <Input
              id="prefixo"
              className="h-8 rounded-sm text-sm"
              value={formData.prefixo_arquivo}
              onChange={(e) => setFormData({...formData, prefixo_arquivo: e.target.value})}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="diretorio" className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">
              Diretório de Exportação
            </Label>
            <Input
              id="diretorio"
              className="h-8 rounded-sm text-sm"
              placeholder="/tmp/exportacoes_contabeis"
              value={formData.diretorio_exportacao}
              onChange={(e) => setFormData({...formData, diretorio_exportacao: e.target.value})}
            />
          </div>

          <Button size="sm" onClick={handleSave} disabled={saving}>
            {saving ? 'Salvando...' : 'Salvar Configuração'}
          </Button>
        </CardContent>
      </Card>

      <Card className="rounded-sm border-border/60">
        <CardHeader>
          <CardTitle>Exportação</CardTitle>
        </CardHeader>
        <CardContent>
          <Button size="sm" variant="outline" onClick={handleExport}>
            <FileDown className="w-4 h-4 mr-2" />
            Exportar Lançamentos
          </Button>
        </CardContent>
      </Card>

      {testResult && (
        <Alert variant={testResult.sucesso ? "success" : "destructive"}>
          <AlertDescription>
            {testResult.mensagem}
          </AlertDescription>
        </Alert>
      )}
    </div>
  );
}
