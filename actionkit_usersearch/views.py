from actionkit.models import *
from django.conf import settings
from django.http import HttpResponse
from djangohelpers import rendered_with, allow_http
import json

from actionkit_usersearch.models import SearchColumn

@allow_http("GET")
@rendered_with("actionkit_usersearch/build_search.html")
def search(request):
    column_options = SearchColumn.objects.all()

    tags = CoreTag.objects.using("ak").all().order_by("name")
    countries = CoreUser.objects.using("ak").values_list(
            "country", flat=True).distinct().order_by("country")

    pages = CorePage.objects.using("ak").all().order_by("title")

    campuses = CoreUserField.objects.using("ak").filter(
            name="campus").values_list(
            "value", flat=True).distinct().order_by("value")

    skills = CoreUserField.objects.using("ak").filter(
            name="skills").values_list(
            "value", flat=True).distinct().order_by("value")
    engagement_levels = CoreUserField.objects.using("ak").filter(
        name="engagement_level").values_list(
        "value", flat=True).distinct().order_by("value")
    affiliations = CoreUserField.objects.using("ak").filter(
            name="affiliation").values_list(
            "value", flat=True).distinct().order_by("value")

    languages = CoreLanguage.objects.using(
            "ak").all().distinct().order_by("name")

    fields = {
        'Location':
            (('country', 'Country'),
             ('state', 'State', 'disabled'),
             ('city', 'City', 'disabled'),
             ('zipcode', 'Zip Code'),
             ),
        'Activity':
            (('action', 'Took part in action'),
             ('source', 'Source'),
             ('tag', 'Is tagged with'),
             ('contacted_since', "Contacted Since"),
             ('contacted_by', "Contacted By"),
             ('emails_opened', "Emails Opened"),
             ('more_actions', "More Actions Since"),
             ('donated_more', "Donated Amount More Than"),
             ('donated_times', "Donated Times More Than"),
             ),
        'About':
            (('campus', "Campus"),
             ('skills', "Skills"),
             ('engagement_level', "Engagement Level"),
             ('language', "Preferred Language"),
             ('student', "Student"),
             ('affiliation', "Affiliation"),
             ('created_before', "Created Before"),
             ('created_after', "Created After"),
             ),
        }

    return locals()


