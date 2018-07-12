# -*- coding: utf-8 -*-
"""Username field for ldap. """

from __future__ import absolute_import, print_function
from flask_babelex import lazy_gettext as _
from wtforms import StringField, PasswordField, validators
from flask_security.forms import Form


def login_form_factory(app):
    class LoginForm(Form):
        """LDAP login form."""

        username = StringField(
            _(app.config['LDAPCLIENT_USERNAME_PLACEHOLDER']),
            validators=[validators.InputRequired()]
        )
        password = PasswordField(
            _('Password'),
            validators=[validators.InputRequired()]
        )

        def validate(self):
            return True

    return LoginForm
