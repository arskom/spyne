From 1.0
========
- Hooks no longer get http environment parameter. You should remove that from your functions that override hook functions.

- Go to your source dirs and run the following commands, by replacing `.svn` with your preferred scm metadata dir:
      egrep -r 'soaplib.serializers' --exclude-dir=.svn . -l | xargs -n1 sed -i 's/soaplib.serializers/soaplib.type/g'
      egrep -r 'soaplib.wsgi' --exclude-dir=.svn . -l | xargs -n1 sed -i 's/soaplib.wsgi/soaplib.pattern.server.wsgi/g'

From 0.8
========

Please help the soaplib project by contributing this section.

