import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, screen, waitFor, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { PessoaSelect } from "../PessoaSelect";
import { usePessoasOperacionais } from "@/lib/hooks/use-pessoas";
import { useSessionStore } from "@/lib/stores/session-store";

vi.mock("@/lib/hooks/use-pessoas", () => ({
  usePessoasOperacionais: vi.fn(),
}));

describe("PessoaSelect", () => {
  const UP_1 = "uuid-up-1";
  const PESSOAS = [
    { id: "1", pessoa_id: "p1", nome_exibicao: "João Silva", unidade_produtiva_id: UP_1, papeis: ["Motorista"] },
    { id: "2", pessoa_id: "p2", nome_exibicao: "Maria Oliveira", unidade_produtiva_id: UP_1, papeis: ["Gerente", "Agrônoma"] },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
    useSessionStore.setState({
      session: {
        id: 1,
        user_id: "user-1",
        tenant_id: "tenant-1",
        device_id: "dev-1",
        device_token: "token",
        pin_hash: "hash",
        user_name: "Test",
        last_sync_at: new Date().toISOString(),
        modules: [],
        fazenda_ids: [UP_1]
      }
    });
  });

  afterEach(() => {
    cleanup();
  });

  const getMainButton = () => screen.getByTestId("pessoa-select-trigger");

  it("desabilitado sem Unidade Produtiva e exibe mensagem de alerta", () => {
    const onChange = vi.fn();
    render(<PessoaSelect onChange={onChange} />);

    const button = getMainButton();
    expect(button).toBeDisabled();
    expect(screen.getByText(/Selecione primeiro a Unidade Produtiva/i)).toBeInTheDocument();
  });

  it("mostra catálogo da Unidade correta quando clicado", async () => {
    vi.mocked(usePessoasOperacionais).mockReturnValue(PESSOAS);
    
    render(<PessoaSelect unidadeProdutivaId={UP_1} onChange={vi.fn()} />);
    
    const button = getMainButton();
    expect(button).not.toBeDisabled();
    
    await userEvent.click(button);
    
    expect(screen.getByText("João Silva")).toBeInTheDocument();
    expect(screen.getByText("Motorista")).toBeInTheDocument();
    expect(screen.getByText("Maria Oliveira")).toBeInTheDocument();
    expect(screen.getByText("Gerente · Agrônoma")).toBeInTheDocument();
  });

  it("pesquisa por nome ignora acentos e case", async () => {
    vi.mocked(usePessoasOperacionais).mockReturnValue(PESSOAS);
    render(<PessoaSelect unidadeProdutivaId={UP_1} onChange={vi.fn()} />);
    
    await userEvent.click(getMainButton());
    const searchInput = screen.getByPlaceholderText("Buscar por nome...");
    
    // Pesquisa "joao" sem acento
    await userEvent.type(searchInput, "joao");
    
    expect(screen.getByText("João Silva")).toBeInTheDocument();
    expect(screen.queryByText("Maria Oliveira")).not.toBeInTheDocument();
  });

  it("seleciona Pessoa e devolve pessoa_id pelo onChange", async () => {
    vi.mocked(usePessoasOperacionais).mockReturnValue(PESSOAS);
    const onChange = vi.fn();
    render(<PessoaSelect unidadeProdutivaId={UP_1} onChange={onChange} />);
    
    await userEvent.click(getMainButton());
    await userEvent.click(screen.getByText("Maria Oliveira"));
    
    expect(onChange).toHaveBeenCalledWith("p2");
  });

  it("permite limpar seleção via botão nativo", async () => {
    vi.mocked(usePessoasOperacionais).mockReturnValue(PESSOAS);
    const onChange = vi.fn();
    render(<PessoaSelect unidadeProdutivaId={UP_1} value="p1" onChange={onChange} />);
    
    const clearButton = document.querySelector("svg.opacity-50.hover\\:opacity-100");
    expect(clearButton).toBeInTheDocument();
    
    if (clearButton) {
      await userEvent.click(clearButton as Element);
      expect(onChange).toHaveBeenCalledWith(null);
    }
  });

  it("estado carregando quando pessoas é undefined", async () => {
    vi.mocked(usePessoasOperacionais).mockReturnValue(undefined);
    render(<PessoaSelect unidadeProdutivaId={UP_1} onChange={vi.fn()} />);
    
    await userEvent.click(getMainButton());
    expect(screen.getByText("Carregando executores...")).toBeInTheDocument();
  });

  it("estado catálogo não sincronizado se vazio e last_sync_at for null", async () => {
    vi.mocked(usePessoasOperacionais).mockReturnValue([]);
    useSessionStore.setState({
      session: {
        id: 1, user_id: "user-1", tenant_id: "tenant-1", device_id: "dev-1", device_token: "token", pin_hash: "hash", user_name: "Test",
        last_sync_at: null, // Sem sync anterior
        modules: [], fazenda_ids: [UP_1]
      }
    });

    render(<PessoaSelect unidadeProdutivaId={UP_1} onChange={vi.fn()} />);
    await userEvent.click(getMainButton());
    expect(screen.getByText(/ainda não sincronizado/i)).toBeInTheDocument();
  });

  it("estado catálogo vazio se não encontrar ninguém", async () => {
    vi.mocked(usePessoasOperacionais).mockReturnValue([]);
    render(<PessoaSelect unidadeProdutivaId={UP_1} onChange={vi.fn()} />);
    await userEvent.click(getMainButton());
    expect(screen.getByText(/Nenhuma pessoa disponível para esta Unidade Produtiva/i)).toBeInTheDocument();
  });

  it("limpa Pessoa incompatível ao trocar de Unidade", async () => {
    const onChange = vi.fn();
    // Cenário: PessoaSelecionada era 'p1', e a UP atualiza mas 'p1' não está mais lá
    vi.mocked(usePessoasOperacionais).mockReturnValue([
      { id: "3", pessoa_id: "p3", nome_exibicao: "Outro", unidade_produtiva_id: UP_1, papeis: [] },
    ]);
    
    render(<PessoaSelect unidadeProdutivaId={UP_1} value="p1" onChange={onChange} />);
    
    await waitFor(() => {
      expect(onChange).toHaveBeenCalledWith(null);
    });
  });

  afterEach(() => {
    cleanup();
  });
});
