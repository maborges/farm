"use client";

import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";
import { Upload } from "lucide-react";
import { useState } from "react";

interface FormFieldProps {
  label: string;
  error?: string;
  required?: boolean;
  children: React.ReactNode;
  className?: string;
}

export function FormField({ label, error, required, children, className }: FormFieldProps) {
  return (
    <div className={cn("space-y-2", className)}>
      <Label>
        {label}
        {required && <span className="text-destructive ml-1">*</span>}
      </Label>
      {children}
      {error && <p className="text-sm text-destructive mt-1">{error}</p>}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Máscaras
// ---------------------------------------------------------------------------

function applyCNPJCPFMask(value: string): string {
  const digits = value.replace(/\D/g, "");
  if (digits.length <= 11) {
    // CPF: 000.000.000-00
    return digits
      .replace(/(\d{3})(\d)/, "$1.$2")
      .replace(/(\d{3})(\d)/, "$1.$2")
      .replace(/(\d{3})(\d{1,2})$/, "$1-$2");
  }
  // CNPJ: 00.000.000/0000-00
  return digits
    .replace(/(\d{2})(\d)/, "$1.$2")
    .replace(/(\d{3})(\d)/, "$1.$2")
    .replace(/(\d{3})(\d)/, "$1/$2")
    .replace(/(\d{4})(\d{1,2})$/, "$1-$2");
}

function applyTelefoneMask(value: string): string {
  const digits = value.replace(/\D/g, "");
  if (digits.length <= 10) {
    // Fixo: (00) 0000-0000
    return digits
      .replace(/(\d{2})(\d)/, "($1) $2")
      .replace(/(\d{4})(\d)/, "$1-$2")
      .replace(/(-\d{4})\d+?$/, "$1");
  }
  // Celular: (00) 00000-0000
  return digits
    .replace(/(\d{2})(\d)/, "($1) $2")
    .replace(/(\d{5})(\d)/, "$1-$2")
    .replace(/(-\d{4})\d+?$/, "$1");
}

function applyIEMask(value: string): string {
  const digits = value.replace(/\D/g, "");
  // IE genérica: agrupa em blocos de 3
  return digits
    .replace(/(\d{3})(\d)/, "$1.$2")
    .replace(/(\d{3})(\d)/, "$1.$2")
    .replace(/(\d{3})(\d{1,3})$/, "$1-$2");
}

// ---------------------------------------------------------------------------
// Helpers de descrição
// ---------------------------------------------------------------------------

const REGIMES_DESCRICAO: Record<string, string> = {
  SIMPLES_NACIONAL: "Simples Nacional",
  LUCRO_PRESUMIDO: "Lucro Presumido",
  LUCRO_REAL: "Lucro Real",
  PRODUTOR_RURAL: "Produtor Rural",
};

// ---------------------------------------------------------------------------
// Componentes de Input com Máscara
// ---------------------------------------------------------------------------

interface MaskedInputProps {
  value: string;
  onChange: (value: string) => void;
  mask: (value: string) => string;
  placeholder?: string;
  maxLength?: number;
  className?: string;
}

export function MaskedInput({ value, onChange, mask, placeholder, maxLength, className }: MaskedInputProps) {
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const raw = e.target.value;
    const masked = mask(raw);
    onChange(masked);
  };

  return (
    <Input
      value={value}
      onChange={handleChange}
      placeholder={placeholder}
      maxLength={maxLength}
      className={className}
    />
  );
}

// ---------------------------------------------------------------------------
// ColorPicker
// ---------------------------------------------------------------------------

interface ColorPickerProps {
  value: string;
  onChange: (value: string) => void;
}

export function ColorPicker({ value, onChange }: ColorPickerProps) {
  return (
    <div className="flex items-center gap-2">
      {/* Color picker nativo */}
      <div className="relative w-10 h-10 rounded-md border border-input overflow-hidden flex-shrink-0">
        <input
          type="color"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="absolute inset-0 w-[150%] h-[150%] -translate-x-[25%] -translate-y-[25%] cursor-pointer"
        />
      </div>
      
      {/* Input de texto com a cor */}
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="#3B82F6"
        className="h-7 w-full min-w-0 rounded-sm border border-input bg-transparent px-2 py-1 text-sm font-mono transition-all outline-none placeholder:text-muted-foreground"
        maxLength={7}
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// IconUploader
// ---------------------------------------------------------------------------

interface IconUploaderProps {
  value: string;
  onChange: (value: string) => void;
}

export function IconUploader({ value, onChange }: IconUploaderProps) {
  const [preview, setPreview] = useState<string | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Lê como base64 para preview imediato
    const reader = new FileReader();
    reader.onloadend = () => {
      setPreview(reader.result as string);
    };
    reader.readAsDataURL(file);

    // Salva apenas nome do arquivo (dentro do limite de 50 chars)
    const name = `upload_${Date.now()}.${file.name.split('.').pop()}`;
    onChange(name);
  };

  const handleRemove = () => {
    setPreview(null);
    onChange("");
  };

  return (
    <div className="flex items-center gap-2">
      {/* Preview */}
      <div className="w-10 h-10 rounded-md border border-input flex-shrink-0 overflow-hidden bg-muted flex items-center justify-center">
        {preview ? (
          <img src={preview} alt="Preview" className="w-full h-full object-cover" />
        ) : value ? (
          <span className="text-xs text-muted-foreground">📷</span>
        ) : (
          <span className="text-muted-foreground text-xs">—</span>
        )}
      </div>

      {/* Botão upload */}
      <label className="cursor-pointer flex-1">
        <div className="h-7 w-full rounded-sm border border-input bg-transparent px-2 py-1 text-sm transition-all flex items-center gap-2 hover:bg-muted/50">
          <Upload className="w-3.5 h-3.5 text-muted-foreground flex-shrink-0" />
          <span className="text-sm text-muted-foreground">
            {value ? "Trocar imagem" : "Carregar imagem"}
          </span>
        </div>
        <input
          type="file"
          accept="image/*"
          onChange={handleFileChange}
          className="hidden"
        />
      </label>

      {value && (
        <button
          type="button"
          onClick={handleRemove}
          className="h-7 px-2 text-xs text-destructive hover:bg-destructive/10 rounded-sm border border-transparent hover:border-destructive/20 transition-all flex-shrink-0"
        >
          Remover
        </button>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// PropriedadeFormFields
// ---------------------------------------------------------------------------

interface PropriedadeFormFieldsProps {
  form: Record<string, any>;
  errors: Record<string, string>;
  onChange: (field: string, value: any) => void;
}

export function PropriedadeFormFields({ form, errors, onChange }: PropriedadeFormFieldsProps) {
  const REGIMES_TRIBUTARIOS = [
    { value: "SIMPLES_NACIONAL", label: "Simples Nacional" },
    { value: "LUCRO_PRESUMIDO", label: "Lucro Presumido" },
    { value: "LUCRO_REAL", label: "Lucro Real" },
    { value: "PRODUTOR_RURAL", label: "Produtor Rural" },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {/* Seção: Informações Básicas */}
      <div className="col-span-full space-y-1">
        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">
          Informações Básicas
        </h3>
        <div className="border-b" />
      </div>

      <FormField label="Nome" error={errors.nome} required className="col-span-2">
        <Input
          value={form.nome}
          onChange={(e) => onChange("nome", e.target.value)}
          placeholder="Nome da propriedade"
          className={errors.nome ? "border-destructive" : ""}
        />
      </FormField>

      <FormField label="Nome Fantasia" error={errors.nome_fantasia}>
        <Input
          value={form.nome_fantasia || ""}
          onChange={(e) => onChange("nome_fantasia", e.target.value)}
          placeholder="Nome fantasia (opcional)"
        />
      </FormField>

      <FormField label="CNPJ/CPF" error={errors.cpf_cnpj}>
        <MaskedInput
          value={form.cpf_cnpj || ""}
          onChange={(v) => onChange("cpf_cnpj", v)}
          mask={applyCNPJCPFMask}
          placeholder="000.000.000-00 ou 00.000.000/0000-00"
          maxLength={18}
        />
      </FormField>

      {/* Seção: Fiscal e Tributário */}
      <FormField label="Inscrição Estadual" error={errors.inscricao_estadual}>
        <MaskedInput
          value={form.inscricao_estadual || ""}
          onChange={(v) => onChange("inscricao_estadual", v)}
          mask={applyIEMask}
          placeholder="000.000.000.000"
          maxLength={20}
        />
      </FormField>

      <div className="flex items-end gap-2">
        <FormField label="Regime Tributário" error={errors.regime_tributario} className="flex-1">
          <Select
            value={form.regime_tributario || ""}
            onValueChange={(value) => onChange("regime_tributario", value)}
          >
            <SelectTrigger>
              <SelectValue placeholder="Selecione o regime" />
            </SelectTrigger>
            <SelectContent>
              {REGIMES_TRIBUTARIOS.map((regime) => (
                <SelectItem key={regime.value} value={regime.value}>
                  {regime.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </FormField>

        <div className="pb-2">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={form.ie_isento}
              onChange={(e) => onChange("ie_isento", e.target.checked)}
              className="h-4 w-4 rounded border-gray-300"
            />
            <span className="text-sm">IE Isento</span>
          </label>
        </div>
      </div>

      {/* Seção: Contato */}

      <FormField label="Email" error={errors.email}>
        <Input
          type="email"
          value={form.email || ""}
          onChange={(e) => onChange("email", e.target.value)}
          placeholder="contato@fazenda.com"
          className={errors.email ? "border-destructive" : ""}
        />
      </FormField>

      <FormField label="Telefone" error={errors.telefone}>
        <MaskedInput
          value={form.telefone || ""}
          onChange={(v) => onChange("telefone", v)}
          mask={applyTelefoneMask}
          placeholder="(11) 99999-9999"
          maxLength={15}
        />
      </FormField>

      {/* Seção: Visual */}
      <div className="col-span-full space-y-1 mt-2">
        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">
          Aparência
        </h3>
        <div className="border-b" />
      </div>

      <FormField label="Cor">
        <ColorPicker
          value={form.cor || "#3B82F6"}
          onChange={(value) => onChange("cor", value)}
        />
      </FormField>

      <FormField label="Ícone" error={errors.icone}>
        <IconUploader
          value={form.icone || ""}
          onChange={(value) => onChange("icone", value)}
        />
      </FormField>

      <FormField label="Ordem" error={errors.ordem}>
        <Input
          type="number"
          value={form.ordem || 0}
          onChange={(e) => onChange("ordem", parseInt(e.target.value) || 0)}
          min={0}
        />
      </FormField>

      {/* Seção: Observações */}
      <div className="col-span-full space-y-1 mt-2">
        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">
          Observações
        </h3>
        <div className="border-b" />
      </div>

      <FormField label="Observações" className="col-span-2">
        <Textarea
          value={form.observacoes || ""}
          onChange={(e) => onChange("observacoes", e.target.value)}
          placeholder="Observações adicionais sobre a propriedade..."
          rows={4}
        />
      </FormField>
    </div>
  );
}
