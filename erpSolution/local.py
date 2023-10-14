from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv("DEBUG")

ALLOWED_HOSTS = ["*", "localhost"]

#MySQL Database Engine
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.getenv("DJANGO_DATABASE_NAME"),
        'USER': os.getenv("DJANGO_DATABASE_USER"),
        'PASSWORD': os.getenv("DJANGO_DATABASE_PASSWORD"),
        'HOST': os.getenv("DJANGO_DATABASE_HOST"),
        'PORT': '3306',
        'OPTIONS': {
            'sql_mode': 'traditional',
        }
    }
}

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.1/howto/static-files/

STATIC_URL = '/static/'

STATICFILES_DIRS = (
    BASE_DIR / "static",
)

MEDIA_URL = '/media/'
MEDIA_ROOT = (BASE_DIR / "media")

CORS_ORIGIN_ALLOW_ALL = True

LOGIN_REDIRECT_URL = 'dashboard'

LOGIN_URL = 'view_login'

LOGOUT_REDIRECT_URL = 'view_login'


DEFAULT_FROM_EMAIL = os.getenv("DJANGO_DEFAULT_EMAIL")

EMAIL_USE_TLS = True
# EMAIL_USE_SSL = True
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_HOST_USER = os.getenv("DJANGO_EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("DJANGO_EMAIL_HOST_PASSWORD")

# Email section
# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'


CORS_ALLOWED_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://192.168.111.115:80"
]

CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]



