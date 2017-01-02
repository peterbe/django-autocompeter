import hashlib
import json
import functools
import time

from elasticsearch_dsl.connections import connections
from elasticsearch.helpers import streaming_bulk
from elasticsearch_dsl.query import Q
from elasticsearch.exceptions import ConnectionTimeout

from django import http
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt

from autocompeter.main.models import Key, Domain, Search
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


def es_retry(callable, *args, **kwargs):
    sleep_time = kwargs.pop('_sleep_time', 1)
    attempts = kwargs.pop('_attempts', 10)
    verbose = kwargs.pop('_verbose', False)
    try:
        return callable(*args, **kwargs)
    except (ConnectionTimeout,) as exception:
        if attempts:
            attempts -= 1
            if verbose:
                print("ES Retrying ({} {}) {}".format(
                    attempts,
                    sleep_time,
                    exception
                ))
            time.sleep(sleep_time)
        else:
            raise


def make_id(*bits):
    return hashlib.md5(''.join(bits).encode('utf-8')).hexdigest()


@auth_key
@csrf_exempt
def home(request, domain):
    if request.method == 'POST':
        url = request.POST['url'].strip()
        assert url
        title = request.POST['title'].strip()
        assert title
        group = request.POST.get('group', '').strip()
        popularity = float(request.POST.get('popularity', 0.0))

        doc = {
            # 'id': make_id(domain.name, url),
            'domain': domain.name,
            'url': url,
            'title': title,
            'group': group,
            'popularity': popularity,
        }
        es_retry(TitleDoc(meta={'id': make_id(domain.name, url)}, **doc).save)
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
        groups = request.GET.get('g', '').strip()
        groups = [x.strip() for x in groups.split(',') if x.strip()]

        size = int(request.GET.get('n', 10))

        terms = [q]

        search = TitleDoc.search()

        # Only bother if the search term is long enough
        if len(q) > 2:
            suggestion = search.suggest('suggestions', q, term={
                'field': 'title',
            })
            suggestions = suggestion.execute_suggest()
            for suggestion in suggestions.suggestions:
                for option in suggestion.options:
                    terms.append(
                        q.replace(suggestion.text, option.text)
                    )
        results = []

        search = search.filter('term', domain=domain)
        query = Q('match_phrase', title=terms[0])
        for term in terms[1:]:
            query |= Q('match_phrase', title=term)

        if groups:
            # first, always include the empty group
            query &= Q('terms', group=[''] + groups)
        else:
            query &= Q('term', group='')

        search = search.query(query)
        search = search.sort('-popularity', '_score')
        search = search[:size]
        response = search.execute()
        for hit in response.hits:
            results.append([
                hit.url,
                hit.title,

            ])
        Search.objects.create(
            domain=domain,
            term=q,
            results=len(results),
        )
        return http.JsonResponse({
            'results': results,
            'terms': terms,
        })


@auth_key
@csrf_exempt
def bulk(request, domain):
    assert domain

    documents = json.loads(request.body.decode('utf-8'))['documents']

    def iterator():
        for document in documents:
            url = document['url'].strip()
            yield TitleDoc(
                meta={'id': make_id(domain.name, url)},
                **{
                    'domain': domain.name,
                    'url': url,
                    'title': document['title'].strip(),
                    'group': document.get('group', '').strip(),
                    'popularity': float(document.get('popularity', 0.0)),
                }
            ).to_dict(True)

    count = failures = 0

    t0 = time.time()
    for success, doc in streaming_bulk(
        connections.get_connection(),
        iterator(),
        index=settings.ES_INDEX,
        doc_type='title_doc',
    ):
        if not success:
            print("NOT SUCCESS!", doc)
            failures += 1
        count += 1
    t1 = time.time()

    return http.JsonResponse({
        'message': 'OK',
        'count': count,
        'failures': failures,
        'took': t1 - t0,
    }, status=201)


def ping(request):
    return http.HttpResponse('pong')
