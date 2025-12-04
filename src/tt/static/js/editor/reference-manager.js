/**
 * Reference Image Manager for Journal Editor
 *
 * Manages the reference (representative) image for a journal entry.
 * Extracted from journal-editor.js as part of modular refactoring.
 *
 * Features:
 * - Reference image state tracking (current UUID)
 * - Drag-and-drop to set reference image
 * - Clear button to remove reference image
 * - Double-click to open image inspector
 * - Drop zone visual feedback
 *
 * @namespace Tt.JournalEditor
 */

(function($) {
  'use strict';

  // Ensure namespace exists
  window.Tt = window.Tt || {};
  window.Tt.JournalEditor = window.Tt.JournalEditor || {};

  /**
   * TRANSIENT CSS CLASS
   * Used for drop zone highlighting (editor-only, never saved)
   */
  var CSS_DROP_ZONE_ACTIVE = 'drop-zone-active';

  /**
   * ReferenceImageManager
   *
   * Manages reference image state and UI interactions.
   *
   * @constructor
   * @param {Object} options - Configuration options
   * @param {jQuery} options.$container - jQuery-wrapped reference image container
   * @param {string|null} options.initialUuid - Initial reference image UUID (null if none)
   * @param {Function} options.onContentChange - Callback when reference image changes (triggers autosave)
   * @param {Function} options.getDraggedImageData - Function that returns dragged image data
   * @param {Function} options.getImageDataByUUID - Function to lookup complete image data by UUID
   * @param {Function} options.setDragState - Function to update drag state (draggedElement, dragSource)
   * @param {Function} options.getDragSource - Function to get current drag source
   * @param {Object} options.DRAG_SOURCE - Drag source constants (PICKER, EDITOR, REFERENCE)
   */
  function ReferenceImageManager(options) {
    this.$container = options.$container;
    this.currentUuid = options.initialUuid || null;
    this.onContentChange = options.onContentChange;
    this.getDraggedImageData = options.getDraggedImageData;
    this.getImageDataByUUID = options.getImageDataByUUID;
    this.setDragState = options.setDragState;
    this.getDragSource = options.getDragSource;
    this.DRAG_SOURCE = options.DRAG_SOURCE;

    // Cache selectors from TtConst
    this.SELECTORS = {
      PLACEHOLDER: TtConst.JOURNAL_REFERENCE_IMAGE_PLACEHOLDER_SELECTOR,
      PREVIEW: TtConst.JOURNAL_REFERENCE_IMAGE_PREVIEW_SELECTOR,
      CLEAR: TtConst.JOURNAL_REFERENCE_IMAGE_CLEAR_SELECTOR,
      THUMBNAIL: TtConst.JOURNAL_REFERENCE_IMAGE_THUMBNAIL_SELECTOR,
      CONTAINER: TtConst.JOURNAL_REFERENCE_IMAGE_CONTAINER_SELECTOR
    };

    this.DATA_ATTRS = {
      UUID: TtConst.REFERENCE_IMAGE_UUID_DATA_ATTR
    };
  }

  /**
   * Initialize reference image event handlers
   * Sets up drag-drop, clear button, and double-click behavior
   */
  ReferenceImageManager.prototype.setup = function() {
    var self = this;

    if (!this.$container || !this.$container.length) {
      return;
    }

    // Setup drag-over handler
    this.$container.on('dragover', function(e) {
      e.preventDefault();
      e.stopPropagation();

      // Set dropEffect based on drag source
      var dragSource = self.getDragSource();
      if (dragSource === self.DRAG_SOURCE.EDITOR) {
        e.originalEvent.dataTransfer.dropEffect = 'move';
      } else {
        e.originalEvent.dataTransfer.dropEffect = 'copy';
      }

      if (self.shouldShowDropZone()) {
        self.setDropZoneVisible(true);
      }
    });

    // Setup drag-leave handler
    this.$container.on('dragleave', function(e) {
      // Only remove if we're leaving the container completely
      if (!$(e.relatedTarget).closest(self.SELECTORS.CONTAINER).length) {
        self.setDropZoneVisible(false);
      }
    });

    // Setup drop handler
    this.$container.on('drop', function(e) {
      e.preventDefault();
      e.stopPropagation();

      self.setDropZoneVisible(false);

      try {
        var imageData = self.getDraggedImageData();
        if (imageData) {
          self.setImage(imageData);
        } else {
          console.warn('[ReferenceImageManager] Drop failed: no image data available');
        }
      } catch (error) {
        console.error('[ReferenceImageManager] Error setting reference image:', error);
        // Show user-friendly notification if toast system is available
        if (typeof Tt !== 'undefined' && Tt.showToast) {
          Tt.showToast('error', 'Could not set reference image. Please try again.');
        }
      } finally {
        // Always clean up drag state, even if error occurred
        self.setDragState(null, null);
      }
    });

    // Setup clear button click
    this.$container.on('click', this.SELECTORS.CLEAR, function(e) {
      e.preventDefault();
      e.stopPropagation();
      self.clearImage();
    });

    // Setup double-click to open inspector
    this.$container.on('dblclick', this.SELECTORS.THUMBNAIL, function(e) {
      e.preventDefault();
      // Get UUID from container (thumbnail doesn't store it)
      var uuid = self.$container.data(self.DATA_ATTRS.UUID);
      if (uuid && typeof AN !== 'undefined' && AN.get) {
        var inspectUrl = Tt.buildImageInspectUrl(uuid);
        AN.get(inspectUrl);
      }
    });

    // Setup reference image dragging (for drag-to-remove)
    this.$container.on('dragstart', this.SELECTORS.THUMBNAIL, function(e) {
      self.setDragState(this, self.DRAG_SOURCE.REFERENCE);

      e.originalEvent.dataTransfer.effectAllowed = 'move';
      e.originalEvent.dataTransfer.setData('text/plain', '');
    });

    this.$container.on('dragend', this.SELECTORS.THUMBNAIL, function(e) {
      // Visual cleanup happens in drop handlers
      self.setDragState(null, null);
    });
  };

  /**
   * Get current reference image UUID
   * @returns {string|null} Current UUID or null if none set
   */
  ReferenceImageManager.prototype.getUuid = function() {
    return this.currentUuid;
  };

  /**
   * Set reference image from image data
   * @param {Object} imageData - {uuid, thumbnailUrl, caption}
   */
  ReferenceImageManager.prototype.setImage = function(imageData) {
    // Use lookup function to get complete data if needed (for thumbnailUrl/caption)
    var completeData = imageData;
    if (!imageData.thumbnailUrl && this.getImageDataByUUID) {
      completeData = this.getImageDataByUUID(imageData.uuid);
      if (!completeData) {
        console.error('[ReferenceImageManager] Cannot set reference image: lookup failed for UUID', imageData.uuid);
        return;
      }
    }

    // Update state
    this.currentUuid = completeData.uuid;
    this.$container.data(this.DATA_ATTRS.UUID, this.currentUuid);

    // Update preview image attributes
    var $preview = this.$container.find(this.SELECTORS.PREVIEW);
    var $placeholder = this.$container.find(this.SELECTORS.PLACEHOLDER);
    var $img = $preview.find(this.SELECTORS.THUMBNAIL);

    $img.attr('src', completeData.thumbnailUrl);
    $img.attr('alt', completeData.caption || 'Reference');

    // Show preview, hide placeholder
    $placeholder.addClass('d-none');
    $preview.removeClass('d-none');

    // Trigger autosave
    if (this.onContentChange) {
      this.onContentChange();
    }
  };

  /**
   * Clear reference image
   */
  ReferenceImageManager.prototype.clearImage = function() {
    // Update state - set to null (matches title/date/timezone pattern)
    this.currentUuid = null;
    this.$container.data(this.DATA_ATTRS.UUID, '');

    // Hide preview, show placeholder
    this.$container.find(this.SELECTORS.PREVIEW).addClass('d-none');
    this.$container.find(this.SELECTORS.PLACEHOLDER).removeClass('d-none');

    // Trigger autosave (will send empty string to backend to clear the field)
    if (this.onContentChange) {
      this.onContentChange();
    }
  };

  /**
   * Check if drop zone should highlight
   * Only for single-image drags, not multi-select
   * @returns {boolean}
   */
  ReferenceImageManager.prototype.shouldShowDropZone = function() {
    return this.getDraggedImageData() !== null;
  };

  /**
   * Set visibility of drop zone highlighting
   * @param {boolean} visible - true to show drop zone, false to hide
   */
  ReferenceImageManager.prototype.setDropZoneVisible = function(visible) {
    if (!this.$container || !this.$container.length) {
      return;
    }

    var $target = this.$container.find(
      this.SELECTORS.PLACEHOLDER + ', ' + this.SELECTORS.PREVIEW
    );

    if (visible) {
      $target.addClass(CSS_DROP_ZONE_ACTIVE);
    } else {
      $target.removeClass(CSS_DROP_ZONE_ACTIVE);
    }
  };

  /**
   * Check if container exists
   * @returns {boolean}
   */
  ReferenceImageManager.prototype.hasContainer = function() {
    return this.$container && this.$container.length > 0;
  };

  // ============================================================
  // EXPORTS TO Tt.JournalEditor NAMESPACE
  // ============================================================

  Tt.JournalEditor.ReferenceImageManager = ReferenceImageManager;

})(jQuery);
