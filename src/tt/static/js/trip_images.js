/*
 * Trip Tools - Trip Images JavaScript
 * Image picker functionality for selecting reference images.
 *
 * Uses shared constants from Tt namespace (main.js) for DOM selectors.
 * All element lookups are scoped to the containing modal to support
 * multiple image pickers on the same page.
 */

(function($) {
    'use strict';

    window.Tt = window.Tt || {};

    var TtTripImages = {
        selectReferenceImage: function(clickedElement) {
            _selectReferenceImage(clickedElement);
        }
    };

    window.Tt.tripImages = TtTripImages;

    // Global function for onclick handlers in templates
    window.selectReferenceImage = function(clickedElement) {
        _selectReferenceImage(clickedElement);
    };

    function _selectReferenceImage(clickedElement) {
        var $card = $(clickedElement).closest(Tt.IMAGE_PICKER_CARD_SELECTOR);
        if ($card.length === 0) {
            console.warn('selectReferenceImage: Could not find image picker card');
            return;
        }

        // Find the containing modal to scope all element lookups
        var $modal = $card.closest('.modal');
        if ($modal.length === 0) {
            console.warn('selectReferenceImage: Could not find containing modal');
            return;
        }

        // Get image data from card's data attributes
        var imageUuid = $card.data(Tt.IMAGE_PICKER_UUID_ATTR);
        var thumbnailUrl = $card.data(Tt.IMAGE_PICKER_THUMBNAIL_URL_ATTR);
        var caption = $card.data(Tt.IMAGE_PICKER_CAPTION_ATTR) || 'Untitled';

        // Update hidden input (scoped to modal)
        var $uuidInput = $modal.find(Tt.IMAGE_PICKER_UUID_INPUT_SELECTOR);
        $uuidInput.val(imageUuid);

        // Update preview image (scoped to modal)
        var $preview = $modal.find(Tt.IMAGE_PICKER_PREVIEW_SELECTOR);
        var $img = $('<img>')
            .attr('src', thumbnailUrl)
            .attr('alt', 'Selected reference')
            .css({
                'width': '100%',
                'height': '100%',
                'object-fit': 'cover'
            });
        $preview.empty().append($img);

        // Update caption text (scoped to modal)
        var $caption = $modal.find(Tt.IMAGE_PICKER_CAPTION_SELECTOR);
        $caption.text(caption);

        // Enable the SET button (scoped to modal)
        var $setBtn = $modal.find(Tt.IMAGE_PICKER_SET_BTN_SELECTOR);
        $setBtn.prop('disabled', false);

        // Update visual selection state (scoped to modal)
        $modal.find(Tt.IMAGE_PICKER_CARD_SELECTOR).each(function() {
            var $thisCard = $(this);
            if ($thisCard.data(Tt.IMAGE_PICKER_UUID_ATTR) === imageUuid) {
                $thisCard.css('border-color', '#007bff');
            } else {
                $thisCard.css('border-color', 'transparent');
            }
        });
    }

})(jQuery);
