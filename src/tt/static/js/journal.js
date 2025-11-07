/**
 * Journal Image Picker - Image Selection Functionality
 *
 * Handles multi-selection of images with SHIFT and CTRL/CMD key support.
 */

(function() {
    'use strict';

    let selectedImages = new Set();
    let lastSelectedIndex = null;

    /**
     * Initialize image selection handlers
     */
    function initImageSelection() {
        // Delegate click handler for image cards
        $(document).on('click', '.journal-image-card', function(e) {
            e.preventDefault();
            handleImageClick(this, e);
        });

        // Delegate double-click handler for opening inspect modal
        $(document).on('dblclick', '.journal-image-card', function(e) {
            e.preventDefault();
            handleImageDoubleClick(this);
        });

        // Delegate hover handlers for metadata preview
        $(document).on('mouseenter', '.journal-image-card', function(e) {
            showMetadataPreview(this);
        });

        $(document).on('mouseleave', '.journal-image-card', function(e) {
            hideMetadataPreview();
        });

        // Update selection count after async updates
        if (typeof addAfterAsyncRenderFunction === 'function') {
            addAfterAsyncRenderFunction(updateSelectionUI);
        }
    }

    /**
     * Handle click on image card with support for SHIFT and CTRL/CMD modifiers
     */
    function handleImageClick(card, event) {
        const $card = $(card);
        const uuid = $card.data('image-uuid');
        const isCtrlOrCmd = event.ctrlKey || event.metaKey;
        const isShift = event.shiftKey;

        if (isShift && lastSelectedIndex !== null) {
            // SHIFT click: select range
            handleRangeSelection($card);
        } else if (isCtrlOrCmd) {
            // CTRL/CMD click: toggle individual
            toggleSelection($card, uuid);
        } else {
            // Normal click: select only this one
            clearAllSelections();
            toggleSelection($card, uuid);
        }

        updateSelectionUI();
    }

    /**
     * Handle SHIFT+click range selection
     */
    function handleRangeSelection($clickedCard) {
        const $allCards = $('.journal-image-card');
        const clickedIndex = $allCards.index($clickedCard);

        const startIndex = Math.min(lastSelectedIndex, clickedIndex);
        const endIndex = Math.max(lastSelectedIndex, clickedIndex);

        // Select all cards in range
        for (let i = startIndex; i <= endIndex; i++) {
            const $card = $allCards.eq(i);
            const uuid = $card.data('image-uuid');
            selectedImages.add(uuid);
            $card.addClass('selected');
        }
    }

    /**
     * Toggle selection state of an image
     */
    function toggleSelection($card, uuid) {
        if (selectedImages.has(uuid)) {
            selectedImages.delete(uuid);
            $card.removeClass('selected');
        } else {
            selectedImages.add(uuid);
            $card.addClass('selected');
        }

        // Update last selected index for SHIFT selection
        const $allCards = $('.journal-image-card');
        lastSelectedIndex = $allCards.index($card);
    }

    /**
     * Clear all selections
     */
    function clearAllSelections() {
        selectedImages.clear();
        $('.journal-image-card').removeClass('selected');
        lastSelectedIndex = null;
    }

    /**
     * Update UI to reflect current selection state
     */
    function updateSelectionUI() {
        const count = selectedImages.size;
        const $countBadge = $('#selected-images-count');

        if (count > 0) {
            if ($countBadge.length === 0) {
                // Create badge if it doesn't exist
                $('.journal-image-panel-header h5').after(
                    '<span id="selected-images-count" class="badge badge-primary ml-2">' +
                    count + ' selected</span>'
                );
            } else {
                // Update existing badge
                $countBadge.text(count + ' selected');
            }
        } else {
            // Remove badge when no selection
            $countBadge.remove();
        }
    }

    /**
     * Handle double-click to open image inspect modal
     */
    function handleImageDoubleClick(card) {
        const $card = $(card);
        const inspectUrl = $card.data('inspect-url');

        if (inspectUrl) {
            AN.get(inspectUrl);
        }
    }

    /**
     * Show metadata preview on hover
     */
    function showMetadataPreview(card) {
        const $card = $(card);

        // Extract metadata from the card
        const caption = $card.find('.font-weight-bold').text().trim() || 'Untitled';
        const time = $card.find('.text-muted').first().text().trim() || 'Unknown time';
        const uuid = $card.data('image-uuid');

        // Create preview popup
        const $preview = $('<div class="image-metadata-preview">' +
            '<strong>' + caption + '</strong><br>' +
            '<small class="text-muted">' + time + '</small><br>' +
            '<small class="text-muted">UUID: ' + uuid.substring(0, 8) + '...</small>' +
            '</div>');

        // Append to body first to measure width
        $('body').append($preview);

        // Position it to the left of the card
        const offset = $card.offset();
        $preview.css({
            top: offset.top + 'px',
            left: (offset.left - $preview.outerWidth() - 10) + 'px'
        });
    }

    /**
     * Hide metadata preview
     */
    function hideMetadataPreview() {
        $('.image-metadata-preview').remove();
    }

    // Initialize on document ready
    $(document).ready(function() {
        initImageSelection();
    });

})();
