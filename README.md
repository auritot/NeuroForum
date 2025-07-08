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
git clone https://github.com/auritot/NeuroForum.git </br>
cd NeuroForum
```
### Create a virtual environment
```
python -m venv venv
source venv/bin/activate 
```
### Install dependencies
```
pip install -r requirements.txt
```
### Set up environment variables

Create a .env file in the root directory

```
DJANGO_SECRET_KEY=your-secret-key
DEBUG=True
MYSQL_DATABASE=neuroforum_db
MYSQL_USER=neuroforum_user
MYSQL_PASSWORD=yourpassword
MYSQL_HOST=localhost
MYSQL_PORT=3306
```

### Run database migrations
```
python manage.py migrate
```
### Create a superuser
```
python manage.py createsuperuser
```
### Run the server
```
python manage.py runserver
```
