from django import forms


class VerificarIngressoForm(forms.Form):
    codigo = forms.UUIDField(
        label="Código do ingresso",
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Cole ou digite o código do ingresso",
        }),
    )
