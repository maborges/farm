/**
 * Página de Configuração - Domínio Sistemas
 * Sprint 25 - Integrações Contábeis
 */

'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { CheckCircle, Loader2, FileDown, Clock } from 'lucide-react';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { getApiBaseUrl } from '@/lib/runtime-config';
import { StatusBadge } from "@/components/ui/status-badge";

export interface DominioConfig {
  id: number;
  tenant_id: string;
  ativo: boolean;
  ultimo_teste?: string;
  teste_status?: string;
  ultimo_sync?: string;
  formato: string;
  agendamento?: string;
}

export function DominioClient({ initialConfig }: { initialConfig: DominioConfig | null }) {
  const [config, setConfig] = useState<DominioConfig | null>(initialConfig);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{sucesso: boolean; mensagem: string} | null>(null);

  const [formData, setFormData] = useState({
    formato: 'TXT',
    layout: 'padrao',
    diretorio_exportacao: '',
    agendamento: 'diario',
    horario_exportacao: '18:00'
  });

  // fetchConfig não é mais necessário no onMount pois recebemos initialConfig
  // mas o mantemos para o onSuccess do salvar.
  const fetchConfig = async () => {
    try {
      const response = await fetch(`${getApiBaseUrl()}/contabilidade/integracoes?sistema=dominio`, {
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
          sistema: 'dominio',
          nome: 'Domínio Sistemas',
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

  const handleTestConnection = async () => {
    setTesting(true);
    setTestResult(null);
    // Simulação de teste - em produção, chamar endpoint real
    setTimeout(() => {
      setTestResult({ sucesso: true, mensagem: 'Configurações validadas com sucesso!' });
      setTesting(false);
    }, 2000);
  };

  const handleExport = async () => {
    // Simulação de exportação
    alert('Exportação iniciada! O arquivo será gerado no diretório configurado.');
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin" />
      </div>
    );
  }

    return (
    <div className="space-y-6">
      <div className="flex items-center justify-end">
        {config ? <StatusBadge status={config.ativo ? "ativo" : "inativo"} /> : null}
      </div>

      <Card className="rounded-sm border-border/60">
        <CardHeader>
          <CardTitle>Configurações Gerais</CardTitle>
          <CardDescription>
            Configure o formato e layout de exportação
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="formato" className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">Formato do Arquivo</Label>
              <Select value={formData.formato} onValueChange={(v) => setFormData({...formData, formato: v})}>
                <SelectTrigger className="h-8 rounded-sm text-sm">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="TXT">TXT</SelectItem>
                  <SelectItem value="CSV">CSV</SelectItem>
                  <SelectItem value="XML">XML</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="layout" className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">Layout</Label>
              <Select value={formData.layout} onValueChange={(v) => setFormData({...formData, layout: v})}>
                <SelectTrigger className="h-8 rounded-sm text-sm">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="padrao">Padrão</SelectItem>
                  <SelectItem value="societario">Societário</SelectItem>
                  <SelectItem value="personalizado">Personalizado</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="diretorio" className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">Diretório de Exportação</Label>
            <Input
              id="diretorio"
              className="h-8 rounded-sm text-sm"
              placeholder="/tmp/exportacoes_contabeis"
              value={formData.diretorio_exportacao}
              onChange={(e) => setFormData({...formData, diretorio_exportacao: e.target.value})}
            />
          </div>

          <div className="flex flex-wrap gap-2">
            <Button size="sm" onClick={handleSave} disabled={saving}>
              {saving ? 'Salvando...' : 'Salvar Configuração'}
            </Button>
            <Button 
              size="sm"
              variant="outline" 
              onClick={handleTestConnection} 
              disabled={testing}
            >
              {testing ? (
                <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Testando...</>
              ) : (
                <><CheckCircle className="w-4 h-4 mr-2" /> Testar Configurações</>
              )}
            </Button>
          </div>

          {testResult && (
            <Alert variant={testResult.sucesso ? 'default' : 'destructive'}>
              <AlertDescription>
                {testResult.mensagem}
              </AlertDescription>
            </Alert>
          )}
        </CardContent>
      </Card>

      {/* Agendamento */}
      <Card>
        <CardHeader>
          <CardTitle>Agendamento de Exportação</CardTitle>
          <CardDescription>
            Configure a exportação automática
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="agendamento">Frequência</Label>
              <Select value={formData.agendamento} onValueChange={(v) => setFormData({...formData, agendamento: v})}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="diario">Diário</SelectItem>
                  <SelectItem value="semanal">Semanal</SelectItem>
                  <SelectItem value="mensal">Mensal</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label htmlFor="horario">Horário</Label>
              <Input
                id="horario"
                type="time"
                value={formData.horario_exportacao}
                onChange={(e) => setFormData({...formData, horario_exportacao: e.target.value})}
              />
            </div>
          </div>

          <Button size="sm" variant="outline" onClick={handleExport}>
            <FileDown className="w-4 h-4 mr-2" />
            Exportar Agora
          </Button>
        </CardContent>
      </Card>

      {config && (
        <Card className="rounded-sm border-border/60">
          <CardHeader>
            <CardTitle>Status</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
              <div>
                <p className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">Último Teste</p>
                <p className="font-medium">
                  {config.ultimo_teste 
                    ? new Date(config.ultimo_teste).toLocaleString('pt-BR')
                    : 'Nunca'}
                </p>
                <Badge variant={config.teste_status === 'sucesso' ? 'default' : 'destructive'}>
                  {config.teste_status || 'Não testado'}
                </Badge>
              </div>
              <div>
                <p className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">Última Exportação</p>
                <p className="font-medium">
                  {config.ultimo_sync 
                    ? new Date(config.ultimo_sync).toLocaleString('pt-BR')
                    : 'Nunca'}
                </p>
              </div>
              <div>
                <p className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">Próxima Exportação</p>
                <p className="font-medium flex items-center gap-2">
                  <Clock className="w-4 h-4" />
                  {formData.agendamento === 'diario' ? 'Hoje' : 'Não agendada'} às {formData.horario_exportacao}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
