This is an example for using Flask and Spyne together. It is very simple,
and does nothing useful.

Create virtualenv and install requirements: ::

    pip install Flask
    pip install -e . # install Spyne from working directory

Run Flask web server: ::

    ./examples/flask/manage.py

Try Flask views to make sure it works: ::

    curl -s http://127.0.0.1:5000/hello | python -m json.tool

Here is a Spyne views call example: ::

    curl -s http://localhost:5000/soap/hello?name=Anton\&times=3 | python -m json.tool

The same view call, but without explicit name argument, to read default from
Flask config: ::

    curl -s http://localhost:5000/soap/hello?times=3 | python -m json.tool
