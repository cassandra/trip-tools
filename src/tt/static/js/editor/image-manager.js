/**
 * Image Manager for Journal Editor
 *
 * Manages image CRUD operations and usage tracking for the journal editor.
 * Extracted from journal-editor.js as part of modular refactoring (Phase 3).
 *
 * Features:
 * - Image element creation with proper attributes and structure
 * - Used image tracking (Map of UUID -> count for same image appearing multiple times)
 * - Image removal with usage tracking updates
 * - Image data lookup from picker cards
 *
 * Dependencies:
 * - jQuery ($)
 * - TtConst (server-injected constants)
 *
 * @namespace Tt.JournalEditor
 */

(function($) {
  'use strict';

  // Ensure namespace exists
  window.Tt = window.Tt || {};
  window.Tt.JournalEditor = window.Tt.JournalEditor || {};

  /**
   * EDITOR-ONLY TRANSIENT CONSTANTS
   * Imported from layout-manager.js (canonical source)
   */
  var EDITOR_TRANSIENT = Tt.JournalEditor.EDITOR_TRANSIENT;

  /**
   * ImageManager
   *
   * Manages image operations and usage tracking for the journal editor.
   *
   * @constructor
   * @param {Object} options - Configuration options
   * @param {jQuery} options.$editor - jQuery-wrapped contenteditable editor element
   * @param {Function} [options.onImageAdded] - Callback when image is added (uuid)
   * @param {Function} [options.onImageRemoved] - Callback when image is removed (uuid)
   * @param {Function} [options.onContentChange] - Callback when content changes
   * @param {Function} [options.refreshLayout] - Callback to refresh image layout
   * @param {Object} [options.imagePicker] - Reference to image picker for filtering
   */
  function ImageManager(options) {
    this.$editor = options.$editor;
    this.onImageAdded = options.onImageAdded || function() {};
    this.onImageRemoved = options.onImageRemoved || function() {};
    this.onContentChange = options.onContentChange || function() {};
    this.refreshLayout = options.refreshLayout || function() {};
    this.imagePicker = options.imagePicker || null;

    // Map of UUID -> count for tracking which images are used in editor
    // Supports same image appearing multiple times
    this.usedImageUUIDs = new Map();
  }

  // ============================================================
  // USAGE TRACKING
  // ============================================================

  /**
   * Initialize used image tracking from existing editor content
   * Parses all images in the editor and populates usedImageUUIDs Map with counts
   * Handles same image appearing multiple times by incrementing count
   */
  ImageManager.prototype.initializeUsedImages = function() {
    var self = this;
    this.usedImageUUIDs.clear();

    this.$editor.find(TtConst.JOURNAL_IMAGE_SELECTOR).each(function() {
      var $img = $(this);
      var uuid = $img.data(TtConst.UUID_DATA_ATTR);
      if (uuid) {
        var currentCount = self.usedImageUUIDs.get(uuid) || 0;
        self.usedImageUUIDs.set(uuid, currentCount + 1);
      }
    });
  };

  /**
   * Check if an image UUID is currently used in the editor
   * @param {string} uuid - Image UUID to check
   * @returns {boolean} True if image is used
   */
  ImageManager.prototype.isImageUsed = function(uuid) {
    return this.usedImageUUIDs.has(uuid);
  };

  /**
   * Get the usage count for an image
   * @param {string} uuid - Image UUID
   * @returns {number} Number of times image appears (0 if not used)
   */
  ImageManager.prototype.getImageUsageCount = function(uuid) {
    return this.usedImageUUIDs.get(uuid) || 0;
  };

  /**
   * Get all used image UUIDs
   * @returns {Set} Set of UUIDs
   */
  ImageManager.prototype.getUsedImageUUIDs = function() {
    return new Set(this.usedImageUUIDs.keys());
  };

  // ============================================================
  // IMAGE ELEMENT CREATION
  // ============================================================

  /**
   * Create image element with proper attributes
   * Also updates usage tracking and picker filter
   *
   * @param {string} uuid - Image UUID
   * @param {string} url - Image URL
   * @param {string} caption - Image caption/alt text
   * @param {string} layout - Layout type ('float-right' or 'full-width')
   * @returns {jQuery} jQuery-wrapped image wrapper element
   */
  ImageManager.prototype.createImageElement = function(uuid, url, caption, layout) {
    // Create the image element
    var $img = $('<img>', {
      'src': url,
      'alt': caption,
      'class': TtConst.JOURNAL_IMAGE_CLASS
    });
    $img.attr('data-' + TtConst.UUID_DATA_ATTR, uuid);
    $img.attr('draggable', true);  // Edit-time only, stripped before save

    // Create wrapper with layout attribute
    var $wrapper = $('<span>', {
      'class': TtConst.JOURNAL_IMAGE_WRAPPER_CLASS
    });
    $wrapper.attr('data-' + TtConst.LAYOUT_DATA_ATTR, layout);

    // Always create caption span - even if empty, for consistent editing experience
    // Empty captions are visible/clickable in editor (via CSS), hidden in travelog
    var $captionSpan = $('<span>', {
      'class': TtConst.TRIP_IMAGE_CAPTION_CLASS
    });
    if (caption && $.trim(caption).length > 0) {
      $captionSpan.text(caption);
    }

    // Create delete button (TRANSIENT - removed before save)
    var $deleteBtn = $('<button>', {
      'class': EDITOR_TRANSIENT.CSS_DELETE_BTN,
      'type': 'button',
      'title': 'Remove image',
      'text': '×'
    });

    // Assemble: wrapper contains image, caption, and delete button
    $wrapper.append($img);
    $wrapper.append($captionSpan);
    $wrapper.append($deleteBtn);

    // Track this image as used (for picker filtering)
    // Increment count to handle same image appearing multiple times
    var currentCount = this.usedImageUUIDs.get(uuid) || 0;
    this.usedImageUUIDs.set(uuid, currentCount + 1);

    // Notify that image was added
    this.onImageAdded(uuid);

    // Update picker filter if it exists
    if (this.imagePicker) {
      this.imagePicker.applyFilter(this.imagePicker.filterScope);
    }

    return $wrapper;
  };

  // ============================================================
  // IMAGE REMOVAL
  // ============================================================

  /**
   * Remove wrapper and update usage tracking
   *
   * This couples the DOM removal with data structure update to ensure
   * they always happen together. Does NOT trigger side effects (autosave,
   * filter updates) - caller is responsible for those.
   *
   * @param {jQuery} $wrapper - The image wrapper to remove
   * @returns {string|null} The UUID of the removed image, or null if none
   * @private
   */
  ImageManager.prototype._removeWrapperAndUpdateUsage = function($wrapper) {
    // Extract UUID before removing
    var $img = $wrapper.find(TtConst.JOURNAL_IMAGE_SELECTOR);
    var uuid = $img.data(TtConst.UUID_DATA_ATTR);

    // Remove wrapper from DOM
    $wrapper.remove();

    // Update usage tracking (always paired with DOM removal)
    // Decrement count to handle same image appearing multiple times
    if (uuid) {
      var currentCount = this.usedImageUUIDs.get(uuid) || 0;
      if (currentCount > 1) {
        this.usedImageUUIDs.set(uuid, currentCount - 1);
      } else {
        this.usedImageUUIDs.delete(uuid);
      }
    }

    return uuid;
  };

  /**
   * Remove image from editor
   * Handles DOM removal, usage tracking, picker filter update, and autosave trigger
   *
   * @param {jQuery} $img - The image element to remove
   */
  ImageManager.prototype.removeImage = function($img) {
    // Get wrapper and remove it (updates usage tracking)
    var $wrapper = $img.closest(TtConst.JOURNAL_IMAGE_WRAPPER_SELECTOR);
    var uuid = this._removeWrapperAndUpdateUsage($wrapper);

    // Notify that image was removed
    if (uuid) {
      this.onImageRemoved(uuid);
    }

    // Update picker filter if image was tracked
    if (uuid && this.imagePicker) {
      this.imagePicker.applyFilter(this.imagePicker.filterScope);
    }

    // Refresh layout (image removed) + trigger autosave
    this.refreshLayout();
    this.onContentChange();
  };

  // ============================================================
  // IMAGE DATA LOOKUP
  // ============================================================

  /**
   * Get image data object from UUID by looking up picker card
   * @param {string} uuid - Image UUID
   * @returns {Object|null} {uuid, url, caption} or null if not found
   */
  ImageManager.prototype.getImageDataFromUUID = function(uuid) {
    var $card = $(TtConst.JOURNAL_EDITOR_MULTI_IMAGE_CARD_SELECTOR + '[data-' + TtConst.IMAGE_UUID_DATA_ATTR + '="' + uuid + '"]');

    if (!$card.length) {
      return null;
    }

    return {
      uuid: uuid,
      url: $card.data(TtConst.IMAGE_MEDIA_URL_DATA_ATTR),
      caption: $card.data(TtConst.CAPTION_DATA_ATTR) || 'Untitled'
    };
  };

  // ============================================================
  // EXPORTS TO Tt.JournalEditor NAMESPACE
  // ============================================================

  Tt.JournalEditor.ImageManager = ImageManager;

  // Export internal constants for testing
  Tt.JournalEditor._IMAGE_MANAGER_TRANSIENT = EDITOR_TRANSIENT;

})(jQuery);
