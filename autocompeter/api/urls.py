from django.conf.urls import url

from autocompeter.api import views


urlpatterns = [
    url(
        r'^bulk$',
        views.bulk,
        name='bulk'
    ),
    url(
        r'^ping$',
        views.ping,
        name='ping'
    ),
    url(
        r'',
        views.home,
        name='home'
    ),
]
