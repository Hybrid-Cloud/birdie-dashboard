# Copyright (c) 2017 Huawei, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
from django.core.urlresolvers import reverse
from django.template.defaultfilters import title  # noqa
from django.utils.http import urlencode
from django.utils.translation import gettext_lazy
from django.utils.translation import pgettext_lazy
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ungettext_lazy

from horizon import tables
from horizon.utils import filters
from oslo_log import log as logging

from conveyordashboard.api import api

LOG = logging.getLogger(__name__)

ALLOW_CLONE_STATUS = ('available', 'cloning', 'finished')
ALLOW_MIGRATE_STATUS = ('available', 'migrating', 'finished')
ALLOW_MODIFY_STATUS = ('initiating', 'available', 'finished')
NOT_ALLOW_EXPORT_STATUS = ('creating', 'error', 'initiating')


class UpdateRow(tables.Row):
    ajax = True

    def get_data(self, request, plan_id):
        plan = api.plan_get(request, plan_id)
        return plan


class DeletePlan(tables.DeleteAction):
    name = 'delete'
    classes = ("btn-default", "btn-danger",)
    icon = 'remove'
    help_text = _("Delete plan is not recoverable.")

    @staticmethod
    def action_present(count):
        return ungettext_lazy(
            u"Delete Plan",
            u"Delete Plans",
            count
        )

    @staticmethod
    def action_past(count):
        return ungettext_lazy(
            u"Scheduled deletion of Plan",
            u"Scheduled deletion of Plans",
            count
        )

    def allowed(self, request, plan=None):
        return True

    def action(self, request, obj_id):
        api.plan_delete(request, obj_id)


class ModifyPlan(tables.LinkAction):
    name = 'modify'
    verbose_name = _("Modify")
    url = 'horizon:conveyor:plans:modify'
    classes = ("ajax-modal",)

    def allowed(self, request, plan):
        return (plan.plan_type == 'clone'
                and plan.plan_status in ALLOW_MODIFY_STATUS)


class ClonePlan(tables.LinkAction):
    name = 'clone'
    verbose_name = _("Clone")
    url = 'horizon:conveyor:plans:clone'
    classes = ("ajax-modal", "btn-default", "btn-clone")
    help_text = _("Execute clone plan")

    def allowed(self, request, plan):
        return (plan.plan_type == 'clone'
                and plan.plan_status in ALLOW_CLONE_STATUS)

    def get_link_url(self, datum):
        base_url = reverse(self.url)
        params = urlencode({'plan_id': self.table.get_object_id(datum),
                            'type': 'clone',
                            'next_url': self.table.get_full_url()})
        return '?'.join([base_url, params])


class MigratePlan(tables.LinkAction):
    name = 'migrate'
    verbose_name = _("Migrate")
    url = 'horizon:conveyor:plans:migrate'
    classes = ("ajax-modal", "btn-default", "btn-migrate")
    help_text = _("Execute migrate plan")

    def get_link_url(self, datum):
        base_url = reverse(self.url)
        params = urlencode({'plan_id': self.table.get_object_id(datum),
                            'type': 'migrate',
                            'next_url': self.table.get_full_url()})
        return '?'.join([base_url, params])

    def allowed(self, request, plan):
        return (plan.plan_type == 'migrate'
                and plan.plan_status in ALLOW_MIGRATE_STATUS)


class ImportPlan(tables.LinkAction):
    name = 'import'
    verbose_name = _("Import")
    url = 'horizon:conveyor:plans:import'
    icon = 'upload'
    classes = ("ajax-modal", "btn-default", "btn-import")
    help_text = _("Import plan from local")


class ExportPlan(tables.LinkAction):
    name = 'export'
    verbose_name = _("Download")
    icon = 'download'
    url = 'horizon:conveyor:plans:export'

    def allowed(self, request, plan):
        return plan.plan_status not in NOT_ALLOW_EXPORT_STATUS


class GenerateTemplate(tables.BatchAction):
    name = 'generate_template'

    @staticmethod
    def action_present(count):
        return ungettext_lazy(
            u"Generate Template",
            u"Generate Templates",
            count
        )

    @staticmethod
    def action_past(count):
        return ungettext_lazy(
            u"Generated Template",
            u"Generated Templates",
            count
        )

    def allowed(self, request, plan):
        return plan.plan_status in ('initiating',)

    def action(self, request, obj_id):
        plan = api.plan_get(request, obj_id)
        if plan.plan_type == 'clone':
            api.export_clone_template(request, obj_id)
        elif plan.plan_type == 'migrate':
            api.export_migrate_template(request, obj_id)
        else:
            raise Exception("Unknown plan type %s" % plan.plan_type)


class PlanFilterAction(tables.FilterAction):
    def filter(self, table, plans, filter_string):
        q = filter_string.lower()

        def comp(plan):
            return q in plan.name.lower()

        return filter(comp, plans)


PLAN_TYPE_CHOICES = (
    ("clone", gettext_lazy(u"Clone")),
    ("migrate", gettext_lazy(u"Migrate"))
)

STATUS_DISPLAY_CHOICES = (
    ("initiating", pgettext_lazy("Current status of plan", u"Initiating")),
    ("creating", pgettext_lazy("Current status of plan", u"Creating")),
    ("available", pgettext_lazy("Current status of plan", u"Available")),
    ("cloning", pgettext_lazy("Current status of plan", u"Cloning")),
    ("migrating", pgettext_lazy("Current status of plan", u"Migrating")),
    ("finished", pgettext_lazy("Current status of plan", u"Finished")),
    ("deleting", pgettext_lazy("Current status of plan", u"Deleting")),
    ("deleted", pgettext_lazy("Current status of plan", u"Deleted")),
    ("error", pgettext_lazy("Current status of plan", u"Error")),
    ("error_deleting",
     pgettext_lazy("Current status of plan", u"Error Deleting")),
)

TASK_DISPLAY_NONE = pgettext_lazy("Task status of plan", u"None")

TASK_DISPLAY_CHOICES = (
    ("deploying", pgettext_lazy("Task status of plan", u"Deploying")),
    ("finished", pgettext_lazy("Task status of plan", u"Finished")),
    ("failed", pgettext_lazy("Task status of plan", u"Failed")),
)


class PlansTable(tables.DataTable):
    PLAN_STATUS_CHOICES = (
        ('available', True),
        ('error', False),
        ('finished', True))
    TASK_STATUS_CHOICES = (
        (None, True),
        ('none', True),
        ('', True),
    )
    # NOTE(gabriel): Commenting out the user column because all we have
    # is an ID, and correlating that at production scale using our current
    # techniques isn't practical. It can be added back in when we have names
    # returned in a practical manner by the API.
    plan_name = tables.Column("plan_name",
                              link="horizon:conveyor:plans:detail",
                              verbose_name=_("Plan Name"))
    plan_type = tables.Column("plan_type",
                              filters=(title,),
                              verbose_name=_("Plan Type"),
                              display_choices=PLAN_TYPE_CHOICES)
    created = tables.Column("created_at",
                            verbose_name=_("Time since created"),
                            filters=(filters.parse_isotime,
                                     filters.timesince_sortable),
                            attrs={'data-type': 'timesince'})
    plan_status = tables.Column("plan_status",
                                filters=(title, filters.replace_underscores),
                                verbose_name=_("Plan Status"),
                                status=True,
                                status_choices=PLAN_STATUS_CHOICES,
                                display_choices=STATUS_DISPLAY_CHOICES)
    task_status = tables.Column("task_status",
                                verbose_name=_("Task Status"),
                                status=True,
                                empty_value=TASK_DISPLAY_NONE,
                                status_choices=TASK_STATUS_CHOICES,
                                display_choices=TASK_DISPLAY_CHOICES)

    def get_object_id(self, obj):
        return obj.plan_id

    class Meta(object):
        name = 'plans'
        verbose_name = _("Plans")
        status_columns = ["plan_status", ]
        table_actions = (ImportPlan, DeletePlan, PlanFilterAction)
        row_class = UpdateRow
        row_actions = (ClonePlan, MigratePlan, GenerateTemplate,
                       ModifyPlan, ExportPlan, DeletePlan,)
