/**
 * Página Principal de Integrações
 * Lista todas as integrações disponíveis
 */

'use client';

import { PageHeader } from '@/components/shared/page-header';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Database, FileText, Calculator, Cloud, CloudSun, Sprout, TrendingUp } from 'lucide-react';
import Link from 'next/link';

const integracoes = [
  {
    id: 'sankhya',
    nome: 'ERP Sankhya',
    descricao: 'Bridge corporativa para ERP, sincronização e exportações',
    categoria: 'ERP',
    status: 'implementado',
    icone: Database,
    link: '/dashboard/settings/integracoes/erp'
  },
  {
    id: 'openweather',
    nome: 'OpenWeather',
    descricao: 'Provedor climático oficial para teste de conexão e consulta atual',
    categoria: 'Clima',
    status: 'implementado',
    icone: CloudSun,
    link: '/dashboard/settings/integracoes/clima/openweather'
  },
  {
    id: 'dominio',
    nome: 'Domínio Sistemas',
    descricao: 'Exportação de lançamentos contábeis',
    categoria: 'Contábil',
    status: 'implementado',
    icone: FileText,
    link: '/integracoes/dominio'
  },
  {
    id: 'fortes',
    nome: 'Fortes Contábil',
    descricao: 'Exportação CSV/XML para Fortes',
    categoria: 'Contábil',
    status: 'implementado',
    icone: Calculator,
    link: '/integracoes/fortes'
  },
  {
    id: 'contmatic',
    nome: 'Contmatic',
    descricao: 'Exportação de lançamentos contábeis',
    categoria: 'Contábil',
    status: 'implementado',
    icone: FileText,
    link: '/integracoes/contmatic'
  },
  {
    id: 'new-holland',
    nome: 'New Holland PLM',
    descricao: 'Integração com máquinas agrícolas',
    categoria: 'IoT',
    status: 'implementado',
    icone: Cloud,
    link: '/integracoes/new-holland'
  },
  {
    id: 'john-deere',
    nome: 'John Deere Ops Center',
    descricao: 'Telemetria e operações de campo',
    categoria: 'IoT',
    status: 'implementado',
    icone: Sprout,
    link: '/iot/john-deere'
  },
  {
    id: 'case-ih',
    nome: 'Case IH AFS',
    descricao: 'Integração com máquinas Case IH',
    categoria: 'IoT',
    status: 'implementado',
    icone: Sprout,
    link: '/iot/case-ih'
  },
  {
    id: 'b3',
    nome: 'B3 - Bolsa',
    descricao: 'Cotações e contratos futuros',
    categoria: 'Financeiro',
    status: 'implementado',
    icone: TrendingUp,
    link: '/financeiro/hedging'
  }
];

export default function IntegracoesPage() {
  return (
    <div className="p-6 flex flex-col gap-6">
      <PageHeader
        title="Integrações"
        description="Gerencie as conexões oficiais do DeepFarms, com acesso direto às configurações e diagnósticos."
      />

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        {integracoes.map((integracao) => (
          <Card key={integracao.id} className="relative rounded-sm border-border/60">
            <CardHeader className="gap-3">
              <div className="flex items-center justify-between gap-3">
                <integracao.icone className="h-8 w-8 text-primary" />
                <Badge variant={integracao.status === 'implementado' ? 'default' : 'secondary'} className="text-[10px] uppercase tracking-widest rounded-sm">
                  {integracao.status}
                </Badge>
              </div>
              <CardTitle className="text-lg">{integracao.nome}</CardTitle>
              <CardDescription>{integracao.descricao}</CardDescription>
            </CardHeader>
            <CardContent className="pt-0">
              <div className="flex items-center justify-between">
                <Badge variant="outline" className="rounded-sm text-[10px] uppercase tracking-widest">{integracao.categoria}</Badge>
                <Button asChild size="sm">
                  <Link href={integracao.link}>
                    Configurar
                  </Link>
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
