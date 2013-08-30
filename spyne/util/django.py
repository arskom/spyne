# coding: utf-8

"""Support for Django model <-> spyne type mapping."""

from __future__ import absolute_import

import logging
from django.core.exceptions import ImproperlyConfigured
from django.core.validators import (email_re, slug_re,
                                    comma_separated_int_list_re, URLValidator)
from spyne.model.complex import ComplexModelMeta, ComplexModelBase
from spyne.model import primitive


logger = logging.getLogger(__name__)


class DjangoFieldMapper(object):

    """Base mapper for django fields."""

    def __init__(self, spyne_model):
        self.spyne_model = spyne_model

    def map(self, field, **kwargs):
        """Map field to spyne model.

        :param field: Django Field instance
        :param kwargs: Extra params to configure spyne model
        :returns: tuple (field attribute name, mapped spyne model)

        """
        params = kwargs.copy()

        if field.max_length:
            params['max_len'] = field.max_length

        customized_model = self.spyne_model(
            default=field.get_default(), nullable=field.null,
            min_occurs=int(not (field.has_default() or field.null)),
            **params)

        return (field.attname, customized_model)


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


class DjangoModelMapper(object):

    r"""Mapper from django models to spyne complex models.

    You can extend it registering new field types:

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

    # default registry shared between DjangoModelMapper instances
    # subclasses may define own registry in __init__
    _registry = {}

    field_mapper_class = DjangoFieldMapper

    class UnknownFieldMapperException(Exception):
        """Raises when there is no field mapper for given django_type."""

    def __init__(self, django_spyne_models=()):
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

    def map(self, django_model):
        """Prepare dict of model fields mapped to spyne models.

        :param django_model: Django model class.
        :returns: dict mapping attribute names to spyne models
        :raises: :exc:`UnknownFieldMapperException`

        """
        field_map = {}

        for field in django_model._meta.fields:
            field_type = field.get_internal_type()
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
                    continue

            attr_name, spyne_model = field_mapper.map(field)
            field_map[attr_name] = spyne_model

        return field_map


default_model_mapper = DjangoModelMapper((
    ('AutoField', primitive.Integer),
    ('CharField', primitive.NormalizedString),
    ('SlugField', primitive.Unicode(type_name='Slug', pattern_re=slug_re)),
    ('TextField', primitive.String),
    ('EmailField', primitive.Unicode(type_name='Email', pattern_re=email_re)),
    ('CommaSeparatedIntegerField', primitive.Unicode(
        type_name='CommaSeparatedField',
        pattern_re=comma_separated_int_list_re)),
    ('UrlField', primitive.AnyUri(type_name='Url',
                                  pattern_re=URLValidator.regex)),
    ('FilePathField', primitive.String),
    ('FileField', primitive.String),
    ('ImageField', primitive.String),

    ('BooleanField', primitive.Boolean),
    ('NullBooleanField', primitive.Boolean),
    ('IntegerField', primitive.Integer),
    ('BigIntegerField', primitive.Integer64),
    ('PositiveIntegerField', primitive.UnsignedInteger),
    ('SmallIntegerField', primitive.Integer16),
    ('PositiveSmallIntegerField', primitive.UnsignedInteger16),
    ('FloatField', primitive.Double),

    ('TimeField', primitive.Time),
    ('DateField', primitive.Date),
    ('DateTimeField', primitive.DateTime),

    ('ForeignKey', primitive.Integer),
))


default_model_mapper.register_field_mapper('DecimalField',
                                           DecimalMapper(primitive.Decimal))


class DjangoComplexModelMeta(ComplexModelMeta):

    """Meta class for complex spyne models representing Django models."""

    def __new__(mcs, name, bases, attrs):
        super_new = super(DjangoComplexModelMeta, mcs).__new__

        try:
            parents = [b for b in bases if issubclass(b, DjangoComplexModel)]
        except NameError:
            # we are defining DjangoComplexModel itself
            parents = None

        if not parents:
            # If this isn't a subclass of DjangoComplexModel, don't do
            # anything special.
            return super_new(mcs, name, bases, attrs)

        attributes = attrs.get('Attributes')

        if attributes is None:
            raise ImproperlyConfigured('You have to define Attributes and '
                                       'specify Attributes.django_model')

        if attributes.django_model is None:
            raise ImproperlyConfigured('You have to define django_model '
                                       'attribute in Attributes')

        mapper = getattr(attributes, 'django_mapper', default_model_mapper)
        attributes.django_mapper = mapper
        spyne_attrs = mapper.map(attributes.django_model)
        spyne_attrs.update(attrs)
        return super_new(mcs, name, bases, spyne_attrs)


class DjangoComplexModel(ComplexModelBase):

    """Base class with Django model mapping support.

    Sample usage:

        class PersonType(DjangoComplexModel):
            class Attributes(DjangoComplexModel.Attributes):
                django_model = Person


    Attribute :attr:``django_model` is required for Django model mapping
    machinery. You can customize your types defining custom type fields:

        class PersonType(DjangoComplexModel):
            gender = primitive.Unicode(pattern='^[FM]$')

            class Attributes(DjangoComplexModel.Attributes):
                django_model = Person


    There is an option to specify custom mapper:

        class PersonType(DjangoComplexModel):
            class Attributes(DjangoComplexModel.Attributes):
                django_model = Person
                django_mapper = my_custom_mapper

    """

    __metaclass__ = DjangoComplexModelMeta
