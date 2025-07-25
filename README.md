#  Tarefas Diárias (Study Task)

![Python](https://img.shields.io/badge/Python-3.11+-blue?style=for-the-badge&logo=python)
![Django](https://img.shields.io/badge/Django-4.2+-green?style=for-the-badge&logo=django)
![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3-purple?style=for-the-badge&logo=bootstrap)

Uma aplicação web construída com Django para acompanhar e visualizar seus hábitos de estudo diários, ajudando a manter a consistência e a motivação.
## Cadastre-se
![Cadastre-se](screenshots/criar_sua_conta.png)
## Login
![Login](screenshots/login.png)
## Redefinir Senha
![Redefinir Senha](screenshots/redefinir_senha.png)
## Perfil
![Perfil](screenshots/meu_perfil.png)
## Dashboard
![Dashboard](screenshots/dashboard.png)
![Dashboard](screenshots/dashboard1.png)

## ✨ Funcionalidades Principais

- **Autenticação de Usuário Completa:** Cadastro, Login, Logout, "Esqueci minha Senha" e Perfil de Usuário.
- **Dashboard Interativo:** Visualize seus dados de estudo de forma clara e objetiva.
- **Gráfico de Frequência Semanal:** Mostra a atividade nos últimos 7 dias.
- **Gráfico de Tendência Mensal:** Acompanha o progresso ao longo dos meses e anos.
- **Calendário Visual:** Dias estudados destacados mês a mês.
- **Seletor de Tema:** Alterna entre temas claro e escuro, com persistência.
- **Design Responsivo:** Totalmente adaptável para desktop e mobile.

---

## 🛠️ Tecnologias Utilizadas

- **Backend:** Python, Django
- **Frontend:** HTML, CSS, JavaScript, Bootstrap 5, Chart.js
- **Banco de Dados (Dev):** SQLite3
- **Deploy Containerizado:** Docker, Docker Compose, PostgreSQL

---

## 🚀 Instalação e Execução

### 🧪 Localmente (Ambiente Virtual)

#### 1. Clone o Repositório

```bash
<<<<<<< HEAD
git clone https://github.com/seu-usuario/seu-repositorio.git
=======
git clone https://github.com/KaioHerculano/daily_task
>>>>>>> 020f46a (update title)
cd seu-repositorio
```

#### 2. Crie e Ative um Ambiente Virtual

```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

#### 3. Instale as Dependências

```bash
pip install -r requirements.txt
```

#### 4. Aplique as Migrações e Crie um Superusuário

```bash
python manage.py migrate
python manage.py createsuperuser
```

---

### ⚙️ Executando com Docker

#### 1. Configure o arquivo `.env`

```env
SECRET_KEY="sua-secret-key"
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

POSTGRES_DB=daily_db
POSTGRES_USER=usuario
POSTGRES_PASSWORD=senha
POSTGRES_HOST=daily_task_db
POSTGRES_PORT=5432
PORT=8000
```

#### 2. Execute com Docker Compose

```bash
docker-compose up --build
```

#### 3. Acesse a aplicação

Abra o navegador em:

```
http://localhost:8000
```

---

## 👀 Em Breve

- Notificações por e-mail
- Exportar relatórios em PDF

---

## 📅 Status do Projeto

> Em desenvolvimento ativo. Contribuições são bem-vindas!


