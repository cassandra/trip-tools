/**
 * Drag and Drop Manager for Journal Editor
 *
 * Manages all drag-and-drop operations for the journal editor including:
 * - Dragging images from picker to editor (insertion)
 * - Dragging images within editor (reordering)
 * - Dragging images from editor to picker (removal)
 * - Drop zone visualization and management
 *
 * Extracted from journal-editor.js as part of modular refactoring (Phase 3).
 *
 * Dependencies:
 * - jQuery ($)
 * - TtConst (server-injected constants)
 * - Tt.JournalEditor.HTML_STRUCTURE (from html-normalization.js)
 *
 * @namespace Tt.JournalEditor
 */

(function($) {
  'use strict';

  // Ensure namespace exists
  window.Tt = window.Tt || {};
  window.Tt.JournalEditor = window.Tt.JournalEditor || {};

  // =========================================================================
  // IMPORTS FROM OTHER MODULES
  // =========================================================================

  /**
   * Reference to HTML_STRUCTURE constants from html-normalization.js
   */
  var HTML_STRUCTURE = Tt.JournalEditor.HTML_STRUCTURE;

  /**
   * EDITOR-ONLY TRANSIENT CONSTANTS
   * Imported from layout-manager.js (canonical source)
   */
  var EDITOR_TRANSIENT = Tt.JournalEditor.EDITOR_TRANSIENT;

  // =========================================================================
  // CONSTANTS DEFINED IN THIS MODULE (exported below)
  // =========================================================================

  /**
   * DRAG SOURCE IDENTIFIERS
   * Identifies where a drag operation originated from.
   */
  var DRAG_SOURCE = {
    PICKER: 'picker',
    EDITOR: 'editor',
    REFERENCE: 'reference'
  };

  /**
   * LAYOUT VALUES
   * These are the actual string values for data-layout attribute.
   */
  var LAYOUT_VALUES = {
    FLOAT_RIGHT: 'float-right',
    FULL_WIDTH: 'full-width'
  };

  /**
   * DragDropManager
   *
   * Manages all drag-and-drop operations for images in the journal editor.
   *
   * @constructor
   * @param {Object} options - Configuration options
   * @param {jQuery} options.$editor - jQuery-wrapped contenteditable editor element
   * @param {Object} options.imageManager - ImageManager instance for image operations
   * @param {Object} [options.imagePicker] - Image picker instance (for multi-select support)
   * @param {Object} [options.referenceImageManager] - Reference image manager instance
   * @param {Function} options.refreshImageLayout - Callback to refresh image layout
   * @param {Function} options.handleContentChange - Callback to trigger autosave
   * @param {Function} options.clearReferenceImage - Callback to clear reference image
   */
  function DragDropManager(options) {
    this.$editor = options.$editor;
    this.imageManager = options.imageManager;
    this.imagePicker = options.imagePicker || null;
    this.referenceImageManager = options.referenceImageManager || null;
    this.refreshImageLayout = options.refreshImageLayout || function() {};
    this.handleContentChange = options.handleContentChange || function() {};
    this.clearReferenceImage = options.clearReferenceImage || function() {};

    // Drag state
    this.draggedElement = null;
    this.dragSource = null;
  }

  // ============================================================
  // SETUP METHODS
  // ============================================================

  /**
   * Setup all drag-and-drop handlers
   */
  DragDropManager.prototype.setup = function() {
    this.setupPickerDragDrop();
    this.setupEditorDragDrop();
    this.setupImageReordering();
    this.setupPickerAsDropTarget();
    this.setupEscapeKeyCancel();
  };

  /**
   * Setup drag-and-drop from picker to editor
   */
  DragDropManager.prototype.setupPickerDragDrop = function() {
    var self = this;

    // Handle dragstart from picker
    $(document).on('dragstart', TtConst.JOURNAL_EDITOR_MULTI_IMAGE_CARD_SELECTOR, function(e) {
      self.draggedElement = this;
      self.dragSource = DRAG_SOURCE.PICKER;

      // Update visual feedback
      self.updateDraggingVisuals(true);

      // Set drag data
      e.originalEvent.dataTransfer.effectAllowed = 'copy';
      e.originalEvent.dataTransfer.setData('text/plain', '');
    });

    // Handle dragend from picker
    $(document).on('dragend', TtConst.JOURNAL_EDITOR_MULTI_IMAGE_CARD_SELECTOR, function(e) {
      // Visual cleanup only - state cleanup happens in drop handlers
      self.updateDraggingVisuals(false);
      self.clearDropZones();
    });
  };

  /**
   * Setup editor as drop target
   */
  DragDropManager.prototype.setupEditorDragDrop = function() {
    var self = this;

    // Editor drag events
    this.$editor.on('dragover', function(e) {
      e.preventDefault();

      // Set appropriate drop effect based on drag source
      if (self.dragSource === DRAG_SOURCE.EDITOR) {
        e.originalEvent.dataTransfer.dropEffect = 'move';
      } else {
        e.originalEvent.dataTransfer.dropEffect = 'copy';
      }

      // Show drop zones for both picker and editor drags
      if (self.dragSource === DRAG_SOURCE.PICKER || self.dragSource === DRAG_SOURCE.EDITOR) {
        self.showDropZones(e);
      }
    });

    this.$editor.on('dragenter', function(e) {
      if (self.dragSource === DRAG_SOURCE.PICKER || self.dragSource === DRAG_SOURCE.EDITOR) {
        $(this).addClass(EDITOR_TRANSIENT.CSS_DRAG_OVER);
      }
    });

    this.$editor.on('dragleave', function(e) {
      // Only remove if we're leaving the editor completely
      if (!$(e.relatedTarget).closest(TtConst.JOURNAL_EDITOR_SELECTOR).length) {
        $(this).removeClass(EDITOR_TRANSIENT.CSS_DRAG_OVER);
        self.clearDropZones();
      }
    });

    this.$editor.on('drop', function(e) {
      // Check if drop is actually on reference container - if so, let it handle the drop
      var $target = $(e.target);
      if ($target.closest(TtConst.JOURNAL_REFERENCE_IMAGE_CONTAINER_SELECTOR).length) {
        return; // Don't preventDefault, don't stopPropagation - let reference handler get it
      }

      e.preventDefault();
      e.stopPropagation();

      $(this).removeClass(EDITOR_TRANSIENT.CSS_DRAG_OVER);

      if (self.dragSource === DRAG_SOURCE.PICKER && self.draggedElement) {
        self.handleImageDrop(e);
      } else if (self.dragSource === DRAG_SOURCE.EDITOR && self.draggedElement) {
        self.handleImageReorder(e);
      }

      self.clearDropZones();

      // Clean up drag state after processing
      self.draggedElement = null;
      self.dragSource = null;
    });
  };

  /**
   * Setup image reordering within editor
   */
  DragDropManager.prototype.setupImageReordering = function() {
    var self = this;

    // Handle dragstart for images already in editor
    this.$editor.on('dragstart', TtConst.JOURNAL_IMAGE_SELECTOR, function(e) {
      var $img = $(this);
      var $wrapper = $img.closest(TtConst.JOURNAL_IMAGE_WRAPPER_SELECTOR);

      self.draggedElement = $wrapper[0]; // Store wrapper, not image
      self.dragSource = DRAG_SOURCE.EDITOR;

      // Update visual feedback
      self.updateDraggingVisuals(true);

      e.originalEvent.dataTransfer.effectAllowed = 'move';
      e.originalEvent.dataTransfer.setData('text/plain', '');
    });

    // Handle dragend for images in editor
    this.$editor.on('dragend', TtConst.JOURNAL_IMAGE_SELECTOR, function(e) {
      // Visual cleanup only - state cleanup happens in drop handlers
      self.updateDraggingVisuals(false);
      self.clearDropZones();
    });
  };

  /**
   * Setup picker panel as drop target for removal operations
   */
  DragDropManager.prototype.setupPickerAsDropTarget = function() {
    var self = this;

    var $pickerGallery = $(TtConst.JOURNAL_EDITOR_MULTI_IMAGE_GALLERY_SELECTOR);
    if (!$pickerGallery.length) {
      return;
    }

    $pickerGallery.on('dragover', function(e) {
      // Allow drops from editor or reference (removal), not from picker (no-op)
      if (self.dragSource === DRAG_SOURCE.EDITOR || self.dragSource === DRAG_SOURCE.REFERENCE) {
        e.preventDefault();
        e.originalEvent.dataTransfer.dropEffect = 'move';
        $(this).addClass('drop-target-active');
      }
    });

    $pickerGallery.on('dragleave', function(e) {
      // Only remove if we're leaving the gallery completely
      if (!$(e.relatedTarget).closest(TtConst.JOURNAL_EDITOR_MULTI_IMAGE_GALLERY_SELECTOR).length) {
        $(this).removeClass('drop-target-active');
      }
    });

    $pickerGallery.on('drop', function(e) {
      if (self.dragSource === DRAG_SOURCE.EDITOR || self.dragSource === DRAG_SOURCE.REFERENCE) {
        e.preventDefault();
        $(this).removeClass('drop-target-active');
        self.handleImageRemovalDrop(e);
      }
    });
  };

  /**
   * Setup Escape key to cancel drag operations
   */
  DragDropManager.prototype.setupEscapeKeyCancel = function() {
    var self = this;

    $(document).on('keydown', function(e) {
      if (e.key === 'Escape' && (self.draggedElement || self.dragSource)) {
        self.updateDraggingVisuals(false);
        self.clearDropZones();
        self.draggedElement = null;
        self.dragSource = null;
      }
    });
  };

  // ============================================================
  // DROP ZONE MANAGEMENT
  // ============================================================

  /**
   * Show drop zones based on mouse position
   */
  DragDropManager.prototype.showDropZones = function(e) {
    var $target = $(e.target);
    var $textBlock = $target.closest(HTML_STRUCTURE.TEXT_BLOCK_SELECTOR);
    var $imageWrapper = $target.closest(TtConst.JOURNAL_IMAGE_WRAPPER_FULL_SELECTOR);

    // Clear existing indicators
    this.clearDropZones();

    if ($textBlock.length && $textBlock.parent().is(this.$editor)) {
      // Mouse is over a text block (p or div) - show drop zone
      $textBlock.addClass(EDITOR_TRANSIENT.CSS_DROP_ZONE_ACTIVE);
    } else if ($imageWrapper.length && $imageWrapper.closest(this.$editor).length) {
      // Mouse is over a full-width image - highlight it to show insertion point
      $imageWrapper.addClass(EDITOR_TRANSIENT.CSS_DROP_ZONE_ACTIVE);
    } else {
      // Mouse is between blocks - show between indicator
      this._showBetweenIndicator(e);
    }
  };

  /**
   * Show indicator between blocks based on mouse position
   * @private
   */
  DragDropManager.prototype._showBetweenIndicator = function(e) {
    var mouseY = e.clientY;
    var $children = this.$editor.children(HTML_STRUCTURE.TEXT_BLOCK_SELECTOR + ', div.' + TtConst.JOURNAL_CONTENT_BLOCK_CLASS + ', h1, h2, h3, h4, h5, h6');

    var foundDropZone = false;
    var self = this;

    $children.each(function() {
      var rect = this.getBoundingClientRect();
      var betweenTop = rect.top - 20;
      var betweenBottom = rect.top + 20;

      if (mouseY >= betweenTop && mouseY <= betweenBottom) {
        var $indicator = $('<div class="' + EDITOR_TRANSIENT.CSS_DROP_ZONE_BETWEEN + '"></div>');
        $(this).before($indicator);
        foundDropZone = true;
        return false;
      }
    });

    // Check if mouse is below the last element (for appending at end)
    if (!foundDropZone && $children.length > 0) {
      var $lastChild = $children.last();
      var lastRect = $lastChild[0].getBoundingClientRect();
      var afterLastTop = lastRect.bottom - 20;

      if (mouseY >= afterLastTop) {
        var $indicator = $('<div class="' + EDITOR_TRANSIENT.CSS_DROP_ZONE_BETWEEN + '"></div>');
        $lastChild.after($indicator);
      }
    }
  };

  /**
   * Clear drop zone indicators
   */
  DragDropManager.prototype.clearDropZones = function() {
    this.$editor.find(HTML_STRUCTURE.TEXT_BLOCK_SELECTOR).removeClass(EDITOR_TRANSIENT.CSS_DROP_ZONE_ACTIVE);
    this.$editor.find(TtConst.JOURNAL_IMAGE_WRAPPER_SELECTOR).removeClass(EDITOR_TRANSIENT.CSS_DROP_ZONE_ACTIVE);
    this.$editor.find('.' + EDITOR_TRANSIENT.CSS_DROP_ZONE_BETWEEN).remove();
  };

  // ============================================================
  // DROP HANDLERS
  // ============================================================

  /**
   * Handle image drop into editor from picker (supports multi-image drop)
   */
  DragDropManager.prototype.handleImageDrop = function(e) {
    if (!this.draggedElement) {
      return;
    }

    // Get images to insert (1 or many)
    var imagesToInsert = this.getPickerImagesToInsert();
    if (imagesToInsert.length === 0) {
      return;
    }

    // Determine drop layout and target
    var dropInfo = this._determineDropTarget(e);
    var layout = dropInfo.layout;
    var $insertTarget = dropInfo.$insertTarget;
    var insertAfterTarget = dropInfo.insertAfterTarget;

    // Insert each image
    var $lastInserted = null;
    for (var i = 0; i < imagesToInsert.length; i++) {
      var imageData = imagesToInsert[i];

      // Create wrapped image element
      var $wrappedImage = this.imageManager.createImageElement(
        imageData.uuid,
        imageData.url,
        imageData.caption,
        layout,
        imageData.inspectUrl
      );

      // Insert the wrapped image
      $lastInserted = this._insertImage($wrappedImage, layout, $insertTarget, insertAfterTarget, $lastInserted);
    }

    // Enforce 2-image limit per paragraph
    if (layout === LAYOUT_VALUES.FLOAT_RIGHT) {
      this._enforceFloatLimit($insertTarget);
    }

    // Refresh layout + trigger autosave
    this.refreshImageLayout();
    this.handleContentChange();

    // Clear picker selections if multiple images were inserted
    if (this.imagePicker && imagesToInsert.length > 1) {
      this.imagePicker.clearAllSelections();
    }
  };

  /**
   * Handle image reordering within editor
   */
  DragDropManager.prototype.handleImageReorder = function(e) {
    if (!this.draggedElement) {
      return;
    }

    // Get wrappers to move
    var wrappersToMove = this.getEditorWrappersToMove();
    if (wrappersToMove.length === 0) {
      return;
    }

    // Detach all wrappers first to prevent DOM issues
    var wrappersData = this._detachWrappers(wrappersToMove);

    // Determine target layout and position
    var reorderInfo = this._determineReorderTarget(e);
    var newLayout = reorderInfo.newLayout;
    var $insertTarget = reorderInfo.$insertTarget;
    var insertMode = reorderInfo.insertMode;

    // Insert each wrapper
    var $lastMoved = null;
    for (var i = 0; i < wrappersData.length; i++) {
      var wrapperData = wrappersData[i];
      var $wrapper = wrapperData.$wrapper;

      // Insert wrapper at target
      $lastMoved = this._insertMovedWrapper($wrapper, $insertTarget, insertMode, $lastMoved);

      // Update layout attribute if changed
      if (newLayout !== wrapperData.oldLayout) {
        $wrapper.attr('data-' + TtConst.LAYOUT_DATA_ATTR, newLayout);
      }
    }

    // Enforce 2-image limit per paragraph
    if (insertMode === 'prepend-paragraph') {
      this._enforceFloatLimit($insertTarget);
    }

    // Refresh layout + trigger autosave
    this.refreshImageLayout();
    this.handleContentChange();
  };

  /**
   * Handle dropping editor or reference images onto picker panel (removal)
   */
  DragDropManager.prototype.handleImageRemovalDrop = function(e) {
    if (!this.draggedElement) {
      return;
    }

    if (this.dragSource === DRAG_SOURCE.EDITOR) {
      // Remove editor images
      var wrappersToRemove = this.getEditorWrappersToMove();
      for (var i = 0; i < wrappersToRemove.length; i++) {
        var $wrapper = wrappersToRemove[i];
        var $img = $wrapper.find(TtConst.JOURNAL_IMAGE_SELECTOR);
        this.imageManager.removeImage($img);
      }
    } else if (this.dragSource === DRAG_SOURCE.REFERENCE) {
      // Clear reference image
      this.clearReferenceImage();
    }

    // Clean up drag state
    this.draggedElement = null;
    this.dragSource = null;
  };

  // ============================================================
  // HELPER METHODS
  // ============================================================

  /**
   * Determine drop target and layout from drop event
   * @private
   */
  DragDropManager.prototype._determineDropTarget = function(e) {
    var $target = $(e.target);
    var $textBlock = $target.closest(HTML_STRUCTURE.TEXT_BLOCK_SELECTOR);
    var $imageWrapper = $target.closest(TtConst.JOURNAL_IMAGE_WRAPPER_FULL_SELECTOR);

    var layout = LAYOUT_VALUES.FULL_WIDTH;
    var $insertTarget = null;
    var insertAfterTarget = false;

    if ($textBlock.length && $textBlock.parent().is(this.$editor)) {
      // Dropped into a text block (p or div) - float-right layout
      layout = LAYOUT_VALUES.FLOAT_RIGHT;
      $insertTarget = $textBlock;
    } else if ($imageWrapper.length && $imageWrapper.closest(this.$editor).length) {
      // Dropped onto an existing full-width image - insert after it
      layout = LAYOUT_VALUES.FULL_WIDTH;
      $insertTarget = $imageWrapper;
    } else {
      // Dropped between blocks - full-width layout
      layout = LAYOUT_VALUES.FULL_WIDTH;
      var result = this._findClosestBlock(e);
      $insertTarget = result.$insertTarget;
      insertAfterTarget = result.insertAfterTarget;
    }

    return {
      layout: layout,
      $insertTarget: $insertTarget,
      insertAfterTarget: insertAfterTarget
    };
  };

  /**
   * Find the closest block element to insert near
   * @private
   */
  DragDropManager.prototype._findClosestBlock = function(e) {
    var mouseY = e.clientY;
    var $children = this.$editor.children(HTML_STRUCTURE.TEXT_BLOCK_SELECTOR + ', div.' + TtConst.JOURNAL_CONTENT_BLOCK_CLASS + ', h1, h2, h3, h4, h5, h6');
    var closestElement = null;
    var minDistance = Infinity;
    var insertAfterTarget = false;

    $children.each(function() {
      var rect = this.getBoundingClientRect();
      var distance = Math.abs(rect.top - mouseY);

      if (distance < minDistance) {
        minDistance = distance;
        closestElement = this;
      }
    });

    var $insertTarget = $(closestElement);

    // Check if dropping after the last element
    if ($children.length > 0) {
      var lastChild = $children.get($children.length - 1);
      var lastRect = lastChild.getBoundingClientRect();
      if (mouseY > lastRect.bottom - 20) {
        insertAfterTarget = true;
        $insertTarget = $(lastChild);
      }
    }

    return {
      $insertTarget: $insertTarget,
      insertAfterTarget: insertAfterTarget
    };
  };

  /**
   * Insert an image element at the appropriate position
   * @private
   */
  DragDropManager.prototype._insertImage = function($wrappedImage, layout, $insertTarget, insertAfterTarget, $lastInserted) {
    if (!$lastInserted) {
      // First insertion - use original target logic
      if (layout === LAYOUT_VALUES.FLOAT_RIGHT) {
        // Insert at beginning of paragraph for float-right
        $insertTarget.prepend($wrappedImage);
      } else if ($insertTarget.is(TtConst.JOURNAL_IMAGE_WRAPPER_FULL_SELECTOR)) {
        // Insert after the target image wrapper
        $insertTarget.after($wrappedImage);
      } else if (insertAfterTarget) {
        // Insert after the last element
        $insertTarget.after($wrappedImage);
      } else {
        // Insert before the target element for full-width
        $insertTarget.before($wrappedImage);
      }
    } else {
      // Subsequent insertions - chain after last inserted
      if (layout === LAYOUT_VALUES.FLOAT_RIGHT) {
        $insertTarget.prepend($wrappedImage);
      } else {
        $lastInserted.after($wrappedImage);
      }
    }

    return $wrappedImage;
  };

  /**
   * Determine reorder target and layout from drop event
   * @private
   */
  DragDropManager.prototype._determineReorderTarget = function(e) {
    var $target = $(e.target);
    var $textBlock = $target.closest(HTML_STRUCTURE.TEXT_BLOCK_SELECTOR);
    var newLayout = LAYOUT_VALUES.FULL_WIDTH;
    var $insertTarget = null;
    var insertMode = null;

    if ($textBlock.length && $textBlock.parent().is(this.$editor)) {
      // Dropped into a text block
      newLayout = LAYOUT_VALUES.FLOAT_RIGHT;
      $insertTarget = $textBlock;
      insertMode = 'prepend-paragraph';
    } else {
      // Dropped outside text blocks
      newLayout = LAYOUT_VALUES.FULL_WIDTH;

      var $targetImageWrapper = $target.closest(TtConst.JOURNAL_IMAGE_WRAPPER_FULL_SELECTOR);

      if ($targetImageWrapper.length && $targetImageWrapper.closest(this.$editor).length) {
        $insertTarget = $targetImageWrapper;
        insertMode = 'after-wrapper';
      } else {
        var result = this._findClosestBlockForReorder(e);
        $insertTarget = result.$insertTarget;
        insertMode = result.insertMode;
      }
    }

    return {
      newLayout: newLayout,
      $insertTarget: $insertTarget,
      insertMode: insertMode
    };
  };

  /**
   * Find the closest block element for reorder operation
   * @private
   */
  DragDropManager.prototype._findClosestBlockForReorder = function(e) {
    var mouseY = e.clientY;
    var $children = this.$editor.children(HTML_STRUCTURE.TEXT_BLOCK_SELECTOR + ', div.' + TtConst.JOURNAL_CONTENT_BLOCK_CLASS + ', h1, h2, h3, h4, h5, h6');
    var closestElement = null;
    var minDistance = Infinity;

    $children.each(function() {
      var rect = this.getBoundingClientRect();
      var distance = Math.abs(rect.top - mouseY);

      if (distance < minDistance) {
        minDistance = distance;
        closestElement = this;
      }
    });

    if (closestElement) {
      return {
        $insertTarget: $(closestElement),
        insertMode: 'before-element'
      };
    } else {
      return {
        $insertTarget: this.$editor,
        insertMode: 'append-editor'
      };
    }
  };

  /**
   * Detach wrappers from DOM and store their data
   * @private
   */
  DragDropManager.prototype._detachWrappers = function(wrappersToMove) {
    var wrappersData = [];
    for (var i = 0; i < wrappersToMove.length; i++) {
      var $wrapper = wrappersToMove[i];
      var oldLayout = $wrapper.data(TtConst.LAYOUT_DATA_ATTR);
      wrappersData.push({
        element: $wrapper.get(0),
        $wrapper: $wrapper,
        oldLayout: oldLayout
      });
      $wrapper.detach();
    }
    return wrappersData;
  };

  /**
   * Insert a moved wrapper at the appropriate position
   * @private
   */
  DragDropManager.prototype._insertMovedWrapper = function($wrapper, $insertTarget, insertMode, $lastMoved) {
    if (!$lastMoved) {
      // First move - use original target logic
      if (insertMode === 'prepend-paragraph') {
        $insertTarget.prepend($wrapper);
      } else if (insertMode === 'after-wrapper') {
        $insertTarget.after($wrapper);
      } else if (insertMode === 'before-element') {
        $insertTarget.before($wrapper);
      } else if (insertMode === 'append-editor') {
        $insertTarget.append($wrapper);
      }
    } else {
      // Subsequent moves - chain after last moved
      if (insertMode === 'prepend-paragraph') {
        $insertTarget.prepend($wrapper);
      } else {
        $lastMoved.after($wrapper);
      }
    }

    return $wrapper;
  };

  /**
   * Enforce 2-image limit per paragraph
   * @private
   */
  DragDropManager.prototype._enforceFloatLimit = function($paragraph) {
    var existingWrappers = $paragraph.find(TtConst.JOURNAL_IMAGE_WRAPPER_FLOAT_SELECTOR);
    var evicted = false;

    while (existingWrappers.length > 2) {
      // Remove rightmost (last) wrapper - FIFO eviction
      this.imageManager._removeWrapperAndUpdateUsage(existingWrappers.last());
      existingWrappers = $paragraph.find(TtConst.JOURNAL_IMAGE_WRAPPER_FLOAT_SELECTOR);
      evicted = true;
    }

    // Update picker filter once if any images were evicted
    if (evicted && this.imagePicker) {
      this.imagePicker.applyFilter(this.imagePicker.filterScope);
    }
  };

  // ============================================================
  // IMAGE DATA RETRIEVAL
  // ============================================================

  /**
   * Get picker images to insert (for multi-image drag-and-drop)
   * @returns {Array} Array of image data objects: [{uuid, url, caption}, ...]
   */
  DragDropManager.prototype.getPickerImagesToInsert = function() {
    if (!this.draggedElement || !this.imagePicker) {
      return [];
    }

    var self = this;
    var $draggedCard = $(this.draggedElement);
    var draggedUuid = $draggedCard.data(TtConst.IMAGE_UUID_DATA_ATTR);

    // Check if dragged card is part of selection
    var isDraggedSelected = this.imagePicker.selectedImages.has(draggedUuid);

    var imagesToInsert = [];

    if (isDraggedSelected && this.imagePicker.selectedImages.size > 1) {
      // Multi-image insert: get all selected cards in DOM order
      var selectedUuids = this.imagePicker.selectedImages;
      $(TtConst.JOURNAL_EDITOR_MULTI_IMAGE_CARD_SELECTOR).each(function() {
        var $card = $(this);
        var uuid = $card.data(TtConst.IMAGE_UUID_DATA_ATTR);
        if (selectedUuids.has(uuid)) {
          var imageData = self.imageManager.getImageDataFromUUID(uuid);
          if (imageData) {
            imagesToInsert.push(imageData);
          }
        }
      });
    } else {
      // Single-image insert: just the dragged card
      var imageData = this.imageManager.getImageDataFromUUID(draggedUuid);
      if (imageData) {
        imagesToInsert.push(imageData);
      }
    }

    return imagesToInsert;
  };

  /**
   * Get image data for currently dragged image(s)
   * Returns single image data or null (for reference area use - multi-select not allowed)
   * @returns {Object|null} {uuid, url, caption} or null if multi-select or no drag
   */
  DragDropManager.prototype.getDraggedImageData = function() {
    if (!this.draggedElement || !this.dragSource) {
      return null;
    }

    if (this.dragSource === DRAG_SOURCE.PICKER) {
      var imagesToInsert = this.getPickerImagesToInsert();
      return (imagesToInsert.length === 1) ? imagesToInsert[0] : null;
    } else if (this.dragSource === DRAG_SOURCE.EDITOR) {
      var wrappersToMove = this.getEditorWrappersToMove();
      if (wrappersToMove.length !== 1) {
        return null;
      }

      var $wrapper = wrappersToMove[0];
      var $img = $wrapper.find(TtConst.JOURNAL_IMAGE_SELECTOR);
      var uuid = $img.data(TtConst.UUID_DATA_ATTR);

      return this.imageManager.getImageDataFromUUID(uuid);
    }

    return null;
  };

  /**
   * Get editor wrappers to move (for drag-and-drop)
   * @returns {Array} Array of jQuery wrapper objects
   */
  DragDropManager.prototype.getEditorWrappersToMove = function() {
    if (!this.draggedElement) {
      return [];
    }

    var $draggedWrapper = $(this.draggedElement);
    return [$draggedWrapper];
  };

  // ============================================================
  // VISUAL FEEDBACK
  // ============================================================

  /**
   * Update dragging visuals (count badge and .dragging class)
   * @param {boolean} isDragging - true to show, false to hide
   */
  DragDropManager.prototype.updateDraggingVisuals = function(isDragging) {
    if (isDragging) {
      var count = 0;
      var $elementsToMark = [];

      if (this.dragSource === DRAG_SOURCE.PICKER && this.imagePicker) {
        var draggedUuid = $(this.draggedElement).data(TtConst.IMAGE_UUID_DATA_ATTR);
        var isDraggedSelected = this.imagePicker.selectedImages.has(draggedUuid);

        if (isDraggedSelected && this.imagePicker.selectedImages.size > 1) {
          // Mark all selected cards
          count = this.imagePicker.selectedImages.size;
          var selectedUuids = this.imagePicker.selectedImages;
          $(TtConst.JOURNAL_EDITOR_MULTI_IMAGE_CARD_SELECTOR).each(function() {
            var $card = $(this);
            if (selectedUuids.has($card.data(TtConst.IMAGE_UUID_DATA_ATTR))) {
              $elementsToMark.push($card);
            }
          });
        } else {
          // Just the dragged card
          count = 1;
          $elementsToMark.push($(this.draggedElement));
        }
      } else if (this.dragSource === DRAG_SOURCE.EDITOR) {
        // Single image drag only
        var $draggedWrapper = $(this.draggedElement);
        count = 1;
        $elementsToMark.push($draggedWrapper);
      }

      // Apply .dragging class
      $elementsToMark.forEach(function($el) {
        $el.addClass(EDITOR_TRANSIENT.CSS_DRAGGING);
      });

      // Add count badge if multiple images
      if (count > 1 && this.draggedElement) {
        var $badge = $('<span>')
          .addClass('drag-count-badge')
          .text(count + ' images');
        $(this.draggedElement).append($badge);
      }
    } else {
      // Remove .dragging class from all elements
      $(TtConst.JOURNAL_EDITOR_MULTI_IMAGE_CARD_SELECTOR).removeClass(EDITOR_TRANSIENT.CSS_DRAGGING);
      this.$editor.find(TtConst.JOURNAL_IMAGE_WRAPPER_SELECTOR).removeClass(EDITOR_TRANSIENT.CSS_DRAGGING);

      // Remove count badges
      $('.drag-count-badge').remove();
    }
  };

  // ============================================================
  // STATE ACCESS (for external integration)
  // ============================================================

  /**
   * Set drag state (used by reference image manager)
   * @param {Element} element - The dragged element
   * @param {string} source - The drag source ('picker', 'editor', 'reference')
   */
  DragDropManager.prototype.setDragState = function(element, source) {
    this.draggedElement = element;
    this.dragSource = source;
  };

  /**
   * Get current drag source
   * @returns {string|null} Current drag source or null
   */
  DragDropManager.prototype.getDragSource = function() {
    return this.dragSource;
  };

  /**
   * Check if reference drop zone should highlight
   * @returns {boolean}
   */
  DragDropManager.prototype.shouldShowReferenceDropZone = function() {
    if (this.referenceImageManager) {
      return this.referenceImageManager.shouldShowDropZone();
    }
    return false;
  };

  /**
   * Set visibility of reference drop zone highlighting
   * @param {boolean} visible - true to show drop zone, false to hide
   */
  DragDropManager.prototype.setReferenceDropZoneVisible = function(visible) {
    if (this.referenceImageManager) {
      this.referenceImageManager.setDropZoneVisible(visible);
    }
  };

  // ============================================================
  // EXPORTS TO Tt.JournalEditor NAMESPACE
  // ============================================================

  Tt.JournalEditor.DragDropManager = DragDropManager;

  // Export constants for external use
  Tt.JournalEditor.DRAG_SOURCE = DRAG_SOURCE;
  Tt.JournalEditor.LAYOUT_VALUES = LAYOUT_VALUES;

  // Export internal constants for testing
  Tt.JournalEditor._DRAG_DROP_TRANSIENT = EDITOR_TRANSIENT;

})(jQuery);
