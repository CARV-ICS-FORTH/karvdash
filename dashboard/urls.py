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

from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views

from . import views


urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('code', views.code, name='code'),
    path('data', views.data, {'path': '/'}, name='data'),
    path('data/<path:path>', views.data, name='data_with_path'),

    path('signup', views.signup, name='signup'),
    path('login', auth_views.LoginView.as_view(template_name='dashboard/login.html'), name='login'),
    path('change_password', views.change_password, name='change_password'),
    path('logout', views.logout, {'next': settings.LOGOUT_REDIRECT_URL}, name='logout'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
