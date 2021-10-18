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

"""Useful stuff to integrate Spyne with Django.

* Django model <-> spyne type mapping
* Service for common exception handling

"""

from __future__ import absolute_import

import logging
logger = logging.getLogger(__name__)

import re

from itertools import chain

from django.core.exceptions import (ImproperlyConfigured, ObjectDoesNotExist,
                                    ValidationError as DjValidationError)
from django.core.validators import (slug_re,
                                    MinLengthValidator, MaxLengthValidator)
try:
    from django.core.validators import comma_separated_int_list_re
except ImportError:
    comma_separated_int_list_re = re.compile(r'^[\d,]+$')

from spyne.error import (ResourceNotFoundError, ValidationError as
                         BaseValidationError, Fault)
from spyne.model import primitive
from spyne.model.complex import ComplexModelMeta, ComplexModelBase
from spyne.service import Service
from spyne.util.cdict import cdict
from spyne.util.odict import odict
from spyne.util.six import add_metaclass


# regex is based on http://www.w3.org/TR/xforms20/#xforms:email
email_re = re.compile(
    r"[A-Za-z0-9!#-'\*\+\-/=\?\^_`\{-~]+"
    r"(\.[A-Za-z0-9!#-'\*\+\-/=\?\^_`\{-~]+)*@"
    # domain part is either a single symbol
    r"("
    # or have at least two symbols
    # hyphen can't be at the beginning or end of domain part
    # domain should contain at least 2 parts, the last one is TLD
    r"[a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?\.)+"
    # TLD should contain only letters, at least 2
    r"[A-Za-z]{2,}", re.IGNORECASE)


def _handle_minlength(validator, params):
    new_min = validator.limit_value
    old_min = params.setdefault('min_len', new_min)
    params['min_len'] = max(old_min, new_min)


def _handle_maxlength(validator, params):
    new_max = validator.limit_value
    old_max = params.setdefault('max_len', new_max)
    params['max_len'] = min(old_max, new_max)


class BaseDjangoFieldMapper(object):

    """Abstrace base class for field mappers."""

    _VALIDATOR_HANDLERS = cdict({
        MinLengthValidator: _handle_minlength,
        MaxLengthValidator: _handle_maxlength,
    })

    @staticmethod
    def is_field_nullable(field, **kwargs):
        """Return True if django field is nullable."""
        return field.null

    @staticmethod
    def is_field_blank(field, **kwargs):
        """Return True if django field is blank."""
        return field.blank

    def map(self, field, **kwargs):
        """Map field to spyne model.

        :param field: Django Field instance
        :param kwargs: Extra params to configure spyne model
        :returns: tuple (field attribute name, mapped spyne model)

        """
        params = kwargs.copy()

        self._process_validators(field.validators, params)

        nullable = self.is_field_nullable(field, **kwargs)
        blank = self.is_field_blank(field, **kwargs)
        required = not (field.has_default() or blank or field.primary_key)

        if field.has_default():
            params['default'] = field.get_default()

        spyne_model = self.get_spyne_model(field, **kwargs)
        customized_model = spyne_model(nullable=nullable,
                                       min_occurs=int(required), **params)

        return (field.attname, customized_model)

    def get_spyne_model(self, field, **kwargs):
        """Return spyne model for given Django field."""
        raise NotImplementedError

    def _process_validators(self, validators, params):
        for v in validators:
            handler = self._VALIDATOR_HANDLERS.get(type(v))
            if handler:
                handler(v, params)


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
    def is_field_blank(field, **kwargs):
        """Return True if `optional_relations` is set.

        Otherwise use basic behaviour.

        """
        optional_relations = kwargs.get('optional_relations', False)
        return (optional_relations or
                BaseDjangoFieldMapper.is_field_blank(field, **kwargs))

    def get_spyne_model(self, field, **kwargs):
        """Return spyne model configured by related field."""
        related_field = field.rel.get_related_field() if hasattr(field, 'rel') else field.remote_field.get_related_field()
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
    def get_all_field_names(meta):
        if hasattr(meta, 'get_all_field_names'):
            return meta.get_all_field_names()

        return list(set(chain.from_iterable(
            (field.name, field.attname) if hasattr(field, 'attname') else (
            field.name,)
            for field in meta.get_fields()
            # For complete backwards compatibility, you may want to exclude
            # GenericForeignKey from the results.
            if not (field.many_to_one and field.related_model is None)
        )))

    @staticmethod
    def _get_fields(django_model, exclude=None):
        field_names = set(exclude) if exclude is not None else set()
        meta = django_model._meta  # pylint: disable=W0212
        unknown_fields_names = \
             field_names.difference(DjangoModelMapper.get_all_field_names(meta))

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


# django's own slug_re.pattern is invalid according to xml schema -- it doesn't
# like the location of the dash character. using the equivalent pattern accepted
# by xml schema here.
SLUG_RE_PATTERN = '[a-zA-Z0-9_-]+'


DEFAULT_FIELD_MAP = (
    ('AutoField', primitive.Integer32),
    ('CharField', primitive.NormalizedString),
    ('SlugField', primitive.Unicode(
        type_name='Slug', pattern=strip_regex_metachars(SLUG_RE_PATTERN))),
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


class ObjectNotFoundError(ResourceNotFoundError):

    """Fault constructed from `model.DoesNotExist` exception."""

    def __init__(self, does_not_exist_exc):
        """Construct fault with code Client.<object_name>NotFound."""
        message = str(does_not_exist_exc)
        object_name = message.split()[0]
        # we do not want to reuse initialization of ResourceNotFoundError
        Fault.__init__(
            self, faultcode='Client.{0}NotFound'.format(object_name),
            faultstring=message)


class ValidationError(BaseValidationError):

    """Fault constructed from `ValidationError` exception."""

    def __init__(self, validation_error_exc):
        """Construct fault with code Client.<validation_error_type_name>."""
        message = str(validation_error_exc)
        # we do not want to reuse initialization of BaseValidationError
        Fault.__init__(
            self, faultcode='Client.{0}'.format(
                type(validation_error_exc).__name__), faultstring=message)


class DjangoService(Service):

    """Service with common Django exception handling."""

    @classmethod
    def call_wrapper(cls, ctx):
        """Handle common Django exceptions."""
        try:
            out_object = super(DjangoService, cls).call_wrapper(ctx)
        except ObjectDoesNotExist as e:
            raise ObjectNotFoundError(e)
        except DjValidationError as e:
            raise ValidationError(e)
        return out_object


# FIXME: To be removed in Spyne 3
DjangoServiceBase = DjangoService
