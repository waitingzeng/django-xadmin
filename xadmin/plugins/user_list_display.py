
from xadmin.sites import site
from xadmin.models import UserSettings
from xadmin.views import BaseAdminPlugin, ListAdminView
from xadmin.views.list import COL_LIST_VAR


class UserListDisplayPlugin(BaseAdminPlugin):

    def init_request(self, *args, **kwargs):
        if self.request.GET.get('_popup'):
            return False
        opts = self.model._meta
        self.settings_key = "userlistdisplay:%s_%s" % (opts.app_label, opts.module_name)
        try:
            self._obj, create = UserSettings.objects.get_or_create(user=self.user, key=self.settings_key)
            if create:
                self.user_list_display = None
            else:
                self.user_list_display = self.filter_list_display(obj.value)
        except:
            self.user_list_display = None
        return True

    def filter_list_display(self, value):
        return [x for x in value.split('.') if x.strip() and x != 'action_checkbox' ]

    def _get_list_display(self, __):
        if COL_LIST_VAR in self.request.GET:
            self._obj.value = self.request.GET[COL_LIST_VAR]
            self._obj.save()

            return self.filter_list_display(self._obj.value)

        if self.user_list_display:
            return self.user_list_display
        return __()

    def get_list_display(self, __):
        self.admin_view.base_list_display = self._get_list_display(__)
        return self.admin_view.base_list_display

site.register_plugin(UserListDisplayPlugin, ListAdminView)
