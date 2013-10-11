from actionkit.models import *
from django.conf import settings
from django.http import HttpResponse
from djangohelpers import rendered_with, allow_http
import json

from actionkit_usersearch.models import SearchColumn

@allow_http("GET")
def campuses(request):
    prefix = request.GET.get('q')
    limit = request.GET.get('limit', '10')
    try:
        limit = int(limit)
    except ValueError:
        limit = 10
    limit = clamp(limit, 1, 1000)
    if prefix:
        cursor = connections['ak'].cursor()
        prefix = prefix + '%'
        cursor.execute("SELECT distinct value FROM core_userfield "
                       "WHERE name=\"campus\" and value LIKE %s ORDER BY value LIMIT %s",
                       [prefix, limit])
        values = [row[0] for row in cursor.fetchall()]
        if not values:
            prefix = '%' + prefix
            cursor.execute("SELECT distinct value FROM core_userfield "
                           "WHERE name=\"campus\" and value LIKE %s ORDER BY value LIMIT %s",
                           [prefix, limit])
            values = [row[0] for row in cursor.fetchall()]
    else:
        values = []

    return HttpResponse(json.dumps(values), content_type='application/json')

@allow_http("GET")
def sources(request):
    prefix = request.GET.get('q')
    limit = request.GET.get('limit', '10')
    try:
        limit = int(limit)
    except ValueError:
        limit = 10
    limit = clamp(limit, 1, 1000)
    if prefix:
        cursor = connections['ak'].cursor()
        prefix = prefix + '%'
        cursor.execute("SELECT distinct source FROM core_user "
                       "WHERE source LIKE %s ORDER BY source LIMIT %s",
                       [prefix, limit])
        sources = [row[0] for row in cursor.fetchall()]
    else:
        sources = []
    return HttpResponse(json.dumps(sources), content_type='application/json')

@allow_http("GET")
def countries(request):
    countries = CoreUser.objects.using("ak").values_list("country", flat=True).distinct().order_by("country")
    countries = [(i,i) for i in countries]
    return HttpResponse(json.dumps(countries),
                        content_type="application/json")

@allow_http("GET")
def regions(request):
    countries = request.GET.getlist("country")
    raw_regions = CoreUser.objects.using("ak").filter(
        country__in=countries).values(
        "country", "region").distinct().order_by("country", "region")
    regions = {}
    for region in raw_regions:
        if region['country'] not in regions:
            regions[region['country']] = []
        regions[region['country']].append(region['region'])
    return HttpResponse(json.dumps(regions), 
                        content_type="application/json")

@allow_http("GET")
def states(request):
    countries = request.GET.getlist("country")
    raw_states = CoreUser.objects.using("ak").filter(
        country__in=countries).values(
        "country", "state").distinct().order_by("country", "state")
    states = {}
    for state in raw_states:
        if state['country'] not in states:
            states[state['country']] = []
        states[state['country']].append(state['state'])
    return HttpResponse(json.dumps(states), 
                        content_type="application/json")

@allow_http("GET")
def cities(request):
    cities = CoreUser.objects.using("ak").values_list("city", flat=True).distinct().order_by("city")
    cities = [(i,i) for i in cities]
    return HttpResponse(json.dumps(cities), 
                        content_type="application/json")

@allow_http("GET")
def pages(request):
    pages = CorePage.objects.using("ak").all().order_by("title")
    pages = [(i.id, str(i)) for i in pages]
    return HttpResponse(json.dumps(pages), 
                        content_type="application/json")

@allow_http("GET")
@rendered_with("actionkit_usersearch/build_search.html")
def search(request):
    column_options = SearchColumn.objects.all()

    """
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
            """

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

from actionkit_usersearch.search_functions import (build_query, 
                                                   _search2)

@allow_http("POST")
def create_report(request):
    # @@TODO
    """
    if request.GET.get("count_submit"):
        resp = redirect("search_count")
        resp['Location'] += "%s" % qsify(request.GET)
        return resp
        """

    query = build_query(request.body)
    report = _search2(request, query)

    return HttpResponse("If all goes well, an email will be sent from 'ActionKit Reports' to %s shortly.  The subject of the email will be '%s' (sorry!)"  %(
            request.user.email, report[1]))

