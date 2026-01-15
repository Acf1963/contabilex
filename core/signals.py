"""
Signals para gerar lançamentos contabilísticos automaticamente
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Fatura, Compra, Despesa, LancamentoDiario, MovimentoRazao, Conta, Classe
from decimal import Decimal

def obter_ou_criar_conta(codigo, descricao, classe_id):
    """Auxiliar para garantir que as contas necessárias existem"""
    try:
        # Tenta buscar a classe, se não existir cria uma genérica (melhor que falhar)
        classe, _ = Classe.objects.get_or_create(
            codigo=str(classe_id), 
            defaults={'descricao': f'Classe {classe_id}'}
        )
        conta, _ = Conta.objects.get_or_create(
            codigo=codigo,
            defaults={
                'descricao': descricao,
                'classe': classe,
                'aceita_lancamentos': True
            }
        )
        return conta
    except Exception:
        return None

@receiver(post_save, sender=Fatura)
def criar_lancamento_fatura(sender, instance, created, **kwargs):
    """
    Cria lançamento contabilístico quando uma fatura é emitida ou paga
    Débito: Clientes (31) 
    Crédito: Vendas (71) -> Subtotal
    Crédito: IVA Liquidado (34.5) -> Impostos
    """
    # Só processa se estiver EMITIDA ou PAGA e não tiver lançamento ainda
    if instance.estado in ['EMITIDA', 'PAGA'] and not instance.lancamentos.exists():
        conta_clientes = obter_ou_criar_conta('31', 'Clientes', 3)
        conta_vendas = obter_ou_criar_conta('71', 'Vendas de Mercadorias', 7)
        conta_iva = obter_ou_criar_conta('34.5', 'IVA - Imposto Liquidado', 3)
        
        if not all([conta_clientes, conta_vendas]):
            return

        lancamento = LancamentoDiario.objects.create(
            descricao=f"Facturação: {instance.numero} - {instance.cliente.nome}",
            data=instance.data_emissao,
            fatura=instance
        )
        
        # Débito em Clientes (Valor Total)
        MovimentoRazao.objects.create(
            lancamento=lancamento, conta=conta_clientes, tipo='D', valor=instance.total
        )
        
        # Crédito em Vendas (Subtotal)
        MovimentoRazao.objects.create(
            lancamento=lancamento, conta=conta_vendas, tipo='C', valor=instance.subtotal
        )
        
        # Crédito em IVA (Se houver)
        if instance.total_imposto > 0 and conta_iva:
            MovimentoRazao.objects.create(
                lancamento=lancamento, conta=conta_iva, tipo='C', valor=instance.total_imposto
            )

@receiver(post_save, sender=Compra)
def criar_lancamento_compra(sender, instance, created, **kwargs):
    """
    Cria lançamento contabilístico para compras
    Débito: Compras (21) ou FSE (61) -> Subtotal
    Débito: IVA Dedutível (34.1) -> Impostos
    Crédito: Fornecedores (32) -> Total
    """
    if instance.estado in ['REGISTADA', 'PAGA'] and not instance.lancamentos.exists():
        conta_fornecedores = obter_ou_criar_conta('32', 'Fornecedores', 3)
        conta_compras = obter_ou_criar_conta('21', 'Compras de Mercadorias', 2)
        conta_iva = obter_ou_criar_conta('34.1', 'IVA - Imposto Dedutível', 3)
        
        if not all([conta_fornecedores, conta_compras]):
            return

        lancamento = LancamentoDiario.objects.create(
            descricao=f"Compra: {instance.numero} - {instance.fornecedor.nome}",
            data=instance.data_emissao,
            compra=instance
        )
        
        # Débito em Compras (Subtotal)
        MovimentoRazao.objects.create(
            lancamento=lancamento, conta=conta_compras, tipo='D', valor=instance.subtotal
        )
        
        # Débito em IVA (Se houver)
        if instance.total_imposto > 0 and conta_iva:
            MovimentoRazao.objects.create(
                lancamento=lancamento, conta=conta_iva, tipo='D', valor=instance.total_imposto
            )
            
        # Crédito em Fornecedores (Total)
        MovimentoRazao.objects.create(
            lancamento=lancamento, conta=conta_fornecedores, tipo='C', valor=instance.total
        )

@receiver(post_save, sender=Despesa)
def criar_lancamento_despesa(sender, instance, created, **kwargs):
    """
    Cria lançamento contabilístico para despesas simples
    """
    if created and not instance.lancamentos.exists():
        conta_fse = obter_ou_criar_conta('61', 'Fornecimentos e Serviços Externos', 6)
        
        # Se tem fornecedor, vai para a conta 32, senão vai para Caixa 45
        if instance.fornecedor:
            conta_contrapartida = obter_ou_criar_conta('32', 'Fornecedores', 3)
        else:
            conta_contrapartida = obter_ou_criar_conta('45', 'Caixa', 4)
            
        if not all([conta_fse, conta_contrapartida]):
            return

        lancamento = LancamentoDiario.objects.create(
            descricao=f"Despesa: {instance.numero} - {instance.descricao}",
            data=instance.data,
            despesa=instance
        )
        
        # Simplificado para despesas: assumimos que o valor é o custo total
        MovimentoRazao.objects.create(
            lancamento=lancamento, conta=conta_fse, tipo='D', valor=instance.valor
        )
        
        MovimentoRazao.objects.create(
            lancamento=lancamento, conta=conta_contrapartida, tipo='C', valor=instance.valor
        )
