import logging
import json

from django import forms
from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.debug import sensitive_variables

from .exceptions import KeystoneAuthException
from contrib.federated import federated

LOG = logging.getLogger(__name__)


class Login(AuthenticationForm):
    """ Form used for logging in a user.

    Handles authentication with Keystone by providing the domain name, username
    and password. A scoped token is fetched after successful authentication.

    A domain name is required if authenticating with Keystone V3 running
    multi-domain configuration.

    If the user authenticated has a default project set, the token will be
    automatically scoped to their default project.

    If the user authenticated has no default project set, the authentication
    backend will try to scope to the projects returned from the user's assigned
    projects. The first successful project scoped will be returned.

    Inherits from the base ``django.contrib.auth.forms.AuthenticationForm``
    class for added security features.
    """
    region = forms.ChoiceField(label=_("Region"), required=False)
    username = forms.CharField(label=_("U"), required=False, initial=settings.OPENSTACK_FEDERATED_DEFAULT_LOGIN, widget=forms.HiddenInput())
    password = forms.CharField(label=_("Password"), required=False,
                               initial=settings.OPENSTACK_FEDERATED_DEFAULT_PASSWORD, widget=forms.HiddenInput())

    def __init__(self, *args, **kwargs):
        super(Login, self).__init__(*args, **kwargs)
        self.fields.keyOrder = ['username', 'password', 'region']
        if getattr(settings,
                   'OPENSTACK_KEYSTONE_MULTIDOMAIN_SUPPORT',
                    False):
            self.fields['domain'] = forms.CharField(label=_("Domain"),
                                                    required=True)
            self.fields.keyOrder = ['domain', 'username', 'password', 'region']
        elif getattr(settings,
                        'OPENSTACK_KEYSTONE_FEDERATED_SUPPORT',
                        False):
            CHOICES=(
                ('Local', 'Local'),
            )
            self.fields['domain'] = forms.ChoiceField(label=_("Domain"),
                                                      required=True,
                                                      choices=CHOICES
                                                      )
            realmList = federated.getRealmList(settings.OPENSTACK_KEYSTONE_FEDERATED_URL)
            if realmList is not None:
                for realm in realmList['realms']:
                    self.fields['domain'].choices.insert(0, (json.dumps(realm), realm['description']))
            self.fields.keyOrder = ['domain', 'username', 'password', 'region']
        self.fields['region'].choices = self.get_region_choices()
        if len(self.fields['region'].choices) == 1:
            self.fields['region'].initial = self.fields['region'].choices[0][0]
            self.fields['region'].widget = forms.widgets.HiddenInput()

    @staticmethod
    def get_region_choices():
        default_region = (settings.OPENSTACK_KEYSTONE_URL, "Default Region")
        return getattr(settings, 'AVAILABLE_REGIONS', [default_region])

    
    def clean__region():
        return self.cleaned_data['region']

    def clean__username():
        return self.cleaned_data['username']

    def clean__password():
        return self.cleaned_data['password']

    @sensitive_variables()
    def clean(self):
        default_domain = getattr(settings,
                                 'OPENSTACK_KEYSTONE_DEFAULT_DOMAIN',
                                 'Default')
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        region = self.cleaned_data.get('region')
        domain = self.cleaned_data.get('domain', default_domain)
        if not (username and password):
            return self.cleaned_data
        try:
            if getattr(settings,
                       'OPENSTACK_KEYSTONE_FEDERATED_SUPPORT',
                       True):
                realm = json.loads(domain)
                ipdEndpoint = federated.getIdPRequest(settings.OPENSTACK_KEYSTONE_FEDERATED_URL, realm)
                print str(ipdEndpoint)
                #settings.LOGIN_REDIRECT_URL = ''
                self.cleaned_data['username'] = '_'
                self.cleaned_data['password'] = '_'
                # fake the user/pasword validation
                settings.LOGIN_REDIRECT_URL = str(ipdEndpoint['idpEndpoint']) + str(ipdEndpoint['idpRequest']) + '&callbackurl=' + str(settings.OPENSTACK_FEDERATED_HORIZON_CALLBACK_URL) 

               # settings.LOGIN_REDIRECT_URL ='http://csvm2c4d.kent.ac.uk:8000/auth/federated_response'
            self.user_cache = authenticate(request=self.request,
                                           username=username,
                                           password=password,
                                           user_domain_name=domain,
                                           auth_url=region)
            msg = 'Login successful for user "%(username)s".' % \
                {'username': username}
            LOG.info(msg)
            #for setting in settings:
                #print settings
        except KeystoneAuthException as exc:
            msg = 'Login failed for user "%(username)s".' % \
                {'username': username}
            LOG.warning(msg)
            self.request.session.flush()
            raise forms.ValidationError(exc)
        self.check_for_test_cookie()
        return self.cleaned_data
