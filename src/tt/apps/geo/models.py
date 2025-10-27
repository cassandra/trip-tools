from django.db import models


class GeoPointModelMixin(models.Model):

    latitude = models.DecimalField(
        max_digits = 9,
        decimal_places = 6,
        null = True,
        blank = True,
    )
    longitude = models.DecimalField(
        max_digits = 9,
        decimal_places = 6,
        null = True,
        blank = True,
    )
    elevation_ft = models.DecimalField(
        max_digits = 9,
        decimal_places = 2,
        null = True,
        blank = True,
    )
    
    class Meta:
        abstract = True
        
