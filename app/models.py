from django.db import models
from django.contrib.auth.models import AbstractUser

# 1. Usuário Customizado (Para todos os tipos de conta)
class User(AbstractUser):
    ROLE_CHOICES = (
        ('CLIENTE', 'Proprietário de Veículo'),
        ('MECANICO', 'Mecânico'),
        ('DONO', 'Dono de Oficina'),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='CLIENTE')
    telefone = models.CharField(max_length=15, blank=True, null=True)
    foto_perfil = models.URLField(blank=True, null=True)
    
    # Campos específicos
    cnpj = models.CharField(max_length=18, blank=True, null=True) 
    especialidade = models.CharField(max_length=50, blank=True, null=True) 
    bio = models.TextField(blank=True, null=True) 
    
    # Vínculo exclusivo do mecânico com a oficina (1 para Muitos)
    # Usamos string 'Workshop' porque a classe Workshop ainda não foi lida pelo Python nesta linha
    oficina_vinculada = models.ForeignKey('Workshop', on_delete=models.SET_NULL, null=True, blank=True, related_name='mecanicos_equipe')

# 2. Oficina
class Workshop(models.Model):
    nome = models.CharField(max_length=100)
    endereco = models.CharField(max_length=200)
    descricao = models.TextField(blank=True, null=True)
    codigo_convite = models.CharField(max_length=20, unique=True)
    dono = models.ForeignKey(User, on_delete=models.CASCADE, related_name='oficinas_gerenciadas')

# 3. Veículo
class Vehicle(models.Model):
    marca = models.CharField(max_length=50)
    modelo = models.CharField(max_length=50)
    ano = models.IntegerField()
    placa = models.CharField(max_length=10, unique=True)
    km_atual = models.IntegerField(null=True, blank=True)
    # SET_NULL: Se o dono deletar a conta, o carro e o histórico ficam no sistema da oficina
    proprietario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='veiculos')
    def __str__(self):
        return f"{self.marca} {self.modelo} - {self.placa}"

# 4. Ordem de Serviço / Manutenção
class Maintenance(models.Model):
    STATUS_CHOICES = (
    ('PENDENTE', 'Pendente'),                 # Cliente abriu, esperando mecânico
    ('ACEITA', 'Aceita'),                     # Mecânico pegou o carro para avaliar
    ('AGUARDANDO_APROVACAO', 'Aguard. Aprovação'), # Vistoria feita, cliente precisa aprovar
    ('ANDAMENTO', 'Em Andamento'),            # Cliente aprovou, serviço rolando
    ('CONCLUIDO', 'Concluído'),               # Serviço finalizado e cobrado
    ('RECUSADA', 'Recusada'),                 # Cliente não aprovou o orçamento
    )
    TIPO_CHOICES = (
        ('CORRETIVA', 'Corretiva'),
        ('PREVENTIVA', 'Preventiva'),
        ('REVISAO', 'Revisão'),
    )
    veiculo = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='manutencoes')
    oficina = models.ForeignKey(Workshop, on_delete=models.SET_NULL, null=True)
    mecanico = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='servicos_realizados')
    diagnostico = models.TextField(blank=True, null=True)
    valor = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    diagnostico_vistoria = models.TextField(blank=True, null=True)
    imagens_evidencia = models.URLField(blank=True, null=True) # Guarda o link da imagem
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='PENDENTE')
    tipo = models.CharField(max_length=15, choices=TIPO_CHOICES)
    descricao_problema = models.TextField()
    diagnostico_mecanico = models.TextField(blank=True, null=True)
    valor_total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    proxima_revisao_data = models.DateField(blank=True, null=True)
    proxima_revisao_km = models.IntegerField(blank=True, null=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    data_aceite = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.veiculo} - {self.get_status_display()}"

# --- TABELA PARA A NOTA FISCAL DETALHADA ---
class ServiceItem(models.Model):
    # Amarramos este item a uma manutenção específica
    manutencao = models.ForeignKey(Maintenance, on_delete=models.CASCADE, related_name='itens_servico')
    descricao = models.CharField(max_length=255) # Ex: "Troca de pastilha de freio"
    preco = models.DecimalField(max_digits=10, decimal_places=2) # Ex: 250.00
    # CAMPOS PARA O ORÇAMENTO INTERATIVO
    aprovado = models.BooleanField(default=True) # Cliente desmarca se não quiser
    obrigatorio = models.BooleanField(default=False) # Verdadeiro se for Mão de Obra
    
    def __str__(self):
        return f"{self.descricao} - R$ {self.preco}"

# 5. Itens do Orçamento (Peças e Serviços)
class MaintenanceItem(models.Model):
    manutencao = models.ForeignKey(Maintenance, on_delete=models.CASCADE, related_name='itens')
    nome_servico = models.CharField(max_length=100)
    valor = models.DecimalField(max_digits=10, decimal_places=2)

# 6. Notificações
class Notification(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notificacoes')
    mensagem = models.CharField(max_length=255)
    lida = models.BooleanField(default=False)
    criado_em = models.DateTimeField(auto_now_add=True)