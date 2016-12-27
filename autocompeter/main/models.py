import time

from django.db.models.signals import post_save, pre_delete
from django.db import models
from django.contrib.auth.models import User

from elasticsearch.exceptions import (
    ConnectionTimeout,
    NotFoundError,
)

from autocompeter.main.search import TitleDoc


# User = get_user_model()

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


class Domain(models.Model):
    name = models.CharField(max_length=100)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Title(models.Model):
    domain = models.ForeignKey(Domain)
    value = models.TextField()
    url = models.URLField(max_length=500)
    popularity = models.FloatField(default=0.0)
    group = models.CharField(max_length=100, null=True)
    modified = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.value

    @classmethod
    def upsert(cls, domain, url, value, group='', popularity=0.0):
        try:
            found = cls.objects.get(
                domain=domain,
                url=url,
            )
            if (
                found.value != value or
                found.popularity != popularity or
                found.group != group
            ):
                found.value = value
                found.popularity = popularity
                found.group = group
                found.save()
            return found
        except cls.DoesNotExist:
            return cls.objects.create(
                domain=domain,
                url=url,
                value=value,
                popularity=popularity,
                group=group,
            )

    def to_search(self):
        assert isinstance(self.value, str)
        doc = {
            'id': self.id,
            # '_id': self.id,
            'domain': self.domain.name,
            'url': self.url,
            'value': self.value,
            'value_suggest': self.value,
            'group': self.group,
            'popularity': self.popularity,
        }
        # print("DOC", doc)
        # print("SELF?", repr(self))
        # print("TTITLE?", repr(doc['title']), type(doc['title']))
        return TitleDoc(**doc)


def update_es(instance, sender, **kwargs):
    doc = instance.to_search()
    # print("IN UPDATE_ES", doc)
    es_retry(doc.save)


post_save.connect(update_es, sender=Title)


def remove_from_es(instance, sender, **kwargs):
    # doc = instance.to_search()
    doc = TitleDoc(_id=instance.id)
    # raise Exception('what are you doing here??')
    # print("IN REMOVE_FROM_ES")
    try:
        doc.delete()
    except NotFoundError:
        print("WARNING! {!r} was not in ES".format(
            instance
        ))


pre_delete.connect(remove_from_es, sender=Title)


class Key(models.Model):
    domain = models.ForeignKey(Domain)
    key = models.TextField(db_index=True, unique=True)
    user = models.ForeignKey(User)
    modified = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.key


class Search(models.Model):
    domain = models.ForeignKey(Domain)
    term = models.TextField()
    results = models.IntegerField(default=0)
    created = models.DateTimeField(auto_now_add=True)
