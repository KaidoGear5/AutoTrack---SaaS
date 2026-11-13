# IMPORTAÇÕES GERAIS E FERRAMENTAS
# ==============================================================================
# render: Monta a tela HTML misturando com os dados do Python.
# redirect: Arremessa o usuário para outra página (URL) após uma ação.
# get_object_or_404: Tenta buscar um dado no banco; se não achar ou for de outro dono, dá erro 404 (página não encontrada), garantindo segurança.
from django.shortcuts import render, redirect, get_object_or_404
# login_required: É um "cadeado". Se o usuário não estiver logado, não deixa acessar a função e manda pra tela de login.
from django.contrib.auth.decorators import login_required
# São importadas as classes que criamos no models.py (Vehicle, Maintenance e ServiceItem) para manipular os dados do banco de dados.
from .models import User, Vehicle, Maintenance, ServiceItem, Workshop, Notification
# São importados os formulários que criados no forms.py para manipular os dados do usuário.
from .forms import VehicleForm, CustomUserCreationForm, MaintenanceForm, FinishMaintenanceForm, VistoriaForm
from django.contrib.auth import login # Ferramenta para forçar o login automático após o cadastro
from django.utils import timezone # Ferramenta para pegar a data e hora exata de "agora"
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import update_session_auth_hash # Ferramenta para atualizar a sessão do usuário após alterar a senha, evitando que ele seja desconectado
from django.core.paginator import Paginator # Ferramenta para dividir listas grandes em várias páginas, evitando sobrecarga de dados na tela
from django.contrib import messages # Ferramenta para enviar mensagens de sucesso ou erro para o usuário, que aparecem na tela após uma ação

# 1. PAINEL PRINCIPAL (Página home)
@login_required(login_url='login')
def home(request):
    # O Django verifica quem é o usuário logado (request.user) e qual o cargo dele (role)
    
    # ROTA DO MECÂNICO
    if request.user.role == 'MECANICO':
        erro = None
        
        # Se o mecânico digitou um código e clicou em "Vincular"
        if request.method == 'POST' and 'codigo_convite' in request.POST:
            codigo_digitado = request.POST.get('codigo_convite')
            # Procura no banco de dados se existe uma Oficina (Workshop) com esse exato código
            oficina_encontrada = Workshop.objects.filter(codigo_convite=codigo_digitado).first()
            
            if oficina_encontrada:
                # Se achou, vincula o mecânico a ela e salva!
                request.user.oficina_vinculada = oficina_encontrada
                request.user.save()
                return redirect('home')
            else:
                erro = "Código inválido. Verifique com o dono da oficina e tente novamente."

        # Busca as O.S que ninguém pegou ainda, mas apenas da oficina que o mecânico está vinculado
        fila_de_espera = Maintenance.objects.filter(oficina=request.user.oficina_vinculada, status='PENDENTE').order_by('-criado_em')
        paginator_fila = Paginator(fila_de_espera, 5)
        page_fila = request.GET.get('page_fila')
        solicitacoes_paginadas = paginator_fila.get_page(page_fila)
        
        # Busca as O.S que ESTE mecânico assumiu
        meus_servicos = Maintenance.objects.filter(mecanico=request.user, status__in=['ACEITA', 'ANDAMENTO']).order_by('-criado_em')
        paginator_servicos = Paginator(meus_servicos, 5)
        page_servicos = request.GET.get('page_servicos')
        servicos_paginados = paginator_servicos.get_page(page_servicos)
        # Busca os cancelamentos solicitados ou rejeitados pelo mecânico
        meus_cancelamentos = Maintenance.objects.filter(mecanico=request.user, status__in=['CANCELAMENTO_SOLICITADO', 'CANCELAMENTO_REJEITADO']).order_by('-criado_em')

        # Notificações - Ordenando das mais recentes para as mais antigas
        todas_notificacoes = Notification.objects.filter(usuario=request.user).order_by('-criado_em')
        notificacoes_nao_lidas = todas_notificacoes.filter(lida=False).count()
        minhas_notificacoes = todas_notificacoes[:15] # Limita a apenas as 15 mais recentes para enviar pro HTML
        mostrar_popup = (notificacoes_nao_lidas > 0) # Só mostra o popup se houver mensagens não lidas E se for a primeira vez que a página carrega sem nenhuma aba específica selecionada (sinal de que acabou de fazer login)

        # 'contexto' é o pacote de dados que enviamos do Python para o HTML
        contexto = {
            'solicitacoes': solicitacoes_paginadas, # Lista de solicitações de manutenção da oficina do mecânico logado, para mostrar na aba de fila de espera
            'meus_servicos': servicos_paginados, # Lista de serviços que o mecânico logado assumiu, para mostrar na aba de meus serviços
            'erro': erro, # Mensagem de erro, se houver
            'notificacoes': minhas_notificacoes, # Envia a lista de notificações para a aba de notificações
            'notificacoes_nao_lidas': notificacoes_nao_lidas, # Envia a contagem de notificações não lidas para o HTML, para mostrar no ícone de sino
            'mostrar_popup': mostrar_popup, # Indica se o popup de notificações deve ser mostrado ou não
            'meus_cancelamentos': meus_cancelamentos, # Lista de cancelamentos solicitados ou rejeitados pelo mecânico logado
        }
        return render(request, 'mechanic_dashboard.html', contexto)

    # ROTA DO DONO - Se for Dono, direciona para a visão gerencial
    elif request.user.role == 'DONO':
        
        # Se o dono preencheu o formulário do pop-up "Nova Oficina"
        if request.method == 'POST':
            nome = request.POST.get('nome')
            endereco = request.POST.get('endereco')
            descricao = request.POST.get('descricao')
            
            if nome:
                Workshop.objects.create(
                    dono=request.user,
                    nome=nome,
                    endereco=endereco,
                    descricao=descricao
                )
                # Recarrega a página mantendo a aba de oficinas aberta
                return redirect('/?tab=oficinas')

        # Busca todas as oficinas que pertencem a este dono
        minhas_oficinas = Workshop.objects.filter(dono=request.user)
        
        # --- CONTAGEM DE KPIs ---
        # 1. Filtra as manutenções do dono, EXCLUINDO as que estão na Sala de Espera do Cliente
        manutencoes_do_dono = Maintenance.objects.filter(oficina__in=minhas_oficinas).exclude(status='AGUARDANDO_VAGA').order_by('-criado_em')
        # 2. Conta os Pendentes (status PENDENTE)
        total_pendentes = manutencoes_do_dono.filter(status='PENDENTE').count()
        # 3. Conta os Em Andamento (incluindo ACEITA, AGUARDANDO_APROVACAO e ANDAMENTO)
        total_andamento = manutencoes_do_dono.filter(status__in=['ACEITA', 'AGUARDANDO_APROVACAO', 'ANDAMENTO']).count()
        # 4. Conta os Concluídos (status CONCLUIDO)
        total_concluidos = manutencoes_do_dono.filter(status='CONCLUIDO').count()

        # --- FILA DE ESPERA EXTERNA (LOTAÇÃO) ---
        fila_espera_externa = Maintenance.objects.filter(oficina__in=minhas_oficinas, status='AGUARDANDO_VAGA').order_by('-criado_em')
        total_espera_externa = fila_espera_externa.count()

        placa_buscada = request.GET.get('placa_busca', '').strip().upper() # Pega a placa digitada na barra de busca, remove espaços e deixa maiúscula
        veiculo_encontrado = None
        busca_realizada = False
        cancelamentos_pendentes = manutencoes_do_dono.filter(status='CANCELAMENTO_SOLICITADO')

        if placa_buscada:
            busca_realizada = True
            # Busca o veículo com a placa exata, mas apenas se ele tiver manutenções em alguma das oficinas do dono
            veiculo_encontrado = Vehicle.objects.filter(placa=placa_buscada, manutencoes__oficina__in=minhas_oficinas).distinct().first()

        # ABA VEÍCULOS: Lista todos os veículos que tiveram manutenções em alguma das oficinas do dono
        meus_veiculos = Vehicle.objects.filter(manutencoes__oficina__in=minhas_oficinas).distinct()
        
        # --- (OFICINAS E VEÍCULOS) ---
        # Paginação das Oficinas (ex: 5 por página)
        paginator_oficinas = Paginator(minhas_oficinas, 5)
        page_oficinas = request.GET.get('page_oficinas')
        oficinas_paginadas = paginator_oficinas.get_page(page_oficinas)

        # Paginação dos Veículos (ex: 10 por página, pois ocupam menos espaço)
        paginator_veiculos = Paginator(meus_veiculos, 5)
        page_veiculos = request.GET.get('page_veiculos')
        veiculos_paginados = paginator_veiculos.get_page(page_veiculos)

        # Notificações - Ordenando das mais recentes para as mais antigas
        # 1. Primeiro pegamos TODAS as notificações
        todas_notificacoes = Notification.objects.filter(usuario=request.user).order_by('-criado_em')
        
        # 2. Contamos quantas não foram lidas
        notificacoes_nao_lidas = todas_notificacoes.filter(lida=False).count()
        
        # 3. Por fim, limitamos a apenas as 15 mais recentes para enviar pro HTML
        minhas_notificacoes = todas_notificacoes[:15]

        # Só mostra o popup se houver mensagens não lidas E se for a primeira vez que a página carrega sem nenhuma aba específica selecionada (sinal de que acabou de fazer login)
        mostrar_popup = (notificacoes_nao_lidas > 0)

        # --- NOVA LÓGICA DE PAGINAÇÃO (DE 10 EM 10) ---
        paginator = Paginator(manutencoes_do_dono, 5) # Corta as manutenções a cada 10 itens
        numero_pagina = request.GET.get('page') # Vê o número da página no URL
        solicitacoes_paginadas = paginator.get_page(numero_pagina)

        # 'contexto' é o pacote de dados que enviamos do Python para o HTML
        contexto = {
            'oficinas': oficinas_paginadas,
            'aba_ativa': request.GET.get('tab', 'oficinas'),
            'total_pendentes': total_pendentes, # Envia os Pendentes pro HTML
            'total_andamento': total_andamento, # Envia os Em Andamento pro HTML
            'total_concluidos': total_concluidos, # Envia os Concluídos pro HTML
            'solicitacoes': solicitacoes_paginadas, # Envia todas as solicitações de manutenção do dono para o HTML, para mostrar na aba de solicitações
            'placa_buscada': placa_buscada, # Envia a placa digitada para o HTML, para mostrar na barra de busca
            'veiculo_encontrado': veiculo_encontrado, # Envia o veículo encontrado para a aba de busca de placa
            'busca_realizada': busca_realizada, # Indica se o dono realizou uma busca de placa ou não
            'veiculos': veiculos_paginados, # Envia a lista de veículos para a aba de veículos
            'notificacoes': minhas_notificacoes, # Envia a lista de notificações para a aba de notificações
            'notificacoes_nao_lidas': notificacoes_nao_lidas, # Envia a contagem de notificações não lidas para o HTML, para mostrar no ícone de sino
            'mostrar_popup': mostrar_popup, # Indica se o popup de notificações deve ser mostrado ou não
            'cancelamentos_pendentes': cancelamentos_pendentes, # Lista de cancelamentos pendentes
            'paginator': paginator, # Envia o objeto de paginação para o HTML, para criar os links de navegação entre páginas
            'fila_espera_externa': fila_espera_externa, # Envia a lista de solicitações em espera externa para o HTML
            'total_espera_externa': total_espera_externa, # Envia a contagem de solicitações em espera externa para o HTML
        }
        return render(request, 'owner_dashboard.html', contexto)
        
    # ROTA DO CLIENTE (Proprietário de Veículo) - Se for Cliente, direciona para a visão do cliente
    else:
        # Pega apenas os carros que pertencem ao usuário que está acessando
        meus_carros = Vehicle.objects.filter(proprietario=request.user)
        
        # Busca o histórico de manutenções apenas dos VEÍCULOS desse cliente específico
        minhas_manutencoes = Maintenance.objects.filter(veiculo__proprietario=request.user).order_by('-criado_em')
        paginator_cliente = Paginator(minhas_manutencoes, 5)
        page_cliente = request.GET.get('page')
        manutencoes_paginadas = paginator_cliente.get_page(page_cliente)

        # --- CORREÇÃO: Busca as oficinas para enviar para o HTML do cliente ---
        oficinas_disponiveis = Workshop.objects.all().distinct()

        # Notificações - Ordenando das mais recentes para as mais antigas
        todas_notificacoes = Notification.objects.filter(usuario=request.user).order_by('-criado_em')
        notificacoes_nao_lidas = todas_notificacoes.filter(lida=False).count()
        minhas_notificacoes = todas_notificacoes[:15] # Limita a apenas as 15 mais recentes para enviar pro HTML
        mostrar_popup = (notificacoes_nao_lidas > 0) # Só mostra o popup se houver mensagens não lidas E se for a primeira vez que a página carrega sem nenhuma aba específica selecionada (sinal de que acabou de fazer login)
        
        contexto = {
            'carros_para_tela': meus_carros,
            'manutencoes_para_tela': manutencoes_paginadas, # Envia as manutenções para a tela do cliente, paginadas
            'oficinas_para_tela': oficinas_disponiveis, # Envia as oficinas para o menu de seleção!
            'notificacoes': minhas_notificacoes,
            'notificacoes_nao_lidas': notificacoes_nao_lidas,
            'mostrar_popup': mostrar_popup
        }
        return render(request, 'home.html', contexto)

# ==============================================================================
# ATUALIZAR PERFIL DO USUÁRIO
# ==============================================================================
@login_required
def atualizar_perfil(request):
    if request.method == 'POST':
        user = request.user
        
        # Atualiza os dados básicos
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.email = request.POST.get('email', user.email)
        
        # Campo Telefone no User model
        if hasattr(user, 'telefone'):
            user.telefone = request.POST.get('telefone', user.telefone)
            
        # Verifica se o usuário digitou uma nova senha. Se sim, atualiza a senha e mantém o usuário logado.
        nova_senha = request.POST.get('nova_senha')
        if nova_senha:
            user.set_password(nova_senha)
            # Mantém o usuário logado após mudar a senha
            update_session_auth_hash(request, user)
            
        user.save()
        
    # Redireciona de volta para a página de onde a pessoa veio
    return redirect(request.META.get('HTTP_REFERER', 'home'))

# ==============================================================================
# CRUD DE VEÍCULOS (Criar, Editar, Excluir)
# ==============================================================================

# ADICIONAR CARRO
@login_required(login_url='login')
def add_vehicle(request):
    # 'POST' significa que o usuário clicou no botão de enviar o formulário
    if request.method == 'POST':
        form = VehicleForm(request.POST) # Preenche o formulário com os dados digitados
        
        if form.is_valid(): # Verifica se não tem dados bizarros (ex: letras na quilometragem)
            novo_carro = form.save(commit=False) # commit=False: "Espera! Não salva no banco ainda!"
            novo_carro.proprietario = request.user # Injeta o usuário logado como dono do carro, por segurança
            novo_carro.save() # "Agora sim, guarda no banco de dados
            
            return redirect('home') # Joga o usuário de volta para o ecrã inicial
            
    # 'GET': O usuário apenas abriu a página para ver o formulário
    else:
        form = VehicleForm() # Cria um formulário completamente vazio
        
    contexto = {
        'form': form
    }
    return render(request, 'add_vehicle.html', contexto)

# EDITAR CARRO
@login_required(login_url='login')
def edit_vehicle(request, id):
    # Busca o carro pelo ID. O filtro "proprietario=request.user" impede que um cliente 
    # espertinho digite o ID do carro de outra pessoa na URL e consiga editar.
    carro = get_object_or_404(Vehicle, id=id, proprietario=request.user)
    
    if request.method == 'POST':
        # instance=carro: "Pegue os dados novos e jogue POR CIMA deste carro específico"
        form = VehicleForm(request.POST, instance=carro)
        if form.is_valid():
            form.save() # Como o 'instance' existe, ele não cria um novo, ele sobreescreve.
            return redirect('home')
    else:
        # Preenche as caixinhas da tela com os dados atuais do carro
        form = VehicleForm(instance=carro)
        
    contexto = {'form': form, 'carro': carro}
    return render(request, 'edit_vehicle.html', contexto)

# EXCLUIR CARRO
@login_required(login_url='login')
def delete_vehicle(request, id):
    # Mesma trava de segurança: só exclui se o carro for do usuário logado
    carro = get_object_or_404(Vehicle, id=id, proprietario=request.user)
    
    if request.method == 'POST':
        carro.delete() # Exclui do banco de dados
        return redirect('home')
        
    contexto = {'carro': carro}
    return render(request, 'delete_vehicle.html', contexto)

# ==============================================================================
# AUTENTICAÇÃO E CADASTROS NOVOS
# ==============================================================================
def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST) # Tenta criar com os dados digitados
        if form.is_valid():
            user = form.save() # Salva o novo usuário no banco com senha criptografada (o Django já faz isso natualmente)
            login(request, user) # Já faz o login automático ao finalizar o cadastro (sem precisar digitar login e senha)
            return redirect('home') # Redireciona para a página inicial após o cadastro
    else:
        form = CustomUserCreationForm() # Entrega o formulário vazio para o visitante
        
    contexto = {'form': form}
    return render(request, 'register.html', contexto)

# ==============================================================================
# FLUXO DE MANUTENÇÃO
# ==============================================================================

# CLIENTE SOLICITA SERVIÇO
@login_required(login_url='login')
def request_maintenance(request):
    if request.method == 'POST':
        # Passamos o usuário logado para que o formulário só mostre os veículos DELE na caixinha de seleção
        form = MaintenanceForm(request.POST, user=request.user)
        
        if form.is_valid():
            nova_manutencao = form.save(commit=False)
            
            # --- NOVA LÓGICA DE FILA DE ESPERA (MOTOR DE CAPACIDADE) ---
            
            # CORREÇÃO: Captura a oficina DIRETAMENTE do que o cliente selecionou no HTML
            oficina_id = request.POST.get('oficina')
            if oficina_id:
                from .models import Workshop # Garante que o modelo Workshop está acessível
                nova_manutencao.oficina = Workshop.objects.filter(id=oficina_id).first()
                
            # Verifica se o cliente escolheu uma oficina específica no formulário
            oficina_escolhida = nova_manutencao.oficina
            
            if oficina_escolhida:
                # Conta quantas Ordens de Serviço (O.S) ativas esta oficina já tem
                os_ativas = Maintenance.objects.filter(
                    oficina=oficina_escolhida,
                    status__in=['PENDENTE', 'AGUARDANDO_APROVACAO', 'ACEITA', 'ANDAMENTO']
                ).count()
                
                # Compara a quantidade de O.S ativas com o limite global da oficina
                if os_ativas >= oficina_escolhida.limite_servicos_global:
                    # Oficina lotada! Altera o status para a Sala de Espera em vez de rejeitar
                    nova_manutencao.status = 'AGUARDANDO_VAGA'
                    dias = oficina_escolhida.dias_espera_lotacao
                    
                    # Cria a mensagem de aviso (amarela) para o cliente ver no painel dele
                    messages.warning(request, f'⚠️ A oficina {oficina_escolhida.nome} está com lotação máxima. O seu pedido foi salvo na fila de espera! Previsão para novas vagas: {dias} dias.')
                else:
                    # Oficina tem vaga. O status já nasce como 'PENDENTE' (definido lá no models.py como default)
                    nova_manutencao.status = 'PENDENTE'
                    # Cria a mensagem de sucesso (verde)
                    messages.success(request, 'Solicitação enviada com sucesso para a oficina!')
            else:
                # Caso a O.S seja criada sem oficina atrelada por algum motivo
                # O status já nasce como 'PENDENTE' (definido lá no models.py como default)
                nova_manutencao.status = 'PENDENTE'
                messages.success(request, 'Solicitação criada com sucesso!')
            
            nova_manutencao.save()
            return redirect('home')
    else:
        form = MaintenanceForm(user=request.user)
        
    contexto = {'form': form}
    return render(request, 'request_maintenance.html', contexto)

# ATENDIMENTO NO BALCÃO (OFICINA REGISTRA MANUTENÇÃO)
@login_required(login_url='login')
def atendimento_balcao(request):
    if request.method == 'POST':
        oficina_atual = None # Identifica de qual oficina está vindo o pedido
        if request.user.role == 'DONO':
            oficina_atual = request.user.oficinas_gerenciadas.first() # Pega a primeira oficina que o dono gerencia
        elif request.user.role == 'MECANICO':
            oficina_atual = request.user.oficina_vinculada # Pega a oficina que o mecânico está vinculado
            
        if not oficina_atual:
            return redirect('home') # Se por algum motivo não tiver oficina, aborta a missão

        # --- VERIFICAÇÃO DE LOTAÇÃO (MOTOR DE CAPACIDADE) ---
        # Conta as Ordens de Serviço ativas nesta oficina específica
        os_ativas = Maintenance.objects.filter(
            oficina=oficina_atual, 
            status__in=['PENDENTE', 'AGUARDANDO_APROVACAO', 'ACEITA', 'ANDAMENTO']
        ).count()
        
        # Se a oficina atingiu ou passou do limite global, exibe o erro e bloqueia a criação
        if os_ativas >= oficina_atual.limite_servicos_global:
            messages.error(request, f'⚠️ Lotação Atingida! A oficina já atingiu o limite máximo de {oficina_atual.limite_servicos_global} serviços em andamento.')
            return redirect('home')

        # Coleta os dados do formulário HTML que forem preenchidos na oficina
        nome_cliente = request.POST.get('nome_cliente')
        email_cliente = request.POST.get('email_cliente')
        telefone_cliente = request.POST.get('telefone_cliente')

        placa = request.POST.get('placa').upper() # Garante que a placa fique maiúscula
        marca = request.POST.get('marca')
        modelo = request.POST.get('modelo')
        ano = request.POST.get('ano', 2020) # 2020 como padrão se não preencherem
        descricao_problema = request.POST.get('descricao_problema')
        tipo_servico = request.POST.get('tipo', 'CORRETIVA') # Corretiva por padrão

        # --- O CLIENTE (SILENT ONBOARDING) ---
        cliente = User.objects.filter(email=email_cliente).first()
        
        if not cliente:
            # Se o e-mail não existe, cria a conta do cliente silenciosamente
            # O Django vai usar o e-mail como login e a placa do carro como senha inicial
            cliente = User.objects.create_user(
                username=email_cliente, 
                email=email_cliente,
                password=placa, 
                first_name=nome_cliente,
                telefone=telefone_cliente,
                role='CLIENTE'
            )

        # --- O VEÍCULO ---
        veiculo = Vehicle.objects.filter(placa=placa).first()
        
        if not veiculo:
            # Cria o carro e já vincula ao proprietário (cliente) que foi criado anteriormente
            veiculo = Vehicle.objects.create(
                placa=placa,
                marca=marca,
                modelo=modelo,
                ano=ano,
                proprietario=cliente
            )

        # --- A ORDEM DE SERVIÇO ---
        # Abre o chamado já amarrado à oficina exata de quem registrou!
        Maintenance.objects.create(
            veiculo=veiculo,
            oficina=oficina_atual,
            descricao_problema=descricao_problema,
            tipo=tipo_servico,
            status='PENDENTE' # Cai direto na fila de espera desta oficina
        )

        # Volta para a página inicial (que vai recarregar o dashboard do Dono ou Mecânico atualizado)
        return redirect('home')
        
    return redirect('home')

# ABRIR O.S PARA VEÍCULO JÁ EXISTENTE (Aba Buscar Placa)
@login_required(login_url='login')
def nova_os_existente(request, veiculo_id):
    if request.method == 'POST':
        # Confirma que o carro existe
        veiculo = get_object_or_404(Vehicle, id=veiculo_id)
        
        # Pega a oficina da Dona
        oficina_atual = None
        if request.user.role == 'DONO':
            oficina_atual = request.user.oficinas_gerenciadas.first()
            
        if oficina_atual:
            descricao_problema = request.POST.get('descricao_problema')
            
            # Abre a OS direto, pulando a criação de cliente e veículo
            Maintenance.objects.create(
                veiculo=veiculo,
                oficina=oficina_atual,
                descricao_problema=descricao_problema,
                tipo='CORRETIVA', # Corretiva por padrão na recepção
                status='PENDENTE'
            )
            
        # Redireciona de volta com a aba de Solicitações aberta para ela ver o pedido lá
        return redirect('/?tab=solicitacoes')
    return redirect('home')

# AÇÕES DA SALA DE ESPERA DO CLIENTE
@login_required
def reenviar_os_cliente(request, id):
    manutencao = get_object_or_404(Maintenance, id=id, veiculo__proprietario=request.user)
    
    if request.method == 'POST' and manutencao.status == 'AGUARDANDO_VAGA':
        oficina = manutencao.oficina
        if oficina:
            os_ativas = Maintenance.objects.filter(
                oficina=oficina, status__in=['PENDENTE', 'AGUARDANDO_APROVACAO', 'ACEITA', 'ANDAMENTO']
            ).count()
            
            if os_ativas >= oficina.limite_servicos_global:
                messages.warning(request, f'⚠️ A oficina {oficina.nome} continua lotada. Tente novamente mais tarde.')
            else:
                manutencao.status = 'PENDENTE'
                manutencao.save()
                messages.success(request, 'Vaga disponível! Solicitação enviada para a oficina com sucesso.')
                
    return redirect('home')

@login_required
def cancelar_os_cliente(request, id):
    manutencao = get_object_or_404(Maintenance, id=id, veiculo__proprietario=request.user)
    if request.method == 'POST' and manutencao.status == 'AGUARDANDO_VAGA':
        manutencao.delete() # Apaga do banco para não sujar o histórico
        messages.success(request, 'Solicitação cancelada com sucesso.')
    return redirect('home')

# MECÂNICO ACEITAR O SERVIÇO
@login_required
def accept_maintenance(request, id):
    if request.method == 'POST':
        manutencao = get_object_or_404(Maintenance, id=id)
        
        # --- VERIFICAÇÃO DO LIMITE DO MECÂNICO (MOTOR DE CAPACIDADE) ---
        # Identifica a oficina da O.S ou a oficina do mecânico
        oficina_atual = manutencao.oficina or getattr(request.user, 'oficina_vinculada', None)
        
        if oficina_atual:
            # Conta quantas O.S o mecânico logado já tem em mãos
            os_ativas_mecanico = Maintenance.objects.filter(
                mecanico=request.user,
                status__in=['ACEITA', 'AGUARDANDO_APROVACAO', 'ANDAMENTO']
            ).count()
            
            # Se atingiu o limite que o Dono configurou, bloqueia e avisa
            if os_ativas_mecanico >= oficina_atual.limite_por_mecanico:
                messages.error(request, f'⚠️ Limite de Trabalho Atingido! Você não pode pegar mais de {oficina_atual.limite_por_mecanico} serviços simultâneos. Conclua algum para liberar espaço.')
                return redirect('home')
        
        # 1. Atualiza os dados da manutenção
        manutencao.mecanico = request.user
        manutencao.status = 'ACEITA'
        
        # 2. Garante que a manutenção pertence à oficina do mecânico
        if not manutencao.oficina and hasattr(request.user, 'oficina_vinculada') and request.user.oficina_vinculada:
            manutencao.oficina = request.user.oficina_vinculada
            
        manutencao.save()
        
        # 3. Notifica o Cliente
        Notification.objects.create(
            usuario=manutencao.veiculo.proprietario,
            mensagem=f"O mecânico {request.user.first_name} iniciou o atendimento do seu {manutencao.veiculo.modelo}."
        )

        # 4. Notifica o Dono (Apenas se a oficina e o dono existirem
        if manutencao.oficina and hasattr(manutencao.oficina, 'dono') and manutencao.oficina.dono:
            Notification.objects.create(
                usuario=manutencao.oficina.dono,
                mensagem=f"O mecânico {request.user.first_name} aceitou o serviço do veículo {manutencao.veiculo.placa}."
            )
            
    # Redireciona de volta para o painel do mecânico
    return redirect('home')

# FUNÇÃO PARA O MECÂNICO ENVIAR A VISTORIA E O ORÇAMENTO
@login_required(login_url='login')
def realizar_vistoria(request, id):
    manutencao = get_object_or_404(Maintenance, id=id, mecanico=request.user, status='ACEITA')
    
    if request.method == 'POST':
        form = VistoriaForm(request.POST, instance=manutencao)
        if form.is_valid():
            vistoria = form.save(commit=False)
            # Pega todos os links enviados, remove os vazios e junta com vírgula
            links_imagens = request.POST.getlist('link_imagem[]')
            links_limpos = [link for link in links_imagens if link.strip()]
            vistoria.imagens_evidencia = ", ".join(links_limpos)
            vistoria.save() # Salva o laudo principal
            
            # Tratamento das Peças e Serviços Dinâmicos
            descricoes = request.POST.getlist('descricao[]')
            precos = request.POST.getlist('preco[]')
            tipos = request.POST.getlist('tipo_item[]') 
            quantidades = request.POST.getlist('quantidade[]') # Pega a lista de quantidades
            
            valor_total = 0
            vistoria.itens_servico.all().delete() 
            
            # O zip agora inclui a lista de 'quantidades'
            for desc, preco, tipo, quant in zip(descricoes, precos, tipos, quantidades):
                if desc and preco:
                    preco_float = float(preco)
                    
                    # Garante que a quantidade é um número inteiro (se vier vazio ou com erro, força 1)
                    try:
                        quant_int = int(quant)
                    except (ValueError, TypeError):
                        quant_int = 1
                        
                    is_obrig = (tipo == 'MAO_DE_OBRA') 

                    ServiceItem.objects.create(
                        manutencao=vistoria,
                        descricao=desc,
                        quantidade=quant_int, # Guarda a quantidade no banco de dados
                        preco=preco_float,    # Guarda o Valor Unitário
                        obrigatorio=is_obrig,
                        aprovado=True 
                    )
                    
                    # Multiplica a quantidade pelo valor unitário para somar ao total da OS
                    valor_total += (preco_float * quant_int) 
            
            vistoria.valor = valor_total 
            vistoria.status = 'AGUARDANDO_APROVACAO' 
            vistoria.save()

            # Notifica o Cliente sobre o Orçamento (Apenas após salvar o formulário!)
            Notification.objects.create(
                usuario=manutencao.veiculo.proprietario,
                mensagem=f"Orçamento disponível! O mecânico {request.user.first_name} enviou a vistoria do seu {manutencao.veiculo.modelo} para aprovação."
            )
            
            return redirect('home')
            
    else:
        form = VistoriaForm(instance=manutencao) 
        
    contexto = {'form': form, 'manutencao': manutencao}
    return render(request, 'realizar_vistoria.html', contexto)

# CLIENTE APROVA O ORÇAMENTO PARCIAL OU TOTAL
@login_required(login_url='login')
def aprovar_vistoria(request, id):
    # Busca a O.S, mas garante que o dono do carro seja quem está logado
    manutencao = get_object_or_404(Maintenance, id=id, veiculo__proprietario=request.user, status='AGUARDANDO_APROVACAO')
    
    if request.method == 'POST':
        # Pega do HTML uma lista com os IDs das peças que o cliente DEIXOU marcadas
        itens_aprovados_ids = request.POST.getlist('itens_aprovados')
        valor_final = 0
        
        # Percorre todos os itens daquele orçamento
        for item in manutencao.itens_servico.all():
            # A Mão de Obra é sempre aprovada; as peças só se estiverem na lista do POST
            # Convertemos o item.id para string (str) porque o HTML sempre envia textos nas listas
            if item.obrigatorio or str(item.id) in itens_aprovados_ids:
                item.aprovado = True
                # NOVO: Multiplica o valor unitário pela quantidade da peça
                valor_final += (item.preco * item.quantidade)
            else:
                item.aprovado = False
            item.save()
            
        manutencao.valor = valor_final # Atualiza o valor final da manutenção apenas com o que foi aprovado
        manutencao.status = 'ANDAMENTO' # Devolve a bola para o mecânico
        manutencao.save()

        Notification.objects.create(
            usuario=manutencao.mecanico,
            mensagem=f"Serviço aprovado! O cliente autorizou o orçamento para o {manutencao.veiculo.modelo} ({manutencao.veiculo.placa})."
        )
        
    return redirect('home')

# CLIENTE RECUSA TUDO
@login_required(login_url='login')
def recusar_vistoria(request, id):
    manutencao = get_object_or_404(Maintenance, id=id, veiculo__proprietario=request.user, status='AGUARDANDO_APROVACAO')
    
    if request.method == 'POST':
        manutencao.status = 'RECUSADA' # Cliente deu o sinal vermelho para tudo!
        manutencao.save()

        Notification.objects.create( 
            usuario=manutencao.mecanico,
            mensagem=f"Serviço recusado! O cliente não autorizou o orçamento para o {manutencao.veiculo.modelo} ({manutencao.veiculo.placa})."
        )
        
    return redirect('home')

# MECÂNICO FINALIZA O SERVIÇO
@login_required(login_url='login')
def finish_maintenance(request, id):
    manutencao = get_object_or_404(Maintenance, id=id, mecanico=request.user, status='ANDAMENTO')
    
    # SALVAMOS O VALOR ATUAL ANTES DE MEXER NO FORMULÁRIO.
    # Isso resolve um bug onde o salvamento de algumas versões do formulário sobreescrevia o valor para 'None'.
    valor_correto = manutencao.valor
    
    if request.method == 'POST':
        form = FinishMaintenanceForm(request.POST, instance=manutencao)
        
        if form.is_valid():
            servico_concluido = form.save(commit=False)
            servico_concluido.status = 'CONCLUIDO' # Encerra o ciclo
            
            # Devolvemos o valor exato para o banco de dados para não ser apagado
            servico_concluido.valor = valor_correto 
            servico_concluido.save()

            Notification.objects.create(
                usuario=manutencao.veiculo.proprietario,
                mensagem=f"Serviço concluído! O mecânico finalizou o atendimento do seu {manutencao.veiculo.modelo} ({manutencao.veiculo.placa})."
            )            
            return redirect('home')
    else:
        form = FinishMaintenanceForm(instance=manutencao)
        
    contexto = {
        'form': form, 
        'manutencao': manutencao,
        'itens_aprovados': manutencao.itens_servico.filter(aprovado=True) # Manda pro HTML só o que o cliente quis, para gerar a nota fiscal limpa
    }
    return render(request, 'finish_maintenance.html', contexto)

# ==============================================================================
# FLUXO DE CANCELAMENTO DE O.S.
# ==============================================================================

# MECÂNICO SOLICITA CANCELAMENTO
@login_required(login_url='login')
def solicitar_cancelamento(request, id):
    if request.method == 'POST':
        manutencao = get_object_or_404(Maintenance, id=id)
        motivo = request.POST.get('motivo_cancelamento')
        
        manutencao.status = 'CANCELAMENTO_SOLICITADO'
        manutencao.motivo_cancelamento_mec = motivo
        
        # Garante que o mecânico não perca o acesso à O.S
        if not manutencao.mecanico:
            manutencao.mecanico = request.user
            
        # CORREÇÃO: Se a O.S veio direto do cliente e não tem oficina, vincula à oficina deste mecânico agora!
        if not manutencao.oficina and hasattr(request.user, 'oficina_vinculada') and request.user.oficina_vinculada:
            manutencao.oficina = request.user.oficina_vinculada
            
        manutencao.save()
        
        # Notifica o Administrador
        if manutencao.oficina and hasattr(manutencao.oficina, 'dono'):
            Notification.objects.create(
                usuario=manutencao.oficina.dono,
                mensagem=f"Cancelamento Solicitado! O mecânico {request.user.first_name} pediu para cancelar a O.S do veículo {manutencao.veiculo.placa}."
            )
            
        # Notifica o Cliente
        Notification.objects.create(
            usuario=manutencao.veiculo.proprietario,
            mensagem=f"Aviso: O mecânico solicitou o cancelamento da ordem de serviço do seu {manutencao.veiculo.modelo}."
        )
            
    return redirect('home')

# ADMIN APROVA CANCELAMENTO (Exclui/Cancela de vez)
@login_required(login_url='login')
def aprovar_cancelamento(request, id):
    if request.method == 'POST':
        manutencao = get_object_or_404(Maintenance, id=id)
        manutencao.status = 'CANCELADO'
        manutencao.save()
        
        if manutencao.mecanico:
            Notification.objects.create(
                usuario=manutencao.mecanico,
                mensagem=f"Cancelamento Aprovado. A O.S do veículo {manutencao.veiculo.placa} foi cancelada definitivamente."
            )
            
        # Notifica o Cliente
        Notification.objects.create(
            usuario=manutencao.veiculo.proprietario,
            mensagem=f"Cancelado: A solicitação de serviço do seu {manutencao.veiculo.modelo} foi cancelada pelo administrador da oficina."
        )
            
    return redirect('/?tab=solicitacoes') # Redireciona para a aba de solicitações do Dono

# ADMIN RECUSA CANCELAMENTO (Devolve para o Mecânico)
@login_required(login_url='login')
def recusar_cancelamento(request, id):
    if request.method == 'POST':
        manutencao = get_object_or_404(Maintenance, id=id)
        motivo_admin = request.POST.get('motivo_recusa')
        
        manutencao.status = 'CANCELAMENTO_REJEITADO'
        manutencao.motivo_recusa_admin = motivo_admin
        manutencao.save()
        
        if manutencao.mecanico:
            Notification.objects.create(
                usuario=manutencao.mecanico,
                mensagem=f"Cancelamento Negado! O Administrador recusou o cancelamento da O.S do veículo {manutencao.veiculo.placa}."
            )
            
        # Notifica o Cliente de que o processo retomou
        Notification.objects.create(
            usuario=manutencao.veiculo.proprietario,
            mensagem=f"Atualização: O cancelamento do seu {manutencao.veiculo.modelo} não prosseguiu. O mecânico dará continuidade."
        )
            
    return redirect('/?tab=solicitacoes')

# MECÂNICO DEVOLVE O.S PARA A FILA DE ESPERA (Após recusa do admin)
@login_required(login_url='login')
def devolver_a_fila(request, id):
    if request.method == 'POST':
        manutencao = get_object_or_404(Maintenance, id=id)
        manutencao.status = 'PENDENTE'
        manutencao.mecanico = None # Remove o mecânico atual, libertando a O.S para outros
        manutencao.motivo_cancelamento_mec = None
        manutencao.motivo_recusa_admin = None
        manutencao.save()
        
    return redirect('home')

# NOTIFICAÇÕES: MARCAR TODAS COMO LIDAS (Chamado via AJAX pelo JavaScript)
@login_required
@csrf_exempt # Permite que o JavaScript chame a função sem problemas
def marcar_notificacoes_lidas(request):
    if request.method == 'POST':
        # Atualiza todas as notificações não lidas do usuário para lidas
        Notification.objects.filter(usuario=request.user, lida=False).update(lida=True)
        return JsonResponse({'status': 'sucesso'})
    return JsonResponse({'status': 'erro'}, status=400)

# ==============================================================================
# CONFIGURAÇÃO DE LIMITES DE O.S. POR OFICINA
# ==============================================================================
@login_required
def configurar_limites_oficina(request, oficina_id):
    if request.method == 'POST' and request.user.role == 'DONO':
        # Procura a oficina garantindo que ela pertence ao dono logado
        oficina = get_object_or_404(Workshop, id=oficina_id, dono=request.user)
        
        # Captura os novos valores digitados
        novo_limite_global = request.POST.get('limite_global')
        novo_limite_mecanico = request.POST.get('limite_mecanico')
        novo_dias_espera = request.POST.get('dias_espera')
        
        if novo_limite_global and novo_limite_mecanico:
            oficina.limite_servicos_global = int(novo_limite_global)
            oficina.limite_por_mecanico = int(novo_limite_mecanico)
            oficina.dias_espera_lotacao = int(novo_dias_espera)
            oficina.save()
            
    # Volta para o painel mantendo a aba de oficinas aberta
    return redirect('/?tab=oficinas')