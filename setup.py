from setuptools import setup, find_packages
import sys, os

version = '0.1'

setup(name='actionkit-usersearch',
      version=version,
      description="",
      long_description="""\
""",
      classifiers=[],
      keywords='',
      author='Ethan Jucovy',
      author_email='ethan.jucovy@gmail.com',
      url='',
      license='BSD',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=False,
      install_requires=[
        "python-dateutils",
        "djangohelpers",
        "django-actionkit-client",
        "zope.dottedname",
      ],
      entry_points="""
[django.plugins]
actionkit_usersearch = actionkit_usersearch
      """,
      )
