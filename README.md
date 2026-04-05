# 📚 Tarefas Diárias (Study Task)

[![CI Pipeline](https://github.com/KaioHerculano/daily_task/actions/workflows/ci.yml/badge.svg)](https://github.com/KaioHerculano/daily_task/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.11+-blue?style=for-the-badge&logo=python)
![Django](https://img.shields.io/badge/Django-4.2+-green?style=for-the-badge&logo=django)
![Poetry](https://img.shields.io/badge/Poetry-blueviolet?style=for-the-badge&logo=poetry)
![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3-purple?style=for-the-badge&logo=bootstrap)

Uma aplicação web construída com Django para acompanhar hábitos de estudo diários, ajudando a manter consistência, disciplina e evolução ao longo do tempo.

---

## ✨ Funcionalidades Principais

- 🔐 **Autenticação Completa:** Cadastro, login, logout e recuperação de senha por e-mail.
- 📊 **Dashboard Interativo:** Visualização clara dos dados de estudo.
- 🔥 **Streak (Ofensiva):** Sequência atual e melhor sequência de dias estudados.
- 🎯 **Metas Semanais:** Definição e acompanhamento de progresso semanal.
- 📧 **Notificações Assíncronas:** Lembretes automáticos via Celery + Redis.
- 📈 **Gráficos:** Frequência semanal e tendência mensal.
- 📅 **Calendário Visual:** Dias estudados destacados.
- 🌙 **Tema Claro/Escuro:** Preferência persistida.
- 📱 **Design Responsivo:** Mobile e desktop.

---

## 📸 Screenshots

### 🔐 Autenticação

#### Cadastro
![Cadastro](screenshots/criar_sua_conta.png)

#### Login
![Login](screenshots/login.png)

#### Redefinição de senha
![Reset](screenshots/redefinir_senha.png)

---

### 👤 Perfil
![Perfil](screenshots/meu_perfil.png)

---

### 📊 Dashboard
![Dashboard](screenshots/dashboard1.png)

---

## 🛠️ Tecnologias Utilizadas

- **Backend:** Python, Django, Celery, Redis
- **Frontend:** HTML, CSS, JavaScript, Bootstrap 5, Chart.js
- **Banco de Dados:** SQLite (dev) / PostgreSQL (produção)
- **Infraestrutura:** Docker, Docker Compose
- **Qualidade:** Poetry, Makefile, Flake8, Black, Coverage, GitHub Actions

---

## 🚀 Instalação e Execução

### 🧪 Ambiente Local com Poetry

```bash
git clone https://github.com/KaioHerculano/daily_task
cd daily_task

poetry install
poetry shell

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

---

## ⚙️ Executando com Docker

### 1. Configure o `.env`

```env
SECRET_KEY="sua-secret-key"
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

POSTGRES_DB=daily_db
POSTGRES_USER=usuario_db
POSTGRES_PASSWORD=senha_forte_db
POSTGRES_HOST=db
POSTGRES_PORT=5432

EMAIL_HOST_USER=resend
EMAIL_HOST_PASSWORD=sua_api_key_do_resend
DEFAULT_FROM_EMAIL=Seu Nome <email@dominio.com>
BASE_URL=http://localhost:8000
```

> ⚠️ Importante: Utilize o Resend como provedor de e-mail. É necessário configurar uma API Key válida e verificar seu domínio.

### 2. Suba os containers

```bash
docker-compose up --build
```

### 3. Acesse

http://localhost:8000

---

## ⚡ Comandos úteis (Makefile)

```bash
make run
make test
make test-coverage
make format
make lint
```

---

## 👀 Roadmap

- 🏆 Sistema de Conquistas / Badges
- 📄 Exportação de relatórios em PDF
- 📊 Analytics avançado

---

## 📅 Status do Projeto

Em desenvolvimento ativo 🚀 Contribuições são bem-vindas!
