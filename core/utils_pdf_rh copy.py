from django.http import HttpResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
import os
from .models import ProcessamentoSalarial, Empresa, Funcionario

def gerar_pdf_recibo(request, pk):
    proc = ProcessamentoSalarial.objects.get(pk=pk)
    empresa = proc.funcionario.empresa
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="Recibo_{proc.funcionario.nome}_{proc.mes}_{proc.ano}.pdf"'
    from datetime import datetime

    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4
    
    # --- Cabeçalho com Logo ---
    if empresa.logo:
        try:
            logo_path = empresa.logo.path
            if os.path.exists(logo_path):
                p.drawImage(ImageReader(logo_path), 2*cm, height - 2.5*cm, width=2.5*cm, preserveAspectRatio=True, mask='auto')
        except:
            p.setFont("Helvetica-Bold", 14)
            p.drawString(2*cm, height - 2*cm, empresa.nome)
    else:
        p.setFont("Helvetica-Bold", 14)
        p.drawString(2*cm, height - 2*cm, empresa.nome)

    p.setFont("Helvetica", 9)
    p.drawString(5*cm, height - 1.5*cm, f"NIF: {empresa.nif}")
    p.drawString(5*cm, height - 2.0*cm, empresa.morada[:100])

    p.setFont("Helvetica-Bold", 14)
    p.drawRightString(width - 2*cm, height - 2*cm, "RECIBO DE SALÁRIO")
    p.setFont("Helvetica", 9)
    p.drawRightString(width - 2*cm, height - 2.5*cm, f"Emissão: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    p.drawRightString(width - 2*cm, height - 3.0*cm, f"Período: {proc.mes:02d}/{proc.ano}")

    p.line(1*cm, height - 3*cm, width - 1*cm, height - 3*cm)

    # --- Dados Funcionario ---
    y = height - 4*cm
    p.setFont("Helvetica-Bold", 10)
    p.drawString(2*cm, y, f"Funcionário: {proc.funcionario.nome}")
    p.setFont("Helvetica", 9)
    p.drawString(2*cm, y - 0.5*cm, f"Cargo: {proc.funcionario.cargo}")
    p.drawString(2*cm, y - 1.0*cm, f"Nº SS: {proc.funcionario.numero_seguranca_social or '---'}")
    p.drawRightString(width - 2*cm, y, f"NIF: {proc.funcionario.nif or '---'}")

    # --- Tabela de Vencimentos ---
    y = height - 6.5*cm
    p.setFillColor(colors.lightgrey)
    p.rect(1.5*cm, y, width - 3*cm, 0.6*cm, fill=1)
    p.setFillColor(colors.black)
    p.setFont("Helvetica-Bold", 9)
    p.drawString(2*cm, y + 0.15*cm, "Descrição")
    p.drawRightString(width - 7*cm, y + 0.15*cm, "Vencimentos")
    p.drawRightString(width - 2*cm, y + 0.15*cm, "Descontos")

    p.setFont("Helvetica", 9)
    y -= 0.6*cm
    # Linha Salario Base
    p.drawString(2*cm, y, "Salário Base")
    p.drawRightString(width - 7*cm, y, f"{proc.salario_base:,.2f}")
    y -= 0.5*cm
    
    if proc.subsidio_alimentacao > 0:
        p.drawString(2*cm, y, "Subsídio de Alimentação")
        p.drawRightString(width - 7*cm, y, f"{proc.subsidio_alimentacao:,.2f}")
        y -= 0.5*cm
    
    if proc.subsidio_transporte > 0:
        p.drawString(2*cm, y, "Subsídio de Transporte")
        p.drawRightString(width - 7*cm, y, f"{proc.subsidio_transporte:,.2f}")
        y -= 0.5*cm

    if proc.outros_abonos > 0:
        p.drawString(2*cm, y, "Outros Abonos")
        p.drawRightString(width - 7*cm, y, f"{proc.outros_abonos:,.2f}")
        y -= 0.5*cm

    # Descontos
    y_desc = height - 7.1*cm
    p.drawString(2*cm, y_desc - 2*cm, "Segurança Social (3%)")
    p.drawRightString(width - 2*cm, y_desc - 2*cm, f"{proc.inss_funcionario:,.2f}")
    
    p.drawString(2*cm, y_desc - 2.5*cm, "I.R.T.")
    p.drawRightString(width - 2*cm, y_desc - 2.5*cm, f"{proc.irt:,.2f}")

    # Totais
    y_fim = height - 13*cm
    p.line(1.5*cm, y_fim, width - 1.5*cm, y_fim)
    p.setFont("Helvetica-Bold", 10)
    p.drawString(2*cm, y_fim - 0.5*cm, "TOTAL BRUTO")
    p.drawRightString(width - 7*cm, y_fim - 0.5*cm, f"{proc.total_bruto:,.2f}")
    
    p.drawString(2*cm, y_fim - 1.0*cm, "TOTAL DESCONTOS")
    p.drawRightString(width - 2*cm, y_fim - 1.0*cm, f"{proc.total_descontos:,.2f}")

    p.setFillColor(colors.HexColor("#f0f0f0"))
    p.rect(1.5*cm, y_fim - 2*cm, width - 3*cm, 0.8*cm, fill=1)
    p.setFillColor(colors.black)
    p.setFont("Helvetica-Bold", 12)
    p.drawString(2*cm, y_fim - 1.5*cm, "LÍQUIDO A RECEBER")
    p.drawRightString(width - 2*cm, y_fim - 1.5*cm, f"{proc.salario_liquido:,.2f} Kz")

    # Rodapé assinaturas
    p.setFont("Helvetica", 8)
    p.drawCentredString(6*cm, 4*cm, "A Empresa")
    p.line(3*cm, 3.8*cm, 9*cm, 3.8*cm)
    
    p.drawCentredString(width - 6*cm, 4*cm, "O Funcionário")
    p.line(width - 9*cm, 3.8*cm, width - 3*cm, 3.8*cm)

    p.showPage()
    p.save()
    return response

def gerar_pdf_folha_geral(request, mes, ano, tipo):
    empresa = request.empresa
    processamentos = ProcessamentoSalarial.objects.filter(funcionario__empresa=empresa, mes=mes, ano=ano)
    
    response = HttpResponse(content_type='application/pdf')
    titulo_ficheiro = f"Folha_{tipo}_{mes}_{ano}.pdf"
    response['Content-Disposition'] = f'inline; filename="{titulo_ficheiro}"'

    p = canvas.Canvas(response, pagesize=landscape(A4))
    w_ls, h_ls = landscape(A4)
    
    p.setFont("Helvetica-Bold", 14)
    p.drawString(1*cm, h_ls - 1.5*cm, f"FOLHA DE REMUNERAÇÕES - {tipo}")
    p.setFont("Helvetica", 10)
    p.drawString(1*cm, h_ls - 2*cm, f"Empresa: {empresa.nome} | NIF: {empresa.nif}")
    from datetime import datetime
    p.drawRightString(w_ls - 1*cm, h_ls - 1.5*cm, f"Processado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    p.drawRightString(w_ls - 1*cm, h_ls - 2.1*cm, f"Período: {mes:02d}/{ano}")

    # Cabeçalho Tabela
    y = h_ls - 3.5*cm
    p.setFillColor(colors.black)
    p.setFont("Helvetica-Bold", 8)
    p.drawString(1*cm, y, "NOME DO TRABALHADOR")
    p.drawString(7*cm, y, "NIF / SS")
    p.drawRightString(12*cm, y, "SALÁRIO BASE")
    p.drawRightString(14.5*cm, y, "ABONOS")
    p.drawRightString(17*cm, y, "TOTAL BRUTO")
    if tipo == 'AGT':
        p.drawRightString(20*cm, y, "INSS (3%)")
        p.drawRightString(23*cm, y, "IRT")
    else: # INSS
        p.drawRightString(20*cm, y, "SS FUNC (3%)")
        p.drawRightString(23*cm, y, "SS EMPR (8%)")
        p.drawRightString(26*cm, y, "TOTAL SS")
    p.drawRightString(w_ls - 1*cm, y, "LÍQUIDO")

    p.line(1*cm, y - 0.2*cm, w_ls - 1*cm, y - 0.2*cm)
    
    y -= 0.7*cm
    p.setFont("Helvetica", 8)
    
    for proc in processamentos:
        p.drawString(1*cm, y, proc.funcionario.nome[:30])
        p.drawString(7*cm, y, f"{proc.funcionario.nif or '---'} / {proc.funcionario.numero_seguranca_social or '---'}")
        p.drawRightString(12*cm, y, f"{proc.salario_base:,.2f}")
        abonos_total = proc.subsidio_alimentacao + proc.subsidio_transporte + proc.outros_abonos
        p.drawRightString(14.5*cm, y, f"{abonos_total:,.2f}")
        p.drawRightString(17*cm, y, f"{proc.total_bruto:,.2f}")
        
        if tipo == 'AGT':
            p.drawRightString(20*cm, y, f"{proc.inss_funcionario:,.2f}")
            p.drawRightString(23*cm, y, f"{proc.irt:,.2f}")
        else: # INSS
            p.drawRightString(20*cm, y, f"{proc.inss_funcionario:,.2f}")
            p.drawRightString(23*cm, y, f"{proc.inss_empresa:,.2f}")
            p.drawRightString(26*cm, y, f"{(proc.inss_funcionario + proc.inss_empresa):,.2f}")
            
        p.drawRightString(w_ls - 1*cm, y, f"{proc.salario_liquido:,.2f}")
        y -= 0.5*cm
        
        if y < 2*cm:
            p.showPage()
            y = h_ls - 2*cm

    p.showPage()
    p.save()
    return response
