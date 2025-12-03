# Data Model

## Users and Trips

- Trip instances do not have a defined, set owner, but a set of one or more members.
- TripMember is a user defined to have permissions to access a Trip (TripPermissionLevel)
- Trips allow one or more TripMember instances.
- Trips may have multiple owners
- A Trip must have at least one owner

## Journals and Travelogs

- A Journal is a day-by-day accounting of the trip, authored by one or more TripMembers
- A Journal can be published for public access.
- A published journal is a Travelog
- A Travelog can an immutable copy of the Journal at time of publication.
- A Trip can have zero or more Journals
- Initial implementation does not allow auser to create more than one Journal.
- Future features may remove the single journal restriction.

## Images

- An image stands alone with to explicit relationship to a Trip.
- An image has one owner who is the person that uploaded the image.
- An image becomes implicitly associated with a Trip by including a reference to it in a Journal.
- The source of truth of which images are associated with which trips is the Journal content.
- An image can be associated with multiple Trips.
- When an image is associated with a Trip, all Trip members with editing permision can modify it.

## Itineraries and Bookings

- An Itinerary is a set of items with a date/time span defining some trip activity or event.
- A Booking is an Itinerary item that is linked ot a financial transaction.
- All Bookings are Itinerary items.
- Not all Itinerary items are Bookings.
- A Booking represents a expected future or a past financial transaction.
