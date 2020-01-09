
.. _manual-django:

Django Integration
==================

This tutorial shows how to integrate Spyne into your Django project.

Imagine that you want to build TODO-list RPC service that exposes its API via
SOAP.  Here are our Django models from project/todo/models.py: ::

    """Models for todo app."""

    from django.db import models


    class TodoList(models.Model):

        """Represents TODO list."""

        name = models.CharField(max_length=100, unique=True)

        @property
        def entries(self):
            return self.todoentry_set.all()


    class TodoEntry(models.Model):

        """Represents TODO list entry."""

        todo_list = models.ForeignKey(TodoList)
        description = models.TextField()
        done = models.BooleanField(default=False)


Let's define `get_todo_list(list_name)` method for initial implementation of our API.

The method should get unique list name as argument and return information about
todo list like id, name and entries array.

We are going to implement our API in project/todo/todolists.py. Let's define
TodoList and TodoEntry types:

.. code-block:: python

    """API for TODO lists."""

    from spyne.util.django import DjangoComplexModel
    from project.todo.models import (TodoList as DjTodoList, TodoEntry as
                                     DjTodoEntry)


    class TodoEntry(DjangoComplexModel):

       """Todo list type for API."""

        class Attributes(DjangoComplexModel.Attributes):
            django_model = DjTodoEntry


    class TodoList(DjangoComplexModel):

        """Todo entry type for API."""

        entries = Array(CartItem).customize(nullable=True)

        class Attributes(DjangoComplexModel.Attributes):
            django_model = DjTodoList


:class:`DjangoComplexModel` creates mapper for us that maps
fields of corresponding Django models to fields of todo types. We decided to add
extra ``entries`` field so we can pass todo list with all its entries via API.
This field is nullable because empty todo list can be represented as null value.
The field is populated from ``DjTodoList.entries`` property that returns
entries queryset.

If you want to customize mapping between Django and Spyne models or you have
custom Django fields you can create own mapper and pass it as `django_mapper =
my_mapper` in ``Attributes``. See :class:`spyne.util.django.DjangoComplexModel` for
details.

Now we are going to define our RPC service: ::

    from spyne.decorator import rpc
    from spyne.error import ResourceNotFoundError
    from spyne.model import primitive
    from spyne.util.django import DjangoService


    class TodoService(DjangoService):

        """Todo list RPC service."""

        @rpc(primitive.String, _returns=TodoList)
        def get_todo_list(ctx, list_name):
            """Get todo list by unique name.

            :param list_name: string
            :returns: TodoList
            :raises:
                Client.TodoListNotFound fault when todo list with given name is not found

            """

            return DjTodoList.objects.get(name=list_name)

You may notice that we defined ``TodoList`` as return value of `get_todo_list` RPC
method but in fact ``DjTodoList`` instance is returned.  This trick works
because our Django models and Spyne types have common attribute interface.

Django specific `spyne.util.django` service captures `DjTodoList.DoesNotExist`
exception and transforms it to `Client.TodoListNotFound` fault.

By default Spyne creates types that are nullable and optional. Let's override
defaults and make our API more strict. We are going to define configuration
function in project/utils/spyne.py: ::

    def configure_spyne():
        """Set spyne defaults.

        Use monkey patching here.

        """
        import spyne.model
        attrs = spyne.model.ModelBase.Attributes
        attrs.NULLABLE_DEFAULT = False
        attrs.min_occurs = 1


Now we are all set to register our SOAP RPC API in Django urlconf. Let's edit
project/urls.py: ::

    from project.utils.spyne import configure_spyne
    configure_spyne()
    from spyne.application import Application
    from spyne.protocol.soap import Soap11
    from spyne.server.django import DjangoView as RPCView

    from project.todo.todolists import TodoService

    api = Application(services=[TodoService], tns='spyne.django.tutorial',
                      in_protocol=Soap11(validator='lxml'), out_protocol=Soap11())

    urlpatterns = patterns(
        '',
        url(r'^api/0.1/', RPCView.as_view(application=api), name='api'),
    )

First we configure spyne defaults. Then we create Spyne application that stores
configuration for our setup.  Finally we define view `api` bound to specific url.
``DjangoView.as_view`` created for us :class:`spyne.server.django.DjangoServer`
instance that will handle rpc requests.

Now we can run Django development server and look at WSDL that defines protocol
for our web service at `http://localhost:8000/api/0.1/`. Todo service client can
do POST requests to the same url.

We have done basic steps to build small RPC service and integrated it into
Django project.
