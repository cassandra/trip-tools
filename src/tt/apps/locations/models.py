from django.db import models
from django.contrib.contenttypes.fields import GenericRelation

from tt.apps.common.model_fields import LabeledEnumField
from tt.apps.contacts.models import ContactInfo
from tt.apps.geo.models import GeoPointModelMixin
from tt.apps.routes.models import Route
from tt.apps.trips.models import Trip

from .enums import AdvancedBookingType, DesirabilityType
from . import managers


class LocationCategory(models.Model):
    """
    Categories for location items (attraction, dining, lodging, etc.)
    """
    objects = managers.LocationCategoryManager()

    name = models.CharField( max_length = 100, unique = True )
    slug = models.SlugField( unique = True )
    description = models.TextField( blank = True )
    color_code = models.CharField(
        max_length = 50,
        blank = True,
        help_text = 'RGB color code, e.g., "RGB (245, 124, 0)"',
    )
    icon_code = models.CharField(
        max_length = 20,
        blank = True,
        help_text = 'Google Maps icon code, e.g., "1535"',
    )

    class Meta:
        verbose_name = 'Location Category'
        verbose_name_plural = 'Location Categories'
        ordering = ['name']

    def __str__(self):
        return self.name


class LocationSubCategory(models.Model):
    """
    Sub-categories (museum, park, religious, trailhead, etc.)
    """
    objects = managers.LocationSubCategoryManager()

    category = models.ForeignKey(
        LocationCategory,
        on_delete = models.CASCADE,
        related_name = 'subcategories',
    )
    name = models.CharField( max_length = 100 )
    slug = models.SlugField()
    color_code = models.CharField(
        max_length = 50,
        blank = True,
        help_text = 'RGB color code, e.g., "RGB (9, 113, 56)"',
    )
    icon_code = models.CharField(
        max_length = 20,
        blank = True,
        help_text = 'Google Maps icon code, e.g., "1596"',
    )

    class Meta:
        verbose_name = 'Location Sub-category'
        verbose_name_plural = 'Location Sub-categories'
        unique_together = [ ('category', 'slug') ]
        ordering = ['category', 'name']

    def __str__(self):
        return f"{self.category.name} - {self.name}"


class Location( GeoPointModelMixin, models.Model ):
    """
    A place of interest associated with a trip.

    Design: Locations are trip-specific to maintain clean data isolation and
    trip context. For location reuse across trips, use copy/import features.
    For pre-trip research, create a "Future Trips" or "Wishlist" trip.
    """
    objects = managers.LocationManager()

    trip = models.ForeignKey(
        Trip,
        on_delete = models.CASCADE,
        related_name = 'locations',
    )
    title = models.CharField(
        max_length = 200,
    )
    subcategory = models.ForeignKey(
        LocationSubCategory,
        on_delete = models.SET_NULL,
        null = True,
        blank = True,
        related_name = 'locations',
    )
    route = models.ForeignKey(
        # Optional for things like scenic drives, hikes, tours, etc.
        Route,
        null = True,
        blank = True,
        on_delete = models.SET_NULL,
        related_name = 'locations',
    )
    contact_info = GenericRelation(
        # Contact information (via GenericRelation): e.g., phone, email,
        # website, address, messaging apps. One-to-many relation.
        ContactInfo,
        related_query_name = 'location',
    )
    rating = models.DecimalField(
        max_digits = 4,
        decimal_places = 1,
        null = True,
        blank = True,
        help_text = 'Rating (e.g., 4.5 out of 5)',
    )
    desirability = LabeledEnumField(
        DesirabilityType,
        'Desirability',
        null = True,
        blank = True,
    )
    advanced_booking = LabeledEnumField(
        AdvancedBookingType,
        'Advanced Booking',
        null = True,
        blank = True,
    )
    open_days_times = models.TextField(
        # Opening days/hours, closed days, days to prefer or avoid (e.g., due to events/crowds)
        # Maybe make this data more structured in the future?
        blank = True,
    )
    created_datetime = models.DateTimeField( auto_now_add = True )
    modified_datetime = models.DateTimeField( auto_now = True )

    class Meta:
        verbose_name = 'Location'
        verbose_name_plural = 'Locations'
        ordering = ['title']


class LocationNote(models.Model):
    """
    Notes associated with locations, with source attribution.
    """
    objects = managers.LocationNoteManager()

    location = models.ForeignKey(
        Location,
        on_delete = models.CASCADE,
        related_name = 'location_notes',
    )

    text = models.TextField()
    source_label = models.CharField( max_length = 200, blank = True )
    source_url = models.URLField( blank = True )

    created_datetime = models.DateTimeField( auto_now_add = True )
    modified_datetime = models.DateTimeField( auto_now = True )

    class Meta:
        verbose_name = 'Location Note'
        verbose_name_plural = 'Location Notes'
        ordering = ['created_datetime']
