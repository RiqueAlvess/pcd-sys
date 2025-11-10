"""
Management command para executar matching automático entre PCDs e Vagas
Pode ser executado diariamente via cron job ou scheduler
"""

from django.core.management.base import BaseCommand
from userpcd.matching import executar_matching_diario


class Command(BaseCommand):
    help = 'Executa matching automático entre PCDs enquadráveis e vagas aprovadas'

    def add_arguments(self, parser):
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Mostra informações detalhadas da execução',
        )

    def handle(self, *args, **options):
        verbose = options.get('verbose', False)

        self.stdout.write(self.style.SUCCESS('🚀 Iniciando matching automático...'))
        self.stdout.write('')

        try:
            # Executar matching
            resultado = executar_matching_diario()

            # Exibir estatísticas
            self.stdout.write(self.style.SUCCESS('✅ Matching executado com sucesso!'))
            self.stdout.write('')
            self.stdout.write('📊 Estatísticas:')
            self.stdout.write(f'  - Vagas processadas: {resultado["total_vagas_processadas"]}')
            self.stdout.write(f'  - PCDs elegíveis: {resultado["total_pcds_elegiveis"]}')
            self.stdout.write(f'  - Matches encontrados: {resultado["matches_encontrados"]}')
            self.stdout.write(f'  - Notificações enviadas: {resultado["notificacoes_enviadas"]}')
            self.stdout.write(f'  - Executado em: {resultado["executado_em"]}')
            self.stdout.write('')

            if verbose:
                self.stdout.write(self.style.WARNING('💡 Dicas:'))
                self.stdout.write('  - PCDs com status "Enquadrável" ou "Sugestivo" são considerados')
                self.stdout.write('  - Apenas vagas com status "Aprovada" pelo médico são processadas')
                self.stdout.write('  - Notificações não são reenviadas se já foram enviadas nos últimos 7 dias')
                self.stdout.write('  - Score mínimo para notificação: 50/100')
                self.stdout.write('')

            # Mensagem de configuração do cron
            self.stdout.write(self.style.SUCCESS('📅 Para executar diariamente, adicione ao crontab:'))
            self.stdout.write('   0 8 * * * cd /path/to/project && python manage.py executar_matching')
            self.stdout.write('')

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Erro ao executar matching: {str(e)}'))
            raise
