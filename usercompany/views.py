from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.messages import constants
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect
from django.utils import timezone
import json

from core.models import Empresa, CategoriaDeficiencia
from userpcd.models import Vaga, Candidatura
from .models import EmpresaExtendida, VagaExtendida, ProcessoSeletivo, NotificacaoEmpresa


def _get_or_create_empresa_extendida(empresa):
    """Helper para obter ou criar empresa extendida"""
    empresa_ext, created = EmpresaExtendida.objects.get_or_create(
        empresa=empresa
    )
    if created:
        empresa_ext.calcular_completude()
    return empresa_ext


def _get_or_create_vaga_extendida(vaga):
    """Helper para obter ou criar vaga extendida"""
    vaga_ext, created = VagaExtendida.objects.get_or_create(
        vaga=vaga
    )
    return vaga_ext


@login_required
def dashboard_empresa(request):
    """Dashboard principal da empresa"""
    if not request.user.is_empresa():
        messages.error(request, 'Acesso negado.')
        return redirect('landing')

    empresa = get_object_or_404(Empresa, user=request.user)
    empresa_ext = _get_or_create_empresa_extendida(empresa)
    
    # Atualizar completude
    empresa_ext.calcular_completude()
    
    # Estatísticas gerais
    vagas_ativas = Vaga.objects.filter(empresa=empresa, status='ativa').count()
    vagas_total = Vaga.objects.filter(empresa=empresa).count()
    candidatos_total = Candidatura.objects.filter(vaga__empresa=empresa).count()
    candidatos_novos = Candidatura.objects.filter(
        vaga__empresa=empresa,
        status='pendente'
    ).count()
    
    # Vagas recentes
    vagas_recentes = Vaga.objects.filter(empresa=empresa)[:5]
    
    # Candidaturas recentes
    candidaturas_recentes = Candidatura.objects.filter(
        vaga__empresa=empresa
    )[:5]
    
    # Notificações não lidas
    notificacoes_nao_lidas = NotificacaoEmpresa.objects.filter(
        empresa=empresa,
        lida=False
    ).count()

    context = {
        'empresa': empresa,
        'empresa_ext': empresa_ext,
        'vagas_ativas': vagas_ativas,
        'vagas_total': vagas_total,
        'candidatos_total': candidatos_total,
        'candidatos_novos': candidatos_novos,
        'vagas_recentes': vagas_recentes,
        'candidaturas_recentes': candidaturas_recentes,
        'notificacoes_nao_lidas': notificacoes_nao_lidas,
    }
    
    return render(request, 'usercompany/dashboard_empresa.html', context)


@login_required
def minhas_vagas(request):
    """Lista de vagas da empresa com filtros"""
    if not request.user.is_empresa():
        messages.error(request, 'Acesso negado.')
        return redirect('landing')

    empresa = get_object_or_404(Empresa, user=request.user)
    
    # Filtros
    status = request.GET.get('status', '')
    tipo = request.GET.get('tipo', '')
    status_medico = request.GET.get('status_medico', '')
    
    vagas = Vaga.objects.filter(empresa=empresa)
    
    if status:
        vagas = vagas.filter(status=status)
    
    # Filtros específicos das extensões
    if tipo or status_medico:
        vagas_ids = []
        for vaga in vagas:
            vaga_ext = _get_or_create_vaga_extendida(vaga)
            
            if tipo and vaga_ext.tipo != tipo:
                continue
            if status_medico and vaga_ext.status_medico != status_medico:
                continue
                
            vagas_ids.append(vaga.id)
        
        vagas = vagas.filter(id__in=vagas_ids)
    
    # Ordenação
    vagas = vagas.order_by('-criada_em')
    
    # Paginação
    paginator = Paginator(vagas, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Adicionar informações extensão para cada vaga
    for vaga in page_obj:
        vaga.vaga_extendida = _get_or_create_vaga_extendida(vaga)
    
    context = {
        'page_obj': page_obj,
        'filtros': {
            'status': status,
            'tipo': tipo,
            'status_medico': status_medico,
        }
    }
    
    return render(request, 'usercompany/minhas_vagas.html', context)


@login_required
def nova_vaga(request):
    """Criar nova vaga"""
    if not request.user.is_empresa():
        messages.error(request, 'Acesso negado.')
        return redirect('landing')

    empresa = get_object_or_404(Empresa, user=request.user)
    
    if request.method == 'POST':
        # Dados básicos da vaga
        titulo = request.POST.get('titulo', '').strip()
        descricao = request.POST.get('descricao', '').strip()
        modalidade = request.POST.get('modalidade', '')
        cidade = request.POST.get('cidade', '').strip()
        uf = request.POST.get('uf', '').strip()
        salario_min = request.POST.get('salario_min', '').strip()
        salario_max = request.POST.get('salario_max', '').strip()
        requisitos = request.POST.get('requisitos', '').strip()
        beneficios = request.POST.get('beneficios', '').strip()
        acessivel = request.POST.get('acessivel') == 'on'
        
        # Dados específicos da extensão
        tipo = request.POST.get('tipo', 'emprego')
        numero_vagas = request.POST.get('numero_vagas', '1')
        duracao_capacitacao = request.POST.get('duracao_capacitacao', '').strip()
        acesso_transporte_publico = request.POST.get('acesso_transporte_publico') == 'on'
        deficiencias_elegiveis = request.POST.getlist('deficiencias_elegiveis')
        
        # Validações básicas
        if not all([titulo, descricao, modalidade, cidade, uf, requisitos]):
            messages.error(request, 'Preencha todos os campos obrigatórios.')
            return render(request, 'usercompany/nova_vaga.html', {
                'deficiencias': CategoriaDeficiencia.objects.all()
            })
        
        try:
            # Criar vaga básica
            vaga = Vaga.objects.create(
                empresa=empresa,
                titulo=titulo,
                descricao=descricao,
                modalidade=modalidade,
                cidade=cidade,
                uf=uf,
                salario_min=float(salario_min) if salario_min else None,
                salario_max=float(salario_max) if salario_max else None,
                requisitos=requisitos,
                beneficios=beneficios,
                acessivel=acessivel,
                status='ativa'
            )
            
            # Criar extensão da vaga
            vaga_ext = VagaExtendida.objects.create(
                vaga=vaga,
                tipo=tipo,
                numero_vagas=int(numero_vagas) if numero_vagas else 1,
                duracao_capacitacao=duracao_capacitacao if tipo == 'capacitacao' else '',
                acesso_transporte_publico=acesso_transporte_publico,
                status_medico='pendente'
            )
            
            # Definir deficiências elegíveis
            if deficiencias_elegiveis:
                vaga_ext.deficiencias_elegiveis.set(deficiencias_elegiveis)
            
            # Criar notificação
            NotificacaoEmpresa.objects.create(
                empresa=empresa,
                tipo='status_vaga',
                titulo='Nova Vaga Criada',
                mensagem=f'Sua vaga "{vaga.titulo}" foi criada e está sendo analisada pela equipe médica.',
                vaga=vaga
            )
            
            messages.success(request, 'Vaga criada com sucesso! Ela está sendo analisada pela equipe médica.')
            return redirect('detalhes_vaga', vaga_id=vaga.id)
            
        except Exception as e:
            messages.error(request, f'Erro ao criar vaga: {str(e)}')
    
    context = {
        'deficiencias': CategoriaDeficiencia.objects.all(),
    }
    
    return render(request, 'usercompany/nova_vaga.html', context)


@login_required
def detalhes_vaga(request, vaga_id):
    """Detalhes de uma vaga específica"""
    if not request.user.is_empresa():
        messages.error(request, 'Acesso negado.')
        return redirect('landing')

    empresa = get_object_or_404(Empresa, user=request.user)
    vaga = get_object_or_404(Vaga, id=vaga_id, empresa=empresa)
    vaga_ext = _get_or_create_vaga_extendida(vaga)
    
    # Atualizar contadores
    vaga_ext.atualizar_contadores()
    
    # Candidatos recentes (primeiros 10)
    candidatos = Candidatura.objects.filter(vaga=vaga)[:10]
    
    # Criar processo seletivo para candidatos que não têm
    for candidatura in candidatos:
        ProcessoSeletivo.objects.get_or_create(
            candidatura=candidatura,
            defaults={'status': 'novo'}
        )
    
    context = {
        'vaga': vaga,
        'vaga_ext': vaga_ext,
        'candidatos': candidatos,
    }
    
    return render(request, 'usercompany/detalhes_vaga.html', context)


@login_required
def editar_vaga(request, vaga_id):
    """Editar uma vaga"""
    if not request.user.is_empresa():
        messages.error(request, 'Acesso negado.')
        return redirect('landing')

    empresa = get_object_or_404(Empresa, user=request.user)
    vaga = get_object_or_404(Vaga, id=vaga_id, empresa=empresa)
    vaga_ext = _get_or_create_vaga_extendida(vaga)
    
    if request.method == 'POST':
        # Atualizar dados básicos
        vaga.titulo = request.POST.get('titulo', '').strip()
        vaga.descricao = request.POST.get('descricao', '').strip()
        vaga.modalidade = request.POST.get('modalidade', '')
        vaga.cidade = request.POST.get('cidade', '').strip()
        vaga.uf = request.POST.get('uf', '').strip()
        
        salario_min = request.POST.get('salario_min', '').strip()
        salario_max = request.POST.get('salario_max', '').strip()
        
        vaga.salario_min = float(salario_min) if salario_min else None
        vaga.salario_max = float(salario_max) if salario_max else None
        vaga.requisitos = request.POST.get('requisitos', '').strip()
        vaga.beneficios = request.POST.get('beneficios', '').strip()
        vaga.acessivel = request.POST.get('acessivel') == 'on'
        
        # Atualizar dados da extensão
        vaga_ext.tipo = request.POST.get('tipo', 'emprego')
        numero_vagas = request.POST.get('numero_vagas', '1')
        vaga_ext.numero_vagas = int(numero_vagas) if numero_vagas else 1
        vaga_ext.duracao_capacitacao = request.POST.get('duracao_capacitacao', '').strip()
        vaga_ext.acesso_transporte_publico = request.POST.get('acesso_transporte_publico') == 'on'
        
        deficiencias_elegiveis = request.POST.getlist('deficiencias_elegiveis')
        
        try:
            vaga.save()
            vaga_ext.save()
            
            # Atualizar deficiências elegíveis
            if deficiencias_elegiveis:
                vaga_ext.deficiencias_elegiveis.set(deficiencias_elegiveis)
            else:
                vaga_ext.deficiencias_elegiveis.clear()
            
            # Se a vaga foi rejeitada, voltar para pendente
            if vaga_ext.status_medico == 'rejeitada':
                vaga_ext.status_medico = 'pendente'
                vaga_ext.save()
                
                NotificacaoEmpresa.objects.create(
                    empresa=empresa,
                    tipo='avaliacao_medica',
                    titulo='Vaga Reenviada para Avaliação',
                    mensagem=f'Sua vaga "{vaga.titulo}" foi reenviada para avaliação médica.',
                    vaga=vaga
                )
            
            messages.success(request, 'Vaga atualizada com sucesso!')
            return redirect('detalhes_vaga', vaga_id=vaga.id)
            
        except Exception as e:
            messages.error(request, f'Erro ao atualizar vaga: {str(e)}')
    
    context = {
        'vaga': vaga,
        'vaga_ext': vaga_ext,
        'deficiencias': CategoriaDeficiencia.objects.all(),
    }
    
    return render(request, 'usercompany/editar_vaga.html', context)


@login_required
@require_POST
@csrf_protect
def encerrar_vaga(request, vaga_id):
    """Encerrar uma vaga"""
    if not request.user.is_empresa():
        return JsonResponse({'error': 'Acesso negado'}, status=403)

    empresa = get_object_or_404(Empresa, user=request.user)
    vaga = get_object_or_404(Vaga, id=vaga_id, empresa=empresa)
    
    if vaga.status == 'encerrada':
        return JsonResponse({'error': 'Vaga já está encerrada'}, status=400)
    
    try:
        vaga.status = 'encerrada'
        vaga.save()
        
        NotificacaoEmpresa.objects.create(
            empresa=empresa,
            tipo='status_vaga',
            titulo='Vaga Encerrada',
            mensagem=f'A vaga "{vaga.titulo}" foi encerrada com sucesso.',
            vaga=vaga
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Vaga encerrada com sucesso!'
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
def candidatos_vaga(request, vaga_id):
    """Lista todos os candidatos de uma vaga"""
    if not request.user.is_empresa():
        messages.error(request, 'Acesso negado.')
        return redirect('landing')

    empresa = get_object_or_404(Empresa, user=request.user)
    vaga = get_object_or_404(Vaga, id=vaga_id, empresa=empresa)
    
    # Filtros
    status = request.GET.get('status', '')
    
    candidatos = Candidatura.objects.filter(vaga=vaga)
    
    if status:
        candidatos = candidatos.filter(status=status)
    
    candidatos = candidatos.order_by('-data_candidatura')
    
    # Paginação
    paginator = Paginator(candidatos, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Criar processo seletivo para candidatos que não têm
    for candidatura in page_obj:
        ProcessoSeletivo.objects.get_or_create(
            candidatura=candidatura,
            defaults={'status': 'novo'}
        )
    
    context = {
        'vaga': vaga,
        'page_obj': page_obj,
        'filtros': {'status': status}
    }
    
    return render(request, 'usercompany/candidatos_vaga.html', context)


@login_required
@require_POST
@csrf_protect
def atualizar_status_candidato(request, candidatura_id):
    """Atualizar status de um candidato"""
    if not request.user.is_empresa():
        return JsonResponse({'error': 'Acesso negado'}, status=403)

    empresa = get_object_or_404(Empresa, user=request.user)
    candidatura = get_object_or_404(Candidatura, id=candidatura_id, vaga__empresa=empresa)
    
    try:
        data = json.loads(request.body)
        novo_status = data.get('status')
        observacoes = data.get('observacoes', '')
        
        if novo_status not in ['pendente', 'em_analise', 'entrevista', 'aprovado', 'rejeitado']:
            return JsonResponse({'error': 'Status inválido'}, status=400)
        
        candidatura.status = novo_status
        candidatura.observacoes = observacoes
        candidatura.save()
        
        # Atualizar processo seletivo
        processo, created = ProcessoSeletivo.objects.get_or_create(
            candidatura=candidatura,
            defaults={'status': 'novo'}
        )
        
        if novo_status == 'em_analise':
            processo.status = 'visualizado'
            processo.data_visualizacao_cv = timezone.now()
        elif novo_status == 'entrevista':
            processo.status = 'entrevista_marcada'
            processo.data_entrevista = timezone.now()
        elif novo_status == 'aprovado':
            processo.status = 'aprovado'
        elif novo_status == 'rejeitado':
            processo.status = 'rejeitado'
        
        processo.observacoes_empresa = observacoes
        processo.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Status atualizado com sucesso!'
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
def visualizar_curriculo(request, candidatura_id):
    """Visualizar currículo de um candidato"""
    if not request.user.is_empresa():
        messages.error(request, 'Acesso negado.')
        return redirect('landing')

    empresa = get_object_or_404(Empresa, user=request.user)
    candidatura = get_object_or_404(Candidatura, id=candidatura_id, vaga__empresa=empresa)
    
    # Marcar CV como visualizado
    processo, created = ProcessoSeletivo.objects.get_or_create(
        candidatura=candidatura,
        defaults={'status': 'novo'}
    )
    
    if processo.status == 'novo':
        processo.status = 'visualizado'
        processo.data_visualizacao_cv = timezone.now()
        processo.save()
    
    # Buscar documentos do candidato
    from userpcd.models import Documento
    curriculo = Documento.objects.filter(
        pcd=candidatura.pcd,
        tipo='curriculo'
    ).first()
    
    laudos = Documento.objects.filter(
        pcd=candidatura.pcd,
        tipo='laudo'
    )
    
    context = {
        'candidatura': candidatura,
        'curriculo': curriculo,
        'laudos': laudos,
        'processo': processo,
    }
    
    return render(request, 'usercompany/visualizar_curriculo.html', context)


@login_required
def editar_perfil_empresa(request):
    """Editar perfil da empresa"""
    if not request.user.is_empresa():
        messages.error(request, 'Acesso negado.')
        return redirect('landing')

    empresa = get_object_or_404(Empresa, user=request.user)
    empresa_ext = _get_or_create_empresa_extendida(empresa)
    
    if request.method == 'POST':
        # Atualizar dados básicos
        empresa.razao_social = request.POST.get('razao_social', '').strip()
        empresa.telefone_principal = request.POST.get('telefone_principal', '').strip()
        empresa.telefone_secundario = request.POST.get('telefone_secundario', '').strip()
        empresa.cnae_principal = request.POST.get('cnae_principal', '').strip()
        empresa.tamanho = request.POST.get('tamanho', '').strip()
        empresa.site = request.POST.get('site', '').strip()
        
        try:
            empresa.save()
            empresa_ext.calcular_completude()
            
            messages.success(request, 'Dados da empresa atualizados com sucesso!')
            return redirect('dashboard_empresa')
            
        except Exception as e:
            messages.error(request, f'Erro ao atualizar dados: {str(e)}')
    
    context = {
        'empresa': empresa,
        'empresa_ext': empresa_ext,
    }
    
    return render(request, 'usercompany/editar_perfil_empresa.html', context)


@login_required
def notificacoes_empresa(request):
    """Lista de notificações da empresa"""
    if not request.user.is_empresa():
        messages.error(request, 'Acesso negado.')
        return redirect('landing')

    empresa = get_object_or_404(Empresa, user=request.user)
    
    if request.method == 'POST':
        # Ações via AJAX
        try:
            data = json.loads(request.body)
            action = data.get('action')
            
            if action == 'marcar_lida':
                notif_id = data.get('notificacao_id')
                notif = NotificacaoEmpresa.objects.get(id=notif_id, empresa=empresa)
                notif.lida = True
                notif.save()
                return JsonResponse({'success': True})
                
            elif action == 'marcar_todas_lidas':
                NotificacaoEmpresa.objects.filter(empresa=empresa, lida=False).update(lida=True)
                return JsonResponse({'success': True})
                
            elif action == 'excluir':
                notif_id = data.get('notificacao_id')
                NotificacaoEmpresa.objects.filter(id=notif_id, empresa=empresa).delete()
                return JsonResponse({'success': True})
                
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    notificacoes = NotificacaoEmpresa.objects.filter(empresa=empresa)
    
    # Marcar como lidas as visualizadas
    notificacoes.filter(lida=False).update(lida=True)
    
    # Paginação
    paginator = Paginator(notificacoes, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
    }
    
    return render(request, 'usercompany/notificacoes_empresa.html', context)


@login_required
def notificacoes_dropdown_empresa(request):
    """API para dropdown de notificações da empresa"""
    if not request.user.is_empresa():
        return JsonResponse({'error': 'Acesso negado'}, status=403)

    empresa = get_object_or_404(Empresa, user=request.user)
    
    notificacoes = NotificacaoEmpresa.objects.filter(empresa=empresa)[:5]
    
    nao_lidas = NotificacaoEmpresa.objects.filter(
        empresa=empresa,
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