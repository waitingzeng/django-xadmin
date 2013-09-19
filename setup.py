#!/usr/bin/env python
from setuptools import setup, find_packages

# version_tuple = __import__('xadmin.version').VERSION
# version = ".".join([str(v) for v in version_tuple])

setup(
    name='django-xadmin',
    version='0.4.0',
    description='Drop-in replacement of Django admin comes with lots of goodies, fully extensible with plugin support, pretty UI based on Twitter Bootstrap.',
    long_description=open('README.rst').read(),
    author='waitingzeng',
    author_email='ttwait@gmail.com',
    url='http://www.xadmin.io',
    download_url='https://github.com/waitingzeng/django-xadmin/archive/master.zip',
    packages=['xadmin', 'xadmin.plugins', 'xadmin.templatetags', 'xadmin.views'],
    include_package_data=True,
    install_requires=[
        'setuptools',
        'xlwt',
        'django-crispy-forms>=1.2.3',
        'django-reversion',
    ],
    extras_require={
        'Excel': ['xlwt'],
        'Reversion': ['django-reversion'],
    },
    zip_safe=True,
    keywords=['admin', 'django', 'xadmin', 'bootstrap'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        "Programming Language :: JavaScript",
        'Programming Language :: Python',
        "Programming Language :: Python :: 2.7",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ]
)
