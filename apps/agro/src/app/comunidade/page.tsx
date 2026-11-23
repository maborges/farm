import { Users, MapPin, MessageSquare, Handshake, ShieldCheck, Clock, CheckCircle2 } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";

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
    <div className="flex flex-col gap-5">
      {/* Cabeçalho da Seção */}
      <div className="hidden md:flex flex-col gap-1">
        <div className="flex flex-wrap items-center gap-2">
          <h1 className="text-lg sm:text-xl font-bold tracking-tight text-foreground flex items-center gap-2">
            <Users className="size-5 text-purple-600 dark:text-purple-400 shrink-0" />
            <span>Comunidade de Produtores</span>
          </h1>
          <Badge variant="priority">Em Breve</Badge>
        </div>
        <p className="text-xs text-muted-foreground">
          A maior rede digital de relacionamento técnico e colaboração entre produtores rurais do Brasil.
        </p>
      </div>

      <Separator className="hidden md:block" />

      {/* Banner de Apresentação */}
      <Card className="bg-gradient-to-br from-purple-500/5 via-card to-card border-purple-500/20">
        <CardHeader>
          <div className="flex items-center gap-2 text-xs text-purple-600 dark:text-purple-400 font-semibold mb-1">
            <Clock className="size-4" />
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
      <div className="flex flex-col gap-3">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Recursos em Desenvolvimento
        </h2>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
          {RECURSOS_PLANEJADOS.map((recurso) => {
            const Icon = recurso.icone;

            return (
              <Card key={recurso.titulo} className="flex flex-col justify-between">
                <CardHeader>
                  <div className="p-2 rounded-sm bg-purple-500/10 text-purple-700 dark:text-purple-400 w-fit">
                    <Icon className="size-4" />
                  </div>
                  <CardAction>
                    <Badge variant="outline">
                      Planejado para {recurso.fase}
                    </Badge>
                  </CardAction>
                  <CardTitle className="text-sm font-semibold pt-2">
                    {recurso.titulo}
                  </CardTitle>
                  <CardDescription className="text-xs">
                    {recurso.descricao}
                  </CardDescription>
                </CardHeader>

                <CardContent>
                  <Separator className="mb-2.5" />
                  <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
                    <CheckCircle2 className="size-3.5 text-primary shrink-0" />
                    <span>Em conformidade com a LGPD e privacidade garantida</span>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </div>

      {/* Compromisso de Segurança e Privacidade */}
      <Alert variant="default">
        <ShieldCheck className="size-4 text-primary" />
        <AlertTitle className="text-xs">Segurança e Privacidade do Produtor</AlertTitle>
        <AlertDescription className="text-xs">
          Nenhum dado patrimonial, polígono de fazenda ou faturamento comercial do DeepFarms SaaS será exposto na comunidade. A participação de produtores no diretório será estritamente voluntária e consentida, sem criação de contas corporativas ou cobranças implícitas.
        </AlertDescription>
      </Alert>
    </div>
  );
}
