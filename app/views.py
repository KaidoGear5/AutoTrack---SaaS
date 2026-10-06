# IMPORTAÇÕES GERAIS E FERRAMENTAS
# ==============================================================================
# render: Monta a tela HTML misturando com os dados do Python.
# redirect: Arremessa o usuário para outra página (URL) após uma ação.
# get_object_or_404: Tenta buscar um dado no banco; se não achar ou for de outro dono, dá erro 404 (página não encontrada), garantindo segurança.
from django.shortcuts import render, redirect, get_object_or_404
# login_required: É um "cadeado". Se o usuário não estiver logado, não deixa acessar a função e manda pra tela de login.
from django.contrib.auth.decorators import login_required
# São importadas as classes que criamos no models.py (Vehicle, Maintenance e ServiceItem) para manipular os dados do banco de dados.
from .models import Vehicle, Maintenance, ServiceItem, Workshop
# São importados os formulários que criados no forms.py para manipular os dados do usuário.
from .forms import VehicleForm, CustomUserCreationForm, MaintenanceForm, FinishMaintenanceForm, VistoriaForm
from django.contrib.auth import login # Ferramenta para forçar o login automático após o cadastro
from django.utils import timezone # Ferramenta para pegar a data e hora exata de "agora"

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

        # Busca as O.S que ninguém pegou ainda (PENDENTE)
        fila_de_espera = Maintenance.objects.filter(status='PENDENTE').order_by('-criado_em')
        
        # Busca as O.S que ESTE mecânico assumiu
        meus_servicos = Maintenance.objects.filter(mecanico=request.user, status__in=['ACEITA', 'ANDAMENTO']).order_by('-criado_em')

        # 'contexto' é o pacote de dados que enviamos do Python para o HTML
        contexto = {
            'solicitacoes': fila_de_espera, # Lista de solicitações de manutenção aguardando atendimento, para mostrar no painel
            'meus_servicos': meus_servicos, # Lista de serviços do mecânico logado, para mostrar no painel
            'erro': erro # Mensagem de erro, se houver
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
        
        contexto = {
            'oficinas': minhas_oficinas,
            # Passamos qual aba deve ficar ativa (padrão: oficinas)
            'aba_ativa': request.GET.get('tab', 'oficinas') 
        }
        return render(request, 'owner_dashboard.html', contexto)
        
    # ROTA DO CLIENTE (Proprietário de Veículo) - Se for Cliente, direciona para a visão do cliente
    else:
        # Pega apenas os carros que pertencem ao usuário que está acessando
        meus_carros = Vehicle.objects.filter(proprietario=request.user)
        
        # Busca o histórico de manutenções apenas dos VEÍCULOS desse cliente específico
        minhas_manutencoes = Maintenance.objects.filter(veiculo__proprietario=request.user).order_by('-criado_em')
        
        contexto = {
            'carros_para_tela': meus_carros,
            'manutencoes_para_tela': minhas_manutencoes # Envia a lista para o HTML
        }
        return render(request, 'home.html', contexto)

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
            # O status já nasce como 'PENDENTE' (definido lá no models.py como default)
            nova_manutencao.save()
            return redirect('home')
    else:
        form = MaintenanceForm(user=request.user)
        
    contexto = {'form': form}
    return render(request, 'request_maintenance.html', contexto)

# MECÂNICO ACEITAR O SERVIÇO
@login_required(login_url='login')
def accept_maintenance(request, id):
    # Trava dupla de segurança: Tem que ser mecânico E tem que ser via POST (clique no botão)
    if request.user.role == 'MECANICO' and request.method == 'POST':
        # Busca a ordem exata, mas APENAS se ela ainda estiver aguardando atendimento (status PENDENTE). Se não achar, dá erro 404.
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

# FUNÇÃO PARA O MECÂNICO ENVIAR A VISTORIA E O ORÇAMENTO
@login_required(login_url='login')
def realizar_vistoria(request, id):
    manutencao = get_object_or_404(Maintenance, id=id, mecanico=request.user, status='ACEITA')
    
    if request.method == 'POST':
        form = VistoriaForm(request.POST, instance=manutencao)
        if form.is_valid():
            vistoria = form.save(commit=False)
            vistoria.save() # Salva o laudo principal
            
            # Tratamento das Peças e Serviços Dinâmicos
            # O HTML envia listas completas de tudo que o mecânico adicionou
            descricoes = request.POST.getlist('descricao[]')
            precos = request.POST.getlist('preco[]')
            tipos = request.POST.getlist('tipo_item[]') # Pega se é Peça ou Mão de Obra
            
            valor_total = 0
            vistoria.itens_servico.all().delete() # Limpa qualquer item que estivesse salvo antes, para evitar duplicatas se o mecânico reeditar
            
            # O 'zip' une as três listas. Ele lê a 1ª descrição, com o 1º preço, com o 1º tipo simultaneamente
            for desc, preco, tipo in zip(descricoes, precos, tipos):
                if desc and preco:
                    preco_float = float(preco) # Converte o texto do HTML para número decimal
                    is_obrig = (tipo == 'MAO_DE_OBRA') # Se ele selecionou Mão de Obra, fica obrigatório

                    # Cria o item no banco de dados e atrela a esta vistoria
                    ServiceItem.objects.create(
                        manutencao=vistoria,
                        descricao=desc,
                        preco=preco_float,
                        obrigatorio=is_obrig,
                        aprovado=True # Começa tudo pré-aprovado para o cliente, que depois pode desmarcar o que não quiser
                    )
                    valor_total += preco_float # Acumula o valor total do orçamento para mostrar no final
            
            vistoria.valor = valor_total # Atualiza o valor total da manutenção com a soma de todos os itens
            vistoria.status = 'AGUARDANDO_APROVACAO' # Joga a bola pro cliente
            vistoria.save()
            
            return redirect('home')
    else:
        form = VistoriaForm(instance=manutencao) # Preenche o formulário com os dados atuais da manutenção, caso o mecânico queira reeditar a vistoria antes do cliente aprovar
        
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
            # Regra de negócio: Se for obrigatório (Mão de Obra) OU se o cliente marcou no HTML, aprova.
            # Convertos o item.id para string (str) porque o HTML sempre envia textos nas listas
            if item.obrigatorio or str(item.id) in itens_aprovados_ids:
                item.aprovado = True
                valor_final += item.preco # Soma apenas o que foi aprovado
            else:
                item.aprovado = False
            item.save()
            
        manutencao.valor = valor_final # Atualiza o valor final da manutenção apenas com o que foi aprovado
        manutencao.status = 'ANDAMENTO' # Devolve a bola para o mecânico
        manutencao.save()
        
    return redirect('home')

# CLIENTE RECUSA TUDO
@login_required(login_url='login')
def recusar_vistoria(request, id):
    manutencao = get_object_or_404(Maintenance, id=id, veiculo__proprietario=request.user, status='AGUARDANDO_APROVACAO')
    
    if request.method == 'POST':
        manutencao.status = 'RECUSADA' # Cliente deu o sinal vermelho para tudo!
        manutencao.save()
        
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
            
            return redirect('home')
    else:
        form = FinishMaintenanceForm(instance=manutencao)
        
    contexto = {
        'form': form, 
        'manutencao': manutencao,
        'itens_aprovados': manutencao.itens_servico.filter(aprovado=True) # Manda pro HTML só o que o cliente quis, para gerar a nota fiscal limpa
    }
    return render(request, 'finish_maintenance.html', contexto)