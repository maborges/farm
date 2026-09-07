'use client';

import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { getApiBaseUrl } from '@/lib/runtime-config';

interface LancamentoContabilFormProps {
  onSuccess?: () => void;
}

export function LancamentoContabilForm({ onSuccess }: LancamentoContabilFormProps) {
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    data_lancamento: new Date().toISOString().split('T')[0],
    documento: '',
    historico: '',
    valor_debito: 0,
    valor_credito: 0,
    conta_debito: '',
    conta_credito: '',
    centro_custo: '',
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      const response = await fetch(
        `${getApiBaseUrl()}/contabilidade/lancamentos`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify(formData),
        }
      );

      if (response.ok) {
        alert('Lançamento criado com sucesso!');
        setFormData({
          data_lancamento: new Date().toISOString().split('T')[0],
          documento: '',
          historico: '',
          valor_debito: 0,
          valor_credito: 0,
          conta_debito: '',
          conta_credito: '',
          centro_custo: '',
        });
        onSuccess?.();
      }
    } catch (error) {
      console.error('Erro ao criar lançamento:', error);
      alert('Erro ao criar lançamento');
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: name.includes('valor') ? parseFloat(value) || 0 : value,
    }));
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Novo Lançamento Contábil</CardTitle>
        <CardDescription>
          Crie um lançamento contábil manual
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="data_lancamento">Data</Label>
              <Input
                id="data_lancamento"
                name="data_lancamento"
                type="date"
                value={formData.data_lancamento}
                onChange={handleChange}
                required
              />
            </div>
            <div>
              <Label htmlFor="documento">Documento</Label>
              <Input
                id="documento"
                name="documento"
                placeholder="NF, RPA, etc."
                value={formData.documento}
                onChange={handleChange}
              />
            </div>
          </div>

          <div>
            <Label htmlFor="historico">Histórico</Label>
            <Textarea
              id="historico"
              name="historico"
              placeholder="Descrição do lançamento"
              value={formData.historico}
              onChange={handleChange}
              required
              rows={3}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="conta_debito">Conta Débito</Label>
              <Input
                id="conta_debito"
                name="conta_debito"
                placeholder="1.1.1.01"
                value={formData.conta_debito}
                onChange={handleChange}
              />
            </div>
            <div>
              <Label htmlFor="conta_credito">Conta Crédito</Label>
              <Input
                id="conta_credito"
                name="conta_credito"
                placeholder="1.1.2.01"
                value={formData.conta_credito}
                onChange={handleChange}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="valor_debito">Valor Débito</Label>
              <Input
                id="valor_debito"
                name="valor_debito"
                type="number"
                step="0.01"
                value={formData.valor_debito}
                onChange={handleChange}
              />
            </div>
            <div>
              <Label htmlFor="valor_credito">Valor Crédito</Label>
              <Input
                id="valor_credito"
                name="valor_credito"
                type="number"
                step="0.01"
                value={formData.valor_credito}
                onChange={handleChange}
              />
            </div>
          </div>

          <div>
            <Label htmlFor="centro_custo">Centro de Custo</Label>
            <Input
              id="centro_custo"
              name="centro_custo"
              placeholder="CC001"
              value={formData.centro_custo}
              onChange={handleChange}
            />
          </div>

          <Button type="submit" disabled={loading}>
            {loading ? 'Criando...' : 'Criar Lançamento'}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
