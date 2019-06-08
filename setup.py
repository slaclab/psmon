import os
import re
from setuptools import setup


def get_version(pkg):
    """Scrap __version__  from __init__.py"""
    vfilename = os.path.join(os.getcwd(), pkg, '__init__.py')
    vfile = open(vfilename).read()
    m = re.search(r'__version__ = (\S+)\n', vfile)
    if m is None or len(m.groups()) != 1:
        raise Exception("Cannot determine __version__ from init file: '%s'!" % vfilename)
    version = m.group(1).strip('\'\"')
    return version


setup(
    name='psmon',
    version=get_version('psmon'),
    description='LCLS analysis monitoring',
    long_description='The psmom package is a remote data visualization tool used at LCLS for analysis monitoring',
    author='Daniel Damiani',
    author_email='ddamiani@slac.stanford.edu',
    url='https://confluence.slac.stanford.edu/display/PSDM/Visualization+Tools',
    packages=['psmon'],
    install_requires=[
        'numpy',
        'pyzmq',
        'pyqtgraph',
        'matplotlib',
        'ipython',
    ],
    entry_points={
        'console_scripts': [
            'psplot = psmon.client:main',
            'psconsole = psmon.console:main',
        ]
    },
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Other Environment',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: BSD License',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Topic :: Scientific/Engineering :: Visualization',
        'Topic :: Utilities',
    ],
)
