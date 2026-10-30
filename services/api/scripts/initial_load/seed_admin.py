import asyncio
import sys
from pathlib import Path

# Keep the existing API import root when this module runs from the package.
API_ROOT = Path(__file__).resolve().parents[2]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from core.model_registry import register_models

# Importa e registra o conjunto canônico de modelos antes que uma consulta
# configure os mappers globais do SQLAlchemy.
register_models()

from sqlalchemy.ext.asyncio import AsyncSession
from core.database import async_session_maker
from core.models.auth import Usuario
from core.models.admin_user import AdminUser
from core.models.email_template import EmailTemplate
from core.services.auth_service import hash_password
import uuid


async def seed_admin_user():
    """Cria o admin do backoffice e sua identidade superuser em usuarios."""
    async with async_session_maker() as session:
        from sqlalchemy import func, select

        stmt = select(AdminUser).where(AdminUser.email == "admin@deepfarms.com.br")
        admin = (await session.execute(stmt)).scalar_one_or_none()
        admin_criado = admin is None
        if admin is None:
            admin = AdminUser(
                email="admin@deepfarms.com.br",
                senha_hash=hash_password("agro1234"),
                nome="Administrador",
                role="super_admin",
                ativo=True,
            )
            session.add(admin)

        # O login da aplicação e o fluxo de recuperação usam `usuarios`,
        # enquanto o cadastro de permissões do backoffice usa `admin_users`.
        # As duas identidades compartilham e-mail e hash inicial da senha.
        usuario_stmt = select(Usuario).where(
            func.lower(Usuario.email) == admin.email.strip().lower()
        )
        usuario = (await session.execute(usuario_stmt)).scalar_one_or_none()
        usuario_criado = usuario is None
        if usuario is None:
            usuario = Usuario(
                email=admin.email,
                username=admin.email.split("@", 1)[0][:50],
                senha_hash=admin.senha_hash,
                nome_completo=admin.nome,
                apelido=admin.nome[:20],
                is_superuser=True,
                ativo=admin.ativo,
            )
            session.add(usuario)
        elif not usuario.is_superuser:
            # O seed atribui explicitamente a função administrativa; conserva
            # a senha já existente para não redefinir credenciais em reexecuções.
            usuario.is_superuser = True

        await session.commit()
        if admin_criado or usuario_criado:
            print("✅ Identidades administrativas verificadas/criadas")
        else:
            print("✅ Admin user já existe")


async def seed_email_templates():
    """Cria templates de email padrão."""
    async with async_session_maker() as session:
        templates = [
            {
                "codigo": "WELCOME",
                "nome": "Boas-vindas",
                "assunto": "Bem-vindo ao DeepFarms!",
                "corpo_html": """
                    <h2>Olá {{nome_responsavel}},</h2>
                    <p>Bem-vindo ao DeepFarms!</p>
                    <p>Sua conta foi criada com sucesso.</p>
                    <p><strong>Dados de acesso:</strong></p>
                    <ul>
                        <li>URL: {{tenant_url}}</li>
                        <li>Email: {{email}}</li>
                    </ul>
                    <p><a href="{{tenant_url}}">Acessar sistema</a></p>
                """,
                "corpo_texto": "Bem-vindo ao DeepFarms! Acesse: {{tenant_url}}",
                "variaveis": ["nome_responsavel", "tenant_url", "email"],
                "tipo": "transacional"
            },
            {
                "codigo": "PASSWORD_RESET",
                "nome": "Reset de Senha",
                "assunto": "Redefinição de Senha - DeepFarms",
                "corpo_html": """
                    <h2>Olá {{nome_responsavel}},</h2>
                    <p>Sua senha foi redefinida.</p>
                    <p><strong>Senha temporária:</strong> {{senha_temporaria}}</p>
                    <p>Você será obrigado a alterar no próximo login.</p>
                    <p><a href="{{tenant_url}}">Acessar sistema</a></p>
                """,
                "corpo_texto": "Senha resetada: {{senha_temporaria}}",
                "variaveis": ["nome_responsavel", "senha_temporaria", "tenant_url"],
                "tipo": "transacional"
            }
        ]

        for tpl_data in templates:
            # Verificar se já existe
            from sqlalchemy import select
            stmt = select(EmailTemplate).where(EmailTemplate.codigo == tpl_data["codigo"])
            result = await session.execute(stmt)
            if result.scalar_one_or_none():
                print(f"✅ Template {tpl_data['codigo']} já existe")
                continue

            template = EmailTemplate(**tpl_data)
            session.add(template)

        await session.commit()
        print(f"✅ {len(templates)} templates criados")


async def main():
    print("🚀 Iniciando seed de dados admin...")
    await seed_admin_user()
    await seed_email_templates()
    print("✅ Seed concluído!")


if __name__ == "__main__":
    asyncio.run(main())
