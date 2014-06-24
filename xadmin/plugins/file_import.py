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

import warnings
import tablib
from django.utils import simplejson as json

try:
    from tablib.compat import xlrd
    XLS_IMPORT = True
except ImportError:
    try:
        import xlrd # NOQA
        XLS_IMPORT = True
    except ImportError:
        xls_warning = "Installed `tablib` library does not include"
        "import support for 'xls' format and xlrd module is not found."
        warnings.warn(xls_warning, ImportWarning)
        XLS_IMPORT = False

from django.utils.importlib import import_module


class Format(object):

    def get_title(self):
        return type(self)

    def create_dataset(self, in_stream):
        """
        Create dataset from given string.
        """
        raise NotImplementedError()

    def export_data(self, dataset):
        """
        Returns format representation for given dataset.
        """
        raise NotImplementedError()

    def is_binary(self):
        """
        Returns if this format is binary.
        """
        return True

    def get_read_mode(self):
        """
        Returns mode for opening files.
        """
        return 'rb'

    def get_extension(self):
        """
        Returns extension for this format files.
        """
        return ""

    def can_import(self):
        return False

    def can_export(self):
        return False


class TablibFormat(Format):
    TABLIB_MODULE = None

    def get_format(self):
        """
        Import and returns tablib module.
        """
        return import_module(self.TABLIB_MODULE)

    def get_title(self):
        return self.get_format().title

    def create_dataset(self, in_stream):
        data = tablib.Dataset()
        self.get_format().import_set(data, in_stream)
        return data

    def export_data(self, dataset):
        return self.get_format().export_set(dataset)

    def get_extension(self):
        # we support both 'extentions' and 'extensions' because currently tablib's master
        # branch uses 'extentions' (which is a typo) but it's dev branch already uses 'extension'.
        # TODO - remove this once the typo is fixxed in tablib's master branch
        if hasattr(self.get_format(), 'extentions'):
            return self.get_format().extentions[0]
        return self.get_format().extensions[0]

    def can_import(self):
        return hasattr(self.get_format(), 'import_set')

    def can_export(self):
        return hasattr(self.get_format(), 'export_set')


class TextFormat(TablibFormat):

    def get_read_mode(self):
        return 'rU'

    def is_binary(self):
        return False


class CSV(TextFormat):
    TABLIB_MODULE = 'tablib.formats._csv'


class JSON(TextFormat):
    TABLIB_MODULE = 'tablib.formats._json'


class YAML(TextFormat):
    TABLIB_MODULE = 'tablib.formats._yaml'


class TSV(TextFormat):
    TABLIB_MODULE = 'tablib.formats._tsv'


class ODS(TextFormat):
    TABLIB_MODULE = 'tablib.formats._ods'


class XLSX(TextFormat):
    TABLIB_MODULE = 'tablib.formats._xlsx'


class HTML(TextFormat):
    TABLIB_MODULE = 'tablib.formats._html'


class XLS(TablibFormat):
    TABLIB_MODULE = 'tablib.formats._xls'

    def can_import(self):
        return XLS_IMPORT

    def create_dataset(self, in_stream):
        """
        Create dataset from first sheet.
        """
        assert XLS_IMPORT
        xls_book = xlrd.open_workbook(file_contents=in_stream)
        dataset = tablib.Dataset()
        sheet = xls_book.sheets()[0]
        ncols = sheet.ncols
        for i in xrange(sheet.nrows):
            if i == 0:
                dataset.headers = sheet.row_values(0)
            else:
                row_data = []
                for j in range(0, ncols):
                    value = sheet.cell_value(i, j)
                    t = sheet.cell_type(i, j)
                    if t == xlrd.XL_CELL_DATE:
                        value = xlrd.xldate_as_tuple(value, 0)
                        value = datetime(*value)
                    row_data.append(value)
                dataset.append(row_data)
        return dataset

#: import / export formats
DEFAULT_FORMATS = (
    CSV,
    XLS,
    JSON,
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

        self.fields_data = {}
        self.import_errors = []

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
            if field.name not in self.fields_data:
                all_data = {unicode(x): x for x in field.rel.to.objects.all()}
                self.fields_data[field.name] = all_data
            value = self.fields_data[field.name][value]
        if field.choices:
            if field.name not in self.fields_data:
                all_data = {unicode(v): k for k, v in field.choices}
                self.fields_data[field.name] = all_data
            value = self.fields_data[field.name][value]

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
        success = 0
        fail = 0
        for i, row in enumerate(dataset.dict):
            new_row = {}
            try:
                for k, v in row.items():
                    field = names_to_fields[k]
                    try:
                        v = v.strip()
                    except:
                        pass
                    try:
                        new_row.update(self.get_field_data(field, v))
                    except KeyError, e:
                        msg = "`%s` : `%s` not found" % (field.verbose_name, v)
                        self.import_errors.append([new_row, msg])
                        logging.error(msg, exc_info=True)
                        raise e
                obj = self.model(**new_row)
                obj.save()
                success += 1
            except Exception, e:
                logging.error('import data fail %s', new_row, exc_info=True)
                if raise_errors:
                    raise e
                self.import_errors.append([new_row, e.message])
                fail += 1

        return success, fail

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
                success, fail = result = self.import_data(dataset, dry_run=False,
                                              raise_errors=False)

                self.admin_view.message_user('Import success %s, fail %s' % (success, fail))
                for row, msg in self.import_errors:
                    self.admin_view.message_user('msg: %s, row: %s' % (str(msg), str(row)))

                return HttpResponseRedirect('.')
        else:
            for k, v in form.errors.items():
                logging.error('%s: %s', k, v)
            return HttpResponse('Fail')
site.register_plugin(ImportPlugin, ListAdminView)
