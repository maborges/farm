"use client";

import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import {
  createPropriedadeSchema,
  type CreatePropriedadeInput,
  type PropriedadeResponse,
} from "@farm/zod-schemas";
import { PropriedadeFormFields } from "./form-fields";
import { usePropriedadeMutations } from "@/lib/hooks/use-propriedade-mutations";

interface PropriedadeFormDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  propriedadeEditando?: PropriedadeResponse | null;
  onSuccess?: () => void;
}

const DEFAULT_FORM: CreatePropriedadeInput = {
  nome: "",
  cpf_cnpj: "",
  inscricao_estadual: "",
  ie_isento: false,
  email: "",
  telefone: "",
  nome_fantasia: "",
  regime_tributario: "",
  cor: "#3B82F6",
  icone: "",
  ordem: 0,
  observacoes: "",
};

export function PropriedadeFormDialog({
  open,
  onOpenChange,
  propriedadeEditando,
  onSuccess,
}: PropriedadeFormDialogProps) {
  const dialogKey = `${open ? "open" : "closed"}-${propriedadeEditando?.id ?? "new"}`;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <PropriedadeFormDialogContent
        key={dialogKey}
        propriedadeEditando={propriedadeEditando}
        onOpenChange={onOpenChange}
        onSuccess={onSuccess}
      />
    </Dialog>
  );
}

function PropriedadeFormDialogContent({
  onOpenChange,
  propriedadeEditando,
  onSuccess,
}: Omit<PropriedadeFormDialogProps, "open">) {
  const [form, setForm] = useState<CreatePropriedadeInput>(DEFAULT_FORM);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const mutations = usePropriedadeMutations(onSuccess);

  const handleFieldChange = (field: string, value: any) => {
    setForm((prev) => ({ ...prev, [field]: value }));
    if (errors[field]) {
      setErrors((prev) => {
        const next = { ...prev };
        delete next[field];
        return next;
      });
    }
  };

  const validate = (): boolean => {
    try {
      if (propriedadeEditando) {
        createPropriedadeSchema.partial().parse(form);
      } else {
        createPropriedadeSchema.parse(form);
      }
      setErrors({});
      return true;
    } catch (error: any) {
      const fieldErrors: Record<string, string> = {};
      if (error.errors) {
        error.errors.forEach((err: any) => {
          if (err.path) fieldErrors[err.path[0]] = err.message;
        });
      } else if (error.issues) {
        error.issues.forEach((issue: any) => {
          if (issue.path) fieldErrors[issue.path[0]] = issue.message;
        });
      }
      setErrors(fieldErrors);
      return false;
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;

    if (propriedadeEditando) {
      mutations.atualizar.mutate({
        id: propriedadeEditando.id,
        data: form,
      });
    } else {
      mutations.criar.mutate(form);
    }
  };

  const handleReset = () => {
    setForm(DEFAULT_FORM);
    setErrors({});
    onOpenChange(false);
  };

  const isEditando = !!propriedadeEditando;

  return (
    <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
      <DialogHeader>
        <DialogTitle>
          {isEditando ? "Editar Produtor" : "Novo Produtor"}
        </DialogTitle>
        <DialogDescription>
          {isEditando
            ? "Edite as informações do produtor rural"
            : "Cadastre um novo produtor rural no sistema"}
        </DialogDescription>
      </DialogHeader>

      <form onSubmit={handleSubmit} className="space-y-6">
        <PropriedadeFormFields
          form={form}
          errors={errors}
          onChange={handleFieldChange}
        />

        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            onClick={handleReset}
            disabled={mutations.isPending}
          >
            Cancelar
          </Button>
          <Button
            type="submit"
            disabled={mutations.isPending}
          >
            {mutations.isPending ? "Salvando..." : "Salvar"}
          </Button>
        </DialogFooter>
      </form>
    </DialogContent>
  );
}
