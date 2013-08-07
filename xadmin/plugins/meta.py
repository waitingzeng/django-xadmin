# coding=utf-8
from xadmin.sites import site


from django.contrib.contenttypes.models import ContentType
class ContentTypeAdmin(object):
    list_per_page = 20
    list_display = ( 'name', 'app_label', 'model' )
    ordering = ('app_label', 'model')
    list_filter = ('app_label', 'model')
    search_fields = ('name', 'app_label', 'model' )

site.register( ContentType, ContentTypeAdmin)

from django.contrib.sessions.models import Session
class SessionAdmin(object):
    list_per_page = 20
    list_display = ( 'session_key', 'session_data', 'expire_date' )
    ordering = ('-expire_date',)
    search_fields = ('session_key',)

site.register( Session, SessionAdmin)


from django.contrib.admin.models import LogEntry
class LogEntryAdmin(object):
    list_per_page = 20
    list_display = ('action_time', 'user', 'content_type', 'object_id', 'object_repr', 'action_flag', 'change_message')
    ordering = ('-action_time',)
    list_filter = ('content_type', 'action_flag', 'user')
    date_hierarchy = 'action_time'
    search_fields = ('object_repr', 'change_message', 'user__username')

site.register( LogEntry, LogEntryAdmin)