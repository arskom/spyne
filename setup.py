from setuptools import setup, find_packages
version = '0.7.2'

setup(name='soaplib',
      version=version,
      description="A simple library for writing soap web services",
      long_description="""\
      This is a simple, easily extendible soap library that provides several useful tools for 
      creating and publishing soap web services in python.  This package features on-demand
      wsdl generation for the published services, a wsgi-compliant web application, support for
      complex class structures, binary attachments, simple framework for creating additional
      serialization mechanisms and a client library.
      
      This is a fork of the original project that uses lxml as it's XML API.
      """,
      classifiers=[
      'Programming Language :: Python',
      'Operating System :: OS Independent',
      'Natural Language :: English',
      'Development Status :: 2 - Pre-Alpha',
      'Intended Audience :: Developers',
      'Topic :: Internet :: WWW/HTTP :: Dynamic Content'
      ],
      keywords='soap',
      author='Aaron Bickell',
      author_email='abickell@optio.com',
      url='http://trac.optio.webfactional.com',
      license='LGPL',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      zip_safe=False,
      install_requires=['pytz','cherrypy','lxml'],
	  test_suite='tests.test_suite',
      entry_points="""
      """,
      )
      
