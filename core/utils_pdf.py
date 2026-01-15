from django.http import HttpResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from django.db.models import Q
from .models import Fatura, Conta, Empresa
from datetime import datetime

def gerar_pdf_fatura(request, fatura_id):
    fatura = Fatura.objects.get(id=fatura_id)
    
    # Configuração da Response
    response = HttpResponse(content_type='application/pdf')
    
    # Se o user quiser download, forçamos o attachment
    if request.GET.get('download'):
        filename = f"Fatura_{fatura.numero.replace('/', '_')}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
    else:
        # Senão, mostra no browser (print mode)
        response['Content-Disposition'] = f'inline; filename="Fatura_{fatura.numero}.pdf"'

    # Criação do Canvas
    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4
    
    # --- Cabeçalho dinâmico ---
    p.setFont("Helvetica-Bold", 18)
    p.setFillColor(colors.HexColor("#0A0302"))
    p.drawString(2*cm, height - 2*cm, fatura.empresa.nome)
    
    p.setFont("Helvetica", 10)
    p.setFillColor(colors.grey)
    p.drawString(2*cm, height - 2.5*cm, f"NIF: {fatura.empresa.nif or '---'}")
    p.drawString(2*cm, height - 2.9*cm, fatura.empresa.morada[:50] if fatura.empresa.morada else "Angola")
    p.drawString(2*cm, height - 3.3*cm, f"Data de Emissão PDF: {datetime.now().strftime('%d/%m/%Y %H:%M')}")

    # Info da Fatura (Direita)
    p.setFont("Helvetica-Bold", 16)
    p.setFillColor(colors.black)
    p.drawRightString(width - 2*cm, height - 2*cm, "FATURA")
    
    p.setFont("Helvetica", 10)
    p.drawRightString(width - 2*cm, height - 2.8*cm, f"Nº: {fatura.numero}")
    p.drawRightString(width - 2*cm, height - 3.3*cm, f"Data: {fatura.data_emissao.strftime('%d/%m/%Y')}")
    p.drawRightString(width - 2*cm, height - 3.8*cm, f"Vencimento: {fatura.data_vencimento.strftime('%d/%m/%Y')}")

    # Separador
    p.setStrokeColor(colors.lightgrey)
    p.line(1*cm, height - 4.5*cm, width - 1*cm, height - 4.5*cm)

    # --- Dados do Cliente ---
    y_cliente = height - 5.5*cm
    p.setFont("Helvetica-Bold", 11)
    p.drawString(2*cm, y_cliente, "Cliente:")
    
    p.setFont("Helvetica", 10)
    p.drawString(2*cm, y_cliente - 0.6*cm, fatura.cliente.nome)
    if fatura.cliente.nif:
        p.drawString(2*cm, y_cliente - 1.1*cm, f"NIF: {fatura.cliente.nif}")
    if fatura.cliente.endereco:
        p.drawString(2*cm, y_cliente - 1.6*cm, fatura.cliente.endereco[:50]) # Limita tamanho

    # --- Tabela de Itens ---
    y_header = height - 8.5*cm
    
    # Cabeçalho da Tabela
    p.setFillColor(colors.HexColor("#f0f0f0"))
    p.rect(1.5*cm, y_header - 0.2*cm, width - 3*cm, 0.8*cm, fill=1, stroke=0)
    
    p.setFillColor(colors.black)
    p.setFont("Helvetica-Bold", 10)
    p.drawString(2*cm, y_header, "Descrição")
    p.drawString(10*cm, y_header, "Qtd")
    p.drawString(12*cm, y_header, "Preço Unit")
    p.drawString(14.5*cm, y_header, "Taxa %")
    p.drawRightString(width - 2*cm, y_header, "Total")

    # Itens
    y = y_header - 1*cm
    p.setFont("Helvetica", 10)
    
    for item in fatura.itens.all():
        p.drawString(2*cm, y, item.descricao[:40])
        p.drawString(10*cm, y, f"{item.quantidade:.2f}")
        p.drawString(12*cm, y, f"{item.preco_unitario:.2f}")
        p.drawString(14.5*cm, y, f"{item.taxa_imposto:.0f}%")
        p.drawRightString(width - 2*cm, y, f"{item.total_linha:.2f}")
        
        y -= 0.6*cm
        # Paginação simples (se necessário, para MVP assumimos 1 pag)
    
    # Separador Finais
    y -= 0.5*cm
    p.setStrokeColor(colors.black)
    p.line(10*cm, y, width - 2*cm, y)
    y -= 0.6*cm

    # --- Totais ---
    p.setFont("Helvetica", 10)
    p.drawRightString(width - 5*cm, y, "Subtotal:")
    p.drawRightString(width - 2*cm, y, f"{fatura.subtotal:.2f} Kz")  # Assumindo Kz, mude se for Euro
    
    y -= 0.6*cm
    p.drawRightString(width - 5*cm, y, "Total Imposto:")
    p.drawRightString(width - 2*cm, y, f"{fatura.total_imposto:.2f} Kz")

    y -= 0.8*cm
    p.setFont("Helvetica-Bold", 12)
    p.drawRightString(width - 5*cm, y, "TOTAL A PAGAR:")
    p.drawRightString(width - 2*cm, y, f"{fatura.total:.2f} Kz")

    # Rodapé
    p.setFont("Helvetica", 8)
    p.setFillColor(colors.grey)
    p.drawCentredString(width/2, 2*cm, "Documento processado por computador - ContabileX PWA")

    p.showPage()
    p.save()
    return response

def gerar_pdf_plano_contas(request):
    """Gera PDF do Plano de Contas Geral"""
    from datetime import datetime
    
    empresa = request.empresa
    contas = Conta.objects.filter(Q(empresa=empresa) | Q(empresa__isnull=True)).order_by('codigo')
    
    response = HttpResponse(content_type='application/pdf')
    filename = f"Plano_de_Contas_{datetime.now().strftime('%Y%m%d')}.pdf"
    response['Content-Disposition'] = f'inline; filename="{filename}"'

    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4
    margin = 2*cm
    y = height - margin

    # --- Título ---
    p.setFont("Helvetica-Bold", 16)
    p.drawString(margin, y, "Plano Geral de Contabilidade (PGC)")
    y -= 1*cm
    
    p.setFont("Helvetica", 10)
    p.setFillColor(colors.grey)
    empresa_nome = empresa.nome if empresa else "Sistemas"
    empresa_nif = empresa.nif if empresa else "---"
    p.drawString(margin, y, f"Empresa: {empresa_nome} | NIF: {empresa_nif}")
    p.drawRightString(width - margin, y, f"Impressão: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    y -= 0.5*cm
    
    p.setStrokeColor(colors.lightgrey)
    p.line(margin, y, width - margin, y)
    y -= 1*cm

    # --- Cabeçalho Tabela ---
    p.setFillColor(colors.black)
    p.setFont("Helvetica-Bold", 10)
    p.drawString(margin, y, "Código")
    p.drawString(margin + 3*cm, y, "Descrição")
    p.drawRightString(width - margin, y, "Tipo")
    y -= 0.5*cm
    p.line(margin, y, width - margin, y)
    y -= 0.6*cm

    p.setFont("Helvetica", 9)
    p.setFillColor(colors.black)

    for conta in contas:
        if y < 2*cm:  # Nova página
            p.showPage()
            y = height - margin
            p.setFont("Helvetica-Bold", 10)
            p.drawString(margin, y, "Código")
            p.drawString(margin + 3*cm, y, "Descrição")
            p.drawRightString(width - margin, y, "Tipo")
            y -= 0.5*cm
            p.line(margin, y, width - margin, y)
            y -= 0.6*cm
            p.setFont("Helvetica", 9)

        # Indentação baseada no tipo
        x_desc = margin + 3*cm
        if conta.tipo == 'INTEGRACAO':
            x_desc += 0.5*cm
        elif conta.tipo == 'MOVIMENTO':
            x_desc += 1*cm
            p.setFillColor(colors.black)
        else:
            p.setFont("Helvetica-Bold", 9)

        p.drawString(margin, y, conta.codigo)
        p.drawString(x_desc, y, conta.descricao[:70])
        p.drawRightString(width - margin, y, conta.get_tipo_display())
        
        # Reset font for others
        p.setFont("Helvetica", 9)
        p.setFillColor(colors.black)
        
        y -= 0.5*cm

    # Rodapé
    p.setFont("Helvetica-Oblique", 8)
    p.setFillColor(colors.grey)
    p.drawCentredString(width/2, 1*cm, f"Gerado por ContabileX PWA em {datetime.now().strftime('%d/%m/%Y')}")

    p.showPage()
    p.save()
    return response
