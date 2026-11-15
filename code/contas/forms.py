from django import forms
from django.contrib.auth.forms import AuthenticationForm, BaseUserCreationForm

from .models import Usuario


class BootstrapFormMixin:
    """Adiciona as classes do Bootstrap aos widgets do formulário."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in self.fields.values():
            widget = campo.widget
            if isinstance(widget, (forms.CheckboxInput, forms.RadioSelect)):
                classe = "form-check-input"
            elif isinstance(widget, forms.Select):
                classe = "form-select"
            else:
                classe = "form-control"
            widget.attrs["class"] = f"{widget.attrs.get('class', '')} {classe}".strip()

    def full_clean(self):
        super().full_clean()
        # Marca os campos com erro para o Bootstrap destacar em vermelho.
        for nome in self.errors:
            if nome in self.fields:
                widget = self.fields[nome].widget
                widget.attrs["class"] = f"{widget.attrs.get('class', '')} is-invalid".strip()


class EntrarForm(BootstrapFormMixin, AuthenticationForm):
    pass


class CadastroForm(BootstrapFormMixin, BaseUserCreationForm):
    """Cadastro público: sempre cria um usuário com perfil Participante."""

    class Meta:
        model = Usuario
        fields = ("first_name", "last_name", "email")
        labels = {
            "first_name": "Nome",
            "last_name": "Sobrenome",
            "email": "E-mail",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["first_name"].required = True

    def save(self, commit=True):
        usuario = super().save(commit=False)
        usuario.perfil = Usuario.Perfil.PARTICIPANTE
        if commit:
            usuario.save()
        return usuario
