from elasticsearch_dsl import (
    Completion,
    DocType,
    Integer,
    Float,
    Text,
    Nested,
    Object,
    Index,
    analyzer,
)

from django.conf import settings



class TitleDoc(DocType):
    id = Integer()
    domain = Text(fields={'raw': Text(index='not_analyzed')})
    value = Text(analyzer='standard')
    value_suggest = Completion()
    url = Text(fields={'raw': Text(index='not_analyzed')})
    popularity = Float()
    group = Text(fields={'raw': Text(index='not_analyzed')})
    # name = String(analyzer=html_strip)
    # name_suggest = Completion(payloads=True)
    # key_phrases_suggest = Completion(payloads=True)
    # text = String(analyzer=html_strip)



# create an index and register the doc types
index = Index(settings.ES_INDEX)
index.settings(**settings.ES_INDEX_SETTINGS)
index.doc_type(TitleDoc)
