"""
WSGI config for tts_sever project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/wsgi/
"""

import os
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tts_sever.settings")

if sys.version_info >= (3, 14):
    from tts_sever.django_py314_patch import apply as _patch_django_context

    _patch_django_context()

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
