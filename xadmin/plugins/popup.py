from django import forms
from django.utils.datastructures import SortedDict
from django.utils.html import escape
from django.utils.encoding import force_unicode
from xadmin.sites import site
from xadmin.views import BaseAdminPlugin, ListAdminView, ModelFormAdminView, DetailAdminView
from django.template.response import SimpleTemplateResponse, TemplateResponse



NON_FIELD_ERRORS = '__all__'


class BasePopPlugin(BaseAdminPlugin):

    def init_request(self, *args, **kwargs):
        return bool(self.request.REQUEST.get('_popup'))


class PopupListPlugin(BasePopPlugin):

    def get_result_list(self, response):
        av = self.admin_view
        base_fields = av.base_list_display
        headers = [force_unicode(c.text) for c in av.result_headers(
        ).cells if c.field_name in base_fields]

        objects = []
        for r in av.results():
            items = []
            for o in filter(lambda c:c.field_name in base_fields, r.cells):
                items.append(escape(str(o.value)))
            objects.append(items)

        return SimpleTemplateResponse('xadmin/blocks/popup_list.html', {'headers': headers, 'objects': objects, 'total_count': av.result_count, 'has_more': av.has_more})

site.register_plugin(PopupListPlugin, ListAdminView)
