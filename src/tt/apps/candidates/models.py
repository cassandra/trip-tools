from django.db import models
from django.contrib.contenttypes.fields import GenericRelation

from tt.apps.attribute.models import AttributeModel
from tt.apps.common.model_fields import LabeledEnumField
from tt.apps.contacts.models import ContactInfo
from tt.apps.locations.models import Location
from tt.apps.routes.models import Route
from tt.apps.trips.models import Trip

from .enums import CandidateType
from . import managers


class CandidateGroup(models.Model):
    """
    A collection of comparable candidates (e.g., multiple hotel options,
    flight options, tour operators for the same activity).  These are used
    to help construct an itinerary.

    Groups candidates together for comparison and decision-making.

    """
    objects = managers.CandidateGroupManager()

    trip = models.ForeignKey(
        Trip,
        on_delete = models.CASCADE,
        related_name = 'candidate_groups',
    )
    candidate_type = LabeledEnumField(
        CandidateType,
        'Candidate Type',
    )
    location = models.ForeignKey(
        # Optionally associate a Location - e.g., a town for lodging options
        Location,
        on_delete = models.SET_NULL,
        null = True,
        blank = True,
        related_name = 'candidate_groups',
    )
    title = models.CharField(
        max_length = 200,
        help_text = 'E.g., "Hotels near Louvre", "Flights Paris to Rome", "Cooking classes"',
    )
    description = models.TextField(
        blank = True,
        help_text = 'Context about what you\'re looking for',
    )

    created_datetime = models.DateTimeField(auto_now_add = True)
    modified_datetime = models.DateTimeField(auto_now = True)

    class Meta:
        verbose_name = 'Candidate Group'
        verbose_name_plural = 'Candidate Groups'
        ordering = ['-created_datetime']


class Candidate(models.Model):
    """
    A single option being considered within a CandidateGroup.

    Stores all comparison-relevant data like pricing, pros/cons, availability.
    """
    objects = managers.CandidateManager()

    group = models.ForeignKey(
        CandidateGroup,
        on_delete = models.CASCADE,
        related_name = 'candidates',
    )
    location = models.ForeignKey(
        Location,
        on_delete = models.SET_NULL,
        null = True,
        blank = True,
        related_name = 'candidates',
    )
    route = models.ForeignKey(
        # Optional for things like scenic drives, hikes, tours, etc.
        Route,
        null = True,
        blank = True,
        on_delete = models.SET_NULL,
        related_name = 'candidates',
    )
    name = models.CharField(
        max_length = 200,
        help_text = 'E.g., hotel name, airline + flight number, tour operator',
    )
    contact_info = GenericRelation(
        ContactInfo,
        related_query_name = 'candidate',
    )
    total_cost = models.DecimalField(
        max_digits = 10,
        decimal_places = 2,
        null = True,
        blank = True,
    )
    unit_cost = models.DecimalField(
        max_digits = 10,
        decimal_places = 2,
        null = True,
        blank = True,
    )
    currency = models.CharField(
        max_length = 3,
        blank = True,
        help_text = 'E.g., USD, EUR, GBP',
    )
    preference_order = models.PositiveIntegerField(
        default = 0,
    )    
    notes = models.TextField(
        blank = True,
        help_text = 'Additional notes about this option',
    )

    created_datetime = models.DateTimeField(auto_now_add = True)
    modified_datetime = models.DateTimeField(auto_now = True)

    class Meta:
        ordering = ['group', 'preference_order']


class CandidateAttribute( AttributeModel ):
    """
    Flexible key-value pairs for candidate-specific comparison data.

    Allows tracking category-specific attributes without bloating the Candidate model:
    - Hotels: "Distance to metro", "Pool", "Breakfast included"
    - Flights: "Layovers", "Baggage", "Seat selection"
    - Tours: "Duration", "Group size", "Languages offered"
    """
    candidate = models.ForeignKey(
        Candidate,
        on_delete = models.CASCADE,
        related_name = 'attributes',
    )

    class Meta:
        verbose_name = 'Candidate Attribute'
        verbose_name_plural = 'Candidate Attributes'
    
    def get_upload_to(self):
        return 'candidates/attributes/'
