from django.http import HttpResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
import os

def gerar_pdf_retencoes(context, empresa):
    response = HttpResponse(content_type='application/pdf')
    filename = f"Mapa_Retencoes_{context['mes']}_{context['ano']}.pdf"
    response['Content-Disposition'] = f'inline; filename="{filename}"'

    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4

    # Cabeçalho
    y = height - 2*cm
    p.setFont("Helvetica-Bold", 14)
    p.drawString(2*cm, y, f"MAPA DE RETENÇÕES NA FONTE")
    p.setFont("Helvetica", 8)
    p.drawString(2*cm, y - 0.5*cm, f"(Serviços e IPU)")
    
    p.setFont("Helvetica", 10)
    p.drawString(2*cm, y - 0.9*cm, f"Empresa: {empresa.nome}")
    p.drawString(2*cm, y - 1.4*cm, f"NIF: {empresa.nif or '---'}")
    p.drawString(2*cm, y - 1.9*cm, f"Período: {context['mes']:02d}/{context['ano']}")
    
    from datetime import datetime
    p.drawRightString(width - 2*cm, y, f"Emitido em: {datetime.now().strftime('%d/%m/%Y %H:%M')}")

    # --- 1. A PAGAR (COMPRAS) ---
    y -= 3*cm
    p.setFillColor(colors.HexColor("#f85149"))
    p.rect(2*cm, y, width - 4*cm, 0.8*cm, fill=1, stroke=0)
    p.setFillColor(colors.white)
    p.setFont("Helvetica-Bold", 10)
    p.drawString(2.5*cm, y + 0.25*cm, "IMPOSTO A PAGAR AO ESTADO (COMPRAS)")
    p.drawRightString(width - 2.5*cm, y + 0.25*cm, f"Total: {empresa.moeda_simbolo} {context['total_pagar']:,.2f}")
    
    y -= 1*cm
    p.setFillColor(colors.black)
    p.setFont("Helvetica-Bold", 8)
    p.drawString(2*cm, y, "DATA")
    p.drawString(4*cm, y, "FORNECEDOR")
    p.drawString(10*cm, y, "DOCUMENTO")
    p.drawString(13*cm, y, "TAXA")
    p.drawRightString(width - 2*cm, y, "VALOR RETIDO")
    p.line(2*cm, y-0.2*cm, width-2*cm, y-0.2*cm)
    
    y -= 0.5*cm
    p.setFont("Helvetica", 8)
    for c in context['compras']:
        p.drawString(2*cm, y, c.data_emissao.strftime("%d/%m/%Y"))
        p.drawString(4*cm, y, c.fornecedor.nome[:30])
        p.drawString(10*cm, y, c.numero)
        p.drawString(13*cm, y, f"{c.taxa_retencao}%")
        p.drawRightString(width - 2*cm, y, f"{c.valor_retencao:,.2f}")
        y -= 0.5*cm
        if y < 3*cm:
            p.showPage()
            y = height - 2*cm

    # --- 2. A RECUPERAR (VENDAS) ---
    if context['compras']:
        y -= 1.5*cm # Espaçamento
    
    # Check page break
    if y < 5*cm:
        p.showPage()
        y = height - 2*cm

    p.setFillColor(colors.HexColor("#3fb950"))
    p.rect(2*cm, y, width - 4*cm, 0.8*cm, fill=1, stroke=0)
    p.setFillColor(colors.white)
    p.setFont("Helvetica-Bold", 10)
    p.drawString(2.5*cm, y + 0.25*cm, "IMPOSTO A RECUPERAR DE CLIENTES (VENDAS)")
    p.drawRightString(width - 2.5*cm, y + 0.25*cm, f"Total: {empresa.moeda_simbolo} {context['total_recuperar']:,.2f}")

    y -= 1*cm
    p.setFillColor(colors.black)
    p.setFont("Helvetica-Bold", 8)
    p.drawString(2*cm, y, "DATA")
    p.drawString(4*cm, y, "CLIENTE")
    p.drawString(10*cm, y, "FATURA")
    p.drawString(13*cm, y, "TAXA")
    p.drawRightString(width - 2*cm, y, "VALOR RETIDO")
    p.line(2*cm, y-0.2*cm, width-2*cm, y-0.2*cm)
    
    y -= 0.5*cm
    p.setFont("Helvetica", 8)
    for v in context['vendas']:
        p.drawString(2*cm, y, v.data_emissao.strftime("%d/%m/%Y"))
        p.drawString(4*cm, y, v.cliente.nome[:30])
        p.drawString(10*cm, y, v.numero)
        p.drawString(13*cm, y, f"{v.taxa_retencao}%")
        p.drawRightString(width - 2*cm, y, f"{v.valor_retencao:,.2f}")
        y -= 0.5*cm
        if y < 3*cm:
            p.showPage()
            y = height - 2*cm

    p.showPage()
    p.save()
    return response

def gerar_pdf_fatura(request, fatura_id):
    # Dummy import to keep existing PDF function valid if imported here
    from .utils_pdf import gerar_pdf_fatura as original_gerar_pdf
    return original_gerar_pdf(request, fatura_id)
