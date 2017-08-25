try:
	from setuptools import setup
except ImportError:
	from distutils.core import setup

config = {
	'name': 'FitBit Data Generator',
	'version': '0.1',
	'url': 'https://github.com/parnellj/fitbit_generator',
	'download_url': 'https://github.com/parnellj/fitbit_generator',
	'author': 'Justin Parnell',
	'author_email': 'parnell.justin@gmail.com',
	'maintainer': 'Justin Parnell',
	'maintainer_email': 'parnell.justin@gmail.com',
	'classifiers': [],
	'license': 'GNU GPL v3.0',
	'description': 'Retrieves and reshapes FitBit exercise monitor data via the FitBit API.',
	'long_description': 'Retrieves and reshapes FitBit exercise monitor data via the FitBit API.',
	'keywords': '',
	'install_requires': ['nose'],
	'packages': ['fitbit_generator'],
	'scripts': []
}
	
setup(**config)
