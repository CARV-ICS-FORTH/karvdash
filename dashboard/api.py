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
import random
import string
import json
import socket

from django.conf import settings
from restless.dj import DjangoResource
from restless.exceptions import NotFound, BadRequest, Conflict

from .models import APIToken, User
from .forms import CreateServiceForm
from .utils.template import Template, ServiceTemplate, FileTemplate
from .utils.kubernetes import KubernetesClient
from .utils.docker import DockerClient


NAMESPACE_TEMPLATE = '''
apiVersion: v1
kind: Namespace
metadata:
  name: $NAME
  labels:
    karvdash: enabled
---
kind: RoleBinding
apiVersion: rbac.authorization.k8s.io/v1
metadata:
  name: admin-binding
  namespace: $NAME
subjects:
- kind: ServiceAccount
  name: default
  namespace: $NAME
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: cluster-admin
---
kind: Template
name: Namespace
variables:
- name: NAME
  default: user
'''

TOKEN_CONFIGMAP_TEMPLATE = '''
apiVersion: v1
kind: ConfigMap
metadata:
  name: ${NAME}
data:
  config.ini: |
    [Karvdash]
    base_url = $BASE_URL
    token = $TOKEN
---
kind: Template
name: TokenConfigMapTemplate
variables:
- name: NAME
  default: user
- name: BASE_URL
  default: http://karvdash.default.svc/api
- name: TOKEN
  default: ""
'''

class APIResource(DjangoResource):
    @property
    def user(self):
        if getattr(self.request.user, 'is_impersonate', False):
            return User.objects.get(pk=self.request.user.pk)
        return self.request.user

    def is_authenticated(self):
        if self.request.user and self.request.user.is_authenticated:
            return True

        token = None
        authorization_header = self.request.META.get('HTTP_AUTHORIZATION', '')
        if authorization_header and authorization_header.lower().startswith('token '):
            token = authorization_header[6:]
        if not token:
            token = self.request.GET.get('token', '')
        if not token:
            return False
        token = token.strip().lower()

        try:
            api_token = APIToken.objects.get(token=token)
        except APIToken.DoesNotExist:
            return False

        if not api_token.user.is_active:
            return False
        self.request.user = api_token.user
        return True

class ServiceResource(APIResource):
    http_methods = {'list': {'GET': 'list',
                             'POST': 'create'},
                    'detail': {'POST': 'execute',
                               'DELETE': 'delete'}}

    def list(self):
        kubernetes_client = KubernetesClient()

        service_database_path = os.path.join(settings.SERVICE_DATABASE_DIR, self.user.username)
        if not os.path.exists(service_database_path):
            os.makedirs(service_database_path)

        service_database = []
        for file_name in os.listdir(service_database_path):
            if file_name.endswith('.yaml'):
                service_database.append(file_name[:-5])

        contents = []
        ingresses = [i.metadata.name for i in kubernetes_client.list_ingresses(namespace=self.user.namespace)]
        for service in kubernetes_client.list_services(namespace=self.user.namespace, label_selector=''):
            name = service.metadata.name
            # ports = [str(p.port) for p in service.spec.ports if p.protocol == 'TCP']
            url = 'http://%s-%s.%s' % (name, self.user.username, settings.INGRESS_DOMAIN) if name in ingresses else None
            try:
                filename = service.metadata.labels['karvdash-template']
                service_template = FileTemplate(filename).format()
            except:
                service_template = None
            if service_template:
                try:
                    values = service.metadata.annotations['karvdash-values']
                    service_template['values'] = json.loads(values)
                except:
                    pass
            contents.append({'name': name,
                             'url': url,
                             'created': service.metadata.creation_timestamp,
                             'actions': True if name in service_database else False,
                             'template': service_template})

        return contents

    def create(self):
        try:
            template = FileTemplate(self.data.pop('filename'))
        except:
            raise NotFound()

        form = CreateServiceForm(self.data, variables=template.variables)
        if not form.is_valid():
            raise BadRequest()

        for variable in template.variables:
            name = variable['name']
            if name.upper() in ('NAMESPACE', 'HOSTNAME', 'REGISTRY', 'LOCAL', 'REMOTE', 'SHARED'): # Set here later on.
                continue
            if name in self.data:
                setattr(template, name, form.cleaned_data[name])

        kubernetes_client = KubernetesClient()
        if template.singleton and len(kubernetes_client.list_services(namespace=self.user.namespace,
                                                                      label_selector='karvdash-template=%s' % template.filename)):
            raise Conflict()

        # Resolve naming conflicts.
        name = template.NAME
        names = [service.metadata.name for service in kubernetes_client.list_services(namespace=self.user.namespace, label_selector='')]
        while name in names:
            name = form.cleaned_data['NAME'] + '-' + ''.join([random.choice(string.ascii_lowercase) for i in range(4)])

        # Set name, hostname, registry, and storage paths.
        template.NAMESPACE = self.user.namespace
        template.NAME = name
        template.HOSTNAME = '%s-%s.%s' % (name, self.user.username, settings.INGRESS_DOMAIN)
        template.REGISTRY = DockerClient(settings.DOCKER_REGISTRY, settings.DOCKER_REGISTRY_NO_VERIFY).registry_host
        template.LOCAL = settings.DATA_DOMAINS['local']['dir'].rstrip('/')
        template.REMOTE = settings.DATA_DOMAINS['remote']['dir'].rstrip('/')
        template.SHARED = settings.DATA_DOMAINS['shared']['dir'].rstrip('/')

        # Inject data folders.
        # if settings.DEBUG:
        #     template.inject_hostpath_volumes(self.user.volumes, add_api_settings=True)

        # Add template label and values.
        template.inject_service_details()

        # Add authentication.
        template.inject_ingress_auth('karvdash-auth', 'Authentication Required - %s' % settings.DASHBOARD_TITLE, redirect_ssl=settings.SERVICE_REDIRECT_SSL)

        # Save yaml.
        service_database_path = os.path.join(settings.SERVICE_DATABASE_DIR, self.user.username)
        if not os.path.exists(service_database_path):
            os.makedirs(service_database_path)
        service_yaml = os.path.join(service_database_path, '%s.yaml' % name)
        with open(service_yaml, 'wb') as f:
            f.write(template.yaml.encode())

        # Apply.
        try:
            if self.user.namespace not in [n.metadata.name for n in kubernetes_client.list_namespaces()]:
                namespace_template = Template(NAMESPACE_TEMPLATE)
                namespace_template.NAME = self.user.namespace

                namespace_yaml = os.path.join(settings.SERVICE_DATABASE_DIR, '%s-namespace.yaml' % self.user.username)
                with open(namespace_yaml, 'wb') as f:
                    f.write(namespace_template.yaml.encode())

                kubernetes_client.apply_yaml(namespace_yaml)
                kubernetes_client.create_docker_registry_secret(self.user.namespace, settings.DOCKER_REGISTRY, 'admin@%s' % settings.INGRESS_DOMAIN)

            api_base_url = settings.API_BASE_URL
            if not api_base_url:
                if os.getenv('KARVDASH_PORT'): # Probably running in Kubernetes
                    api_base_url = 'http://karvdash.default.svc/api'
                else:
                    service_host = socket.gethostbyname(socket.gethostname())
                    service_port = self.request.META['SERVER_PORT']
                    api_base_url = 'http://%s:%s/api' % (service_host, service_port)
            api_template = Template(TOKEN_CONFIGMAP_TEMPLATE)
            api_template.NAME = 'karvdash-api'
            api_template.BASE_URL = api_base_url
            api_template.TOKEN = self.user.api_token.token # Get or create

            api_yaml = os.path.join(settings.SERVICE_DATABASE_DIR, '%s-api.yaml' % self.user.username)
            with open(api_yaml, 'wb') as f:
                f.write(api_template.yaml.encode())

            kubernetes_client.apply_yaml(api_yaml, namespace=self.user.namespace)

            self.user.update_kubernetes_credentials(kubernetes_client=kubernetes_client)
            kubernetes_client.apply_yaml(service_yaml, namespace=self.user.namespace)
        except:
            raise

        service_template = template.format()
        service_template['values'] = template.values
        return {'name': name,
                'url': 'http://%s-%s.%s' % (name, self.user.username, settings.INGRESS_DOMAIN),
                # 'created': creation_timestamp,
                'actions': True,
                'template': service_template}

    def execute(self, pk):
        name = pk

        if 'command' not in self.data:
            raise BadRequest()
        all_pods = True if self.data.get('all_pods') in (1, '1', 'True', 'true') else False

        result = KubernetesClient().exec_command_in_pod(namespace=self.user.namespace,
                                                        label_selector='app=%s' % name,
                                                        command=self.data['command'],
                                                        all_pods=all_pods)
        return {'result': result}

    def delete(self, pk):
        name = pk
        kubernetes_client = KubernetesClient()

        service_database_path = os.path.join(settings.SERVICE_DATABASE_DIR, self.user.username)
        if not os.path.exists(service_database_path):
            os.makedirs(service_database_path)

        service_yaml = os.path.join(service_database_path, '%s.yaml' % name)
        if not os.path.exists(service_yaml):
            raise NotFound()
        else:
            try:
                kubernetes_client.delete_yaml(service_yaml, namespace=self.user.namespace)
            except:
                raise
            else:
                os.unlink(service_yaml)

class TemplateResource(APIResource):
    http_methods = {'list': {'GET': 'list',
                             'POST': 'add'},
                    'detail': {'GET': 'get',
                               'DELETE': 'remove'}}

    # def is_debug(self):
    #     return True

    # def bubble_exceptions(self):
    #     return True

    @property
    def templates(self):
        contents = []
        for file_name in os.listdir(settings.SERVICE_TEMPLATE_DIR):
            if not file_name.endswith('.template.yaml'):
                continue

            try:
                template = FileTemplate(file_name)
            except:
                continue
            contents.append(template)

        return contents

    def list(self):
        return [template.format() for template in self.templates]

    def add(self):
        try:
            template = ServiceTemplate(self.data.pop('template'))
        except:
            raise BadRequest()

        return template.format()

    def get(self, pk):
        identifier = pk

        for template in self.templates:
            if template.identifier == identifier:
                return template.format(include_data=True)
        else:
            raise NotFound()

    def remove(self, pk):
        pass
