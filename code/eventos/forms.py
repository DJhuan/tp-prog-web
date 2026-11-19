from django import forms
from django.forms import inlineformset_factory

from contas.models import Usuario
from .models import Evento, TipoIngresso


class EventoForm(forms.ModelForm):
    organizadores = forms.ModelMultipleChoiceField(
        queryset=Usuario.objects.none(), required=False,
        widget=forms.SelectMultiple(attrs={"class": "form-select", "size": 5}),
        help_text="Selecione os organizadores que poderão validar ingressos e consultar a presença.",
    )

    class Meta:
        model = Evento
        exclude = ("produtora", "coordenador")
        widgets = {
            "data": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "horario": forms.TimeInput(attrs={"type": "time", "class": "form-control"}),
            "descricao": forms.Textarea(attrs={"rows": 4, "class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["organizadores"].queryset = Usuario.objects.filter(
            perfil=Usuario.Perfil.ORGANIZADOR, is_active=True
        ).order_by("first_name", "email")
        for field in self.fields.values():
            if not isinstance(field.widget, (forms.CheckboxInput, forms.SelectMultiple)):
                field.widget.attrs.setdefault("class", "form-control")


class TipoIngressoForm(forms.ModelForm):
    class Meta:
        model = TipoIngresso
        exclude = ("evento",)
        widgets = {"descricao": forms.Textarea(attrs={"rows": 2})}


TipoIngressoFormSet = inlineformset_factory(
    Evento, TipoIngresso, form=TipoIngressoForm, extra=3, can_delete=True,
    min_num=1, validate_min=True,
)


