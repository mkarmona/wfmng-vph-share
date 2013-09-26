__author__ = 'Matteo Balasso <m.balasso@scsitaly.com>, Daniele Giunchi <d.giunchi@scsitaly.com>'
__copyright__= 'Copyright (C) 2012 SCS srl'
__credits__ = ['Matteo Balasso','Daniele Giunchi']

__classifiers__ = [
    'Development Status :: 4 - Beta',
    'Intended Audience :: Developers',
    'License :: BSD'
    'Operating System :: OS Independent',
    "Framework :: Flask",
    "Programming Language :: Python",
    "Topic :: Software Development :: Libraries :: Python Modules",
    ]

import os
here = os.path.dirname(__file__)
__version__ = open(os.path.join(here, 'version.txt'),'r').read()
__description__ = open(os.path.join(here, 'README.txt'),'r').read()

del os, here

__docformat__ = 'restructuredtext en'

__doc__ = """
:author: %s
:organization: SCS s.r.l.
:address: Via Parini 1, 40033 Casalecchio di Reno, Italy
:contact: http://www.scsitaly.com
:version: %s
:date: 2012-01
:copyright: %s
:abstract: %s
""" % (__author__, __version__,__copyright__,__description__)

from wfmng import *
