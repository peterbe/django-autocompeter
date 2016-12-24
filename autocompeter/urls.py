from django.conf.urls import url, include

import autocompeter.main.urls
import autocompeter.api.urls

urlpatterns = [
    url('', include(autocompeter.main.urls.urlpatterns)),
    url(r'^v1/?', include(autocompeter.api.urls.urlpatterns)),
]
