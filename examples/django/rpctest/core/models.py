# coding: utf-8

"""Rpc test models."""

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

    foreign_key = models.ForeignKey('self', null=True)

    url_field = models.URLField(default='http://example.com')
    file_field = models.FileField(upload_to='test_file', null=True)
