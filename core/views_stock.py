from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Sum, F, Q
from django.utils import timezone
from .models import Produto, Inventario, LinhaInventario, MovimentoStock, LancamentoDiario, MovimentoRazao, Conta
from .forms_stock import ProdutoForm, InventarioForm, LinhaInventarioForm, MovimentoStockForm
from decimal import Decimal

# ============================================
# PRODUTOS
# ============================================

def produtos_list(request):
    """Lista de produtos"""
    empresa = request.empresa
    produtos = empresa.produtos.all()
    
    # Filtros
    search = request.GET.get('search', '')
    tipo = request.GET.get('tipo', '')
    alerta = request.GET.get('alerta', '')
    
    if search:
        produtos = produtos.filter(Q(codigo__icontains=search) | Q(nome__icontains=search))
    if tipo:
        produtos = produtos.filter(tipo=tipo)
    if alerta == 'sim':
        produtos = [p for p in produtos if p.alerta_stock]
    
    # Estatísticas
    total_produtos = produtos.count()
    valor_total_stock = sum(p.valor_stock for p in produtos)
    produtos_alerta = len([p for p in produtos if p.alerta_stock])
    
    context = {
        'produtos': produtos,
        'total_produtos': total_produtos,
        'valor_total_stock': valor_total_stock,
        'produtos_alerta': produtos_alerta,
        'form': ProdutoForm(empresa=empresa) if request.method != 'POST' else None,
    }
    
    if request.method == 'POST':
        form = ProdutoForm(request.POST, empresa=empresa)
        if form.is_valid():
            produto = form.save(commit=False)
            produto.empresa = empresa
            produto.save()
            messages.success(request, f'Produto {produto.codigo} criado com sucesso!')
            return redirect('produtos_list')
        else:
            context['form'] = form
    
    return render(request, 'stock/produtos_lista.html', context)

def editar_produto(request, pk):
    """Editar produto"""
    produto = get_object_or_404(Produto, pk=pk, empresa=request.empresa)
    
    if request.method == 'POST':
        form = ProdutoForm(request.POST, instance=produto, empresa=request.empresa)
        if form.is_valid():
            form.save()
            messages.success(request, f'Produto {produto.codigo} atualizado!')
            return redirect('produtos_list')
    else:
        form = ProdutoForm(instance=produto, empresa=request.empresa)
    
    return render(request, 'stock/produto_editar.html', {'form': form, 'produto': produto})

def produto_detalhe(request, pk):
    """Detalhes do produto com histórico de movimentos"""
    produto = get_object_or_404(Produto, pk=pk, empresa=request.empresa)
    movimentos = produto.movimentos.all()[:50]
    
    context = {
        'produto': produto,
        'movimentos': movimentos,
    }
    return render(request, 'stock/produto_detalhe.html', context)

# ============================================
# MOVIMENTOS DE STOCK
# ============================================

def movimentos_stock_list(request):
    """Lista de movimentos de stock"""
    empresa = request.empresa
    movimentos = empresa.movimentos_stock.select_related('produto').all()[:100]
    
    context = {
        'movimentos': movimentos,
        'form': MovimentoStockForm(empresa=empresa) if request.method != 'POST' else None,
    }
    
    if request.method == 'POST':
        form = MovimentoStockForm(request.POST, empresa=empresa)
        if form.is_valid():
            movimento = form.save(commit=False)
            movimento.empresa = empresa
            movimento.usuario = request.user.username if hasattr(request, 'user') else 'Sistema'
            movimento.save()
            
            # Atualizar stock do produto
            produto = movimento.produto
            if movimento.tipo == 'ENTRADA':
                produto.stock_atual += movimento.quantidade
            elif movimento.tipo == 'SAIDA':
                produto.stock_atual -= movimento.quantidade
            elif movimento.tipo == 'AJUSTE':
                # Ajuste direto
                produto.stock_atual = movimento.quantidade
            produto.save()
            
            messages.success(request, f'Movimento registado! Stock atual: {produto.stock_atual} {produto.unidade}')
            return redirect('movimentos_stock_list')
        else:
            context['form'] = form
    
    return render(request, 'stock/movimentos_lista.html', context)

# ============================================
# INVENTÁRIOS
# ============================================

def inventarios_list(request):
    """Lista de inventários"""
    empresa = request.empresa
    inventarios = empresa.inventarios.all()
    
    context = {
        'inventarios': inventarios,
        'form': InventarioForm() if request.method != 'POST' else None,
    }
    
    if request.method == 'POST':
        form = InventarioForm(request.POST)
        if form.is_valid():
            inventario = form.save(commit=False)
            inventario.empresa = empresa
            inventario.save()
            
            # Criar linhas para todos os produtos ativos
            produtos = empresa.produtos.filter(ativo=True)
            for produto in produtos:
                LinhaInventario.objects.create(
                    inventario=inventario,
                    produto=produto,
                    stock_sistema=produto.stock_atual,
                    preco_custo=produto.preco_custo
                )
            
            messages.success(request, f'Inventário {inventario.numero} criado com {produtos.count()} produtos!')
            return redirect('inventario_detalhe', pk=inventario.pk)
        else:
            context['form'] = form
    
    return render(request, 'stock/inventarios_lista.html', context)

def inventario_detalhe(request, pk):
    """Detalhes do inventário com contagem"""
    inventario = get_object_or_404(Inventario, pk=pk, empresa=request.empresa)
    linhas = inventario.linhas.select_related('produto').all()
    
    # Calcular totais
    total_diferenca_valor = sum(linha.valor_diferenca for linha in linhas)
    linhas_com_diferenca = [l for l in linhas if l.diferenca != 0]
    
    context = {
        'inventario': inventario,
        'linhas': linhas,
        'total_diferenca_valor': total_diferenca_valor,
        'linhas_com_diferenca': len(linhas_com_diferenca),
    }
    
    return render(request, 'stock/inventario_detalhe.html', context)

def atualizar_contagem(request, inventario_pk, linha_pk):
    """Atualizar contagem de uma linha de inventário"""
    linha = get_object_or_404(LinhaInventario, pk=linha_pk, inventario__pk=inventario_pk, inventario__empresa=request.empresa)
    
    if request.method == 'POST':
        stock_contado = request.POST.get('stock_contado')
        observacoes = request.POST.get('observacoes', '')
        
        try:
            linha.stock_contado = Decimal(stock_contado)
            linha.observacoes = observacoes
            linha.save()
            messages.success(request, f'Contagem atualizada para {linha.produto.codigo}')
        except:
            messages.error(request, 'Valor inválido')
    
    return redirect('inventario_detalhe', pk=inventario_pk)

def finalizar_inventario(request, pk):
    """Finalizar inventário e ajustar stocks"""
    inventario = get_object_or_404(Inventario, pk=pk, empresa=request.empresa)
    
    if inventario.estado != 'EM_CURSO':
        messages.warning(request, 'Este inventário já foi finalizado ou cancelado.')
        return redirect('inventario_detalhe', pk=pk)
    
    if request.method == 'POST':
        linhas_com_diferenca = [l for l in inventario.linhas.all() if l.diferenca != 0]
        
        for linha in linhas_com_diferenca:
            # Criar movimento de ajuste
            MovimentoStock.objects.create(
                empresa=request.empresa,
                produto=linha.produto,
                tipo='INVENTARIO',
                origem='INVENTARIO',
                data=inventario.data,
                quantidade=abs(linha.diferenca),
                preco_unitario=linha.preco_custo,
                inventario=inventario,
                observacoes=f'Ajuste de inventário {inventario.numero}',
                usuario=request.user.username if hasattr(request, 'user') else 'Sistema'
            )
            
            # Atualizar stock do produto
            linha.produto.stock_atual = linha.stock_contado
            linha.produto.save()
        
        # Marcar inventário como finalizado
        inventario.estado = 'FINALIZADO'
        inventario.finalizado_em = timezone.now()
        inventario.save()
        
        messages.success(request, f'Inventário finalizado! {len(linhas_com_diferenca)} produtos ajustados.')
        return redirect('inventario_detalhe', pk=pk)
    
    return redirect('inventario_detalhe', pk=pk)
