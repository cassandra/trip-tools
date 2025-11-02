from django.db import models


class ItineraryManager(models.Manager):
    """Manager for Itinerary model."""

    def for_user(self, user):
        """Get all itineraries for trips where user is a member."""
        return self.filter( trip__members__user = user ).distinct()

    def for_trip(self, trip):
        """Get all itineraries for a specific trip."""
        return self.filter( trip = trip )


class ItineraryItemManager(models.Manager):
    """Manager for ItineraryItem model."""

    def for_itinerary(self, itinerary):
        """Get all items for a specific itinerary."""
        return self.filter(itinerary=itinerary)

    def for_date(self, itinerary, date):
        """Get all items starting on a specific date."""
        return self.filter(itinerary=itinerary, start_datetime__date=date)

    def by_item_type(self, item_type):
        """Get items by item type."""
        return self.filter(item_type=item_type)
