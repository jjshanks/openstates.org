from django.shortcuts import render
from pupa.models import RunPlan
from opencivicdata.core.models import (Jurisdiction, Person, Organization,
                                       Membership)
from opencivicdata.legislative.models import Bill, VoteEvent
from admintools.models import (PeopleReport, OrganizationReport,
                               BillReport, VoteEventReport, DataQualityIssue)
from admintools.issues import IssueType
from collections import defaultdict


def overview(request):
    rows = []
    all_jurs = Jurisdiction.objects.order_by('name')
    for jur in all_jurs:
        reports = {}
        reports['name'] = jur.name
        reports['people'] = {'warning': PeopleReport.objects.get(jurisdiction=jur).warnings_count}
        reports['orgs'] = {'warning': OrganizationReport.objects.get(jurisdiction=jur).warnings_count,
                           'error': OrganizationReport.objects.get(jurisdiction=jur).no_memberships_count}
        reports['bills'] = {'warning': BillReport.objects.get(jurisdiction=jur).warnings_count,
                            'action_error': BillReport.objects.get(jurisdiction=jur).no_actions_count}
        reports['voteevents'] = {'warning': VoteEventReport.objects.get(jurisdiction=jur).warnings_count,
                                 'bill_error': VoteEventReport.objects.get(jurisdiction=jur).missing_bill_count,
                                 'counts_error': VoteEventReport.objects.get(jurisdiction=jur).missing_counts_count}

        run = RunPlan.objects.filter(jurisdiction=jur).order_by('-end_time').first()
        reports['run'] = {'status': run.success,
                          'date': run.end_time.date()}
        rows.append(reports)

    return render(request, 'admintools/index.html', {'rows': rows})


def jur_dataquality_issues(jur_name):
    cards = defaultdict(dict)
    l = {'person': PeopleReport,
         'organization': OrganizationReport,
         'membership': OrganizationReport,
         'bill': BillReport,
         'voteevent': VoteEventReport}
    issues = IssueType.choices()
    for issue, description in issues:
        related_class = IssueType.class_for(issue)
        cards[related_class][issue] = {}
        cards[related_class][issue]['alert'] = True if IssueType.level_for(issue) == 'error' else False
        cards[related_class][issue]['description'] = description
        label = issue.replace("-", "_") + '_count'
        cards[related_class][issue]['count'] = l[related_class].objects.filter(jurisdiction__name__exact=jur_name).values_list(label, flat=True).first()
    return dict(cards)


def jurisdiction_intro(request, jur_name):
    issues = jur_dataquality_issues(jur_name)
    return render(request, 'admintools/jurisdiction_intro.html', {'jur_name': jur_name,
                                                                  'cards': issues})


def list_issue_objects(request, jur_name, related_class, issue_slug=None):
    l = {'person': Person,
         'organization': Organization,
         'membership': Membership,
         'bill': Bill,
         'voteevent': VoteEvent}
    issues = [issue_slug] if issue_slug is not None else IssueType.get_issues_for(related_class)
    cards = defaultdict(list)
    for issue in issues:
        description = IssueType.description_for(issue)
        issue = IssueType.class_for(issue) + '-' + issue
        objects_list = DataQualityIssue.objects.filter(jurisdiction__name__exact=jur_name,
                                                       issue=issue).values_list('object_id',
                                                                                flat=True)
        cards[description] = list(l[related_class].objects.in_bulk(objects_list).values())
    cards = dict(cards)
    if related_class in ['person', 'organization']:
        url_slug = 'core_' + related_class + '_change'
    elif related_class in ['bill', 'voteevent']:
        url_slug = 'legislative_' + related_class + '_change'
    else:
        url_slug = None
    return render(request, 'admintools/list_issues.html', {'jur_name': jur_name,
                                                           'cards': cards,
                                                           'url_slug': url_slug})
