# encoding: utf-8

from setuptools import setup, find_packages

version = '0.2'

setup(
    name='ckanext-metadata',
    version=version,
    description='A metadata management framework for CKAN',
    url='https://github.com/SAEONData/ckanext-metadata',
    author='Mark Jacobson',
    author_email='mark@saeon.ac.za',
    license='MIT',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2.7',
    ],
    keywords='CKAN Metadata',
    packages=find_packages(exclude=['contrib', 'docs', 'tests*']),
    namespace_packages=['ckanext'],
    install_requires=[
        # CKAN extensions should list dependencies in requirements.txt, not here
    ],
    include_package_data=True,
    package_data={},
    entry_points='''
        [ckan.plugins]
        metadata = ckanext.metadata.plugin:MetadataFrameworkPlugin
        elastic = ckanext.metadata.elastic.plugin:ElasticPlugin

        [paste.paster_command]
        metadata = ckanext.metadata.command:MetadataFrameworkCommand

        [babel.extractors]
        ckan = ckan.lib.extract:extract_ckan
    ''',
    message_extractors={
        'ckanext': [
            ('**.py', 'python', None),
            ('**.js', 'javascript', None),
            ('**/templates/**.html', 'ckan', None),
        ],
    }
)
