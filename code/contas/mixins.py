from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied


class PerfilRequeridoMixin(LoginRequiredMixin):
    """Restringe uma view aos perfis explicitamente autorizados."""
    perfis_permitidos = ()

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and request.user.perfil not in self.perfis_permitidos:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)
