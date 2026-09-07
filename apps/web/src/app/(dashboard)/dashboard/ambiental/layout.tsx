import type { ReactNode } from "react";
import { UnidadeContextNotice } from "@/components/ambiental/unidade-context-notice";

export default function AmbientalLayout({ children }: { children: ReactNode }) {
  return (
    <>
      <UnidadeContextNotice />
      {children}
    </>
  );
}
