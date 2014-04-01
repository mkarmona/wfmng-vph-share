from django.conf.urls.defaults import patterns, url, include
from django.contrib import admin

admin.autodiscover()

urlpatterns = patterns(
    'cyfronet.views',
    url(r'^cloudmanager/$', 'cloudmanager'),
    url(r'^tools/$', 'cloudmanager'),
    url(r'^datamanager/$', 'datamanager'),
    url(r'^policymanager/$', 'policymanager'),

    url(r'^lobcder(.*)$', 'lobcder'),

)
