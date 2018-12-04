# encoding: utf-8

from setuptools import setup, find_packages

version = '0.4.1'

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
        metadata_framework = ckanext.metadata.plugin:MetadataFrameworkPlugin
        metadata_infrastructure_ui = ckanext.metadata.plugin:InfrastructureUIPlugin
        metadata_elasticsearch = ckanext.metadata.elastic.plugin:ElasticSearchPlugin

        [paste.paster_command]
        metadata_framework = ckanext.metadata.command:MetadataFrameworkCommand

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
