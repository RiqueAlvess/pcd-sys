from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.messages import constants
from .models import User, Empresa, PCDProfile, CategoriaDeficiencia
from django.contrib.auth.decorators import login_required
from django.urls import reverse, NoReverseMatch 


@login_required
def dashboard(request):
    """
    Dashboard principal baseado no tipo de usuário.
    Redireciona para o dashboard específico de acordo com o role do usuário.
    """
    user = request.user

    if user.is_pcd():
        return redirect('dashboard_pcd')
    elif user.is_empresa():
        return redirect('dashboard_empresa')
    elif user.is_medico():
        return redirect('dashboard_medico')
    elif user.is_root():
        return redirect('admin:index')
    else:
        # Fallback para usuários sem role específico
        messages.info(request, 'Por favor, complete seu cadastro.')
        return redirect('escolha_tipo')

# ------------------------- PÁGINAS BÁSICAS -------------------------- #

def landing(request):
    return redirect('escolha_tipo')

def escolha_tipo(request):
    return render(request, 'core/escolha_tipo.html')

# ------------------------- LOGIN ------------------------------------ #

def login_view(request):
    """
    Exibe formulário de login e autentica usuário.
    Versão robusta que não quebra se dashboards não existirem.
    """
    # Se já está logado, redireciona inteligentemente
    if request.user.is_authenticated:
        return smart_redirect_after_login(request.user, request)

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        senha = request.POST.get('senha', '').strip()

        if not username or not senha:
            messages.add_message(request, constants.ERROR,
                                 'Preencha usuário e senha.')
            return render(request, 'core/login.html')

        user = authenticate(request, username=username, password=senha)

        if user is None:
            messages.add_message(request, constants.ERROR,
                                 'Usuário ou senha inválidos.')
            return render(request, 'core/login.html')

        # Login bem-sucedido
        login(request, user)
        messages.add_message(request, constants.SUCCESS,
                             'Login realizado com sucesso.')
        
        # Se for empresa, verificar se tem perfil
        if user.is_empresa():
            try:
                Empresa.objects.get(user=user)
            except Empresa.DoesNotExist:
                # Criar um perfil básico se não existir
                try:
                    Empresa.objects.create(
                        user=user,
                        razao_social=f"Empresa de {user.username}",
                        telefone_principal="Não informado",
                        cnpj="Não informado",
                        cnae_principal="Não informado",
                        tamanho="1-10",
                        site=None
                    )
                    messages.add_message(request, constants.WARNING,
                                      'Detectamos que seu perfil de empresa estava incompleto. Por favor, atualize suas informações.')
                except Exception as e:
                    messages.add_message(request, constants.ERROR,
                                      f'Erro ao recuperar seu perfil: {str(e)}')
        
        # Redirecionamento inteligente e seguro
        return smart_redirect_after_login(user, request)

    return render(request, 'core/login.html')


def logout_view(request):
    """
    View de logout que aceita tanto GET quanto POST
    """
    logout(request)
    messages.add_message(request, constants.SUCCESS, 'Logout realizado com sucesso.')
    return redirect('login')


def smart_redirect_after_login(user, request):
    """
    Função auxiliar para redirecionamento seguro após login
    Não quebra se as URLs não existirem
    """
    try:
        # Tenta redirecionar para dashboard específico do usuário
        if user.is_pcd():
            # Verifica se a URL existe antes de redirecionar
            reverse('dashboard_pcd')
            return redirect('dashboard_pcd')
        elif user.is_empresa():
            # Quando implementarmos dashboard da empresa
            reverse('dashboard_empresa')
            return redirect('dashboard_empresa')
        elif user.is_medico():
            reverse('dashboard_medico')
            return redirect('dashboard_medico')
        elif user.is_root():
            return redirect('admin:index')
        else:
            return redirect('escolha_tipo')

    except NoReverseMatch:
        # Se a URL específica não existir, usa fallbacks
        if user.is_pcd():
            messages.info(request, 'Dashboard PCD em desenvolvimento. Redirecionando...')
            return redirect('escolha_tipo')
        elif user.is_empresa():
            messages.info(request, 'Dashboard empresa em desenvolvimento.')
            return redirect('escolha_tipo')
        elif user.is_root():
            return redirect('admin:index')
        else:
            return redirect('escolha_tipo')

    except Exception as e:
        # Fallback final em caso de qualquer outro erro
        messages.warning(request, 'Redirecionando para página inicial.')
        return redirect('escolha_tipo')
    
# ------------------------- CADASTRO PCD ----------------------------- #

def cadastro_pcd(request):
    """
    Cadastro inicial simplificado para PCD.
    Dispara mensagens de:
      - ERROR  : usuário duplicado ou campo obrigatório faltando
      - SUCCESS: cadastro concluído
    """
    if request.method == 'POST':
        username  = request.POST.get('username', '').strip()
        email     = request.POST.get('email', '').strip()
        senha     = request.POST.get('senha', '').strip()
        telefone  = request.POST.get('telefone', '').strip()
        cpf       = request.POST.get('cpf', '').strip()
        data_nasc = request.POST.get('data_nascimento', '').strip()
        def_ids   = request.POST.getlist('deficiencias')

        obrigatorios = [username, email, senha, telefone, cpf, data_nasc]
        if not all(obrigatorios):
            messages.add_message(request, constants.ERROR,
                                 'Preencha todos os campos obrigatórios.')
            return _render_pcd_form(request)

        if User.objects.filter(username=username).exists():
            messages.add_message(request, constants.ERROR,
                                 'Nome de usuário já existe.')
            return _render_pcd_form(request)

        user = User.objects.create_user(username=username,
                                        email=email,
                                        password=senha,
                                        role='pcd')
        pcd = PCDProfile.objects.create(user=user,
                                        telefone=telefone,
                                        cpf=cpf,
                                        data_nascimento=data_nasc)
        pcd.deficiencias.set(def_ids)

        login(request, user)
        messages.add_message(request, constants.SUCCESS,
                             'Cadastro realizado com sucesso.')
        return redirect('dashboard')

    return _render_pcd_form(request)

def _render_pcd_form(request):
    """Helper para reapresentar formulário PCD com lista de deficiências."""
    deficiencias = CategoriaDeficiencia.objects.all()
    return render(request, 'core/cadastro_pcd.html',
                  {'deficiencias': deficiencias})

# ------------------------- CADASTRO EMPRESA ------------------------- #

def cadastro_empresa(request):
    """
    Cadastro inicial da empresa.
    Mensagens:
      - ERROR  : usuário duplicado ou campo obrigatório faltando
      - SUCCESS: cadastro concluído
    """
    if request.method == 'POST':
        username  = request.POST.get('username', '').strip()
        email     = request.POST.get('email', '').strip()
        senha     = request.POST.get('senha', '').strip()

        tel1      = request.POST.get('telefone_principal', '').strip()
        tel2      = request.POST.get('telefone_secundario', '').strip()
        cnpj      = request.POST.get('cnpj', '').strip()
        razao     = request.POST.get('razao_social', '').strip()
        cnae      = request.POST.get('cnae_principal', '').strip()
        tamanho   = request.POST.get('tamanho', '').strip()
        site      = request.POST.get('site', '').strip()

        obrig = [username, email, senha, tel1, cnpj, razao, cnae, tamanho]
        if not all(obrig):
            messages.add_message(request, constants.ERROR,
                                 'Preencha todos os campos obrigatórios.')
            return render(request, 'core/cadastro_empresa.html')

        if User.objects.filter(username=username).exists():
            messages.add_message(request, constants.ERROR,
                                 'Nome de usuário já existe.')
            return render(request, 'core/cadastro_empresa.html')

        user = User.objects.create_user(username=username,
                                        email=email,
                                        password=senha,
                                        role='empresa')

        Empresa.objects.create(user=user,
                               telefone_principal=tel1,
                               telefone_secundario=tel2,
                               cnpj=cnpj,
                               razao_social=razao,
                               cnae_principal=cnae,
                               tamanho=tamanho,
                               site=site or None)

        login(request, user)
        messages.add_message(request, constants.SUCCESS,
                             'Cadastro realizado com sucesso.')
        return redirect('dashboard')

    return render(request, 'core/cadastro_empresa.html')
