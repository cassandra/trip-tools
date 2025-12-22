/**
 * Journal Entry Editor - ContentEditable with Image Management
 *
 * EDITOR-ONLY JavaScript - This file is for the edit view only.
 * For the public/external journal view, see journal.js instead.
 *
 * Features:
 * - Rich text editing with automatic paragraph creation
 * - Drag-and-drop image insertion with layout detection
 * - Image click to inspect in modal
 * - Image reordering within editor
 * - Image removal with hover controls
 * - Autosave integration with 2-second debounce
 * - Responsive design with mobile warning
 * - Keyboard shortcuts: Ctrl/Cmd+B (bold), Ctrl/Cmd+I (italic)
 *
 * ============================================================
 * IMAGE PICKER PANEL
 * ============================================================
 *
 * The sidebar image picker allows browsing trip images by date or recent uploads.
 * Three filter buttons control which images are displayed:
 *
 * - Date Input: Standard date picker to load images from a specific date
 * - Last Used Date Button: Returns to the previously viewed date after browsing Recent
 * - Recent Button: Shows recently uploaded images (useful after uploading new images)
 *
 * Last Used Date Tracking:
 * The "last used date" button remembers the most recently viewed date, allowing
 * users to return to it after viewing Recent images. This is tracked via:
 * - `lastUsedDate` variable: Tracks the date, initialized from server's filter_date
 * - `data-last-used-date` attribute: Stores the date on the button element
 * - Button label: Dynamically updated to show the date (e.g., "Sep 29")
 *
 * For Prologue/Epilogue pages (no entry date), the button starts disabled
 * and becomes active once the user selects a date.
 *
 * Scope filters (Unused/Used/All) are client-side only and filter images
 * based on whether they're already used in the editor content.
 *
 * ============================================================
 * HTML CONTRACT: PERSISTENT vs TRANSIENT
 * ============================================================
 *
 * PERSISTENT HTML (saved to database, visible in public view):
 * - <span class="trip-image-wrapper" data-layout="float-right|full-width">
 * - <img class="trip-image" data-uuid="..." src="..." alt="...">
 * - <span class="trip-image-caption">Caption text</span> (optional, if caption exists)
 * - <div class="full-width-image-group"> (wraps consecutive full-width images)
 * - <p class="has-float-image"> (paragraphs containing float-right images)
 * - data-layout attribute (float-right | full-width)
 * - data-uuid attribute (image identifier)
 *
 * TRANSIENT HTML (editor-only, removed before save):
 * - <button class="trip-image-delete-btn">× (delete button)
 * - CSS classes: .drop-zone-active, .drop-zone-between, .dragging, .drag-over, .selected
 * - Any <div class="drop-zone-between"> elements
 *
 * The getCleanHTML() method is responsible for removing ALL transient
 * elements/classes before saving. The backend HTML sanitizer (Bleach)
 * provides additional safety by whitelisting only allowed tags/attributes.
 *
 * ARCHITECTURE:
 * - EditorLayoutManager: Manages layout-related DOM manipulations
 * - AutoSaveManager: Handles saving with debouncing and retry logic
 * - JournalEditorMultiImagePicker: Image picker panel with selection and filtering
 * - JournalEditor: Main orchestrator connecting UI events to managers
 * - initImagePickerFilters(): Initializes date/recent filter buttons and lastUsedDate tracking
 */

(function($) {
  'use strict';

  // =========================================================================
  // IMPORTS FROM EXTRACTED MODULES
  // =========================================================================

  /**
   * HTML STRUCTURE CONSTANTS
   * Reference to constants defined in html-normalization.js
   */
  var HTML_STRUCTURE = Tt.JournalEditor.HTML_STRUCTURE;

  /**
   * EDITOR-ONLY TRANSIENT CONSTANTS
   * Imported from layout-manager.js (canonical source)
   */
  var EDITOR_TRANSIENT = Tt.JournalEditor.EDITOR_TRANSIENT;

  /**
   * LAYOUT VALUES
   * Imported from drag-drop-manager.js (canonical source)
   */
  var LAYOUT_VALUES = Tt.JournalEditor.LAYOUT_VALUES;

  /**
   * DRAG SOURCE IDENTIFIERS
   * Imported from drag-drop-manager.js (canonical source)
   */
  var DRAG_SOURCE = Tt.JournalEditor.DRAG_SOURCE;

  /**
   * STATUS VALUES
   * Imported from autosave-manager.js (canonical source)
   */
  var STATUS = Tt.JournalEditor.STATUS;

  /**
   * ============================================================
   * REFERENCES TO EXTRACTED MODULES
   * ============================================================
   *
   * From html-normalization.js:
   * - ToolbarHelper: DOM cleanup and formatting normalization
   * - CursorPreservation: Save/restore cursor across DOM changes
   * - runFullNormalization: Master normalization orchestrator
   *
   * From toolbar-manager.js:
   * - JournalEditorToolbar: Formatting toolbar implementation
   *
   * From reference-manager.js:
   * - ReferenceImageManager: Reference image state and interactions
   */
  var ToolbarHelper = Tt.JournalEditor.ToolbarHelper;
  var CursorPreservation = Tt.JournalEditor.CursorPreservation;
  var runFullNormalization = Tt.JournalEditor.runFullNormalization;
  var JournalEditorToolbar = Tt.JournalEditor.JournalEditorToolbar;
  var ReferenceImageManager = Tt.JournalEditor.ReferenceImageManager;
  var KeyboardNavigationManager = Tt.JournalEditor.KeyboardNavigationManager;
  var ImageManager = Tt.JournalEditor.ImageManager;
  var DragDropManager = Tt.JournalEditor.DragDropManager;
  var AutoSaveManager = Tt.JournalEditor.AutoSaveManager;
  var EditorLayoutManager = Tt.JournalEditor.EditorLayoutManager;
  var getSelectionModifiers = Tt.JournalEditor.getSelectionModifiers;
  var SelectionBadgeManager = Tt.JournalEditor.SelectionBadgeManager;
  var imageSelectionCoordinator = Tt.JournalEditor.imageSelectionCoordinator;
  var ImageDataService = Tt.JournalEditor.ImageDataService;
  var JournalEditorMultiImagePicker = Tt.JournalEditor.JournalEditorMultiImagePicker;
  var PasteHandler = Tt.JournalEditor.PasteHandler;

  // ========== END OF EXTRACTED CODE REFERENCES ==========

  // Module state
  let editorInstance = null;

  /**
   * JournalEditor - Main editor class
   */
  function JournalEditor($editor) {
    this.$editor = $editor;
    this.$form = $editor.closest(TtConst.JOURNAL_ENTRY_FORM_SELECTOR);
    this.$titleInput = this.$form.find(TtConst.JOURNAL_TITLE_INPUT_ID_SELECTOR);
    this.$dateInput = this.$form.find(TtConst.JOURNAL_DATE_INPUT_ID_SELECTOR);
    this.$timezoneInput = this.$form.find(TtConst.JOURNAL_TIMEZONE_INPUT_SELECTOR);
    this.$includeInPublishInput = this.$form.find('#id_include_in_publish');
    this.$previewBtn = $(TtConst.JOURNAL_PREVIEW_BTN_SELECTOR);
    this.$statusElement = this.$form.find(TtConst.JOURNAL_SAVE_STATUS_SELECTOR);

    this.currentVersion = $editor.data(TtConst.CURRENT_VERSION_DATA_ATTR) || 1;

    // Reference image container (for backward compatibility)
    this.$referenceContainer = $(TtConst.JOURNAL_REFERENCE_IMAGE_CONTAINER_SELECTOR);

    // Initialize managers
    this.editorLayoutManager = new EditorLayoutManager(this.$editor);

    var entryUuid = $editor.data(TtConst.ENTRY_UUID_DATA_ATTR);
    this.tripUuid = $editor.data(TtConst.TRIP_UUID_DATA_ATTR);
    var autosaveUrl = Tt.buildJournalEntryAutosaveUrl(entryUuid);
    var csrfToken = this.getCSRFToken();
    this.autoSaveManager = new AutoSaveManager(this, autosaveUrl, csrfToken);

    // Initialize image manager
    var self = this;
    this.imageManager = new ImageManager({
      $editor: this.$editor,
      onImageAdded: function(uuid) {
        // Hook for future extension
      },
      onImageRemoved: function(uuid) {
        // Hook for future extension
      },
      onContentChange: function() {
        self.handleContentChange();
      },
      refreshLayout: function() {
        self.refreshImageLayout();
      }
    });

    // Expose usedImageUUIDs for backwards compatibility with imagePicker
    this.usedImageUUIDs = this.imageManager.usedImageUUIDs;

    // Initialize image picker (if panel exists)
    // IMPORTANT: Must initialize AFTER imageManager is created
    var $imagePanel = $(EDITOR_TRANSIENT.SEL_JOURNAL_EDITOR_MULTI_IMAGE_PANEL);
    if ($imagePanel.length > 0) {
      this.imagePicker = new JournalEditorMultiImagePicker($imagePanel, this);
      // Give imageManager access to picker for filter updates
      this.imageManager.imagePicker = this.imagePicker;
    }

    // Initialize drag-drop manager (after imageManager and imagePicker)
    this.dragDropManager = new DragDropManager({
      $editor: this.$editor,
      imageManager: this.imageManager,
      imagePicker: this.imagePicker,
      referenceImageManager: this.referenceImageManager,
      refreshImageLayout: function() {
        self.refreshImageLayout();
      },
      handleContentChange: function() {
        self.handleContentChange();
      },
      clearReferenceImage: function() {
        self.clearReferenceImage();
      }
    });

    // Expose drag state for backwards compatibility
    this.draggedElement = null;
    this.dragSource = null;

    this.init();
  }

  /**
   * Initialize the editor
   */
  JournalEditor.prototype.init = function() {
    if (!this.$editor.length) {
      return;
    }

    // Initialize used image tracking from existing content
    this.initializeUsedImages();

    // Initialize reference image state from server data
    this.initializeReferenceImage();

    // Apply initial filter to image picker now that usedImageUUIDs is populated
    if (this.imagePicker) {
      this.imagePicker.applyFilter(this.imagePicker.filterScope);
    }

    // Initialize autosave baseline with current content
    this.autoSaveManager.initializeBaseline();
    this.updateStatus(STATUS.SAVED);

    // Initialize ContentEditable
    this.initContentEditable();

    // Initialize toolbar
    this.initializeToolbar();

    // Setup autosave handlers
    this.setupAutosave();

    // Setup manual save button
    this.setupManualSaveButton();

    // Setup drag-and-drop for image operations (delegates to DragDropManager)
    this.dragDropManager.setup();

    // Setup image click to inspect
    this.setupImageClickToInspect();

    // Setup image selection
    this.setupImageSelection();

    // Setup image removal (delete button handler)
    this.setupImageRemoval();

    // Setup reference image functionality
    this.setupReferenceImage();

    // Setup keyboard navigation
    this.setupKeyboardNavigation();

    // Setup edge paragraph insertion (clicking in padding or arrow keys at boundaries)
    this.setupEdgeParagraphInsertion();
  };

  /**
   * Initialize used image tracking from existing editor content
   * Delegates to ImageManager
   */
  JournalEditor.prototype.initializeUsedImages = function() {
    this.imageManager.initializeUsedImages();
  };

  /**
   * Initialize reference image manager and state from server data
   * Creates ReferenceImageManager with callbacks for external dependencies
   */
  JournalEditor.prototype.initializeReferenceImage = function() {
    var self = this;

    // Get initial UUID from container data attribute
    var initialUuid = null;
    if (this.$referenceContainer.length) {
      var refImageUuid = this.$referenceContainer.data(TtConst.REFERENCE_IMAGE_UUID_DATA_ATTR);
      if (refImageUuid) {
        initialUuid = refImageUuid;
      }
    }

    // Create ReferenceImageManager with callbacks
    this.referenceImageManager = new ReferenceImageManager({
      $container: this.$referenceContainer,
      initialUuid: initialUuid,
      onContentChange: function() {
        self.handleContentChange();
      },
      getDraggedImageData: function() {
        return self.dragDropManager.getDraggedImageData();
      },
      getImageDataByUUID: function(uuid) {
        return ImageDataService.getImageDataByUUID(uuid);
      },
      setDragState: function(element, source) {
        self.dragDropManager.setDragState(element, source);
      },
      getDragSource: function() {
        return self.dragDropManager.getDragSource();
      },
      DRAG_SOURCE: Tt.JournalEditor.DRAG_SOURCE
    });
  };

  /**
   * Initialize ContentEditable functionality
   */
  JournalEditor.prototype.initContentEditable = function() {
    var self = this;

    // Refresh layout on page load (delete buttons, groups, float markers)
    this.editorLayoutManager.refreshLayout();

    // Only add paragraph structure if editor is genuinely empty
    var hasTextContent = $.trim(this.$editor.text()).length > 0;
    var hasImages = this.$editor.find('img').length > 0;
    var hasContent = hasTextContent || hasImages;

    if (!hasContent && !this.$editor.children().length) {
      this.$editor.html('<p><br></p>');
    }

    // Initialize paste handler (extracted to editor/paste-handler.js)
    this.pasteHandler = new PasteHandler(this.$editor, {
      onContentChange: function() {
        self.handleContentChange();
      }
    });
    this.pasteHandler.setup();

    // Prevent dropping files directly into editor (would show file:// URLs)
    this.$editor.on('drop', function(e) {
      if (e.originalEvent.dataTransfer.files.length > 0) {
        e.preventDefault();
        return false;
      }
    });

    // Note: Keyboard handling (Enter/Backspace) moved to KeyboardNavigationManager
  };

  /**
   * Initialize formatting toolbar
   */
  JournalEditor.prototype.initializeToolbar = function() {
    var $toolbar = $('.journal-editor-toolbar');
    if ($toolbar.length) {
      var self = this;
      this.toolbar = new JournalEditorToolbar(
        $toolbar,
        this.$editor,
        function() {
          self.handleContentChange();
        }
      );
    }
  };

  /**
   * Setup autosave handlers
   */
  JournalEditor.prototype.setupAutosave = function() {
    var self = this;

    // Track content changes
    this.$editor.on('input', function() {
      self.handleContentChange();
    });

    // Note: Paste normalization is not needed here because initContentEditable()
    // already handles paste events by preventing default and inserting plain text only.
    // The plain text insertion via execCommand('insertText') creates properly
    // structured content that doesn't require additional normalization.

    // Track metadata changes
    this.$titleInput.on('input', function() {
      self.handleContentChange();
    });

    // Date changes trigger immediate save:
    // - 'change' from picker selection (not keyboard) → immediate save
    // - 'blur' when field loses focus → immediate save
    // Track keyboard input to distinguish picker from typing
    var dateInputIsTyping = false;

    this.$dateInput.on('keydown', function(e) {
      if (e.key !== 'Enter') {
        dateInputIsTyping = true;
      }
    });

    this.$dateInput.on('change', function() {
      if (!dateInputIsTyping) {
        // Change from picker selection, not keyboard
        self.handleContentChange();
        self.autoSaveManager.saveNow();
      }
      // Reset flag - if it was typing, blur will handle save
    });

    this.$dateInput.on('blur', function() {
      dateInputIsTyping = false;
      self.handleContentChange();
      self.autoSaveManager.saveNow();
    });

    this.$timezoneInput.on('change', function() {
      self.handleContentChange();
    });

    this.$includeInPublishInput.on('change', function() {
      self.handleContentChange();
      self.updatePreviewButtonVisibility();
    });

    // Prevent ENTER from submitting form - trigger immediate save instead
    this.$titleInput.on('keydown', function(e) {
      if (e.key === 'Enter') {
        e.preventDefault();
        self.handleContentChange();
        self.autoSaveManager.saveNow();
      }
    });

    this.$dateInput.on('keydown', function(e) {
      if (e.key === 'Enter') {
        e.preventDefault();
        self.handleContentChange();
        self.autoSaveManager.saveNow();
      }
    });
  };

  /**
   * Setup save status button click handler
   * The status button is clickable when in 'unsaved' or 'error' state
   */
  JournalEditor.prototype.setupManualSaveButton = function() {
    var self = this;

    this.$statusElement.on('click', function() {
      if (!$(this).prop('disabled')) {
        self.autoSaveManager.saveNow();
      }
    });
  };

  /**
   * Refresh image layout (wrapping and float markers)
   * Only called when images are added, removed, or moved
   */
  JournalEditor.prototype.refreshImageLayout = function() {
    this.editorLayoutManager.wrapFullWidthImageGroups();
    this.editorLayoutManager.markFloatParagraphs();
  };

  /**
   * Handle content change (fired on every keystroke)
   * Note: Does NOT run normalization - that happens at idle time (see runNormalizationAtIdle)
   * Note: Does NOT refresh layout - only schedules autosave
   */
  JournalEditor.prototype.handleContentChange = function() {
    // Schedule autosave (handles change detection and debouncing)
    this.autoSaveManager.scheduleSave();
  };

  /**
   * Update Preview button visibility based on include_in_publish checkbox state.
   * Preview is only available when the entry is marked for publishing.
   */
  JournalEditor.prototype.updatePreviewButtonVisibility = function() {
    if (this.$includeInPublishInput.is(':checked')) {
      this.$previewBtn.show();
    } else {
      this.$previewBtn.hide();
    }
  };

  /**
   * Run normalization at idle time (after user stops typing for 2 seconds)
   * Called by autosave idle timer before actual save
   */
  JournalEditor.prototype.runNormalizationAtIdle = function() {
    // Save cursor position before normalization
    var cursor = CursorPreservation.save(this.$editor);

    // Run full HTML normalization
    runFullNormalization(this.$editor[0]);

    // Refresh layout to update markers and groups
    // Must happen BEFORE cursor restore because wrapFullWidthImageGroups
    // unwraps/rewraps image groups which destroys cursor position
    this.editorLayoutManager.wrapFullWidthImageGroups();
    this.editorLayoutManager.markFloatParagraphs();

    // Restore cursor position after normalization AND layout operations
    CursorPreservation.restore(this.$editor, cursor);
  };

  // Note: Cursor position helpers (isCursorAtEnd, isCursorAtStart, setCursorAtStart)
  // moved to KeyboardNavigationManager

  // Note: handleEnterInBlock and handleBackspaceInBlock moved to KeyboardNavigationManager

  /**
   * Get clean HTML for saving
   *
   * Removes ALL transient (editor-only) elements and classes.
   * Only persistent HTML elements/attributes are kept.
   *
   * PERSISTENT (saved to database):
   * - <span class="trip-image-wrapper" data-layout="...">
   * - <img class="trip-image" data-uuid="..." src="...">
   * - <div class="full-width-image-group">
   * - <p class="has-float-image">
   *
   * TRANSIENT (removed before save):
   * - <button class="trip-image-delete-btn">
   * - .drop-zone-active, .drop-zone-between
   * - .dragging, .drag-over
   * - .selected
   */
  JournalEditor.prototype.getCleanHTML = function() {
    // Clone the editor content to avoid modifying the displayed version
    var $clone = this.$editor.clone();

    // Run full normalization before saving
    runFullNormalization($clone[0]);

    // Remove transient elements (never saved to database)
    $clone.find(EDITOR_TRANSIENT.SEL_DELETE_BTN).remove();
    $clone.find('.' + EDITOR_TRANSIENT.CSS_DROP_ZONE_BETWEEN).remove();

    // Remove transient classes (editor-only states)
    $clone.find('.' + EDITOR_TRANSIENT.CSS_DROP_ZONE_ACTIVE)
          .removeClass(EDITOR_TRANSIENT.CSS_DROP_ZONE_ACTIVE);
    $clone.find('.' + EDITOR_TRANSIENT.CSS_DRAGGING)
          .removeClass(EDITOR_TRANSIENT.CSS_DRAGGING);
    $clone.removeClass(EDITOR_TRANSIENT.CSS_DRAG_OVER);

    // Remove selected state (editor UI only)
    $clone.find('.' + EDITOR_TRANSIENT.CSS_SELECTED).removeClass(EDITOR_TRANSIENT.CSS_SELECTED);

    // Remove edit-time-only attributes from images (draggable is editor-only)
    $clone.find(TtConst.JOURNAL_IMAGE_SELECTOR).removeAttr('draggable');

    // Remove contenteditable attributes (editor-only for caption isolation)
    $clone.find(TtConst.JOURNAL_IMAGE_WRAPPER_SELECTOR).removeAttr('contenteditable');
    $clone.find(TtConst.JOURNAL_IMAGE_CAPTION_SELECTOR).removeAttr('contenteditable');

    return $clone.html();
  };

  /**
   * Get current reference image UUID
   * Delegates to ReferenceImageManager
   * @returns {string|null} Current UUID or null if none set
   */
  JournalEditor.prototype.getReferenceImageUuid = function() {
    if (this.referenceImageManager) {
      return this.referenceImageManager.getUuid();
    }
    return null;
  };

  /**
   * Handle version conflict
   */
  JournalEditor.prototype.handleVersionConflict = function(data) {
    console.warn('Version conflict detected');
    this.updateStatus('error', 'Conflict detected - please review changes');

    // Display the conflict modal if provided
    if (data && data.modal) {
      AN.displayModal(data.modal);
    }
  };

  /**
   * Update save status display
   * Single button that changes appearance based on state:
   * - saved: green outline, disabled
   * - unsaved: warning (yellow), clickable to save
   * - saving: info (blue), disabled
   * - error: danger (red), clickable to retry
   */
  JournalEditor.prototype.updateStatus = function(status, message) {
    var text = '';
    var btnClass = 'btn-outline-success';
    var disabled = true;
    var title = '';

    switch (status) {
      case 'saved':
        text = 'Saved';
        btnClass = 'btn-outline-primary';
        disabled = true;
        title = 'Content saved';
        break;
      case 'unsaved':
        text = 'Unsaved';
        btnClass = 'btn-secondary';
        disabled = false;
        title = 'Click to save';
        break;
      case 'saving':
        text = 'Saving...';
        btnClass = 'btn-info';
        disabled = true;
        title = 'Saving in progress';
        break;
      case 'error':
        text = message || 'Retry';
        btnClass = 'btn-danger';
        disabled = false;
        title = 'Click to retry save';
        break;
    }

    this.$statusElement
      .removeClass('btn-outline-primary btn-info btn-danger btn-primary btn-secondary')
      .addClass(btnClass)
      .prop('disabled', disabled)
      .attr('title', title)
      .text(text);
  };

  /**
   * Handle title update from server
   * Updates the title input field and shows a brief notification
   */
  JournalEditor.prototype.handleTitleUpdate = function(newTitle) {
    // Update the title input field
    this.$titleInput.val(newTitle);

    // Show brief notification in status area
    var originalStatus = this.$statusElement.text();
    var originalClass = this.$statusElement.attr('class');

    this.$statusElement
      .removeClass('badge-secondary badge-success badge-warning badge-info badge-danger')
      .addClass('badge-info')
      .text('Title updated to match new date');

    // Restore original status after 3 seconds
    setTimeout(function() {
      this.$statusElement.attr('class', originalClass).text(originalStatus);
    }.bind(this), 3000);
  };

  /**
   * Create image element with proper attributes
   * Delegates to ImageManager
   */
  JournalEditor.prototype.createImageElement = function(uuid, url, caption, layout) {
    return this.imageManager.createImageElement(uuid, url, caption, layout);
  };

  /**
   * Setup image click to inspect
   * Single-click opens the Image Inspector modal
   */
  JournalEditor.prototype.setupImageClickToInspect = function() {
    var self = this;

    // Single-click to open Image Inspector modal
    this.$editor.on('click', TtConst.JOURNAL_IMAGE_SELECTOR, function(e) {
      e.preventDefault();
      e.stopPropagation();

      var $img = $(this);
      var uuid = $img.data(TtConst.UUID_DATA_ATTR);

      if (uuid) {
        var inspectUrl = Tt.buildImageInspectUrl(uuid, self.tripUuid);
        AN.get(inspectUrl);
      }
    });

    // Prevent default drag on existing images (handled in setupImageReordering)
    this.$editor.on('dragstart', TtConst.JOURNAL_IMAGE_SELECTOR, function(e) {
      // This is handled in setupImageReordering
    });
  };

  /**
   * Setup image selection in editor
   */
  JournalEditor.prototype.setupImageSelection = function() {
    // Event handlers are already set up in setupImageClickToInspect()
    // This method is a placeholder for any future initialization needs
  };

  /**
   * Get image data object from UUID by looking up picker card
   * Delegates to ImageManager
   * @param {string} uuid - Image UUID
   * @returns {Object|null} {uuid, thumbnailUrl, fullUrl, caption} or null if not found
   */
  JournalEditor.prototype.getImageDataFromUUID = function(uuid) {
    return this.imageManager.getImageDataFromUUID(uuid);
  };

  /**
   * Setup image removal
   */
  JournalEditor.prototype.setupImageRemoval = function() {
    var self = this;

    // Note: Images are always wrapped with delete button at creation time
    // No need for hover-based wrapping

    // Handle delete button click
    this.$editor.on('click', EDITOR_TRANSIENT.SEL_DELETE_BTN, function(e) {
      e.preventDefault();
      e.stopPropagation();

      var $wrapper = $(this).closest(TtConst.JOURNAL_IMAGE_WRAPPER_SELECTOR);
      var $img = $wrapper.find(TtConst.JOURNAL_IMAGE_SELECTOR);

      self.removeImage($img);
    });
  };

  /**
   * Remove wrapper from DOM and update usage tracking (private helper)
   * Delegates to ImageManager
   *
   * @param {jQuery} $wrapper - The image wrapper to remove
   * @returns {string|null} The UUID of the removed image, or null if none
   * @private
   */
  JournalEditor.prototype._removeWrapperAndUpdateUsage = function($wrapper) {
    return this.imageManager._removeWrapperAndUpdateUsage($wrapper);
  };

  /**
   * Remove image from editor
   * Delegates to ImageManager
   */
  JournalEditor.prototype.removeImage = function($img) {
    this.imageManager.removeImage($img);
  };

  /**
   * Setup reference image drag-and-drop, clear button, and double-click
   * Delegates to ReferenceImageManager
   */
  JournalEditor.prototype.setupReferenceImage = function() {
    if (this.referenceImageManager) {
      this.referenceImageManager.setup();
    }
  };

  /**
   * Set reference image from image data
   * Delegates to ReferenceImageManager
   * @param {Object} imageData - {uuid, url, caption, inspectUrl (optional)}
   */
  JournalEditor.prototype.setReferenceImage = function(imageData) {
    if (this.referenceImageManager) {
      this.referenceImageManager.setImage(imageData);
    }
  };

  /**
   * Clear reference image
   * Delegates to ReferenceImageManager
   */
  JournalEditor.prototype.clearReferenceImage = function() {
    if (this.referenceImageManager) {
      this.referenceImageManager.clearImage();
    }
  };

  /**
   * Setup keyboard navigation and shortcuts
   * Delegates to KeyboardNavigationManager
   */
  JournalEditor.prototype.setupKeyboardNavigation = function() {
    var self = this;

    this.keyboardManager = new KeyboardNavigationManager({
      $editor: this.$editor,
      onContentChange: function() {
        self.handleContentChange();
      }
    });

    this.keyboardManager.setup();
  };

  /**
   * Setup edge paragraph insertion
   * Clicking in the editor's top/bottom padding creates a new paragraph
   * when the first/last element is a non-editable block (e.g., full-width image group)
   */
  JournalEditor.prototype.setupEdgeParagraphInsertion = function() {
    var self = this;

    this.$editor.on('click', function(e) {
      // Only handle direct clicks on the editor element (padding area)
      if (e.target !== self.$editor[0]) {
        return;  // Click was on a child element, not padding
      }

      var $firstChild = self.$editor.children().first();
      var $lastChild = self.$editor.children().last();

      // Get click position
      var clickY = e.clientY;

      // Check if click is in top padding (above first child)
      if ($firstChild.length) {
        var firstChildRect = $firstChild[0].getBoundingClientRect();
        if (clickY < firstChildRect.top) {
          // Clicked in top padding - insert paragraph at start
          self.insertParagraphAtEdge('start');
          return;
        }
      }

      // Check if click is in bottom padding (below last child)
      if ($lastChild.length) {
        var lastChildRect = $lastChild[0].getBoundingClientRect();
        if (clickY > lastChildRect.bottom) {
          // Clicked in bottom padding - insert paragraph at end
          self.insertParagraphAtEdge('end');
          return;
        }
      }
    });
  };

  /**
   * Insert a new paragraph at the start or end of the editor
   * @param {string} edge - 'start' or 'end'
   */
  JournalEditor.prototype.insertParagraphAtEdge = function(edge) {
    var $newParagraph = $('<p class="' + HTML_STRUCTURE.TEXT_BLOCK_CLASS + '"><br></p>');

    if (edge === 'start') {
      this.$editor.prepend($newParagraph);
    } else {
      this.$editor.append($newParagraph);
    }

    // Position cursor in new paragraph
    var range = document.createRange();
    range.selectNodeContents($newParagraph[0]);
    range.collapse(true);

    var selection = window.getSelection();
    selection.removeAllRanges();
    selection.addRange(range);

    // Scroll new paragraph into view if added at end (may be below fold)
    if (edge === 'end') {
      $newParagraph[0].scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    // Trigger content change for autosave
    this.handleContentChange();
  };

  /**
   * Utility: Get CSRF token
   */
  JournalEditor.prototype.getCSRFToken = function() {
    return Cookies.get('csrftoken');
  };

  /**
   * Check if editor has unsaved content
   * Public method for beforeunload handler to check unsaved state
   * @returns {boolean} true if there are unsaved changes
   */
  JournalEditor.prototype.hasUnsavedContent = function() {
    return this.autoSaveManager && this.autoSaveManager.hasUnsavedChanges;
  };

  /**
   * Initialize editor on document ready
   */
  $(document).ready(function() {
    var $editor = $(TtConst.JOURNAL_EDITOR_ID_SELECTOR);

    if ($editor.length && $editor.attr('contenteditable') === 'true') {
      editorInstance = new JournalEditor($editor);
    }
  });

  /**
   * Global beforeunload handler
   * Warns user before navigating away from page with unsaved changes
   *
   * Browser will display standard warning message (cannot be customized)
   */
  $(window).on('beforeunload', function(e) {
    if (editorInstance && editorInstance.hasUnsavedContent()) {
      // Prevent default behavior
      e.preventDefault();

      // Required for Chrome
      e.returnValue = '';

      // Required for other browsers
      return '';
    }
  });

  // Expose for debugging (preserves functions from picker-filters-manager.js)
  window.JournalEditor = window.JournalEditor || {};
  window.JournalEditor.getInstance = function() {
    return editorInstance;
  };

  // Initialize image picker filters when DOM is ready
  // (Delegates to extracted picker-filters-manager.js module)
  $(document).ready(function() {
    Tt.JournalEditor.initImagePickerFilters(editorInstance);
  });

})(jQuery);
