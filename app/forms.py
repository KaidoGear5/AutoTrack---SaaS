from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from .models import Vehicle, Maintenance

# Pega o modelo de usuário correto que está configurado no seu projeto
User = get_user_model()

# Criamos uma cópia do formulário original, mas apontando para o seu usuário
class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        # Adicionamos os campos exatos que você desenhou no Figma
        fields = ('username', 'first_name', 'email', 'telefone', 'role', 'cnpj')

class VehicleForm(forms.ModelForm):
    class Meta:
        model = Vehicle
        # Aqui dizemos quais campos o cliente pode preencher na tela
        fields = ['marca', 'modelo', 'placa', 'ano', 'km_atual']

class MaintenanceForm(forms.ModelForm):
    class Meta:
        model = Maintenance
        # Pedimos apenas o que o cliente sabe preencher no momento
        fields = ['veiculo', 'tipo', 'descricao_problema']

    # Esta função filtra a garagem para mostrar só os carros do dono
    def __init__(self, *args, **kwargs):
        usuario_logado = kwargs.pop('user', None) # Pega o usuário que a View vai mandar
        super().__init__(*args, **kwargs)
        
        if usuario_logado:
            # Filtra a caixinha 'veiculo' para mostrar apenas carros deste proprietário
            self.fields['veiculo'].queryset = Vehicle.objects.filter(proprietario=usuario_logado)

class FinishMaintenanceForm(forms.ModelForm):
    class Meta:
        model = Maintenance
        # Pedimos apenas o diagnóstico e o preço para finalizar
        fields = ['diagnostico', 'valor']

class VistoriaForm(forms.ModelForm):
    class Meta:
        model = Maintenance
        fields = ['diagnostico_vistoria', 'imagens_evidencia']