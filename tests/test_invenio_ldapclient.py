# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 Galter Health Sciences Library & Learning Center.
#
# Invenio-LDAPClient is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Module tests."""

from __future__ import absolute_import, print_function

import pytest
from flask import Flask

from invenio_ldapclient import InvenioLDAPClient


def test_version():
    """Test version import."""
    from invenio_ldapclient import __version__
    assert __version__


def test_init():
    """Test extension initialization."""
    app = Flask('testapp')
    ext = InvenioLDAPClient(app)
    assert 'invenio-ldapclient' in app.extensions

    app = Flask('testapp')
    ext = InvenioLDAPClient()
    assert 'invenio-ldapclient' not in app.extensions
    ext.init_app(app)
    assert 'invenio-ldapclient' in app.extensions
    assert app.config['LDAPCLIENT_AUTHENTICATION'] is True
    assert app.config['LDAPCLIENT_AUTO_REGISTRATION'] is True
    assert app.config['LDAPCLIENT_EXCLUSIVE_AUTHENTICATION'] is True
    assert app.config['LDAPCLIENT_LOGIN_USER_TEMPLATE'] == \
        'invenio_ldapclient/login_user.html'
    assert app.config['LDAPCLIENT_USERNAME_PLACEHOLDER'] == 'Username'
    assert app.config['LDAPCLIENT_SERVER_PORT'] == 389
    assert app.config['LDAPCLIENT_USE_SSL'] is False
    assert app.config['LDAPCLIENT_TLS'] is None
    assert app.config['LDAPCLIENT_CUSTOM_CONNECTION'] is None
    assert app.config['LDAPCLIENT_USERNAME_ATTRIBUTE'] == 'uid'
    assert app.config['LDAPCLIENT_EMAIL_ATTRIBUTE'] == 'mail'
    assert app.config['LDAPCLIENT_FULL_NAME_ATTRIBUTE'] == 'displayName'
    assert app.config['LDAPCLIENT_SEARCH_ATTRIBUTES'] == [
        app.config['LDAPCLIENT_USERNAME_ATTRIBUTE'],
        app.config['LDAPCLIENT_EMAIL_ATTRIBUTE'],
        app.config['LDAPCLIENT_FULL_NAME_ATTRIBUTE']
    ]

    # import pytest; pytest.set_trace()
    assert app.config['SECURITY_LOGIN_USER_TEMPLATE'] == \
        app.config['LDAPCLIENT_LOGIN_USER_TEMPLATE']


def test_init_non_exclusive_LDAP_auth():
    app = Flask('testapp')
    app.config['LDAPCLIENT_EXCLUSIVE_AUTHENTICATION'] = False
    ext = InvenioLDAPClient(app)
    ext.init_app(app)
    assert app.config['LDAPCLIENT_EXCLUSIVE_AUTHENTICATION'] is False
    with pytest.raises(KeyError, message='SECURITY_LOGIN_USER_TEMPLATE'):
        assert app.config['SECURITY_LOGIN_USER_TEMPLATE'] == \
            app.config['LDAPCLIENT_LOGIN_USER_TEMPLATE']


def test_view(app):
    """Test view."""
    InvenioLDAPClient(app)
    # FIXME later
    # with app.test_client() as client:
    #    res = client.get("/")
    #
    #    assert res.status_code == 200
    #    assert 'Welcome to Invenio-LDAPClient' in str(res.data)
