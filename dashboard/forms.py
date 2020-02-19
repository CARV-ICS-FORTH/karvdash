# Copyright [2019] [FORTH-ICS]
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os

from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth.models import User
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit

from .utils.gene import Gene


validate_docker_name = RegexValidator(r'^[0-9a-z\-\.]*$', 'Only alphanumeric characters, dash, and period are allowed.')
validate_docker_tag = RegexValidator(r'^[0-9a-zA-Z_\-\.]*$', 'Only alphanumeric characters, dash, underscore, and period are allowed.')

validate_kubernetes_label = RegexValidator(r'^(([A-Za-z0-9][-A-Za-z0-9_.]*)?[A-Za-z0-9])?$', 'Only alphanumeric characters, dash, underscore, and period are allowed.')

class SignUpForm(UserCreationForm):
    email = forms.EmailField(max_length=254, help_text='Required. Please use a valid email address.')

    class Meta:
        model = User
        fields = ('username', 'password1', 'password2', 'email')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'username',
            'password1',
            'password2',
            'email',
            Submit('submit', 'Submit', css_class='btn-success btn-lg btn-block')
        )

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exists():
            raise ValidationError('A user with that email already exists.')
        return email

def service_template_choices():
    choices = []
    for file_name in os.listdir(settings.SERVICE_TEMPLATE_DIR):
        if not file_name.endswith('.gene.yaml'):
            continue

        file_path = os.path.join(settings.SERVICE_TEMPLATE_DIR, file_name)
        try:
            with open(file_path, 'rb') as f:
                gene = Gene(f.read())
        except:
            continue
        choices.append((file_name, str(gene)))

    return choices

class AddServiceForm(forms.Form):
    file_name = forms.ChoiceField(label='Service to create', choices=service_template_choices)

class CreateServiceForm(forms.Form):
    def __init__(self, *args, **kwargs):
        variables = kwargs.pop('variables')
        super().__init__(*args, **kwargs)
        for variable in variables:
            name = variable['name']
            if name.upper() in ('PORT', 'REGISTRY', 'LOCAL', 'REMOTE'):
                continue
            kwargs = {'validators': [validate_kubernetes_label]} if name == 'NAME' else {}
            self.fields[name] = forms.CharField(label=name.capitalize(),
                                                initial=variable['default'],
                                                help_text=variable.get('help'),
                                                **kwargs)

class AddImageForm(forms.Form):
    name = forms.CharField(label='Image name', min_length=1, max_length=128, validators=[validate_docker_name])
    tag = forms.CharField(label='Tag', min_length=1, max_length=128, validators=[validate_docker_tag])
    file_field = forms.FileField(label='Saved image file to add')

class AddFolderForm(forms.Form):
    name = forms.CharField(label='Name for the new folder', min_length=1, max_length=255, initial='New Folder')

class AddFilesForm(forms.Form):
    file_field = forms.FileField(label='Files to add', widget=forms.ClearableFileInput(attrs={'multiple': True}))

class AddImageFromFileForm(forms.Form):
    name = forms.CharField(label='Image name', min_length=1, max_length=128, validators=[validate_docker_name])
    tag = forms.CharField(label='Tag', min_length=1, max_length=128, validators=[validate_docker_tag])

class EditUserForm(forms.Form):
    email = forms.EmailField(label='Email')
