from django.utils.translation import ugettext as _

from xadmin.sites import site
from xadmin.views import BaseAdminPlugin, ListAdminView

from xadmin.views.list import ResultRow, ResultItem
from xadmin.util import display_for_field
from django.db.models import FieldDoesNotExist

AGGREGATE_TITLE = {
    'min': _('Min'), 'max': _('Max'), 'avg': _('Avg'), 'sum': _('Sum'), 'count': _('Count')
}


class AggregationQuerySetPlugin(BaseAdminPlugin):

    aggregate_queryset_fields = {}
    aggregate_queryset_all = False

    def init_request(self, *args, **kwargs):
        return bool(self.aggregate_queryset_fields) and not bool(self.request.REQUEST.get('_popup'))

    def _get_field_aggregate(self, field_name, queryset, row):
        item = ResultItem(field_name, row)
        item.classes = ['aggregate', ]
        if field_name not in self.aggregate_queryset_fields:
            item.text = ""
        else:
            try:
                agg_method = self.aggregate_queryset_fields[field_name]
                key = '%s__%s' % (field_name, agg_method)

                all_values = []
                for obj in queryset:
                    v = getattr(obj, field_name)
                    if callable(v):
                        v = v()
                    all_values.append(v)

                value = sum(all_values)
                if agg_method == 'min':
                    value = min(all_values)
                elif agg_method == 'max':
                    value = max(all_values)
                elif agg_method == 'avg':
                    value = value / len(all_values)
                elif agg_method == 'count':
                    value = len(all_values)

                item.text = value
                item.wraps.append('%%s<span class="aggregate_title label label-info">%s</span>' % AGGREGATE_TITLE[agg_method])
                item.classes.append(agg_method)
            except FieldDoesNotExist:
                item.text = ""

        return item

    def _get_aggregate_row(self):
        if self.aggregate_queryset_all:
            queryset = self.admin_view.list_queryset._clone()
        else:
            queryset = self.admin_view.result_list._clone()
        
        row = ResultRow()
        row['is_display_first'] = False
        row.cells = [self._get_field_aggregate(field_name, queryset, row) for field_name in self.admin_view.list_display]
        row.css_class = 'info aggregate'
        return row

    def results(self, rows):
        if rows:
            rows.append(self._get_aggregate_row())
        return rows

    # Media
    def get_media(self, media):
        media.add_css({'screen': [self.static(
            'xadmin/css/xadmin.plugin.aggregation.css'), ]})
        return media


site.register_plugin(AggregationQuerySetPlugin, ListAdminView)
