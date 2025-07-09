# NeuroForum

NeuroForum is a collaborative web platform built with Django that enables users to engage in discussions, share resources, and manage posts in a secure, modular environment. This repository is structured for scalability, maintainability, and ease of quality assurance testing.

## Features

- User registration, login, and session management
- Post creation, editing, and commenting
- Admin moderation interface
- Linting, testing, and security enforcement via GitHub Actions
- Dockerized environment for easy setup

## To Use

### Clone the repo
```
git clone https://github.com/auritot/NeuroForum.git
cd NeuroForum
```
### Create a virtual environment
```
python -m venv venv
source venv/bin/activate 
```
## Linux / WSL
### Install system dependencies
```
sudo apt update
sudo apt install -y \
  python3-dev \
  default-libmysqlclient-dev \
  build-essential \
  pkg-config \
  redis-server
```
### Install Python packages
```
pip install -r requirements.txt
```
### Create your .env file
```
cat > .env <<EOF
DJANGO_SECRET_KEY=your-secret-key
DEBUG=True

# Database
MYSQL_DATABASE=neuroforum_db
MYSQL_USER=neuroforum_user
MYSQL_PASSWORD=your-db-password
MYSQL_HOST=localhost
MYSQL_PORT=3306

# Redis
REDIS_HOST=127.0.0.1

# Encryption
FERNET_KEY=$(python3 - <<PYCODE
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
PYCODE
)

# ReCAPTCHA Keys (https://developers.google.com/recaptcha/)
RECAPTCHA_PUBLIC_KEY='<Generated Public Key>'
RECAPTCHA_PRIVATE_KEY='<Generated Private Key>'

# (Optional) email in console
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_USE_TLS=True
EMAIL_PORT=587
EMAIL_HOST_USER=<Sender Gmail account>
EMAIL_HOST_PASSWORD=<Gmail app-specific password>

# (Optional) sonarcube configuration
SONARQUBE_HOST_URL=<URL to sonarqube interface>
SONARQUBE_JDBC_URL=jdbc:postgresql://db_sonar:5432/sonarqube
SONARQUBE_JDBC_USERNAME=<sonarcube username>
SONARQUBE_JDBC_PASSWORD=<sonarcube password>
POSTGRES_USER=<sonarcube postgre username>
POSTGRES_PASSWORD=<sonarcube postgre password>
POSTGRES_DB=<sonarcube postgre database name>
IS_DOCKER=true
CI=false
EOF
```
### Start Redis
```
sudo service redis-server start
```
### Run migrations & create superuser
```
python manage.py migrate
python manage.py createsuperuser
```
### Run Server
```
python manage.py runserver
```
## Windows
### Use docker desktop
```
docker run -d --name redis -p 6379:6379 redis:7
```
### Go into virtualenv & install pkgs
```
venv\Scripts\activate
pip install -r requirements.txt
```
### Create your .env file
```
@"
DJANGO_SECRET_KEY=your-secret-key
DEBUG=True

# Database
MYSQL_DATABASE=neuroforum_db
MYSQL_USER=neuroforum_user
MYSQL_PASSWORD=your-db-password
MYSQL_HOST=localhost
MYSQL_PORT=3306

# Redis
REDIS_HOST=127.0.0.1

# Encryption
FERNET_KEY=$(python - <<PYCODE
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
PYCODE
)

# ReCAPTCHA Keys (https://developers.google.com/recaptcha/)
RECAPTCHA_PUBLIC_KEY='<Generated Public Key>'
RECAPTCHA_PRIVATE_KEY='<Generated Private Key>'

# (Optional) email in console
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_USE_TLS=True
EMAIL_PORT=587
EMAIL_HOST_USER=<Sender Gmail account>
EMAIL_HOST_PASSWORD=<Gmail app-specific password>

# (Optional) sonarcube configuration
SONARQUBE_HOST_URL=<URL to sonarqube interface>
SONARQUBE_JDBC_URL=jdbc:postgresql://db_sonar:5432/sonarqube
SONARQUBE_JDBC_USERNAME=<sonarcube username>
SONARQUBE_JDBC_PASSWORD=<sonarcube password>
POSTGRES_USER=<sonarcube postgre username>
POSTGRES_PASSWORD=<sonarcube postgre password>
POSTGRES_DB=<sonarcube postgre database name>
IS_DOCKER=true
CI=false
"@ | Out-File -Encoding utf8 .env
```
### Run migrations & create superuser
```
python manage.py migrate
python manage.py createsuperuser
```
### Run Server
```
python manage.py runserver
```
