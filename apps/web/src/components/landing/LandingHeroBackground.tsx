/**
 * Background padronizado com degradê e efeito fade para as seções Hero das Landing Pages.
 * Utiliza variáveis de tema HSL (primária agro) com transição vertical em fade suave
 * para garantir consistência visual perfeita entre as páginas de Gestão e Agro.
 */
export function LandingHeroBackground() {
  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden" aria-hidden="true">
      {/* Luz radial atmosférica superior com fade-out gradual */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_80%_65%_at_50%_-10%,hsl(var(--primary)/0.16),transparent_75%)] [mask-image:linear-gradient(to_bottom,black_40%,transparent_100%)]" />

      {/* Degradê vertical com efeito fade do topo em direção ao fundo */}
      <div className="absolute inset-0 bg-gradient-to-b from-primary/10 via-primary/[0.03] to-transparent [mask-image:linear-gradient(to_bottom,black_50%,transparent_100%)]" />

      {/* Linha de acento de luz sutil no topo com fade lateral */}
      <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-primary/40 to-transparent" />

      {/* Glows de profundidade com animação suave de flutuação */}
      <div className="float-glow absolute -left-24 top-16 size-64 rounded-full bg-primary/8 blur-3xl" />
      <div className="float-glow-delayed absolute -right-20 top-28 size-52 rounded-full bg-primary/6 blur-3xl" />
    </div>
  );
}

