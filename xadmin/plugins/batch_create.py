#!/user/bin/python
#coding=utf8
from xadmin.views import BaseAdminPlugin, ListAdminView, CreateAdminView
from xadmin.views.base import filter_hook, ModelAdminView
from xadmin.sites import site
from django.core.urlresolvers import reverse
import json
import urllib
from django import forms
from django.template.response import TemplateResponse
import logging
from django.http.request import QueryDict



class BatchCreatePlugin(BaseAdminPlugin):
    # Actions
    batch_create_fields = []

    def init_request(self, *args, **kwargs):
        return bool(self.batch_create_fields)

    def get_bulkcreate_url(self, *args, **kwargs):
        url = self.get_model_url(self.model, 'bulkcreate', *args, **kwargs)
        querystring = json.dumps(self.batch_create_fields)
        return '%s?%s' % (url, urllib.quote_plus(querystring))

    def block_object_tools(self, context, nodes):
        name = ' Bulk Create ' + self.opts.verbose_name
        url = self.get_bulkcreate_url()
        nodes.append('<form class="exform pull-right"><a href="%(url)s" class="btn btn-ajax" data-for-id="content-block" data-refresh-url="#" title="%(name)s"><i class="icon-plus icon-white"></i>%(name)s</a></form>' % locals())

site.register_plugin(BatchCreatePlugin, ListAdminView)




class BulkCreateView(CreateAdminView):
    new_create = 0
    had_exists = 0
    create_error = 0
    
    def get_fields(self):
        querystring = urllib.unquote_plus(self.request.META['QUERY_STRING'])

        self.batch_create_fields = json.loads(querystring)
        return self.batch_create_fields

    def get_form_url(self):
        return '%s?%s' % (self.request.path, self.request.META['QUERY_STRING'])

    def get(self, request, *args, **kwargs):
        self.get_fields()
        return TemplateResponse(
            self.request, 'xadmin/views/quick_form.html',
            {'form': self.get_change_form(), 'form_url': self.get_form_url()}, current_app=self.admin_site.name)

    def get_change_form(self):
        options = {
        }
        for name in self.batch_create_fields:
            field = self.opts.get_field(name)
            options[name] = forms.CharField(widget=forms.Textarea, label=field.verbose_name)
        return type(str("%s%sBulkCreateForm" % (self.opts.app_label, self.opts.module_name)), (forms.Form,), options)
        
    def bulkcreate(self, line):
        if line.find('-') != -1:
            start, end = line.split('-', 1)
        else:
            start, end = line, line

        base = start
        base_len = len(base)
        start, end = int(start), int(end)
        for num in xrange(start, end+1):
            num = str(num)
            phone_number = base[:base_len - len(num)] + num
            try:
                obj, create = PhoneNumber.objects.get_or_create(phone=phone_number, user=self.user)
            except:
                logging.exception('create %s fail', phone_number)
                self.create_error += 1
                continue
            if create:
                self.new_create += 1
            else:
                self.had_exists += 1

    def post(self, request, *args, **kwargs):
        self.get_fields()
        data = {}
        max_len = 0
        for field in self.batch_create_fields:
            data[field] = request.REQUEST.get(field).split('\n')
            max_len = max(len(data[field]), max_len)

        for i in range(max_len):
            item_data = {}
            try:
                for field in self.batch_create_fields:
                    item_data[field] = data[field][i]
            except:
                logging.error('get form data fail', exc_info=True)
                break
            try:
                request.POST = item_data
                self.instance_forms()
                self.setup_forms()
                if self.form_obj.is_valid():
                    self.form_obj.save()
                    self.new_create += 1
                else:
                    logging.error('invalid data %s error %s', item_data, self.form_obj.errors)
                    self.create_error += 1
            except Exception, e:
                logging.error('create error %s', e, exc_info=True)
                self.create_error += 1

        self.message_user('new create %s, error %s' % (self.new_create, self.create_error))
        return self.ajax_success()

site.register_modelview(r'^bulkcreate/$', BulkCreateView, name='%s_%s_bulkcreate')
