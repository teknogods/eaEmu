#!/usr/bin/env python2.6
from django.core.management import execute_manager
try:
    import eaEmu.dj.settings # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write('''Error: Can't find eaEmu.dj.settings from %r. It appears you've customized things.
You'll have to run django-admin.py, passing it your settings module.
''' % __file__)
    sys.exit(1)

if __name__ == "__main__":
    execute_manager(settings)
