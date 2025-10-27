from django.db import models
from django.conf import settings

from tt.apps.locations.models import Location
from tt.apps.trips.models import Trip

from tt.apps.attribute.models import AttributeModel
from . import managers


class Review(models.Model):
    """
    Reviews for locations (hotels, restaurants, attractions).
    """
    objects = managers.ReviewManager()

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete = models.CASCADE,
        related_name = 'reviews',
    )
    trip = models.ForeignKey(
        Trip,
        on_delete = models.CASCADE,
        related_name = 'reviews',
    )
    location = models.ForeignKey(
        Location,
        on_delete = models.CASCADE,
        related_name = 'reviews',
    )

    title = models.CharField( max_length = 200 )
    text = models.TextField()
    rating = models.IntegerField(
        help_text = 'Rating',
        null = True,
        blank = True,
    )
    posted_to = models.CharField(
        max_length = 500,
        blank = True,
        help_text = 'Delimited list of sites',
    )

    created_datetime = models.DateTimeField( auto_now_add = True )
    modified_datetime = models.DateTimeField( auto_now = True )

    class Meta:
        verbose_name = 'Review'
        verbose_name_plural = 'Reviews'
        ordering = ['-created_datetime']

    def __str__(self):
        return f"Review: {self.location.title} - {self.title}"

    
class ReviewAttribute( AttributeModel ):

    review = models.ForeignKey(
        Review,
        on_delete = models.CASCADE,
        related_name = 'attributes',
    )

    class Meta:
        verbose_name = 'Review Attribute'
        verbose_name_plural = 'Review Attributes'
    
    def get_upload_to(self):
        return 'reviews/attributes/'
