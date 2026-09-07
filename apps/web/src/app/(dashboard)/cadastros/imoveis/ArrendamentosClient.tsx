"use client";

import * as React from "react";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import { Plus, RefreshCcw, ArrowRightLeft } from "lucide-react";
import type { ImovelRural, UnidadeProdutiva } from "./ImoveisClient";

type ArrendamentoStatus = "ATIVO" | "ENCERRADO" | "RESCINDIDO" | "SUSPENSO";

interface ContratoArrendamento {
  id: string;
  imovel_id: string;
  unidade_produtiva_id: string;
  tipo: "ARRENDAMENTO" | "PARCERIA";
  arrendatario_tipo: "PESSOA_FISICA" | "PESSOA_JURIDICA" | "FAZENDA_TENANT";
  area_arrendada_ha: string | number;
  valor_modalidade: "FIXO_BRL" | "FIXO_SACAS" | "PERCENTUAL";
  valor: string | number;
  periodicidade: "MENSAL" | "SEMESTRAL" | "ANUAL" | "SAFRA";
  data_inicio: string;
  data_fim: string;
  dia_vencimento?: number | null;
  indice_reajuste?: string | null;
  status: ArrendamentoStatus;
  motivo_rescisao?: string | null;
  created_at?: string;
  imovel?: {
    id: string;
    nome: string;
    municipio: string;
    uf: string;
  } | null;
}

interface ArrendamentosClientProps {
  imoveis: ImovelRural[];
  fazendas: UnidadeProdutiva[];
  activeFazendaId?: string;
}

const STATUS_BADGE: Record<ArrendamentoStatus, string> = {
  ATIVO: "bg-green-100 text-green-700 border-green-300",
  ENCERRADO: "bg-slate-100 text-slate-700 border-slate-300",
  RESCINDIDO: "bg-red-100 text-red-700 border-red-300",
  SUSPENSO: "bg-yellow-100 text-yellow-700 border-yellow-300",
};

function currencyLabel(value: string | number) {
  const numberValue = typeof value === "number" ? value : Number(value || 0);
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(numberValue);
}

export function ArrendamentosClient({ imoveis, fazendas, activeFazendaId }: ArrendamentosClientProps) {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({
    imovel_id: "",
    unidade_produtiva_id: "",
    tipo: "ARRENDAMENTO",
    arrendatario_tipo: "PESSOA_FISICA",
    area_arrendada_ha: "",
    valor_modalidade: "FIXO_BRL",
    valor: "",
    periodicidade: "ANUAL",
    data_inicio: "",
    data_fim: "",
    dia_vencimento: "10",
    indice_reajuste: "",
    commodity_referencia: "",
    clausulas_observacoes: "",
  });

  const { data: contratos = [], isLoading } = useQuery<ContratoArrendamento[]>({
    queryKey: ["imoveis-arrendamentos", activeFazendaId],
    queryFn: () => apiFetch("imoveis/arrendamentos"),
    initialData: [],
  });

  const createMutation = useMutation({
    mutationFn: (payload: Record<string, unknown>) =>
      apiFetch("imoveis/arrendamentos", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["imoveis-arrendamentos"] });
      setOpen(false);
      toast.success("Contrato de arrendamento criado com sucesso");
    },
    onError: (error: Error) => {
      toast.error(error.message || "Erro ao criar contrato");
    },
  });

  const handleSubmit = () => {
    if (!form.imovel_id || !form.unidade_produtiva_id || !form.data_inicio || !form.data_fim) {
      toast.error("Preencha os campos obrigatórios");
      return;
    }

    createMutation.mutate({
      ...form,
      area_arrendada_ha: Number(form.area_arrendada_ha || 0),
      valor: Number(form.valor || 0),
      dia_vencimento: Number(form.dia_vencimento || 10),
      indice_reajuste: form.indice_reajuste || undefined,
      commodity_referencia: form.commodity_referencia || undefined,
      clausulas_observacoes: form.clausulas_observacoes || undefined,
      arrendatario_fazenda_id: undefined,
      path_contrato_pdf: undefined,
      registro_cartorio: undefined,
      tipo: form.tipo === "PARCERIA" ? "PARCERIA" : "ARRENDAMENTO",
      arrendatario_tipo: form.arrendatario_tipo,
      valor_modalidade: form.valor_modalidade,
      periodicidade: form.periodicidade,
    });
  };

  const handleOpenCreate = () => {
    const imovelPadrao = activeFazendaId
      ? imoveis.find((item) => item.unidade_produtiva_id === activeFazendaId)?.id
      : imoveis[0]?.id;

    setForm((current) => ({
      ...current,
      unidade_produtiva_id: current.unidade_produtiva_id || activeFazendaId || "",
      imovel_id: current.imovel_id || imovelPadrao || "",
    }));
    setOpen(true);
  };

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between gap-4">
          <div>
            <CardTitle>Arrendamentos e Parcerias</CardTitle>
            <CardDescription>Gestão de contratos, vencimentos e reajustes</CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              className="rounded-sm"
              onClick={() => queryClient.invalidateQueries({ queryKey: ["imoveis-arrendamentos"] })}
            >
              <RefreshCcw className="h-3.5 w-3.5 mr-2" />
              Atualizar
            </Button>
            <Button
              size="sm"
              className="rounded-sm"
              onClick={handleOpenCreate}
            >
              <Plus className="h-3.5 w-3.5 mr-2" />
              Novo contrato
            </Button>
          </div>
        </div>
      </CardHeader>

      <CardContent>
        {isLoading ? (
          <div className="py-8 text-center text-sm text-muted-foreground">Carregando contratos...</div>
        ) : contratos.length === 0 ? (
          <div className="py-8 text-center text-sm text-muted-foreground">
            Nenhum contrato de arrendamento cadastrado.
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Imóvel</TableHead>
                <TableHead>Tipo</TableHead>
                <TableHead>Área</TableHead>
                <TableHead>Valor</TableHead>
                <TableHead>Vigência</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {contratos.map((contrato) => (
                <TableRow key={contrato.id}>
                  <TableCell className="font-medium">
                    <div className="flex flex-col">
                      <span>{contrato.imovel?.nome || contrato.imovel_id}</span>
                      <span className="text-xs text-muted-foreground">
                        {contrato.imovel ? `${contrato.imovel.municipio}/${contrato.imovel.uf}` : "Imóvel vinculado"}
                      </span>
                    </div>
                  </TableCell>
                  <TableCell>{contrato.tipo}</TableCell>
                  <TableCell>{contrato.area_arrendada_ha}</TableCell>
                  <TableCell>{currencyLabel(contrato.valor)}</TableCell>
                  <TableCell>
                    <div className="flex flex-col text-xs">
                      <span>{contrato.data_inicio}</span>
                      <span>{contrato.data_fim}</span>
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline" className={`rounded-sm text-[10px] uppercase font-bold px-1.5 py-0 ${STATUS_BADGE[contrato.status]}`}>
                      {contrato.status}
                    </Badge>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-4xl p-0">
          <DialogHeader className="px-6 pt-6">
            <DialogTitle>Novo contrato de arrendamento</DialogTitle>
            <DialogDescription>
              Cadastre arrendamento ou parceria com geração automática de parcelas.
            </DialogDescription>
          </DialogHeader>

          <div className="grid gap-4 px-6 pb-6 md:grid-cols-2">
            <div>
              <label className="text-sm font-medium mb-1 block">Imóvel *</label>
              <Select value={form.imovel_id} onValueChange={(value) => setForm({ ...form, imovel_id: value })}>
                <SelectTrigger>
                  <SelectValue placeholder="Selecione o imóvel" />
                </SelectTrigger>
                <SelectContent>
                  {imoveis.map((imovel) => (
                    <SelectItem key={imovel.id} value={imovel.id}>
                      {imovel.nome}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <label className="text-sm font-medium mb-1 block">Fazenda *</label>
              <Select value={form.unidade_produtiva_id} onValueChange={(value) => setForm({ ...form, unidade_produtiva_id: value })}>
                <SelectTrigger>
                  <SelectValue placeholder="Selecione a fazenda" />
                </SelectTrigger>
                <SelectContent>
                  {fazendas.map((fazenda) => (
                    <SelectItem key={fazenda.id} value={fazenda.id}>
                      {fazenda.nome}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <label className="text-sm font-medium mb-1 block">Tipo</label>
              <Select value={form.tipo} onValueChange={(value) => setForm({ ...form, tipo: value })}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="ARRENDAMENTO">Arrendamento</SelectItem>
                  <SelectItem value="PARCERIA">Parceria</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div>
              <label className="text-sm font-medium mb-1 block">Arrendatário</label>
              <Select value={form.arrendatario_tipo} onValueChange={(value) => setForm({ ...form, arrendatario_tipo: value })}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="PESSOA_FISICA">Pessoa física</SelectItem>
                  <SelectItem value="PESSOA_JURIDICA">Pessoa jurídica</SelectItem>
                  <SelectItem value="FAZENDA_TENANT">Outra fazenda</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div>
              <label className="text-sm font-medium mb-1 block">Área arrendada (ha) *</label>
              <Input
                type="number"
                step="0.0001"
                value={form.area_arrendada_ha}
                onChange={(e) => setForm({ ...form, area_arrendada_ha: e.target.value })}
              />
            </div>

            <div>
              <label className="text-sm font-medium mb-1 block">Valor *</label>
              <Input
                type="number"
                step="0.01"
                value={form.valor}
                onChange={(e) => setForm({ ...form, valor: e.target.value })}
              />
            </div>

            <div>
              <label className="text-sm font-medium mb-1 block">Modalidade</label>
              <Select value={form.valor_modalidade} onValueChange={(value) => setForm({ ...form, valor_modalidade: value })}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="FIXO_BRL">Fixo em BRL</SelectItem>
                  <SelectItem value="FIXO_SACAS">Fixo em sacas</SelectItem>
                  <SelectItem value="PERCENTUAL">Percentual</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div>
              <label className="text-sm font-medium mb-1 block">Periodicidade</label>
              <Select value={form.periodicidade} onValueChange={(value) => setForm({ ...form, periodicidade: value })}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="MENSAL">Mensal</SelectItem>
                  <SelectItem value="SEMESTRAL">Semestral</SelectItem>
                  <SelectItem value="ANUAL">Anual</SelectItem>
                  <SelectItem value="SAFRA">Safra</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div>
              <label className="text-sm font-medium mb-1 block">Início *</label>
              <Input
                type="date"
                value={form.data_inicio}
                onChange={(e) => setForm({ ...form, data_inicio: e.target.value })}
              />
            </div>

            <div>
              <label className="text-sm font-medium mb-1 block">Fim *</label>
              <Input
                type="date"
                value={form.data_fim}
                onChange={(e) => setForm({ ...form, data_fim: e.target.value })}
              />
            </div>

            <div>
              <label className="text-sm font-medium mb-1 block">Dia de vencimento</label>
              <Input
                type="number"
                min={1}
                max={28}
                value={form.dia_vencimento}
                onChange={(e) => setForm({ ...form, dia_vencimento: e.target.value })}
              />
            </div>

            <div>
              <label className="text-sm font-medium mb-1 block">Índice de reajuste</label>
              <Input
                value={form.indice_reajuste}
                onChange={(e) => setForm({ ...form, indice_reajuste: e.target.value })}
                placeholder="IGP-M, IPCA..."
              />
            </div>

            <div>
              <label className="text-sm font-medium mb-1 block">Commodity referência</label>
              <Input
                value={form.commodity_referencia}
                onChange={(e) => setForm({ ...form, commodity_referencia: e.target.value })}
                placeholder="SOJA, MILHO..."
              />
            </div>

            <div className="md:col-span-2">
              <label className="text-sm font-medium mb-1 block">Cláusulas e observações</label>
              <Textarea
                rows={4}
                value={form.clausulas_observacoes}
                onChange={(e) => setForm({ ...form, clausulas_observacoes: e.target.value })}
              />
            </div>
          </div>

          <DialogFooter className="px-6 pb-6">
            <Button variant="outline" className="rounded-sm" onClick={() => setOpen(false)}>
              Cancelar
            </Button>
            <Button className="rounded-sm" onClick={handleSubmit} disabled={createMutation.isPending}>
              <ArrowRightLeft className="h-3.5 w-3.5 mr-2" />
              Criar contrato
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  );
}
