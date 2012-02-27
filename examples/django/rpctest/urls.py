from django.conf.urls.defaults import patterns, include, url

urlpatterns = patterns('',
    url(r'^hello_world/','core.views.hello_world_service'),
)
