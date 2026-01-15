from .models import Empresa

def empresa_context(request):
    """
    Context processor para disponibilizar a empresa ativa e a lista de empresas em todos os templates.
    """
    todas_empresas = Empresa.objects.all()
    active_empresa = getattr(request, 'empresa', None)
    
    # Realidades por país (Idiomas e Termos Fiscais)
    realidades = {
        'AO': {
            'lang': 'pt',
            'mapa_fiscal': 'Mapa de Retenções',
            'imposto_lucro': 'Imposto Industrial',
            'taxa_base': 'IVA',
            'moeda': 'Kwanza',
            'nif_label': 'NIF'
        },
        'PT': {
            'lang': 'pt',
            'mapa_fiscal': 'Declaração de Retenções',
            'imposto_lucro': 'IRC',
            'taxa_base': 'IVA',
            'moeda': 'Euro',
            'nif_label': 'NIF'
        },
        'FR': {
            'lang': 'fr',
            'mapa_fiscal': 'Retenues à la source',
            'imposto_lucro': 'IS (Impôt sur les sociétés)',
            'taxa_base': 'TVA',
            'moeda': 'Euro',
            'nif_label': 'SIREN'
        },
        'ES': {
            'lang': 'es',
            'mapa_fiscal': 'Retenciones',
            'imposto_lucro': 'IS (Impuesto sobre Sociedades)',
            'taxa_base': 'IVA',
            'moeda': 'Euro',
            'nif_label': 'NIF/CIF'
        },
        'US': {
            'lang': 'en',
            'mapa_fiscal': 'Tax Withholding Map',
            'imposto_lucro': 'Income Tax',
            'taxa_base': 'Sales Tax',
            'moeda': 'Dollar',
            'nif_label': 'EIN/SSN'
        }
    }
    
    current_realidade = realidades.get(active_empresa.pais if active_empresa else 'AO', realidades['AO'])

    return {
        'active_empresa': active_empresa,
        'todas_empresas': todas_empresas,
        'r': current_realidade # Disponível como {{ r.label }} nos templates
    }
