from decimal import Decimal, ROUND_CEILING
from .models import TabelaIRT

def calcular_irt_angola(rendimento_tributavel):
    """
    Calcula o IRT de Angola baseado na tabela na base de dados
    """
    r = Decimal(rendimento_tributavel)
    
    # Encontrar o escalão correto (primeiro limite que for maior ou igual ao rendimento)
    # Mas a tabela funciona por intervalos.
    # Ex: <= 100k -> 0
    # <= 150k -> (r - excesso) * taxa + fixa
    
    # Vamos percorrer a tabela ordenada por limite
    escalao = TabelaIRT.objects.filter(limite__gte=r).order_by('limite').first()
    
    if not escalao:
        # Se rendimento for maior que o ultimo limite (caso não tenhamos posto um limite infinito)
        # Pegar o último escalão (maior limite)
        escalao = TabelaIRT.objects.order_by('-limite').first()
        
    if not escalao:
        return Decimal('0')

    if r <= escalao.limite:
        valor = (r - escalao.excesso) * (escalao.taxa / 100) + escalao.parcela_fixa
        return valor.quantize(Decimal('1'), rounding=ROUND_CEILING)
    
    return Decimal('0')

def calcular_salario(funcionario, mes, ano, horas_falta=0, horas_50=Decimal('0'), horas_100=Decimal('0')):
    """
    Processa o salário com faltas e horas extras.
    Calculos baseados na LGT Angola.
    Horário Base: 44 horas semanais.
    Fator Mensal: (44 * 52) / 12 = 190.6666667 horas/mês
    """
    base = funcionario.salario_base
    alimentacao = funcionario.subsidio_alimentacao
    transporte = funcionario.subsidio_transporte
    abonos = funcionario.outros_abonos
    
    # Horas mensais de trabalho (44h semanais)
    horas_mes = Decimal('190.666666667')
    valor_hora = base / horas_mes

    # --- 1. Ajustes por Faltas (Em Horas) ---
    # Faltas injustificadas descontam no salário base e subsídios proporcionalmente
    
    # Proporção da falta em relação ao mês
    horas_falta = Decimal(horas_falta)
    fator_desconto = horas_falta / horas_mes
    
    desconto_base = base * fator_desconto
    desconto_ali = alimentacao * fator_desconto
    desconto_tra = transporte * fator_desconto
    
    # Salários ajustados
    base_ajustada = base - desconto_base
    alimentacao_ajustada = alimentacao - desconto_ali
    transporte_ajustada = transporte - desconto_tra
    
    desconto_total_faltas = desconto_base # Apenas o base para o "Desconto Faltas", os subsidios apenas reduzem
    
    # --- 2. Horas Extras ---
    # Valor Hora já calculado acima
    
    valor_he_50 = valor_hora * horas_50 * Decimal('1.5')
    valor_he_100 = valor_hora * horas_100 * Decimal('2.0')
    total_horas_extras = valor_he_50 + valor_he_100
    
    # --- 3. Base de Incidência ---
    # Total sujeito a impostos
    base_inss = base_ajustada + transporte_ajustada + alimentacao_ajustada + abonos + total_horas_extras
    inss_funcionario = (base_inss * Decimal('0.03')).quantize(Decimal('1'), rounding=ROUND_CEILING)
    inss_empresa = (base_inss * Decimal('0.08')).quantize(Decimal('1'), rounding=ROUND_CEILING)
    
    # Base IRT
    # Isenções (Ajustadas aos dias trabalhados ou fixas? A lei refere limites mensais. Vamos manter o limite mensal por simplicidade, ou ajustar se faltou o mês todo)
    # Na prática, se faltou recebe menos subsidio, logo menos a isentar.
    isencao_ali = min(alimentacao_ajustada, Decimal('30000'))
    isencao_tra = min(transporte_ajustada, Decimal('30000'))
    
    total_bruto = base_ajustada + alimentacao_ajustada + transporte_ajustada + abonos + total_horas_extras
    
    rendimento_tributavel = total_bruto - inss_funcionario - isencao_ali - isencao_tra
    # Nota: Abonos e Horas Extras são normalmente tributáveis em sede de IRT
    
    irt = calcular_irt_angola(max(0, rendimento_tributavel))
    
    total_descontos = inss_funcionario + irt
    liquido = total_bruto - total_descontos
    
    return {
        'salario_base': base_ajustada, # Guardamos o valor efetivamente pago
        'subsidio_alimentacao': alimentacao_ajustada,
        'subsidio_transporte': transporte_ajustada,
        'outros_abonos': abonos,
        'valor_horas_extras': total_horas_extras,
        'desconto_faltas': desconto_total_faltas, # Informativo
        
        'total_bruto': total_bruto,
        'inss_funcionario': inss_funcionario,
        'inss_empresa': inss_empresa,
        'irt': irt,
        'total_descontos': total_descontos,
        'salario_liquido': liquido
    }
