from django.shortcuts import render, redirect, get_object_or_404 # Importa funções do Django para renderizar templates, redirecionar usuários e buscar objetos no banco de dados
from django.contrib.auth import authenticate, login # Importa as funções de autenticação e login do Django
from django.contrib.auth.forms import AuthenticationForm # Importa o formulário de login padrão do Django
from django.contrib.auth.decorators import user_passes_test # Importa o decorador que vai proteger a View
from django.http import JsonResponse # Importa a função para retornar respostas JSON
from django.db.models import Count, Q, Sum # Importa funções para contagem e consultas complexas no banco de dados
from app.models import User # Importa o modelo de usuário padrão do Django
from django.core.paginator import Paginator # Importa a classe de paginação do Django
from django.conf import settings # Importa as configurações do Django
import psutil, os # Importa a biblioteca psutil para monitoramento de recursos do sistema e os para manipulação de caminhos de arquivos


# 1. A PORTA DE SEGURANÇA (O Escudo)
# Esta função verifica se quem está tentando acessar é o "Dono" (Superuser)
def is_superuser(user):
    return user.is_superuser

# 2. A LÓGICA DO DASHBOARD (O Cérebro)
# O @user_passes_test é um guarda-costas: se a função acima for Falsa, ele chuta o usuário para a tela de login convencional.
# MODO FURTIVO: login_url='/login/' garante que quem tentar acessar /master/ sem permissão vai para o login dos clientes.
@user_passes_test(is_superuser, login_url='/login/')
def master_dashboard(request):
    
    # Aqui é feita a busca dos dados reais no Banco de Dados
    total_cadastros = User.objects.count()
    total_ativos = User.objects.filter(is_active=True).count()

    # Leitura de Hardware
    # O interval=0.5 faz o Python medir a CPU por meio segundo para dar um resultado preciso
    cpu_uso = psutil.cpu_percent(interval=0.5) 
    memoria = psutil.virtual_memory()
    ram_uso = memoria.percent

    # Verifica o estado do interruptor
    caminho_flag = os.path.join(settings.BASE_DIR, 'manutencao.flag')
    em_manutencao = os.path.exists(caminho_flag)

        
    # Aqui tudo são empacotados todos os dados num "dicionário" para enviar para a tela
    contexto = {
        'total_cadastros': total_cadastros,
        'total_ativos': total_ativos,
        'cpu_uso': cpu_uso,
        'ram_uso': ram_uso,
        'em_manutencao': em_manutencao,
    }
    
    # O render junta os dados (contexto) com o visual (HTML) e entrega ao usuário
    return render(request, 'master_dashboard.html', contexto)

def master_login(request):
    # MODO FURTIVO: Se um cliente comum já estiver logado no sistema e tentar xeretar essa URL, chuta pro login convencional.
    if request.user.is_authenticated and not request.user.is_superuser:
        return redirect('/login/')

    # Se o usuário já estiver logado e for o dono, manda direto pro painel
    if request.user.is_authenticated and request.user.is_superuser:
        return redirect('master_dashboard')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            # A trava principal: só loga se for Superuser
            if user.is_superuser:
                login(request, user)
                return redirect('master_dashboard')
            else:
                # MODO FURTIVO: Se um cliente tentar usar o login dele nesta tela master, 
                # em vez de dar erro, fingimos que nada aconteceu e mandamos pro login convencional.
                return redirect('/login/')
    
    return render(request, 'master_login.html')

# URL invisível acedida pelo JavaScript a cada 2 segundos
@user_passes_test(is_superuser, login_url='/login/')
def api_saude_servidor(request):
    cpu_uso = psutil.cpu_percent(interval=0.5)
    memoria = psutil.virtual_memory()
    ram_uso = memoria.percent
    
    total_hits = User.objects.aggregate(total=Sum('requisicoes'))['total'] or 0
    
    # NOVO: Pega os 5 utilizadores com mais requisições (que tenham mais de 0)
    top_users = list(User.objects.filter(requisicoes__gt=0).order_by('-requisicoes').values('username', 'requisicoes')[:5])
    
    return JsonResponse({
        'cpu': cpu_uso,
        'ram': ram_uso,
        'hits': total_hits,
        'top_users': top_users # Envia o ranking para o JavaScript
    })

@user_passes_test(is_superuser, login_url='/login/')
def toggle_user_status(request, user_id):
    usuario = get_object_or_404(User, id=user_id)
    
    # Trava de segurança: impede alterar o status do Dono do sistema
    if not usuario.is_superuser:
        # Inverte o status atual (se True vira False, se False vira True)
        usuario.is_active = not usuario.is_active
        usuario.save(update_fields=['is_active'])
        
    return redirect('master_clientes')

@user_passes_test(is_superuser, login_url='/login/')
def delete_user(request, user_id):
    usuario = get_object_or_404(User, id=user_id)
    
    # Trava de segurança: impede excluir a conta do Dono do sistema
    if not usuario.is_superuser:
        usuario.delete()
        
    return redirect('master_clientes')

@user_passes_test(is_superuser, login_url='/login/')
def master_clientes(request):
    total_cadastros = User.objects.count()
    query = request.GET.get('q', '')
    
    lista_usuarios = User.objects.annotate(
        qnt_veiculos=Count('veiculos', distinct=True),
        qnt_manutencoes=Count('servicos_realizados', distinct=True)
    )
    
    if query:
        lista_usuarios = lista_usuarios.filter(
            Q(username__icontains=query) | Q(email__icontains=query)
        )
        
    lista_usuarios = lista_usuarios.order_by('-date_joined')
    
    # --- MÁGICA DA PAGINAÇÃO AQUI ---
    paginator = Paginator(lista_usuarios, 10) # Corta de 10 em 10
    numero_pagina = request.GET.get('page') # Vê em que página o usuário clicou
    page_obj = paginator.get_page(numero_pagina) # Puxa só os 10 daquela página
    
    contexto = {
        'page_obj': page_obj, # Agora enviamos o pacote paginado (page_obj) para a tela
        'total_cadastros': total_cadastros,
        'query': query,
    }
    return render(request, 'master_clientes.html', contexto)

@user_passes_test(is_superuser, login_url='/login/')
def master_saude(request):
    # O histórico de CPU/RAM será gerido no frontend com Chart.js futuramente
    return render(request, 'master_saude.html')

@user_passes_test(is_superuser, login_url='/login/')
def toggle_manutencao(request):
    caminho_flag = os.path.join(settings.BASE_DIR, 'manutencao.flag')
    
    # Se o arquivo existe, exclui (Desliga a manutenção)
    if os.path.exists(caminho_flag):
        os.remove(caminho_flag)
    # Se não existe, cria (Liga a manutenção)
    else:
        with open(caminho_flag, 'w') as f:
            f.write('ativo')
            
    return redirect('master_dashboard')