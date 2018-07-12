"""Invenio module that adds more fun to the platform."""

from __future__ import absolute_import, print_function

from flask import (
    Blueprint,
    redirect,
    after_this_request,
    current_app as app
)
from ldap3 import Server, Connection, ALL, ALL_ATTRIBUTES
from invenio_accounts.models import User
from invenio_userprofiles.models import UserProfile
from flask_security import login_user
from werkzeug.local import LocalProxy
from invenio_db import db
import uuid

from .forms import login_form_factory

_security = LocalProxy(lambda: app.extensions['security'])
_datastore = LocalProxy(lambda: _security.datastore)

blueprint = Blueprint(
    'invenio_unicorn',
    __name__,
    template_folder='templates',
    static_folder='static',
)


def _commit(response=None):
    _datastore.commit()
    return response


def register_user(entries):
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


@blueprint.route('/ldap-login', methods=['POST'])
def ldap_login_view():
    form = login_form_factory(
        app
    )()
    ldap_user = None
    ldap_pass = None
    from IPython import embed; embed()
    raise
    # FIXME email validator and CSRF token erros
    # if form.validate_on_submit():
    ldap_user = "uid={},ou=people,dc=northwestern,dc=edu".format(
        form.username.data)
    ldap_pass = form.password.data

    server = Server('registry.northwestern.edu', get_info=ALL, use_ssl=True)
    conn = Connection(server, ldap_user, ldap_pass)
    if ldap_user and ldap_pass and conn.bind():
        conn.search(
            'dc=northwestern,dc=edu',
            '(uid={})'.format(form.username.data),
            attributes=ALL_ATTRIBUTES)
        email = conn.entries[0].mail.values[0]
        user = User.query.filter_by(email=email).one_or_none()

        after_this_request(_commit)
        if not user:
            user = register_user(conn.entries[0])

        if not login_user(user, remember=False):
            raise ValueError('Could not log user in: {}'.format(ldap_user))
    else:
        print('User NOT authenticated {}'.format(ldap_user))

    conn.unbind()
    db.session.commit()
    return redirect(app.config['SECURITY_POST_LOGIN_VIEW'])
