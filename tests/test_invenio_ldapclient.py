# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 Galter Health Sciences Library & Learning Center.
#
# Invenio-LDAPClient is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Module tests."""

from __future__ import absolute_import, print_function

from unittest.mock import MagicMock, Mock, patch

import invenio_accounts
import ldap3
import pytest
from flask import Flask
from invenio_accounts.models import User
from invenio_userprofiles.models import UserProfile
from werkzeug.local import LocalProxy

import invenio_ldapclient
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
    assert app.config['LDAPCLIENT_FIND_BY_EMAIL'] is True
    assert app.config['LDAPCLIENT_AUTO_REGISTRATION'] is True
    assert app.config['LDAPCLIENT_EXCLUSIVE_AUTHENTICATION'] is True
    assert app.config['LDAPCLIENT_LOGIN_USER_TEMPLATE'] == \
        'invenio_ldapclient/login_user.html'
    assert app.config['LDAPCLIENT_USERNAME_PLACEHOLDER'] == 'Username'
    assert app.config['LDAPCLIENT_SERVER_HOSTNAME'] == 'example.com'
    assert app.config['LDAPCLIENT_SERVER_PORT'] == 389
    assert app.config['LDAPCLIENT_USE_SSL'] is False
    assert app.config['LDAPCLIENT_TLS'] is None
    assert app.config['LDAPCLIENT_CUSTOM_CONNECTION'] is None
    assert app.config['LDAPCLIENT_SEARCH_BASE'] == 'dc=example,dc=com'
    assert app.config['LDAPCLIENT_BIND_BASE'] == 'ou=people,dc=example,dc=com'
    assert app.config['LDAPCLIENT_USERNAME_ATTRIBUTE'] == 'uid'
    assert app.config['LDAPCLIENT_EMAIL_ATTRIBUTE'] == 'mail'
    assert app.config['LDAPCLIENT_FULL_NAME_ATTRIBUTE'] == 'displayName'
    assert app.config['LDAPCLIENT_SEARCH_ATTRIBUTES'] is None
    assert app.config['SECURITY_LOGIN_USER_TEMPLATE'] == \
        app.config['LDAPCLIENT_LOGIN_USER_TEMPLATE']


def test_init_non_exclusive_LDAP_auth():
    app = Flask('testapp')
    app.config['LDAPCLIENT_EXCLUSIVE_AUTHENTICATION'] = False
    ext = InvenioLDAPClient(app)
    ext.init_app(app)
    assert app.config['LDAPCLIENT_EXCLUSIVE_AUTHENTICATION'] is False
    with pytest.raises(KeyError, message='SECURITY_LOGIN_USER_TEMPLATE'):
        assert app.config['SECURITY_LOGIN_USER_TEMPLATE']


# View tests
def test_get_ldap_login(app):
    app.config['LDAPCLIENT_EXCLUSIVE_AUTHENTICATION'] = True
    app.config['LDAPCLIENT_USERNAME_PLACEHOLDER'] = 'Da User'
    app.config['COVER_TEMPLATE'] = 'login.html'
    app.jinja_loader.searchpath.append('tests/templates')
    app.jinja_loader.searchpath.append(
        invenio_accounts.__path__[0] + '/templates'
    )
    app.extensions['security'] = Mock()
    InvenioLDAPClient(app)

    response = app.test_client().get("/ldap-login")

    assert response.status_code == 200
    html_text = response.get_data(as_text=True)
    assert 'placeholder="Da User"' in html_text


def test_view_ldap_conn_returns_False(app):
    """Test view when there's something wrong with LDAP connection."""
    app.extensions['security'] = Mock()
    InvenioLDAPClient(app)
    app.config['SECURITY_POST_LOGIN_VIEW'] = '/abc'
    form = Mock()

    with patch(
        'invenio_ldapclient.views.login_form_factory',
        autospec=True, return_value=Mock(return_value=form)
    ) as form_factory_mock:
        with patch(
            'invenio_ldapclient.views._ldap_connection',
            autospec=True, return_value=False
        ) as ldap_conn_mock:
            res = app.test_client().post(
                "/ldap-login",
                data=dict(username='bad', password='bad')
            )

    form_factory_mock.assert_called_once_with(app)
    ldap_conn_mock.assert_called_once_with(form)
    assert app.config['SECURITY_CONFIRMABLE'] is False
    assert app.config['SECURITY_RECOVERABLE'] is False
    assert app.config['SECURITY_REGISTERABLE'] is False
    assert app.config['SECURITY_CHANGEABLE'] is False
    assert app.config['USERPROFILES_EMAIL_ENABLED'] is False
    assert app.view_functions['security.login'] == \
        invenio_ldapclient.views.ldap_login_form
    assert res.status_code == 302
    assert res.location == 'http://localhost/abc'


@patch('invenio_ldapclient.views.login_user', lambda user, remember: True)
@patch('invenio_ldapclient.views.db.session.commit', lambda: True)
def test_view_ldap_conn_returns_True(app):
    """Test view when LDAP connection is A-OK."""
    app.extensions['security'] = Mock()
    InvenioLDAPClient(app)
    app.config['SECURITY_POST_LOGIN_VIEW'] = '/abc'
    ldap_conn = Mock(bind=lambda: True, unbind=lambda: True)
    user = Mock()

    with patch(
        'invenio_ldapclient.views._ldap_connection',
        autospec=True, return_value=ldap_conn
    ) as ldap_conn_mock:
        with patch(
            'invenio_ldapclient.views._find_or_register_user',
            autospec=True, return_value=user
        ) as find_register_mock:
            with patch(
                'invenio_ldapclient.views.after_this_request',
                autospec=True
            ) as after_request_mock:
                res = app.test_client().post(
                    "/ldap-login",
                    data=dict(username='itsame', password='good')
                )

    lform = ldap_conn_mock.call_args[0][0]
    assert lform.username.data == 'itsame'
    assert lform.password.data == 'good'
    assert ldap_conn_mock.called is True
    find_register_mock.assert_called_once_with(ldap_conn, 'itsame')
    after_request_mock.assert_called_once_with(
        invenio_ldapclient.views._commit
    )
    assert app.view_functions['security.login'] == \
        invenio_ldapclient.views.ldap_login_form
    assert res.status_code == 302
    assert res.location == 'http://localhost/abc'


def test_view__ldap_connection(app):
    InvenioLDAPClient(app)
    subject = invenio_ldapclient.views._ldap_connection
    # Form cannot be validated
    form_invalid = Mock(validate_on_submit=lambda: False)
    assert subject(form_invalid) is False

    # Form missing required info
    form_no_user = Mock(
        validate_on_submit=lambda: True,
        password=Mock(data='pass'),
        username=Mock(data='')
    )
    assert subject(form_no_user) is False

    # With default TLS and Connection
    app.config['LDAPCLIENT_BIND_BASE'] = 'ou=base,cn=test'
    app.config['LDAPCLIENT_SERVER_HOSTNAME'] = 'ldap.host'
    app.config['LDAPCLIENT_SERVER_PORT'] = 666
    app.config['LDAPCLIENT_USE_SSL'] = True
    form_valid = Mock(
        validate_on_submit=lambda: True,
        password=Mock(data='dapass'),
        username=Mock(data='itsame')
    )

    conn = subject(form_valid)
    assert type(conn) == ldap3.core.connection.Connection
    assert conn.user == 'uid=itsame,ou=base,cn=test'
    assert conn.password == 'dapass'
    assert type(conn.server) == ldap3.core.server.Server

    assert conn.server.port == 666
    assert conn.server.host == 'ldap.host'
    assert conn.server.ssl is True
    assert type(conn.server.tls) == ldap3.core.tls.Tls
    assert conn.server.tls.validate == 0

    # With non-default TLS and default Connection
    app.config['LDAPCLIENT_TLS'] = ldap3.core.tls.Tls()
    conn = subject(form_valid)
    assert conn.server.tls == app.config['LDAPCLIENT_TLS']

    # With non-default Connection
    app.config['LDAPCLIENT_CUSTOM_CONNECTION'] = \
        lambda u, p: 'User: {}, Pass: {}'.format(u, p)
    assert subject(form_valid) == 'User: itsame, Pass: dapass'


@patch('invenio_ldapclient.views._search_ldap', lambda x, y: None)
def test_view__find_or_register_user_no_email(app):
    InvenioLDAPClient(app)
    app.config['LDAPCLIENT_EMAIL_ATTRIBUTE'] = 'daMail'
    subject = invenio_ldapclient.views._find_or_register_user
    conn = Mock(entries=[{'daMail': Mock(values=[])}])
    assert subject(conn, 'itsame') is None


@patch('invenio_ldapclient.views._search_ldap', lambda x, y: None)
def test_view__find_or_register_active_user_found_by_username(app):
    InvenioLDAPClient(app)
    subject = invenio_ldapclient.views._find_or_register_user
    conn = Mock(entries=[{'mail': Mock(values=['itsame@ta.da'])}])
    user = Mock(active=True)

    def filter_by_username(username_obj):
        username = username_obj.get_children()[1].value
        assert username == 'itsame'
        return Mock(one_or_none=lambda: user)

    user_mock = Mock(
        query=Mock(
            join=lambda obj: Mock(
                filter=MagicMock(
                    side_effect=filter_by_username))))

    @patch('invenio_ldapclient.views.User', user_mock)
    @patch(
        'invenio_ldapclient.views._register_or_update_user',
        return_value=user
    )
    def assert_returns_user(mocks):
        assert subject(conn, 'itsame') == user

    assert_returns_user()


@patch('invenio_ldapclient.views._search_ldap', lambda x, y: None)
def test_view__find_or_register_inactive_user_found_by_username(app):
    InvenioLDAPClient(app)
    subject = invenio_ldapclient.views._find_or_register_user
    conn = Mock(entries=[{'mail': Mock(values=['itsame@ta.da'])}])
    user = Mock(active=False)

    def filter_by_username(username_obj):
        username = username_obj.get_children()[1].value
        assert username == 'itsame'
        return Mock(one_or_none=lambda: user)

    user_mock = Mock(
        query=Mock(
            join=lambda obj: Mock(
                filter=MagicMock(
                    side_effect=filter_by_username))))

    @patch('invenio_ldapclient.views.User', user_mock)
    @patch(
        'invenio_ldapclient.views._register_or_update_user',
        return_value=user
    )
    def assert_returns_none(mocks):
        assert subject(conn, 'itsame') is None

    assert_returns_none()


@patch('invenio_ldapclient.views._search_ldap', lambda x, y: None)
def test_view__find_or_register_active_user_found_by_email(app):
    InvenioLDAPClient(app)
    subject = invenio_ldapclient.views._find_or_register_user
    conn = Mock(entries=[{'mail': Mock(values=['itsame@ta.da'])}])
    user = Mock(active=True)

    def filter_by_email(email):
        assert email == 'itsame@ta.da'
        return Mock(one_or_none=lambda: user)

    user_mock = Mock(
        query=Mock(
            join=lambda obj: Mock(
                filter=lambda username: Mock(one_or_none=lambda: None),
            ),
            filter_by=MagicMock(side_effect=filter_by_email)
        )
    )

    @patch('invenio_ldapclient.views.User', user_mock)
    @patch(
        'invenio_ldapclient.views._register_or_update_user',
        return_value=user
    )
    def assert_returns_user(mocks):
        assert subject(conn, 'itsame') == user

    assert_returns_user()


@patch('invenio_ldapclient.views._search_ldap', lambda x, y: None)
def test_view__find_or_register_inactive_user_found_by_email(app):
    InvenioLDAPClient(app)
    subject = invenio_ldapclient.views._find_or_register_user
    conn = Mock(entries=[{'mail': Mock(values=['itsame@ta.da'])}])
    user = Mock(active=False)

    def filter_by_email(email):
        assert email == 'itsame@ta.da'
        return Mock(one_or_none=lambda: user)

    user_mock = Mock(
        query=Mock(
            join=lambda obj: Mock(
                filter=lambda username: Mock(one_or_none=lambda: None),
            ),
            filter_by=MagicMock(side_effect=filter_by_email)
        )
    )

    @patch('invenio_ldapclient.views.User', user_mock)
    @patch(
        'invenio_ldapclient.views._register_or_update_user',
        return_value=user
    )
    def assert_returns_none(mocks):
        assert subject(conn, 'itsame') is None

    assert_returns_none()


@patch('invenio_ldapclient.views._search_ldap', lambda x, y: None)
def test_view__find_or_register_not_found_by_username_no_email_filtering(app):
    app.config['LDAPCLIENT_FIND_BY_EMAIL'] = False
    InvenioLDAPClient(app)
    subject = invenio_ldapclient.views._find_or_register_user
    conn = Mock(entries=[{'mail': Mock(values=['itsame@ta.da'])}])
    user = Mock(active=True)
    new_user = Mock()

    def filter_by_email(email):
        assert email == 'itsame@ta.da'
        return Mock(one_or_none=lambda: user)

    user_mock = Mock(
        query=Mock(
            join=lambda obj: Mock(
                filter=lambda username: Mock(one_or_none=lambda: None),
            ),
            filter_by=MagicMock(side_effect=filter_by_email)
        )
    )

    @patch('invenio_ldapclient.views.User', user_mock)
    @patch(
        'invenio_ldapclient.views._register_or_update_user',
        return_value=new_user
    )
    def assert_returns_new_user(mocks):
        assert subject(conn, 'itsame') == new_user

    assert_returns_new_user()


@patch('invenio_ldapclient.views._search_ldap', lambda x, y: None)
def test_view__find_or_register_user_not_found_no_auto_registration(app):
    app.config['LDAPCLIENT_AUTO_REGISTRATION'] = False
    InvenioLDAPClient(app)
    subject = invenio_ldapclient.views._find_or_register_user
    conn = Mock(entries=[{'mail': Mock(values=['itsame@ta.da'])}])

    def filter_by_email(email):
        assert email == 'itsame@ta.da'
        return Mock(one_or_none=lambda: None)

    user_mock = Mock(
        query=Mock(
            join=lambda obj: Mock(
                filter=lambda username: Mock(one_or_none=lambda: None),
            ),
            filter_by=MagicMock(side_effect=filter_by_email)
        )
    )

    @patch('invenio_ldapclient.views.User', user_mock)
    def assert_returns_none():
        assert subject(conn, 'itsame') is None

    assert_returns_none()


def test_view__search_ldap(app):
    InvenioLDAPClient(app)
    app.config['LDAPCLIENT_SEARCH_BASE'] = 'ou=base,cn=com'
    app.config['LDAPCLIENT_USERNAME_ATTRIBUTE'] = 'userId'
    subject = invenio_ldapclient.views._search_ldap

    # LDAPCLIENT_SEARCH_ATTRIBUTES is not set
    conn_mock = Mock()
    assert subject(conn_mock, 'itsame') is None
    conn_mock.search.assert_called_once_with(
        'ou=base,cn=com',
        '(userId=itsame)',
        attributes='*'
    )

    # LDAPCLIENT_SEARCH_ATTRIBUTES is set
    app.config['LDAPCLIENT_SEARCH_ATTRIBUTES'] = ['abc', 'bcd']
    conn_mock = Mock()
    assert subject(conn_mock, 'itsame') is None
    conn_mock.search.assert_called_once_with(
        'ou=base,cn=com',
        '(userId=itsame)',
        attributes=['abc', 'bcd']
    )


@patch('uuid.uuid4', lambda: Mock(hex='fancy-pass'))
def test_view__register_or_update_user(app):
    InvenioLDAPClient(app)
    app.config['LDAPCLIENT_EMAIL_ATTRIBUTE'] = 'daMail'
    app.config['LDAPCLIENT_USERNAME_ATTRIBUTE'] = 'daUsername'
    app.config['LDAPCLIENT_FULL_NAME_ATTRIBUTE'] = 'daFullName'
    entries = {
        'daMail': Mock(values=['itsame@ta.da']),
        'daUsername': Mock(values=['itsame']),
        'daFullName': Mock(values=['Itsa Me']),
    }
    subject = invenio_ldapclient.views._register_or_update_user

    # New user
    up_mock = MagicMock(autospec=UserProfile)
    with patch('invenio_ldapclient.views.UserProfile', lambda user_id: up_mock):  # noqa
        user_mock = Mock(get_id=lambda: '666')
        user_class_mock = Mock(
            query=Mock(
                filter_by=lambda email: Mock(
                    one_or_none=lambda: user_mock
                )
            )
        )
        with patch('invenio_ldapclient.views._datastore') as cu_patch:
            with patch('invenio_ldapclient.views.User', user_class_mock):
                with patch('invenio_ldapclient.views.db.session.add') as session_patch:  # noqa
                    assert subject(entries) == user_mock

    assert up_mock.username == 'itsame'
    assert up_mock.full_name == 'Itsa Me'
    cu_patch.create_user.assert_called_once_with(
        active=True,
        email='itsame@ta.da',
        password='fancy-pass'
    )
    session_patch.assert_called_with(up_mock)

    # Existing user
    up_mock2 = MagicMock(autospec=UserProfile)
    user_mock2 = Mock(autospec=User, profile=up_mock2)
    with patch('invenio_ldapclient.views._datastore') as cu_patch:
        with patch(
            'invenio_ldapclient.views.db.session.add'
        ) as session_patch:
            assert subject(entries, user_account=user_mock2) == user_mock2
            assert up_mock2.username == 'itsame'
            assert up_mock2.full_name == 'Itsa Me'
            assert session_patch.call_args_list[0][0][0] == user_mock2
            assert session_patch.call_args_list[1][0][0] == up_mock2


def test__security(app):
    """Test security method."""
    InvenioLDAPClient(app)
    app.extensions['security'] = 'ama security'
    subject = invenio_ldapclient.views._security
    assert type(subject) == LocalProxy
    assert subject == 'ama security'


def test__datastore(app):
    """Test datastore method."""
    InvenioLDAPClient(app)
    datastore_mock = Mock()
    app.extensions['security'] = Mock(datastore=datastore_mock)
    subject = invenio_ldapclient.views._datastore
    assert type(subject) == LocalProxy
    assert subject == datastore_mock


def test_blueprint(app):
    """Test blueprint."""
    InvenioLDAPClient(app)
    subject = invenio_ldapclient.views.blueprint
    assert subject.name == 'invenio_ldapclient'
    assert subject.template_folder == 'templates'


def test__commit(app):
    """Test the _commit method."""
    InvenioLDAPClient(app)
    with patch('invenio_ldapclient.views._datastore') as datastore_patch:
        assert invenio_ldapclient.views._commit() is None
        datastore_patch.commit.assert_called_once_with()
