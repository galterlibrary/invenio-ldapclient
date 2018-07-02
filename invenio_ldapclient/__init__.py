# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 Galter Health Sciences Library & Learning Center.
#
# Invenio-LDAPClient is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Invenio v3 LDAP client for authentication and user attributes population."""

from __future__ import absolute_import, print_function

from .ext import InvenioLDAPClient
from .version import __version__

__all__ = ('__version__', 'InvenioLDAPClient')
