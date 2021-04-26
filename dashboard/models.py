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
import socket
import random

from django.db import models
from django.contrib.auth.models import User as AuthUser
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from django.conf import settings
from urllib.parse import urlparse
from collections import namedtuple

from .utils.template import Template
from .utils.kubernetes import KubernetesClient
from .utils.file_domains.file import PrivateFileDomain, SharedFileDomain
from .utils.file_domains.s3 import PrivateS3Domain, SharedS3Domain


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
name: TokenConfigMap
variables:
- name: NAME
  default: user
- name: BASE_URL
  default: http://karvdash.default.svc/api
- name: TOKEN
  default: ""
'''

class User(AuthUser):
    class Meta:
        proxy = True

    @property
    def namespace(self):
        return 'karvdash-%s' % self.username

    @property
    def file_domains(self):
        files_url = urlparse(settings.FILES_URL)
        if files_url.scheme == 'file':
            return {'private': PrivateFileDomain(settings.FILES_URL, settings.FILES_MOUNT_DIR, self),
                    'shared': SharedFileDomain(settings.FILES_URL, settings.FILES_MOUNT_DIR, self)}
        if files_url.scheme in ('minio', 'minios'):
            return {'private': PrivateS3Domain(settings.FILES_URL, settings.FILES_MOUNT_DIR, self),
                    'shared': SharedS3Domain(settings.FILES_URL, settings.FILES_MOUNT_DIR, self)}
        raise ValueError('Unsupported URL for files')

    @property
    def dataset_volumes(self):
        # Return datasets as objects.
        DatasetTuple = namedtuple('DatasetTuple', ['volume_name', 'url', 'mount_dir'])

        datasets = {}
        kubernetes_client = KubernetesClient()
        try:
            for dataset in kubernetes_client.list_crds(group='com.ie.ibm.hpsys', version='v1alpha1', namespace=self.namespace, plural='datasets'):
                try:
                    # Hidden datasets are included in file domains.
                    if dataset['metadata']['labels']['karvdash-hidden'] == 'true':
                        continue
                except:
                    pass
                try:
                    dataset_type = dataset['spec']['local']['type']
                    if dataset_type in ('COS', 'H3', 'ARCHIVE'):
                        dataset_name = dataset['metadata']['name']
                        datasets[dataset_name] = DatasetTuple(dataset_name, 'dataset://%s' % dataset_name, '/mnt/datasets/%s' % dataset_name)
                    else:
                        continue
                except:
                    continue
        except:
            pass

        return datasets

    @property
    def api_token(self):
        try:
            api_token = APIToken.objects.get(user=self)
        except APIToken.DoesNotExist:
            api_token = APIToken(user=self)
            api_token.save()
        return api_token

def generate_token():
    return ''.join(random.choice('0123456789abcdef') for n in range(40))

class APIToken(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    token = models.CharField(max_length=64, blank=False, null=False, default=generate_token)

@receiver(user_logged_in)
def create_user_namespace(sender, user, request, **kwargs):
    user = User.objects.get(pk=user.pk)

    kubernetes_client = KubernetesClient()
    if user.namespace in [n.metadata.name for n in kubernetes_client.list_namespaces()]:
        return

    ingress_url = urlparse(settings.INGRESS_URL)
    ingress_host = '%s:%s' % (ingress_url.hostname, ingress_url.port) if ingress_url.port else ingress_url.hostname

    # Create namespace file.
    namespace_template = Template(NAMESPACE_TEMPLATE)
    namespace_template.NAME = user.namespace

    namespace_yaml = os.path.join(settings.SERVICE_DATABASE_DIR, '%s-namespace.yaml' % user.username)
    with open(namespace_yaml, 'wb') as f:
        f.write(namespace_template.yaml.encode())

    # Create API connectivity configuration file (mounted inside containers).
    service_domain = settings.SERVICE_DOMAIN
    if not service_domain:
        # If running in Kubernetes this should be set.
        service_host = socket.gethostbyname(socket.gethostname())
        service_port = request.META['SERVER_PORT']
        service_domain = '%s:%s' % (service_host, service_port)
    api_template = Template(TOKEN_CONFIGMAP_TEMPLATE)
    api_template.NAME = 'karvdash-api'
    api_template.BASE_URL = 'http://%s/api' % service_domain
    api_template.TOKEN = user.api_token.token # Get or create

    api_yaml = os.path.join(settings.SERVICE_DATABASE_DIR, '%s-api.yaml' % user.username)
    with open(api_yaml, 'wb') as f:
        f.write(api_template.yaml.encode())

    # Apply.
    kubernetes_client.apply_yaml(namespace_yaml)
    kubernetes_client.create_docker_registry_secret(user.namespace, settings.DOCKER_REGISTRY, 'admin@%s' % ingress_host)
    # if settings.DATASETS_AVAILABLE:
    #     kubernetes_client.add_namespace_label(user.namespace, 'monitor-pods-datasets')
    kubernetes_client.apply_yaml(api_yaml, namespace=user.namespace)
