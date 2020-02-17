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

import kubernetes.client
import kubernetes.config


class KubernetesClient(object):
    def __init__(self):
        self._client = None

    @property
    def client(self):
        if not self._client:
            try:
                kubernetes.config.load_kube_config()
            except:
                kubernetes.config.load_incluster_config()
            self._client = kubernetes.client.CoreV1Api()
        return self._client

    @property
    def host(self):
        return self.client.api_client.configuration.host

    def list_namespaces(self):
        return self.client.list_namespace().items

    def create_namespace(self, namespace):
        return os.system('kubectl create namespace %s' % namespace) == 0

    def destroy_namespace(self, namespace):
        return os.system('kubectl delete namespace %s' % namespace) == 0

    def list_services(self):
        return self.client.list_service_for_all_namespaces().items

    def create_service(self, yaml_file, namespace=None):
        if namespace:
            if namespace not in [n.metadata.name for n in self.list_namespaces()]:
                if not self.create_namespace(namespace):
                    messages.error(request, 'Can not create namespace "%s". Please contact an admin.' % namespace)
                    return False
        return os.system('kubectl apply -n %s -f %s' % (namespace if namespace else 'default', yaml_file)) == 0

    def remove_service(self, yaml_file, namespace=None):
        return os.system('kubectl delete -n %s -f %s' % (namespace if namespace else 'default', yaml_file)) == 0

def namespace_for_user(user):
    return 'genome-%s' % user.username
