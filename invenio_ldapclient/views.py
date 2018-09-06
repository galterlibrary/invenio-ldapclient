"""Invenio module that adds more fun to the platform."""

from __future__ import absolute_import, print_function

import uuid

from flask import Blueprint, after_this_request
from flask import current_app as app
from flask import redirect, render_template
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


def __register_user(entries):
    email = entries.mail.values[0]
    username = entries.uid.values[0]
    full_name = entries.displayName.values[0]
    password = uuid.uuid4().hex

    # User
    kwargs = dict(email=email, password=password, active=True)
    _datastore.create_user(**kwargs)
    user = User.query.filter_by(email=email).one_or_none()

    # from IPython import embed; embed()
    # User profile
    profile = UserProfile(user_id=int(user.get_id()))
    profile.full_name = full_name
    profile.username = username
    db.session.add(profile)
    return user


def __ldap_connection(form):
    if not form.validate_on_submit():
        return False

    form_pass = form.password.data
    form_user = form.username.data

    if not form_user or not form_pass:
        return False

    ldap_user = "{}={},{}".format(
        app.config['LDAPCLIENT_USERNAME_ATTRIBUTE'],
        form_user,
        app.config['LDAPCLIENT_BIND_BASE']
    )

    ldap_server_kwargs = {
        'port': app.config['LDAPCLIENT_SERVER_PORT'],
        'get_info': ALL,
        'use_ssl': app.config['LDAPCLIENT_USE_SSL']
    }

    if app.config['LDAPCLIENT_TLS']:
        ldap_server_options['tls'] = app.config['LDAPCLIENT_TLS']

    server = Server(
        app.config['LDAPCLIENT_SERVER_HOSTNAME'],
        **ldap_server_kwargs
    )

    if app.config['LDAPCLIENT_CUSTOM_CONNECTION']:
        return app.config['LDAPCLIENT_CUSTOM_CONNECTION']()
    else:
        return Connection(server, ldap_user, form_pass)


def __find_or_register_user(entries, username):
    if not entries:
        return None
    email = entries[
        app.config['LDAPCLIENT_EMAIL_ATTRIBUTE']
    ].values[0]
    if not email:
        # Email is required
        return None
    user = User.query.filter_by(email=email).one_or_none()
    if user:
        return user
    return UserProfile.query(filter_by(
        **{ app.config['LDAPCLIENT_USERNAME_ATTRIBUTE']: username }
    ))


@blueprint.route('/ldap-login', methods=['POST'])
def ldap_login_view():
    """Process login request using LDAP and register the user if needed."""
    form = login_form_factory(app)()
    conn = __ldap_connection(form)

    if conn and conn.bind():
        search_attribs=ALL_ATTRIBUTES
        if 'LDAPCLIENT_SEARCH_ATTRIBUTES' in app.config.keys():
            search_attribs = app.config['LDAPCLIENT_SEARCH_ATTRIBUTES']

        conn.search(
            app.config['LDAPCLIENT_SEARCH_BASE'],
            '({}={})'.format(
                app.config['LDAPCLIENT_USERNAME_ATTRIBUTE'],
                form.username.data
            ),
            attributes=search_attribs)

        __find_or_register_user(conn.entries[0], form.username.data)
        #from IPython.core.debugger import Pdb; Pdb().set_trace()
        email = conn.entries[0].mail.values[0]
        user = User.query.filter_by(email=email).one_or_none()

        after_this_request(_commit)
        if not user:
            user = __register_user(conn.entries[0])

        if not login_user(user, remember=False):
            raise ValueError('Could not log user in: {}'.format(
                form.username.data))

        conn.unbind()
        db.session.commit()
    else:
        print('User NOT authenticated {}'.format(form.username.data))

    return redirect(app.config['SECURITY_POST_LOGIN_VIEW'])


def ldap_login_form():
    """Display the LDAP login form."""
    form = login_form_factory(
        app
    )()
    return render_template(
        app.config['SECURITY_LOGIN_USER_TEMPLATE'],
        login_user_form=form
    )
