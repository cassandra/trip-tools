"""
Management command to seed location categories and subcategories.

Idempotent - safe to run multiple times. Uses get_or_create pattern.

Usage:
    ./src/manage.py tt_createseeddata
"""
from django.core.management.base import BaseCommand

from tt.apps.locations.models import LocationCategory, LocationSubCategory


class Command( BaseCommand ):
    help = 'Seed location categories and subcategories'

    def add_arguments( self, parser ):
        parser.add_argument(
            '--quiet',
            action='store_true',
            help='Suppress output messages'
        )

    def handle( self, *args, **options ):
        quiet = options['quiet']

        categories_data = [
            {
                'name': 'Attractions',
                'slug': 'attractions',
                'color_code': 'RGB (245, 124, 0)',
                'icon_code': '1535',
                'subcategories': [
                    {'name': 'Hike/Trail', 'slug': 'hike', 'color_code': 'RGB (9, 113, 56)', 'icon_code': '1596'},
                    {'name': 'Museum', 'slug': 'museum', 'color_code': 'RGB (245, 124, 0)', 'icon_code': '1636'},
                    {'name': 'Viewpoint/Photo Op', 'slug': 'view_photoop', 'color_code': 'RGB (57, 73, 171)', 'icon_code': '1535'},
                    {'name': 'Neighborhood/Area', 'slug': 'neighborhood', 'color_code': 'RGB (245, 124, 0)', 'icon_code': '1604'},
                    {'name': 'Town', 'slug': 'town', 'color_code': 'RGB (245, 124, 0)', 'icon_code': '1547'},
                    {'name': 'Church/Religious', 'slug': 'church_religious', 'color_code': 'RGB (245, 124, 0)', 'icon_code': '1671'},
                    {'name': 'Cemetery', 'slug': 'cemetery', 'color_code': 'RGB (245, 124, 0)', 'icon_code': '1542'},
                    {'name': 'Store/Shop', 'slug': 'store_shop', 'color_code': 'RGB (245, 124, 0)', 'icon_code': '1686'},
                    {'name': 'Historic/Ruins', 'slug': 'historic_ruins', 'color_code': 'RGB (245, 124, 0)', 'icon_code': '1598'},
                    {'name': 'Park/Garden', 'slug': 'park_garden', 'color_code': 'RGB (245, 124, 0)', 'icon_code': '1582'},
                    {'name': 'Waterfall', 'slug': 'waterfall', 'color_code': 'RGB (245, 124, 0)', 'icon_code': '1892'},
                    {'name': 'Beach', 'slug': 'beach', 'color_code': 'RGB (245, 124, 0)', 'icon_code': '1521'},
                    {'name': 'Cinema/Play', 'slug': 'cinema_play', 'color_code': 'RGB (245, 124, 0)', 'icon_code': '1635'},
                    {'name': 'Monument', 'slug': 'monument', 'color_code': 'RGB (245, 124, 0)', 'icon_code': '1599'},
                    {'name': 'Fountain/Statue', 'slug': 'fountain', 'color_code': 'RGB (245, 124, 0)', 'icon_code': '1580'},
                    {'name': 'Artwork', 'slug': 'artwork', 'color_code': 'RGB (245, 124, 0)', 'icon_code': '1509'},
                    {'name': 'Astronomy', 'slug': 'astronomy', 'color_code': 'RGB (245, 124, 0)', 'icon_code': '1878'},
                    {'name': 'Cave', 'slug': 'cave', 'color_code': 'RGB (245, 124, 0)', 'icon_code': '1767'},
                    {'name': 'Geothermal/Hot Springs', 'slug': 'geothermal', 'color_code': 'RGB (245, 124, 0)', 'icon_code': '1811'},
                ]
            },
            {
                'name': 'Dining',
                'slug': 'dining',
                'color_code': 'RGB (251, 192, 45)',
                'icon_code': '1577',
                'subcategories': [
                    {'name': 'Lunch/Dinner', 'slug': 'lunch_dinner', 'color_code': 'RGB (251, 192, 45)', 'icon_code': '1577'},
                    {'name': 'Coffee/Breakfast', 'slug': 'coffee_breakfast', 'color_code': 'RGB (121, 85, 72)', 'icon_code': '1534'},
                    {'name': 'Deserts/Snacks', 'slug': 'deserts', 'color_code': 'RGB (57, 73, 171)', 'icon_code': '1607'},
                    {'name': 'Drinks/Bar', 'slug': 'drinks_bar', 'color_code': 'RGB (156, 39, 176)', 'icon_code': '1517'},
                    {'name': 'Food Area', 'slug': 'food_area', 'color_code': 'RGB (0, 151, 167)', 'icon_code': '1611'},
                ]
            },
            {
                'name': 'Towns',
                'slug': 'towns',
                'color_code': 'RGB (165, 39, 20)',
                'icon_code': '1603',
                'subcategories': [
                    # Singleton subcategory for Towns category
                    {'name': 'Town', 'slug': 'towns_town', 'color_code': 'RGB (165, 39, 20)', 'icon_code': '1603'},
                ]
            },
            {
                'name': 'Lodging',
                'slug': 'lodging',
                'color_code': 'RGB (194, 24, 91)',
                'icon_code': '1602',
                'subcategories': [
                    # Singleton subcategory for Lodging category
                    {'name': 'Accommodation', 'slug': 'accommodation', 'color_code': 'RGB (194, 24, 91)', 'icon_code': '1602'},
                ]
            },
            {
                'name': 'Transportation/Tours',
                'slug': 'transportation_tours',
                'color_code': 'RGB (0, 151, 167)',
                'icon_code': '1522',
                'subcategories': [
                    {'name': 'Plane', 'slug': 'plane', 'color_code': 'RGB (0, 151, 167)', 'icon_code': '1504'},
                    {'name': 'Car/Auto', 'slug': 'car_auto', 'color_code': 'RGB (0, 151, 167)', 'icon_code': '1538'},
                    {'name': 'Boat', 'slug': 'boat', 'color_code': 'RGB (0, 151, 167)', 'icon_code': '1681'},
                    {'name': 'Train', 'slug': 'train', 'color_code': 'RGB (0, 151, 167)', 'icon_code': '1716'},
                    {'name': 'Cable Car/Funicular', 'slug': 'cable_car_funicular', 'color_code': 'RGB (0, 151, 167)', 'icon_code': '1533'},
                    {'name': 'Walking', 'slug': 'walking', 'color_code': 'RGB (0, 151, 167)', 'icon_code': '1596'},
                    {'name': 'Ferry', 'slug': 'ferry', 'color_code': 'RGB (0, 151, 167)', 'icon_code': '1569'},
                    {'name': 'Bus', 'slug': 'bus', 'color_code': 'RGB (0, 151, 167)', 'icon_code': '1532'},
                    {'name': 'Bicycle', 'slug': 'bicycle', 'color_code': 'RGB (0, 151, 167)', 'icon_code': '1522'},
                    {'name': 'Helicopter', 'slug': 'helicopter', 'color_code': 'RGB (0, 151, 167)', 'icon_code': '1593'},
                    {'name': 'Parking', 'slug': 'parking', 'color_code': 'RGB (0, 151, 167)', 'icon_code': '1644'},
                ]
            },
        ]

        created_cats = 0
        created_subcats = 0

        for cat_data in categories_data:
            subcategories_data = cat_data.pop( 'subcategories' )
            category, created = LocationCategory.objects.get_or_create(
                slug = cat_data['slug'],
                defaults = cat_data
            )
            if created:
                created_cats += 1

            for subcat_data in subcategories_data:
                _, created = LocationSubCategory.objects.get_or_create(
                    slug = subcat_data['slug'],
                    defaults = {
                        'category': category,
                        **subcat_data
                    }
                )
                if created:
                    created_subcats += 1

        if not quiet:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Seed data complete: {created_cats} categories, '
                    f'{created_subcats} subcategories created'
                )
            )
