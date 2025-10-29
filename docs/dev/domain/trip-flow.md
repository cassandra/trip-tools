# Trip Flow and Requirements

The overall trip experience has four major phases:
1. Research and Planning
2. Booking
3. Execution
4. Post-trip Activities

Within each, there are various activities, data associated with those activities and a set of tools that are used during the phase.  below we detail these phases and their activities, data and tools.

## Research and Planning

### Activities

- Researching locations
  - Reading Travel logs and articles
  - Prompting AI Assistants
- Plotting locations on a map
- Plotting routes on a map
  - Driving routes
  - Hiking routes
- Itinerary Options
  - Flight options
  - Ground transportation options

### Data

- Geographic Point
  - Generic for multiple uses
  - longitude
  - latitude
  - elevation

- ContactInfo
  - Generic for multiple uses: email, phone, address, web link, etc.

- Route
  - Generic for multiple uses: a sequence of Route Waypoints
  - Route Waypoint
    - Geographic Point
	- date/time
	
- Trip
  - User
  - Title
  - Description
  - Status { upcoming, current, past }
  
- Location
  - Items that visually show on a map
  - Trip
  - Title
  - Category - e.g., attraction, dining, town, lodging, dining, transportation, tours, etc.
  - Sub-category - e.g., museum, park, religious, trailhead, etc.
  - Geographic location
    - geographic coordinates
	- town
  - Contact Info (email, phone, chat/messaging, urls)
  - Desirability { low, medium, high }
  - Advanced Booking Required { no, maybe, yes }
  - Open days/times
  - List of Location Notes
  - Location Note
    - Text
    - Note source label and/or source link
  
- Candidate Group
  - Related set of Candidates for comparisons - e.g., flights, hotels, tours, etc.
  - Trip
  - title
  - description
  - Location (optional) - e.g., a town for lodging options
  - Candidate type - e.g., transportation, lodging, tour
  - Candidate
    - name
	- notes
	- Contact Info
    - Location (optional) - e.g., a hotel or tour
	- Route (optional) - e.g., a flight with possible connections
    - Total cost
    - Unit cost
	- Currency
    - Rating
	- Preference rank/order
	- Extra Attributes (using general name/type/value model w/attachments)

- Itinerary
  - Trip
  - title
  - description
  - Set of Itinerary Items
  - Itinerary Item
    - Itinerary
    - Item type - e.g., flight, lodging, car rental, tour, activity, etc.
    - title
    - description
    - notes
	- Location (optional)
	- Route (optional)
	- start date/time
	- end date/time

### Tools Used

- Google My Maps
- Google Sheets
- Custom Browser Plugin
- Travel Sites 
  - TripAdvisor
  - Atlas Obscura
- Web Searches for travel logs and articles
- AI Agents (for reommendations)
- Google Flights (options, prices, price watching)
- FlightConnections (https://www.flightconnections.com/)
  
## Booking

### Activities

- Booking
  - Flights
  - Hotels
  - Cars
  - Trains
  - Boats
  - Tours
- Organizing emails, receipts, tickets, etc.
- Accumulating TODO items and scheduling them
- Executing TODO items

### Data

BookingData
  - Itinerary Item
  - Booking status - e.g., todo, done, etc.
  - Payment status - e.g., todo, paid, auto-bill, etc
  - Cancellation policy
  - Confirmed
  - Booking site
  - Booking reference
  - Confirmation number
  - Booking date
  - Payment date
  - Total cost
  - Unit cost
  - Currency
  - Extra Attributes (using general name/type/value model w/attachments)
    
### Tools Used

- TripIt
- Google My Maps
- Google Sheets
- Custom Browser Plugin
- Booking Sites (booking,com, chase travel, airline sites, hotel sites, rental cars, etc)
- Google Flights
- Seat Guru (or similar)

## Execution (During travel)

### Activities

- Pre-trip checklist
- Keeping log of daily activities (raw data used later for trip journal)
- Taking photos and videos
- Additional Bookings
- Additional Payments
- Itinerary changes (add, remove, chgange, cancel)
- Tracking expenses
- Weather forecasts for planning

### Data

- Daily Notebook
  - date
  - text

### Tools Used

- TripIt
- Google My Maps
- Google Sheets
- Booking Sites (booking,com, chase travel, airline sites, hotel sites, rental cars, etc)
- Google Flights
- Seat Guru (or similar)
- Tricount (shared expense tracking)
- Text editor (trip notebook)
- Phone/Camera

## Post-trip Activities

### Activities

- Writing Reviews
  - Hotels
  - Restaurants
  - Activities/Tours
  - Locations/Sites
- Updating personal travel map
  - Add new locations
  - Regenerate map
- Organizing photos
  - Filtering
  - Captioning
  - Ordering
  - Cropping
  - Thumbnails
- Adding Photos
  - tickets/stubs
  - brochures/maps
  - misc. accumulated location items (e.g., beer coasters)
- Creating trip journal
  - Create day-by-day pages with photos, captions and textual descriptions
  - Use daily trip logs and photos to form narratives
  - Creating day-by-day itinerary map
  - Creating photo-only navigation
  - Creating table of contents by day w/daily image selection
  
### Data

Review
  - Trip
  - Location
  - title
  - Text
  - Rating
  - Posted to list
	  
### Tools Used

- Review sites
  - Google (restaurants)
  - Booking.com (hotels)
  - Trip Advisor (tours and places)
- Tripadvisor (personal travel map)
- Journaling Tools (sister project)
  - Organize photos
  - Create trip journal / web pages
