
PLUGINS = ('actions', 'filters', 'bookmark', 'export', 'layout', 'refresh', 'sortable', 'details', 
    'editable', 'relate', 'chart', 'popup', 'ajax', 'relfield', 'inline', 'topnav', 'portal', 'quickform', 
    'wizard', 'images', 'auth', 'multiselect', 'themes', 'aggregation', 'mobile', 'passwords', 
    'sitemenu', 'language', 'comments', 'meta', 'batch_create', 'file_import', 'aggregation_queryset', 'user_list_display')

def register_builtin_plugins(site):
    from django.utils.importlib import import_module
    from django.conf import settings

    exclude_plugins = getattr(settings, 'XADMIN_EXCLUDE_PLUGINS', [])

    for plugin in PLUGINS:
        if plugin not in exclude_plugins:
            try:
                import_module('xadmin.plugins.%s' % plugin)
            except ImportError:
                pass
