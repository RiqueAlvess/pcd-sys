from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from core.models import PCDProfile
from .models import PerfilPCDExtendido, Candidatura, Documento, Notificacao


@receiver(post_save, sender=PCDProfile)
def criar_perfil_extendido(sender, instance, created, **kwargs):
    """
    Cria automaticamente um PerfilPCDExtendido quando um PCDProfile é criado
    """
    if created:
        PerfilPCDExtendido.objects.get_or_create(
            pcd_profile=instance,
            defaults={'percentual_completude': 50}
        )


@receiver(post_save, sender=PCDProfile)
def atualizar_completude_perfil(sender, instance, **kwargs):
    """
    Atualiza o percentual de completude sempre que o PCDProfile é modificado
    """
    try:
        perfil_ext = PerfilPCDExtendido.objects.get(pcd_profile=instance)
        perfil_ext.calcular_completude()
    except PerfilPCDExtendido.DoesNotExist:
        # Criar perfil extendido se não existir
        perfil_ext = PerfilPCDExtendido.objects.create(
            pcd_profile=instance,
            percentual_completude=50
        )
        perfil_ext.calcular_completude()


@receiver(post_save, sender=Candidatura)
def notificar_candidatura_enviada(sender, instance, created, **kwargs):
    """
    Cria notificação quando uma candidatura é enviada
    """
    if created:
        Notificacao.objects.create(
            user=instance.pcd.user,
            tipo='candidatura',
            titulo='Candidatura Enviada',
            mensagem=f'Sua candidatura para a vaga "{instance.vaga.titulo}" na empresa {instance.vaga.empresa.razao_social} foi enviada com sucesso!'
        )


@receiver(post_save, sender=Candidatura)
def notificar_mudanca_status_candidatura(sender, instance, created, **kwargs):
    """
    Cria notificação quando o status de uma candidatura muda
    """
    if not created:  # Só para atualizações, não criações
        status_messages = {
            'em_analise': f'Sua candidatura para "{instance.vaga.titulo}" está sendo analisada pela empresa {instance.vaga.empresa.razao_social}.',
            'entrevista': f'🎉 Parabéns! Você foi selecionado(a) para entrevista na vaga "{instance.vaga.titulo}" da empresa {instance.vaga.empresa.razao_social}.',
            'aprovado': f'🎉 Excelente! Você foi aprovado(a) na vaga "{instance.vaga.titulo}" da empresa {instance.vaga.empresa.razao_social}. Aguarde o contato da empresa.',
            'rejeitado': f'Infelizmente, você não foi selecionado(a) para a vaga "{instance.vaga.titulo}" da empresa {instance.vaga.empresa.razao_social}. Continue tentando, há muitas oportunidades!'
        }
        
        if instance.status in status_messages:
            Notificacao.objects.create(
                user=instance.pcd.user,
                tipo='candidatura',
                titulo=f'Candidatura - {instance.get_status_display()}',
                mensagem=status_messages[instance.status]
            )


@receiver(post_save, sender=Documento)
def notificar_upload_documento(sender, instance, created, **kwargs):
    """
    Cria notificação quando um documento é enviado
    """
    if created:
        tipo_display = instance.get_tipo_display()
        Notificacao.objects.create(
            user=instance.pcd.user,
            tipo='documento',
            titulo=f'{tipo_display} Enviado',
            mensagem=f'Seu {tipo_display.lower()} "{instance.nome_original}" foi enviado com sucesso e está sendo analisado.'
        )


@receiver(post_save, sender=Documento)
def notificar_status_documento(sender, instance, created, **kwargs):
    """
    Cria notificação quando o status de um documento muda
    """
    if not created:  # Só para atualizações
        if instance.status == 'aprovado':
            Notificacao.objects.create(
                user=instance.pcd.user,
                tipo='documento',
                titulo=f'{instance.get_tipo_display()} Aprovado',
                mensagem=f'Seu {instance.get_tipo_display().lower()} "{instance.nome_original}" foi aprovado!'
            )
        elif instance.status == 'rejeitado':
            mensagem = f'Seu {instance.get_tipo_display().lower()} "{instance.nome_original}" foi rejeitado.'
            if instance.observacoes:
                mensagem += f' Motivo: {instance.observacoes}'
            
            Notificacao.objects.create(
                user=instance.pcd.user,
                tipo='documento',
                titulo=f'{instance.get_tipo_display()} Rejeitado',
                mensagem=mensagem
            )


@receiver(post_delete, sender=Documento)
def limpar_arquivo_documento(sender, instance, **kwargs):
    """
    Remove o arquivo do disco quando um documento é deletado
    """
    if instance.arquivo:
        try:
            import os
            if os.path.isfile(instance.arquivo.path):
                os.remove(instance.arquivo.path)
        except Exception:
            # Falha silenciosa se não conseguir remover o arquivo
            pass


@receiver(post_save, sender=PerfilPCDExtendido)
def notificar_perfil_completo(sender, instance, **kwargs):
    """
    Cria notificação quando o perfil atinge 100% de completude
    """
    if instance.percentual_completude == 100:
        # Verifica se já existe uma notificação de perfil completo
        existe_notificacao = Notificacao.objects.filter(
            user=instance.pcd_profile.user,
            tipo='sistema',
            titulo__contains='Perfil Completo'
        ).exists()
        
        if not existe_notificacao:
            Notificacao.objects.create(
                user=instance.pcd_profile.user,
                tipo='sistema',
                titulo='🎉 Perfil 100% Completo!',
                mensagem='Parabéns! Seu perfil está completamente preenchido. Agora você tem acesso a todas as funcionalidades e maior visibilidade para as empresas.'
            )


# Signal para limpar notificações antigas automaticamente
def limpar_notificacoes_antigas():
    """
    Remove notificações mais antigas que 30 dias (pode ser chamado via cron job)
    """
    from django.utils import timezone
    from datetime import timedelta
    
    data_limite = timezone.now() - timedelta(days=30)
    notificacoes_antigas = Notificacao.objects.filter(
        criada_em__lt=data_limite,
        lida=True
    )
    
    count = notificacoes_antigas.count()
    notificacoes_antigas.delete()
    
    return f'{count} notificações antigas removidas'