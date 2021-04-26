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

from django.conf import settings as django_settings

def settings(request):
    return {'ingress_url': django_settings.INGRESS_URL,
            'dashboard_title': django_settings.DASHBOARD_TITLE,
            'dashboard_theme': django_settings.DASHBOARD_THEME,
            'issues_url': django_settings.ISSUES_URL,
            'datasets_available': django_settings.DATASETS_AVAILABLE,
            'keycloak_key': django_settings.SOCIAL_AUTH_KEYCLOAK_KEY,
            'keycloak_logout_url': django_settings.SOCIAL_AUTH_KEYCLOAK_LOGOUT_URL}
