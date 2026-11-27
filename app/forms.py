from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from .models import Vehicle, Maintenance

User = get_user_model()

class CustomUserCreationForm(UserCreationForm):
    # A classe 'Meta' diz ao Django qual tabela do banco (model) este formulário usa
    # e quais campos digitados no HTML ele deve capturar automaticamente.
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'first_name', 'email', 'telefone', 'role', 'cnpj')

    # O método '__init__' roda toda vez que o formulário é carregado na tela.
    def __init__(self, *args, **kwargs):
        # 'super().__init__' monta primeiro toda a estrutura padrão de usuário e senha do Django
        super().__init__(*args, **kwargs)
        # Define quais campos são opcionais (False) e quais são obrigatórios (True)
        self.fields['telefone'].required = False
        self.fields['cnpj'].required = False
        self.fields['email'].required = True

    # No Django, toda função com nome 'clean_<nome_do_campo>' serve como um "fiscal" automático
    # exclusivo para validar e limpar aquele campo específico antes de salvar no banco.
    def clean_username(self):
        # '.strip()' remove espaços em branco digitados sem querer no começo ou no fim
        username = self.cleaned_data.get('username', '').strip()

        # Bloqueia espaços no meio e bloqueia o '@': assim o sistema nunca confunde
        # um Nome de Usuário com um E-mail na hora de fazer login!
        if ' ' in username or '@' in username:
            raise forms.ValidationError('O nome de usuário não deve conter espaços nem o símbolo "@".')

        # '__iexact' compara ignorando maiúsculas/minúsculas (impede criar "Carlos" se já existe "carlos")
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError('Este nome de usuário já está em uso. Escolha outro.')

        return username

    # Fiscal específico do campo 'email': padroniza tudo em letras minúsculas (.lower())
    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if not email:
            raise forms.ValidationError('Informe um endereço de e-mail válido.')
        return email

    # O método 'clean()' (sem nome de campo depois) é o fiscal GERAL do formulário.
    # Usamos ele quando uma regra precisa cruzar DOIS campos ao mesmo tempo: aqui, 'email' + 'role' (cargo).
    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        # Pega o cargo escolhido nos cartões da tela (Cliente, Mecânico ou Dono)
        role = cleaned_data.get('role') or self.data.get('role', 'CLIENTE')

        if email and role:
            # Procura no banco se já existe uma conta com ESTE MESMO e-mail E ESTE MESMO cargo.
            # Isso libera ter 1 Cliente + 1 Mecânico + 1 Dono no mesmo e-mail, mas barra repetir o mesmo cargo!
            if User.objects.filter(email__iexact=email, role=role).exists():
                # Transforma o código do banco (ex: 'DONO') no nome amigável ('Dono de Oficina')
                nomes_perfis = dict(User.ROLE_CHOICES)
                nome_perfil = nomes_perfis.get(role, role)

                # Pendura a mensagem de erro no campo 'email' para aparecer na caixa vermelha da tela
                self.add_error(
                    'email',
                    f'Este e-mail já possui um cadastro como "{nome_perfil}". É permitido no máximo 1 cadastro de cada tipo (Cliente, Mecânico e Dono) por e-mail.'
                )

        return cleaned_data

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
