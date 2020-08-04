__author__ = "Cobbin"
import os

DEBUG = True
ADMINS = frozenset([
    os.environ.get('ADMINS_EMAIL')
])
