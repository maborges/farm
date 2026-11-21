import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { CampoPwaUpdateBanner } from "../pwa-update-banner";
import { usePwaUpdateStore } from "@/lib/stores/pwa-update-store";
import { useSyncStore } from "@/lib/stores/sync-store";

describe("CampoPwaUpdateBanner", () => {
  beforeEach(() => {
    usePwaUpdateStore.getState().reset();
    useSyncStore.setState({ pendingCount: 0, status: "idle", isOnline: true });
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("não renderiza quando não há atualização ou quando foi dispensado", () => {
    const { container, rerender } = render(<CampoPwaUpdateBanner />);
    expect(container.firstChild).toBeNull();

    usePwaUpdateStore.setState({ hasUpdate: true, dismissed: true });
    rerender(<CampoPwaUpdateBanner />);
    expect(container.firstChild).toBeNull();
  });

  it("exibe título, aviso de preservação offline e botão Atualizar quando há pendentes", () => {
    usePwaUpdateStore.setState({ hasUpdate: true, dismissed: false });
    useSyncStore.setState({ pendingCount: 3 });

    render(<CampoPwaUpdateBanner />);

    expect(screen.getByText("Nova versão disponível")).toBeInTheDocument();
    expect(screen.getByText(/registros pendentes permanecem salvos/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Atualizar/i })).toBeInTheDocument();
  });

  it("chama applyUpdate ao clicar em Atualizar", async () => {
    const user = userEvent.setup();
    const applyUpdateSpy = vi.fn(async () => {});
    usePwaUpdateStore.setState({
      hasUpdate: true,
      dismissed: false,
      applyUpdate: applyUpdateSpy,
    });

    render(<CampoPwaUpdateBanner />);
    await user.click(screen.getByRole("button", { name: /Atualizar/i }));

    expect(applyUpdateSpy).toHaveBeenCalledTimes(1);
  });

  it("oculta o banner ao clicar no botão de dispensar", async () => {
    const user = userEvent.setup();
    usePwaUpdateStore.setState({ hasUpdate: true, dismissed: false });

    const { container } = render(<CampoPwaUpdateBanner />);
    await user.click(screen.getByRole("button", { name: "Dispensar aviso de atualização" }));

    expect(usePwaUpdateStore.getState().dismissed).toBe(true);
    expect(container.firstChild).toBeNull();
  });
});
