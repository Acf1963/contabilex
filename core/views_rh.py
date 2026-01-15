from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from .models import Funcionario, ProcessamentoSalarial, Empresa, LancamentoDiario, MovimentoRazao, Conta
from .forms import FuncionarioForm, ProcessamentoVariaveisForm
from .utils_rh import calcular_salario
from django.db.models import Sum

def funcionarios_list(request):
    empresa = request.empresa
    if not empresa:
        return redirect('configuracao_empresa')
        
    funcionarios = Funcionario.objects.filter(empresa=empresa)
    if request.method == 'POST':
        form = FuncionarioForm(request.POST)
        if form.is_valid():
            funcionario = form.save(commit=False)
            funcionario.empresa = empresa
            funcionario.save()
            messages.success(request, 'Funcionário cadastrado com sucesso!')
            return redirect('funcionarios_list')
    else:
        form = FuncionarioForm()
    
    return render(request, 'rh/funcionarios_lista.html', {
        'funcionarios': funcionarios,
        'form': form
    })

def editar_funcionario(request, pk):
    empresa = request.empresa
    funcionario = get_object_or_404(Funcionario, pk=pk, empresa=empresa)
    if request.method == 'POST':
        form = FuncionarioForm(request.POST, instance=funcionario)
        if form.is_valid():
            form.save()
            messages.success(request, 'Dados do funcionário atualizados!')
            return redirect('funcionarios_list')
    else:
        form = FuncionarioForm(instance=funcionario)
    return render(request, 'rh/funcionario_form.html', {'form': form, 'funcionario': funcionario})

def processamento_rh(request):
    empresa = request.empresa
    if not empresa:
        return redirect('configuracao_empresa')
        
    hoje = timezone.now().date()
    mes_atual = hoje.month
    ano_atual = hoje.year
    
    mes = int(request.GET.get('mes', mes_atual))
    ano = int(request.GET.get('ano', ano_atual))
    
    processamentos = ProcessamentoSalarial.objects.filter(
        funcionario__empresa=empresa, 
        mes=mes, 
        ano=ano
    ).order_by('funcionario__nome')
    
    if request.method == 'POST' and 'processar' in request.POST:
        # Processa salários para todos os funcionários ativos
        funcionarios = Funcionario.objects.filter(empresa=empresa, ativo=True)
        count = 0
        for f in funcionarios:
            res = calcular_salario(f, mes, ano)
            proc, created = ProcessamentoSalarial.objects.update_or_create(
                funcionario=f, mes=mes, ano=ano,
                defaults={
                    'salario_base': res['salario_base'],
                    'subsidio_alimentacao': res['subsidio_alimentacao'],
                    'subsidio_transporte': res['subsidio_transporte'],
                    'outros_abonos': res['outros_abonos'],
                    'total_bruto': res['total_bruto'],
                    'inss_funcionario': res['inss_funcionario'],
                    'inss_empresa': res['inss_empresa'],
                    'irt': res['irt'],
                    'total_descontos': res['total_descontos'],
                    'salario_liquido': res['salario_liquido'],
                }
            )
            count += 1
        messages.success(request, f'Processamento concluído para {count} funcionários ({mes}/{ano}).')
        return redirect(f'/rh/processamento/?mes={mes}&ano={ano}')

    return render(request, 'rh/processamento.html', {
        'processamentos': processamentos,
        'mes_selecionado': mes,
        'ano_selecionado': ano,
        'meses': range(1, 13),
        'anos': range(ano_atual - 2, ano_atual + 2)
    })

def editar_processamento(request, pk):
    proc = get_object_or_404(ProcessamentoSalarial, pk=pk, funcionario__empresa=request.empresa)
    
    if proc.contabilizado:
        messages.error(request, 'Não é possível editar um processamento já contabilizado.')
        return redirect(f'/rh/processamento/?mes={proc.mes}&ano={proc.ano}')

    if request.method == 'POST':
        form = ProcessamentoVariaveisForm(request.POST)
        if form.is_valid():
            proc.horas_falta = form.cleaned_data['horas_falta']
            proc.horas_50 = form.cleaned_data['horas_50']
            proc.horas_100 = form.cleaned_data['horas_100']
            
            # Recalcular valores
            res = calcular_salario(proc.funcionario, proc.mes, proc.ano, proc.horas_falta, proc.horas_50, proc.horas_100)

            
            # Atualizar campos
            proc.salario_base = res['salario_base']
            proc.subsidio_alimentacao = res['subsidio_alimentacao']
            proc.subsidio_transporte = res['subsidio_transporte']
            proc.outros_abonos = res['outros_abonos']
            proc.valor_horas_extras = res['valor_horas_extras']
            proc.desconto_faltas = res['desconto_faltas']
            proc.total_bruto = res['total_bruto']
            proc.inss_funcionario = res['inss_funcionario']
            proc.inss_empresa = res['inss_empresa']
            proc.irt = res['irt']
            proc.total_descontos = res['total_descontos']
            proc.salario_liquido = res['salario_liquido']
            
            proc.save()
            messages.success(request, 'Processamento recalculado com sucesso!')
            return redirect(f'/rh/processamento/?mes={proc.mes}&ano={proc.ano}')
    else:
        form = ProcessamentoVariaveisForm(initial={
            'horas_falta': proc.horas_falta,
            'horas_50': proc.horas_50,
            'horas_100': proc.horas_100
        })
    
    return render(request, 'rh/editar_processamento.html', {'form': form, 'proc': proc})

def contabilizar_salarios(request):
    """Gera lançamentos contabilísticos para todos os salários do mês"""
    empresa = request.empresa
    mes = int(request.GET.get('mes'))
    ano = int(request.GET.get('ano'))
    
    processamentos = ProcessamentoSalarial.objects.filter(
        funcionario__empresa=empresa, 
        mes=mes, 
        ano=ano,
        contabilizado=False
    )
    
    if not processamentos.exists():
        messages.warning(request, 'Não existem processamentos pendentes de contabilização para este período.')
        return redirect(f'/rh/processamento/?mes={mes}&ano={ano}')

    # Tenta obter contas do plano (Simplificado para PGC)
    # 62.1 - Remunerações
    # 62.2 - Encargos (INSS Empresa)
    # 34.1 - INSS a Pagar
    # 34.2 - IRT a Pagar
    # 36.1 - Remunerações a Pagar
    
    try:
        c_62 = Conta.objects.filter(codigo__startswith='62', empresa=empresa).first()
        c_34 = Conta.objects.filter(codigo__startswith='34', empresa=empresa).first()
        c_36 = Conta.objects.filter(codigo__startswith='36', empresa=empresa).first()
        
        # Fallback genérico se não acertou as contas
        if not c_62: c_62 = Conta.objects.filter(empresa=empresa, codigo__startswith='6').first()
        if not c_34: c_34 = Conta.objects.filter(empresa=empresa, codigo__startswith='3').first()
        if not c_36: c_36 = Conta.objects.filter(empresa=empresa, codigo__startswith='3').first()
    except:
        messages.error(request, 'Erro ao localizar contas do PGC. Verifique o seu Plano de Contas.')
        return redirect(f'/rh/processamento/?mes={mes}&ano={ano}')

    # Agrupar valores
    total_bruto = sum(p.total_bruto for p in processamentos)
    total_inss_empresa = sum(p.inss_empresa for p in processamentos)
    total_inss_func = sum(p.inss_funcionario for p in processamentos)
    total_irt = sum(p.irt for p in processamentos)
    total_liquido = sum(p.salario_liquido for p in processamentos)
    
    # Criar Lançamento
    lc = LancamentoDiario.objects.create(
        empresa=empresa,
        tipo='NORMAL',
        data=timezone.now(),
        descricao=f"Processamento Salarial - {mes}/{ano}"
    )
    
    # Movimentos
    # 1. Custo com Pessoal (Debito)
    # Bruto + Encargos Empresa
    MovimentoRazao.objects.create(lancamento=lc, conta=c_62, tipo='D', valor=total_bruto + total_inss_empresa)
    
    # 2. Passivos (Credito)
    # INSS Total (Func + Empresa) -> Estado
    MovimentoRazao.objects.create(lancamento=lc, conta=c_34, tipo='C', valor=total_inss_empresa + total_inss_func)
    
    # IRT -> Estado
    MovimentoRazao.objects.create(lancamento=lc, conta=c_34, tipo='C', valor=total_irt)
    
    # Liquido -> Pessoal a Pagar
    MovimentoRazao.objects.create(lancamento=lc, conta=c_36, tipo='C', valor=total_liquido)
    
    # Atualizar status
    processamentos.update(contabilizado=True, lancamento=lc)
    
    messages.success(request, f'Contabilização efetuada com sucesso! Lançamento {lc.numero}.')
    return redirect(f'/rh/processamento/?mes={mes}&ano={ano}')

def pdf_recibo_salario(request, pk):
    from .utils_pdf_rh import gerar_pdf_recibo
    return gerar_pdf_recibo(request, pk)

def pdf_folha_remuneracoes(request):
    # Folha AGT / INSS
    from .utils_pdf_rh import gerar_pdf_folha_geral
    mes = int(request.GET.get('mes', timezone.now().month))
    ano = int(request.GET.get('ano', timezone.now().year))
    tipo = request.GET.get('tipo', 'AGT') # 'AGT' ou 'INSS'
    return gerar_pdf_folha_geral(request, mes, ano, tipo)

# ==========================================
# NOVAS FUNCIONALIDADES RH (FALTAS, IRT, ETC)
# ==========================================

from .models import TabelaIRT, Falta, HoraExtra
from .forms import TabelaIRTForm, FaltaForm, HoraExtraForm
from decimal import Decimal

def tabela_irt_list(request):
    """Visualizar e Editar Tabela IRT"""
    tabela = TabelaIRT.objects.all()
    if request.method == 'POST':
        # Se for edição, idealmente seria um FormSet, mas para simplificar vamos permitir apenas reset ou update individual
        pass
    
    return render(request, 'rh/tabela_irt.html', {'tabela': tabela})

def atualizar_tabela_irt(request):
    """Reseta a Tabela IRT para os valores padrão de 2020/2021"""
    if request.method == 'POST':
        TabelaIRT.objects.all().delete()
        
        # Padrão AGT conforme imagem enviada pelo usuário
        dados = [
            (Decimal('100000'), Decimal('0.0'), Decimal('0'), Decimal('0')),
            (Decimal('150000'), Decimal('13.0'), Decimal('0'), Decimal('100001')),
            (Decimal('200000'), Decimal('16.0'), Decimal('12500'), Decimal('150001')),
            (Decimal('300000'), Decimal('18.0'), Decimal('31250'), Decimal('200001')),
            (Decimal('500000'), Decimal('19.0'), Decimal('49250'), Decimal('300001')),
            (Decimal('1000000'), Decimal('20.0'), Decimal('87250'), Decimal('500001')),
            (Decimal('1500000'), Decimal('21.0'), Decimal('187249'), Decimal('1000001')),
            (Decimal('2000000'), Decimal('22.0'), Decimal('292249'), Decimal('1500001')),
            (Decimal('2500000'), Decimal('23.0'), Decimal('402249'), Decimal('2000001')),
            (Decimal('5000000'), Decimal('24.0'), Decimal('517249'), Decimal('2500001')),
            (Decimal('10000000'), Decimal('24.5'), Decimal('1117249'), Decimal('5000001')),
            (Decimal('99999999999'), Decimal('25.0'), Decimal('2342248'), Decimal('10000001')),
        ]
        
        for limite, taxa, fixa, excesso in dados:
            TabelaIRT.objects.create(limite=limite, taxa=taxa, parcela_fixa=fixa, excesso=excesso)
            
        messages.success(request, 'Tabela IRT atualizada com sucesso (Padrão AGT).')
    
    return redirect('tabela_irt')

def lancamentos_rh_list(request):
    """Lista Faltas e Horas Extras"""
    empresa = request.empresa
    if not empresa: return redirect('configuracao_empresa')
    
    faltas = Falta.objects.filter(funcionario__empresa=empresa).order_by('-data')[:50]
    horas_extras = HoraExtra.objects.filter(funcionario__empresa=empresa).order_by('-data')[:50]
    
    return render(request, 'rh/lancamentos_list.html', {
        'faltas': faltas,
        'horas_extras': horas_extras
    })

def nova_falta(request):
    empresa = request.empresa
    if request.method == 'POST':
        form = FaltaForm(request.POST, request.FILES, empresa=empresa)
        if form.is_valid():
            form.save()
            messages.success(request, 'Falta registada com sucesso.')
            return redirect('lancamentos_rh_list')
    else:
        form = FaltaForm(empresa=empresa)
    
    return render(request, 'rh/falta_form.html', {'form': form})

def nova_hora_extra(request):
    empresa = request.empresa
    if request.method == 'POST':
        form = HoraExtraForm(request.POST, empresa=empresa)
        if form.is_valid():
            form.save()
            messages.success(request, 'Horas extras registadas com sucesso.')
            return redirect('lancamentos_rh_list')
    else:
        form = HoraExtraForm(empresa=empresa)
    
    return render(request, 'rh/hora_extra_form.html', {'form': form})

