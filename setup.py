from distutils.core import setup

setup(
    name='kb',
    version='1.0.0',
    packages=[''],
    url='',
    license='',
    author='vieglais',
    author_email='',
    description='Knowledge Base',
    entry_points = {
        'console_scripts': [
            'kb = kb:main',
            'ccouch = ccouch:main',
        ]
    }
)
