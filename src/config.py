__author__ = "Cobbin"
import os

DEBUG = True
ADMINS = frozenset([
    "cobbin@email.com", os.environ.get('ADMINS_EMAIL')
])