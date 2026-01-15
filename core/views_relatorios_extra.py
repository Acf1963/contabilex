from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Sum, Q 
from .models import Compra, Fatura, Empresa, LancamentoDiario, MovimentoRazao, Conta
from django.utils import timezone
from django.contrib import messages
from .utils_pdf_retencao import gerar_pdf_retencoes

def liquidar_retencao_compra(request, pk):
    """Marca a retenção de uma compra como paga ao Estado e gera lançamento"""
    compra = get_object_or_404(Compra, pk=pk, empresa=request.empresa)
    
    if request.method == 'POST' and not compra.retencao_paga:
        compra.retencao_paga = True
        compra.save()
        
        # Gerar Lançamento Contabilístico
        # Débito: 34.1 (Estado - Retenção a Pagar)
        # Crédito: 43/45 (Banco/Caixa)
        try:
            # Tenta encontrar conta do Estado
            conta_estado = Conta.objects.filter(codigo='34.1', empresa=compra.empresa).first() or \
                           Conta.objects.filter(codigo__startswith='34', empresa=compra.empresa).first()
            
            # Tenta encontrar conta de Banco (default 43.1 ou primeira 43) ou Caixa
            conta_pagamento = Conta.objects.filter(codigo__startswith='43', empresa=compra.empresa).first() or \
                              Conta.objects.filter(codigo__startswith='45', empresa=compra.empresa).first()

            if conta_estado and conta_pagamento:
                lancamento = LancamentoDiario.objects.create(
                    empresa=compra.empresa,
                    data=timezone.now().date(),
                    descricao=f"Pagamento Retenção Compra {compra.numero}",
                    compra=compra
                )
                
                # Débito (Liquida Dívida Estado)
                MovimentoRazao.objects.create(lancamento=lancamento, conta=conta_estado, tipo='D', valor=compra.valor_retencao)
                
                # Crédito (Sai Dinheiro)
                MovimentoRazao.objects.create(lancamento=lancamento, conta=conta_pagamento, tipo='C', valor=compra.valor_retencao)
                
                messages.success(request, f'Retenção da compra {compra.numero} liquidada e contabilizada.')
            else:
                messages.warning(request, f'Retenção marcada como paga, mas contas 34.1 ou 43 não encontradas para lançamento automático.')
                
        except Exception as e:
            messages.error(request, f'Erro ao gerar lançamento: {str(e)}')
            
    return redirect('relatorio_retencoes')

def confirmar_dar_venda(request, pk):
    """Marca o DAR de uma venda como recebido (Recuperado) e gera lançamento"""
    fatura = get_object_or_404(Fatura, pk=pk, empresa=request.empresa)
    
    if request.method == 'POST' and not fatura.retencao_paga:
        fatura.retencao_paga = True
        fatura.save()
        
        # Gerar Lançamento Contabilístico
        # "Troca" de dívida do cliente por direito sobre o Estado
        # Débito: 34.2 (Estado - Imposto a Recuperar)
        # Crédito: 31.8 (Cliente - Retenção Pendente) -> A conta que debitamos na emissão
        try:
            conta_recuperar = Conta.objects.filter(codigo='34.2', empresa=fatura.empresa).first() or \
                              Conta.objects.filter(codigo__startswith='34', empresa=fatura.empresa).first()
            
            conta_cliente_ret = Conta.objects.filter(codigo='31.8', empresa=fatura.empresa).first() or \
                                Conta.objects.filter(codigo__startswith='34', empresa=fatura.empresa).first()

            if conta_recuperar and conta_cliente_ret:
                lancamento = LancamentoDiario.objects.create(
                    empresa=fatura.empresa,
                    data=timezone.now().date(),
                    descricao=f"Recebimento DAR Fatura {fatura.numero}",
                    fatura=fatura
                )
                
                # Débito (Ativo Estado)
                MovimentoRazao.objects.create(lancamento=lancamento, conta=conta_recuperar, tipo='D', valor=fatura.valor_retencao)
                
                # Crédito (Fecha pendente cliente)
                MovimentoRazao.objects.create(lancamento=lancamento, conta=conta_cliente_ret, tipo='C', valor=fatura.valor_retencao)
                
                messages.success(request, f'DAR da fatura {fatura.numero} confirmado e contabilizado.')
            else:
                messages.warning(request, f'DAR confirmado, mas contas não encontradas para lançamento.')

        except Exception as e:
            messages.error(request, f'Erro ao gerar lançamento: {str(e)}')

    return redirect('relatorio_retencoes')

def relatorio_retencoes(request):
    empresa = request.empresa
    
    # Filtros de data
    mes = request.GET.get('mes')
    ano = request.GET.get('ano')
    
    if not mes or not ano:
        hoje = timezone.now()
        mes = hoje.month
        ano = hoje.year
    else:
        mes = int(mes)
        ano = int(ano)

    # 1. Retenções a Pagar (Compras)
    # Filtra compras REGISTADAS ou PAGAS que tenham retenção > 0
    compras_com_retencao = Compra.objects.filter(
        empresa=empresa,
        aplicar_retencao=True,
        valor_retencao__gt=0,
        data_emissao__month=mes,
        data_emissao__year=ano
    ).exclude(estado='RASCUNHO')
    
    total_retencao_pagar = compras_com_retencao.aggregate(total=Sum('valor_retencao'))['total'] or 0

    # 2. Retenções a Recuperar (Vendas)
    # Filtra faturas EMITIDAS ou PAGAS que tenham retenção > 0
    vendas_com_retencao = Fatura.objects.filter(
        empresa=empresa,
        aplicar_retencao=True,
        valor_retencao__gt=0,
        data_emissao__month=mes,
        data_emissao__year=ano
    ).exclude(estado='RASCUNHO')
    
    total_retencao_recuperar = vendas_com_retencao.aggregate(total=Sum('valor_retencao'))['total'] or 0
    
    context = {
        'compras': compras_com_retencao,
        'vendas': vendas_com_retencao,
        'total_pagar': total_retencao_pagar,
        'total_recuperar': total_retencao_recuperar,
        'mes': mes,
        'ano': ano,
        'meses': range(1, 13),
        'anos': range(ano - 2, ano + 2)
    }
    
    if request.GET.get('pdf') == 'true':
        return gerar_pdf_retencoes(context, empresa)
        
    return render(request, 'relatorio_retencoes.html', context)
