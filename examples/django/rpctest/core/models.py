# coding: utf-8

"""Rpc test models."""

from django.core.validators import MinLengthValidator, MaxLengthValidator
from django.db import models


class FieldContainer(models.Model):

    """Test model for ``DjangoMapper``."""

    char_field = models.CharField(max_length=32, default='test')
    char_field_nullable = models.CharField(max_length=32, null=True)
    slug_field = models.SlugField(max_length=32, unique=True)
    text_field = models.TextField(default='text_field')
    email_field = models.EmailField()
    boolean_field = models.BooleanField(default=True)
    integer_field = models.IntegerField(default=1)
    positive_integer_field = models.PositiveIntegerField(default=1)
    float_field = models.FloatField(default=1)
    decimal_field = models.DecimalField(max_digits=10, decimal_places=4,
                                        default=1)
    time_field = models.TimeField(auto_now_add=True)
    date_field = models.DateField(auto_now_add=True)
    datetime_field = models.DateTimeField(auto_now_add=True)

    foreign_key = models.ForeignKey('self', null=True,
                                    related_name='related_containers')
    one_to_one_field = models.OneToOneField('self', null=True)

    custom_foreign_key = models.ForeignKey(
        'RelatedFieldContainer', null=True,
        related_name='related_fieldcontainers')
    custom_one_to_one_field = models.OneToOneField('RelatedFieldContainer',
                                                   null=True)

    url_field = models.URLField(default='http://example.com')
    file_field = models.FileField(upload_to='test_file', null=True)
    excluded_field = models.CharField(max_length=32, default='excluded')
    blank_field = models.CharField(max_length=32, blank=True)
    length_validators_field = models.CharField(
        max_length=32, null=True, validators=[MinLengthValidator(3),
                                              MaxLengthValidator(10)])


class RelatedFieldContainer(models.Model):

    """Related container model to test related fields."""

    id = models.CharField(max_length=30, primary_key=True)


class User(models.Model):

    """Model for tests of relation field mapper."""

    name = models.CharField(max_length=50)


class UserProfile(models.Model):

    """Related model for tests of relation field mapper."""

    user = models.ForeignKey(User)
    data = models.CharField(max_length=50)
