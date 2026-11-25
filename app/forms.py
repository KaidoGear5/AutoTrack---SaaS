from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from .models import Vehicle, Maintenance

User = get_user_model()

class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'first_name', 'email', 'telefone', 'role', 'cnpj')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['telefone'].required = False
        self.fields['cnpj'].required = False

class VehicleForm(forms.ModelForm):
    class Meta:
        model = Vehicle
        fields = ['marca', 'modelo', 'placa', 'ano', 'km_atual']

class MaintenanceForm(forms.ModelForm):
    class Meta:
        model = Maintenance
        fields = ['veiculo', 'tipo', 'descricao_problema']

    def __init__(self, *args, **kwargs):
        usuario_logado = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if usuario_logado:
            self.fields['veiculo'].queryset = Vehicle.objects.filter(proprietario=usuario_logado)

class FinishMaintenanceForm(forms.ModelForm):
    class Meta:
        model = Maintenance
        fields = ['diagnostico', 'valor']

class VistoriaForm(forms.ModelForm):
    class Meta:
        model = Maintenance
        fields = ['diagnostico_vistoria', 'imagens_evidencia']
