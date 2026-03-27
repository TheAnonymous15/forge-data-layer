# -*- coding: utf-8 -*-
"""
ForgeForth Africa - Data Layer App Configuration
"""
from django.apps import AppConfig


class DataLayerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'data_layer'
    verbose_name = 'Data Layer Service'

    def ready(self):
        pass

