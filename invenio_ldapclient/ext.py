# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 Galter Health Sciences Library & Learning Center.
#
# Invenio-LDAPClient is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Invenio v3 LDAP client for authentication and user attributes population."""

from __future__ import absolute_import, print_function

from . import config
from .views import blueprint
from .forms import login_form_factory


class InvenioLDAPClient(object):
    """Invenio-LDAPClient extension."""

    def __init__(self, app=None):
        """Extension initialization."""
        if app:
            self.init_app(app)

    def init_app(self, app):
        """Flask application initialization."""
        self.init_config(app)
        app.register_blueprint(blueprint)
        app.extensions['invenio-ldapclient'] = self

    def init_config(self, app):
        """Initialize configuration."""
        # Use theme's base template if theme is installed
        if 'BASE_TEMPLATE' in app.config:
            app.config.setdefault(
                'LDAPCLIENT_BASE_TEMPLATE',
                app.config['BASE_TEMPLATE'],
            )
        for k in dir(config):
            if k.startswith('LDAPCLIENT_'):
                app.config.setdefault(k, getattr(config, k))

        #from IPython import embed; embed()
        if app.config['LDAPCLIENT_EXCLUSIVE_AUTHENTICATION']:
            app.extensions['security'].login_form = (
                login_form_factory(app.extensions['security'].login_form, app)
            )

            app.config['SECURITY_LOGIN_USER_TEMPLATE'] = (
                'invenio_ldapclient/login_user.html'
            )
