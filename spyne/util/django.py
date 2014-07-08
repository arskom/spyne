# encoding: utf-8
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

"""Support for Django model <-> spyne type mapping.

This module is EXPERIMENTAL. Tests and patches are welcome.

"""

from __future__ import absolute_import

import logging
logger = logging.getLogger(__name__)

import re
from django.core.exceptions import ImproperlyConfigured
from django.core.validators import slug_re, comma_separated_int_list_re
from spyne.model.complex import ComplexModelMeta, ComplexModelBase
from spyne.model import primitive
from spyne.util.odict import odict
from spyne.util.six import add_metaclass


# regex is based on http://www.w3.org/TR/xforms20/#xforms:email
email_re = re.compile(
    r"[A-Za-z0-9!#-'\*\+\-/=\?\^_`\{-~]+"
    r"(\.[A-Za-z0-9!#-'\*\+\-/=\?\^_`\{-~]+)*@"
    r"[A-Za-z0-9!#-'\*\+\-/=\?\^_`\{-~]+"
    r"(\.[A-Za-z0-9!#-'\*\+\-/=\?\^_`\{-~]+)*", re.IGNORECASE)


class BaseDjangoFieldMapper(object):

    """Abstrace base class for field mappers."""

    @staticmethod
    def is_field_nullable(field, **kwargs):
        """Return True if django field is nullable."""
        return field.null

    def map(self, field, **kwargs):
        """Map field to spyne model.

        :param field: Django Field instance
        :param kwargs: Extra params to configure spyne model
        :returns: tuple (field attribute name, mapped spyne model)

        """
        params = kwargs.copy()

        if field.max_length:
            params['max_len'] = field.max_length

        nullable = self.is_field_nullable(field, **kwargs)
        required = not (field.has_default() or nullable or field.primary_key)

        if field.has_default():
            params['default'] = field.get_default()

        spyne_model = self.get_spyne_model(field, **kwargs)
        customized_model = spyne_model(nullable=nullable,
                                       min_occurs=int(required), **params)

        return (field.attname, customized_model)

    def get_spyne_model(self, field, **kwargs):
        """Return spyne model for given Django field."""
        raise NotImplementedError


class DjangoFieldMapper(BaseDjangoFieldMapper):

    """Basic mapper for django fields."""

    def __init__(self, spyne_model):
        """Django field mapper constructor."""
        self.spyne_model = spyne_model

    def get_spyne_model(self, field, **kwargs):
        """Return configured spyne model."""
        return self.spyne_model


class DecimalMapper(DjangoFieldMapper):

    """Mapper for DecimalField."""

    def map(self, field, **kwargs):
        """Map DecimalField to spyne model.

        :returns: tuple (field attribute name, mapped spyne model)

        """
        params = kwargs.copy()
        params.update({
            'total_digits': field.max_digits,
            'fraction_digits': field.decimal_places,
        })
        return super(DecimalMapper, self).map(field, **params)


class RelationMapper(BaseDjangoFieldMapper):

    """Mapper for relation fields (ForeignKey, OneToOneField)."""

    def __init__(self, django_model_mapper):
        """Constructor for relation field mapper."""
        self.django_model_mapper = django_model_mapper

    @staticmethod
    def is_field_nullable(field, **kwargs):
        """Return True if `optional_relations` is set.

        Otherwise use basic behaviour.

        """
        optional_relations = kwargs.get('optional_relations', False)
        return (optional_relations or
                BaseDjangoFieldMapper.is_field_nullable(field, **kwargs))

    def get_spyne_model(self, field, **kwargs):
        """Return spyne model configured by related field."""
        related_field = field.rel.get_related_field()
        field_type = related_field.__class__.__name__
        field_mapper = self.django_model_mapper.get_field_mapper(field_type)

        _, related_spyne_model = field_mapper.map(related_field, **kwargs)
        return related_spyne_model


class DjangoModelMapper(object):

    r"""Mapper from django models to spyne complex models.

    You can extend it registering new field types: ::

        class NullBooleanMapper(DjangoFieldMapper):

            def map(self, field, **kwargs):
                params = kwargs.copy()
                # your mapping logic goes here
                return super(NullBooleanMapper, self).map(field, **params)

        default_model_mapper.register_field_mapper('NullBooleanField', \
                NullBooleanMapper(primitive.Boolean))


    You may subclass it if you want different mapping logic for different
    Django models.

    """

    field_mapper_class = DjangoFieldMapper

    class UnknownFieldMapperException(Exception):

        """Raises when there is no field mapper for given django_type."""

    def __init__(self, django_spyne_models=()):
        """Register field mappers in internal registry."""
        self._registry = {}

        for django_type, spyne_model in django_spyne_models:
            self.register(django_type, spyne_model)

    def get_field_mapper(self, django_type):
        """Get mapper registered for given django_type.

        :param django_type: Django internal field type
        :returns: registered mapper
        :raises: :exc:`UnknownFieldMapperException`

        """
        try:
            return self._registry[django_type]
        except KeyError:
            raise self.UnknownFieldMapperException(
                'No mapper for field type {0}'.format(django_type))

    def register(self, django_type, spyne_model):
        """Register default field mapper for django_type and spyne_model.

        :param django_type: Django internal field type
        :param spyne_model: Spyne model, usually primitive

        """
        field_mapper = self.field_mapper_class(spyne_model)
        self.register_field_mapper(django_type, field_mapper)

    def register_field_mapper(self, django_type, field_mapper):
        """Register field mapper for django_type.

        :param django_type: Django internal field type
        :param field_mapper: :class:`DjangoFieldMapper` instance

        """
        self._registry[django_type] = field_mapper

    @staticmethod
    def _get_fields(django_model, exclude=None):
        field_names = set(exclude) if exclude is not None else set()
        meta = django_model._meta  # pylint: disable=W0212
        unknown_fields_names = field_names.difference(
            meta.get_all_field_names())

        if unknown_fields_names:
            raise ImproperlyConfigured(
                'Unknown field names: {0}'
                .format(', '.join(unknown_fields_names)))

        return [field for field in meta.fields if field.name not in
                field_names]

    def map(self, django_model, exclude=None, **kwargs):
        """Prepare dict of model fields mapped to spyne models.

        :param django_model: Django model class.
        :param exclude: list of fields excluded from mapping.
        :param kwargs: extra kwargs are passed to all field mappers

        :returns: dict mapping attribute names to spyne models
        :raises: :exc:`UnknownFieldMapperException`

        """
        field_map = odict()

        for field in self._get_fields(django_model, exclude):
            field_type = field.__class__.__name__

            try:
                field_mapper = self._registry[field_type]
            except KeyError:
                # mapper for this field is not registered
                if not (field.has_default() or field.null):
                    # field is required
                    raise self.UnknownFieldMapperException(
                        'No mapper for field type {0}'.format(field_type))
                else:
                    # skip this field
                    logger.info('Field {0} is skipped from mapping.')
                    continue

            attr_name, spyne_model = field_mapper.map(field, **kwargs)
            field_map[attr_name] = spyne_model

        return field_map


def strip_regex_metachars(pattern):
    """Strip ^ and $ from pattern begining and end.

    According to http://www.w3.org/TR/xmlschema-0/#regexAppendix XMLSchema
    expression language does not contain the metacharacters ^ and $.

    :returns: stripped pattern string

    """
    start = 0
    till = len(pattern)

    if pattern.startswith('^'):
        start = 1

    if pattern.endswith('$'):
        till -= 1

    return pattern[start:till]


DEFAULT_FIELD_MAP = (
    ('AutoField', primitive.Integer32),
    ('CharField', primitive.NormalizedString),
    ('SlugField', primitive.Unicode(
        type_name='Slug', pattern=strip_regex_metachars(slug_re.pattern))),
    ('TextField', primitive.Unicode),
    ('EmailField', primitive.Unicode(
        type_name='Email', pattern=strip_regex_metachars(email_re.pattern))),
    ('CommaSeparatedIntegerField', primitive.Unicode(
        type_name='CommaSeparatedField',
        pattern=strip_regex_metachars(comma_separated_int_list_re.pattern))),
    ('URLField', primitive.AnyUri),
    ('FilePathField', primitive.Unicode),

    ('BooleanField', primitive.Boolean),
    ('NullBooleanField', primitive.Boolean),
    ('IntegerField', primitive.Integer),
    ('BigIntegerField', primitive.Integer64),
    ('PositiveIntegerField', primitive.UnsignedInteger32),
    ('SmallIntegerField', primitive.Integer16),
    ('PositiveSmallIntegerField', primitive.UnsignedInteger16),
    ('FloatField', primitive.Double),

    ('TimeField', primitive.Time),
    ('DateField', primitive.Date),
    ('DateTimeField', primitive.DateTime),

    # simple fixed defaults for relation fields
    ('ForeignKey', primitive.Integer32),
    ('OneToOneField', primitive.Integer32),
)


def model_mapper_factory(mapper_class, field_map):
    """Factory for model mappers.

    The factory is useful to create custom field mappers based on default one.

    """
    model_mapper = mapper_class(field_map)

    # register relation field mappers that are aware of related field type
    model_mapper.register_field_mapper(
        'ForeignKey', RelationMapper(model_mapper))

    model_mapper.register_field_mapper(
        'OneToOneField', RelationMapper(model_mapper))

    model_mapper.register_field_mapper('DecimalField',
                                       DecimalMapper(primitive.Decimal))
    return model_mapper


default_model_mapper = model_mapper_factory(DjangoModelMapper,
                                            DEFAULT_FIELD_MAP)


class DjangoComplexModelMeta(ComplexModelMeta):

    """Meta class for complex spyne models representing Django models."""

    def __new__(mcs, name, bases, attrs):  # pylint: disable=C0202
        """Populate new complex type from configured Django model."""
        super_new = super(DjangoComplexModelMeta, mcs).__new__

        abstract = bool(attrs.get('__abstract__', False))

        if abstract:
            # skip processing of abstract models
            return super_new(mcs, name, bases, attrs)

        attributes = attrs.get('Attributes')

        if attributes is None:
            raise ImproperlyConfigured('You have to define Attributes and '
                                       'specify Attributes.django_model')

        if getattr(attributes, 'django_model', None) is None:
            raise ImproperlyConfigured('You have to define django_model '
                                       'attribute in Attributes')

        mapper = getattr(attributes, 'django_mapper', default_model_mapper)
        attributes.django_mapper = mapper
        exclude = getattr(attributes, 'django_exclude', None)
        optional_relations = getattr(attributes, 'django_optional_relations',
                                     False)
        spyne_attrs = mapper.map(attributes.django_model, exclude=exclude,
                                 optional_relations=optional_relations)
        spyne_attrs.update(attrs)
        return super_new(mcs, name, bases, spyne_attrs)


@add_metaclass(DjangoComplexModelMeta)
class DjangoComplexModel(ComplexModelBase):

    """Base class with Django model mapping support.

    Sample usage: ::

        class PersonType(DjangoComplexModel):
            class Attributes(DjangoComplexModel.Attributes):
                django_model = Person


    Attribute :attr:`django_model` is required for Django model mapping
    machinery. You can customize your types defining custom type fields: ::

        class PersonType(DjangoComplexModel):
            gender = primitive.Unicode(pattern='^[FM]$')

            class Attributes(DjangoComplexModel.Attributes):
                django_model = Person


    There is an option to specify custom mapper: ::

        class PersonType(DjangoComplexModel):
            class Attributes(DjangoComplexModel.Attributes):
                django_model = Person
                django_mapper = my_custom_mapper

    You can also exclude some fields from mapping: ::

        class PersonType(DjangoComplexModel):
            class Attributes(DjangoComplexModel.Attributes):
                django_model = Person
                django_exclude = ['phone']

    You may set `django_optional_relations`` attribute flag to indicate
    that relation fields (ForeignKey, OneToOneField) of your model are
    optional.  This is useful when you want to create base and related
    instances in remote procedure. In this case primary key of base model is
    not yet available.

    """

    __abstract__ = True
