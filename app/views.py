from django.shortcuts import render, redirect, get_object_or_404 # 1. Adicionamos o 'redirect' e 'get_object_or_404' aqui
from django.contrib.auth.decorators import login_required
from .models import Vehicle, Maintenance, ServiceItem
from .forms import VehicleForm, CustomUserCreationForm, MaintenanceForm, FinishMaintenanceForm, VistoriaForm  # 2. Importamos o nosso novo formulário
from django.contrib.auth import login # 3. Ferramenta para auto-login
from django.utils import timezone # 4. Para registrar a data e hora do aceite do serviço

@login_required(login_url='login')
def home(request):
    # 1. Se for Mecânico, direciona para o painel de serviços
    if request.user.role == 'MECANICO':
        # Busca a fila de espera com o novo status
        fila_de_espera = Maintenance.objects.filter(status='PENDENTE').order_by('-criado_em')
        
        # Busca os serviços que o mecânico assumiu (tanto os apenas aceitos quanto os já em andamento)
        meus_servicos = Maintenance.objects.filter(mecanico=request.user, status__in=['ACEITA', 'ANDAMENTO']).order_by('-criado_em')

        contexto = {
            'solicitacoes': fila_de_espera, # Lista de solicitações de manutenção aguardando atendimento, para mostrar no painel
            'meus_servicos': meus_servicos # Lista de serviços do mecânico logado, para mostrar no painel
        }
        return render(request, 'mechanic_dashboard.html', contexto)

    # 2. Se for Dono, direciona para a visão gerencial
    elif request.user.role == 'DONO':
        return render(request, 'owner_dashboard.html')
        
    # 3. Se for Cliente (Padrão), carrega a garagem que já construímos
    else:
        meus_carros = Vehicle.objects.filter(proprietario=request.user)
        
        # Busca as manutenções dos carros deste dono, da mais nova para a mais velha
        minhas_manutencoes = Maintenance.objects.filter(veiculo__proprietario=request.user).order_by('-criado_em')
        
        contexto = {
            'carros_para_tela': meus_carros,
            'manutencoes_para_tela': minhas_manutencoes # Enviamos a lista para o HTML
        }
        return render(request, 'home.html', contexto)

# 4. FUNÇÃO PARA ADICIONAR CARROS
@login_required(login_url='login')
def add_vehicle(request):
    # Se o usuário clicou no botão "Salvar" (Enviou dados)
    if request.method == 'POST':
        form = VehicleForm(request.POST) # Preenche o formulário com os dados digitados
        
        if form.is_valid(): # O Django verifica se as regras (ex: tamanho da placa) foram respeitadas
            novo_carro = form.save(commit=False) # Pausa! Cria o carro, mas NÃO guarda ainda
            novo_carro.proprietario = request.user # Injeta o usuário logado como dono do carro
            novo_carro.save() # Agora sim, guarda na base de dados definitivamente
            
            return redirect('home') # Arremessa o usuário de volta para o ecrã inicial
            
    # Se o usuário apenas abre à página (Ainda não digitou nada)
    else:
        form = VehicleForm() # Cria um formulário completamente vazio
        
    contexto = {
        'form': form
    }
    return render(request, 'add_vehicle.html', contexto)

# 5. FUNÇÃO PARA EDITAR CARROS
@login_required(login_url='login')
def edit_vehicle(request, id):
    # 4. Busca o carro exato pelo ID, MAS garante que pertence ao usuário logado
    carro = get_object_or_404(Vehicle, id=id, proprietario=request.user)
    
    if request.method == 'POST':
        form = VehicleForm(request.POST, instance=carro) # 5. instance=carro avisa: "Atualize os dados DENTRO deste carro existente"
        if form.is_valid():
            form.save() # Como o 'instance' existe, ele não cria um novo, ele sobreescreve.
            return redirect('home')
    else:
        # Preenche as caixinhas da tela com os dados atuais do carro
        form = VehicleForm(instance=carro)
        
    contexto = {'form': form, 'carro': carro}
    return render(request, 'edit_vehicle.html', contexto)

# 6. FUNÇÃO PARA EXCLUIR CARROS
@login_required(login_url='login')
def delete_vehicle(request, id):
    carro = get_object_or_404(Vehicle, id=id, proprietario=request.user)
    
    if request.method == 'POST':
        carro.delete() # Exclui do banco de dados
        return redirect('home')
        
    contexto = {'carro': carro}
    return render(request, 'delete_vehicle.html', contexto)

# 7. FUNÇÃO PARA CRIAR CADASTRO DE NOVOS USUÁRIOS
def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST) # Tenta criar com os dados digitados
        if form.is_valid():
            user = form.save() # Salva o novo usuário no banco com senha criptografada
            login(request, user) # Já faz o login automático para não irritar o client
            return redirect('home') # Redireciona para a página inicial após o cadastro
    else:
        form = CustomUserCreationForm() # Entrega o formulário vazio para o visitante
        
    contexto = {'form': form}
    return render(request, 'register.html', contexto)

# --- FUNÇÃO PARA O CLIENTE REGISTRAR UM PROBLEMA ---
@login_required(login_url='login')
def request_maintenance(request):
    if request.method == 'POST':
        # Passamos o request.user para o formulário saber de quem é a garagem
        form = MaintenanceForm(request.POST, user=request.user)
        
        if form.is_valid():
            nova_manutencao = form.save(commit=False)
            # Como configurado no models.py, o status já nasce como 'AGUARDANDO' automaticamente
            nova_manutencao.save()
            return redirect('home')
    else:
        form = MaintenanceForm(user=request.user)
        
    contexto = {'form': form}
    return render(request, 'request_maintenance.html', contexto)

# --- FUNÇÃO PARA O MECÂNICO ACEITAR O SERVIÇO ---
@login_required(login_url='login')
def accept_maintenance(request, id):
    # Garante que apenas mecânicos podem fazer isso e apenas via botão seguro (POST)
    if request.user.role == 'MECANICO' and request.method == 'POST':
        # Busca a ordem exata, mas APENAS se ela ainda estiver aguardando
        manutencao = get_object_or_404(Maintenance, id=id, status='PENDENTE')
        
        # 1. Atribui o mecânico logado como o responsável
        manutencao.mecanico = request.user
        
        # 2. Atualiza o status
        manutencao.status = 'ACEITA' # Agora o cliente sabe que alguém vai cuidar do carro
        
        # 3. Registra a data e hora do aceite
        manutencao.data_aceite = timezone.now()
        
        # 4. Salva no banco de dados
        manutencao.save()
        
    # Recarrega a página inicial (que vai remontar o painel atualizado)
    return redirect('home')

# --- FUNÇÃO PARA O MECÂNICO CONCLUIR O SERVIÇO ---
# --- FUNÇÃO ATUALIZADA PARA O MECÂNICO CONCLUIR O SERVIÇO (CORREÇÃO DO VALOR NONE) ---
@login_required(login_url='login')
def finish_maintenance(request, id):
    manutencao = get_object_or_404(Maintenance, id=id, mecanico=request.user, status='ANDAMENTO')
    
    # SALVAMOS O VALOR AQUI PARA O FORMULÁRIO NÃO APAGAR SEM QUERER
    valor_correto = manutencao.valor 
    
    if request.method == 'POST':
        form = FinishMaintenanceForm(request.POST, instance=manutencao)
        
        if form.is_valid():
            servico_concluido = form.save(commit=False)
            servico_concluido.status = 'CONCLUIDO'
            
            # Devolvemos o valor exato para o banco de dados!
            servico_concluido.valor = valor_correto 
            servico_concluido.save()
            
            return redirect('home')
    else:
        form = FinishMaintenanceForm(instance=manutencao)
        
    contexto = {
        'form': form, 
        'manutencao': manutencao,
        'itens_aprovados': manutencao.itens_servico.filter(aprovado=True)
    }
    return render(request, 'finish_maintenance.html', contexto)

# --- FUNÇÃO PARA O MECÂNICO ENVIAR A VISTORIA E O ORÇAMENTO ---
@login_required(login_url='login')
def realizar_vistoria(request, id):
    manutencao = get_object_or_404(Maintenance, id=id, mecanico=request.user, status='ACEITA')
    
    if request.method == 'POST':
        form = VistoriaForm(request.POST, instance=manutencao)
        if form.is_valid():
            vistoria = form.save(commit=False)
            vistoria.save() # Salva o laudo principal
            
            # Pega as listas que o mecânico preencheu
            descricoes = request.POST.getlist('descricao[]')
            precos = request.POST.getlist('preco[]')
            tipos = request.POST.getlist('tipo_item[]') # Pega se é Peça ou Mão de Obra
            
            valor_total = 0
            vistoria.itens_servico.all().delete() # Limpa itens velhos se ele estiver reeditando
            
            # Salva item por item
            for desc, preco, tipo in zip(descricoes, precos, tipos):
                if desc and preco:
                    preco_float = float(preco)
                    is_obrig = (tipo == 'MAO_DE_OBRA') # Se ele selecionou Mão de Obra, fica obrigatório
                    
                    ServiceItem.objects.create(
                        manutencao=vistoria,
                        descricao=desc,
                        preco=preco_float,
                        obrigatorio=is_obrig,
                        aprovado=True # Começa tudo pré-aprovado para o cliente
                    )
                    valor_total += preco_float
            
            vistoria.valor = valor_total
            vistoria.status = 'AGUARDANDO_APROVACAO' 
            vistoria.save()
            
            return redirect('home')
    else:
        form = VistoriaForm(instance=manutencao)
        
    contexto = {'form': form, 'manutencao': manutencao}
    return render(request, 'realizar_vistoria.html', contexto)

# --- FUNÇÕES PARA O CLIENTE APROVAR OU RECUSAR A VISTORIA ---
# --- FUNÇÃO ATUALIZADA: CLIENTE APROVA O ORÇAMENTO PARCIAL OU TOTAL ---
@login_required(login_url='login')
def aprovar_vistoria(request, id):
    manutencao = get_object_or_404(Maintenance, id=id, veiculo__proprietario=request.user, status='AGUARDANDO_APROVACAO')
    
    if request.method == 'POST':
        # Recebe a lista de IDs dos itens que o cliente deixou marcados (aprovados)
        itens_aprovados_ids = request.POST.getlist('itens_aprovados')
        valor_final = 0
        
        # Percorre todos os itens daquele orçamento
        for item in manutencao.itens_servico.all():
            # A Mão de Obra é sempre aprovada; as peças só se estiverem na lista do POST
            if item.obrigatorio or str(item.id) in itens_aprovados_ids:
                item.aprovado = True
                valor_final += item.preco
            else:
                item.aprovado = False
            item.save()
            
        # Atualiza o valor final da manutenção apenas com o que foi aprovado
        manutencao.valor = valor_final
        manutencao.status = 'ANDAMENTO'
        manutencao.save()
        
    return redirect('home')

@login_required(login_url='login')
def recusar_vistoria(request, id):
    manutencao = get_object_or_404(Maintenance, id=id, veiculo__proprietario=request.user, status='AGUARDANDO_APROVACAO')
    
    if request.method == 'POST':
        manutencao.status = 'RECUSADA' # Cliente deu o sinal vermelho para tudo!
        manutencao.save()
        
    return redirect('home')