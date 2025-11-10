from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.contrib.messages import constants
from .models import User, Empresa, PCDProfile, CategoriaDeficiencia
from django.contrib.auth.decorators import login_required
from django.urls import reverse, NoReverseMatch
from django.utils import timezone
from userpcd.models import PerfilPCDExtendido, Notificacao, Documento
from usercompany.models import VagaExtendida, NotificacaoEmpresa
from userpcd.models import Vaga 


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
                        tamanho="1-10"
                    )
                    messages.add_message(request, constants.WARNING,
                                      'Detectamos que seu perfil de empresa estava incompleto. Por favor, atualize suas informações.')
                except Exception as e:
                    messages.add_message(request, constants.ERROR,
                                      f'Erro ao recuperar seu perfil: {str(e)}')
        
        # Redirecionamento inteligente e seguro
        return smart_redirect_after_login(user, request)

    return render(request, 'core/login.html')


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


# ------------------------- VIEWS MÉDICO ----------------------------- #

@login_required
def dashboard_medico(request):
    """Dashboard para médicos avaliadores"""
    if not request.user.is_medico():
        messages.error(request, 'Acesso negado.')
        return redirect('dashboard')

    # Estatísticas gerais
    pcds_pendentes = PerfilPCDExtendido.objects.filter(status_medico='pendente').count()
    vagas_pendentes = VagaExtendida.objects.filter(status_medico='pendente').count()

    # Avaliações realizadas pelo médico
    pcds_avaliados = PerfilPCDExtendido.objects.filter(medico_avaliador=request.user).count()
    vagas_avaliadas = VagaExtendida.objects.filter(medico_avaliador=request.user).count()

    context = {
        'pcds_pendentes': pcds_pendentes,
        'vagas_pendentes': vagas_pendentes,
        'pcds_avaliados': pcds_avaliados,
        'vagas_avaliadas': vagas_avaliadas,
    }

    return render(request, 'core/medico/dashboard.html', context)


@login_required
def listar_pcds_pendentes(request):
    """Lista PCDs pendentes de avaliação médica"""
    if not request.user.is_medico():
        messages.error(request, 'Acesso negado.')
        return redirect('dashboard')

    # Filtros
    status_filter = request.GET.get('status', 'pendente')

    if status_filter == 'todos':
        perfis = PerfilPCDExtendido.objects.select_related('pcd_profile__user').all()
    else:
        perfis = PerfilPCDExtendido.objects.filter(status_medico=status_filter).select_related('pcd_profile__user')

    perfis = perfis.order_by('-pcd_profile__criado_em')

    context = {
        'perfis': perfis,
        'status_filter': status_filter,
        'status_choices': PerfilPCDExtendido.STATUS_MEDICO_CHOICES,
    }

    return render(request, 'core/medico/listar_pcds.html', context)


@login_required
def avaliar_pcd(request, pcd_id):
    """Formulário de avaliação de PCD"""
    if not request.user.is_medico():
        messages.error(request, 'Acesso negado.')
        return redirect('dashboard')

    pcd_profile = get_object_or_404(PCDProfile, id=pcd_id)
    perfil_extendido, created = PerfilPCDExtendido.objects.get_or_create(pcd_profile=pcd_profile)

    # Buscar documentos do PCD
    documentos = Documento.objects.filter(pcd=pcd_profile).order_by('-data_upload')

    if request.method == 'POST':
        status_medico = request.POST.get('status_medico')
        observacoes = request.POST.get('observacoes_medicas', '')

        if not status_medico:
            messages.error(request, 'Por favor, selecione um status de avaliação.')
            return redirect('avaliar_pcd', pcd_id=pcd_id)

        # Atualizar avaliação
        perfil_extendido.status_medico = status_medico
        perfil_extendido.observacoes_medicas = observacoes
        perfil_extendido.data_avaliacao_medica = timezone.now()
        perfil_extendido.medico_avaliador = request.user
        perfil_extendido.save()

        # Criar notificação para o PCD
        criar_notificacao_avaliacao_pcd(pcd_profile, status_medico)

        messages.success(request, f'Avaliação de {pcd_profile.user.username} realizada com sucesso.')
        return redirect('listar_pcds_pendentes')

    context = {
        'pcd_profile': pcd_profile,
        'perfil_extendido': perfil_extendido,
        'documentos': documentos,
        'status_choices': PerfilPCDExtendido.STATUS_MEDICO_CHOICES,
    }

    return render(request, 'core/medico/avaliar_pcd.html', context)


@login_required
def listar_vagas_pendentes(request):
    """Lista vagas pendentes de avaliação médica"""
    if not request.user.is_medico():
        messages.error(request, 'Acesso negado.')
        return redirect('dashboard')

    # Filtros
    status_filter = request.GET.get('status', 'pendente')

    if status_filter == 'todos':
        vagas = VagaExtendida.objects.select_related('vaga__empresa').all()
    else:
        vagas = VagaExtendida.objects.filter(status_medico=status_filter).select_related('vaga__empresa')

    vagas = vagas.order_by('-vaga__criada_em')

    context = {
        'vagas': vagas,
        'status_filter': status_filter,
        'status_choices': VagaExtendida.STATUS_MEDICO_CHOICES,
    }

    return render(request, 'core/medico/listar_vagas.html', context)


@login_required
def avaliar_vaga(request, vaga_id):
    """Formulário de avaliação de vaga"""
    if not request.user.is_medico():
        messages.error(request, 'Acesso negado.')
        return redirect('dashboard')

    vaga = get_object_or_404(Vaga, id=vaga_id)
    vaga_extendida, created = VagaExtendida.objects.get_or_create(vaga=vaga)

    # Buscar todas as categorias de deficiência
    categorias = CategoriaDeficiencia.objects.all()

    if request.method == 'POST':
        status_medico = request.POST.get('status_medico')
        observacoes = request.POST.get('observacoes_medicas', '')
        deficiencias_ids = request.POST.getlist('deficiencias_elegiveis')

        if not status_medico:
            messages.error(request, 'Por favor, selecione um status de avaliação.')
            return redirect('avaliar_vaga', vaga_id=vaga_id)

        # Atualizar avaliação
        vaga_extendida.status_medico = status_medico
        vaga_extendida.observacoes_medicas = observacoes
        vaga_extendida.data_avaliacao_medica = timezone.now()
        vaga_extendida.medico_avaliador = request.user
        vaga_extendida.save()

        # Atualizar deficiências elegíveis
        if status_medico == 'aprovada':
            vaga_extendida.deficiencias_elegiveis.set(deficiencias_ids)

        # Criar notificação para a empresa
        criar_notificacao_avaliacao_vaga(vaga, status_medico)

        messages.success(request, f'Avaliação da vaga "{vaga.titulo}" realizada com sucesso.')
        return redirect('listar_vagas_pendentes')

    context = {
        'vaga': vaga,
        'vaga_extendida': vaga_extendida,
        'categorias': categorias,
        'status_choices': VagaExtendida.STATUS_MEDICO_CHOICES,
    }

    return render(request, 'core/medico/avaliar_vaga.html', context)


# ------------------------- FUNÇÕES AUXILIARES ----------------------- #

def criar_notificacao_avaliacao_pcd(pcd_profile, status_medico):
    """Cria notificação para PCD após avaliação médica"""
    status_display = dict(PerfilPCDExtendido.STATUS_MEDICO_CHOICES).get(status_medico, status_medico)

    mensagens = {
        'enquadravel': 'Parabéns! Você foi classificado como Enquadrável. Agora você pode se candidatar às vagas disponíveis.',
        'sugestivo': 'Você foi classificado como Sugestivo de Enquadrável. Isso significa que você pode se candidatar às vagas, mas pode ser necessário avaliação adicional em alguns casos.',
        'nao_enquadravel': 'Infelizmente, você não foi classificado como enquadrável no momento. Entre em contato conosco para mais informações.',
        'avaliacao_adicional': 'É necessária uma avaliação médica adicional (presencial ou por telemedicina) para completar sua classificação. Entraremos em contato em breve.',
        'necessita_laudo': 'É necessário um laudo médico detalhado ou exame atualizado para completar sua avaliação. Por favor, envie a documentação necessária.',
    }

    mensagem = mensagens.get(status_medico, 'Sua avaliação médica foi concluída. Acesse seu perfil para mais detalhes.')

    Notificacao.objects.create(
        user=pcd_profile.user,
        tipo='sistema',
        titulo=f'Avaliação Médica Concluída: {status_display}',
        mensagem=mensagem
    )


def criar_notificacao_avaliacao_vaga(vaga, status_medico):
    """Cria notificação para empresa após avaliação de vaga"""
    status_display = dict(VagaExtendida.STATUS_MEDICO_CHOICES).get(status_medico, status_medico)

    mensagens = {
        'aprovada': 'Sua vaga foi aprovada! Ela agora está disponível para matching com candidatos PCD compatíveis.',
        'rejeitada': 'Infelizmente, sua vaga não foi aprovada. Entre em contato para mais informações.',
        'pendente': 'Sua vaga está em análise pela equipe médica.',
    }

    mensagem = mensagens.get(status_medico, 'A avaliação médica da sua vaga foi concluída.')

    NotificacaoEmpresa.objects.create(
        empresa=vaga.empresa,
        tipo='avaliacao_medica',
        titulo=f'Avaliação da Vaga "{vaga.titulo}": {status_display}',
        mensagem=mensagem,
        vaga=vaga
    )
