from .tenant import Tenant
from .unidade_produtiva import UnidadeProdutiva, UnidadeProdutiva as Fazenda
from .auth import Usuario, PerfilAcesso, TenantUsuario, UnidadeProdutivaUsuario, UnidadeProdutivaUsuario as FazendaUsuario, ConviteAcesso, TentativaLogin
from .billing import PlanoAssinatura, AssinaturaTenant, Fatura
from .plan_changes import PlanoPricing, MudancaPlano, CobrancaAsaas, HistoricoBloqueio
from .support import ChamadoSuporte, MensagemChamado
from .knowledge_base import ConhecimentoCategoria, ConhecimentoArtigo
from .configuration import ConfiguracaoSaaS
from .tenant_config import ConfiguracaoTenant
from .categoria_custom import CategoriaCustom, TipoCategoria
from .configuracao_fazenda import ConfiguracaoFazenda
from .historico_configuracao import HistoricoConfiguracao
from .admin_user import AdminUser
from .admin_impersonation import AdminImpersonation
from .sessao import SessaoAtiva
from .cupom import Cupom
from .email_template import EmailTemplate, EmailLog
from .admin_audit_log import AdminAuditLog
from .tenant_audit_log import TenantAuditLog
from .module_usage import ModuleUsageStat
from .crm import PipelineEstagio, LeadCRM, AtividadeCRM
from .sequencial import SequencialContador

# Cadastros — pessoas
from core.cadastros.pessoas.models import (
    Pessoa, PessoaDocumento, PessoaContato, PessoaEndereco, PessoaBancario,
    TipoRelacionamento, PessoaRelacionamento,
    PessoaConsentimento, PessoaAcessoLog,
    PessoaUsuario,
)

# Cadastros — propriedades / áreas rurais
from core.cadastros.propriedades.models import (
    AreaRural, RegistroAmbiental,
)
from core.cadastros.propriedade_imovel.models import PropriedadeImovel

# Cadastros — equipamentos
from core.cadastros.equipamentos.models import Equipamento, EquipamentoAlocacao

# Certificações / ESG
from certificacoes_esg.models import (
    AvaliacaoCertificacao,
    ChecklistCertificacao,
    CriterioCertificacao,
    EvidenciaCertificacao,
    NaoConformidadeCertificacao,
    PassaporteRastreabilidade,
    PassaporteRastreabilidadeEvidencia,
    PassaporteRastreabilidadeEvento,
    PlanoAcaoCertificacao,
    RelatorioESG,
    RelatorioESGEvidencia,
    RelatorioESGIndicador,
    ProgramaCertificacao,
)

# Cadastros — produtos (insumos / almoxarifado)
from core.cadastros.produtos.models import (
    Produto, ProdutoAgricola, ProdutoEstoque, ProdutoEPI, ProdutoCultura,
)

# Cadastros — commodities (produtos de saída / receita)
from core.cadastros.commodities.models import (
    Commodity, CommodityClassificacao, CotacaoCommodity,
    UNIDADES_PESO_FIXO, UNIDADES_SEM_PESO_FIXO,
)

# RH
from rh.models import ColaboradorRH, LancamentoDiaria, Empreitada

# Pecuária
from pecuaria.animal.models import LoteAnimal, Animal, EventoAnimal
from pecuaria.producao.models import ProducaoLeite
from pecuaria.models.manejo import ManejoLote

# Operacional
from operacional.models.frota import PlanoManutencao, OrdemServico, ItemOrdemServico, RegistroManutencao
from operacional.models.estoque import Deposito, SaldoEstoque, LoteEstoque, RequisicaoMaterial, ItemRequisicao, ReservaEstoque, EstoqueLocalizacao
from operacional.models.estoque_implantacao import EstoqueImplantacaoSessao, EstoqueImplantacaoItem
from operacional.models.compras import (
    CotacaoCompra, CotacaoItem, SolicitacaoCompra, SolicitacaoItem, AlocacaoItem,
)
from pecuaria.climatico.models import ModeloZoosanitario
