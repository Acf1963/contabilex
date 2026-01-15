from .models import Empresa

class EmpresaMiddleware:
    """
    Middleware que identifica a empresa ativa na sessão e a disponibiliza no request.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 1. Tentar obter o ID da empresa da sessão
        empresa_id = request.session.get('empresa_id')
        
        request.empresa = None
        
        if empresa_id:
            try:
                request.empresa = Empresa.objects.get(id=empresa_id)
            except Empresa.DoesNotExist:
                # Se o ID na sessão é inválido, limpar e pegar a primeira disponível
                request.session['empresa_id'] = None
        
        # 2. Se não houver empresa selecionada, tentar definir a primeira como padrão
        if not request.empresa:
            request.empresa = Empresa.objects.first()
            if request.empresa:
                request.session['empresa_id'] = request.empresa.id
        
        # 3. Ativar o idioma baseado no país da empresa ativa
        if request.empresa:
            from django.utils import translation
            paises_idiomas = {
                'AO': 'pt',
                'PT': 'pt',
                'FR': 'fr',
                'ES': 'es',
                'US': 'en',
            }
            idioma = paises_idiomas.get(request.empresa.pais, 'pt')
            translation.activate(idioma)
            request.LANGUAGE_CODE = translation.get_language()

        response = self.get_response(request)
        return response
