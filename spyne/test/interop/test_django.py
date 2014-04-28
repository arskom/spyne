# coding: utf-8
#!/usr/bin/env python
#
# spyne - Copyright (C) Spyne contributors.
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301
#


from __future__ import absolute_import

import datetime
from django.test import TestCase, TransactionTestCase, Client

from spyne.client.django import DjangoTestClient
from spyne.model.fault import Fault
from spyne.util.django import DjangoComplexModel

from rpctest.core.models import (FieldContainer, RelatedFieldContainer,
                                 UserProfile as DjUserProfile)
from rpctest.core.views import app, hello_world_service, Container


class SpyneTestCase(TransactionTestCase):
    def setUp(self):
        self.client = DjangoTestClient('/hello_world/', hello_world_service.app)

    def _test_say_hello(self):
        resp =  self.client.service.say_hello('Joe',5)
        list_resp = list(resp)
        self.assertEqual(len(list_resp), 5)
        self.assertEqual(list_resp,['Hello, Joe']*5)


class DjangoViewTestCase(TestCase):
    def test_say_hello(self):
        client = DjangoTestClient('/say_hello/', app)
        resp =  client.service.say_hello('Joe', 5)
        list_resp = list(resp)
        self.assertEqual(len(list_resp), 5)
        self.assertEqual(list_resp, ['Hello, Joe'] * 5)

    def test_response_encoding(self):
        client = DjangoTestClient('/say_hello/', app)
        response = client.service.say_hello.get_django_response('Joe', 5)
        self.assertTrue('Content-Type' in response)
        self.assertTrue(response['Content-Type'].startswith('text/xml'))

    def test_error(self):
        client = Client()
        response = client.post('/say_hello/', {})
        self.assertContains(response, 'faultstring', status_code=500)

    def test_wsdl(self):
        client = Client()
        response = client.get('/say_hello/')
        self.assertContains(response,
                            'location="http://testserver/say_hello/"')


class ModelTestCase(TestCase):

    """Test mapping between django and spyne models."""

    def setUp(self):
        self.client = DjangoTestClient('/api/', app)

    def test_exclude(self):
        """Test if excluded field is not mapped."""
        type_info = Container.get_flat_type_info(Container)
        self.assertIn('id', type_info)
        self.assertNotIn('excluded_field', type_info)

    def test_get_container(self):
        """Test mapping from Django model to spyne model."""
        get_container = lambda: self.client.service.get_container(2)
        self.assertRaises(Fault, get_container)
        container = FieldContainer.objects.create(slug_field='container')
        FieldContainer.objects.create(slug_field='container2',
                                      foreign_key=container,
                                      one_to_one_field=container,
                                      char_field='yo')
        c = get_container()
        self.assertIsInstance(c, Container)

    def test_create_container(self):
        """Test complex input to create Django model."""
        related_container = RelatedFieldContainer(id='related')
        new_container = FieldContainer(slug_field='container',
                                       date_field=datetime.date.today(),
                                       datetime_field=datetime.datetime.now(),
                                       time_field=datetime.time(),
                                       custom_foreign_key=related_container,
                                       custom_one_to_one_field=related_container)
        create_container = (lambda: self.client.service.create_container(
            new_container))
        c = create_container()

        self.assertIsInstance(c, Container)
        self.assertEqual(c.custom_one_to_one_field_id, 'related')
        self.assertEqual(c.custom_foreign_key_id, 'related')
        self.assertRaises(Fault, create_container)

    def test_create_container_unicode(self):
        """Test complex unicode input to create Django model."""
        new_container = FieldContainer(
            char_field=u'спайн',
            text_field=u'спайн',
            slug_field='spyne',
            date_field=datetime.date.today(),
            datetime_field=datetime.datetime.now(),
            time_field=datetime.time()
        )
        create_container = (lambda: self.client.service.create_container(
            new_container))
        c = create_container()
        self.assertIsInstance(c, Container)
        self.assertRaises(Fault, create_container)

    def test_optional_relation_fields(self):
        """Test if optional_relations flag makes fields optional."""
        class UserProfile(DjangoComplexModel):
            class Attributes(DjangoComplexModel.Attributes):
                django_model = DjUserProfile

        self.assertFalse(UserProfile._type_info['user_id'].Attributes.nullable)

        class UserProfile(DjangoComplexModel):
            class Attributes(DjangoComplexModel.Attributes):
                django_model = DjUserProfile
                django_optional_relations = True

        self.assertTrue(UserProfile._type_info['user_id'].Attributes.nullable)
