"use client";

import type { ReactNode } from "react";
import { CheckCircle, Loader2, RefreshCw, Save } from "lucide-react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type {
  ConsoleResourceState,
  ErpConsoleConfig,
  ProviderFieldDefinition,
  ProviderSchemaResponse,
} from "./types";

interface ErpConfigurationSectionProps {
  sectionId?: string;
  schemaState: ConsoleResourceState<ProviderSchemaResponse>;
  configState: ConsoleResourceState<ErpConsoleConfig>;
  connectionFields: ProviderFieldDefinition[];
  credentialFields: ProviderFieldDefinition[];
  hasEditableFields: boolean;
  saving?: boolean;
  testing?: boolean;
  onRetry: () => void;
  onSave: () => void;
  onTestConnection: () => void;
  renderField: (field: ProviderFieldDefinition) => React.ReactNode;
  summaryContent?: ReactNode;
  saveAllowed?: boolean;
  testAllowed?: boolean;
}

export interface ErpConfigurationSectionViewState {
  schemaMessage:
    | "loading"
    | "forbidden"
    | "error"
    | "empty"
    | "config_forbidden"
    | "config_error"
    | "config_not_found"
    | "none";
  message: string | null;
  showForm: boolean;
  showActions: boolean;
  hasFields: boolean;
}

function hasAnyFields(
  connectionFields: ProviderFieldDefinition[],
  credentialFields: ProviderFieldDefinition[],
) {
  return connectionFields.length > 0 || credentialFields.length > 0;
}

export function resolveErpConfigurationSectionViewState(params: {
  schemaState: ConsoleResourceState<ProviderSchemaResponse>;
  configState: ConsoleResourceState<ErpConsoleConfig>;
  connectionFields: ProviderFieldDefinition[];
  credentialFields: ProviderFieldDefinition[];
  hasEditableFields: boolean;
  saveAllowed?: boolean;
}) {
  const {
    schemaState,
    configState,
    connectionFields,
    credentialFields,
    hasEditableFields,
    saveAllowed = true,
  } = params;
  const hasFields = hasAnyFields(connectionFields, credentialFields);
  const showForm = schemaState.status === "success" && hasEditableFields;
  const showActions = showForm && saveAllowed;

  if (schemaState.status === "loading") {
    return {
      schemaMessage: "loading",
      message: "Carregando campos de configuração...",
      showForm,
      showActions,
      hasFields,
    } satisfies ErpConfigurationSectionViewState;
  }

  if (schemaState.status === "forbidden") {
    return {
      schemaMessage: "forbidden",
      message:
        "Você pode visualizar a integração, mas não possui permissão para acessar ou alterar sua configuração.",
      showForm,
      showActions,
      hasFields,
    } satisfies ErpConfigurationSectionViewState;
  }

  if (schemaState.status === "error" || schemaState.status === "not_found") {
    return {
      schemaMessage: "error",
      message: "Não foi possível carregar os campos de configuração deste ERP.",
      showForm,
      showActions,
      hasFields,
    } satisfies ErpConfigurationSectionViewState;
  }

  if (schemaState.status === "empty") {
    return {
      schemaMessage: "empty",
      message: "Este provider não disponibilizou campos de configuração.",
      showForm,
      showActions,
      hasFields,
    } satisfies ErpConfigurationSectionViewState;
  }

  if (configState.status === "forbidden") {
    return {
      schemaMessage: "config_forbidden",
      message: "Você não possui permissão para acessar a configuração desta integração.",
      showForm,
      showActions,
      hasFields,
    } satisfies ErpConfigurationSectionViewState;
  }

  if (configState.status === "error") {
    return {
      schemaMessage: "config_error",
      message:
        configState.message || "Não foi possível carregar a configuração atual desta integração.",
      showForm,
      showActions,
      hasFields,
    } satisfies ErpConfigurationSectionViewState;
  }

  if (configState.status === "not_found") {
    return {
      schemaMessage: "config_not_found",
      message:
        "Esta integração ainda não possui configuração salva. Preencha os campos abaixo para iniciar a conexão.",
      showForm,
      showActions,
      hasFields,
    } satisfies ErpConfigurationSectionViewState;
  }

  return {
    schemaMessage: "none",
    message: null,
    showForm,
    showActions,
    hasFields,
  } satisfies ErpConfigurationSectionViewState;
}

function renderSchemaStateMessage(
  viewState: ErpConfigurationSectionViewState,
  onRetry: () => void,
) {
  if (viewState.schemaMessage === "loading") {
    return (
      <Alert>
        <Loader2 className="h-4 w-4 animate-spin" />
        <AlertDescription>{viewState.message}</AlertDescription>
      </Alert>
    );
  }

  if (viewState.schemaMessage === "forbidden") {
    return (
      <Alert variant="destructive">
        <AlertDescription>
          {viewState.message}
        </AlertDescription>
      </Alert>
    );
  }

  if (viewState.schemaMessage === "error") {
    return (
      <Alert variant="destructive">
        <AlertDescription className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <span>{viewState.message}</span>
          <Button type="button" size="sm" variant="outline" onClick={onRetry}>
            <RefreshCw className="mr-2 h-4 w-4" />
            Tentar novamente
          </Button>
        </AlertDescription>
      </Alert>
    );
  }

  if (viewState.schemaMessage === "empty") {
    return (
      <Alert>
        <AlertDescription>
          {viewState.message}
        </AlertDescription>
      </Alert>
    );
  }

  if (viewState.schemaMessage === "config_forbidden") {
    return (
      <Alert variant="destructive">
        <AlertDescription>
          {viewState.message}
        </AlertDescription>
      </Alert>
    );
  }

  if (viewState.schemaMessage === "config_error") {
    return (
      <Alert variant="destructive">
        <AlertDescription className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <span>{viewState.message}</span>
          <Button type="button" size="sm" variant="outline" onClick={onRetry}>
            <RefreshCw className="mr-2 h-4 w-4" />
            Tentar novamente
          </Button>
        </AlertDescription>
      </Alert>
    );
  }

  if (viewState.schemaMessage === "config_not_found") {
    return (
      <Alert>
        <AlertDescription>
          {viewState.message}
        </AlertDescription>
      </Alert>
    );
  }

  return null;
}

export function ErpConfigurationSection({
  sectionId = "erp-configuracao",
  schemaState,
  configState,
  connectionFields,
  credentialFields,
  hasEditableFields,
  saving = false,
  testing = false,
  onRetry,
  onSave,
  onTestConnection,
  renderField,
  summaryContent,
  saveAllowed = true,
  testAllowed = true,
}: ErpConfigurationSectionProps) {
  const viewState = resolveErpConfigurationSectionViewState({
    schemaState,
    configState,
    connectionFields,
    credentialFields,
    hasEditableFields,
    saveAllowed,
  });
  const stateMessage = renderSchemaStateMessage(viewState, onRetry);
  const { showForm, showActions, hasFields } = viewState;

  return (
    <Card id={sectionId} tabIndex={-1}>
      <CardHeader>
        <CardTitle>Configuração da integração</CardTitle>
        <CardDescription>
          O console mostra ambiente, gateway, endereços e credenciais mascaradas. Nenhum segredo é exibido em tela.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {stateMessage}

        {showForm ? (
          <>
            {connectionFields.length > 0 ? (
              <div className="space-y-4">
                <h3 className="border-b pb-2 text-sm font-medium">Configurações de conexão</h3>
                <div className="grid gap-4 md:grid-cols-2">{connectionFields.map(renderField)}</div>
              </div>
            ) : null}

            {credentialFields.length > 0 ? (
              <div className="mt-6 space-y-4">
                <h3 className="border-b pb-2 text-sm font-medium text-destructive">Credenciais e segredos</h3>
                <div className="grid gap-4 md:grid-cols-2">{credentialFields.map(renderField)}</div>
              </div>
            ) : null}
          </>
        ) : null}

        {!showForm && schemaState.status === "success" && !hasFields ? (
          <Alert>
            <AlertDescription>
              Este provider não disponibilizou campos de configuração.
            </AlertDescription>
          </Alert>
        ) : null}

        {showActions ? (
          <div className="mt-6 flex flex-wrap gap-2">
            <Button size="sm" variant="outline" onClick={onSave} disabled={saving}>
              {saving ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Salvando...
                </>
              ) : (
                <>
                  <Save className="mr-2 h-4 w-4" />
                  Salvar dados
                </>
              )}
            </Button>
            {testAllowed ? (
              <Button size="sm" variant="outline" onClick={onTestConnection} disabled={testing}>
                {testing ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Testando...
                  </>
                ) : (
                  <>
                    <CheckCircle className="mr-2 h-4 w-4" />
                    Testar comunicação
                  </>
                )}
              </Button>
            ) : null}
            <Button size="sm" variant="outline" onClick={onRetry}>
              <RefreshCw className="mr-2 h-4 w-4" />
              Atualizar situação
            </Button>
          </div>
        ) : null}

        {summaryContent}
      </CardContent>
    </Card>
  );
}
