from django.http import HttpResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from PIL import Image
from datetime import datetime
from num2words import num2words
from .models import ProcessamentoSalarial


# ============================================================
#   CORES INSTITUCIONAIS
# ============================================================

COR_PRIMARIA = colors.HexColor("#B6643C")   # Terracota suave
COR_SECUNDARIA = colors.HexColor("#E5AE90") # Terracota clara


# ============================================================
#   UTILITÁRIOS
# ============================================================

def valor_por_extenso(valor):
    try:
        # Parte inteira e decimal
        inteiro = int(valor)
        centavos = round((valor - inteiro) * 100)
        
        texto_inteiro = num2words(inteiro, lang='pt_BR').capitalize()
        
        # Ajuste para moeda de Angola (Kwanza/Kwanzas)
        sufixo = "Kwanza" if inteiro == 1 else "Kwanzas"
        resultado = f"{texto_inteiro} {sufixo}"
        
        if centavos > 0:
            texto_centavos = num2words(centavos, lang='pt_BR')
            sufixo_cent = "cêntimo" if centavos == 1 else "cêntimos"
            resultado += f" e {texto_centavos} {sufixo_cent}"
            
        return resultado
    except:
        return ""


# ============================================================
#   FUNÇÃO: RECIBO INDIVIDUAL
# ============================================================

def gerar_pdf_recibo(request, pk):
    proc = ProcessamentoSalarial.objects.get(pk=pk)
    empresa = proc.funcionario.empresa

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = (
        f'inline; filename="Recibo_{proc.funcionario.nome}_{proc.mes}_{proc.ano}.pdf"'
    )

    p = canvas.Canvas(response, pagesize=landscape(A4))
    width, height = landscape(A4)

    def desenhar_recibo(x_offset, titulo_copia):
        # Local "width" para o recibo (metade da folha menos margens)
        w_recibo = (width / 2)
        
        # --------------------------------------------------------
        # CABEÇALHO
        # --------------------------------------------------------
        logo_width = 2.2 * cm
        logo_x = x_offset + 1.2 * cm
        logo_y = height - 5.2 * cm

        if empresa.logo:
            try:
                img = Image.open(empresa.logo.path)
                if img.mode in ("RGBA", "LA"):
                    bg = Image.new("RGB", img.size, (255, 255, 255))
                    bg.paste(img, mask=img.split()[-1])
                    img = bg
                img.thumbnail((180, 180))
                img_reader = ImageReader(img)
                p.drawImage(img_reader, logo_x, logo_y, width=logo_width, preserveAspectRatio=True, mask='auto')
            except:
                pass

        # Nome da empresa e Título (Original/Cópia)
        text_x = logo_x + logo_width + 0.5 * cm
        
        # Coordenada Y inicial (topo)
        y = logo_y + logo_width + 0.3 * cm
        leading = 1.3 * cm        # Para o corpo do recibo
        leading_header = 0.7 * cm # Reduzido apenas para o cabeçalho
        
        p.setFont("Helvetica-Bold", 12)
        p.drawString(text_x, y, empresa.nome)
        
        p.setFont("Helvetica-Bold", 10)
        p.drawRightString(x_offset + w_recibo - 1 * cm, y, "RECIBO DE SALÁRIO")
        
        y -= leading_header
        
        p.setFont("Helvetica", 9)
        p.drawString(text_x, y, f"NIF: {empresa.nif}")
        
        p.setFont("Helvetica-Bold", 8)
        p.drawRightString(x_offset + w_recibo - 1 * cm, y, f"Período: {proc.mes:02d}/{proc.ano}")
        
        y -= (leading_header * 0.8)
        
        p.setFont("Helvetica-BoldOblique", 8)
        p.drawRightString(x_offset + w_recibo - 1 * cm, y, titulo_copia)

        # --------------------------------------------------------
        # DADOS DO FUNCIONÁRIO
        # --------------------------------------------------------
        y -= (leading * 1.0) # Retoma o espaçamento maior para separar do funcionário
        
        p.setFont("Helvetica-Bold", 9)
        p.drawString(x_offset + 1 * cm, y, f"Funcionário: {proc.funcionario.nome}")
        p.drawRightString(x_offset + w_recibo - 1 * cm, y, f"NIF: {proc.funcionario.nif or '---'}")
        
        y -= (leading * 0.7)
        p.setFont("Helvetica", 8)
        p.drawString(x_offset + 1 * cm, y, f"Cargo: {proc.funcionario.cargo}")
        
        y -= (leading * 0.6)
        p.drawString(x_offset + 1 * cm, y, f"Nº SS: {proc.funcionario.numero_seguranca_social or '---'}")

        # --------------------------------------------------------
        # TABELA
        # --------------------------------------------------------
        y -= (leading * 0.8)
        p.setFillColor(COR_PRIMARIA)
        p.rect(x_offset + 0.8 * cm, y, w_recibo - 1.6 * cm, 0.7 * cm, fill=1)
        
        p.setFillColor(colors.white)
        p.setFont("Helvetica-Bold", 8)
        p.drawString(x_offset + 1 * cm, y + 0.2 * cm, "Descrição")
        p.drawRightString(x_offset + w_recibo - 4.5 * cm, y + 0.2 * cm, "Vencimentos")
        p.drawRightString(x_offset + w_recibo - 1 * cm, y + 0.2 * cm, "Descontos")

        p.setFillColor(colors.black)
        p.setFont("Helvetica", 8)
        y -= (leading * 0.8)

        # 1. Salário Base (Vencimento)
        p.drawString(x_offset + 1 * cm, y, "Salário Base")
        p.drawRightString(x_offset + w_recibo - 4.5 * cm, y, f"{proc.salario_base:,.2f}")
        y -= (leading * 0.6)

        # 2. Abonos (Vencimentos)
        abonos_list = [
            ("Subsídio Alimentação", proc.subsidio_alimentacao),
            ("Subsídio Transporte", proc.subsidio_transporte),
            ("Outros Abonos", proc.outros_abonos)
        ]
        for desc, valor in abonos_list:
            if valor > 0:
                p.drawString(x_offset + 1 * cm, y, desc)
                p.drawRightString(x_offset + w_recibo - 4.5 * cm, y, f"{valor:,.2f}")
                y -= (leading * 0.6)

        # 3. Descontos (Segurança Social e IRT)
        # Segurança Social
        p.drawString(x_offset + 1 * cm, y, "Segurança Social (3%)")
        p.drawRightString(x_offset + w_recibo - 1 * cm, y, f"{proc.inss_funcionario:,.2f}")
        y -= (leading * 0.6)
        
        # IRT
        p.drawString(x_offset + 1 * cm, y, "I.R.T.")
        p.drawRightString(x_offset + w_recibo - 1 * cm, y, f"{proc.irt:,.2f}")
        y -= (leading * 0.6)

        # Totais
        y -= (leading * 0.6)
        p.line(x_offset + 0.8 * cm, y + 0.4 * cm, x_offset + w_recibo - 0.8 * cm, y + 0.4 * cm)
        
        p.setFont("Helvetica-Bold", 8)
        p.drawString(x_offset + 1 * cm, y, "TOTAL BRUTO")
        p.drawRightString(x_offset + w_recibo - 4.5 * cm, y, f"{proc.total_bruto:,.2f}")
        
        y -= (leading * 0.6)
        p.drawString(x_offset + 1 * cm, y, "TOTAL DESCONTOS")
        p.drawRightString(x_offset + w_recibo - 1 * cm, y, f"{proc.total_descontos:,.2f}")

        # Líquido
        y -= (leading * 1.0)
        box_h = 0.8 * cm
        p.setFillColor(COR_SECUNDARIA)
        p.rect(x_offset + 0.8 * cm, y, w_recibo - 1.6 * cm, box_h, fill=1)
        p.setFillColor(colors.black)
        p.setFont("Helvetica-Bold", 10)
        p.drawString(x_offset + 1 * cm, y + (box_h/3.5), "LÍQUIDO A RECEBER")
        p.drawRightString(x_offset + w_recibo - 1 * cm, y + (box_h/3.5), f"{proc.salario_liquido:,.2f} Kz")

        # Valor por Extenso
        y -= 0.6 * cm
        p.setFont("Helvetica-Oblique", 7)
        p.drawString(x_offset + 1 * cm, y, f"({valor_por_extenso(proc.salario_liquido)})")

        # Assinaturas
        p.setFont("Helvetica", 7)
        y_sign = 2.0 * cm # Baixado ligeiramente para dar espaço ao extenso
        p.drawCentredString(x_offset + (w_recibo/4) + 0.5 * cm, y_sign, "A Empresa")
        p.line(x_offset + 1 * cm, y_sign - 0.2 * cm, x_offset + (w_recibo/2) - 0.5 * cm, y_sign - 0.2 * cm)
        
        p.drawCentredString(x_offset + (3*w_recibo/4) - 0.5 * cm, y_sign, "O Funcionário")
        p.line(x_offset + (w_recibo/2) + 0.5 * cm, y_sign - 0.2 * cm, x_offset + w_recibo - 1 * cm, y_sign - 0.2 * cm)

    # Desenhar os dois recibos
    desenhar_recibo(0, "ORIGINAL")
    desenhar_recibo(width / 2, "CÓPIA")

    # Linha tracejada de corte
    p.setDash(6, 3)
    p.line(width / 2, 1 * cm, width / 2, height - 1 * cm)

    p.showPage()
    p.save()
    return response


# ============================================================
#   FUNÇÃO: FOLHA AGT / INSS
# ============================================================

def gerar_pdf_folha_geral(request, mes, ano, tipo):
    empresa = request.empresa
    processamentos = ProcessamentoSalarial.objects.filter(
        funcionario__empresa=empresa,
        mes=mes,
        ano=ano
    )

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = (
        f'inline; filename="Folha_{tipo}_{mes}_{ano}.pdf"'
    )

    p = canvas.Canvas(response, pagesize=landscape(A4))
    w, h = landscape(A4)

    # Reset coordenadas
    p.saveState()
    p.translate(0, 0)
    p.scale(1, 1)

    # --------------------------------------------------------
    # CABEÇALHO MINIMALISTA PREMIUM
    # --------------------------------------------------------
    logo_width = 2.5 * cm
    logo_x = 1 * cm
    logo_y = h - 6.2 * cm

    img = None
    if empresa.logo:
        try:
            img = Image.open(empresa.logo.path)

            if img.mode in ("RGBA", "LA"):
                bg = Image.new("RGB", img.size, (255, 255, 255))
                bg.paste(img, mask=img.split()[-1])
                img = bg

            img.thumbnail((250, 250))
            img_reader = ImageReader(img)

            p.drawImage(
                img_reader,
                logo_x, logo_y,
                width=logo_width,
                preserveAspectRatio=True,
                mask='auto'
            )

        except Exception as ex:
            p.setFont("Helvetica", 8)
            p.drawString(logo_x, logo_y, f"Erro ao carregar logo: {ex}")

    # Nome da empresa
    text_x = logo_x + logo_width + 1.5 * cm
    text_y = logo_y + 3.7 * cm

    p.setFont("Helvetica-Bold", 14)
    p.drawString(text_x, text_y, empresa.nome)

    p.setFont("Helvetica", 10)
    p.drawString(text_x, text_y - 0.6 * cm, f"NIF: {empresa.nif}")

    # --------------------------------------------------------
    # TÍTULOS
    # --------------------------------------------------------
    p.setFont("Helvetica-Bold", 14)
    p.drawString(5 * cm, h - 1.5 * cm, f"FOLHA DE REMUNERAÇÕES - {tipo}")

    p.setFont("Helvetica", 10)
    p.drawRightString(w - 1 * cm, h - 1.5 * cm, f"Processado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    p.drawRightString(w - 1 * cm, h - 2.1 * cm, f"Período: {mes:02d}/{ano}")

    # --------------------------------------------------------
    # CABEÇALHO DA TABELA (COR PRIMÁRIA)
    # --------------------------------------------------------
    y = h - 4 * cm
    p.setFillColor(COR_PRIMARIA)
    p.rect(1 * cm, y - 0.2 * cm, w - 2 * cm, 0.8 * cm, fill=1)

    p.setFillColor(colors.white)
    p.setFont("Helvetica-Bold", 8)

    p.drawString(1.2 * cm, y + 0.1 * cm, "NOME DO TRABALHADOR")
    p.drawString(5.5 * cm, y + 0.1 * cm, "NIF / SS")
    p.drawRightString(12.5 * cm, y + 0.1 * cm, "SALÁRIO BASE")
    p.drawRightString(15.0 * cm, y + 0.1 * cm, "ABONOS")
    p.drawRightString(18.0 * cm, y + 0.1 * cm, "TOTAL BRUTO")

    if tipo == "AGT":
        p.drawRightString(21.0 * cm, y + 0.1 * cm, "INSS (3%)")
        p.drawRightString(24.0 * cm, y + 0.1 * cm, "IRT")
    else:
        p.drawRightString(21.0 * cm, y + 0.1 * cm, "SS FUNC (3%)")
        p.drawRightString(24.0 * cm, y + 0.1 * cm, "SS EMPR (8%)")
        p.drawRightString(27.0 * cm, y + 0.1 * cm, "TOTAL SS")

    p.drawRightString(w - 1 * cm, y + 0.1 * cm, "LÍQUIDO")

    # --------------------------------------------------------
    # LINHAS DA TABELA
    # --------------------------------------------------------
    y -= 1 * cm
    p.setFillColor(colors.black)
    p.setFont("Helvetica", 8)

    for proc in processamentos:
        p.drawString(1.2 * cm, y, proc.funcionario.nome[:30])
        p.drawString(5.5 * cm, y, f"{proc.funcionario.nif or '---'} / {proc.funcionario.numero_seguranca_social or '---'}")
        p.drawRightString(12.5 * cm, y, f"{proc.salario_base:,.2f}")

        abonos = proc.subsidio_alimentacao + proc.subsidio_transporte + proc.outros_abonos
        p.drawRightString(15.0 * cm, y, f"{abonos:,.2f}")
        p.drawRightString(18.0 * cm, y, f"{proc.total_bruto:,.2f}")

        if tipo == "AGT":
            p.drawRightString(21.0 * cm, y, f"{proc.inss_funcionario:,.2f}")
            p.drawRightString(24.0 * cm, y, f"{proc.irt:,.2f}")
        else:
            p.drawRightString(21.0 * cm, y, f"{proc.inss_funcionario:,.2f}")
            p.drawRightString(24.0 * cm, y, f"{proc.inss_empresa:,.2f}")
            p.drawRightString(27.0 * cm, y, f"{(proc.inss_funcionario + proc.inss_empresa):,.2f}")

        p.drawRightString(w - 1 * cm, y, f"{proc.salario_liquido:,.2f}")

        y -= 0.5 * cm

        if y < 2 * cm:
            p.showPage()
            y = h - 2 * cm

    # --------------------------------------------------------
    # LINHA DE TOTAIS
    # --------------------------------------------------------
    y -= 0.6 * cm
    
    # Fundo com transparência (cor primária a 20% de opacidade / 80% transparência)
    p.saveState()
    p.setFillColor(COR_PRIMARIA)
    p.setStrokeColor(COR_PRIMARIA)
    p.setFillAlpha(0.2)
    p.rect(1 * cm, y - 0.2 * cm, w - 2 * cm, 0.7 * cm, fill=1, stroke=0)
    p.restoreState()

    p.setFont("Helvetica-Bold", 8)
    p.setFillColor(colors.black)
    p.drawString(1.2 * cm, y, "TOTAL GERAL")

    # Cálculos dos totais
    total_base = sum(pr.salario_base for pr in processamentos)
    total_abonos = sum(pr.subsidio_alimentacao + pr.subsidio_transporte + pr.outros_abonos for pr in processamentos)
    total_bruto = sum(pr.total_bruto for pr in processamentos)
    total_inss_func = sum(pr.inss_funcionario for pr in processamentos)
    total_liquido = sum(pr.salario_liquido for pr in processamentos)

    p.drawRightString(12.5 * cm, y, f"{total_base:,.2f}")
    p.drawRightString(15.0 * cm, y, f"{total_abonos:,.2f}")
    p.drawRightString(18.0 * cm, y, f"{total_bruto:,.2f}")

    if tipo == "AGT":
        total_irt = sum(pr.irt for pr in processamentos)
        p.drawRightString(21.0 * cm, y, f"{total_inss_func:,.2f}")
        p.drawRightString(24.0 * cm, y, f"{total_irt:,.2f}")
    else:
        total_inss_emp = sum(pr.inss_empresa for pr in processamentos)
        total_ss = total_inss_func + total_inss_emp
        p.drawRightString(21.0 * cm, y, f"{total_inss_func:,.2f}")
        p.drawRightString(24.0 * cm, y, f"{total_inss_emp:,.2f}")
        p.drawRightString(27.0 * cm, y, f"{total_ss:,.2f}")

    p.drawRightString(w - 1 * cm, y, f"{total_liquido:,.2f}")
    
    y -= 0.2 * cm
    p.line(1 * cm, y, w - 1 * cm, y)

    p.showPage()
    p.save()
    return response

