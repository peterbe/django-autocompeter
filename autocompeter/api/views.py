import json
import functools

# from django.shortcuts import render
from django import http
from django.views.decorators.csrf import csrf_exempt

from autocompeter.main.models import Title, Key, Domain, Search
from autocompeter.main.search import TitleDoc


def auth_key(func):

    @functools.wraps(func)
    def inner(request, *args):
        if request.method == 'GET':
            return func(request, None, *args)
        try:
            auth_key = request.META['HTTP_AUTH_KEY']
            assert auth_key
        except (AttributeError, AssertionError):
            # XXX check what autocompeter Go does
            return http.JsonResponse({
                'error': "Missing header 'Auth-Key'",
            }, status=400)
        try:
            key = Key.objects.get(key=auth_key)
        except Key.DoesNotExist:
            # XXX check what autocompeter Go does
            return http.JsonResponse({
                'error': "Auth-Key not recognized",
            }, status=403)
        domain = Domain.objects.get(key=key)
        return func(request, domain, *args)

    return inner


@auth_key
@csrf_exempt
def home(request, domain):
    # print(request.META.keys())

    if request.method == 'POST':
        # print("BODY", request.body)
        url = request.POST['url'].strip()
        assert url
        title = request.POST['title'].strip()
        assert title
        group = request.POST.get('group', '').strip()
        popularity = float(request.POST.get('popularity', 0.0))
        # for x in Title.objects.all():
        #     x.delete()
        Title.upsert(
            domain,
            url,
            title,
            group=group,
            popularity=popularity,
        )
        # try:
        #     found = Title.objects.get(
        #         domain=domain,
        #         # value=title,
        #         url=url,
        #     )
        #     print("FOUND", repr(found))
        #     different = not (
        #         found.value == title and
        #         found.popularity == popularity and
        #         found.group == group
        #     )
        #     if different:
        #         found.value = title
        #         found.group = group
        #         found.popularity = popularity
        #         found.save()
        # except Title.DoesNotExist:
        #     print("NOT FOUND")
        #     Title.objects.create(
        #         domain=domain,
        #         value=title,
        #         url=url,
        #         popularity=popularity,
        #         group=group
        #     )
        #     print("CREATED")
        # for thing in request.POST.items():
        #     print("THING", thing)
        return http.JsonResponse({'message': 'OK'}, status=201)
    elif request.method == 'DELETE':
        print(dir(request))
        raise Exception
    else:
        q = request.GET.get('q', '')
        if not q:
            return http.JsonResponse({'error': "Missing 'q'"}, status=400)
        domain = request.GET.get('d', '').strip()
        if not domain:
            return http.JsonResponse({'error': "Missing 'd'"}, status=400)
        size = int(request.GET.get('n', 10))
        results = []
        search = TitleDoc.search()

        print(Domain.objects.all().count(), "__DOMAINS__")
        for domain in Domain.objects.all().order_by('name'):
            print(
                '  ',
                domain.name,
                Title.objects.filter(domain=domain).count(), 'titles',
            )
            print(
                '  ',
                'Keys:',
                [x.key for x in Key.objects.filter(domain=d)]
            )
            print()

        # # search = search.filter()
        # # XXX needs to "filter" on domain and group
        # search = search.suggest('title_suggestions', q, completion={
        #     'field': 'value_suggest',
        #     'size': size,
        # })
        #
        # # XXX needs to sort my popularity
        # response = search.execute_suggest()

        # for suggestion in response.title_suggestions:
        #     print("SUGGESTION", suggestion)
        #     for option in suggestion.options:
        #         print("TEXT", option.text, option._score)

        # print("RESPONSE", response)
        # print("RESPONSE", dir(response))
        # for hit in response
        # for title in Title.objects.all():
        #     print(title)
        # for hit in response.hits:
        #     print('\tHIT', hit.to_dict())
        # print(Title.objects.all())
        # for x in Title.objects.all():
        #     print(x.value)
        search = TitleDoc.search()
        search = search.query('match_phrase_prefix', value=q)
        response = search.execute()
        for hit in response.hits:
            # print(hit.value, hit.url)
            results.append([
                hit.url,
                hit.value,

            ])
            # print('\t', hit.to_dict())
        return http.JsonResponse({
            'results': results,
            'terms': q,
        })


@auth_key
@csrf_exempt
def bulk(request, domain):
    # print(repr(request.body.decode('utf-8')))
    assert domain

    documents = json.loads(request.body.decode('utf-8'))['documents']
    # print(documents)
    for document in documents:
        Title.upsert(
            domain,
            url=document['url'],
            value=document['title'],
            popularity=float(document.get('popularity', 0.0)),
            group=document.get('group', ''),
        )
    # raise NotImplementedError
    return http.JsonResponse({'message': 'OK'}, status=201)


def ping(request):
    return http.HttpResponse('pong')
