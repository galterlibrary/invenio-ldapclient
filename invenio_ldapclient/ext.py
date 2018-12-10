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
        if 'COVER_TEMPLATE' in app.config:
            app.config.setdefault(
                'LDAPCLIENT_BASE_TEMPLATE',
                app.config['COVER_TEMPLATE'],
            )

        for k in dir(config):
            if k.startswith('LDAPCLIENT_'):
                app.config.setdefault(k, getattr(config, k))

        if not app.config['LDAPCLIENT_AUTHENTICATION']:
            return

        if app.config['LDAPCLIENT_EXCLUSIVE_AUTHENTICATION']:
            @app.before_first_request
            def ldap_login_view_setup():
                from .views import ldap_login
                app.view_functions['security.login'] = ldap_login
                app.config['SECURITY_CONFIRMABLE'] = False
                app.config['SECURITY_RECOVERABLE'] = False
                app.config['SECURITY_REGISTERABLE'] = False
                app.config['SECURITY_CHANGEABLE'] = False
                app.config['USERPROFILES_EMAIL_ENABLED'] = False

            app.config['SECURITY_LOGIN_USER_TEMPLATE'] = (
                app.config['LDAPCLIENT_LOGIN_USER_TEMPLATE']
            )
