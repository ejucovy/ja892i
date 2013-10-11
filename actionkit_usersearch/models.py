from django.db import models
from zope.dottedname.resolve import resolve

from actionkit_usersearch.columns import TYPE_CHOICES

class SearchColumn(models.Model):
    name = models.CharField(unique=True, max_length=50)
    display_name = models.CharField(max_length=100, null=True, blank=True)

    type = models.CharField(
        max_length=50,
        choices=[(i[0], i[1][0])
                 for i in 
                 TYPE_CHOICES.items()])
    parameters = models.TextField(null=True, blank=True)

    def load(self):
        return resolve(TYPE_CHOICES[self.type][1])(self)

