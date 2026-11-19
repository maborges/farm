/**
 * Página de Configuração - Fortes Contábil
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
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { getApiBaseUrl } from '@/lib/runtime-config';
import { StatusBadge } from "@/components/ui/status-badge";

interface FortesConfig {
  id: number;
  tenant_id: string;
  ativo: boolean;
  ultimo_teste?: string;
  teste_status?: string;
}

export default function FortesConfigPage() {
  const [config, setConfig] = useState<FortesConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testResult, setTestResult] = useState<{sucesso: boolean; mensagem: string} | null>(null);

  const [formData, setFormData] = useState({
    formato: 'CSV',
    delimitador: ';',
    codificacao: 'UTF-8',
    incluir_cabecalho: true,
    diretorio_exportacao: ''
  });

  useEffect(() => {
    fetchConfig();
  }, []);

  const fetchConfig = async () => {
    try {
      const response = await fetch(`${getApiBaseUrl()}/contabilidade/integracoes?istema=fortes`, {
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
          sistema: 'fortes',
          nome: 'Fortes Contábil',
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
    alert('Exportação iniciada! Arquivo CSV será gerado.');
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
        title="Fortes Contábil"
        description="Exportação de lançamentos em CSV/XML."
        breadcrumbs={[
          { label: "Integrações", href: "/integracoes" },
          { label: "Fortes Contábil" },
        ]}
      />

      <div className="flex items-center justify-end">
        {config ? <StatusBadge status={config.ativo ? "ativo" : "inativo"} /> : null}
      </div>

      <Card className="rounded-sm border-border/60">
        <CardHeader>
          <CardTitle>Formato de Exportação</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="formato" className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">
                Formato
              </Label>
              <Select value={formData.formato} onValueChange={(v) => setFormData({...formData, formato: v})}>
                <SelectTrigger className="h-8 rounded-sm text-sm">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="CSV">CSV</SelectItem>
                  <SelectItem value="XML">XML</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="delimitador" className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">
                Delimitador
              </Label>
              <Select value={formData.delimitador} onValueChange={(v) => setFormData({...formData, delimitador: v})}>
                <SelectTrigger className="h-8 rounded-sm text-sm">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value=";">Ponto e vírgula (;)</SelectItem>
                  <SelectItem value=",">Vírgula (,)</SelectItem>
                  <SelectItem value="|">Pipe (|)</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="codificacao" className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">
                Codificação
              </Label>
              <Select value={formData.codificacao} onValueChange={(v) => setFormData({...formData, codificacao: v})}>
                <SelectTrigger className="h-8 rounded-sm text-sm">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="UTF-8">UTF-8</SelectItem>
                  <SelectItem value="LATIN1">Latin-1</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="flex items-end">
              <Label className="flex items-center gap-2 text-xs font-medium">
                <Input
                  type="checkbox"
                  checked={formData.incluir_cabecalho}
                  onChange={(e) => setFormData({...formData, incluir_cabecalho: e.target.checked})}
                  className="h-4 w-4"
                />
                Incluir cabeçalho
              </Label>
            </div>
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
          <div className="flex flex-wrap gap-2">
            <Button size="sm" variant="outline" onClick={handleExport}>
              <FileDown className="w-4 h-4 mr-2" />
              Exportar Lançamentos (CSV)
            </Button>
            <Button size="sm" variant="outline" onClick={handleExport}>
              <FileDown className="w-4 h-4 mr-2" />
              Exportar Lançamentos (XML)
            </Button>
          </div>
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
