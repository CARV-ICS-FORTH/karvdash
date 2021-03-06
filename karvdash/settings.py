# Copyright [2019] [FORTH-ICS]
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Django settings for karvdash project.

Generated by 'django-admin startproject' using Django 3.0.2.

For more information on this file, see
https://docs.djangoproject.com/en/3.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.0/ref/settings/
"""

import os


# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('DJANGO_SECRET', '%ad&%4*!xpf*$wd3^t56+#ode4=@y^ju_t+j9f+20ajsta^gog')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True if os.getenv('DJANGO_DEBUG', '1') else False

ALLOWED_HOSTS = ['*']


# Version
try:
    with open(os.path.join(BASE_DIR, 'VERSION'), 'rb') as f:
        VERSION = f.read().decode().strip().lstrip('v')
except:
    raise
    VERSION = 'unknown'


# Application definition

INSTALLED_APPS = [
    'dashboard.apps.DashboardConfig',
    'crispy_forms',
    'impersonate',
    'chunked_upload',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'impersonate.middleware.ImpersonateMiddleware',
    'karvdash.middleware.AddLogUserHeaderMiddleware',
]

ROOT_URLCONF = 'karvdash.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'dashboard.context_processors.settings',
            ],
        },
    },
]

WSGI_APPLICATION = 'karvdash.wsgi.application'


# Password hashes

PASSWORD_HASHERS = [
    'dashboard.hashers.APR1PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
]

# Database
# https://docs.djangoproject.com/en/3.0/ref/settings/#databases

DATABASE_DIR = os.getenv('KARVDASH_DATABASE_DIR', os.path.join(BASE_DIR, 'db'))
if not os.path.exists(DATABASE_DIR):
    os.makedirs(DATABASE_DIR)

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(DATABASE_DIR, 'db.sqlite3'),
    }
}

# Password validation
# https://docs.djangoproject.com/en/3.0/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/3.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.0/howto/static-files/

STATIC_URL = '/static/'

STATIC_ROOT = os.path.join(BASE_DIR, 'static')


# Authentication

AUTHENTICATION_BACKENDS = ['dashboard.auth_backends.ProxiedModelBackend']
LOGIN_URL = '/login'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'


# Form styling with crispy-forms

CRISPY_TEMPLATE_PACK = 'bootstrap4'


# Bootstrap compatible messages

from django.contrib.messages import constants as messages # noqa: E402

MESSAGE_TAGS = {
    messages.DEBUG: 'alert-info',
    messages.INFO: 'alert-info',
    messages.SUCCESS: 'alert-success',
    messages.WARNING: 'alert-warning',
    messages.ERROR: 'alert-danger',
}


# File management domains

FILES_URL = os.getenv('KARVDASH_FILES_URL', 'file://%s' % BASE_DIR)
FILES_MOUNT_DIR = os.getenv('KARVDASH_FILES_MOUNT_DIR', BASE_DIR)


# Upload path
CHUNKED_UPLOAD_PATH = os.getenv('KARVDASH_UPLOADS_DIR', os.path.join(BASE_DIR, 'uploads'))


# Docker registry endpoint

DOCKER_REGISTRY = os.getenv('KARVDASH_DOCKER_REGISTRY', '')
DOCKER_REGISTRY_NO_VERIFY = True if os.getenv('KARVDASH_DOCKER_REGISTRY_NO_VERIFY', '') else False


# Service templates

SYSTEM_TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')
SERVICE_TEMPLATE_DIR = os.path.join(DATABASE_DIR, 'templates')
SERVICE_DATABASE_DIR = os.path.join(DATABASE_DIR, 'services')


# Password file export

HTPASSWD_EXPORT_DIR = os.getenv('KARVDASH_HTPASSWD_EXPORT_DIR')


# API URL

SERVICE_DOMAIN = os.getenv('KARVDASH_SERVICE_DOMAIN')


# Ingress domain

INGRESS_URL = os.getenv('KARVDASH_INGRESS_URL', 'http://localtest.me')


# Theme

DASHBOARD_TITLE = os.getenv('KARVDASH_DASHBOARD_TITLE', 'Dashboard')
DASHBOARD_THEME = os.getenv('KARVDASH_DASHBOARD_THEME', 'evolve')
ISSUES_URL = os.getenv('KARVDASH_ISSUES_URL')


# Datasets

DATASETS_AVAILABLE = True if os.getenv('KARVDASH_DATASETS_AVAILABLE', '') else False
if not DATASETS_AVAILABLE and not FILES_URL.startswith('file://'):
    raise ValueError('Datasets are required for non-file files URL')


# Local directories allowed to be mounted in containers (in addition to file domains)

ALLOWED_HOSTPATH_DIRS = [d.strip() for d in os.getenv('KARVDASH_ALLOWED_HOSTPATH_DIRS', '').split(':') if d.strip()]


# Disabled templates

DISABLED_SERVICE_TEMPLATES = []
DISABLED_SERVICE_TEMPLATES_FILE = os.getenv('KARVDASH_DISABLED_SERVICE_TEMPLATES_FILE')
if DISABLED_SERVICE_TEMPLATES_FILE and os.path.isfile(DISABLED_SERVICE_TEMPLATES_FILE):
    with open(DISABLED_SERVICE_TEMPLATES_FILE) as f:
        DISABLED_SERVICE_TEMPLATES = [line.strip() for line in f if line.strip()]

DISABLED_DATASET_TEMPLATES = []
DISABLED_DATASET_TEMPLATES_FILE = os.getenv('KARVDASH_DISABLED_DATASET_TEMPLATES_FILE')
if DISABLED_DATASET_TEMPLATES_FILE and os.path.isfile(DISABLED_DATASET_TEMPLATES_FILE):
    with open(DISABLED_DATASET_TEMPLATES_FILE) as f:
        DISABLED_DATASET_TEMPLATES = [line.strip() for line in f if line.strip()]


# Preconfigured service URL prefixes

import re # noqa: E402

SERVICE_URL_PREFIXES = []
SERVICE_URL_PREFIXES_FILE = os.getenv('KARVDASH_SERVICE_URL_PREFIXES_FILE')
if SERVICE_URL_PREFIXES_FILE and os.path.isfile(SERVICE_URL_PREFIXES_FILE):
    with open(SERVICE_URL_PREFIXES_FILE) as f:
        SERVICE_URL_PREFIXES = [line.strip() for line in f if line.strip()]

for service_url_prefix in SERVICE_URL_PREFIXES:
    if not bool(re.match(r'^[0-9a-zA-Z_\-]+$', service_url_prefix)):
        raise ValueError('Invalid characters in service URL prefix')

GENERATE_SERVICE_URLS = False if SERVICE_URL_PREFIXES else True
