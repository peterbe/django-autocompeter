import random
from urllib.parse import urlparse

from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib import messages

from autocompeter.main.models import Domain, Key


def generate_new_key(length=24):
    pool = list('abcdefghjkmnopqrstuvwxyzABCDEFGHJKMNPQRSTUVWXYZ123456789')
    random.shuffle(pool)
    return ''.join(pool[:length])


def home(request):
    context = {}
    if request.method == 'POST':
        assert request.user.is_authenticated
        if 'domain' in request.POST:
            d = request.POST['domain'].strip()
            if '://' in d:
                d = urlparse(d).netloc
            if d:
                domain, created = Domain.objects.get_or_create(
                    name=d,
                )
                if created:
                    Key.objects.create(
                        domain=domain,
                        key=generate_new_key(),
                        user=request.user,
                    )
                    messages.success(
                        request,
                        'New domain (and key) created.'
                    )
                else:
                    Key.objects.create(
                        domain=domain,
                        key=generate_new_key(),
                        user=request.user,
                    )
                    messages.success(
                        request,
                        'New key created.'
                    )
                return redirect('main:home')

            else:
                messages.error(
                    request,
                    'No domain specified'
                )
        elif request.POST.get('delete'):
            count, _ = Key.objects.filter(
                key=request.POST['delete'],
                user=request.user
            ).delete()
            messages.success(
                request,
                '{} key deleted'.format(count)
            )
        else:
            raise NotImplementedError
    if request.user.is_authenticated:
        context['keys'] = Key.objects.filter(
            user=request.user
        ).order_by('domain__name', 'key')
    else:
        context['keys'] = []

    context['DEBUG'] = settings.DEBUG
    return render(request, 'main/home.html', context)
