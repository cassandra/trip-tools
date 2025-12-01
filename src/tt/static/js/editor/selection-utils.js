/**
 * Selection Utilities for Journal Editor
 *
 * Shared utilities for image selection and coordination across editor components.
 *
 * Components:
 * - getSelectionModifiers: Extracts modifier key state from events
 * - SelectionBadgeManager: Displays selection count badges
 * - ImageSelectionCoordinator: Coordinates selection state across components
 * - ImageDataService: Centralized image data lookup service
 *
 * Dependencies:
 * - jQuery
 * - TtConst (from main.js)
 *
 * Usage:
 *   var modifiers = Tt.JournalEditor.getSelectionModifiers(event);
 *   var badgeManager = new Tt.JournalEditor.SelectionBadgeManager($element, 'badge-id');
 *   var imageData = Tt.JournalEditor.ImageDataService.getImageDataByUUID(uuid);
 */

(function($) {
  'use strict';

  // =========================================================================
  // Modifier Key Detection
  // =========================================================================

  /**
   * Get modifier key state from event
   * @param {Event} event - Mouse event
   * @returns {Object} { isCtrlOrCmd, isShift }
   */
  function getSelectionModifiers(event) {
    return {
      isCtrlOrCmd: event.ctrlKey || event.metaKey,
      isShift: event.shiftKey
    };
  }

  // =========================================================================
  // SelectionBadgeManager
  // =========================================================================

  /**
   * SelectionBadgeManager
   *
   * Manages a selection count badge next to a reference element.
   * Used by both picker and editor to show selection counts.
   *
   * @param {jQuery} $referenceElement - Element to position badge after
   * @param {string} badgeId - Unique ID for the badge element
   */
  function SelectionBadgeManager($referenceElement, badgeId) {
    this.$referenceElement = $referenceElement;
    this.badgeId = badgeId;
    this.$badge = null;
  }

  /**
   * Update badge with current count
   * Creates badge if it doesn't exist, removes if count is 0
   * @param {number} count - Number of selected items
   */
  SelectionBadgeManager.prototype.update = function(count) {
    if (count > 0) {
      if (!this.$badge) {
        this.$badge = $('<span>')
          .attr('id', this.badgeId)
          .addClass('badge badge-primary ml-2')
          .insertAfter(this.$referenceElement);
      }
      this.$badge.text(count + ' selected');
    } else {
      this.remove();
    }
  };

  /**
   * Remove the badge from DOM
   */
  SelectionBadgeManager.prototype.remove = function() {
    if (this.$badge) {
      this.$badge.remove();
      this.$badge = null;
    }
  };

  // =========================================================================
  // ImageSelectionCoordinator
  // =========================================================================

  /**
   * ImageSelectionCoordinator
   *
   * Coordinates image selection state across components.
   * Currently manages picker selections only.
   * Designed for extensibility if multi-component coordination is needed.
   */
  function ImageSelectionCoordinator() {
    this.pickerClearCallback = null;
  }

  /**
   * Register picker's clear selection callback
   * @param {Function} clearCallback - Function to call to clear picker selections
   */
  ImageSelectionCoordinator.prototype.registerPicker = function(clearCallback) {
    this.pickerClearCallback = clearCallback;
  };

  /**
   * Notify coordinator of picker selection state changes
   * Placeholder for future coordination needs
   * @param {boolean} hasSelections - Whether picker has selections
   */
  ImageSelectionCoordinator.prototype.notifyPickerSelection = function(hasSelections) {
    // Placeholder for future coordination needs
  };

  // Global singleton instance
  var imageSelectionCoordinator = new ImageSelectionCoordinator();

  // =========================================================================
  // ImageDataService
  // =========================================================================

  /**
   * ImageDataService
   *
   * Centralized service for retrieving image data from picker cards.
   * Decouples features from picker DOM structure.
   *
   * All image data lookups should go through this service to avoid
   * duplicated DOM queries and tight coupling to picker implementation.
   */
  var ImageDataService = {
    /**
     * Get complete image data for a given UUID
     * @param {string} uuid - Image UUID
     * @returns {Object|null} Image data object or null if not found
     *   {
     *     uuid: string,
     *     url: string,
     *     caption: string,
     *     inspectUrl: string
     *   }
     */
    getImageDataByUUID: function(uuid) {
      if (!uuid) {
        console.error('[ImageDataService] Cannot lookup image: missing UUID');
        return null;
      }

      // Find picker card with this UUID
      var $card = $(TtConst.JOURNAL_EDITOR_MULTI_IMAGE_CARD_SELECTOR + '[data-' + TtConst.IMAGE_UUID_DATA_ATTR + '="' + uuid + '"]');

      if ($card.length === 0) {
        console.warn('[ImageDataService] No picker card found for UUID:', uuid);
        return null;
      }

      // Extract all data from card in one pass
      var imageUuid = $card.data(TtConst.IMAGE_UUID_DATA_ATTR);
      var $img = $card.find('img');
      var url = $img.attr('src') || '';
      var caption = $img.attr('alt') || '';

      if (!imageUuid) {
        console.error('[ImageDataService] Picker card missing data-image-uuid for UUID:', uuid);
        return null;
      }

      // Build inspect URL from UUID using TtUrlPatterns
      var inspectUrl = Tt.buildImageInspectUrl(imageUuid);

      return {
        uuid: imageUuid,
        url: url,
        caption: caption,
        inspectUrl: inspectUrl
      };
    }
  };

  // =========================================================================
  // Export to Tt.JournalEditor namespace
  // =========================================================================
  window.Tt = window.Tt || {};
  window.Tt.JournalEditor = window.Tt.JournalEditor || {};
  window.Tt.JournalEditor.getSelectionModifiers = getSelectionModifiers;
  window.Tt.JournalEditor.SelectionBadgeManager = SelectionBadgeManager;
  window.Tt.JournalEditor.ImageSelectionCoordinator = ImageSelectionCoordinator;
  window.Tt.JournalEditor.imageSelectionCoordinator = imageSelectionCoordinator;
  window.Tt.JournalEditor.ImageDataService = ImageDataService;

})(jQuery);
