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
import re
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase, TransactionTestCase, Client

from spyne.client.django import DjangoTestClient
from spyne.model.fault import Fault
from spyne.model.complex import ComplexModelBase
from spyne.util.django import (DjangoComplexModel, DjangoComplexModelMeta,
                               default_model_mapper, email_re)
from spyne.util.six import add_metaclass

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

    def test_cached_wsdl(self):
        """Test if wsdl is cached."""
        client = Client()
        response = client.get('/say_hello/')
        self.assertContains(response,
                            'location="http://testserver/say_hello/"')
        response = client.get('/say_hello/', HTTP_HOST='newtestserver')
        self.assertNotContains(response,
                            'location="http://newtestserver/say_hello/"')

    def test_not_cached_wsdl(self):
        """Test if wsdl is not cached."""
        client = Client()
        response = client.get('/say_hello_not_cached/')
        self.assertContains(
            response, 'location="http://testserver/say_hello_not_cached/"')
        response = client.get('/say_hello_not_cached/',
                              HTTP_HOST='newtestserver')

        self.assertContains(
            response, 'location="http://newtestserver/say_hello_not_cached/"')

class ModelTestCase(TestCase):

    """Test mapping between django and spyne models."""

    def setUp(self):
        self.client = DjangoTestClient('/api/', app)

    def test_exclude(self):
        """Test if excluded field is not mapped."""
        type_info = Container.get_flat_type_info(Container)
        self.assertIn('id', type_info)
        self.assertNotIn('excluded_field', type_info)

    def test_pk_mapping(self):
        """Test if primary key is mapped as optional but not nillable."""
        type_info = Container.get_flat_type_info(Container)
        pk_field = type_info['id']
        self.assertEqual(pk_field.Attributes.min_occurs, 0)
        self.assertFalse(pk_field.Attributes.nullable)

    def test_regex_pattern_mapping(self):
        """Test if regex pattern is mapped from django model."""
        type_info = Container.get_flat_type_info(Container)
        email_field = type_info['email_field']
        self.assertEqual(email_field.__name__, 'Unicode')
        self.assertIsNotNone(email_field.Attributes.pattern)
        self.assertEqual(email_field.Attributes.min_occurs, 1)
        self.assertFalse(email_field.Attributes.nullable)

    def test_blank_field(self):
        """Test if blank fields are optional but not null."""
        type_info = Container.get_flat_type_info(Container)
        blank_field = type_info['blank_field']
        self.assertEqual(blank_field.__name__, 'NormalizedString')
        self.assertEqual(blank_field.Attributes.min_occurs, 0)
        self.assertFalse(blank_field.Attributes.nullable)

    def test_blank_as_dict(self):
        """Test if blank field is omitted in as_dict representation."""
        container = Container()
        container_dict = container.as_dict()
        self.assertNotIn('blank_field', container_dict)

    def test_length_validators_field(self):
        """Test if length validators are correctly mapped."""
        type_info = Container.get_flat_type_info(Container)
        length_validators_field = type_info['length_validators_field']
        self.assertEqual(length_validators_field.__name__, 'NormalizedString')
        self.assertEqual(length_validators_field.Attributes.min_occurs, 1)
        self.assertTrue(length_validators_field.Attributes.nullable)
        self.assertEqual(length_validators_field.Attributes.min_len, 3)
        self.assertEqual(length_validators_field.Attributes.max_len, 10)

    def test_get_container(self):
        """Test mapping from Django model to spyne model."""
        get_container = lambda: self.client.service.get_container(2)
        self.assertRaises(Fault, get_container)
        container = FieldContainer.objects.create(slug_field='container')
        FieldContainer.objects.create(slug_field='container2',
                                      foreign_key=container,
                                      one_to_one_field=container,
                                      email_field='email@example.com',
                                      char_field='yo')
        c = get_container()
        self.assertIsInstance(c, Container)

    def test_create_container(self):
        """Test complex input to create Django model."""
        related_container = RelatedFieldContainer(id='related')
        new_container = FieldContainer(slug_field='container',
                                       date_field=datetime.date.today(),
                                       datetime_field=datetime.datetime.now(),
                                       email_field='email@example.com',
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
            email_field='email@example.com',
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

        self.assertEqual(
            UserProfile._type_info['user_id'].Attributes.min_occurs, 0)

    def test_abstract_custom_djangomodel(self):
        """Test if can create custom DjangoComplexModel."""
        @add_metaclass(DjangoComplexModelMeta)
        class OrderedDjangoComplexModel(ComplexModelBase):
            __abstract__ = True

            class Attributes(ComplexModelBase.Attributes):
                declare_order = 'declared'

        class OrderedFieldContainer(OrderedDjangoComplexModel):
            class Attributes(OrderedDjangoComplexModel.Attributes):
                django_model = FieldContainer

        field_container = OrderedFieldContainer()
        type_info_fields = field_container._type_info.keys()
        django_field_names = [field.get_attname() for field in
                              FieldContainer._meta.fields]
        # file field is not mapped
        django_field_names.remove('file_field')
        # check if ordering is the same as defined in Django model
        self.assertEqual(type_info_fields, django_field_names)

    def test_nonabstract_custom_djangomodel(self):
        """Test if can't create non abstract custom model."""
        try:
            @add_metaclass(DjangoComplexModelMeta)
            class CustomNotAbstractDjangoComplexModel(ComplexModelBase):

                class Attributes(ComplexModelBase.Attributes):
                    declare_order = 'declared'
        except ImproperlyConfigured:
            pass
        else:
            assert False, 'Can create non abstract custom model'


# in XmlSchema ^ and $ are set implicitly
python_email_re = '^' + email_re.pattern + '$'


class EmailRegexTestCase(TestCase):

    """Tests for email_re."""

    def test_empty(self):
        """Empty string is invalid email."""
        self.assertIsNone(re.match(python_email_re, ''))

    def test_valid(self):
        """Test valid email."""
        self.assertIsNotNone(re.match(python_email_re,
                                      'valid.email@example.com'))

    def test_valid_single_letter_domain(self):
        """Test valid email."""
        self.assertIsNotNone(re.match(python_email_re, 'valid.email@e.x.com'))

    def test_invalid(self):
        """Test invalid email."""
        self.assertIsNone(re.match(python_email_re, '@example.com'))

    def test_invalid_tld(self):
        """Test if email from Top Level Domain is invalid."""
        self.assertIsNone(re.match(python_email_re, 'babushka@email'))
        self.assertIsNone(re.match(python_email_re, 'babushka@domain.email-'))


class DjangoServiceTestCase(TestCase):

    """Tests for Django specific service."""

    def test_handle_does_not_exist(self):
        """Test if Django service handles `ObjectDoesNotExist` exceptions."""
        client = DjangoTestClient('/api/', app)
        with self.assertRaisesRegexp(Fault, 'Client.FieldContainerNotFound'):
            client.service.raise_does_not_exist()

    def test_handle_validation_error(self):
        """Test if Django service handles `ValidationError` exceptions."""
        client = DjangoTestClient('/api/', app)
        with self.assertRaisesRegexp(Fault, 'Client.ValidationError'):
            client.service.raise_validation_error()


class FromUnicodeAssertionTestCase(TestCase):

    def test_from_unicode_does_not_assert(self):
        client = Client()
        url = '/synchro/1/'
        msg = b"""<?xml version="1.0" encoding="UTF-8"?><SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/
            soap/envelope/"xmlns:ns1="tns" xmlns:ns0="http://schemas.xmlsoap.org/soap/envelope/" xmlns:xsi="
            http://www.w3.org/2001/XMLSchema-instance"><SOAP-ENV:Header/><ns0:Body><ns1:sync><ns1:model_id>TestModel
            </ns1:model_id><ns1:timestamp>2015-09-23T13:54:51.796366+00:00</ns1:timestamp><ns1:payload>
            </ns1:payload><ns1:partial/></ns1:sync></ns0:Body></SOAP-ENV:Envelope>"""
        hdrs = {'SOAPAction': b'"sync"', 'Content-Type': 'text/xml; charset=utf-8'}
        client.post(url, msg, 'text/xml', True, **hdrs)
