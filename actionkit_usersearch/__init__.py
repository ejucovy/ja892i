INSTALLED_APPS = [
    'actionkit_usersearch',
    ]

URLCONFS = [
    ("^user/search/", "actionkit_usersearch.urls"),
    ]

import dj_database_url
import os
DATABASES = {
    'dummy': dj_database_url.parse(os.environ['ACTIONKIT_DUMMY_DATABASE_URL'])
    }
