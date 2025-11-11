"""
Views para o painel médico - Classificação de PCDs e Avaliação de Vagas
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Prefetch
from django.utils import timezone

from core.models import PCDProfile, ClassificacaoPCD, User
from userpcd.models import Vaga, Notificacao, Documento, PerfilPCDExtendido
from usercompany.models import VagaExtendida, NotificacaoEmpresa


def medico_required(view_func):
    """Decorator para verificar se o usuário é médico"""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Você precisa estar autenticado.')
            return redirect('login')
        if not request.user.is_medico():
            messages.error(request, 'Acesso restrito a médicos.')
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper


@login_required
@medico_required
def dashboard_medico(request):
    """Dashboard principal do médico com resumo das atividades"""

    # Contadores
    pcds_pendentes = PCDProfile.objects.filter(
        Q(classificacoes__isnull=True) |
        Q(classificacoes__status='exame_necessario')
    ).distinct().count()

    vagas_pendentes = VagaExtendida.objects.filter(
        status_medico='pendente',
        vaga__status='ativa'
    ).count()

    classificacoes_realizadas = ClassificacaoPCD.objects.filter(
        medico=request.user
    ).count()

    vagas_avaliadas = VagaExtendida.objects.filter(
        status_medico__in=['aprovada', 'rejeitada']
    ).count()

    # Atividades recentes
    atividades_recentes = ClassificacaoPCD.objects.filter(
        medico=request.user
    ).select_related('pcd', 'pcd__user').order_by('-criado_em')[:10]

    context = {
        'pcds_pendentes': pcds_pendentes,
        'vagas_pendentes': vagas_pendentes,
        'classificacoes_realizadas': classificacoes_realizadas,
        'vagas_avaliadas': vagas_avaliadas,
        'atividades_recentes': atividades_recentes,
    }

    return render(request, 'medico/dashboard.html', context)


@login_required
@medico_required
def lista_pcd_pendentes(request):
    """Lista PCDs aguardando avaliação médica"""

    # Filtros
    status_filter = request.GET.get('status', '')
    busca = request.GET.get('busca', '')

    # Query base: PCDs com perfil estendido
    # Usar Prefetch para ordenar classificações e pegar apenas a última
    ultima_classificacao_prefetch = Prefetch(
        'classificacoes',
        queryset=ClassificacaoPCD.objects.select_related('medico').order_by('-criado_em'),
        to_attr='classificacoes_ordenadas'
    )

    pcds = PCDProfile.objects.select_related(
        'user',
        'perfilpcdextendido'
    ).prefetch_related(
        'deficiencias',
        ultima_classificacao_prefetch
    )

    # Filtro de status
    if status_filter == 'pendente':
        pcds = pcds.filter(classificacoes__isnull=True)
    elif status_filter == 'avaliado':
        pcds = pcds.filter(classificacoes__isnull=False).distinct()
    elif status_filter == 'exame_necessario':
        pcds = pcds.filter(classificacoes__status='exame_necessario').distinct()

    # Busca por nome ou CPF
    if busca:
        pcds = pcds.filter(
            Q(nome_completo__icontains=busca) |
            Q(cpf__icontains=busca) |
            Q(user__email__icontains=busca)
        )

    pcds = pcds.order_by('-criado_em')

    # Adicionar ultima_classificacao a cada PCD para uso no template
    pcds_list = list(pcds)
    for pcd in pcds_list:
        pcd.ultima_classificacao = pcd.classificacoes_ordenadas[0] if pcd.classificacoes_ordenadas else None

    context = {
        'pcds': pcds_list,
        'status_filter': status_filter,
        'busca': busca,
    }

    return render(request, 'medico/lista_pcd.html', context)


@login_required
@medico_required
def avaliar_pcd(request, pcd_id):
    """Formulário para avaliar e classificar um PCD"""

    pcd = get_object_or_404(
        PCDProfile.objects.select_related('user', 'perfilpcdextendido')
                          .prefetch_related('deficiencias', 'classificacoes'),
        id=pcd_id
    )

    # Buscar documentos do PCD
    documentos = Documento.objects.filter(pcd=pcd).order_by('-data_upload')

    # Última classificação (se existir)
    ultima_classificacao = pcd.classificacoes.order_by('-criado_em').first()

    if request.method == 'POST':
        status = request.POST.get('status')
        observacao = request.POST.get('observacao', '')
        documentos_analisados = request.POST.get('documentos_analisados', '')

        # Criar nova classificação
        classificacao = ClassificacaoPCD.objects.create(
            pcd=pcd,
            medico=request.user,
            status=status,
            observacao=observacao,
            documentos_analisados=documentos_analisados
        )

        # Atualizar status_medico no PerfilPCDExtendido (se existir)
        try:
            perfil_estendido = pcd.perfilpcdextendido
            # Mapear status da classificação para status do perfil
            if status == 'enquadravel':
                perfil_estendido.status_medico = 'enquadravel'
            elif status == 'sugestivo':
                perfil_estendido.status_medico = 'sugestivo'
            elif status == 'nao_enquadravel':
                perfil_estendido.status_medico = 'nao_enquadravel'
            else:
                perfil_estendido.status_medico = 'pendente'
            perfil_estendido.save()
        except PerfilPCDExtendido.DoesNotExist:
            pass

        # Criar notificação para o PCD
        status_display = dict(ClassificacaoPCD.STATUS_CHOICES).get(status, status)
        Notificacao.objects.create(
            user=pcd.user,
            tipo='sistema',
            titulo='Classificação Médica Realizada',
            mensagem=f'Sua classificação médica foi concluída. Status: {status_display}.'
        )

        messages.success(request, f'PCD {pcd.nome_completo} classificado com sucesso!')
        return redirect('lista_pcd_pendentes')

    context = {
        'pcd': pcd,
        'documentos': documentos,
        'ultima_classificacao': ultima_classificacao,
        'status_choices': ClassificacaoPCD.STATUS_CHOICES,
    }

    return render(request, 'medico/avaliar_pcd.html', context)


@login_required
@medico_required
def vagas_pendentes(request):
    """Lista vagas aguardando avaliação médica"""

    # Filtros
    status_filter = request.GET.get('status', 'pendente')
    tipo_filter = request.GET.get('tipo', '')
    busca = request.GET.get('busca', '')

    # Query base
    vagas_ext = VagaExtendida.objects.select_related(
        'vaga',
        'vaga__empresa',
        'vaga__empresa__user'
    ).prefetch_related('deficiencias_elegiveis')

    # Filtro de status médico
    if status_filter:
        vagas_ext = vagas_ext.filter(status_medico=status_filter)

    # Filtro de tipo
    if tipo_filter:
        vagas_ext = vagas_ext.filter(tipo=tipo_filter)

    # Filtro apenas vagas ativas
    vagas_ext = vagas_ext.filter(vaga__status='ativa')

    # Busca por título ou empresa
    if busca:
        vagas_ext = vagas_ext.filter(
            Q(vaga__titulo__icontains=busca) |
            Q(vaga__empresa__razao_social__icontains=busca)
        )

    vagas_ext = vagas_ext.order_by('-vaga__criada_em')

    context = {
        'vagas_ext': vagas_ext,
        'status_filter': status_filter,
        'tipo_filter': tipo_filter,
        'busca': busca,
    }

    return render(request, 'medico/lista_vagas.html', context)


@login_required
@medico_required
def avaliar_vaga(request, vaga_id):
    """Formulário para avaliar uma vaga e definir deficiências elegíveis"""

    vaga_ext = get_object_or_404(
        VagaExtendida.objects.select_related('vaga', 'vaga__empresa')
                             .prefetch_related('deficiencias_elegiveis'),
        vaga_id=vaga_id
    )

    # Buscar todas as categorias de deficiência disponíveis
    from core.models import CategoriaDeficiencia
    categorias = CategoriaDeficiencia.objects.all()

    if request.method == 'POST':
        status_medico = request.POST.get('status_medico')
        observacoes_medicas = request.POST.get('observacoes_medicas', '')
        deficiencias_ids = request.POST.getlist('deficiencias_elegiveis')

        # Atualizar status e observações
        vaga_ext.status_medico = status_medico
        vaga_ext.observacoes_medicas = observacoes_medicas
        vaga_ext.save()

        # Atualizar deficiências elegíveis
        if deficiencias_ids:
            vaga_ext.deficiencias_elegiveis.set(deficiencias_ids)
        else:
            vaga_ext.deficiencias_elegiveis.clear()

        # Criar notificação para a empresa
        status_display = dict(VagaExtendida.STATUS_MEDICO_CHOICES).get(status_medico, status_medico)
        NotificacaoEmpresa.objects.create(
            empresa=vaga_ext.vaga.empresa,
            tipo='avaliacao_medica',
            titulo='Avaliação Médica da Vaga Concluída',
            mensagem=f'A vaga "{vaga_ext.vaga.titulo}" foi avaliada. Status: {status_display}.',
            vaga=vaga_ext.vaga
        )

        messages.success(request, f'Vaga "{vaga_ext.vaga.titulo}" avaliada com sucesso!')
        return redirect('vagas_pendentes')

    context = {
        'vaga_ext': vaga_ext,
        'categorias': categorias,
        'deficiencias_selecionadas': vaga_ext.deficiencias_elegiveis.values_list('id', flat=True),
        'status_choices': VagaExtendida.STATUS_MEDICO_CHOICES,
    }

    return render(request, 'medico/avaliar_vaga.html', context)


@login_required
@medico_required
def historico_classificacoes(request):
    """Histórico de todas as classificações realizadas pelo médico"""

    classificacoes = ClassificacaoPCD.objects.filter(
        medico=request.user
    ).select_related('pcd', 'pcd__user').order_by('-criado_em')

    # Filtros
    status_filter = request.GET.get('status', '')
    if status_filter:
        classificacoes = classificacoes.filter(status=status_filter)

    context = {
        'classificacoes': classificacoes,
        'status_filter': status_filter,
        'status_choices': ClassificacaoPCD.STATUS_CHOICES,
    }

    return render(request, 'medico/historico_classificacoes.html', context)
