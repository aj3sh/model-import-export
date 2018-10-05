import os
import sys
import setuptools

with open("README.md", "r") as fh:
	long_description = fh.read()


if sys.argv[-1] == 'publish':
	if os.system("pip freeze | grep twine"):
		print("twine not installed.\nUse `pip install twine`.\nExiting.")
		sys.exit()
	os.system("python3 setup.py sdist bdist_wheel")
	os.system("twine upload dist/*")
	sys.exit()


setuptools.setup(
	name="model_import_export",
	version="0.1.0",
	author="Ajesh Sen Thapa",
	author_email="aj3sshh@gmail.com",
	description="Import/Export feature for django models",
	long_description=long_description,
	long_description_content_type="text/markdown",
	url="https://github.com/aj3sh/model_import_export",
	packages=setuptools.find_packages(),
	install_requires=[

		'numpy==1.15.2',
		'openpyxl==2.5.8',
		'pandas==0.23.4',
		'xlrd==1.1.0',
		'xlwt==1.3.0',
	
	],
	classifiers=[

		'Environment :: Web Environment',
		'Framework :: Django',
		'Framework :: Django :: 1.11',
		'Framework :: Django :: 2.0',
		'Framework :: Django :: 2.1',
		'Programming Language :: Python :: 3',
		'License :: OSI Approved :: MIT License',
		'Operating System :: OS Independent',
	
	],
)