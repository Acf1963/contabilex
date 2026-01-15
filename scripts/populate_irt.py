from core.models import TabelaIRT
from decimal import Decimal

def populate_irt():
    # Clear existing to avoid duplicates if run multiple times
    TabelaIRT.objects.all().delete()
    
    # Data from 2020/2021 table (Logic from utils_rh.py)
    # Limite | Taxa | Parcela Fixa | Excesso/Abater
    # logic: (r - excesso) * taxa + parcela_fixa
    
    # 0 - 100,000: 0%
    TabelaIRT.objects.create(
        limite=Decimal('100000'), 
        taxa=Decimal('0.00'), 
        parcela_fixa=Decimal('0'), 
        excesso=Decimal('0')
    )
    
    # 100,001 - 150,000: 10% on excess of 100,000
    TabelaIRT.objects.create(
        limite=Decimal('150000'), 
        taxa=Decimal('0.10'), 
        parcela_fixa=Decimal('0'), 
        excesso=Decimal('100000')
    )
    
    # 150,001 - 200,000: 13% on excess of 150,000 + 5,000
    TabelaIRT.objects.create(
        limite=Decimal('200000'), 
        taxa=Decimal('0.13'), 
        parcela_fixa=Decimal('5000'), 
        excesso=Decimal('150000')
    )
    
    # 200,001 - 300,000: 16% on excess of 200,000 + 11,500
    TabelaIRT.objects.create(
        limite=Decimal('300000'), 
        taxa=Decimal('0.16'), 
        parcela_fixa=Decimal('11500'), 
        excesso=Decimal('200000')
    )
    
    # 300,001 - 500,000: 18% on excess of 300,000 + 27,500
    TabelaIRT.objects.create(
        limite=Decimal('500000'), 
        taxa=Decimal('0.18'), 
        parcela_fixa=Decimal('27500'), 
        excesso=Decimal('300000')
    )
    
    # 500,001 - 1,000,000: 19% on excess of 500,000 + 63,500
    TabelaIRT.objects.create(
        limite=Decimal('1000000'), 
        taxa=Decimal('0.19'), 
        parcela_fixa=Decimal('63500'), 
        excesso=Decimal('500000')
    )
    
    # 1,000,001 - 1,500,000: 20% on excess of 1,000,000 + 158,500
    TabelaIRT.objects.create(
        limite=Decimal('1500000'), 
        taxa=Decimal('0.20'), 
        parcela_fixa=Decimal('158500'), 
        excesso=Decimal('1000000')
    )
    
    # 1,500,001 - 2,000,000: 21% on excess of 1,500,000 + 258,500
    TabelaIRT.objects.create(
        limite=Decimal('2000000'), 
        taxa=Decimal('0.21'), 
        parcela_fixa=Decimal('258500'), 
        excesso=Decimal('1500000')
    )

    # 2,000,001 - 5,000,000: 22% on excess of 2,000,000 + 363,500
    TabelaIRT.objects.create(
        limite=Decimal('5000000'), 
        taxa=Decimal('0.22'), 
        parcela_fixa=Decimal('363500'), 
        excesso=Decimal('2000000')
    )

    # 5,000,001 - 10,000,000: 23% on excess of 5,000,000 + 1,023,500
    TabelaIRT.objects.create(
        limite=Decimal('10000000'), 
        taxa=Decimal('0.23'), 
        parcela_fixa=Decimal('1023500'), 
        excesso=Decimal('5000000')
    )

    # > 10,000,000: 25% on excess of 10,000,000 + 2,173,500
    # Use a very large number for limit
    TabelaIRT.objects.create(
        limite=Decimal('999999999999'), 
        taxa=Decimal('0.25'), 
        parcela_fixa=Decimal('2173500'), 
        excesso=Decimal('10000000')
    )
    
    print("Tabela IRT populated.")

if __name__ == "__main__":
    populate_irt()
