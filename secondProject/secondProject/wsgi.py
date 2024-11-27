"""
WSGI config for secondProject project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/wsgi/
"""
#help

import os
from django.core.wsgi import get_wsgi_application

settings_module = 'secondProject.secondProject.deployment' if 'WEBSITE_HOSTNAME' in os.environ else 'secondProject.secondProject.settings'
os.environ.setdefault('DJANGO_SETTINGS_MODULE', settings_module)

application = get_wsgi_application()
