from decimal import Decimal
import re
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Material, Perfil


class PesagemForm(forms.Form):
    data = forms.DateField(label='Data', initial=timezone.localdate, widget=forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}), input_formats=['%Y-%m-%d'])
    material = forms.ModelChoiceField(label='Material', queryset=Material.objects.all(), empty_label='Selecione um material')
    peso = forms.DecimalField(label='Peso recebido (kg)', min_value=Decimal('0.01'), max_digits=12, decimal_places=2, widget=forms.NumberInput(attrs={'step': '.01', 'inputmode': 'decimal', 'placeholder': '0,00'}))


class EtapaForm(forms.Form):
    data = forms.DateField(label='Data', initial=timezone.localdate, widget=forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}), input_formats=['%Y-%m-%d'])
    material = forms.ModelChoiceField(label='Material', queryset=Material.objects.all(), empty_label='Selecione um material')


class ItensForm(forms.Form):
    def __init__(self, *args, classificacoes, venda=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.rows = []
        for c in classificacoes:
            peso = f'peso_{c.pk}'
            self.fields[peso] = forms.DecimalField(label=f'Peso de {c.nome}', required=False, min_value=0, max_digits=12, decimal_places=2, widget=forms.NumberInput(attrs={'step': '.01', 'placeholder': '0,00', 'inputmode': 'decimal', 'class': 'peso'}))
            preco = f'preco_{c.pk}'
            if venda:
                self.fields[preco] = forms.DecimalField(label=f'Preço por kg de {c.nome}', required=False, min_value=0, max_digits=10, decimal_places=2, widget=forms.NumberInput(attrs={'step': '.01', 'placeholder': '0,00', 'inputmode': 'decimal', 'class': 'preco'}))
            self.rows.append({'classificacao': c, 'peso': self[peso], 'preco': self[preco] if venda else None})

    def clean(self):
        data = super().clean()
        if not any(v and v > 0 for k, v in data.items() if k.startswith('peso_')):
            raise forms.ValidationError('Informe pelo menos um peso positivo.')
        return data


class RelatorioForm(forms.Form):
    tipo = forms.ChoiceField(choices=[('mensal', 'Mensal'), ('anual', 'Anual')])
    ano = forms.IntegerField(min_value=1900, max_value=9999)
    mes = forms.IntegerField(required=False, min_value=1, max_value=12)

    def clean(self):
        data = super().clean()
        if data.get('tipo') == 'mensal' and not data.get('mes'):
            self.add_error('mes', 'Selecione o mês.')
        return data


class PainelForm(forms.Form):
    ano = forms.IntegerField(label='Ano', min_value=1900, max_value=9999, initial=lambda: timezone.localdate().year)
    meses = [(i, nome) for i, nome in enumerate(['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'], 1)]
    mes = forms.TypedChoiceField(label='Mês inicial', required=False, coerce=int, empty_value=None, choices=[('', 'Ano inteiro')] + meses)
    mes_final = forms.TypedChoiceField(label='Mês final', required=False, coerce=int, empty_value=None, choices=[('', 'Mesmo mês inicial')] + meses)

    def clean(self):
        data = super().clean()
        inicio, fim = data.get('mes'), data.get('mes_final')
        if fim and not inicio:
            self.add_error('mes', 'Selecione o mês inicial para consultar um intervalo.')
        elif inicio and fim and fim < inicio:
            self.add_error('mes_final', 'O mês final deve ser igual ou posterior ao mês inicial.')
        return data


class CooperadoForm(forms.Form):
    nome = forms.CharField(label='Nome', max_length=150)
    sobrenome = forms.CharField(label='Sobrenome', max_length=150)
    email = forms.EmailField(label='E-mail', max_length=254)
    telefone = forms.CharField(label='Telefone (opcional)', max_length=20, required=False)
    cpf = forms.CharField(label='CPF (opcional)', max_length=14, required=False, help_text='Somente o presidente pode consultar estes dados.')
    username = forms.CharField(label='Login', max_length=150)
    cargo = forms.ChoiceField(label='Cargo', choices=[('cooperado', 'Cooperado'), ('diretoria', 'Diretoria')])
    senha = forms.CharField(label='Senha inicial', widget=forms.PasswordInput, required=False, help_text='Pelo menos 8 caracteres. Na edição, deixe em branco para manter a senha.')
    confirmar_senha = forms.CharField(label='Confirmar senha', widget=forms.PasswordInput, required=False)
    ativo = forms.BooleanField(label='Acesso ativo', initial=True, required=False)

    def __init__(self, *args, usuario=None, **kwargs):
        self.usuario = usuario
        if usuario and not args:
            perfil = Perfil.objects.filter(usuario=usuario).first()
            kwargs['initial'] = {'nome': usuario.first_name, 'sobrenome': usuario.last_name, 'email': usuario.email, 'username': usuario.username, 'ativo': usuario.is_active, 'telefone': perfil.telefone if perfil else '', 'cpf': perfil.cpf if perfil else '', 'cargo': perfil.cargo if perfil else 'cooperado'}
        super().__init__(*args, **kwargs)
        if not usuario:
            self.fields['senha'].required = True
            self.fields['confirmar_senha'].required = True

    def clean_username(self):
        value = self.cleaned_data['username']
        field = get_user_model()._meta.get_field('username')
        field.run_validators(value)
        qs = get_user_model().objects.filter(username__iexact=value)
        if self.usuario:
            qs = qs.exclude(pk=self.usuario.pk)
        if qs.exists():
            raise forms.ValidationError('Este login já está cadastrado.')
        return value

    def clean_email(self):
        value = self.cleaned_data['email'].lower()
        qs = get_user_model().objects.filter(email__iexact=value)
        if self.usuario:
            qs = qs.exclude(pk=self.usuario.pk)
        if qs.exists():
            raise forms.ValidationError('Este e-mail já está cadastrado.')
        return value

    def clean_cpf(self):
        value = re.sub(r'\D', '', self.cleaned_data.get('cpf', ''))
        if not value:
            return None
        if len(value) != 11 or len(set(value)) == 1:
            raise forms.ValidationError('Informe um CPF válido.')
        for n in (9, 10):
            digit = (sum(int(value[i]) * (n + 1 - i) for i in range(n)) * 10) % 11
            if int(value[n]) != (0 if digit == 10 else digit):
                raise forms.ValidationError('Informe um CPF válido.')
        qs = Perfil.objects.filter(cpf=value)
        if self.usuario:
            qs = qs.exclude(usuario=self.usuario)
        if qs.exists():
            raise forms.ValidationError('Este CPF já está cadastrado.')
        return value

    def clean(self):
        data = super().clean()
        senha = data.get('senha')
        if senha:
            if senha != data.get('confirmar_senha'):
                self.add_error('confirmar_senha', 'As senhas não conferem.')
            try:
                validate_password(senha)
            except ValidationError as error:
                self.add_error('senha', error)
        return data
