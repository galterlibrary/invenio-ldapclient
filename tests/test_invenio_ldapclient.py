# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 Galter Health Sciences Library & Learning Center.
#
# Invenio-LDAPClient is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Module tests."""

from __future__ import absolute_import, print_function

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
    assert app.config['LDAPCLIENT_EXCLUSIVE_AUTHENTICATION'] is False


def test_view(app):
    """Test view."""
    InvenioLDAPClient(app)
    with app.test_client() as client:
        res = client.get("/")
        assert res.status_code == 200
        assert 'Welcome to Invenio-LDAPClient' in str(res.data)
