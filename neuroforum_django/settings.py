"""
Django settings for neuroforum_django project.

Generated by 'django-admin startproject' using Django 5.2.1.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.2/ref/settings/
"""

import os
import sys

from pathlib import Path
from dotenv import load_dotenv
from sshtunnel import SSHTunnelForwarder

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=BASE_DIR / '.env')

IS_GITHUB_CI = os.getenv("CI", "").lower() == "true"
IS_DOCKER = os.getenv("IS_DOCKER", "false").lower() == "true"

IS_LOCAL = not IS_DOCKER and not IS_GITHUB_CI

# after load_dotenv
REDIS_HOST = os.getenv("REDIS_HOST",
               "127.0.0.1" if os.getenv("DEBUG","True")=="True" else "redis")

ssh_key_content = os.getenv('SSH_PRIVATE_KEY')
pem_path = BASE_DIR / "id_rsa"

if ssh_key_content:
    with open(pem_path, "w") as pem_file:
        pem_file.write(ssh_key_content.replace("\\n", "\n"))
    os.chmod(pem_path, 0o600)

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# Load Django SECRET_KEY securely from environment
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY')
if not SECRET_KEY:
    raise ValueError("DJANGO_SECRET_KEY not set in environment variables.")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv("DEBUG", "True") == "True"

ALLOWED_HOSTS = ['18.216.113.147', '127.0.0.1',
                 'neuroforum.ddns.net']

# CSRF_TRUST
CSRF_TRUSTED_ORIGINS = [
    "https://neuroforum.ddns.net"
]

if not DEBUG:
    SESSION_COOKIE_SECURE   = True
    CSRF_COOKIE_SECURE      = True
    SESSION_COOKIE_DOMAIN   = "neuroforum.ddns.net"
else:
    # local dev: allow cookies on localhost over HTTP
    SESSION_COOKIE_SECURE   = False
    CSRF_COOKIE_SECURE      = False
    SESSION_COOKIE_DOMAIN   = None

SESSION_COOKIE_HTTPONLY = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

SECURE_HSTS_SECONDS = 31536000         # Enforce HTTPS with HSTS
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

def create_ssh_tunnel():
    """
    Creates an SSH tunnel to the remote MySQL server.
    """
    pem_path = BASE_DIR / "id_rsa"

    if not pem_path.exists():
        raise FileNotFoundError(f"SSH key not found at {pem_path}")

    tunnel = SSHTunnelForwarder(
        ('18.216.113.147', 22),
        ssh_username='student16',
        ssh_pkey=str(pem_path),  # Convert Path to str for compatibility
        remote_bind_address=('127.0.0.1', 3306),
        local_bind_address=('127.0.0.1',)
    )

    tunnel.start()
    print(
        f"[SSH TUNNEL] Running at {tunnel.local_bind_host}:{tunnel.local_bind_port}")
    return tunnel


# Application definition
INSTALLED_APPS = [
    'forum',
    'django_recaptcha',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'channels',
    'cryptography',
]

ASGI_APPLICATION = 'neuroforum_django.asgi.application'


CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [(REDIS_HOST, 6379)],
        },
    },
}

MIDDLEWARE = [
    'forum.middleware.IPBanMiddleware',    
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "forum.services.custom_session_middleware.CustomSessionMiddleware",
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'neuroforum_django.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'forum.context_processors.chat_partners_processor',
            ],
        },
    },
]

WSGI_APPLICATION = 'neuroforum_django.wsgi.application'

# Create the SSH tunnel

if DEBUG and not IS_GITHUB_CI and not IS_DOCKER:

    tunnel = create_ssh_tunnel()
    db_host = tunnel.local_bind_host
    db_port = tunnel.local_bind_port
    print(f"[Local Dev] SSH tunnel active at {db_host}:{db_port}")
else:

    db_host = os.getenv("DB_HOST", "db")
    db_port = os.getenv("DB_PORT", "3306")
    print(f"[Docker/CI] Using DB_HOST={db_host}:{db_port}")

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.getenv('MYSQL_DATABASE'),
        'USER': os.getenv('MYSQL_USER'),
        'PASSWORD': os.getenv('MYSQL_PASSWORD'),
        'HOST': db_host,
        'PORT': db_port,  
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        },
        'TEST': {
            'NAME': os.getenv("DJANGO_TEST_DATABASE", "test_neuroforum_database"),
        }
    }
}

DATABASES = DATABASES

if os.getenv("CI") == "true":
    DATABASES["default"]["TEST"] = {
        "NAME": os.getenv("DJANGO_TEST_DATABASE", "test_neuroforum_database"),
        "MIRROR": None,
        "DEPENDENCIES": [],
        "SERIALIZE": False,
        "CREATE_DB": False, 
    }

# Email configuration
EMAIL_BACKEND = os.getenv('EMAIL_BACKEND')
EMAIL_HOST = os.getenv('EMAIL_HOST')
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True') == 'True'
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Asia/Singapore'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = '/static/'

STATICFILES_DIRS = (os.path.join(BASE_DIR, 'forum/templates/static'),)

X_FRAME_OPTIONS = 'SAMEORIGIN'

LOGIN_URL = "/login/"

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ReCaptcha settings
RECAPTCHA_PUBLIC_KEY = os.getenv('RECAPTCHA_PUBLIC_KEY', 'dummy-public-key')
RECAPTCHA_PRIVATE_KEY = os.getenv('RECAPTCHA_PRIVATE_KEY', 'dummy-private-key')

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': f'redis://{REDIS_HOST}:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

running_pytest = any("pytest" in arg for arg in sys.argv)
if os.getenv("CI", "").lower() == "true" or running_pytest:
    # Django cache → locmem
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }
    }

    # Channels → in-memory channel layer
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer",
        },
    }