import os
from django.conf import settings
from django.shortcuts import render

class MonitorDeRequisicoesMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 1. Antes da página carregar: Verifica se é um utilizador logado e comum (ignora o dono)
        if request.user.is_authenticated and not request.user.is_superuser:
            request.user.requisicoes += 1
            # update_fields garante que o banco só atualiza este número e fica super rápido
            request.user.save(update_fields=['requisicoes'])
            
        # 2. Deixa o Django entregar a página normalmente
        response = self.get_response(request)
        return response

class ManutencaoMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        caminho_flag = os.path.join(settings.BASE_DIR, 'manutencao.flag')
        
        # Se o interruptor (arquivo) existir, o modo está ATIVO
        if os.path.exists(caminho_flag):
            eh_dono = request.user.is_authenticated and request.user.is_superuser
            eh_painel = request.path.startswith('/master/')
            
            # Bloqueia todos, EXCETO você (Dono) e as rotas do Master Control
            if not (eh_dono or eh_painel):
                return render(request, 'manutencao.html', status=503)
                
        return self.get_response(request)