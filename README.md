<img src="src/tt/static/img/tt-logo-467x200.png" alt="Trip Tools Logo" height="75">

# Trip Tools

Open source trip planning, trip management and trip journaling.

## Why Trip Tools?

**The Problem:** There are lots of good tools you can use for managing your trips. 

Why is that a problem?  Because you need to use **lots** of tools.  

A trip is not just about planning, it is not just about managing your bookings and it is not just about sharing your travel logs/photos. Tools tend to focus on only one part of your overall "trip problem" which create data silos/ The burden is put on you to juggle and try to stitch these all together: cutting and pasting, multiple logins, different formats, etc.  Planning a trip with others just exacerbates the problem: e.g., now you need to "invite" or "share" a slew of different services/documents.

**Our Solution:** We view the entire life-cycle of a trip as one problem. Pre-trip research, comparisons, bookings, data needed on the travel days themselves, post-trip journaling/photo sharing, etc.  This is the problem we aim to solve:

   *Making everything connected an accessible from a single place by connecting all the data at each phase of a trip's lifecycle.*

## Project Status

**Early Development** We are just getting started. We have the main post-trip features currently available:

1. Journal Creation & Editing
    - Rich text editor with drag-and-drop image insertion
    - Auto-save with conflict detection and visual diffs
    - Reference image system for entries
    - Version history with restore capabilities
2. Publishing System
    - Convert private journals to public travelogs
    - Three visibility levels: PRIVATE, PROTECTED (password), PUBLIC
    - Immutable snapshots preserve published versions
    - Password protection with session-based access
3. Image Management
    - Multi-file upload with processing
    - EXIF metadata extraction (GPS, timestamps)
    - Image resizing for web and thumbnails
    - Permission-based access control
4. Public Viewing
    - Clean travelog interface with 6 color themes
    - Table of contents navigation
    - Image gallery with date-based browsing
    - Responsive design for all devices

## Contributing

We welcome all types of contributions:

**Users:** Try the app and share your experience - what works, what doesn't, what's missing

**Developers:** Help improve the codebase. Built with Django, JavaScript, and Bootstrap. See [Development](docs/Development.md).

**Designers:** Help us improve the user experience and visual design. We'd love your input on making this more intuitive and beautiful.

See [Contributing Guidelines](CONTRIBUTING.md) for details.

## Architecture & Security

- **Privacy-first:** Your data is your data. No third-party services get access.
- **Local-first:** You can host and run this at home if you like.
- **Django backend:** Mature, secure web framework

For technical details, see our [Development Documentation](docs/Development.md).

---

## Resources

### Contributors  
- [Contributing](CONTRIBUTING.md) - How to get involved
- [Development](docs/Development.md) - Technical setup and guidelines
- [Code of Conduct](CODE_OF_CONDUCT.md) - Community standards
- [Security](SECURITY.md) - Security policy and reporting

### Project
- [ChangeLog](CHANGELOG.md) - Release history
- [License](LICENSE.md) - MIT License terms
