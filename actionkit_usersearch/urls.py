from django.conf.urls.defaults import patterns, include, url

urlpatterns = patterns(
    'actionkit_usersearch.views',
    url('^$',
        'search',
        name='usersearch_search'),
    )
