from __future__ import with_statement

import logging
import tempfile
from datetime import datetime
from django.template import loader
from django.contrib import admin
from django.utils.translation import ugettext_lazy as _
from django.conf.urls import patterns, url
from django.template.response import TemplateResponse
from django.contrib import messages
from django.http import HttpResponseRedirect, HttpResponse
from django.core.urlresolvers import reverse
from xadmin.views import BaseAdminPlugin, ListAdminView
from xadmin.sites import site
from django import forms
from django.db import models

from import_export.resources import modelresource_factory
from import_export.formats import base_formats

#: import / export formats
DEFAULT_FORMATS = (
    base_formats.CSV,
    base_formats.XLS,
    base_formats.JSON,
)

class ImportForm(forms.Form):
    import_file = forms.FileField(
            label=_('File to import')
            )
    import_type = forms.CharField(widget=forms.HiddenInput())
    
class ImportMenuPlugin(BaseAdminPlugin):

    list_import = ('xls', 'csv', 'xml', 'json')
    import_names = {'xls': 'Excel', 'csv': 'CSV', 'xml': 'XML', 'json': 'JSON'}

    def init_request(self, *args, **kwargs):
        pass

    def block_top_toolbar(self, context, nodes):
        if self.list_import:

            context.update({
                'form_params': self.admin_view.get_form_params({'_do_': 'import'}, ('import_type',)),
            })
            nodes.append(loader.render_to_string('xadmin/blocks/model_list.top_toolbar.imports.html', context_instance=context))
        

class ImportPlugin(BaseAdminPlugin):
    """
    Import mixin.
    """
    import_fields = []
    list_import = ('xls', 'csv', 'xml', 'json')
    import_mimes = {'xls': 'application/vnd.ms-excel', 'csv': 'text/csv',
                    'xml': 'application/xhtml+xml', 'json': 'application/json'}
    import_names = {'xls': 'Excel', 'csv': 'CSV', 'xml': 'XML', 'json': 'JSON'}

    #: template for import view
    import_template_name = 'admin/import_export/import.html'
    #: resource class
    resource_class = None
    #: available import formats
    formats = DEFAULT_FORMATS
    #: import data encoding
    from_encoding = "utf-8"

    def init_request(self, *args, **kwargs):
        import_formats = self.get_import_formats().keys()
        self.list_import = [
            f for f in self.list_import if f in import_formats]
        if not self.import_fields:
            self.import_fields = [x.name for x in self.model._meta.fields]


    def block_top_toolbar(self, context, nodes):
        if self.list_import:
            import_formats = self.get_import_formats()

            context.update({
                'form_params': self.admin_view.get_form_params({'_do_': 'import'}, ('import_type',)),
                'import_types': [{'type': et, 'name': self.import_names[et]} for et in self.list_import],
            })
            nodes.append(loader.render_to_string('xadmin/blocks/model_list.top_toolbar.imports.html', context_instance=context))

    def get_response(self, response, context, *args, **kwargs):
        if self.request.REQUEST.get('_do_') != 'import':
            return response

        return self.import_action() or response

    def get_resource_class(self):
        if not self.resource_class:
            return modelresource_factory(self.model)
        else:
            return self.resource_class

    def get_import_formats(self):
        """
        Returns available import formats.
        """
        return {f.__name__.lower(): f for f in self.formats if f().can_import()}

    def get_field_data(self, field, value):
        if isinstance(field, models.ForeignKey):
            if not hasattr(field, 'all_data'):
                all_data = {unicode(x): x for x in field.rel.to.objects.all()}
                field.all_data = all_data
            value = field.all_data[value]
        
        return {field.name: value}

    def import_data(self, dataset, dry_run=False, raise_errors=False,
            use_transactions=None, include_header=False):
        """
        Imports data from ``dataset``.

        ``use_transactions``
            If ``True`` import process will be processed inside transaction.
            If ``dry_run`` is set, or error occurs, transaction will be rolled
            back.
        """
        fields = [self.model._meta.get_field(x) for x in self.import_fields]

        names_to_fields = {unicode(field.verbose_name): field for field in fields}
        for i, row in enumerate(dataset.dict):

            new_row = {}
            for k, v in row.items():
                field = names_to_fields[k]
                new_row.update(self.get_field_data(field, v))

            obj = self.model(**new_row)
            try:
                obj.pk = None
                obj.save()
            except Exception, e:
                logging.error('import data fail %s', new_row, exc_info=True)
                if raise_errors:
                    raise e

    def import_action(self):
        '''
        Perform a dry_run of the import to make sure the import will not
        result in errors.  If there where no error, save the user
        uploaded file to a local temp file that will be used by
        'process_import' for the actual import.
        '''
        resource = self.get_resource_class()()

        request = self.request
        context = {}

        import_formats = self.get_import_formats()
        form = ImportForm(request.POST or None,
                          request.FILES or None)
        if request.POST and form.is_valid():
            input_format = import_formats[
                form.cleaned_data['import_type']
            ]()
            import_file = form.cleaned_data['import_file']
            # first always write the uploaded file to disk as it may be a
            # memory file or else based on settings upload handlers
            with tempfile.NamedTemporaryFile(delete=False) as uploaded_file:
                for chunk in import_file.chunks():
                    uploaded_file.write(chunk)

            # then read the file, using the proper format-specific mode
            with open(uploaded_file.name,
                      input_format.get_read_mode()) as uploaded_import_file:
                # warning, big files may exceed memory
                data = uploaded_import_file.read()
                if not input_format.is_binary() and self.from_encoding:
                    data = unicode(data, self.from_encoding).encode('utf-8')
                dataset = input_format.create_dataset(data)
                result = self.import_data(dataset, dry_run=False,
                                              raise_errors=True)

                return None
        else:
            for k, v in form.errors.items():
                logging.error('%s: %s', k, v)
            return HttpResponse('Fail')
site.register_plugin(ImportPlugin, ListAdminView)
