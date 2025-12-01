import json

from django.urls import reverse


class TtUrlPatterns:
    """
    URL patterns for JavaScript, generated using Django's reverse().

    Uses PLACEHOLDER_UUID which JavaScript replaces with actual UUIDs.
    This ensures URL patterns stay in sync with urls.py.
    """
    PLACEHOLDER_UUID = '00000000-0000-0000-0000-000000000000'

    def __init__(self):
        self.IMAGE_INSPECT = reverse(
            'images_image_inspect',
            kwargs ={ 'image_uuid': self.PLACEHOLDER_UUID }
        )

    def to_json_dict_str(self):
        return json.dumps({
            'PLACEHOLDER_UUID': self.PLACEHOLDER_UUID,
            'IMAGE_INSPECT': self.IMAGE_INSPECT,
        }, indent = 4 )
