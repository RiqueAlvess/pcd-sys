from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.messages import constants
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect
import mimetypes
import os

from core.models import PCDProfile, CategoriaDeficiencia, Empresa
from .models import Vaga, Candidatura, Documento, Notificacao, PerfilPCDExtendido, Conversa, Mensagem
from django.utils import timezone


def _get_or_create_perfil_extendido(pcd_profile):
    """Helper para obter ou criar perfil estendido"""
    perfil_ext, created = PerfilPCDExtendido.objects.get_or_create(
        pcd_profile=pcd_profile
    )
    if created:
        perfil_ext.calcular_completude()
    return perfil_ext


@login_required
def dashboard_pcd(request):
    """Dashboard principal do usuário PCD"""
    if not request.user.is_pcd():
        messages.error(request, 'Acesso negado.')
        return redirect('landing')

    pcd_profile = get_object_or_404(PCDProfile, user=request.user)
    perfil_ext = _get_or_create_perfil_extendido(pcd_profile)
    
    # Atualizar completude
    perfil_ext.calcular_completude()
    
    # Vagas compatíveis (filtro simples por enquanto)
    vagas_disponiveis = Vaga.objects.filter(
        status='ativa'
    ).exclude(
        candidatos__pcd=pcd_profile
    )[:5]  # Primeiras 5
    
    # Candidaturas recentes
    candidaturas_recentes = Candidatura.objects.filter(
        pcd=pcd_profile
    )[:3]
    
    # Notificações não lidas
    notificacoes_nao_lidas = Notificacao.objects.filter(
        user=request.user,
        lida=False
    ).count()
    
    # Documentos
    curriculo = Documento.objects.filter(
        pcd=pcd_profile,
        tipo='curriculo'
    ).first()
    
    laudos = Documento.objects.filter(
        pcd=pcd_profile,
        tipo='laudo'
    )

    context = {
        'pcd_profile': pcd_profile,
        'perfil_ext': perfil_ext,
        'vagas_disponiveis': vagas_disponiveis,
        'candidaturas_recentes': candidaturas_recentes,
        'notificacoes_nao_lidas': notificacoes_nao_lidas,
        'curriculo': curriculo,
        'laudos': laudos,
        'deficiencias': CategoriaDeficiencia.objects.all(),
    }
    
    return render(request, 'usercore/dashboard_pcd.html', context)


@login_required
@csrf_protect
def editar_perfil_pcd(request):
    """Editar dados pessoais do PCD"""
    if not request.user.is_pcd():
        return JsonResponse({'error': 'Acesso negado'}, status=403)

    pcd_profile = get_object_or_404(PCDProfile, user=request.user)
    perfil_ext = _get_or_create_perfil_extendido(pcd_profile)

    if request.method == 'POST':
        # Dados pessoais básicos
        pcd_profile.nome_completo = request.POST.get('nome_completo', '').strip()
        pcd_profile.telefone = request.POST.get('telefone', '').strip()
        data_nasc = request.POST.get('data_nascimento', '').strip()
        if data_nasc:
            pcd_profile.data_nascimento = data_nasc
        
        # Endereço
        perfil_ext.cep = request.POST.get('cep', '').strip()
        perfil_ext.rua = request.POST.get('rua', '').strip()
        perfil_ext.numero = request.POST.get('numero', '').strip()
        perfil_ext.complemento = request.POST.get('complemento', '').strip()
        perfil_ext.bairro = request.POST.get('bairro', '').strip()
        perfil_ext.cidade = request.POST.get('cidade', '').strip()
        perfil_ext.uf = request.POST.get('uf', '').strip()

        try:
            pcd_profile.save()
            perfil_ext.save()
            perfil_ext.calcular_completude()
            
            messages.add_message(request, constants.SUCCESS,
                               'Dados atualizados com sucesso!')
        except Exception as e:
            messages.add_message(request, constants.ERROR,
                               f'Erro ao salvar dados: {str(e)}')

        return redirect('dashboard_pcd')

    context = {
        'pcd_profile': pcd_profile,
        'perfil_ext': perfil_ext,
    }
    return render(request, 'usercore/editar_perfil.html', context)


@login_required
@csrf_protect
def atualizar_deficiencias(request):
    """Atualizar deficiências do usuário via AJAX"""
    if not request.user.is_pcd():
        return JsonResponse({'error': 'Acesso negado'}, status=403)

    if request.method == 'POST':
        pcd_profile = get_object_or_404(PCDProfile, user=request.user)
        def_ids = request.POST.getlist('deficiencias')
        
        try:
            pcd_profile.deficiencias.set(def_ids)
            perfil_ext = _get_or_create_perfil_extendido(pcd_profile)
            perfil_ext.calcular_completude()
            
            return JsonResponse({
                'success': True,
                'message': 'Deficiências atualizadas com sucesso!',
                'completude': perfil_ext.percentual_completude
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    return JsonResponse({'error': 'Método não permitido'}, status=405)


@login_required
@csrf_protect
def upload_documento(request):
    """Upload de currículo ou laudo médico"""
    if not request.user.is_pcd():
        return JsonResponse({'error': 'Acesso negado'}, status=403)

    if request.method == 'POST':
        pcd_profile = get_object_or_404(PCDProfile, user=request.user)
        
        arquivo = request.FILES.get('arquivo')
        tipo = request.POST.get('tipo')
        cid_10 = request.POST.get('cid_10', '').strip()
        
        if not arquivo or not tipo:
            return JsonResponse({'error': 'Arquivo e tipo são obrigatórios'}, status=400)
        
        # Validar tipo de arquivo
        content_type, _ = mimetypes.guess_type(arquivo.name)
        tipos_permitidos = [
            'application/pdf',
            'image/jpeg',
            'image/png',
            'image/jpg'
        ]
        
        if content_type not in tipos_permitidos:
            return JsonResponse({
                'error': 'Tipo de arquivo não permitido. Use PDF, JPG ou PNG.'
            }, status=400)
        
        # Validar tamanho (5MB max)
        if arquivo.size > 5 * 1024 * 1024:
            return JsonResponse({
                'error': 'Arquivo muito grande. Máximo 5MB.'
            }, status=400)
        
        try:
            # Para currículo, remover o anterior
            if tipo == 'curriculo':
                Documento.objects.filter(
                    pcd=pcd_profile,
                    tipo='curriculo'
                ).delete()
            
            documento = Documento.objects.create(
                pcd=pcd_profile,
                tipo=tipo,
                arquivo=arquivo,
                nome_original=arquivo.name,
                cid_10=cid_10 if tipo == 'laudo' else ''
            )
            
            # Atualizar completude
            perfil_ext = _get_or_create_perfil_extendido(pcd_profile)
            perfil_ext.calcular_completude()
            
            return JsonResponse({
                'success': True,
                'message': f'{documento.get_tipo_display()} enviado com sucesso!',
                'documento_id': documento.id,
                'data_upload': documento.data_upload.strftime('%d/%m/%Y %H:%M'),
                'completude': perfil_ext.percentual_completude
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    return JsonResponse({'error': 'Método não permitido'}, status=405)


@login_required
def vagas_disponiveis(request):
    """Listagem de vagas com filtros"""
    if not request.user.is_pcd():
        messages.error(request, 'Acesso negado.')
        return redirect('landing')

    pcd_profile = get_object_or_404(PCDProfile, user=request.user)
    
    # Filtros
    modalidade = request.GET.get('modalidade', '')
    cidade = request.GET.get('cidade', '')
    uf = request.GET.get('uf', '')
    
    vagas = Vaga.objects.filter(status='ativa')
    
    if modalidade:
        vagas = vagas.filter(modalidade=modalidade)
    if cidade:
        vagas = vagas.filter(cidade__icontains=cidade)
    if uf:
        vagas = vagas.filter(uf__iexact=uf)
    
    # Excluir vagas já candidatadas
    vagas = vagas.exclude(candidatos__pcd=pcd_profile)
    
    # Paginação
    paginator = Paginator(vagas, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Opções para filtros
    modalidades = Vaga.MODALIDADE_CHOICES
    
    context = {
        'page_obj': page_obj,
        'modalidades': modalidades,
        'filtros': {
            'modalidade': modalidade,
            'cidade': cidade,
            'uf': uf,
        }
    }
    
    return render(request, 'usercore/vagas_disponiveis.html', context)


@login_required
@require_POST
@csrf_protect
def candidatar_vaga(request, vaga_id):
    """Candidatar-se a uma vaga"""
    if not request.user.is_pcd():
        return JsonResponse({'error': 'Acesso negado'}, status=403)

    pcd_profile = get_object_or_404(PCDProfile, user=request.user)
    vaga = get_object_or_404(Vaga, id=vaga_id, status='ativa')
    
    # Verificar se já se candidatou
    if Candidatura.objects.filter(pcd=pcd_profile, vaga=vaga).exists():
        return JsonResponse({'error': 'Você já se candidatou a esta vaga'}, status=400)
    
    try:
        candidatura = Candidatura.objects.create(
            pcd=pcd_profile,
            vaga=vaga
        )
        
        # Criar notificação
        Notificacao.objects.create(
            user=request.user,
            tipo='candidatura',
            titulo='Candidatura Enviada',
            mensagem=f'Sua candidatura para "{vaga.titulo}" foi enviada com sucesso!'
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Candidatura enviada com sucesso!'
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
def minhas_candidaturas(request):
    """Lista de candidaturas do usuário"""
    if not request.user.is_pcd():
        messages.error(request, 'Acesso negado.')
        return redirect('landing')

    pcd_profile = get_object_or_404(PCDProfile, user=request.user)
    
    candidaturas = Candidatura.objects.filter(pcd=pcd_profile)
    
    # Paginação
    paginator = Paginator(candidaturas, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
    }
    
    return render(request, 'usercore/minhas_candidaturas.html', context)


@login_required
def notificacoes(request):
    """Lista de notificações"""
    notificacoes = Notificacao.objects.filter(user=request.user)
    
    # Marcar como lidas
    notificacoes.filter(lida=False).update(lida=True)
    
    # Paginação
    paginator = Paginator(notificacoes, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
    }
    
    return render(request, 'usercore/notificacoes.html', context)


@login_required
def notificacoes_dropdown(request):
    """API para dropdown de notificações"""
    notificacoes = Notificacao.objects.filter(
        user=request.user
    )[:5]

    nao_lidas = Notificacao.objects.filter(
        user=request.user,
        lida=False
    ).count()

    data = {
        'notificacoes': [
            {
                'id': n.id,
                'titulo': n.titulo,
                'mensagem': n.mensagem[:100] + '...' if len(n.mensagem) > 100 else n.mensagem,
                'lida': n.lida,
                'criada_em': n.criada_em.strftime('%d/%m %H:%M'),
                'tipo': n.tipo
            }
            for n in notificacoes
        ],
        'nao_lidas': nao_lidas
    }

    return JsonResponse(data)


@login_required
def lista_conversas_pcd(request):
    """Lista de conversas do usuário PCD"""
    if not request.user.is_pcd():
        messages.error(request, 'Acesso negado.')
        return redirect('landing')

    pcd_profile = get_object_or_404(PCDProfile, user=request.user)

    # Buscar todas as conversas do PCD
    conversas = Conversa.objects.filter(pcd=pcd_profile).select_related(
        'empresa__user', 'vaga', 'candidatura'
    ).order_by('-atualizada_em')

    # Adicionar informações extras para cada conversa
    for conversa in conversas:
        conversa.ultima_msg = conversa.ultima_mensagem()
        conversa.nao_lidas = conversa.mensagens_nao_lidas_pcd()

    # Paginação
    paginator = Paginator(conversas, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'total_conversas': conversas.count(),
    }

    return render(request, 'userpcd/lista_conversas_pcd.html', context)


@login_required
def sala_chat_pcd(request, conversa_id):
    """Sala de chat entre PCD e Empresa"""
    if not request.user.is_pcd():
        messages.error(request, 'Acesso negado.')
        return redirect('landing')

    pcd_profile = get_object_or_404(PCDProfile, user=request.user)
    conversa = get_object_or_404(
        Conversa,
        id=conversa_id,
        pcd=pcd_profile
    )

    if request.method == 'POST':
        # Enviar nova mensagem
        conteudo = request.POST.get('mensagem', '').strip()

        if conteudo:
            try:
                mensagem = Mensagem.objects.create(
                    conversa=conversa,
                    remetente_empresa=False,
                    conteudo=conteudo
                )

                # Atualizar timestamp da conversa
                conversa.atualizada_em = timezone.now()
                conversa.save()

                messages.success(request, 'Mensagem enviada com sucesso!')
                return redirect('sala_chat_pcd', conversa_id=conversa.id)

            except Exception as e:
                messages.error(request, f'Erro ao enviar mensagem: {str(e)}')
        else:
            messages.error(request, 'A mensagem não pode estar vazia.')

    # Marcar mensagens não lidas como lidas
    mensagens_nao_lidas = conversa.mensagens.filter(
        remetente_empresa=True,
        lida=False
    )
    mensagens_nao_lidas.update(lida=True)

    # Buscar todas as mensagens da conversa
    mensagens = conversa.mensagens.all()

    context = {
        'conversa': conversa,
        'mensagens': mensagens,
        'empresa': conversa.empresa,
        'vaga': conversa.vaga,
        'candidatura': conversa.candidatura,
    }

    return render(request, 'userpcd/sala_chat_pcd.html', context)