from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from .models import PerfilUsuario
import re


class CadastroForm(UserCreationForm):
    """Formulário de cadastro de novos usuários"""
    
    first_name = forms.CharField(
        label='Nome',
        max_length=30,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Seu nome'
        })
    )
    
    last_name = forms.CharField(
        label='Sobrenome',
        max_length=30,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Seu sobrenome'
        })
    )
    
    email = forms.EmailField(
        label='E-mail',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'seu@email.com'
        })
    )
    
    telefone = forms.CharField(
        label='Telefone/WhatsApp',
        max_length=15,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '84 1234567'
        })
    )
    
    senha1 = forms.CharField(
        label='Senha',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': '••••••••'
        })
    )
    
    senha2 = forms.CharField(
        label='Confirmar Senha',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': '••••••••'
        })
    )
    
    termos = forms.BooleanField(
        label='Concordo com os Termos de Uso',
        required=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
        # NOVO CAMPO: Aceitação dos termos
    aceita_termos = forms.BooleanField(
        required=True, 
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='Li e aceito os <a href="/termos-e-condicoes/" target="_blank">Termos e Condições</a> e a <a href="/politica-de-privacidade/" target="_blank">Política de Privacidade</a>'
    )
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'senha1', 'senha2', 'telefone', 'termos']
    
    def clean_email(self):
        """Valida se o e-mail já está cadastrado"""
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError('Este e-mail já está cadastrado.')
        return email
    
    def clean_telefone(self):
        """Valida e formata o telefone"""
        telefone = self.cleaned_data.get('telefone')
        # Remove caracteres não numéricos
        telefone_limpo = re.sub(r'\D', '', telefone)
        
        if len(telefone_limpo) < 8 or len(telefone_limpo) > 9:
            raise ValidationError('Telefone inválido. Use formato: 84 1234567')
        
        return telefone_limpo
    
    def clean_senha2(self):
        """Valida se as senhas conferem"""
        senha1 = self.cleaned_data.get('senha1')
        senha2 = self.cleaned_data.get('senha2')
        
        if senha1 and senha2 and senha1 != senha2:
            raise ValidationError('As senhas não conferem.')
        
        if senha1 and len(senha1) < 6:
            raise ValidationError('A senha deve ter no mínimo 6 caracteres.')
        
        return senha2
    
    def save(self, commit=True):
        """Salva o usuário e cria o perfil"""
        user = super().save(commit=False)
        user.username = self.cleaned_data['email'].split('@')[0]
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        
        # Garantir username único
        username = user.username
        base_username = username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1
        user.username = username
        
        if commit:
            user.set_password(self.cleaned_data['senha1'])
            user.save()
            
            # Criar perfil do usuário
            PerfilUsuario.objects.create(
                user=user,
                telefone=self.cleaned_data['telefone']
            )
        
        return user


class LoginForm(forms.Form):
    """Formulário de login"""
    
    email = forms.EmailField(
        label='E-mail',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'seu@email.com',
            'autofocus': True
        })
    )
    
    senha = forms.CharField(
        label='Senha',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': '••••••••'
        })
    )
    
    lembrar = forms.BooleanField(
        label='Lembrar-me',
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )