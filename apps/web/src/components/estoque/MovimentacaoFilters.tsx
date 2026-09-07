'use client';

import { useState, useCallback } from 'react';
import { MovimentacaoFilters as FilterType } from '@/hooks/use-estoque';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Card, CardContent } from '@/components/ui/card';
import { X } from 'lucide-react';

interface MovimentacaoFiltersProps {
  onFilterChange: (filters: FilterType) => void;
  depositos?: { id: string; nome: string }[];
  isLoading?: boolean;
}

const TIPOS_MOVIMENTACAO = [
  { value: 'ENTRADA', label: 'Entrada' },
  { value: 'SAIDA', label: 'Saída' },
  { value: 'SAIDA_REVERSA', label: 'Devolução (Reversa)' },
  { value: 'AJUSTE', label: 'Ajuste' },
  { value: 'TRANSFERENCIA', label: 'Transferência' },
];

export function MovimentacaoFilters({
  onFilterChange,
  depositos = [],
  isLoading = false,
}: MovimentacaoFiltersProps) {
  const [filters, setFilters] = useState<FilterType>({});
  const [isOpen, setIsOpen] = useState(false);

  const handleFilterChange = useCallback(
    (key: keyof FilterType, value: any) => {
      const newFilters = { ...filters };

      if (value === '' || value === null) {
        delete newFilters[key];
      } else {
        (newFilters as Record<string, unknown>)[key] = value;
      }

      setFilters(newFilters);
      onFilterChange(newFilters);
    },
    [filters, onFilterChange]
  );

  const handleClearAll = useCallback(() => {
    setFilters({});
    onFilterChange({});
  }, [onFilterChange]);

  const hasActiveFilters = Object.keys(filters).length > 0;

  return (
    <Card>
      <CardContent className="pt-6">
        <div className="space-y-4">
          {/* Summary row */}
          <div className="flex items-center justify-between">
            <div className="text-sm font-medium">Filtros</div>
            {hasActiveFilters && (
              <Button
                variant="ghost"
                size="sm"
                onClick={handleClearAll}
                className="h-auto p-0 text-xs"
              >
                <X className="mr-1 h-3 w-3" />
                Limpar tudo
              </Button>
            )}
          </div>

          {/* Filters grid */}
          <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-5">
            {/* Tipo */}
            <Select
              value={filters.tipo || ''}
              onValueChange={(value) => handleFilterChange('tipo', value)}
              disabled={isLoading}
            >
              <SelectTrigger className="text-xs">
                <SelectValue placeholder="Tipo" />
              </SelectTrigger>
              <SelectContent>
                {TIPOS_MOVIMENTACAO.map((tipo) => (
                  <SelectItem key={tipo.value} value={tipo.value}>
                    {tipo.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            {/* Depósito */}
            {depositos.length > 0 && (
              <Select
                value={filters.deposito_id || ''}
                onValueChange={(value) => handleFilterChange('deposito_id', value)}
                disabled={isLoading}
              >
                <SelectTrigger className="text-xs">
                  <SelectValue placeholder="Depósito" />
                </SelectTrigger>
                <SelectContent>
                  {depositos.map((dep) => (
                    <SelectItem key={dep.id} value={dep.id}>
                      {dep.nome}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}

            {/* Data Início */}
            <Input
              type="date"
              placeholder="Data inicial"
              value={filters.data_inicio || ''}
              onChange={(e) => handleFilterChange('data_inicio', e.target.value)}
              disabled={isLoading}
              className="text-xs"
            />

            {/* Data Fim */}
            <Input
              type="date"
              placeholder="Data final"
              value={filters.data_fim || ''}
              onChange={(e) => handleFilterChange('data_fim', e.target.value)}
              disabled={isLoading}
              className="text-xs"
            />

            {/* Lote */}
            <Input
              type="text"
              placeholder="Número do lote"
              value={filters.numero_lote || ''}
              onChange={(e) => handleFilterChange('numero_lote', e.target.value)}
              disabled={isLoading}
              className="text-xs"
            />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
