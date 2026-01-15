from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib import messages
from django.db.models import Q
from datetime import datetime
from .relatorios import (
    gerar_balancete, 
    gerar_razao, 
    gerar_diario,
    gerar_demonstracao_resultados,
    exportar_balancete_excel,
    gerar_balanco_patrimonial,
    gerar_mapa_iva,
    gerar_fluxo_caixa,
    gerar_balancete_resultados,
    calcular_apuramento_resultados
)
from .models import Conta, Empresa
import tempfile
import os

def relatorios_menu(request):
    """Menu principal de relatórios"""
    return render(request, 'relatorios/menu.html')

def relatorio_balancete(request):
    """Balancete"""
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')
    exportar = request.GET.get('exportar')
    
    if data_inicio:
        data_inicio = datetime.strptime(data_inicio, '%Y-%m-%d').date()
    if data_fim:
        data_fim = datetime.strptime(data_fim, '%Y-%m-%d').date()
    
    empresa = request.empresa
    balancete = gerar_balancete(empresa, data_inicio, data_fim)
    
    if exportar == 'excel':
        # Exportar para Excel
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
        exportar_balancete_excel(balancete, temp_file.name, empresa=empresa)
        
        with open(temp_file.name, 'rb') as f:
            response = HttpResponse(f.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = f'attachment; filename="Balancete_{datetime.now().strftime("%Y%m%d")}.xlsx"'
        
        os.unlink(temp_file.name)
        return response
    
    return render(request, 'relatorios/balancete.html', {
        'balancete': balancete,
        'data_inicio': data_inicio,
        'data_fim': data_fim,
        'empresa': empresa,
    })

def relatorio_razao(request):
    """Razão de uma conta"""
    conta_id = request.GET.get('conta')
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')
    empresa = request.empresa
    
    contas = Conta.objects.filter(movimentos__lancamento__empresa=empresa).distinct().order_by('codigo')
    
    razao = None
    if conta_id:
        if data_inicio:
            data_inicio = datetime.strptime(data_inicio, '%Y-%m-%d').date()
        if data_fim:
            data_fim = datetime.strptime(data_fim, '%Y-%m-%d').date()
        
        razao = gerar_razao(conta_id, empresa, data_inicio, data_fim)
    
    return render(request, 'relatorios/razao.html', {
        'contas': contas,
        'razao': razao,
        'conta_selecionada': conta_id,
        'data_inicio': data_inicio,
        'data_fim': data_fim,
        'empresa': empresa,
    })

def relatorio_diario(request):
    """Diário"""
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')
    
    if data_inicio:
        data_inicio = datetime.strptime(data_inicio, '%Y-%m-%d').date()
    if data_fim:
        data_fim = datetime.strptime(data_fim, '%Y-%m-%d').date()
    
    empresa = request.empresa
    diario = gerar_diario(empresa, data_inicio, data_fim)
    
    return render(request, 'relatorios/diario.html', {
        'diario': diario,
        'data_inicio': data_inicio,
        'data_fim': data_fim,
        'empresa': empresa,
    })

def relatorio_demonstracao_resultados(request):
    """Demonstração de Resultados"""
    ano = request.GET.get('ano', datetime.now().year)
    empresa = request.empresa
    demonstracao = gerar_demonstracao_resultados(empresa, ano)
    
    return render(request, 'relatorios/demonstracao_resultados.html', {
        'demonstracao': demonstracao,
        'ano': ano,
        'empresa': empresa,
    })

def relatorio_balanco_patrimonial(request):
    """Balanço"""
    data_ref = request.GET.get('data')
    if data_ref:
        data_ref = datetime.strptime(data_ref, '%Y-%m-%d').date()
    
    empresa = request.empresa
    balanco = gerar_balanco_patrimonial(empresa, data_ref)
    
    return render(request, 'relatorios/balanco.html', {
        'balanco': balanco,
        'empresa': empresa,
    })

def relatorio_mapa_iva(request):
    """Mapa de IVA"""
    mes = int(request.GET.get('mes', datetime.now().month))
    ano = int(request.GET.get('ano', datetime.now().year))
    empresa = request.empresa
    
    mapa = gerar_mapa_iva(empresa, mes, ano)
    
    return render(request, 'relatorios/mapa_iva.html', {
        'mapa': mapa,
        'mes': mes,
        'ano': ano,
        'empresa': empresa,
    })

def relatorio_fluxo_caixa(request):
    """Fluxo de Caixa"""
    mes = int(request.GET.get('mes', datetime.now().month))
    ano = int(request.GET.get('ano', datetime.now().year))
    empresa = request.empresa
    
    fluxo = gerar_fluxo_caixa(empresa, mes, ano)
    
    return render(request, 'relatorios/fluxo_caixa.html', {
        'fluxo': fluxo,
        'mes': mes,
        'ano': ano,
        'empresa': empresa,
    })

def relatorio_balancete_resultados(request):
    """Balancete de Apuramento de Resultados"""
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')
    ano = request.GET.get('ano')
    
    if data_inicio:
        data_inicio = datetime.strptime(data_inicio, '%Y-%m-%d').date()
    if data_fim:
        data_fim = datetime.strptime(data_fim, '%Y-%m-%d').date()
    if ano:
        ano = int(ano)
    else:
        ano = datetime.now().year
        
    empresa = request.empresa
    balancete = gerar_balancete_resultados(empresa, ano, data_inicio, data_fim)
    
    return render(request, 'relatorios/balancete_resultados.html', {
        'balancete': balancete,
        'data_inicio': data_inicio,
        'data_fim': data_fim,
        'ano': ano,
        'empresa': empresa,
    })

def apuramento_resultados(request):
    """View para processar o fecho de contas e apuramento de resultados"""
    from .models import LancamentoDiario, MovimentoRazao, Conta
    from datetime import date
    
    ano = int(request.GET.get('ano', datetime.now().year))
    empresa = request.empresa
    dados = calcular_apuramento_resultados(empresa, ano)
    
    if request.method == 'POST':
        # Executar o lançamento de fecho
        try:
            # Tentar obter conta da empresa primeiro, senão do PGC global
            conta_88 = Conta.objects.filter(codigo='88').filter(Q(empresa=empresa) | Q(empresa__isnull=True)).first()
            if not conta_88:
                messages.error(request, 'Conta 88 não encontrada.')
                return redirect('apuramento_resultados')
            
            lancamento = LancamentoDiario.objects.create(
                empresa=empresa,
                data=date(ano, 12, 31),
                descricao=f"Apuramento de Resultados - Exercício {ano}"
            )
            
            for item in dados['items']:
                if item['tipo'] == 'CUSTO':
                    # Gastos (6) têm saldo Devedor (D > C)
                    # Para anular: Creditamos a conta 6 e Debitamos a 88
                    # Crédito na conta 6
                    MovimentoRazao.objects.create(
                        lancamento=lancamento,
                        conta=item['conta'],
                        tipo='C',
                        valor=item['saldo']
                    )
                    # Débito na conta 88
                    MovimentoRazao.objects.create(
                        lancamento=lancamento,
                        conta=conta_88,
                        tipo='D',
                        valor=item['saldo']
                    )
                else:
                    # Proveitos (7) têm saldo Credor (C > D)
                    # Para anular: Debitamos a conta 7 e Creditamos a 88
                    # Débito na conta 7
                    MovimentoRazao.objects.create(
                        lancamento=lancamento,
                        conta=item['conta'],
                        tipo='D',
                        valor=item['saldo']
                    )
                    # Crédito na conta 88
                    MovimentoRazao.objects.create(
                        lancamento=lancamento,
                        conta=conta_88,
                        tipo='C',
                        valor=item['saldo']
                    )
            
            messages.success(request, f'Apuramento de resultados do exercício {ano} concluído com sucesso!')
            return redirect('relatorio_diario')
            
        except Exception as e:
            messages.error(request, f'Erro ao processar apuramento: {str(e)}')
            
    return render(request, 'relatorios/apuramento_form.html', {
        'dados': dados,
        'ano': ano,
        'empresa': empresa,
    })

def exportar_saft_xml(request):
    """
    Exporta o ficheiro SAF-T (AO)
    """
    from .utils_saft import gerar_saft_xml
    from datetime import datetime, date
    
    mes = int(request.GET.get('mes', datetime.now().month))
    ano = int(request.GET.get('ano', datetime.now().year))
    empresa = request.empresa
    
    # Calcular datas
    if mes == 0: # Ano inteiro
        start_date = date(ano, 1, 1)
        end_date = date(ano, 12, 31)
    else:
        from calendar import monthrange
        start_date = date(ano, mes, 1)
        last_day = monthrange(ano, mes)[1]
        end_date = date(ano, mes, last_day)
        
    xml_content = gerar_saft_xml(empresa, start_date, end_date)
    
    filename = f"SAFT_AO_{empresa.nif}_{ano}_{mes:02d}.xml"
    
    response = HttpResponse(xml_content, content_type='application/xml')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response

