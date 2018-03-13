# -*- coding: utf-8 -*-

from setuptools import setup, find_packages


def get_version_from_file():
    # get version number from __init__ file
    # before module is installed

    fname = 'asyncamqp/__init__.py'
    with open(fname) as f:
        fcontent = f.readlines()
    version_line = [l for l in fcontent if 'VERSION' in l][0]
    return version_line.split('=')[1].strip().strip("'").strip('"')


def get_long_description_from_file():
    # content of README will be the long description

    fname = 'README'
    with open(fname) as f:
        fcontent = f.read()
    return fcontent

VERSION = get_version_from_file()

DESCRIPTION = """
aioampq without callbacks!
""".strip()

LONG_DESCRIPTION = get_long_description_from_file()

setup(name='asyncamqp',
      version=VERSION,
      author='Juca Crispim',
      author_email='juca@poraodojuca.net',
      url='https://github.com/jucacrispim/asyncamqp',
      description=DESCRIPTION,
      long_description=LONG_DESCRIPTION,
      packages=find_packages(exclude=['tests', 'tests.*']),
      license='GPL',
      include_package_data=True,
      install_requires=['aioamqp'],
      # classifiers=[
      #     'Development Status :: 3 - Alpha',
      #     'Environment :: No Input/Output (Daemon)',
      #     'Environment :: Web Environment',
      #     'Intended Audience :: Developers',
      #     'License :: OSI Approved :: GNU General Public License (GPL)',
      #     'Natural Language :: English',
      #     'Operating System :: OS Independent',
      #     'Topic :: Software Development :: Build Tools',
      #     'Topic :: Software Development :: Testing',
      # ],
      # entry_points={
      #     'console_scripts': ['toxicbuild=toxicbuild.script:main',
      #                         'toxicmaster=toxicbuild.master:main',
      #                         'toxicslave=toxicbuild.slave:main',
      #                         'toxicweb=toxicbuild.ui:main']
      # },
      test_suite='tests',
      provides=['asyncamqp'],)
