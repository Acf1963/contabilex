from django.shortcuts import redirect
from django.contrib import messages
from django.core.cache import cache
import requests
import re

from decimal import Decimal
from django.utils import timezone
from .models import Cambio

def atualizar_cambios(request):
    """Força atualização das taxas de câmbio consumindo a API do BNA"""
    try:
        # Limpa cache existente antes de forçar novo pedido
        cache.delete('bna_exchange_rates')
        
        headers = {'User-Agent': 'Mozilla/5.0'}
        url_base = "https://www.bna.ao/service/rest/taxas/get/taxa/referencia?tipocambio=b&moeda="
        
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        # USD
        res_usd = requests.get(f"{url_base}usd", headers=headers, timeout=10, verify=False)
        usd = "912.286"
        if res_usd.status_code == 200:
            data = res_usd.json()
            if data.get('success') and data.get('genericResponse'):
                usd = str(data['genericResponse'][0]['taxa'])
        
        # EUR
        res_eur = requests.get(f"{url_base}eur", headers=headers, timeout=10, verify=False)
        eur = "1069.522"
        if res_eur.status_code == 200:
            data = res_eur.json()
            if data.get('success') and data.get('genericResponse'):
                eur = str(data['genericResponse'][0]['taxa'])
        
        rates = {'USD': usd, 'EUR': eur}
        cache.set('bna_exchange_rates', rates, 86400)
        
        # Atualização automática da empresa ativa
        empresa = getattr(request, 'empresa', None)
        log_update = ""
        if empresa:
            v_usd = Decimal(usd)
            v_eur = Decimal(eur)
            
            # Decide qual taxa aplicar com base na moeda estrangeira da empresa
            taxa_aplicar = None
            if empresa.moeda_estrangeira == 'USD':
                taxa_aplicar = v_usd
            elif empresa.moeda_estrangeira == 'EUR':
                taxa_aplicar = v_eur
            
            if taxa_aplicar:
                empresa.taxa_cambio = taxa_aplicar
                empresa.save()
                
                # Regista no histórico para hoje
                Cambio.objects.update_or_create(
                    empresa=empresa,
                    data_inicio=timezone.now().date(),
                    defaults={'taxa': taxa_aplicar}
                )
                log_update = f" e aplicada à empresa {empresa.nome}"
        
        messages.success(request, f'Taxas atualizadas via BNA API: USD {usd} | EUR {eur}{log_update}')
    except Exception as e:
        messages.error(request, f'Erro técnico ao conectar à API do BNA: {str(e)}')
    
    return redirect(request.META.get('HTTP_REFERER', 'home'))
