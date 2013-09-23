#coding:utf-8
from itertools import chain

import xadmin
from django import forms
from django.db.models import ManyToManyField
from django.forms.util import flatatt
from django.template import loader
from django.utils.encoding import force_unicode
from django.utils.html import escape, conditional_escape
from django.utils.safestring import mark_safe
from xadmin.util import vendor
from xadmin.views import BaseAdminPlugin, ModelFormAdminView
from django.utils.safestring import mark_safe
from django.utils.html import conditional_escape, format_html, format_html_join
from django.utils.encoding import force_text, python_2_unicode_compatible



class SelectMultipleTransfer(forms.SelectMultiple):

    @property
    def media(self):
        return vendor('xadmin.widget.select-transfer.js', 'xadmin.widget.select-transfer.css')

    def __init__(self, verbose_name, is_stacked, attrs=None, choices=()):
        self.verbose_name = verbose_name
        self.is_stacked = is_stacked
        super(SelectMultipleTransfer, self).__init__(attrs, choices)

    def render_opt(self, selected_choices, option_value, option_label):
        option_value = force_unicode(option_value)
        return u'<option value="%s">%s</option>' % (
            escape(option_value), conditional_escape(force_unicode(option_label))), bool(option_value in selected_choices)

    def render(self, name, value, attrs=None, choices=()):
        if attrs is None:
            attrs = {}
        attrs['class'] = ''
        if self.is_stacked:
            attrs['class'] += 'stacked'
        if value is None:
            value = []
        final_attrs = self.build_attrs(attrs, name=name)

        selected_choices = set(force_unicode(v) for v in value)
        available_output = []
        chosen_output = []

        for option_value, option_label in chain(self.choices, choices):
            if isinstance(option_label, (list, tuple)):
                available_output.append(u'<optgroup label="%s">' %
                                        escape(force_unicode(option_value)))
                for option in option_label:
                    output, selected = self.render_opt(
                        selected_choices, *option)
                    if selected:
                        chosen_output.append(output)
                    else:
                        available_output.append(output)
                available_output.append(u'</optgroup>')
            else:
                output, selected = self.render_opt(
                    selected_choices, option_value, option_label)
                if selected:
                    chosen_output.append(output)
                else:
                    available_output.append(output)

        context = {
            'verbose_name': self.verbose_name,
            'attrs': attrs,
            'field_id': attrs['id'],
            'flatatts': flatatt(final_attrs),
            'available_options': u'\n'.join(available_output),
            'chosen_options': u'\n'.join(chosen_output),
        }
        return mark_safe(loader.render_to_string('xadmin/forms/transfer.html', context))


class SelectMultipleDropdown(forms.SelectMultiple):

    @property
    def media(self):
        return vendor('multiselect.js', 'multiselect.css', 'xadmin.widget.multiselect.js')

    def render(self, name, value, attrs=None, choices=()):
        if attrs is None:
            attrs = {}
        attrs['class'] = 'selectmultiple selectdropdown'
        return super(SelectMultipleDropdown, self).render(name, value, attrs, choices)


class SelectMultipleCheckbox(forms.CheckboxSelectMultiple):

    def render(self, name, value, attrs=None, choices=()):
        
        if value is None: value = []
        has_id = attrs and 'id' in attrs
        final_attrs = self.build_attrs(attrs, name=name)
        output = ['<ul class="list-inline">']
        # Normalize to strings
        str_values = set([force_text(v) for v in value])
        for i, (option_value, option_label) in enumerate(chain(self.choices, choices)):
            # If an ID attribute was given, add a numeric index as a suffix,
            # so that the checkboxes don't all have the same ID attribute.
            if has_id:
                final_attrs = dict(final_attrs, id='%s_%s' % (attrs['id'], i))
                label_for = format_html(' for="{0}"', final_attrs['id'])
            else:
                label_for = ''

            cb = forms.CheckboxInput(final_attrs, check_test=lambda value: value in str_values)
            option_value = force_text(option_value)
            rendered_cb = cb.render(name, option_value)
            option_label = force_text(option_label)
            output.append(format_html('<li><label{0}>{1} {2}</label></li>',
                                      label_for, rendered_cb, option_label))
        output.append('</ul>')
        return mark_safe('\n'.join(output))
        



class M2MSelectPlugin(BaseAdminPlugin):

    def init_request(self, *args, **kwargs):
        return hasattr(self.admin_view, 'style_fields') and \
            (
                'm2m_transfer' in self.admin_view.style_fields.values() or
                'm2m_dropdown' in self.admin_view.style_fields.values() or
                'm2m_checkbox' in self.admin_view.style_fields.values()
            )

    def get_field_style(self, attrs, db_field, style, **kwargs):
        if style == 'm2m_transfer' and isinstance(db_field, ManyToManyField):
            return {'widget': SelectMultipleTransfer(db_field.verbose_name, False), 'help_text': ''}
        if style == 'm2m_dropdown' and isinstance(db_field, ManyToManyField):
            return {'widget': SelectMultipleDropdown, 'help_text': ''}
        if style == 'm2m_checkbox' and isinstance(db_field, ManyToManyField):
            return {'widget': SelectMultipleCheckbox, 'help_text': ''}
        return attrs


xadmin.site.register_plugin(M2MSelectPlugin, ModelFormAdminView)
