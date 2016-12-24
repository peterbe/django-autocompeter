import os
import time

from django.core.management.base import BaseCommand
from django.conf import settings

from elasticsearch_dsl.connections import connections
from elasticsearch.helpers import streaming_bulk

from autocompeter.main.models import Title
from autocompeter.main.search import index, TitleDoc


class Command(BaseCommand):

    # def add_arguments(self, parser):
    #     parser.add_argument('--limit', default=10000)
    #     parser.add_argument('--offset', default=0)

    def handle(self, **options):
        # limit = int(options['limit'])
        # last_offset_fn = os.path.join(
        #     os.path.dirname(__file__),
        #     '.index-data'
        # )
        # if options['offset'] == 'remembered':
        #     try:
        #         with open(last_offset_fn) as f:
        #             offset = int(f.read()) + limit
        #     except FileNotFoundError:
        #         offset = 0
        # else:
        #     offset = int(options['offset'])

        self.es = connections.get_connection()
        index.delete(ignore=404)
        index.create()
        self.verbose_run(
            Title,
            limit=10000,
            offset=0,
            select_related='domain'
            # name='simple_artist',
        )

    def verbose_run(
        self,
        model,
        limit,
        offset,
        select_related=None,
        name=None,
    ):
        if not name:
            name = model._meta.verbose_name
        print('Indexing {}'.format(name))
        start = time.time()
        count = 0
        qs = model.objects.all().order_by('id')
        if select_related:
            qs = qs.select_related(select_related)
        iterator = qs[offset:offset + limit]
        report_every = max(1, int(limit / 1000))  # .1%
        print('report_every=', report_every)
        print('limit=', limit)
        print('offset=', offset)
        albums = None
        # if model == Song:
        #     albums = {}
        #     combos = Song.albums.through.objects.filter(
        #         song_id__gte=offset,
        #         song_id__lt=offset + limit
        #     )
        #     all_ = Album.objects.filter(id__in=combos.values('album_id'))
        #     album_map = {}
        #     for album in all_:
        #         album_map[album.id] = album
        #     for each in combos:
        #         if each.song_id not in albums:
        #             albums[each.song_id] = []
        #         albums[each.song_id].append(album_map[each.album_id])

        for success, doc in streaming_bulk(
                self.es,
                (
                    m.to_search().to_dict(True)
                    for m in iterator
                ),
                index=settings.ES_INDEX,
                doc_type=name.lower(),
        ):
            if not success:
                print("NOT SUCCESS!", doc)
            count += 1
            if not count % report_every:
                print(count + offset)
        print('DONE\nIndexing %d %s in %.2f seconds' % (
            count, name, time.time() - start
        ))
