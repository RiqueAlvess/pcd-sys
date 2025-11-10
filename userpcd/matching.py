"""
Sistema de Matching Automatizado entre Vagas e PCDs
Calcula compatibilidade baseada em múltiplos critérios
"""

from django.db.models import Q
from core.models import PCDProfile
from userpcd.models import Vaga
from usercompany.models import VagaExtendida


class MatchingEngine:
    """Motor de matching que calcula compatibilidade entre PCDs e Vagas"""

    # Pesos para cada critério de matching
    PESO_DEFICIENCIA = 40  # Compatibilidade de deficiência
    PESO_LOCALIZACAO = 20  # Proximidade geográfica
    PESO_MODALIDADE = 15   # Modalidade de trabalho
    PESO_PERFIL = 15       # Completude do perfil
    PESO_STATUS = 10       # Status médico do PCD

    @classmethod
    def calcular_match(cls, pcd_profile, vaga):
        """
        Calcula o score de compatibilidade entre um PCD e uma vaga
        Retorna um valor de 0 a 100
        """
        score = 0
        detalhes = {}

        # 1. Verificar deficiências compatíveis (40 pontos)
        score_deficiencia, detalhes_def = cls._match_deficiencia(pcd_profile, vaga)
        score += score_deficiencia
        detalhes['deficiencia'] = detalhes_def

        # 2. Verificar localização (20 pontos)
        score_loc, detalhes_loc = cls._match_localizacao(pcd_profile, vaga)
        score += score_loc
        detalhes['localizacao'] = detalhes_loc

        # 3. Verificar modalidade (15 pontos)
        score_mod, detalhes_mod = cls._match_modalidade(pcd_profile, vaga)
        score += score_mod
        detalhes['modalidade'] = detalhes_mod

        # 4. Verificar completude do perfil (15 pontos)
        score_perfil, detalhes_perfil = cls._match_perfil(pcd_profile)
        score += score_perfil
        detalhes['perfil'] = detalhes_perfil

        # 5. Verificar status médico (10 pontos)
        score_status, detalhes_status = cls._match_status(pcd_profile)
        score += score_status
        detalhes['status'] = detalhes_status

        return {
            'score': int(score),
            'detalhes': detalhes,
            'nivel': cls._classificar_match(score)
        }

    @classmethod
    def _match_deficiencia(cls, pcd_profile, vaga):
        """Verifica compatibilidade de deficiências"""
        try:
            vaga_ext = VagaExtendida.objects.get(vaga=vaga)
            deficiencias_vaga = set(vaga_ext.deficiencias_elegiveis.all())

            if not deficiencias_vaga:
                return cls.PESO_DEFICIENCIA, 'Vaga aceita todas as deficiências'

            deficiencias_pcd = set(pcd_profile.deficiencias.all())

            if not deficiencias_pcd:
                return 0, 'PCD não informou deficiências'

            match = deficiencias_vaga.intersection(deficiencias_pcd)

            if match:
                deficiencias_nomes = [str(d) for d in match]
                return cls.PESO_DEFICIENCIA, f'Compatível: {", ".join(deficiencias_nomes)}'
            else:
                return 0, 'Deficiências não compatíveis'

        except VagaExtendida.DoesNotExist:
            return cls.PESO_DEFICIENCIA, 'Vaga aceita todas as deficiências'

    @classmethod
    def _match_localizacao(cls, pcd_profile, vaga):
        """Verifica compatibilidade de localização"""
        try:
            perfil_ext = pcd_profile.perfil_extendido

            if not perfil_ext.uf or not perfil_ext.cidade:
                return cls.PESO_LOCALIZACAO * 0.5, 'Localização não informada'

            if perfil_ext.cidade.lower() == vaga.cidade.lower() and perfil_ext.uf == vaga.uf:
                return cls.PESO_LOCALIZACAO, f'Mesma cidade: {vaga.cidade}/{vaga.uf}'

            if perfil_ext.uf == vaga.uf:
                return cls.PESO_LOCALIZACAO * 0.5, f'Mesmo estado: {vaga.uf}'

            return 0, f'Localização diferente'

        except:
            return 0, 'Localização não informada'

    @classmethod
    def _match_modalidade(cls, pcd_profile, vaga):
        """Verifica compatibilidade de modalidade de trabalho"""
        if vaga.modalidade == 'remoto':
            return cls.PESO_MODALIDADE, 'Trabalho remoto - compatível com todos'

        if vaga.modalidade == 'hibrido':
            return cls.PESO_MODALIDADE * 0.7, 'Trabalho híbrido'

        if vaga.acessivel:
            return cls.PESO_MODALIDADE * 0.8, 'Vaga presencial acessível'
        else:
            return cls.PESO_MODALIDADE * 0.3, 'Vaga presencial - verificar acessibilidade'

    @classmethod
    def _match_perfil(cls, pcd_profile):
        """Verifica completude do perfil do PCD"""
        try:
            perfil_ext = pcd_profile.perfil_extendido
            completude = perfil_ext.percentual_completude

            score = (completude / 100) * cls.PESO_PERFIL

            if completude >= 90:
                return score, 'Perfil muito completo'
            elif completude >= 70:
                return score, 'Perfil completo'
            elif completude >= 50:
                return score, 'Perfil parcialmente completo'
            else:
                return score, 'Complete seu perfil para mais matches'

        except:
            return 0, 'Perfil não encontrado'

    @classmethod
    def _match_status(cls, pcd_profile):
        """Verifica status médico do PCD"""
        try:
            perfil_ext = pcd_profile.perfil_extendido
            status = perfil_ext.status_medico

            status_scores = {
                'enquadravel': cls.PESO_STATUS,
                'sugestivo': cls.PESO_STATUS * 0.7,
                'avaliacao_adicional': cls.PESO_STATUS * 0.3,
                'necessita_laudo': cls.PESO_STATUS * 0.2,
                'pendente': cls.PESO_STATUS * 0.5,
                'nao_enquadravel': 0
            }

            score = status_scores.get(status, 0)

            status_msgs = {
                'enquadravel': 'Status médico: ✅ Enquadrável',
                'sugestivo': 'Status médico: ⚠️ Sugestivo',
                'avaliacao_adicional': 'Status médico: 🩺 Necessita Avaliação Adicional',
                'necessita_laudo': 'Status médico: 📄 Necessita Laudo Atualizado',
                'pendente': 'Status médico: ⏳ Pendente',
                'nao_enquadravel': 'Status médico: 🚫 Não Enquadrável'
            }

            return score, status_msgs.get(status, 'Status desconhecido')

        except:
            return cls.PESO_STATUS * 0.5, 'Status médico pendente'

    @classmethod
    def _classificar_match(cls, score):
        """Classifica o match em níveis"""
        if score >= 80:
            return 'Excelente'
        elif score >= 60:
            return 'Muito Bom'
        elif score >= 40:
            return 'Bom'
        elif score >= 20:
            return 'Regular'
        else:
            return 'Baixo'

    @classmethod
    def buscar_vagas_compativeis(cls, pcd_profile, min_score=30, limit=20):
        """Busca vagas compatíveis com um PCD"""
        vagas = Vaga.objects.filter(status='ativa').select_related('empresa')

        matches = []
        for vaga in vagas:
            match_result = cls.calcular_match(pcd_profile, vaga)

            if match_result['score'] >= min_score:
                matches.append({
                    'vaga': vaga,
                    'score': match_result['score'],
                    'nivel': match_result['nivel'],
                    'detalhes': match_result['detalhes']
                })

        matches.sort(key=lambda x: x['score'], reverse=True)
        return matches[:limit]

    @classmethod
    def buscar_candidatos_compativeis(cls, vaga, min_score=30, limit=20):
        """Busca PCDs compatíveis com uma vaga"""
        pcds = PCDProfile.objects.filter(
            user__is_active=True
        ).select_related('user', 'perfil_extendido')

        matches = []
        for pcd in pcds:
            match_result = cls.calcular_match(pcd, vaga)

            if match_result['score'] >= min_score:
                matches.append({
                    'pcd': pcd,
                    'score': match_result['score'],
                    'nivel': match_result['nivel'],
                    'detalhes': match_result['detalhes']
                })

        matches.sort(key=lambda x: x['score'], reverse=True)
        return matches[:limit]

    @classmethod
    def notificar_matches_novos(cls, vaga):
        """Notifica PCDs sobre uma nova vaga compatível"""
        from userpcd.models import Notificacao

        matches = cls.buscar_candidatos_compativeis(vaga, min_score=50, limit=10)

        notificacoes_criadas = 0
        for match in matches:
            pcd = match['pcd']
            score = match['score']
            nivel = match['nivel']

            if score >= 50:
                Notificacao.objects.create(
                    user=pcd.user,
                    tipo='sistema',
                    titulo=f'Nova vaga compatível! Match {nivel} ({score}%)',
                    mensagem=f'A vaga "{vaga.titulo}" da empresa {vaga.empresa.razao_social} tem {nivel.lower()} compatibilidade com seu perfil. Confira!'
                )
                notificacoes_criadas += 1

        return notificacoes_criadas


# Funções auxiliares
def get_vagas_recomendadas(pcd_profile, limit=10):
    """Retorna vagas recomendadas para um PCD"""
    return MatchingEngine.buscar_vagas_compativeis(pcd_profile, min_score=30, limit=limit)


def get_candidatos_recomendados(vaga, limit=10):
    """Retorna candidatos recomendados para uma vaga"""
    return MatchingEngine.buscar_candidatos_compativeis(vaga, min_score=30, limit=limit)


def calcular_compatibilidade(pcd_profile, vaga):
    """Calcula compatibilidade entre PCD e vaga"""
    return MatchingEngine.calcular_match(pcd_profile, vaga)


def executar_matching_diario():
    """
    Executa matching diário entre PCDs enquadráveis e vagas aprovadas.
    Envia notificações para PCDs sobre vagas compatíveis.

    Returns:
        dict: Estatísticas do matching executado
    """
    from userpcd.models import PerfilPCDExtendido, Notificacao
    from usercompany.models import VagaExtendida
    from datetime import datetime, timedelta

    # Buscar vagas ativas e aprovadas pelo médico
    vagas_aprovadas = VagaExtendida.objects.filter(
        status_medico='aprovada',
        vaga__status='ativa'
    ).select_related('vaga', 'vaga__empresa')

    # Buscar PCDs enquadráveis ou sugestivos
    pcds_elegiveis = PerfilPCDExtendido.objects.filter(
        status_medico__in=['enquadravel', 'sugestivo'],
        pcd_profile__user__is_active=True
    ).select_related('pcd_profile', 'pcd_profile__user')

    total_vagas = vagas_aprovadas.count()
    total_pcds = pcds_elegiveis.count()
    matches_encontrados = 0
    notificacoes_enviadas = 0

    # Para cada vaga aprovada, encontrar PCDs compatíveis
    for vaga_ext in vagas_aprovadas:
        vaga = vaga_ext.vaga

        # Buscar candidatos compatíveis (score >= 50)
        matches = MatchingEngine.buscar_candidatos_compativeis(vaga, min_score=50, limit=20)

        matches_encontrados += len(matches)

        # Enviar notificação para PCDs compatíveis (apenas se não foram notificados recentemente)
        for match in matches:
            pcd = match['pcd']
            score = match['score']
            nivel = match['nivel']

            # Verificar se já foi notificado sobre esta vaga nas últimas 7 dias
            ultima_notificacao = Notificacao.objects.filter(
                user=pcd.user,
                tipo='sistema',
                titulo__contains=vaga.titulo,
                criada_em__gte=datetime.now() - timedelta(days=7)
            ).exists()

            if not ultima_notificacao:
                Notificacao.objects.create(
                    user=pcd.user,
                    tipo='sistema',
                    titulo=f'🎯 Nova vaga compatível! Match {nivel} ({score}%)',
                    mensagem=f'A vaga "{vaga.titulo}" da empresa {vaga.empresa.razao_social} '
                            f'tem {nivel.lower()} compatibilidade com seu perfil.\n\n'
                            f'📍 Localização: {vaga.cidade}/{vaga.uf}\n'
                            f'💼 Modalidade: {vaga.get_modalidade_display()}\n\n'
                            f'Acesse seu dashboard para ver mais detalhes e se candidatar!'
                )
                notificacoes_enviadas += 1

    return {
        'total_vagas_processadas': total_vagas,
        'total_pcds_elegiveis': total_pcds,
        'matches_encontrados': matches_encontrados,
        'notificacoes_enviadas': notificacoes_enviadas,
        'executado_em': datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    }
