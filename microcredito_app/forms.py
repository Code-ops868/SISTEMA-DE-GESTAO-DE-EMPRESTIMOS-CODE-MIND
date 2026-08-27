from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from .models import PerfilUsuario, Cliente
import re
from datetime import date


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


# ============================================
# FORMULÁRIO DE CLIENTE COM DOCUMENTOS
# ============================================

class ClienteForm(forms.ModelForm):
    """
    Formulário para cadastro/edição de clientes
    com validação de documentos moçambicanos
    """
    
    class Meta:
        model = Cliente
        fields = [
            'nome', 'email', 'telefone',
            'nuit', 'nuib', 'bi_passaporte',
            'data_emissao_documento', 'data_validade_documento',
            'renda_mensal', 'data_nascimento', 'endereco', 'observacoes'
        ]
        widgets = {
            'data_emissao_documento': forms.DateInput(attrs={'type': 'date'}),
            'data_validade_documento': forms.DateInput(attrs={'type': 'date'}),
            'data_nascimento': forms.DateInput(attrs={'type': 'date'}),
            'endereco': forms.Textarea(attrs={'rows': 3}),
            'observacoes': forms.Textarea(attrs={'rows': 2}),
        }
    
    def clean_nuit(self):
        """Valida NUIT - 9 dígitos numéricos"""
        nuit = self.cleaned_data.get('nuit')
        if nuit:
            nuit = nuit.strip()
            if not re.match(r'^[0-9]{9}$', nuit):
                raise ValidationError('NUIT deve ter exatamente 9 dígitos numéricos.')
            
            # Verificar duplicidade
            cliente_id = self.instance.id if self.instance else None
            if Cliente.objects.filter(nuit=nuit).exclude(id=cliente_id).exists():
                raise ValidationError('NUIT já cadastrado para outro cliente.')
        return nuit
    
    def clean_nuib(self):
        """Valida NUIB - 9 dígitos numéricos"""
        nuib = self.cleaned_data.get('nuib')
        if nuib:
            nuib = nuib.strip()
            if not re.match(r'^[0-9]{9}$', nuib):
                raise ValidationError('NUIB deve ter exatamente 9 dígitos numéricos.')
            
            cliente_id = self.instance.id if self.instance else None
            if Cliente.objects.filter(nuib=nuib).exclude(id=cliente_id).exists():
                raise ValidationError('NUIB já cadastrado para outro cliente.')
        return nuib
    #=====================================================================
    def clean_bi_passaporte(self):
        """Valida BI: 13 dígitos + letra (Módulo 23)"""
        bi = self.cleaned_data.get('bi_passaporte')
        if bi:
            bi = bi.strip().upper()
            
            # BI: 13 dígitos + 1 letra
            match = re.match(r'^([0-9]{13})([A-Z])$', bi)
            if match:
                numeros = match.group(1)
                letra_informada = match.group(2)
                
                letras = 'ABCDEFGHJKLMNPQRSTVWXYZ'
                peso = 0
                for i, digito in enumerate(numeros):
                    peso += int(digito) * (i + 1)
                
                resto = peso % 23
                letra_calculada = letras[resto - 1] if resto > 0 else 'Z'
                
                if letra_informada != letra_calculada:
                    raise ValidationError(f'BI inválido. Letra correta: {letra_calculada}')
            else:
                raise ValidationError('Formato: 13 dígitos + letra (ex: 031123456789B)')
            
            # Verificar duplicidade
            cliente_id = self.instance.id if self.instance else None
            if Cliente.objects.filter(bi_passaporte=bi).exclude(id=cliente_id).exists():
                raise ValidationError('BI já cadastrado para outro cliente.')
        return bi
        
    #=========================================================================
    def clean(self):
        """Validação cruzada dos campos"""
        cleaned_data = super().clean()
        data_emissao = cleaned_data.get('data_emissao_documento')
        data_validade = cleaned_data.get('data_validade_documento')
        
        if data_emissao and data_validade:
            if data_emissao > data_validade:
                self.add_error('data_validade_documento', 'A data de validade deve ser posterior à data de emissão.')
            
            if data_validade < date.today():
                self.add_error('data_validade_documento', 'O documento está vencido. Por favor, atualize os dados.')
        
        return cleaned_data