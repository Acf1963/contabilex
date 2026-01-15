from django.core.management.base import BaseCommand
from core.models import Classe, Conta

class Command(BaseCommand):
    help = 'Popula o Plano Geral de Contabilidade (Simplificado para Angola)'

    def handle(self, *args, **kwargs):
        self.stdout.write('Iniciando populacao do PGC...')

        # Classe 3
        c3, _ = Classe.objects.get_or_create(codigo='3', descricao='Terceiros')
        
        # 31 Clientes
        conta31, _ = Conta.objects.get_or_create(
            codigo='31', 
            defaults={'descricao': 'Clientes', 'classe': c3, 'aceita_lancamentos': False}
        )
        
        # 32 Fornecedores
        conta32, _ = Conta.objects.get_or_create(
            codigo='32', 
            defaults={'descricao': 'Fornecedores', 'classe': c3, 'aceita_lancamentos': False}
        )

        # Classe 4
        c4, _ = Classe.objects.get_or_create(codigo='4', descricao='Meios Monetários')
        
        # 45 Caixa
        conta45, _ = Conta.objects.get_or_create(
            codigo='45', 
            defaults={'descricao': 'Caixa', 'classe': c4, 'aceita_lancamentos': True}
        )

        self.stdout.write(self.style.SUCCESS('PGC populado com sucesso!'))
