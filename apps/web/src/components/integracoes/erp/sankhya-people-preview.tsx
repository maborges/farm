import { AlertCircle, Users } from "lucide-react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

export interface SankhyaPersonPreview {
  id: number;
  sankhya_id: string;
  tipo: string;
  nome: string;
  nome_fantasia?: string | null;
  cidade?: string | null;
  uf?: string | null;
  ativo: boolean;
  sincronizado_em?: string | null;
}

type PreviewState =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "empty"; message: string }
  | { kind: "ready"; people: SankhyaPersonPreview[] };

export function buildSankhyaPeoplePreviewState(
  people: SankhyaPersonPreview[],
  loading: boolean,
  error: string | null,
): PreviewState {
  if (loading) return { kind: "loading" };
  if (error) return { kind: "error", message: error };
  if (people.length === 0) {
    return { kind: "empty", message: "Nenhuma pessoa sincronizada até o momento." };
  }
  return { kind: "ready", people };
}

function formatLocation(person: SankhyaPersonPreview) {
  return [person.cidade, person.uf].filter(Boolean).join(" / ") || "Não informado";
}

function formatDateTime(value?: string | null) {
  return value ? new Date(value).toLocaleString("pt-BR") : "Não informado";
}

export function SankhyaPeoplePreview({
  people,
  loading,
  error,
}: {
  people: SankhyaPersonPreview[];
  loading: boolean;
  error: string | null;
}) {
  const state = buildSankhyaPeoplePreviewState(people, loading, error);

  return (
    <Card className="rounded-sm border-border/70">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Users className="h-4 w-4" /> Pessoas recebidas do Sankhya
        </CardTitle>
        <CardDescription>Últimos registros persistidos pelo conector neste produtor.</CardDescription>
      </CardHeader>
      <CardContent>
        {state.kind === "loading" ? (
          <div className="space-y-2" aria-label="Carregando pessoas sincronizadas">
            <Skeleton className="h-8 w-full" />
            <Skeleton className="h-8 w-full" />
            <Skeleton className="h-8 w-full" />
          </div>
        ) : state.kind === "error" ? (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{state.message}</AlertDescription>
          </Alert>
        ) : state.kind === "empty" ? (
          <div className="rounded-sm border border-dashed p-6 text-center text-sm text-muted-foreground">
            {state.message}
          </div>
        ) : (
          <div className="overflow-x-auto rounded-sm border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Nome</TableHead>
                  <TableHead>Tipo</TableHead>
                  <TableHead>Código Sankhya</TableHead>
                  <TableHead>Localidade</TableHead>
                  <TableHead>Situação</TableHead>
                  <TableHead>Sincronizado em</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {state.people.map((person) => (
                  <TableRow key={person.id}>
                    <TableCell className="font-medium">{person.nome}</TableCell>
                    <TableCell>{person.tipo === "FISICA" ? "Pessoa física" : "Pessoa jurídica"}</TableCell>
                    <TableCell>{person.sankhya_id}</TableCell>
                    <TableCell>{formatLocation(person)}</TableCell>
                    <TableCell>{person.ativo ? "Ativo" : "Inativo"}</TableCell>
                    <TableCell>{formatDateTime(person.sincronizado_em)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
