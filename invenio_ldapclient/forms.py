# -*- coding: utf-8 -*-
"""Username field for ldap. """

from __future__ import absolute_import, print_function
from flask_babelex import lazy_gettext as _
from wtforms import StringField, PasswordField, validators


def login_form_factory(Form, app):
    class LoginForm(Form):
        """LDAP login form."""

        def __init__(self, *args, **kwargs):
            super(LoginForm, self).__init__(*args, **kwargs)

        email = None

        username = StringField(
            _(app.config['LDAPCLIENT_USERNAME_PLACEHOLDER']),
            validators=[validators.InputRequired()]
        )
        password = PasswordField(
            _('Password'),
            validators=[validators.InputRequired()]
        )

    return LoginForm
