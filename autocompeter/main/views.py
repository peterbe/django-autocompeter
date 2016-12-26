import random

from django.shortcuts import render, redirect
from django.contrib import messages

from autocompeter.main.models import Domain, Key


def generate_new_key(length=24):
    pool = list('abcdefghjkmnopqrstuvwxyzABCDEFGHJKMNPQRSTUVWXYZ123456789')
    random.shuffle(pool)
    return ''.join(pool[:length])


def home(request):
    context = {}
    # for d in Domain.objects.all():
    #     d.delete()
    if request.method == 'POST':
        if 'domain' in request.POST:
            d = request.POST['domain'].strip()
            if d:
                domain, created = Domain.objects.get_or_create(
                    name=d,
                )
                if created:
                    Key.objects.create(
                        domain=domain,
                        key=generate_new_key(),
                    )
                    messages.success(
                        request,
                        'New domain (and key) created.'
                    )
                return redirect('main:home')
            else:
                messages.error(
                    request,
                    'No domain specified'
                )
        else:
            raise NotImplementedError
            # print(list(request.POST.items()))
    # context =

    return render(request, 'main/home.html', context)
