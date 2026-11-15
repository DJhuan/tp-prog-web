from django.test import Client, TestCase
from django.urls import reverse

from .models import Usuario


class AdminLoginTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Usuario.objects.create_superuser(
            email="admin@example.com", password="test-password-123"
        )

    def test_login_with_csrf_redirects_to_dashboard(self):
        client = Client(enforce_csrf_checks=True)
        response = client.get(reverse("admin:login"))
        self.assertContains(response, 'name="username"')
        self.assertContains(response, 'name="next" value="/admin/"')
        response = client.post(reverse("admin:login"), {
            "username": "admin@example.com",
            "password": "test-password-123",
            "next": reverse("admin:index"),
            "csrfmiddlewaretoken": client.cookies["csrftoken"].value,
        })
        self.assertRedirects(response, reverse("admin:index"))

    def test_invalid_password_displays_error(self):
        response = self.client.post(reverse("admin:login"), {
            "username": "admin@example.com",
            "password": "wrong-password",
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].non_field_errors())
        self.assertContains(response, 'class="errorlist nonfield"')
        self.assertContains(response, 'value="admin@example.com"')

    def test_jazzmin_and_theme_assets_on_admin_pages(self):
        self.client.force_login(Usuario.objects.get(email="admin@example.com"))
        for url in (
            reverse("admin:index"),
            reverse("admin:eventos_evento_changelist"),
            reverse("admin:eventos_evento_add"),
            reverse("admin:password_change"),
        ):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertContains(response, 'id="jazzy-navbar"')
                self.assertContains(response, 'id="jazzmin-dark-mode-theme"')
                self.assertContains(response, 'js/admin.js', count=1)

    def test_login_uses_jazzmin_registration_base(self):
        response = self.client.get(reverse("admin:login"))
        self.assertContains(response, 'jazzmin-login-page')
        self.assertContains(response, 'id="jazzmin-dark-mode-theme"')
        self.assertContains(response, 'js/admin.js', count=1)


class CadastroLoginLogoutTests(TestCase):
    def test_cadastro_cria_participante_e_ja_faz_login(self):
        response = self.client.post(reverse("contas:cadastrar"), {
            "first_name": "Ana",
            "last_name": "Souza",
            "email": "ana@example.com",
            "password1": "senha-forte-123",
            "password2": "senha-forte-123",
        })
        self.assertRedirects(response, reverse("eventos:lista"))
        usuario = Usuario.objects.get(email="ana@example.com")
        self.assertEqual(usuario.perfil, Usuario.Perfil.PARTICIPANTE)
        self.assertFalse(usuario.is_staff)
        self.assertEqual(int(self.client.session["_auth_user_id"]), usuario.pk)

    def test_cadastro_rejeita_email_repetido_e_senhas_diferentes(self):
        Usuario.objects.create_user(email="ana@example.com", password="x", perfil="PARTICIPANTE")
        response = self.client.post(reverse("contas:cadastrar"), {
            "first_name": "Ana",
            "email": "ana@example.com",
            "password1": "senha-forte-123",
            "password2": "outra-senha-456",
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn("email", response.context["form"].errors)
        self.assertIn("password2", response.context["form"].errors)
        self.assertContains(response, "is-invalid")

    def test_cadastro_ignora_perfil_enviado_no_post(self):
        self.client.post(reverse("contas:cadastrar"), {
            "first_name": "Eve",
            "email": "eve@example.com",
            "password1": "senha-forte-123",
            "password2": "senha-forte-123",
            "perfil": "ADMINISTRADOR",
            "is_staff": "on",
        })
        usuario = Usuario.objects.get(email="eve@example.com")
        self.assertEqual(usuario.perfil, Usuario.Perfil.PARTICIPANTE)
        self.assertFalse(usuario.is_staff)

    def test_login_redireciona_por_perfil(self):
        Usuario.objects.create_user(email="p@example.com", password="senha-123", perfil="PARTICIPANTE")
        Usuario.objects.create_superuser(email="adm@example.com", password="senha-123")
        casos = (("p@example.com", reverse("eventos:lista")), ("adm@example.com", reverse("admin:index")))
        for email, destino in casos:
            with self.subTest(email=email):
                client = Client()
                response = client.post(reverse("contas:entrar"), {"username": email, "password": "senha-123"}, follow=True)
                self.assertRedirects(response, destino)

    def test_login_invalido_mostra_erro(self):
        response = self.client.post(reverse("contas:entrar"), {"username": "x@example.com", "password": "errada"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].non_field_errors())

    def test_logout_por_post(self):
        usuario = Usuario.objects.create_user(email="p@example.com", password="senha-123", perfil="PARTICIPANTE")
        self.client.force_login(usuario)
        response = self.client.post(reverse("contas:sair"))
        self.assertRedirects(response, reverse("eventos:lista"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_navbar_mostra_entrar_ou_sair(self):
        response = self.client.get(reverse("eventos:lista"))
        self.assertContains(response, reverse("contas:cadastrar"))
        usuario = Usuario.objects.create_user(email="p@example.com", password="x", perfil="PARTICIPANTE")
        self.client.force_login(usuario)
        response = self.client.get(reverse("eventos:lista"))
        self.assertContains(response, f'action="{reverse("contas:sair")}"')
