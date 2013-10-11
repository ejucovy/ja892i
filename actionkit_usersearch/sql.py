from django.db import connections

def raw_sql_from_queryset(queryset):
    dummy_queryset = queryset.using('dummy')
    # @@TODO: this is necessary for some reason.
    dummy_queryset.query.group_by = None
    try:
        # trigger the query
        list(dummy_queryset)
    except Exception, e:
        queries = connections['dummy'].queries
        actual_sql = queries[-1]['sql']        
        return actual_sql.replace("-9999", "{{ user_ids }}")
    else:
        #sql, params = dummy_queryset.query.sql_with_params()
        #db = connections['dummy'].cursor()
        #import pdb; pdb.set_trace()
        assert False, "Dummy query was expected to fail"
