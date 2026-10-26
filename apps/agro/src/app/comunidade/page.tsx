import { Users, MapPin, MessageSquare, Handshake, ShieldCheck, Clock, CheckCircle2 } from "lucide-react";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

const RECURSOS_PLANEJADOS = [
  {
    titulo: "Diretório Regional de Produtores",
    descricao: "Encontre outros produtores por município, estado, culturas cultivadas e interesses em comum para troca de conhecimento agronômico.",
    icone: MapPin,
    fase: "MVP 2",
  },
  {
    titulo: "Grupos Temáticos e Oficiais",
    descricao: "Participe de discussões técnicas sobre soja, milho, café, gado de corte e leite, com injeção automática de boletins de mercado e clima.",
    icone: Users,
    fase: "MVP 3",
  },
  {
    titulo: "Troca Segura de Contatos",
    descricao: "Solicite contato a outros produtores de maneira consentida ('Troca de Cartão de Visitas Digital') sem expor dados pessoais ou telefone sem permissão.",
    icone: Handshake,
    fase: "MVP 2",
  },
  {
    titulo: "Mensageria e Chat em Tempo Real",
    descricao: "Converse diretamente com seus contatos confirmados para negociar sementes, insumos, compartilhar fretes ou tirar dúvidas de campo.",
    icone: MessageSquare,
    fase: "MVP 4",
  },
];

export default function ComunidadePage() {
  return (
    <div className="space-y-5">
      {/* Cabeçalho da Seção */}
      <div className="border-b border-border pb-4">
        <div className="flex items-center gap-2">
          <h1 className="text-lg sm:text-xl font-bold tracking-tight text-foreground flex items-center gap-2">
            <Users className="w-5 h-5 text-purple-600 dark:text-purple-400" />
            Comunidade de Produtores
          </h1>
          <Badge variant="secondary" className="text-[10px]">Em Breve</Badge>
        </div>
        <p className="text-xs text-muted-foreground mt-0.5">
          A maior rede digital de relacionamento técnico e colaboração entre produtores rurais do Brasil.
        </p>
      </div>

      {/* Banner de Apresentação */}
      <Card className="bg-gradient-to-br from-purple-500/5 via-card to-card border-purple-500/20">
        <CardHeader>
          <div className="flex items-center gap-2 text-xs text-purple-600 dark:text-purple-400 font-semibold mb-1">
            <Clock className="w-4 h-4" />
            <span>Funcionalidade em Planejamento Estruturado</span>
          </div>
          <CardTitle className="text-base sm:text-lg">
            Conectando quem produz com quem vivencia os mesmos desafios no campo
          </CardTitle>
          <CardDescription className="text-xs">
            A comunidade DeepFarms Agro foi concebida para criar uma rede qualificada de produtores rurais, livre de spam comercial agressivo e com foco em resultados práticos na lavoura e no rebanho.
          </CardDescription>
        </CardHeader>
      </Card>

      {/* Grid de Recursos Planejados */}
      <div className="space-y-3">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Recursos em Desenvolvimento
        </h2>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
          {RECURSOS_PLANEJADOS.map((recurso) => {
            const Icon = recurso.icone;

            return (
              <Card key={recurso.titulo} className="flex flex-col justify-between">
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between gap-2">
                    <div className="p-2 rounded-sm bg-purple-500/10 text-purple-700 dark:text-purple-400">
                      <Icon className="w-4 h-4" />
                    </div>
                    <Badge variant="outline" className="text-[10px]">
                      Planejado para {recurso.fase}
                    </Badge>
                  </div>
                  <CardTitle className="text-sm font-semibold pt-2">
                    {recurso.titulo}
                  </CardTitle>
                  <CardDescription className="text-xs">
                    {recurso.descricao}
                  </CardDescription>
                </CardHeader>

                <CardContent className="pt-0">
                  <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground border-t border-border/50 pt-2.5">
                    <CheckCircle2 className="w-3.5 h-3.5 text-primary flex-shrink-0" />
                    <span>Em conformidade com a LGPD e privacidade garantida</span>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </div>

      {/* Compromisso de Segurança e Privacidade */}
      <section className="p-4 rounded-sm border border-border bg-muted/30 text-xs space-y-2">
        <div className="flex items-center gap-2 font-semibold text-foreground">
          <ShieldCheck className="w-4 h-4 text-primary" />
          <span>Segurança e Privacidade do Produtor</span>
        </div>
        <p className="text-[11px] text-muted-foreground leading-relaxed">
          Nenhum dado patrimonial, polígono de fazenda ou faturamento comercial do DeepFarms SaaS será exposto na comunidade. A participação de produtores no diretório será estritamente voluntária e consentida, sem criação de contas corporativas ou cobranças implícitas.
        </p>
      </section>
    </div>
  );
}
