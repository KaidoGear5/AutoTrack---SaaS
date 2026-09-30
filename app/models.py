# ==============================================================================
# IMPORTAÇÕES DO DJANGO
# ==============================================================================
# Importa o módulo 'models' do Django, que contém as ferramentas para criar as tabelas do banco de dados usando apenas código Python.
from django.db import models
# Importa o 'AbstractUser', que é o modelo de usuário padrão do Django
# (já vem com login, senha, e-mail, etc). Esse modelo é importado para criar o nosso próprio usuário 
# "turbinado", adicionando novos campos como 'role' (cargo), 'telefone', cnpj, etc.
from django.contrib.auth.models import AbstractUser

# 1. USUÁRIO CUSTOMIZADO (Tabela que guarda todos que acessam o sistema)
class User(AbstractUser):
    # Opções de perfil disponíveis definidas no sistema.
    # O primeiro valor (ex: 'CLIENTE') é o que vai pro banco de dados. 
    # O segundo (ex: 'Proprietário de Veículo') é o que aparece na tela para o usuário.
    ROLE_CHOICES = (
        ('CLIENTE', 'Proprietário de Veículo'),
        ('MECANICO', 'Mecânico'),
        ('DONO', 'Dono de Oficina'),
    )
    # Campo que define o tipo de acesso do usuário. Por padrão, se ninguém alterar nada, ele é CLIENTE.
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='CLIENTE')
    # blank=True e null=True significam que o campo não é obrigatório e pode ficar vazio no banco.
    telefone = models.CharField(max_length=15, blank=True, null=True)
    foto_perfil = models.URLField(blank=True, null=True) # Guarda apenas o link (URL) da foto
    
    # Campos específicos dependendo do tipo de usuário
    cnpj = models.CharField(max_length=18, blank=True, null=True) # Usado pelo DONO da oficina
    especialidade = models.CharField(max_length=50, blank=True, null=True) # Usado pelo MECÂNICO (ex: "Suspensão")
    bio = models.TextField(blank=True, null=True) # Uma breve descrição do usuário
    
    # Relacionamento (Vínculo do mecânico com a oficina)
    # ForeignKey: Cria uma relação "Muitos para 1" (Muitos mecânicos podem pertencer a 1 oficina).
    # A string 'Workshop' com aspas porque a classe Workshop foi escrita mais abaixo no código.
    # on_delete=models.SET_NULL: Se a oficina for deletada, o mecânico não é apagado, ele apenas fica sem oficina (null).
    # related_name='mecanicos_equipe': É um "apelido" para buscarmos todos os mecânicos de uma oficina facilmente.
    oficina_vinculada = models.ForeignKey('Workshop', on_delete=models.SET_NULL, null=True, blank=True, related_name='mecanicos_equipe')

# 2. OFICINA (Tabela que guarda os dados da oficina)
class Workshop(models.Model):
    nome = models.CharField(max_length=100)
    endereco = models.CharField(max_length=200)
    descricao = models.TextField(blank=True, null=True) # TextField é para textos grandes, sem limite
    codigo_convite = models.CharField(max_length=20, unique=True) # unique=True: Garante que não existam dois códigos de convite iguais em toda a plataforma.
    # on_delete=models.SET_NULL: Se o dono deletar a conta, a oficina continua no sistema, mas sem dono (null).
    dono = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='oficinas_gerenciadas') 

# 3. VEÍCULO (Tabela que guarda os veículos dos clientes)
class Vehicle(models.Model):
    marca = models.CharField(max_length=50)
    modelo = models.CharField(max_length=50)
    ano = models.IntegerField()
    placa = models.CharField(max_length=10, unique=True) # unique=True: Garante que não existam dois veículos com a mesma placa em toda a plataforma.
    km_atual = models.IntegerField(null=True, blank=True)
    # SET_NULL: Se o dono do carro deletar a conta, o carro e o histórico ficam salvos 
    # no sistema da oficina (importante para manter os relatórios financeiros e de serviço da oficina intactos).
    proprietario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='veiculos')
    # Essa função faz com que, ao imprimir o veículo no painel de administração, 
    # ele apareça com um nome bonito (Ex: "Honda Civic - ABC1234") em vez de "Vehicle Object(1)".
    def __str__(self):
        return f"{self.marca} {self.modelo} - {self.placa}"

# 4. ORDEM DE SERVIÇO / MANUTENÇÃO (Tabela principal do fluxo de trabalho)
class Maintenance(models.Model):
    # Opções que ditam em qual fase/etapa o serviço se encontra.
    STATUS_CHOICES = (
    ('PENDENTE', 'Pendente'),                 # Cliente abriu, esperando mecânico
    ('ACEITA', 'Aceita'),                     # Mecânico pegou o carro para avaliar
    ('AGUARDANDO_APROVACAO', 'Aguard. Aprovação'), # Vistoria feita, cliente precisa aprovar
    ('ANDAMENTO', 'Em Andamento'),            # Cliente aprovou, serviço rolando
    ('CONCLUIDO', 'Concluído'),               # Serviço finalizado e cobrado
    ('RECUSADA', 'Recusada'),                 # Cliente não aprovou o orçamento
    )
    # Tipo da manutenção
    TIPO_CHOICES = (
        ('CORRETIVA', 'Corretiva'),
        ('PREVENTIVA', 'Preventiva'),
        ('REVISAO', 'Revisão'),
    )
    # Relacionamentos (Quem participa desta Ordem de Serviço)
    veiculo = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='manutencoes')
    oficina = models.ForeignKey(Workshop, on_delete=models.SET_NULL, null=True)
    mecanico = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='servicos_realizados')
    # Dados preenchidos durante a vistoria e orçamento
    diagnostico = models.TextField(blank=True, null=True)
    valor = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    diagnostico_vistoria = models.TextField(blank=True, null=True)
    imagens_evidencia = models.URLField(blank=True, null=True) # Guarda o link da imagem
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='PENDENTE')
    tipo = models.CharField(max_length=15, choices=TIPO_CHOICES)
    descricao_problema = models.TextField()
    diagnostico_mecanico = models.TextField(blank=True, null=True)
    valor_total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    # Informações para o futuro (Pós-venda e lembretes)
    proxima_revisao_data = models.DateField(blank=True, null=True) # Campo focado apenas na Data (DD/MM/AAAA)
    proxima_revisao_km = models.IntegerField(blank=True, null=True)
    # auto_now_add=True: Pega a data e hora exata em que essa O.S foi criada automaticamente.
    criado_em = models.DateTimeField(auto_now_add=True)
    data_aceite = models.DateTimeField(blank=True, null=True) # Data e hora em que o mecânico aceitou a O.S

    def __str__(self):
        # Mostra o carro e o status (Ex: "Honda Civic - Aguard. Aprovação")
        return f"{self.veiculo} - {self.get_status_display()}"

# TABELA PARA A NOTA FISCAL DETALHADA E ORÇAMENTO INTERATIVO
class ServiceItem(models.Model):
    # Amarramos este item a uma manutenção específica. Se a manutenção for deletada, 
    # as peças e serviços dela (CASCADE) são apagadas também.
    manutencao = models.ForeignKey(Maintenance, on_delete=models.CASCADE, related_name='itens_servico')
    descricao = models.CharField(max_length=255) # Ex: "Troca de pastilha de freio"
    preco = models.DecimalField(max_digits=10, decimal_places=2) # Ex: 250.00
    # CAMPOS PARA O ORÇAMENTO INTERATIVO
    # BooleanField = Verdadeiro (True) ou Falso (False)
    aprovado = models.BooleanField(default=True) # Cliente desmarca a caixinha se não quiser fazer o serviço
    obrigatorio = models.BooleanField(default=False) # Se for obrigatório, o cliente não consegue desmarcar a caixinha (ex: mão de obra)
    
    def __str__(self):
        return f"{self.descricao} - R$ {self.preco}"

# 5. ITENS DO ORÇAMENTO (Tabela Alternativa)
# Essa tabela tem um funcionamento semelhante ao ServiceItem, 
# no entanto, não possui os campos interativos de 'aprovado' e 'obrigatorio'.
class MaintenanceItem(models.Model):
    manutencao = models.ForeignKey(Maintenance, on_delete=models.CASCADE, related_name='itens')
    nome_servico = models.CharField(max_length=100)
    valor = models.DecimalField(max_digits=10, decimal_places=2)

# 6. Notificações
class Notification(models.Model):
    # Para qual usuário a notificação vai (pro dono, pro cliente, ou pro mecânico)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notificacoes')
    mensagem = models.CharField(max_length=255)
    # Flag para saber se o usuário já clicou e leu a notificação (começa sempre como Falso, ou seja, Não lida)
    lida = models.BooleanField(default=False)
    criado_em = models.DateTimeField(auto_now_add=True)