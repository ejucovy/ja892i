from actionkit import rest
from actionkit.models import *
from collections import namedtuple
import datetime
import dateutil.parser
from django.http import QueryDict
from django.template.defaultfilters import slugify
import hashlib
import re

from actionkit_usersearch.models import SearchColumn
from actionkit_usersearch import sql

def make_default_user_query(users, query_data, values, search_on, extra_data={}):
    """
    given a query_data dict and values which come from the ui,
    generate a dict that will be used for a user query

    this default query is a within query, that optionally adds some
    extra key/value data to the query dict
    """

    query = {}

    query_str = query_data['query']
    within = query_str + '__in'
    query[within] = values

    extra_info = query_data.get('extra')
    if extra_info:
        query.update(extra_info)


    if extra_data.get('istoggle', True):
        users = users.filter(**query)
        human_query = u"%s is in (%s)" % (search_on, u', '.join(values))
    else:
        users = users.exclude(**query)
        human_query = u"%s is not in (%s)" % (search_on, u', '.join(values))
    return users, human_query

def make_date_query(users, query_data, values, search_on, extra_data={}):
    date = values[0]
    match = dateutil.parser.parse(date)
    if extra_data.get('istoggle', True):
        users = users.filter(**{query_data['query']: match})
        human_query = "%s is in %s" % (search_on, values)
    else:
        users = users.exclude(**{query_data['query']: match})
        human_query = "%s is not in %s" % (search_on, values)
    return users, human_query

def make_zip_radius_query(users, query_data, values, search_on, extra_data={}):
    zipcode = values[0]
    if 'distance' in extra_data:
        distance = extra_data['distance']
        distance = float(distance)
        assert distance > 0, "Bad distance"
        latlon = zipcode_to_latlon(zipcode)
        assert latlon is not None, "No location found for: %s" % zipcode
        lat, lon = latlon
        bbox = latlon_bbox(lat, lon, distance)
        assert bbox is not None, "Bad bounding box for latlon: %s,%s" % (lat, lon)
        lat1, lat2, lon1, lon2 = bbox
        if extra_data.get('istoggle', True):
            users = users.filter(location__latitude__range=(lat1, lat2),
                                 location__longitude__range=(lon1, lon2))
            human_query = "within %s miles of %s" % (distance, zipcode)
        else:
            users = users.exclude(location__latitude__range=(lat1, lat2),
                                  location__longitude__range=(lon1, lon2))
            human_query = "not within %s miles of %s" % (distance, zipcode)
    else:
        if extra_data.get('istoggle', True):
            users = users.filter(zip=zipcode)
            human_query = "in zip code %s" % zipcode
        else:
            users = users.exclude(zip=zipcode)
            human_query = "not in zip code %s" % zipcode
    return users, human_query


def make_contact_since_query(users, query_data, values, search_on, extra_data={}):
    contacted_since = values[0]
    match = dateutil.parser.parse(contacted_since)
    search = ContactRecord.objects.filter(completed_at__gt=match)
    human_query = ["contacted since %s" % contacted_since]
    if 'contacted_by' in extra_data:
        contacted_by = extra_data['contacted_by']
        search = search.filter(user__username=contacted_by)
        human_query.append("by %s" % contacted_by)
    akids = list(search.values_list("akid", flat=True))
    if len(akids) == 0:
        ## TODO give a helpful error message, not a mysterious always-null query
        akids = [0]
    if extra_data.get('istoggle', True):
        users = users.filter(id__in=akids)
        human_query = " ".join(human_query)
    else:
        users = users.exclude(id__in=akids)
        human_query = 'not %s' % (" ".join(human_query))
    return users, human_query


def make_contact_by_query(users, query_data, values, search_on, extra_data={}):
    contacted_by = values[0]
    search = ContactRecord.objects.filter(user__username=contacted_by)
    human_query = ["contacted by %s" % contacted_by]
    if 'contacted_since' in extra_data:
        contacted_since = extra_data['contacted_since']
        match = dateutil.parser.parse(contacted_since)
        search = search.filter(completed_at__gt=match)
        human_query.append("since %s" % contacted_since)
    akids = list(search.values_list("akid", flat=True))
    if len(akids) == 0:
        ## TODO give a helpful error message, not a mysterious always-null query
        akids = [0]
    if extra_data.get('istoggle', True):
        users = users.filter(id__in=akids)
        human_query = " ".join(human_query)
    else:
        users = users.exclude(id__in=akids)
        human_query = 'not %s' % (" ".join(human_query))
    return users, human_query

def make_emails_opened_query(users, query_data, values, search_on, extra_data={}):
    num_opens = values[0]
    num_opens = int(num_opens)
    human_query = "opened at least %s emails" % num_opens
    if 'since' in extra_data:
        since = dateutil.parser.parse(extra_data['since'])
        users = users.filter(email_opens__created_at__gte=since)
        human_query += " since %s" % since
    users = users.annotate(num_opens=Count('email_opens', distinct=True))
    if extra_data.get('istoggle', True):
        users = users.filter(num_opens__gte=num_opens)
    else:
        users = users.exclude(num_opens__gte=num_opens)
        human_query = 'not %s' % human_query
    return users, human_query


def make_more_actions_since_query(users, query_data, values, search_on, extra_data={}):
    num_actions = values[0]
    num_actions = int(num_actions)
    human_query = 'more than %s actions' % num_actions
    if 'since' in extra_data:
        since = dateutil.parser.parse(extra_data['since'])
        users = users.filter(actions__created_at__gte=since)
        human_query += ' since %s' % extra_data['since']
    users = users.annotate(num_actions=Count('actions', distinct=True))
    if extra_data.get('istoggle', True):
        users = users.filter(num_actions__gt=num_actions)
    else:
        users = users.exclude(num_actions__gt=num_actions)
        human_query = 'not %s' % human_query
    return users, human_query


def make_donated_more_than_query(users, query_data, values, search_on, extra_data={}):
    if extra_data.get('istoggle', True):
        human_query = 'has donated more than %s' % values[0]
    else:
        human_query = 'has not donated more than %s' % values[0]
    total_donated = float(values[0])
    if 'since' in extra_data:
        since = dateutil.parser.parse(extra_data['since'])
        users = users.filter(orders__created_at__gte=since)
        human_query += ' since %s' % extra_data['since']
    users = users.filter(orders__status='completed')
    users = users.annotate(total_orders=Sum('orders__total'))
    if extra_data.get('istoggle', True):
        users = users.filter(total_orders__gte=total_donated)
    else:
        users = users.exclude(total_orders__gte=total_donated)
    return users, human_query


def make_donated_times_query(users, query_data, values, search_on, extra_data={}):
    if extra_data.get('istoggle', True):
        human_query = 'has donated more than %s times' % values[0]
    else:
        human_query = 'has not donated more than %s times' % values[0]
    times_donated = int(values[0])
    if 'since' in extra_data:
        since = dateutil.parser.parse(extra_data['since'])
        users = users.filter(orders__created_at__gte=since)
        human_query += ' since %s' % extra_data['since']
    users = users.filter(orders__status='completed')
    users = users.annotate(n_orders=Count('orders', distinct=True))
    if extra_data.get('istoggle', True):
        users = users.filter(n_orders__gte=times_donated)
    else:
        users = users.exclude(n_orders__gte=times_donated)
    return users, human_query


QUERIES = {
    'country': {
        'query': "country",
        },
    'region': {
        'query': "region",
        },
    'state': {
        'query': "state",
        },
    'city': {
        'query': "city",
        },
    'action': {
        'query': "actions__page__id",
        },
    'source': {
        'query': "source",
        },
    'tag': {
        'query': "actions__page__pagetags__tag__id",
        },
    'campus': {
        'query': "fields__value",
        'extra': {"fields__name": "campus"},
        },
    'skills': {
        'query': "fields__value",
        'extra': {"fields__name": "skills"},
        },
    'engagement_level': {
        'query': "fields__value",
        'extra': {"fields__name": "engagement_level"},
        },
    'student': {
        'query': "fields__value",
        'extra': {"fields__name": "student"},
        },
    'affiliation': {
        'query': "fields__value",
        'extra': {"fields__name": "affiliation"},
        },
    'language': {
        'query': "lang__id",
        },
    'created_before': {
        'query': "created_at__lte",
        'query_fn': make_date_query,
        },
    'created_after': {
        'query': "created_at__gte",
        'query_fn': make_date_query,
        },
    'zipcode': {
        'query_fn': make_zip_radius_query,
        },
    'contacted_since': {
        'query_fn': make_contact_since_query,
        },
    'contacted_by': {
        'query_fn': make_contact_by_query,
        },
    'emails_opened': {
        'query_fn': make_emails_opened_query,
        },
    'more_actions': {
        'query_fn': make_more_actions_since_query,
        },
    'donated_more': {
        'query_fn': make_donated_more_than_query,
        },
    'donated_times': {
        'query_fn': make_donated_times_query,
        },
    }

Query = namedtuple("Query", "human_query query_string raw_sql report_data")

def build_query(querystring, queryset_modifier_fn=None):
    query_params = QueryDict(querystring)

    base_user_query = CoreUser.objects.using("ak").order_by("id")
    
    includes = []

    include_pattern = re.compile("^include:\d+$")
    for key in query_params.keys():
        if (include_pattern.match(key)
            and query_params[key]
            and (not query_params[key].endswith('_istoggle'))):
            includes.append((key, query_params.getlist(key)))

    human_query = []

    all_user_queries = []
    for include_group in includes:
        users = base_user_query
        _human_query = []
        for item in include_group[1]:
            ## "distance" is handled in a group with "zipcode", so we ignore it here
            if item == "zipcode__distance":
                continue
            ## same for "contacted_by", in a group with "contacted_since"
            if item == "contacted_since__contacted_by":
                continue
            if item == "contacted_by__contacted_since":
                continue
            ## ditto
            if item == 'more_actions__since':
                continue

            possible_values = query_params.getlist(
                "%s_%s" % (include_group[0], item))
            if len(possible_values) == 0:
                continue
            query_data = QUERIES[item]
            extra_data = {}

            istogglename = '%s_%s_istoggle' % (include_group[0], item)
            istoggle = query_params.get(istogglename, '1')
            try:
                istoggle = bool(int(istoggle))
            except ValueError:
                istoggle = True
            extra_data['istoggle'] = istoggle

            ## XXX special cased zip code and distance
            # these two fields are together, if we have another case like this
            # we should probably formalize this
            if item == "zipcode":
                distance = query_params.get('%s_zipcode__distance' % include_group[0])
                if distance:
                    extra_data['distance'] = distance

            ## XXX special cased contacted_since and contacted_by
            # these two fields are together, if we have another case like this
            # we should probably formalize this
            if item == "contacted_since":
                contacted_by = query_params.get(
                    '%s_contacted_since__contacted_by' % include_group[0])
                if contacted_by:
                    extra_data['contacted_by'] = contacted_by

            if item == "contacted_by":
                contacted_since = query_params.get(
                    '%s_contacted_by__contacted_since' % include_group[0])
                if contacted_since:
                    extra_data['contacted_since'] = contacted_since

            if item == "emails_opened":
                since = query_params.get('%s_emails_opened__since' % include_group[0])
                if since:
                    extra_data['since'] = since
            if item == "more_actions":
                since = query_params.get('%s_more_actions__since' % include_group[0])
                if since:
                    extra_data['since'] = since
            if item == "donated_more":
                since = query_params.get('%s_donated_more__since' % include_group[0])
                if since:
                    extra_data['since'] = since
            if item == "donated_times":
                since = query_params.get('%s_donated_times__since' % include_group[0])
                if since:
                    extra_data['since'] = since

            make_query_fn = query_data.get('query_fn', make_default_user_query)
            users, __human_query = make_query_fn(
                users, query_data, possible_values, item, extra_data)
            _human_query.append(__human_query)

        if not _human_query or (
            users.query.sql_with_params() == base_user_query.query.sql_with_params()):
            continue

        all_user_queries.append(users)
        human_query.append("(%s)" % " and ".join(_human_query))

    human_query = "\n or ".join(human_query)
    users = None
    for i, query in enumerate(all_user_queries):
        if i == 0:
            users = query
        else:
            users = users | query
    if users is None:
        users = base_user_query

    ### If both of user_name and user_email are filled out,
    ### search for anyone who matches EITHER condition, rather than both.
    extra_where = []
    extra_params = []
    if query_params.get("user_name"):
        extra_where.append(
            "CONCAT(`core_user`.`first_name`, ' ', `core_user`.`last_name`) LIKE %s")
        extra_params.append("%" + "%".join(query_params['user_name'].split()) + "%")
        human_query += "\n and name is like \"%s\"" % query_params['user_name']
    if query_params.get("user_email"):
        extra_where.append("`core_user`.`email` LIKE %s")
        extra_params.append("%" + query_params.get("user_email") + "%")
        human_query += "\n and email is like \"%s\"" % query_params['user_email']
    if query_params.get("user_akid"):
        akids = [int(i.strip()) for i in query_params["user_akid"].split(",")]
        for akid in akids:
            extra_where.append("`core_user`.`id` = %s")
            extra_params.append(akid)
        human_query += "\n and AKID is in %s" % akids
    if len(extra_where):
        if len(extra_where) == 2:
            extra_where = ["(%s OR %s)" % tuple(extra_where)]
        users = users.extra(
            where=extra_where,
            params=extra_params)

    users = users.extra(select={'phone': (
                "SELECT `normalized_phone` FROM `core_phone` "
                "WHERE `core_phone`.`user_id`=`core_user`.`id` "
                "LIMIT 1"),
                                'name': (
                "CONCAT(CONCAT(first_name, \" \"), last_name)"),
                                'campus': (
                "SELECT `value` from `core_userfield` "
                "WHERE`core_userfield`.`parent_id`=`core_user`.`id` "
                'AND `core_userfield`.`name`="campus" LIMIT 1'),
                                'skills': (
                "SELECT `value` from `core_userfield` "
                "WHERE`core_userfield`.`parent_id`=`core_user`.`id` "
                'AND `core_userfield`.`name`="skills" LIMIT 1'),
                                'engagement_level': (
                "SELECT `value` from `core_userfield` "
                "WHERE`core_userfield`.`parent_id`=`core_user`.`id` "
                'AND `core_userfield`.`name`="engagement_level" LIMIT 1'),
                                'affiliation': (
                "SELECT `value` from `core_userfield` "
                "WHERE`core_userfield`.`parent_id`=`core_user`.`id` "
                'AND `core_userfield`.`name`="affiliation" LIMIT 1'),
                                })

    columns = SearchColumn.objects.filter(name__in=query_params.getlist("column"))
    for column in columns:
        users = column.load()(users)

    if users.query.sql_with_params() == base_user_query.query.sql_with_params():
        users = base_user_query.none()

    if queryset_modifier_fn is not None:
        users = queryset_modifier_fn(users)

    if not query_params.get('subscription_all_users', False):
        users = users.filter(subscription_status='subscribed')
        human_query += "\n and subscription_status is 'subscribed'"

    users = users.distinct()
    raw_sql = sql.raw_sql_from_queryset(users)

    del users

    return Query(human_query, querystring, raw_sql, None)

def _search2(request, query):
    querystring = query.query_string
    query_params = QueryDict(querystring)

    slug = hashlib.sha1(
        query.raw_sql + datetime.datetime.now().utcnow().isoformat()).hexdigest()
    slug = slugify(slug)

    ## Create a new report
    ## (https://roboticdogs.actionkit.com/docs/manual/api/rest/reports.html#creating-reports)
    ## using the raw sql
    resp = rest.create_report(query.raw_sql, query.human_query, slug, slug)

    report_id = resp['id']
    shortname = resp['short_name']

    ## and then trigger an asynchronous run of that report
    ## (https://roboticdogs.actionkit.com/docs/manual/api/rest/reports.html#running-reports-asynchronously)
    task_id = rest.run_report(shortname, email_to=request.user.email,
                              data=query.report_data)

    return report_id, shortname, task_id
