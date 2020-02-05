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
import yaml
import kubernetes.client
import kubernetes.config

from django.shortcuts import render, redirect, reverse
from django.http import FileResponse
from django.conf import settings
from django.contrib.auth import logout as auth_logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from urllib.parse import urlparse
from datetime import datetime

from .forms import SignUpForm, ChangePasswordForm, AddServiceForm, CreateServiceForm, AddImageForm, AddFolderForm, AddFilesForm, AddImageFromFileForm
from .utils.gene import Gene
from .utils.docker import DockerClient


@login_required
def dashboard(request):
    # return render(request, 'dashboard/dashboard.html', {'title': 'Dashboard'})
    return redirect('services')

@login_required
def services(request):
    try:
        kubernetes.config.load_kube_config()
    except:
        kubernetes.config.load_incluster_config()
    kubernetes_client = kubernetes.client.CoreV1Api()

    # Handle changes.
    if (request.method == 'POST'):
        if 'action' not in request.POST:
            messages.error(request, 'Invalid action.')
        elif request.POST['action'] == 'Create':
            form = AddServiceForm(request.POST)
            if form.is_valid():
                file_name = form.cleaned_data['file_name']
                return redirect('service_create', file_name)
            else:
                messages.error(request, 'Failed to create service. Probably invalid service name.')
        elif request.POST['action'] == 'Remove':
            name = request.POST.get('service', None)
            if name:
                real_name = os.path.join(settings.SERVICE_DATABASE_DIR, '%s.yaml' % name)
                if not os.path.exists(real_name):
                    messages.error(request, 'Service description for "%s" not found.' % name)
                else:
                    if os.system('kubectl delete -f %s' % real_name) < 0:
                        messages.error(request, 'Can not remove service "%s".' % name)
                    else:
                        messages.success(request, 'Service "%s" removed.' % name)
                        os.unlink(real_name)
        else:
            messages.error(request, 'Invalid action.')

        return redirect('services')

    # There is no hierarchy here.
    trail = [{'name': '<i class="fa fa-university" aria-hidden="true"></i> %s' % kubernetes_client.api_client.configuration.host}]

    # Get service names from our database.
    service_database = []
    for file_name in os.listdir(settings.SERVICE_DATABASE_DIR):
        if file_name.endswith('.yaml'):
            service_database.append(file_name[:-5])

    # Fill in the contents.
    contents = []
    for service in kubernetes_client.list_service_for_all_namespaces().items:
        name = service.metadata.name
        spec_type = service.spec.type
        ports = [str(p.port) for p in service.spec.ports if p.protocol == 'TCP']
        contents.append({'name': name,
                         'url': 'http://%s:%s' % (urlparse(request.build_absolute_uri()).hostname, ports[0]) if spec_type == 'LoadBalancer' and ports else '',
                         'type': 'External' if spec_type == 'LoadBalancer' else 'Internal',
                         'port': ', '.join(ports),
                         'created': service.metadata.creation_timestamp,
                         'actions': True if name in service_database else False})

    # Sort them up.
    sort_by = request.GET.get('sort_by')
    if sort_by and sort_by in ('name', 'type', 'port', 'created'):
        request.session['services_sort_by'] = sort_by
    else:
        sort_by = request.session.get('services_sort_by', 'name')
    order = request.GET.get('order')
    if order and order in ('asc', 'desc'):
        request.session['services_order'] = order
    else:
        order = request.session.get('services_order', 'asc')

    contents = sorted(contents,
                      key=lambda x: x[sort_by],
                      reverse=True if order == 'desc' else False)

    return render(request, 'dashboard/services.html', {'title': 'Services',
                                                       'trail': trail,
                                                       'contents': contents,
                                                       'sort_by': sort_by,
                                                       'order': order,
                                                       'add_service_form': AddServiceForm()})

@login_required
def service_create(request, file_name=''):
    # Validate given file name.
    real_name = os.path.join(settings.SERVICE_TEMPLATE_DIR, file_name)
    try:
        with open(real_name, 'rb') as f:
            gene = Gene(f.read())
    except:
        messages.error(request, 'Invalid service.')
        return redirect('services')

    # Handle changes.
    if (request.method == 'POST'):
        if 'action' not in request.POST:
            messages.error(request, 'Invalid action.')
        elif request.POST['action'] == 'Create':
            form = CreateServiceForm(request.POST, variables=gene.variables)
            if form.is_valid():
                for variable in gene.variables:
                    name = variable['name']
                    if name.upper() in ('PORT', 'REGISTRY', 'LOCAL', 'REMOTE'): # Set here later on.
                        continue
                    setattr(gene, name, form.cleaned_data[name])

                try:
                    kubernetes.config.load_kube_config()
                except:
                    kubernetes.config.load_incluster_config()
                kubernetes_client = kubernetes.client.CoreV1Api()

                # Get active names and ports.
                names = []
                ports = []
                for service in kubernetes_client.list_service_for_all_namespaces().items:
                    names.append(service.metadata.name)
                    ports += [p.port for p in service.spec.ports if p.protocol == 'TCP'] # XXX Only TCP...

                # Set name, port, and registry.
                name = gene.NAME
                while name in names:
                    name = form.cleaned_data['NAME'] + '-' + ''.join([random.choice(string.ascii_lowercase) for i in range(4)])
                gene.NAME = name

                port = gene.PORT
                while port in ports:
                    port += 1
                gene.PORT = port

                gene.REGISTRY = '%s/' % settings.DOCKER_REGISTRY

                gene.LOCAL = '%s' % settings.DATA_DOMAINS['local']['dir'].rstrip('/')
                gene.REMOTE = '%s' % settings.DATA_DOMAINS['remote']['dir'].rstrip('/')

                # Inject data folders.
                gene.inject_hostpath_volumes(settings.DATA_DOMAINS)

                # Save yaml.
                if not os.path.exists(settings.SERVICE_DATABASE_DIR):
                    os.makedirs(settings.SERVICE_DATABASE_DIR)
                real_name = os.path.join(settings.SERVICE_DATABASE_DIR, '%s.yaml' % name)
                with open(real_name, 'wb') as f:
                    f.write(gene.yaml.encode())

                # Apply.
                if os.system('kubectl apply -f %s' % real_name) < 0:
                    messages.error(request, 'Can not create service "%s".' % name)
                else:
                    messages.success(request, 'Service "%s" created.' % name)
        else:
            messages.error(request, 'Invalid action.')

        return redirect('services')

    return render(request, 'dashboard/service_create.html', {'title': 'Create Service',
                                                             'create_service_form': CreateServiceForm(variables=gene.variables)})

@login_required
def images(request):
    docker_client = DockerClient(settings.DOCKER_REGISTRY)

    # Handle changes.
    if (request.method == 'POST'):
        if 'action' not in request.POST:
            messages.error(request, 'Invalid action.')
        elif request.POST['action'] == 'Add':
            form = AddImageForm(request.POST, request.FILES)
            files = request.FILES.getlist('file_field')
            if form.is_valid():
                name = form.cleaned_data['name']
                tag = form.cleaned_data['tag']
                try:
                    for f in files:
                        docker_client.add_image(f, name, tag)
                except Exception as e:
                    messages.error(request, 'Failed to add image: %s.' % str(e))
                else:
                    messages.success(request, 'Image "%s:%s" added.' % (name, tag))
            else:
                messages.error(request, 'Failed to add image. Probably invalid characters in name or tag.')

        elif request.POST['action'] == 'Delete':
            name = request.POST.get('name', None)
            try:
                repository, tag = name.split(':')
            except ValueError:
                messages.error(request, 'Invalid name.')
            else:
                try:
                    docker_client.registry(repository).del_alias(tag)
                except Exception as e:
                    messages.error(request, 'Failed to delete image: %s.' % str(e))
                else:
                    messages.success(request, 'Image "%s" deleted. Run garbage collection in the registry to reclaim space.' % name)
        else:
            messages.error(request, 'Invalid action.')

        return redirect('images')

    # There is no hierarchy here.
    trail = [{'name': '<i class="fa fa-archive" aria-hidden="true"></i> %s' % settings.DOCKER_REGISTRY}]

    # Fill in the contents.
    contents = []
    for repository in docker_client.registry().list_repos():
        registry = docker_client.registry(repository)
        for alias in registry.list_aliases():
            hashes = registry.get_alias(alias, sizes=True)
            contents.append({'name': repository,
                             'tag': alias,
                             'size': sum([h[1] for h in hashes])})

    # Sort them up.
    sort_by = request.GET.get('sort_by')
    if sort_by and sort_by in ('name', 'tag', 'size'):
        request.session['images_sort_by'] = sort_by
    else:
        sort_by = request.session.get('images_sort_by', 'name')
    order = request.GET.get('order')
    if order and order in ('asc', 'desc'):
        request.session['images_order'] = order
    else:
        order = request.session.get('images_order', 'asc')

    contents = sorted(contents,
                      key=lambda x: x[sort_by],
                      reverse=True if order == 'desc' else False)

    return render(request, 'dashboard/images.html', {'title': 'Images',
                                                     'trail': trail,
                                                     'contents': contents,
                                                     'sort_by': sort_by,
                                                     'order': order,
                                                     'add_image_form': AddImageForm()})

@login_required
def data(request, path='/'):
    # Normalize given path and split.
    path = os.path.normpath(path)
    path = path.lstrip('/')
    if path == '':
        path = list(settings.DATA_DOMAINS.keys())[0] # First is the default.
    path_components = [p for p in path.split('/') if p]

    # Figure out the real path we are working on.
    for domain, variables in settings.DATA_DOMAINS.items():
        folder = variables['dir']
        if path_components[0] == domain:
            real_path = os.path.join(folder, '/'.join(path_components[1:]))
            break
    else:
        messages.error(request, 'Invalid path.')
        return redirect('data')

    # Handle changes.
    if (request.method == 'POST'):
        if 'action' not in request.POST:
            messages.error(request, 'Invalid action.')
        elif request.POST['action'] == 'Create':
            form = AddFolderForm(request.POST)
            if form.is_valid():
                name = form.cleaned_data['name']
                real_name = os.path.join(real_path, name)
                if os.path.exists(real_name):
                    messages.error(request, 'Can not add "%s". An item with the same name already exists.' % name)
                else:
                    os.mkdir(real_name)
                    messages.success(request, 'Folder "%s" created.' % name)
            else:
                # XXX Show form errors in messages.
                pass
        elif request.POST['action'] == 'Add':
            form = AddFilesForm(request.POST, request.FILES)
            files = request.FILES.getlist('file_field')
            if form.is_valid():
                for f in files:
                    real_name = os.path.join(real_path, f.name)
                    if os.path.exists(real_name):
                        messages.error(request, 'Can not add "%s". An item with the same name already exists.' % f.name)
                        break
                else:
                    for f in files:
                        real_name = os.path.join(real_path, f.name)
                        with open(real_name, 'wb') as dest:
                            for chunk in f.chunks():
                                dest.write(chunk)
                    messages.success(request, 'Item%s %s added.' % ('s' if len(files) > 1 else '', ', '.join(['"%s"' % f.name for f in files])))
            else:
                # XXX Show form errors in messages.
                pass
        elif request.POST['action'] == 'Delete':
            name = request.POST.get('filename', None)
            if name:
                real_name = os.path.join(real_path, name)
                if not os.path.exists(real_name):
                    messages.error(request, 'Item "%s" not found in folder.' % name)
                else:
                    try:
                        if os.path.isfile(real_name):
                            os.remove(real_name)
                        else:
                            os.rmdir(real_name)
                    except Exception as e: # noqa: F841
                        # messages.error(request, 'Failed to delete "%s": %s.' % (name, str(e)))
                        messages.error(request, 'Failed to delete "%s". Probably not permitted or directory not empty.' % name)
                    else:
                        messages.success(request, 'Item "%s" deleted.' % name)
        elif request.POST['action'] == 'Add image':
            form = AddImageFromFileForm(request.POST)
            name = request.POST.get('filename', None)
            if form.is_valid() and name:
                real_name = os.path.join(real_path, name)
                name = form.cleaned_data['name']
                tag = form.cleaned_data['tag']
                try:
                    docker_client = DockerClient(settings.DOCKER_REGISTRY)
                    with open(real_name, 'rb') as f:
                        docker_client.add_image(f, name, tag)
                except Exception as e:
                    messages.error(request, 'Failed to add image: %s.' % str(e))
                else:
                    messages.success(request, 'Image "%s:%s" added.' % (name, tag))
            else:
                messages.error(request, 'Failed to add image. Probably invalid characters in name or tag.')
        else:
            messages.error(request, 'Invalid action.')

        return redirect('data', path)

    # Respond appropriately if the path is not a directory.
    if os.path.isfile(real_path):
        return FileResponse(open(real_path, 'rb'), as_attachment=True, filename=os.path.basename(real_path))
    if not os.path.isdir(real_path):
        messages.error(request, 'Invalid path.')
        return redirect('data')

    # This is a directory. Leave a trail of breadcrumbs.
    trail = []
    trail.append({'name': '<i class="fa fa-hdd-o" aria-hidden="true"></i>',
                  'url': reverse('data', args=[domain]) if len(path_components) != 1 else None})
    for i, path_component in enumerate(path_components[1:]):
        trail.append({'name': path_component,
                      'url': reverse('data', args=[os.path.join(*path_components[:i + 2])]) if i != (len(path_components) - 2) else None})

    # Fill in the contents.
    contents = []
    for file_name in os.listdir(real_path):
        file_path = os.path.join(real_path, file_name)
        if os.path.isdir(file_path):
            file_type = 'dir'
        elif os.path.isfile(file_path):
            file_type = 'file'
        else:
            continue
        mtime = os.path.getmtime(file_path)
        contents.append({'name': file_name,
                         'modified': datetime.fromtimestamp(mtime),
                         'type': file_type,
                         'size': os.path.getsize(file_path) if file_type != 'dir' else 0,
                         'url': reverse('data', args=[os.path.join(path, file_name)])})

    # Sort them up.
    sort_by = request.GET.get('sort_by')
    if sort_by and sort_by in ('name', 'modified', 'size'):
        request.session['data_sort_by'] = sort_by
    else:
        sort_by = request.session.get('data_sort_by', 'name')
    order = request.GET.get('order')
    if order and order in ('asc', 'desc'):
        request.session['data_order'] = order
    else:
        order = request.session.get('data_order', 'asc')

    contents = sorted(contents,
                      key=lambda x: x[sort_by],
                      reverse=True if order == 'desc' else False)

    return render(request, 'dashboard/data.html', {'title': 'Data',
                                                   'domain': domain,
                                                   'trail': trail,
                                                   'contents': contents,
                                                   'sort_by': sort_by,
                                                   'order': order,
                                                   'add_folder_form': AddFolderForm(),
                                                   'add_files_form': AddFilesForm(),
                                                   'add_image_from_file_form': AddImageFromFileForm()})

def signup(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False
            user.save()

            message = 'Your account has been created, but in order to login an administrator will have to activate it.'
            return render(request, 'dashboard/signup.html', {'message': message,
                                                             'next': settings.LOGIN_REDIRECT_URL})
    else:
        form = SignUpForm()
    return render(request, 'dashboard/signup.html', {'form': form,
                                                     'next': settings.LOGIN_REDIRECT_URL})

@login_required
def change_password(request):
    next = request.GET.get('next', settings.LOGIN_REDIRECT_URL)

    if request.method == 'POST':
        form = ChangePasswordForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Password successfully changed.')
            return redirect(next)
    else:
        form = ChangePasswordForm(request.user)
    return render(request, 'dashboard/change_password.html', {'form': form,
                                                              'next': next})

@login_required
def logout(request, next):
    auth_logout(request)
    return redirect(next)
