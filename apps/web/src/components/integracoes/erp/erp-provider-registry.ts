import type { ComponentType } from "react";
import { SankhyaConsole } from "@/components/integracoes/sankhya-console";

export type ErpProviderConsoleComponent = ComponentType;

export const ERP_PROVIDER_CONSOLES = {
  sankhya: SankhyaConsole,
} satisfies Record<string, ErpProviderConsoleComponent>;
