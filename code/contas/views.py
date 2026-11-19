from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect
from django.urls import NoReverseMatch, reverse, reverse_lazy
from django.views.generic import CreateView

from .forms import CadastroForm, EntrarForm
from .models import Usuario


# Para onde cada perfil vai depois do login. As rotas do coordenador e do
# organizador são criadas pela Pessoa B; até existirem, cai na página inicial.
DESTINO_POR_PERFIL = {
    Usuario.Perfil.ADMINISTRADOR: "admin:index",
    Usuario.Perfil.VENDEDOR: "admin:index",
    Usuario.Perfil.COORDENADOR: "eventos:dashboard",
    Usuario.Perfil.ORGANIZADOR: "ingressos:eventos_organizador",
    Usuario.Perfil.PARTICIPANTE: "eventos:lista",
}


class EntrarView(LoginView):
    template_name = "contas/entrar.html"
    authentication_form = EntrarForm
    redirect_authenticated_user = True


class SairView(LogoutView):
    # No Django 5+ o logout só aceita POST (formulário com csrf_token).
    pass


class CadastroView(CreateView):
    form_class = CadastroForm
    template_name = "contas/cadastrar.html"
    success_url = reverse_lazy("eventos:lista")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("contas:inicio")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        resposta = super().form_valid(form)
        login(self.request, self.object)
        messages.success(
            self.request,
            f"Bem-vindo(a) ao EVENTA, {self.object.first_name}! Sua conta foi criada."
        )
        return resposta


@login_required
def inicio(request):
    """Redireciona o usuário para a área correspondente ao seu perfil."""
    nome_rota = DESTINO_POR_PERFIL.get(request.user.perfil, "eventos:lista")
    try:
        destino = reverse(nome_rota)
    except NoReverseMatch:
        destino = reverse("eventos:lista")
    return redirect(destino)
