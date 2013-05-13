
About
=====

Spyne projects do not have to adhere to any specific file layout. However, the
file layout in this example project seems to be quite tidy and comfortable to
work with as most of the boilerplate for a propery Python project is already
here.

To start hacking on this project:

#. Copy the template directory to a different folder.

#. Do: ::

    find -name "*.py" | xargs sed -i s/template/your_project/g
    mv template your_project

#. Tweak the requirements in setup.py according to the protocols and transports
   you choose to work with. You can look at Spyne's own README to see which
   protocol or transport requires which package.

#. Tweak the database credentials and exception handling.

#. Hack away!

Installation
============

1. Bootstrap distribute if needed: ::

       wget http://python-distribute.org/distribute_setup.py

   (yes, wget, not ``curl | python`` because setup script tries to import it)

2. Run: ::

       python setup.py develop --user

   The template_daemon executable is now installed at $HOME/.local/bin. You
   may need to add that path to your $PATH.

Usage
=====

1. Run: ::

        template_deamon

2. In a separate console, run: ::

        curl "http://localhost:8000/put_user?user_user_name=jack&user_full_name=jack%20brown&user_email=jack@spyne.io"
        curl "http://localhost:8000/get_all_user"
