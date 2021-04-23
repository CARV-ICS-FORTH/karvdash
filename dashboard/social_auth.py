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


def add_staff_authorization(backend, user, response, *args, **kwargs):
    if not user:
        return

    try:
        roles = response['realm_access']['roles']
    except KeyError:
        return

    should_be_staff = ('admin' in roles)
    if not user.is_staff == should_be_staff:
        user.is_staff = should_be_staff
        user.save()
