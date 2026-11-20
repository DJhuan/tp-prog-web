# EVENTA

## Índice

- **Nome da aplicação:** Eventa
- **Integrantes do grupo:**
  - Jhuan Carlos Sabaini Dassie
  - Rafaella Maciel Pereira Leite
  - Vitor Gabriel Firmino
- [**Descrição do projeto**](#descrição-do-projeto)
- **Tecnologias utilizadas:**
  - Python e Django
  - SQLite
  - Bootstrap 5
  - Django Admin com tema e templates personalizados
  - WhiteNoise (arquivos estáticos), Gunicorn (servidor WSGI) e Pillow (imagens)
  - Docker e Docker Compose
- [**Instruções para instalação**](#instruções-para-instalação)
- [**Instruções para execução**](#como-executar)
- [**Populando o banco com dados de demonstração**](#populando-o-banco-com-dados-de-demonstração)
- [**Principais funcionalidades**](#principais-funcionalidades)
- [**Principais rotas**](#principais-rotas)
- [**Estrutura do projeto**](#estrutura-do-projeto)

## Descrição do projeto

O **EVENTA** é uma plataforma web para gestão de eventos e venda de ingressos. O sistema funciona como ponte tecnológica, um SaaS (Software as a Service) onde vendedores da plataforma comercializam a solução para produtoras de eventos. O sistema gerencia todo o ciclo de vida do evento, desde a sua criação pelos coordenadores da produtora, a configuração e venda de ingressos para os participantes, até a validação das entradas no dia do evento pelos organizadores.

## Instruções para instalação

### Com Docker Compose (recomendado)

1. Copie `.env.example` para `.env` e altere `SECRET_KEY` para um valor
   exclusivo em ambientes não locais.
2. Construa e inicie a aplicação:

   ```bash
   docker compose up --build -d
   ```

3. Acesse <http://localhost:8000/>. As migrações são executadas
   automaticamente antes do servidor iniciar.

O banco SQLite é persistido no volume Docker `sqlite_data` e as imagens
enviadas no volume `media_data`. Para parar os serviços, execute
`docker compose down`; para remover também os dados, execute
`docker compose down -v`.

### Ambiente local (sem Docker)

```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cd code
python manage.py migrate
```

### Variáveis de ambiente

| Variável        | Padrão (local)                     | Descrição                                    |
| --------------- | ---------------------------------- | -------------------------------------------- |
| `SECRET_KEY`    | `django-insecure-development-only` | Chave secreta do Django. Troque em produção. |
| `DEBUG`         | `True` (local) / `False` (Docker)  | Modo de depuração.                           |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1`              | Hosts aceitos, separados por vírgula.        |
| `DATABASE_PATH` | `code/db.sqlite3`                  | Caminho do arquivo SQLite.                   |
| `MEDIA_ROOT`    | `code/media`                       | Pasta onde ficam as imagens enviadas.        |

## Como executar

### Com Docker

Depois do `docker compose up --build -d`, a aplicação fica disponível em
<http://localhost:8000/>. Para executar comandos do Django dentro do container,
use `docker compose exec -w /app/code web python manage.py <comando>`.

### Localmente

Com o ambiente virtual ativado, dentro da pasta `code`:

```bash
python manage.py createsuperuser   # opcional: cria um administrador
python manage.py runserver
```

Acesse <http://127.0.0.1:8000/> para a vitrine de eventos e
<http://127.0.0.1:8000/admin/> para o painel administrativo.

## Populando o banco com dados de demonstração

O comando `popular_banco` cria um conjunto completo de dados fictícios para
demonstrar todas as áreas do sistema: usuários de todos os perfis, produtoras,
eventos com imagens, tipos de ingresso, pedidos e check-ins.

```bash
# Docker
docker compose exec -w /app/code web python manage.py popular_banco

# Local (dentro da pasta code)
python manage.py popular_banco
```

### Contas criadas

Todas as contas usam a senha **`eventa123`**.

| Perfil                           | E-mail                    | Para onde vai após o login                    |
| -------------------------------- | ------------------------- | --------------------------------------------- |
| Administrador                    | `admin@eventa.com`        | Painel administrativo                         |
| Vendedor                         | `vendedor@eventa.com`     | Painel administrativo (produtoras e usuários) |
| Coordenador (Aurora Produções)   | `coordenador@eventa.com`  | Dashboard da produtora                        |
| Coordenador (Horizonte Cultural) | `coordenador2@eventa.com` | Dashboard da produtora                        |
| Organizador                      | `organizador@eventa.com`  | Portaria (lista de presença e check-in)       |
| Participante                     | `participante@eventa.com` | Vitrine de eventos e "Meus ingressos"         |

Também são criados mais dois organizadores (`organizador2@eventa.com` e
`organizador3@eventa.com`) e outros nove participantes.

## Principais funcionalidades

O sistema foi projetado com divisão de permissões e módulos focados em atender tanto a administração da plataforma quanto o público final.

### Autenticação e Controle de Acesso

- **Sistema de Contas:** Cadastro de novos usuários (participantes), login e logout de contas na plataforma.
- **Perfis de Usuário:** Controle de permissões de acesso baseado nos papéis de Administrador, Vendedor, Coordenador, Organizador (Staff) e Participante. Após o login, cada perfil é redirecionado para a sua área.
- **Painel Administrativo Customizado:** Área restrita para gestão global da plataforma, utilizando tema personalizado para melhor usabilidade.

### Gestão da Plataforma (SaaS)

- **Gestão de Produtoras:** Funcionalidade exclusiva para Vendedores e Administradores cadastrarem novas produtoras de eventos.
- **Gestão de Coordenadores:** Vínculo de usuários coordenadores às suas respectivas produtoras autorizadas.

### Produção de Eventos (Área do Coordenador)

- **CRUD de Eventos:** Cadastro, consulta, edição e exclusão de eventos da produtora, com foto e banner.
- **Gestão de Ingressos e Lotes:** Criação e configuração de diferentes tipos de ingressos, preços e capacidade para cada evento.
- **Alocação de Staff:** Designação de Organizadores específicos para trabalharem na validação de ingressos de um determinado evento.
- **Dashboard:** Indicadores da produtora (ingressos vendidos, receita, ocupação e check-ins) e gráficos de vendas por tipo de ingresso e por dia.

### Área do Participante (Usuário Final)

- **Catálogo de Eventos:** Vitrine pública com busca por nome ou local, filtro por data e página de detalhes de cada evento.
- **Carrinho e Compra de Ingressos:** Seleção de ingressos de um ou mais eventos no carrinho, com verificação de estoque e geração de pedido com um ticket único por ingresso.
- **Carteira Digital:** Área logada do participante para visualizar e acessar todos os ingressos adquiridos.

### Validação na Portaria (Área do Organizador)

- **Lista de Presença:** Visualização dos ingressos vendidos e participantes esperados para o evento em que o staff está alocado.
- **Check-in de Ingressos:** Validação individual (baixa) dos tickets na porta do evento pelo código do ingresso, com bloqueio automático contra uso duplicado.

### Perfis de usuário e controle de acesso

- **Administrador (ADM):** Possui acesso total ao sistema através do painel administrativo (Django Admin personalizado). Pode gerenciar todos os usuários, produtoras, eventos e vendas.
- **Vendedor da Plataforma:** Acessa o painel administrativo com permissões limitadas. Sua função é cadastrar e gerenciar as **Produtoras** e os **Coordenadores** que adquiriram a solução.
- **Coordenador (Produtora):** Acessa a área restrita da aplicação web. É responsável pelo CRUD (cadastro, leitura, edição e exclusão) de **Eventos** e **Ingressos** e pela alocação dos **Organizadores** que trabalharão no dia do evento.
- **Organizador (Staff):** Acessa a aplicação web no dia do evento. Sua única permissão é visualizar a lista de ingressos vendidos para o seu evento e validar (dar "baixa" ou "check-in") na entrada do participante.
- **Participante (Usuário Final):** Acessa a área pública e a área de cliente da aplicação. Pode visualizar eventos disponíveis, realizar o próprio cadastro, comprar ingressos e visualizar sua carteira de ingressos adquiridos.

### Regras de negócio principais

1. **Hierarquia de Criação:** Um evento só pode existir se estiver vinculado a uma Produtora e criado por um Coordenador.
2. **Vínculo de Staff:** Organizadores só podem validar ingressos de eventos para os quais foram explicitamente designados pelo Coordenador.
3. **Compra de Ingressos:** Um participante pode comprar múltiplos ingressos, mas cada ingresso gera um ticket único (identificado por um código UUID) para validação individual na porta.
4. **Validação:** Um ingresso só pode ser validado uma única vez. Uma vez que o Organizador marca o ticket como "utilizado", o sistema bloqueia novas tentativas de entrada.
5. **Disponibilidade:** Apenas eventos publicados e com data a partir de hoje aparecem na vitrine e podem ter ingressos vendidos.

## Principais rotas

| Rota                                                     | Descrição                                  | Acesso                              |
| -------------------------------------------------------- | ------------------------------------------ | ----------------------------------- |
| `/`                                                      | Vitrine de eventos                         | Público                             |
| `/eventos/<id>/`                                         | Detalhes do evento                         | Público                             |
| `/contas/entrar/`, `/contas/sair/`, `/contas/cadastrar/` | Login, logout e cadastro                   | Público                             |
| `/carrinho/`                                             | Carrinho de compras                        | Público (compra exige participante) |
| `/meus-ingressos/`                                       | Carteira de ingressos                      | Participante                        |
| `/painel/dashboard/`                                     | Dashboard da produtora                     | Coordenador                         |
| `/painel/eventos/`                                       | Gestão de eventos (criar, editar, excluir) | Coordenador                         |
| `/portaria/eventos/`                                     | Eventos em que o organizador está alocado  | Organizador                         |
| `/portaria/<id>/`                                        | Lista de presença do evento                | Organizador                         |
| `/portaria/`                                             | Validação (check-in) de ingressos          | Organizador                         |
| `/admin/`                                                | Painel administrativo                      | Administrador e Vendedor            |

## Estrutura do projeto

```text
.
├── code/                    # Projeto Django
│   ├── config/              # Configurações, URLs e WSGI
│   ├── contas/              # Usuários, perfis, login e cadastro
│   ├── eventos/             # Produtoras, eventos, tipos de ingresso e dashboard
│   │   └── management/commands/popular_banco.py
│   ├── ingressos/           # Carrinho, pedidos, ingressos e check-in
│   ├── static/              # CSS, JS, imagens e Bootstrap
│   ├── templates/           # Templates HTML (inclui o admin personalizado)
│   └── manage.py
├── Dockerfile
├── docker-compose.yml
├── docker-entrypoint.sh     # Aplica as migrações e inicia o servidor
├── requirements.txt
└── .env.example
```

### Divisão de aplicativos

- **`contas`: Gestão de Identidade e Perfis:** focado exclusivamente no requisito de autenticação e perfis distintos.
  - Gerencia o modelo de Usuário Customizado (Custom User), com login por e-mail, e o login/logout.
  - Contém os perfis (Administrador, Vendedor, Coordenador, Organizador e Participante) e a qual Produtora um usuário pertence.

- **`eventos` (Gestão de Catálogo e Produção):**
  - Focado no CRUD de entidades do negócio.
  - É o domínio do Coordenador.
  - Contém os modelos de **Produtora**, **Evento** (nome, data, local, descrição, imagens) e os **Tipos de Ingressos/Lotes** (Pista Lote 1 - R$ 50, Camarote VIP - R$ 100).
  - Contém a relação de quais Organizadores (staff) estão alocados para trabalhar em qual Evento.

- **`ingressos`: Motor de Vendas e Validação**
  - É aqui que o Participante e o Organizador interagem com o sistema.
  - Contém o carrinho de compras e o modelo de **Pedido/Venda** (transação do comprador).
  - Contém o modelo do **Ingresso Gerado** (o ticket individual único do participante, vinculado a um Tipo de Ingresso do app `eventos`).
  - Gerencia a lógica de validação na porta (o check-in feito pelo Organizador mudando o status do ingresso para "utilizado").

Essa abordagem de 3 apps atende com folga a exigência técnica de possuir pelo menos dois aplicativos, evita que o código vire uma "salada" e demonstra para o professor que o grupo compreendeu o conceito de separação de responsabilidades (cada app cuida de uma parte do fluxo de dados, independente de quem está logado).
