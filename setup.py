from setuptools import setup


setup(
    name='psmon',
    version='0.2.0',
    description='LCLS analysis monitoring',
    long_description='The psmom package is a remote data visualization tool used at LCLS for analysis monitoring',
    author='Daniel Damiani',
    author_email='ddamiani@slac.stanford.edu',
    url='https://confluence.slac.stanford.edu/display/PSDM/psana+-+Python+Script+Analysis+Manual#psana-PythonScriptAnalysisManual-Real-timeOnlinePlotting/Monitoring',
    package_dir={'psmon': 'src'},
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
        'Topic :: Scientific/Engineering :: Visualization',
        'Topic :: Utilities',
    ],
)
