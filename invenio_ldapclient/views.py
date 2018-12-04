"""Invenio module that adds more fun to the platform."""

from __future__ import absolute_import, print_function

import uuid

from flask import Blueprint, after_this_request
from flask import current_app as app
from flask import flash, redirect, render_template
from flask_security import login_user
from invenio_accounts.models import User
from invenio_db import db
from invenio_userprofiles.models import UserProfile
from ldap3 import ALL, ALL_ATTRIBUTES, Connection, Server
from werkzeug.local import LocalProxy

from .forms import login_form_factory

_security = LocalProxy(lambda: app.extensions['security'])
_datastore = LocalProxy(lambda: _security.datastore)

blueprint = Blueprint(
    'invenio_ldapclient',
    __name__,
    template_folder='templates',
    static_folder='static',
)


def _commit(response=None):
    _datastore.commit()
    return response


def _ldap_connection(form):
    """Make LDAP connection based on configuration."""
    if not form.validate_on_submit():
        return False

    form_pass = form.password.data
    form_user = form.username.data
    if not form_user or not form_pass:
        return False

    if app.config['LDAPCLIENT_CUSTOM_CONNECTION']:
        return app.config['LDAPCLIENT_CUSTOM_CONNECTION'](
            form_user, form_pass
        )

    ldap_server_kwargs = {
        'port': app.config['LDAPCLIENT_SERVER_PORT'],
        'get_info': ALL,
        'use_ssl': app.config['LDAPCLIENT_USE_SSL']
    }
    if app.config['LDAPCLIENT_TLS']:
        ldap_server_kwargs['tls'] = app.config['LDAPCLIENT_TLS']
    server = Server(
        app.config['LDAPCLIENT_SERVER_HOSTNAME'],
        **ldap_server_kwargs
    )

    ldap_user = "{}={},{}".format(
        app.config['LDAPCLIENT_USERNAME_ATTRIBUTE'],
        form_user,
        app.config['LDAPCLIENT_BIND_BASE']
    )
    return Connection(server, ldap_user, form_pass)


def _search_ldap(connection, username):
    """Fetch the user entry from LDAP."""
    search_attribs = app.config['LDAPCLIENT_SEARCH_ATTRIBUTES']
    if search_attribs is None:
        search_attribs = ALL_ATTRIBUTES

    connection.search(
        app.config['LDAPCLIENT_SEARCH_BASE'],
        '({}={})'.format(
            app.config['LDAPCLIENT_USERNAME_ATTRIBUTE'], username
        ),
        attributes=search_attribs)


def _register_or_update_user(entries, user_account=None):
    """Register or update a user."""
    email = entries[app.config['LDAPCLIENT_EMAIL_ATTRIBUTE']].values[0]
    username = entries[app.config['LDAPCLIENT_USERNAME_ATTRIBUTE']].values[0]
    if 'LDAPCLIENT_FULL_NAME_ATTRIBUTE' in app.config:
        full_name = entries[app.config[
            'LDAPCLIENT_FULL_NAME_ATTRIBUTE'
        ]].values[0]

    if user_account is None:
        kwargs = dict(email=email, active=True, password=uuid.uuid4().hex)
        _datastore.create_user(**kwargs)
        user_account = User.query.filter_by(email=email).one_or_none()
        profile = UserProfile(user_id=int(user_account.get_id()))
    else:
        user_account.email = email
        db.session.add(user_account)
        profile = user_account.profile

    profile.full_name = full_name
    profile.username = username
    db.session.add(profile)
    return user_account


def _find_or_register_user(connection, username):
    """Find user by email, username or register a new one."""
    _search_ldap(connection, username)

    entries = connection.entries[0]
    if not entries:
        return None

    try:
        email = entries[app.config['LDAPCLIENT_EMAIL_ATTRIBUTE']].values[0]
    except IndexError:
        # Email is required
        return None

    # Try by username first
    user = User.query.join(UserProfile).filter(
        UserProfile.username == username
    ).one_or_none()

    # Try by email next
    if not user and app.config['LDAPCLIENT_FIND_BY_EMAIL']:
        user = User.query.filter_by(email=email).one_or_none()

    if user:
        if not user.active:
            return None
        return _register_or_update_user(entries, user_account=user)

    # Register new user
    if app.config['LDAPCLIENT_AUTO_REGISTRATION']:
        return _register_or_update_user(entries)


@blueprint.route('/ldap-login', methods=['POST'])
def ldap_login_view():
    """Process login request using LDAP and register the user if needed."""
    form = login_form_factory(app)()
    connection = _ldap_connection(form)

    if connection and connection.bind():
        after_this_request(_commit)
        user = _find_or_register_user(connection, form.username.data)

        if not user or not login_user(user, remember=False):
            flash("We couldn't log you in, please contact your administrator.")

        connection.unbind()
        db.session.commit()
    else:
        flash("We couldn't log you in, please check your password.")

    return redirect(app.config['SECURITY_POST_LOGIN_VIEW'])


@blueprint.route('/ldap-login', methods=['GET'])
def ldap_login_form():
    """Display the LDAP login form."""
    form = login_form_factory(app)()
    return render_template(
        app.config['SECURITY_LOGIN_USER_TEMPLATE'],
        login_user_form=form
    )
