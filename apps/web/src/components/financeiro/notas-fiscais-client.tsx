"use client";

import { useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useFieldArray, useForm, useWatch } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { notaFiscalManualSchema, type NotaFiscalManualForm } from '@farm/zod-schemas';
import { FileText, Upload, Plus, Download, RefreshCw, ExternalLink } from 'lucide-react';
import { toast } from 'sonner';
import { apiFetch } from '@/lib/api';
import { useAppStore } from '@/lib/stores/app-store';
import { PageHeader } from '@/components/shared/page-header';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Skeleton } from '@/components/ui/skeleton';
import { Dialog, DialogBody, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';

type Json = string | number | boolean | null | Json[] | { [key: string]: Json };
type Vinculo = { tipo: string; id: string; label: string };
interface Nota {
    id: string; tipo: string; numero?: number; serie: string; chave_acesso?: string;
    emitente_nome: string; emitente_cpf_cnpj?: string; destinatario_nome: string;
    destinatario_documento?: string; destinatario_uf?: string; unidade_produtiva_id?: string;
    data_emissao: string; valor_total: number; valor_produtos: number; valor_icms: number;
    valor_frete: number; descricao_produto?: string;
    gestao?: {
        origem?: string; direcao?: string; ambiente?: string; observacoes?: string;
        itens?: { prod: Record<string, string> }[]; dados_xml?: Json;
        protocolo_xml?: Record<string, string>; sha256?: string;
        divergencias?: Json; alertas?: string[]; vinculos?: Vinculo[];
        historico?: { evento: string; em: string }[];
        consulta?: { estado: string; cstat?: string; motivo?: string; em?: string };
    };
}
const BASE = '/financeiro/notas-fiscais';
const DIRECOES = [['entrada', 'Entrada'], ['saida', 'Saída']];
const PROCESSOS = [['compra', 'Compra'], ['despesa', 'Conta a pagar'], ['receita', 'Conta a receber'], ['safra', 'Safra'], ['comercializacao', 'Comercialização']];
const moeda = (v: number) => Number(v).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
const data = (v?: string) => v ? new Date(v).toLocaleString('pt-BR') : '—';

function Escolha({ value, onChange, options, label, disabled }: {
    value: string; onChange: (value: string) => void; options: string[][]; label: string; disabled?: boolean;
}) {
    return <Select value={value} onValueChange={onChange} disabled={disabled}>
        <SelectTrigger aria-label={label} className="w-full"><SelectValue placeholder={label} /></SelectTrigger>
        <SelectContent><SelectGroup>{options.map(([id, title]) => <SelectItem key={id} value={id}>{title}</SelectItem>)}</SelectGroup></SelectContent>
    </Select>;
}

function Situacao({ nota }: { nota: Nota }) {
    const consulta = nota.gestao?.consulta;
    return <Badge variant="secondary">{consulta?.estado === 'consultada' ? `${consulta.cstat} · ${consulta.motivo}` : 'Não consultada na SEFAZ'}</Badge>;
}

function DadosXml({ value }: { value: Json }) {
    if (value === null) return <span>—</span>;
    if (typeof value !== 'object') return <span className="break-words">{String(value)}</span>;
    return <dl className="flex min-w-0 flex-col gap-2">{Object.entries(value).map(([key, child]) =>
        <div key={key} className="min-w-0 border-l pl-3">
            {child && typeof child === 'object' ? <details><summary className="cursor-pointer">{key}</summary><div className="py-2"><DadosXml value={child} /></div></details>
                : <><dt className="text-xs text-muted-foreground">{key}</dt><dd><DadosXml value={child} /></dd></>}
        </div>)}</dl>;
}

export function NotasFiscaisClient() {
    const qc = useQueryClient();
    const tenantId = useAppStore(s => s.tenant?.id);
    const unidadeId = useAppStore(s => s.activeFazendaId);
    const isGrupo = useAppStore(s => s.isVisaoGrupo);
    const [busca, setBusca] = useState('');
    const [q, setQ] = useState('');
    const [direcao, setDirecao] = useState('todos');
    const [pagina, setPagina] = useState(0);
    const [manual, setManual] = useState(false);
    const [upload, setUpload] = useState(false);
    const [arquivos, setArquivos] = useState<File[]>([]);
    const [direcaoXml, setDirecaoXml] = useState('entrada');
    const [anexarId, setAnexarId] = useState<string | null>(null);
    const [selecionada, setSelecionada] = useState<string | null>(null);
    const [tipoProcesso, setTipoProcesso] = useState('compra');
    const [buscaProcesso, setBuscaProcesso] = useState('');
    const [processo, setProcesso] = useState('');
    const contextoUnidade = isGrupo ? undefined : unidadeId || undefined;
    useEffect(() => { const timer = setTimeout(() => { setQ(busca); setPagina(0); }, 350); return () => clearTimeout(timer); }, [busca]);
    const lista = useQuery({
        queryKey: ['documentos-fiscais', tenantId, contextoUnidade, q, direcao, pagina],
        queryFn: () => apiFetch<{ items: Nota[]; total: number }>(BASE, { params: {
            q, direcao: direcao === 'todos' ? undefined : direcao, unidade_produtiva_id: contextoUnidade, limit: 20, offset: pagina * 20,
        } }),
    });
    const detalhe = useQuery({ queryKey: ['documentos-fiscais', tenantId, selecionada], queryFn: () => apiFetch<Nota>(`${BASE}/${selecionada}`), enabled: !!selecionada });
    const nota = detalhe.data;
    const processos = useQuery({
        queryKey: ['documentos-fiscais-processos', tenantId, tipoProcesso, buscaProcesso],
        queryFn: () => apiFetch<{ id: string; label: string }[]>(`${BASE}/processos`, { params: { tipo: tipoProcesso, q: buscaProcesso } }), enabled: !!selecionada,
    });
    const mutation = useMutation({ mutationFn: (work: () => Promise<unknown>) => work(),
        onSuccess: () => { qc.invalidateQueries({ queryKey: ['documentos-fiscais'] }); },
        onError: (error: Error) => toast.error(error.message || 'Não foi possível concluir a operação.'),
    });
    const pending = mutation.isPending;
    const form = useForm<NotaFiscalManualForm>({ resolver: zodResolver(notaFiscalManualSchema), defaultValues: {
        direcao: 'entrada', tipo: 'NF-e', numero: '', serie: '1', data_emissao: '', emitente_nome: '', emitente_cpf_cnpj: '',
        destinatario_nome: '', destinatario_documento: '', destinatario_uf: '', chave_acesso: '',
        valor_total: '', valor_produtos: '0', valor_icms: '0', valor_frete: '0', descricao_produto: '', observacoes: '',
        itens: [{ descricao: '', ncm: '', cfop: '', quantidade: '1', unidade: 'UN', valor_unitario: '0', valor_total: '0' }],
    } });
    const itens = useFieldArray({ control: form.control, name: 'itens' });
    const direcaoManual = useWatch({ control: form.control, name: 'direcao' });
    const tipoManual = useWatch({ control: form.control, name: 'tipo' });
    const salvar = form.handleSubmit(values => mutation.mutate(async () => {
        const { numero, valor_total, valor_produtos, valor_icms, valor_frete, itens: itensForm, ...rest } = values;
        const payload = { ...rest, numero: numero ? Number(numero) : undefined,
            data_emissao: new Date(values.data_emissao).toISOString(), unidade_produtiva_id: contextoUnidade,
            valor_total: Number(valor_total.replace(',', '.')), valor_produtos: Number(valor_produtos.replace(',', '.')),
            valor_icms: Number(valor_icms.replace(',', '.')), valor_frete: Number(valor_frete.replace(',', '.')),
            itens: itensForm.map(item => ({ ...item,
                quantidade: Number(item.quantidade.replace(',', '.')),
                valor_unitario: Number(item.valor_unitario.replace(',', '.')),
                valor_total: Number(item.valor_total.replace(',', '.')),
            })),
            destinatario_uf: values.destinatario_uf || undefined, chave_acesso: values.chave_acesso || undefined };
        const saved = await apiFetch<Nota>(BASE, { method: 'POST', body: JSON.stringify(payload) });
        setManual(false); form.reset(); setSelecionada(saved.id); toast.success('Registro manual salvo.');
    }));
    function importar() {
        if (!arquivos.length) return;
        if (arquivos.some(arquivo => arquivo.size > 2 * 1024 * 1024)) { toast.error('Cada XML deve ter até 2 MB.'); return; }
        const body = new FormData(); body.append('direcao', direcaoXml);
        const unidade = anexarId ? nota?.unidade_produtiva_id : contextoUnidade;
        if (unidade) body.append('unidade_id', unidade);
        if (anexarId) { body.append('arquivo', arquivos[0]); body.append('nota_id', anexarId); }
        else arquivos.forEach(arquivo => body.append('arquivos', arquivo));
        mutation.mutate(async () => {
            if (anexarId || arquivos.length === 1) {
                if (!anexarId) { body.delete('arquivos'); body.append('arquivo', arquivos[0]); }
                const saved = await apiFetch<Nota>(`${BASE}/importar-xml`, { method: 'POST', body });
                setSelecionada(saved.id); toast.success('XML importado. Confira as evidências e os vínculos.');
            } else {
                const result = await apiFetch<{ importados: number; falhas: number }>(`${BASE}/importar-lote-xml`, { method: 'POST', body });
                toast.success(`${result.importados} XML(s) importado(s)${result.falhas ? `; ${result.falhas} falha(s)` : ''}.`);
            }
            setUpload(false); setArquivos([]); setAnexarId(null);
        });
    }
    function abrirUpload(target?: Nota) {
        setAnexarId(target?.id || null); setDirecaoXml(target?.gestao?.direcao || 'entrada'); setArquivos([]); setUpload(true);
    }
    async function baixar() {
        if (!nota) return;
        try {
            const blob = await apiFetch<Blob>(`${BASE}/${nota.id}/xml`, { responseType: 'blob' });
            const url = URL.createObjectURL(blob); const a = document.createElement('a');
            a.href = url; a.download = `${nota.chave_acesso || nota.id}.xml`; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
        } catch (error) { toast.error(error instanceof Error ? error.message : 'Falha no download.'); }
    }
    const campos: { name: keyof NotaFiscalManualForm; label: string; type?: string; full?: boolean }[] = [
        { name: 'numero', label: 'Número' }, { name: 'serie', label: 'Série' },
        { name: 'data_emissao', label: 'Data e hora de emissão *', type: 'datetime-local', full: true },
        { name: 'emitente_nome', label: 'Emitente *' }, { name: 'emitente_cpf_cnpj', label: 'CPF/CNPJ do emitente' },
        { name: 'destinatario_nome', label: 'Destinatário *' }, { name: 'destinatario_documento', label: 'CPF/CNPJ do destinatário' },
        { name: 'destinatario_uf', label: 'UF do destinatário' }, { name: 'valor_total', label: 'Valor total (R$) *' },
        { name: 'valor_produtos', label: 'Produtos (R$)' }, { name: 'valor_icms', label: 'ICMS (R$)' },
        { name: 'valor_frete', label: 'Frete (R$)' }, { name: 'descricao_produto', label: 'Descrição resumida' },
        { name: 'chave_acesso', label: 'Chave de acesso (44 dígitos)', full: true }, { name: 'observacoes', label: 'Observações internas', full: true },
    ];
    return <div className="flex w-full min-w-0 max-w-7xl flex-col gap-5 p-4 sm:p-6">
        <PageHeader title="Notas fiscais" description="Entrada e saída: importe XML, confira a situação fiscal e associe aos processos."
            icon={<FileText />} breadcrumbs={[{ label: 'Financeiro', href: '/dashboard/financeiro' }, { label: 'Notas fiscais' }]}
            actions={<><Button size="sm" variant="outline" onClick={() => setManual(true)}><Plus data-icon="inline-start" />Digitar nota</Button>
                <Button size="sm" onClick={() => abrirUpload()}><Upload data-icon="inline-start" />Importar XML</Button></>} />
        <Alert><AlertDescription>Importe notas emitidas por fornecedores, pelo seu ERP ou por outro emissor. Os registros manuais ficam aguardando XML. A consulta SEFAZ informa a situação na data da verificação.</AlertDescription></Alert>
        <div className="flex flex-col gap-3 sm:flex-row"><Input aria-label="Buscar notas" placeholder="Número, chave, emitente ou destinatário" value={busca} onChange={e => setBusca(e.target.value)} className="sm:max-w-md" />
            <div className="sm:w-44"><Escolha label="Direção" value={direcao} onChange={v => { setDirecao(v); setPagina(0); }} options={[["todos", "Entradas e saídas"], ...DIRECOES]} /></div></div>
        {lista.isError ? <Alert variant="destructive"><AlertDescription>Não foi possível carregar as notas. <Button size="sm" variant="outline" onClick={() => lista.refetch()}>Tentar novamente</Button></AlertDescription></Alert>
            : lista.isLoading ? <Skeleton className="h-56 w-full" /> : <div className="min-w-0 rounded-sm border"><Table>
                <TableHeader><TableRow><TableHead>Nota / emissão</TableHead><TableHead>Operação</TableHead><TableHead>Participantes</TableHead><TableHead>Origem</TableHead><TableHead>Situação SEFAZ</TableHead><TableHead className="text-right">Total</TableHead><TableHead><span className="sr-only">Ações</span></TableHead></TableRow></TableHeader>
                <TableBody>{lista.data?.items.map(n => <TableRow key={n.id}>
                    <TableCell><div>{n.tipo} {n.numero ?? 'Sem número'} / {n.serie}</div><div className="text-xs text-muted-foreground">{data(n.data_emissao)}</div></TableCell>
                    <TableCell>{n.gestao?.direcao === 'entrada' ? 'Entrada' : n.gestao?.direcao === 'saida' ? 'Saída' : 'A classificar'}</TableCell>
                    <TableCell className="max-w-56"><div className="truncate" title={n.emitente_nome}>{n.emitente_nome}</div><div className="truncate text-xs text-muted-foreground" title={n.destinatario_nome}>Para: {n.destinatario_nome}</div></TableCell>
                    <TableCell>{n.gestao?.origem === 'xml' ? 'XML importado' : 'Manual · aguardando XML'}{n.gestao?.ambiente === '2' && <div>Homologação</div>}</TableCell>
                    <TableCell><Situacao nota={n} /></TableCell><TableCell className="text-right tabular-nums">{moeda(n.valor_total)}</TableCell>
                    <TableCell><Button size="sm" variant="ghost" onClick={() => { setSelecionada(n.id); setProcesso(''); }}>Detalhes</Button></TableCell></TableRow>)}
                    {!lista.data?.items.length && <TableRow><TableCell colSpan={7} className="py-12 text-center">Nenhuma nota encontrada. Importe um XML ou registre os dados manualmente.</TableCell></TableRow>}</TableBody>
            </Table></div>}
        <div className="flex items-center justify-between gap-3"><span className="text-sm text-muted-foreground">{lista.data?.total ?? 0} documentos · Página {pagina + 1}</span><div className="flex gap-2">
            <Button size="sm" variant="outline" disabled={pagina === 0 || lista.isFetching} onClick={() => setPagina(p => p - 1)}>Anterior</Button>
            <Button size="sm" variant="outline" disabled={(pagina + 1) * 20 >= (lista.data?.total ?? 0) || lista.isFetching} onClick={() => setPagina(p => p + 1)}>Próxima</Button></div></div>

        <Dialog open={manual} onOpenChange={v => { if (!pending) { setManual(v); if (!v) form.reset(); } }}>
            <DialogContent className="max-w-[calc(100%-2rem)] gap-0 sm:max-w-xl" aria-labelledby="manual-title" aria-describedby="manual-description">
                <DialogHeader className="shrink-0 border-b py-4"><DialogTitle id="manual-title">Registrar nota manualmente</DialogTitle><DialogDescription id="manual-description">Transcreva os dados do documento existente. A conferência do arquivo ficará pendente.</DialogDescription></DialogHeader>
                <DialogBody className="py-4"><form id="nota-manual" onSubmit={salvar} className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                    <div className="flex flex-col gap-1"><Label>Operação</Label><Escolha label="Operação da nota" value={direcaoManual} onChange={v => form.setValue('direcao', v as 'entrada' | 'saida')} options={DIRECOES} disabled={pending} /></div>
                    <div className="flex flex-col gap-1"><Label>Tipo</Label><Escolha label="Tipo de nota" value={tipoManual} onChange={v => form.setValue('tipo', v as NotaFiscalManualForm['tipo'])} options={['NF-e', 'NFP-e', 'NFC-e'].map(v => [v, v])} disabled={pending} /></div>
                    {campos.map(c => <div key={c.name} className={c.full ? 'flex flex-col gap-1 sm:col-span-2' : 'flex flex-col gap-1'}>
                        <Label htmlFor={`nf-${c.name}`}>{c.label}</Label><Input id={`nf-${c.name}`} type={c.type || 'text'} {...form.register(c.name)} disabled={pending} aria-invalid={!!form.formState.errors[c.name]} aria-describedby={form.formState.errors[c.name] ? `error-${c.name}` : undefined} />
                        {form.formState.errors[c.name] && <p id={`error-${c.name}`} className="text-xs text-destructive">{form.formState.errors[c.name]?.message}</p>}
                    </div>)}
                    <div className="flex flex-col gap-3 sm:col-span-2">
                        <div className="flex items-center justify-between gap-2"><div><Label>Itens da nota *</Label><p className="text-xs text-muted-foreground">Inclua todos os produtos que constam no documento.</p></div><Button type="button" size="sm" variant="outline" onClick={() => itens.append({ descricao: '', ncm: '', cfop: '', quantidade: '1', unidade: 'UN', valor_unitario: '0', valor_total: '0' })} disabled={pending}><Plus data-icon="inline-start" />Adicionar item</Button></div>
                        {itens.fields.map((item, index) => <div key={item.id} className="grid grid-cols-1 gap-2 rounded-sm border p-3 sm:grid-cols-2">
                            <div className="flex flex-col gap-1 sm:col-span-2"><Label>Produto {index + 1}</Label><Input {...form.register(`itens.${index}.descricao` as const)} disabled={pending} /></div>
                            <div className="flex flex-col gap-1"><Label>NCM</Label><Input {...form.register(`itens.${index}.ncm` as const)} disabled={pending} /></div>
                            <div className="flex flex-col gap-1"><Label>CFOP</Label><Input {...form.register(`itens.${index}.cfop` as const)} disabled={pending} /></div>
                            <div className="flex flex-col gap-1"><Label>Quantidade</Label><Input {...form.register(`itens.${index}.quantidade` as const)} disabled={pending} /></div>
                            <div className="flex flex-col gap-1"><Label>Unidade</Label><Input {...form.register(`itens.${index}.unidade` as const)} disabled={pending} /></div>
                            <div className="flex flex-col gap-1"><Label>Valor unitário (R$)</Label><Input {...form.register(`itens.${index}.valor_unitario` as const)} disabled={pending} /></div>
                            <div className="flex flex-col gap-1"><Label>Total do item (R$)</Label><Input {...form.register(`itens.${index}.valor_total` as const)} disabled={pending} /></div>
                            {itens.fields.length > 1 && <Button type="button" size="sm" variant="ghost" className="justify-self-start text-destructive" onClick={() => itens.remove(index)} disabled={pending}>Remover item</Button>}
                        </div>)}
                        {form.formState.errors.itens?.message && <p className="text-xs text-destructive">{form.formState.errors.itens.message}</p>}
                    </div>
                </form></DialogBody><DialogFooter className="shrink-0"><Button size="sm" variant="outline" disabled={pending} onClick={() => { setManual(false); form.reset(); }}>Cancelar</Button><Button size="sm" form="nota-manual" type="submit" disabled={pending}>{pending ? 'Salvando…' : 'Salvar registro'}</Button></DialogFooter>
            </DialogContent>
        </Dialog>
        <Dialog open={upload} onOpenChange={v => { if (!pending) setUpload(v); }}>
            <DialogContent className="max-w-[calc(100%-2rem)] gap-0 sm:max-w-lg" aria-labelledby="xml-title" aria-describedby="xml-description">
                <DialogHeader className="shrink-0 border-b py-4"><DialogTitle id="xml-title">{anexarId ? 'Anexar XML ao registro' : 'Importar XML'}</DialogTitle><DialogDescription id="xml-description">Arquivo original NF-e/NFC-e, até 2 MB. As diferenças com o registro manual serão apresentadas para conferência.</DialogDescription></DialogHeader>
                <DialogBody className="flex flex-col gap-4 py-4"><Escolha label="Operação do XML" value={direcaoXml} onChange={setDirecaoXml} options={DIRECOES} disabled={pending} /><Label htmlFor="arquivo-xml">{anexarId ? 'Arquivo XML' : 'Arquivos XML'}</Label><Input id="arquivo-xml" type="file" multiple={!anexarId} accept=".xml,application/xml,text/xml" disabled={pending} onChange={e => setArquivos(Array.from(e.target.files || []))} />
                    <p className="text-xs text-muted-foreground">{anexarId ? 'Anexe o XML oficial ao registro manual.' : 'Você pode importar até 200 XMLs. A aplicação não gera automaticamente títulos ou movimentos de estoque.'}</p></DialogBody><DialogFooter className="shrink-0"><Button size="sm" variant="outline" disabled={pending} onClick={() => setUpload(false)}>Cancelar</Button><Button size="sm" disabled={!arquivos.length || pending} onClick={importar}>{pending ? 'Importando…' : 'Importar'}</Button></DialogFooter>
            </DialogContent>
        </Dialog>
        <Dialog open={!!selecionada && !upload} onOpenChange={v => { if (!v && !pending) setSelecionada(null); }}>
            <DialogContent className="max-w-[calc(100%-2rem)] gap-0 sm:max-w-3xl" aria-labelledby="detalhe-title" aria-describedby="detalhe-description">
                <DialogHeader className="shrink-0 border-b py-4"><DialogTitle id="detalhe-title">Nota fiscal {nota?.numero ?? ''}</DialogTitle><DialogDescription id="detalhe-description">Dados do documento, evidências e associações.</DialogDescription></DialogHeader>
                <DialogBody className="flex flex-col gap-5 py-4">{detalhe.isLoading ? <Skeleton className="h-48" /> : detalhe.isError ? <Alert variant="destructive"><AlertDescription>Não foi possível abrir a nota.</AlertDescription></Alert> : nota && <>
                    <div className="flex flex-wrap gap-2"><Situacao nota={nota} /><Badge variant="outline">{nota.gestao?.origem === 'xml' ? 'XML preservado' : 'Aguardando XML'}</Badge>{nota.gestao?.ambiente === '2' && <Badge variant="secondary">Homologação</Badge>}</div>
                    <dl className="grid grid-cols-1 gap-3 sm:grid-cols-2"><div><dt className="text-xs text-muted-foreground">Emitente</dt><dd>{nota.emitente_nome}<br />{nota.emitente_cpf_cnpj}</dd></div><div><dt className="text-xs text-muted-foreground">Destinatário</dt><dd>{nota.destinatario_nome}<br />{nota.destinatario_documento}</dd></div><div><dt className="text-xs text-muted-foreground">Emissão</dt><dd>{data(nota.data_emissao)}</dd></div><div><dt className="text-xs text-muted-foreground">Total</dt><dd>{moeda(nota.valor_total)}</dd></div><div className="min-w-0 sm:col-span-2"><dt className="text-xs text-muted-foreground">Chave de acesso</dt><dd className="break-all font-mono text-xs">{nota.chave_acesso || 'Não informada'}</dd></div></dl>
                    {nota.gestao?.observacoes && <p>{nota.gestao.observacoes}</p>}
                    <section className="flex flex-col gap-2"><h3 className="font-medium">Conferência fiscal</h3><p className="text-sm">Última consulta: {data(nota.gestao?.consulta?.em)}. {nota.gestao?.consulta?.motivo}</p>
                        {nota.gestao?.protocolo_xml?.nProt && <p className="text-sm">Protocolo no XML: {nota.gestao.protocolo_xml.nProt} · código {nota.gestao.protocolo_xml.cStat}</p>}
                        <p className="text-xs text-muted-foreground">A consulta verifica a situação na SEFAZ. A verificação criptográfica da assinatura e a validação completa do leiaute XML ainda não estão disponíveis.</p>
                        {nota.gestao?.alertas?.filter(a => !a.includes('SEFAZ ainda')).map(a => <p key={a} className="text-xs text-muted-foreground">{a}</p>)}
                        <div className="flex flex-wrap gap-2"><Button size="sm" variant="outline" disabled={pending || !nota.chave_acesso} onClick={() => mutation.mutate(async () => { await apiFetch(`${BASE}/${nota.id}/consultar-sefaz`, { method: 'POST' }); toast.success('Consulta concluída.'); })}><RefreshCw data-icon="inline-start" />Consultar SEFAZ</Button>
                            <Button size="sm" variant="outline" disabled={!nota.chave_acesso} onClick={() => { const host = nota.gestao?.ambiente === '2' ? 'hom' : 'www'; window.open(`https://${host}.nfe.fazenda.gov.br/portal/consultaRecaptcha.aspx`, '_blank', 'noopener,noreferrer'); }}><ExternalLink data-icon="inline-start" />Portal oficial</Button>
                            <Button size="sm" variant="ghost" disabled={!nota.chave_acesso} onClick={() => navigator.clipboard.writeText(nota.chave_acesso || '').then(() => toast.success('Chave copiada.')).catch(() => toast.error('Não foi possível copiar.'))}>Copiar chave</Button></div></section>
                    {!!nota.gestao?.itens?.length && <section className="min-w-0"><h3 className="mb-2 font-medium">Itens ({nota.gestao.itens.length})</h3><Table><TableHeader><TableRow><TableHead>Produto</TableHead><TableHead>NCM / CFOP</TableHead><TableHead>Quantidade</TableHead><TableHead>Total</TableHead></TableRow></TableHeader><TableBody>{nota.gestao.itens.map((item, i) => <TableRow key={i}><TableCell>{item.prod.xProd}</TableCell><TableCell>{item.prod.NCM} / {item.prod.CFOP}</TableCell><TableCell>{item.prod.qCom} {item.prod.uCom}</TableCell><TableCell>{moeda(Number(item.prod.vProd))}</TableCell></TableRow>)}</TableBody></Table></section>}
                    {nota.gestao?.divergencias && Object.keys(nota.gestao.divergencias).length > 0 && <details><summary className="cursor-pointer font-medium">Diferenças entre digitação e XML</summary><DadosXml value={nota.gestao.divergencias} /></details>}
                    {nota.gestao?.dados_xml && <details><summary className="cursor-pointer font-medium">Dados completos: tributos, transporte, pagamentos e informações adicionais</summary><div className="py-3"><DadosXml value={nota.gestao.dados_xml} /></div></details>}
                    <section className="flex flex-col gap-3"><h3 className="font-medium">Processos associados</h3>{nota.gestao?.vinculos?.length ? nota.gestao.vinculos.map(v => <div key={`${v.tipo}-${v.id}`} className="rounded-sm border p-2 text-sm">{PROCESSOS.find(([id]) => id === v.tipo)?.[1] || v.tipo}: {v.label}</div>) : <p className="text-sm text-muted-foreground">Nenhum processo associado.</p>}
                        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2"><Escolha label="Tipo de processo" value={tipoProcesso} onChange={v => { setTipoProcesso(v); setProcesso(''); }} options={PROCESSOS} /><Input placeholder="Descrição ou número do processo" aria-label="Buscar processo" value={buscaProcesso} onChange={e => { setBuscaProcesso(e.target.value); setProcesso(''); }} /></div>
                        {processos.isError ? <p className="text-sm text-destructive">Não foi possível carregar os processos.</p> : <Escolha label={processos.isLoading ? 'Carregando processos…' : 'Selecione o processo'} value={processo} onChange={setProcesso} options={(processos.data || []).map(p => [p.id, p.label])} disabled={processos.isLoading} />}
                        {!processos.isLoading && !processos.isError && !processos.data?.length && <p className="text-xs text-muted-foreground">Nenhum processo encontrado para este cliente.</p>}
                        <Button size="sm" variant="outline" className="self-start" disabled={!processo || pending} onClick={() => mutation.mutate(async () => { await apiFetch(`${BASE}/${nota.id}/vinculos`, { method: 'POST', body: JSON.stringify({ tipo: tipoProcesso, id: processo }) }); setProcesso(''); toast.success('Processo associado.'); })}>Associar processo</Button></section>
                    <details><summary className="cursor-pointer font-medium">Histórico e integridade</summary><div className="flex flex-col gap-2 py-3">{nota.gestao?.historico?.map((h, i) => <p key={i} className="text-xs">{data(h.em)} · {h.evento}</p>)}{nota.gestao?.sha256 && <p className="break-all font-mono text-xs">SHA-256: {nota.gestao.sha256}</p>}</div></details>
                </>}</DialogBody><DialogFooter className="shrink-0">{nota?.gestao?.origem === 'xml' ? <Button size="sm" variant="outline" onClick={baixar}><Download data-icon="inline-start" />Baixar XML original</Button> : <Button size="sm" variant="outline" disabled={!nota || pending} onClick={() => nota && abrirUpload(nota)}><Upload data-icon="inline-start" />Anexar XML</Button>}<Button size="sm" disabled={pending} onClick={() => setSelecionada(null)}>Fechar</Button></DialogFooter>
            </DialogContent>
        </Dialog>
    </div>;
}
