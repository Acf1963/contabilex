from django.core.management.base import BaseCommand
from core.models import Classe, Conta

class Command(BaseCommand):
    help = 'Popula o PGC de Angola com contas essenciais para relatórios'

    def handle(self, *args, **kwargs):
        # Classes do PGC Angola
        classes_data = [
            ('1', 'Disponibilidades'),
            ('2', 'Existências'),
            ('3', 'Terceiros'),
            ('4', 'Imobilizações'),
            ('5', 'Capital, Reservas e Resultados Transitados'),
            ('6', 'Custos e Perdas'),
            ('7', 'Proveitos e Ganhos'),
            ('8', 'Resultados'),
        ]
        
        for codigo, descricao in classes_data:
            Classe.objects.get_or_create(codigo=codigo, defaults={'descricao': descricao})
            self.stdout.write(self.style.SUCCESS(f'Classe {codigo} - {descricao}'))
        
        # Contas essenciais com hierarquia Razão -> Integração -> Movimento
        contas_data = [
            # Código, Descrição, Classe, Pai, Aceita Lanc., Tipo, Entidade
            
            # Classe 1 - Disponibilidades
            ('11', 'Caixa', 1, None, False, 'RAZAO', 'CAIXA'),
            ('11.1', 'Caixa Geral', 1, '11', True, 'MOVIMENTO', 'CAIXA'),
            ('12', 'Bancos', 1, None, False, 'RAZAO', 'BANCO'),
            ('12.1', 'Depósitos à Ordem', 1, '12', True, 'MOVIMENTO', 'BANCO'),
            
            # Classe 2 - Existências
            ('21', 'Compras', 2, None, False, 'RAZAO', 'NENHUM'),
            ('21.1', 'Compras de Mercadorias', 2, '21', True, 'MOVIMENTO', 'NENHUM'),
            ('22', 'Matérias-Primas, Auxiliares e Materiais', 2, None, True, 'MOVIMENTO', 'NENHUM'),
            
            # Classe 3 - Terceiros
            ('31', 'Clientes', 3, None, False, 'RAZAO', 'CLIENTE'),
            ('31.1', 'Clientes c/c', 3, '31', False, 'INTEGRACAO', 'CLIENTE'),
            ('31.1.1', 'Clientes Gerais', 3, '31.1', True, 'MOVIMENTO', 'CLIENTE'),
            
            ('32', 'Fornecedores', 3, None, False, 'RAZAO', 'FORNECEDOR'),
            ('32.1', 'Fornecedores c/c', 3, '32', False, 'INTEGRACAO', 'FORNECEDOR'),
            ('32.1.1', 'Fornecedores Gerais', 3, '32.1', True, 'MOVIMENTO', 'FORNECEDOR'),
            
            ('34', 'Estado', 3, None, False, 'RAZAO', 'ESTADO'),
            ('34.1', 'Imposto sobre o Rendimento', 3, '34', False, 'INTEGRACAO', 'ESTADO'),
            ('34.1.1', 'I.R.T', 3, '34.1', True, 'MOVIMENTO', 'ESTADO'),
            ('34.3', 'IVA', 3, '34', False, 'INTEGRACAO', 'ESTADO'),
            ('34.3.1', 'IVA Liquidado', 3, '34.3', True, 'MOVIMENTO', 'ESTADO'),
            ('34.3.2', 'IVA Dedutível', 3, '34.3', True, 'MOVIMENTO', 'ESTADO'),

            # Classe 6 - Custos
            ('61', 'Custo das Existências Vendidas', 6, None, True, 'MOVIMENTO', 'NENHUM'),
            ('62', 'F.S.E.', 6, None, False, 'RAZAO', 'NENHUM'),
            ('62.1', 'Comunicações', 6, '62', True, 'MOVIMENTO', 'NENHUM'),
            ('62.2', 'Energia e Água', 6, '62', True, 'MOVIMENTO', 'NENHUM'),
            ('63', 'Impostos e Taxas', 6, None, True, 'MOVIMENTO', 'NENHUM'),
            ('64', 'Gastos com Pessoal', 6, None, False, 'RAZAO', 'NENHUM'),
            ('64.1', 'Remunerações', 6, '64', True, 'MOVIMENTO', 'NENHUM'),
            
            # Classe 7 - Proveitos
            ('71', 'Vendas', 7, None, True, 'MOVIMENTO', 'NENHUM'),
            ('72', 'Prestações de Serviços', 7, None, True, 'MOVIMENTO', 'NENHUM'),
            
            # Classe 8 - Resultados
            ('88', 'Resultado Líquido', 8, None, True, 'MOVIMENTO', 'NENHUM'),
        ]
        
        for codigo, descricao, classe_id, conta_pai_codigo, aceita_lancamentos, tipo, tipo_entidade in contas_data:
            classe = Classe.objects.get(codigo=str(classe_id))
            conta_pai = None
            if conta_pai_codigo:
                # Buscar conta pai apenas no plano global
                conta_pai = Conta.objects.filter(codigo=conta_pai_codigo, empresa__isnull=True).first()
            
            Conta.objects.update_or_create(
                codigo=codigo,
                empresa__isnull=True, # Garantir que operamos apenas no plano mestre
                defaults={
                    'descricao': descricao,
                    'classe': classe,
                    'conta_pai': conta_pai,
                    'aceita_lancamentos': aceita_lancamentos,
                    'tipo': tipo,
                    'tipo_entidade': tipo_entidade
                }
            )
            self.stdout.write(self.style.SUCCESS(f'Conta {codigo} - {descricao}'))
        
        self.stdout.write(self.style.SUCCESS('\n✅ PGC populado com sucesso!'))
