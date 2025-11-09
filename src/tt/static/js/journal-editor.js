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
 * - Image removal with keyboard and hover controls
 * - Autosave integration with 2-second debounce
 * - Responsive design with mobile warning
 * - Simplified keyboard shortcuts (6 total)
 *   - Text formatting: Ctrl/Cmd+B/I
 *   - Picker operations: Escape, Delete, Ctrl+R (stub)
 *   - Editor operations: Escape, Delete, Ctrl+R (stub)
 *   - Global: Ctrl+/ for help (stub)
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
 * - JournalEditor: Main orchestrator connecting UI events to managers
 */

(function($) {
  'use strict';

  /**
   * EDITOR-ONLY TRANSIENT CONSTANTS
   * These are runtime-only CSS classes added/removed by JavaScript.
   * They are NEVER saved to the database and NEVER appear in templates.
   *
   * For shared constants (IDs, classes used in templates), see Tt namespace in main.js
   */
  const EDITOR_TRANSIENT = {
    // Transient CSS classes (editor UI only, never saved)
    CSS_DELETE_BTN: 'trip-image-delete-btn',
    CSS_DROP_ZONE_ACTIVE: 'drop-zone-active',
    CSS_DROP_ZONE_BETWEEN: 'drop-zone-between',
    CSS_DRAGGING: 'dragging',
    CSS_DRAG_OVER: 'drag-over',
    CSS_SELECTED: 'selected',

    // Transient element selectors
    SEL_DELETE_BTN: '.trip-image-delete-btn',
    SEL_DROP_ZONE_BETWEEN: '.drop-zone-between',
  };

  /**
   * LAYOUT VALUES
   * These are the actual string values for data-layout attribute.
   * Not DOM selectors, just the values.
   */
  const LAYOUT_VALUES = {
    FLOAT_RIGHT: 'float-right',
    FULL_WIDTH: 'full-width',
  };

  /**
   * ============================================================
   * SHARED UTILITIES FOR IMAGE SELECTION
   * ============================================================
   */

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

  /**
   * SelectionBadgeManager
   *
   * Manages a selection count badge next to a reference element.
   * Used by both picker and editor to show selection counts.
   */
  function SelectionBadgeManager($referenceElement, badgeId) {
    this.$referenceElement = $referenceElement;
    this.badgeId = badgeId;
    this.$badge = null;
  }

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

  SelectionBadgeManager.prototype.remove = function() {
    if (this.$badge) {
      this.$badge.remove();
      this.$badge = null;
    }
  };

  /**
   * ImageSelectionCoordinator
   *
   * Ensures mutual exclusivity between picker and editor image selections.
   * Only one area can have selections at a time.
   *
   * Usage:
   * - Call notifyPickerSelection() when picker selections change
   * - Call notifyEditorSelection() when editor selections change
   * - Coordinator will call clearSelection() on the other area as needed
   */
  function ImageSelectionCoordinator() {
    this.pickerClearCallback = null;
    this.editorClearCallback = null;
  }

  ImageSelectionCoordinator.prototype.registerPicker = function(clearCallback) {
    this.pickerClearCallback = clearCallback;
  };

  ImageSelectionCoordinator.prototype.registerEditor = function(clearCallback) {
    this.editorClearCallback = clearCallback;
  };

  ImageSelectionCoordinator.prototype.notifyPickerSelection = function(hasSelections) {
    if (hasSelections && this.editorClearCallback) {
      this.editorClearCallback();
    }
  };

  ImageSelectionCoordinator.prototype.notifyEditorSelection = function(hasSelections) {
    if (hasSelections && this.pickerClearCallback) {
      this.pickerClearCallback();
    }
  };

  // Global singleton
  const imageSelectionCoordinator = new ImageSelectionCoordinator();

  // Module state
  let editorInstance = null;

  /**
   * EditorLayoutManager
   *
   * Manages layout-related DOM manipulations for the editor.
   * Responsible for maintaining the structure of persistent HTML elements.
   *
   * This manager handles:
   * - Wrapping consecutive full-width images in groups
   * - Marking paragraphs with float-right images for CSS clearing
   * - Ensuring delete buttons exist on all image wrappers
   */
  function EditorLayoutManager($editor) {
    this.$editor = $editor;
  }

  /**
   * Wrap consecutive full-width images in container divs
   * This allows them to clear floats properly (block-level element needed)
   */
  EditorLayoutManager.prototype.wrapFullWidthImageGroups = function() {
    // Remove existing wrappers first
    this.$editor.find('.' + Tt.JOURNAL_FULL_WIDTH_GROUP_CLASS).each(function() {
      var $group = $(this);
      $group.children(Tt.JOURNAL_IMAGE_WRAPPER_FULL_SELECTOR).unwrap();
    });

    // Group consecutive full-width images
    var groups = [];
    var currentGroup = [];

    this.$editor.children().each(function() {
      var $child = $(this);
      if ($child.is(Tt.JOURNAL_IMAGE_WRAPPER_FULL_SELECTOR)) {
        currentGroup.push(this);
      } else {
        if (currentGroup.length > 0) {
          groups.push(currentGroup);
          currentGroup = [];
        }
      }
    });

    // Don't forget the last group
    if (currentGroup.length > 0) {
      groups.push(currentGroup);
    }

    // Wrap each group
    groups.forEach(function(group) {
      $(group).wrapAll('<div class="' + Tt.JOURNAL_FULL_WIDTH_GROUP_CLASS + '"></div>');
    });
  };

  /**
   * Mark paragraphs that contain float-right images
   * This allows CSS to clear floats appropriately
   */
  EditorLayoutManager.prototype.markFloatParagraphs = function() {
    // Remove existing marks
    this.$editor.find('p').removeClass(Tt.JOURNAL_FLOAT_MARKER_CLASS);

    // Mark paragraphs with float-right images
    this.$editor.find('p').each(function() {
      var $p = $(this);
      if ($p.find(Tt.JOURNAL_IMAGE_WRAPPER_FLOAT_SELECTOR).length > 0) {
        $p.addClass(Tt.JOURNAL_FLOAT_MARKER_CLASS);
      }
    });
  };

  /**
   * Ensure all image wrappers have delete buttons
   * Called on page load to add buttons to wrappers from saved content
   */
  EditorLayoutManager.prototype.ensureDeleteButtons = function() {
    this.$editor.find(Tt.JOURNAL_IMAGE_WRAPPER_SELECTOR).each(function() {
      var $wrapper = $(this);

      // Check if delete button already exists
      if ($wrapper.find(EDITOR_TRANSIENT.SEL_DELETE_BTN).length === 0) {
        // Add delete button
        var $deleteBtn = $('<button>', {
          'class': EDITOR_TRANSIENT.CSS_DELETE_BTN,
          'type': 'button',
          'title': 'Remove image',
          'text': '×'
        });
        $wrapper.append($deleteBtn);
      }
    });
  };

  /**
   * Unified layout refresh method
   * Calls all layout methods in the correct order
   * This ensures consistent layout behavior across all operations
   */
  EditorLayoutManager.prototype.refreshLayout = function() {
    // 1. Ensure delete buttons exist (must happen before any other operations)
    this.ensureDeleteButtons();

    // 2. Wrap full-width image groups (affects DOM structure)
    this.wrapFullWidthImageGroups();

    // 3. Mark float paragraphs (depends on DOM structure being finalized)
    this.markFloatParagraphs();
  };

  /**
   * AutoSaveManager
   *
   * Manages automatic saving of journal content with debouncing and retry logic.
   *
   * This manager handles:
   * - Change detection (content, title, date, timezone, reference image)
   * - Debounced auto-save with 2-second delay
   * - Save execution with retry logic
   * - Status display updates
   */
  function AutoSaveManager(editor, autosaveUrl, csrfToken) {
    this.editor = editor;
    this.autosaveUrl = autosaveUrl;
    this.csrfToken = csrfToken;

    // Save state
    this.saveTimeout = null;
    this.maxTimeout = null;
    this.isSaving = false;
    this.retryCount = 0;
    this.hasUnsavedChanges = false;

    // Tracked values for change detection
    this.lastSavedHTML = '';
    this.lastSavedTitle = '';
    this.lastSavedDate = '';
    this.lastSavedTimezone = '';
    this.lastSavedReferenceImage = '';
  }

  /**
   * Initialize with current content as "saved" baseline
   */
  AutoSaveManager.prototype.initializeBaseline = function() {
    this.lastSavedHTML = this.editor.getCleanHTML();
    this.lastSavedTitle = this.editor.$titleInput.val() || '';
    this.lastSavedDate = this.editor.$dateInput.val() || '';
    this.lastSavedTimezone = this.editor.$timezoneInput.val() || '';
    this.lastSavedReferenceImage = this.editor.getReferenceImageId();
    this.hasUnsavedChanges = false;
  };

  /**
   * Check if content has changed since last save
   * Returns true if any field differs from last saved state
   */
  AutoSaveManager.prototype.detectChanges = function() {
    var htmlChanged = (this.editor.getCleanHTML() !== this.lastSavedHTML);
    var titleChanged = (this.editor.$titleInput.val() || '') !== this.lastSavedTitle;
    var dateChanged = (this.editor.$dateInput.val() || '') !== this.lastSavedDate;
    var timezoneChanged = (this.editor.$timezoneInput.val() || '') !== this.lastSavedTimezone;
    var referenceImageChanged = this.editor.getReferenceImageId() !== this.lastSavedReferenceImage;

    return htmlChanged || titleChanged || dateChanged || timezoneChanged || referenceImageChanged;
  };

  /**
   * Schedule a save with debouncing (2 second delay, 30 second max)
   * Call this method whenever content changes
   */
  AutoSaveManager.prototype.scheduleSave = function() {
    // Update change detection
    this.hasUnsavedChanges = this.detectChanges();

    if (this.hasUnsavedChanges) {
      this.editor.updateStatus('unsaved');
    }

    // Clear existing timeout
    if (this.saveTimeout) {
      clearTimeout(this.saveTimeout);
    }

    // Set maximum timeout on first change (30 seconds)
    if (!this.maxTimeout) {
      this.maxTimeout = setTimeout(function() {
        this.executeSave();
        this.maxTimeout = null;
      }.bind(this), 30000);
    }

    // Set new timeout (2 seconds)
    this.saveTimeout = setTimeout(function() {
      this.executeSave();
      // Clear max timeout since we saved via regular timeout
      if (this.maxTimeout) {
        clearTimeout(this.maxTimeout);
        this.maxTimeout = null;
      }
    }.bind(this), 2000);
  };

  /**
   * Execute save to server
   */
  AutoSaveManager.prototype.executeSave = function() {
    if (this.isSaving || !this.hasUnsavedChanges) {
      return;
    }

    this.isSaving = true;
    this.editor.updateStatus('saving');

    // Capture snapshot of what we're saving (prevents race conditions)
    var snapshot = {
      html: this.editor.getCleanHTML(),
      title: this.editor.$titleInput.val() || '',
      date: this.editor.$dateInput.val() || '',
      timezone: this.editor.$timezoneInput.val() || '',
      referenceImage: this.editor.getReferenceImageId()
    };

    var data = {
      text: snapshot.html,
      version: this.editor.currentVersion,
      new_title: snapshot.title,
      new_date: snapshot.date,
      new_timezone: snapshot.timezone
    };

    $.ajax({
      url: this.autosaveUrl,
      type: 'POST',
      contentType: 'application/json',
      data: JSON.stringify(data),
      headers: {
        'X-CSRFToken': this.csrfToken
      },
      success: function(response) {
        if (response.status === 'success') {
          // Update "last saved" to match what we just successfully saved
          this.lastSavedHTML = snapshot.html;
          this.lastSavedTitle = snapshot.title;
          this.lastSavedDate = snapshot.date;
          this.lastSavedTimezone = snapshot.timezone;
          this.lastSavedReferenceImage = snapshot.referenceImage;

          // Recheck if changes occurred during save
          this.hasUnsavedChanges = this.detectChanges();

          this.editor.currentVersion = response.version;
          this.editor.$editor.data('current-version', response.version);
          this.retryCount = 0;

          if (this.maxTimeout) {
            clearTimeout(this.maxTimeout);
            this.maxTimeout = null;
          }

          if (this.hasUnsavedChanges) {
            this.editor.updateStatus('unsaved');
          } else {
            this.editor.updateStatus('saved', response.modified_datetime);
          }
        } else {
          this.editor.updateStatus('error', response.message);
        }
      }.bind(this),
      error: function(xhr, status, error) {
        if (xhr.status === 409) {
          this.editor.handleVersionConflict(xhr.responseJSON);
        } else {
          console.error('Auto-save error:', error);
          var errorMessage = 'Network error';

          if (xhr.responseJSON && xhr.responseJSON.message) {
            errorMessage = xhr.responseJSON.message;
          }

          // Retry logic for server errors
          var shouldRetry = (xhr.status >= 500 || xhr.status === 0) && this.retryCount < 3;

          if (shouldRetry) {
            this.retryCount++;
            var delay = Math.pow(2, this.retryCount) * 1000;
            this.editor.updateStatus('error', 'Save failed - retrying (' + this.retryCount + '/3)...');

            setTimeout(function() {
              this.executeSave();
            }.bind(this), delay);
          } else {
            this.editor.updateStatus('error', errorMessage);
          }
        }
      }.bind(this),
      complete: function() {
        this.isSaving = false;
      }.bind(this)
    });
  };

  /**
   * JournalImagePicker
   *
   * Manages image selection in the journal image picker panel.
   *
   * Features:
   * - Single-click selection toggle
   * - Ctrl/Cmd+click for multi-select
   * - Shift+click for range selection
   * - Double-click to open Image Inspector modal
   * - Selection count badge display
   */
  function JournalImagePicker($panel) {
    this.$panel = $panel;
    this.selectedImages = new Set();
    this.lastSelectedIndex = null;

    // Initialize badge manager
    var $headerTitle = this.$panel.find('.journal-image-panel-header h5');
    this.badgeManager = new SelectionBadgeManager($headerTitle, 'selected-images-count');

    // Register with coordinator
    imageSelectionCoordinator.registerPicker(this.clearAllSelections.bind(this));

    this.init();
  }

  /**
   * Initialize image picker event handlers
   */
  JournalImagePicker.prototype.init = function() {
    var self = this;

    // Click handler for image selection
    $(document).on('click', Tt.JOURNAL_IMAGE_CARD_SELECTOR, function(e) {
      e.preventDefault();
      self.handleImageClick(this, e);
    });

    // Double-click handler for opening inspector modal
    $(document).on('dblclick', Tt.JOURNAL_IMAGE_CARD_SELECTOR, function(e) {
      e.preventDefault();
      self.handleImageDoubleClick(this);
    });
  };

  /**
   * Handle image card click with modifier key support
   */
  JournalImagePicker.prototype.handleImageClick = function(card, event) {
    var $card = $(card);
    var uuid = $card.data(Tt.JOURNAL_IMAGE_UUID_ATTR);
    var modifiers = getSelectionModifiers(event);

    if (modifiers.isShift && this.lastSelectedIndex !== null) {
      this.handleRangeSelection($card);
    } else if (modifiers.isCtrlOrCmd) {
      this.toggleSelection($card, uuid);
    } else {
      this.clearAllSelections();
      this.toggleSelection($card, uuid);
    }

    this.updateSelectionUI();
  };

  /**
   * Handle Shift+click range selection
   */
  JournalImagePicker.prototype.handleRangeSelection = function($clickedCard) {
    var $allCards = $(Tt.JOURNAL_IMAGE_CARD_SELECTOR);
    var clickedIndex = $allCards.index($clickedCard);
    var startIndex = Math.min(this.lastSelectedIndex, clickedIndex);
    var endIndex = Math.max(this.lastSelectedIndex, clickedIndex);

    for (var i = startIndex; i <= endIndex; i++) {
      var $card = $allCards.eq(i);
      var uuid = $card.data(Tt.JOURNAL_IMAGE_UUID_ATTR);
      this.selectedImages.add(uuid);
      $card.addClass(EDITOR_TRANSIENT.CSS_SELECTED);
    }
  };

  /**
   * Toggle selection state for a single image
   */
  JournalImagePicker.prototype.toggleSelection = function($card, uuid) {
    if (this.selectedImages.has(uuid)) {
      this.selectedImages.delete(uuid);
      $card.removeClass(EDITOR_TRANSIENT.CSS_SELECTED);
    } else {
      this.selectedImages.add(uuid);
      $card.addClass(EDITOR_TRANSIENT.CSS_SELECTED);
    }

    var $allCards = $(Tt.JOURNAL_IMAGE_CARD_SELECTOR);
    this.lastSelectedIndex = $allCards.index($card);
  };

  /**
   * Clear all selections
   */
  JournalImagePicker.prototype.clearAllSelections = function() {
    this.selectedImages.clear();
    $(Tt.JOURNAL_IMAGE_CARD_SELECTOR).removeClass(EDITOR_TRANSIENT.CSS_SELECTED);
    this.lastSelectedIndex = null;
  };

  /**
   * Update selection count badge UI
   */
  JournalImagePicker.prototype.updateSelectionUI = function() {
    var count = this.selectedImages.size;
    this.badgeManager.update(count);

    // Notify coordinator when selections change
    imageSelectionCoordinator.notifyPickerSelection(count > 0);
  };

  /**
   * Handle double-click to open Image Inspector modal
   */
  JournalImagePicker.prototype.handleImageDoubleClick = function(card) {
    var $card = $(card);
    var inspectUrl = $card.data('inspect-url');

    if (inspectUrl && typeof AN !== 'undefined' && AN.get) {
      AN.get(inspectUrl);
    }
  };

  /**
   * JournalEditor - Main editor class
   */
  function JournalEditor($editor) {
    this.$editor = $editor;
    this.$form = $editor.closest(Tt.JOURNAL_ENTRY_FORM_SELECTOR);
    this.$titleInput = this.$form.find('#' + Tt.JOURNAL_TITLE_INPUT_ID);
    this.$dateInput = this.$form.find('#' + Tt.JOURNAL_DATE_INPUT_ID);
    this.$timezoneInput = this.$form.find('#' + Tt.JOURNAL_TIMEZONE_INPUT_ID);
    this.$statusElement = this.$form.find('.' + Tt.JOURNAL_SAVE_STATUS_CLASS);

    this.entryPk = $editor.data(Tt.JOURNAL_ENTRY_PK_ATTR);
    this.currentVersion = $editor.data(Tt.JOURNAL_CURRENT_VERSION_ATTR) || 1;

    this.draggedElement = null;
    this.dragSource = null; // 'picker' or 'editor'

    // Editor image selection state
    this.selectedEditorImages = new Set();
    this.lastSelectedEditorIndex = null;

    // Initialize badge manager for editor selections
    this.editorBadgeManager = new SelectionBadgeManager(this.$statusElement, 'selected-editor-images-count');

    // Register with coordinator
    imageSelectionCoordinator.registerEditor(this.clearEditorImageSelections.bind(this));

    // Initialize managers
    this.editorLayoutManager = new EditorLayoutManager(this.$editor);

    var autosaveUrl = $editor.data(Tt.JOURNAL_AUTOSAVE_URL_ATTR);
    var csrfToken = this.getCSRFToken();
    this.autoSaveManager = new AutoSaveManager(this, autosaveUrl, csrfToken);

    // Initialize image picker (if panel exists)
    var $imagePanel = $('.journal-image-panel');
    if ($imagePanel.length > 0) {
      this.imagePicker = new JournalImagePicker($imagePanel);
    }

    this.init();
  }

  /**
   * Initialize the editor
   */
  JournalEditor.prototype.init = function() {
    if (!this.$editor.length) {
      return;
    }

    // Initialize autosave baseline with current content
    this.autoSaveManager.initializeBaseline();
    this.updateStatus('saved');

    // Initialize ContentEditable
    this.initContentEditable();

    // Setup autosave handlers
    this.setupAutosave();

    // Setup drag-and-drop for image insertion
    this.setupImageDragDrop();

    // Setup image click to inspect
    this.setupImageClickToInspect();

    // Setup image selection
    this.setupImageSelection();

    // Setup image reordering
    this.setupImageReordering();

    // Setup image removal
    this.setupImageRemoval();

    // Setup keyboard navigation
    this.setupKeyboardNavigation();
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

    // Handle paste - strip formatting and sanitize
    this.$editor.on('paste', function(e) {
      e.preventDefault();
      var text = (e.originalEvent.clipboardData || window.clipboardData).getData('text/plain');
      document.execCommand('insertText', false, text);
    });

    // Prevent dropping files directly into editor (would show file:// URLs)
    this.$editor.on('drop', function(e) {
      if (e.originalEvent.dataTransfer.files.length > 0) {
        e.preventDefault();
        return false;
      }
    });

    // Handle Enter key to ensure proper paragraph structure
    this.$editor.on('keydown', function(e) {
      if (e.key === 'Enter' && !e.shiftKey) {
        // Let browser handle it, but ensure we get <p> tags
        document.execCommand('defaultParagraphSeparator', false, 'p');
      }
    });
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

    // Track metadata changes
    this.$titleInput.on('input', function() {
      self.handleContentChange();
    });

    this.$dateInput.on('change', function() {
      self.handleContentChange();
    });

    this.$timezoneInput.on('change', function() {
      self.handleContentChange();
    });
  };

  /**
   * Handle content change
   */
  JournalEditor.prototype.handleContentChange = function() {
    // Refresh layout (groups and float markers, but NOT delete buttons - they already exist)
    // Note: We skip delete buttons here since they're only needed on initial load
    this.editorLayoutManager.wrapFullWidthImageGroups();
    this.editorLayoutManager.markFloatParagraphs();

    // Schedule autosave (handles change detection and debouncing)
    this.autoSaveManager.scheduleSave();
  };


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

    return $clone.html();
  };

  /**
   * Get current reference image ID
   * TODO: Implement when reference image UI is added
   */
  JournalEditor.prototype.getReferenceImageId = function() {
    // Placeholder - will be implemented when reference image selection is added
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
      AN.processModalAction(data.modal);
    }
  };

  /**
   * Update save status display
   */
  JournalEditor.prototype.updateStatus = function(status, message) {
    var statusText = '';
    var statusClass = 'badge-secondary';

    switch (status) {
      case 'saved':
        statusText = 'Saved';
        statusClass = 'badge-success';
        if (message) {
          var savedDate = new Date(message);
          var now = new Date();
          var diffSeconds = Math.floor((now - savedDate) / 1000);

          if (diffSeconds < 60) {
            statusText = 'Saved ' + diffSeconds + ' seconds ago';
          } else {
            var diffMinutes = Math.floor(diffSeconds / 60);
            statusText = 'Saved ' + diffMinutes + ' minutes ago';
          }
        }
        break;
      case 'unsaved':
        statusText = 'Unsaved changes';
        statusClass = 'badge-warning';
        break;
      case 'saving':
        statusText = 'Saving...';
        statusClass = 'badge-info';
        break;
      case 'error':
        statusText = message || 'Error saving';
        statusClass = 'badge-danger';
        break;
    }

    this.$statusElement
      .removeClass('badge-secondary badge-success badge-warning badge-info badge-danger')
      .addClass(statusClass)
      .text(statusText);
  };

  /**
   * Setup drag-and-drop for image insertion from picker
   */
  JournalEditor.prototype.setupImageDragDrop = function() {
    var self = this;

    // Make picker images draggable (already set in HTML)
    // Handle dragstart from picker
    $(document).on('dragstart', Tt.JOURNAL_IMAGE_CARD_SELECTOR, function(e) {
      self.draggedElement = this;
      self.dragSource = 'picker';

      // Update visual feedback (handles multi-image .dragging and count badge)
      self.updateDraggingVisuals(true);

      // Set drag data
      e.originalEvent.dataTransfer.effectAllowed = 'copy';
      e.originalEvent.dataTransfer.setData('text/plain', ''); // Required for Firefox
    });

    // Handle dragend from picker
    $(document).on('dragend', Tt.JOURNAL_IMAGE_CARD_SELECTOR, function(e) {
      // Clean up visual feedback (handles multi-image .dragging and count badge)
      self.updateDraggingVisuals(false);
      self.clearDropZones();
      self.draggedElement = null;
      self.dragSource = null;
    });

    // Editor drag events
    this.$editor.on('dragover', function(e) {
      e.preventDefault();

      // Set appropriate drop effect based on drag source
      if (self.dragSource === 'editor') {
        e.originalEvent.dataTransfer.dropEffect = 'move';
      } else {
        e.originalEvent.dataTransfer.dropEffect = 'copy';
      }

      // Show drop zones for both picker and editor drags
      if (self.dragSource === 'picker' || self.dragSource === 'editor') {
        self.showDropZones(e);
      }
    });

    this.$editor.on('dragenter', function(e) {
      if (self.dragSource === 'picker' || self.dragSource === 'editor') {
        $(this).addClass(EDITOR_TRANSIENT.CSS_DRAG_OVER);
      }
    });

    this.$editor.on('dragleave', function(e) {
      // Only remove if we're leaving the editor completely
      if (!$(e.relatedTarget).closest('.' + Tt.JOURNAL_EDITOR_CLASS).length) {
        $(this).removeClass(EDITOR_TRANSIENT.CSS_DRAG_OVER);
        self.clearDropZones();
      }
    });

    this.$editor.on('drop', function(e) {
      e.preventDefault();
      e.stopPropagation();

      $(this).removeClass(EDITOR_TRANSIENT.CSS_DRAG_OVER);

      if (self.dragSource === 'picker' && self.draggedElement) {
        self.handleImageDrop(e);
      } else if (self.dragSource === 'editor' && self.draggedElement) {
        self.handleImageReorder(e);
      }

      self.clearDropZones();
    });
  };

  /**
   * Show drop zones based on mouse position
   */
  JournalEditor.prototype.showDropZones = function(e) {
    var $target = $(e.target);
    var $paragraph = $target.closest('p');
    var $imageWrapper = $target.closest(Tt.JOURNAL_IMAGE_WRAPPER_FULL_SELECTOR);

    // Clear existing indicators
    this.clearDropZones();

    if ($paragraph.length && $paragraph.parent().is(this.$editor)) {
      // Mouse is over a paragraph - show paragraph drop zone
      $paragraph.addClass(EDITOR_TRANSIENT.CSS_DROP_ZONE_ACTIVE);
    } else if ($imageWrapper.length && $imageWrapper.closest(this.$editor).length) {
      // Mouse is over a full-width image - highlight it to show insertion point
      // (wrapper may be inside .full-width-image-group, so check if it's within editor)
      $imageWrapper.addClass(EDITOR_TRANSIENT.CSS_DROP_ZONE_ACTIVE);
    } else {
      // Mouse is between paragraphs/images - show between indicator
      var mouseY = e.clientY;
      var $children = this.$editor.children('p, ' + Tt.JOURNAL_IMAGE_WRAPPER_FULL_SELECTOR + ', .' + Tt.JOURNAL_FULL_WIDTH_GROUP_CLASS);

      $children.each(function() {
        var rect = this.getBoundingClientRect();
        var betweenTop = rect.top - 20;
        var betweenBottom = rect.top + 20;

        if (mouseY >= betweenTop && mouseY <= betweenBottom) {
          var $indicator = $('<div class="' + EDITOR_TRANSIENT.CSS_DROP_ZONE_BETWEEN + '"></div>');
          $(this).before($indicator);
          return false;
        }
      });
    }
  };

  /**
   * Clear drop zone indicators
   */
  JournalEditor.prototype.clearDropZones = function() {
    this.$editor.find('p').removeClass(EDITOR_TRANSIENT.CSS_DROP_ZONE_ACTIVE);
    this.$editor.find(Tt.JOURNAL_IMAGE_WRAPPER_SELECTOR).removeClass(EDITOR_TRANSIENT.CSS_DROP_ZONE_ACTIVE);
    this.$editor.find('.' + EDITOR_TRANSIENT.CSS_DROP_ZONE_BETWEEN).remove();
  };

  /**
   * Handle image drop into editor (supports multi-image drop)
   */
  JournalEditor.prototype.handleImageDrop = function(e) {
    if (!this.draggedElement) {
      return;
    }

    // Get images to insert (1 or many)
    var imagesToInsert = this.getPickerImagesToInsert();
    if (imagesToInsert.length === 0) {
      return;
    }

    // Determine drop layout and target (same logic as before)
    var $target = $(e.target);
    var $paragraph = $target.closest('p');
    var $imageWrapper = $target.closest(Tt.JOURNAL_IMAGE_WRAPPER_FULL_SELECTOR);

    var layout = LAYOUT_VALUES.FULL_WIDTH;
    var $insertTarget = null;

    if ($paragraph.length && $paragraph.parent().is(this.$editor)) {
      // Dropped into a paragraph - float-right layout
      layout = LAYOUT_VALUES.FLOAT_RIGHT;
      $insertTarget = $paragraph;
    } else if ($imageWrapper.length && $imageWrapper.closest(this.$editor).length) {
      // Dropped onto an existing full-width image - insert after it (into same group)
      layout = LAYOUT_VALUES.FULL_WIDTH;
      $insertTarget = $imageWrapper;
    } else {
      // Dropped between paragraphs/images - full-width layout
      layout = LAYOUT_VALUES.FULL_WIDTH;

      // Find the closest paragraph or full-width group to insert before/after
      var mouseY = e.clientY;
      var $children = this.$editor.children('p, ' + Tt.JOURNAL_IMAGE_WRAPPER_FULL_SELECTOR + ', .' + Tt.JOURNAL_FULL_WIDTH_GROUP_CLASS);
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

      $insertTarget = $(closestElement);
    }

    // Insert each image using existing logic
    var $lastInserted = null;
    for (var i = 0; i < imagesToInsert.length; i++) {
      var imageData = imagesToInsert[i];

      // Create wrapped image element
      var $wrappedImage = this.createImageElement(
        imageData.uuid,
        imageData.url,
        imageData.caption,
        layout
      );

      // Insert the wrapped image
      if (!$lastInserted) {
        // First insertion - use original target logic
        if (layout === LAYOUT_VALUES.FLOAT_RIGHT) {
          // Insert at beginning of paragraph for float-right
          $insertTarget.prepend($wrappedImage);
        } else if ($insertTarget.is(Tt.JOURNAL_IMAGE_WRAPPER_FULL_SELECTOR)) {
          // Insert after the target image wrapper (will be in same group)
          $insertTarget.after($wrappedImage);
        } else {
          // Insert before the target element for full-width
          $insertTarget.before($wrappedImage);
        }
      } else {
        // Subsequent insertions - chain after last inserted
        if (layout === LAYOUT_VALUES.FLOAT_RIGHT) {
          // For float-right, prepend each one (so they appear in order)
          $insertTarget.prepend($wrappedImage);
        } else {
          // For full-width, insert after last
          $lastInserted.after($wrappedImage);
        }
      }

      $lastInserted = $wrappedImage;
    }

    // NOW enforce 2-image limit per paragraph (after all insertions)
    if (layout === LAYOUT_VALUES.FLOAT_RIGHT) {
      var existingWrappers = $insertTarget.find(Tt.JOURNAL_IMAGE_WRAPPER_FLOAT_SELECTOR);
      while (existingWrappers.length > 2) {
        // Remove rightmost (last) wrapper
        existingWrappers.last().remove();
        existingWrappers = $insertTarget.find(Tt.JOURNAL_IMAGE_WRAPPER_FLOAT_SELECTOR);
      }
    }

    // Trigger layout refresh + autosave (ONCE, not per image)
    this.handleContentChange();

    // Clear picker selections if multiple images were inserted
    if (this.imagePicker && imagesToInsert.length > 1) {
      this.imagePicker.clearAllSelections();
    }
  };


  /**
   * Create image element with proper attributes
   */
  JournalEditor.prototype.createImageElement = function(uuid, url, caption, layout) {
    // Create the image element
    var $img = $('<img>', {
      'src': url,
      'alt': caption,
      'class': Tt.JOURNAL_IMAGE_CLASS,
    });
    $img.attr('data-' + Tt.JOURNAL_UUID_ATTR, uuid);
    $img.attr('draggable', true);

    // Create wrapper with layout attribute
    var $wrapper = $('<span>', {
      'class': Tt.JOURNAL_IMAGE_WRAPPER_CLASS
    });
    $wrapper.attr('data-' + Tt.JOURNAL_LAYOUT_ATTR, layout);

    // Create caption span if caption exists and is non-empty
    var $captionSpan = null;
    if (caption && $.trim(caption).length > 0) {
      $captionSpan = $('<span>', {
        'class': 'trip-image-caption',
        'text': caption
      });
    }

    // Create delete button (TRANSIENT)
    var $deleteBtn = $('<button>', {
      'class': EDITOR_TRANSIENT.CSS_DELETE_BTN,
      'type': 'button',
      'title': 'Remove image',
      'text': '×'
    });

    // Assemble: wrapper contains image, optional caption, and delete button
    $wrapper.append($img);
    if ($captionSpan) {
      $wrapper.append($captionSpan);
    }
    $wrapper.append($deleteBtn);

    return $wrapper;
  };

  /**
   * Setup image double-click to inspect
   * Single-click is reserved for future selection feature
   */
  JournalEditor.prototype.setupImageClickToInspect = function() {
    var self = this;

    // Double-click to open Image Inspector modal (consistent with picker behavior)
    this.$editor.on('dblclick', Tt.JOURNAL_IMAGE_SELECTOR, function(e) {
      e.preventDefault();
      e.stopPropagation();

      var $img = $(this);
      var uuid = $img.data('uuid');

      // Get inspect URL from the corresponding picker card
      var $pickerCard = $(Tt.JOURNAL_IMAGE_CARD_SELECTOR + '[data-' + Tt.JOURNAL_IMAGE_UUID_ATTR + '="' + uuid + '"]');
      var inspectUrl = $pickerCard.data('inspect-url');

      if (inspectUrl) {
        AN.get(inspectUrl);
      } else {
        console.warn('No inspect URL found for image:', uuid);
      }
    });

    // Single-click handler - now implemented for selection
    this.$editor.on('click', Tt.JOURNAL_IMAGE_SELECTOR, function(e) {
      e.preventDefault();
      e.stopPropagation();

      self.handleEditorImageClick(this, e);
    });

    // Prevent default drag on existing images (handled in setupImageReordering)
    this.$editor.on('dragstart', Tt.JOURNAL_IMAGE_SELECTOR, function(e) {
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
   * Get picker images to insert (for multi-image drag-and-drop)
   * Returns array of image data objects: [{uuid, url, caption}, ...]
   */
  JournalEditor.prototype.getPickerImagesToInsert = function() {
    if (!this.draggedElement || !this.imagePicker) {
      return [];
    }

    var $draggedCard = $(this.draggedElement);
    var draggedUuid = $draggedCard.data(Tt.JOURNAL_IMAGE_UUID_ATTR);

    // Check if dragged card is part of selection
    var isDraggedSelected = this.imagePicker.selectedImages.has(draggedUuid);

    var imagesToInsert = [];

    if (isDraggedSelected && this.imagePicker.selectedImages.size > 1) {
      // Multi-image insert: get all selected cards in DOM order
      var selectedUuids = this.imagePicker.selectedImages;
      $(Tt.JOURNAL_IMAGE_CARD_SELECTOR).each(function() {
        var $card = $(this);
        var uuid = $card.data(Tt.JOURNAL_IMAGE_UUID_ATTR);
        if (selectedUuids.has(uuid)) {
          imagesToInsert.push({
            uuid: uuid,
            url: $card.data('image-url'),
            caption: $card.data('caption') || 'Untitled'
          });
        }
      });
    } else {
      // Single-image insert: just the dragged card
      imagesToInsert.push({
        uuid: draggedUuid,
        url: $draggedCard.data('image-url'),
        caption: $draggedCard.data('caption') || 'Untitled'
      });
    }

    return imagesToInsert;
  };

  /**
   * Get editor wrappers to move (for multi-image drag-and-drop)
   * Returns array of jQuery wrapper objects: [$wrapper1, $wrapper2, ...]
   */
  JournalEditor.prototype.getEditorWrappersToMove = function() {
    if (!this.draggedElement) {
      return [];
    }

    var $draggedWrapper = $(this.draggedElement);
    var $draggedImg = $draggedWrapper.find(Tt.JOURNAL_IMAGE_SELECTOR);
    var draggedUuid = $draggedImg.data(Tt.JOURNAL_UUID_ATTR);

    // Check if dragged wrapper is part of selection
    var isDraggedSelected = this.selectedEditorImages.has(draggedUuid);

    var wrappersToMove = [];

    if (isDraggedSelected && this.selectedEditorImages.size > 1) {
      // Multi-image move: get all selected wrappers in DOM order
      var selectedUuids = this.selectedEditorImages;
      var self = this;
      this.$editor.find(Tt.JOURNAL_IMAGE_WRAPPER_SELECTOR).each(function() {
        var $wrapper = $(this);
        var $img = $wrapper.find(Tt.JOURNAL_IMAGE_SELECTOR);
        var uuid = $img.data(Tt.JOURNAL_UUID_ATTR);
        if (selectedUuids.has(uuid)) {
          wrappersToMove.push($wrapper);
        }
      });
    } else {
      // Single-image move: just the dragged wrapper
      wrappersToMove.push($draggedWrapper);
    }

    return wrappersToMove;
  };

  /**
   * Update dragging visuals (count badge and .dragging class)
   * @param {boolean} isDragging - true to show, false to hide
   */
  JournalEditor.prototype.updateDraggingVisuals = function(isDragging) {
    if (isDragging) {
      var count = 0;
      var $elementsToMark = [];

      if (this.dragSource === 'picker' && this.imagePicker) {
        var draggedUuid = $(this.draggedElement).data(Tt.JOURNAL_IMAGE_UUID_ATTR);
        var isDraggedSelected = this.imagePicker.selectedImages.has(draggedUuid);

        if (isDraggedSelected && this.imagePicker.selectedImages.size > 1) {
          // Mark all selected cards
          count = this.imagePicker.selectedImages.size;
          var selectedUuids = this.imagePicker.selectedImages;
          $(Tt.JOURNAL_IMAGE_CARD_SELECTOR).each(function() {
            var $card = $(this);
            if (selectedUuids.has($card.data(Tt.JOURNAL_IMAGE_UUID_ATTR))) {
              $elementsToMark.push($card);
            }
          });
        } else {
          // Just the dragged card
          count = 1;
          $elementsToMark.push($(this.draggedElement));
        }
      } else if (this.dragSource === 'editor') {
        var $draggedWrapper = $(this.draggedElement);
        var $draggedImg = $draggedWrapper.find(Tt.JOURNAL_IMAGE_SELECTOR);
        var draggedUuid = $draggedImg.data(Tt.JOURNAL_UUID_ATTR);
        var isDraggedSelected = this.selectedEditorImages.has(draggedUuid);

        if (isDraggedSelected && this.selectedEditorImages.size > 1) {
          // Mark all selected wrappers
          count = this.selectedEditorImages.size;
          var selectedUuids = this.selectedEditorImages;
          var self = this;
          this.$editor.find(Tt.JOURNAL_IMAGE_WRAPPER_SELECTOR).each(function() {
            var $wrapper = $(this);
            var $img = $wrapper.find(Tt.JOURNAL_IMAGE_SELECTOR);
            if (selectedUuids.has($img.data(Tt.JOURNAL_UUID_ATTR))) {
              $elementsToMark.push($wrapper);
            }
          });
        } else {
          // Just the dragged wrapper
          count = 1;
          $elementsToMark.push($draggedWrapper);
        }
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
      $(Tt.JOURNAL_IMAGE_CARD_SELECTOR).removeClass(EDITOR_TRANSIENT.CSS_DRAGGING);
      this.$editor.find(Tt.JOURNAL_IMAGE_WRAPPER_SELECTOR).removeClass(EDITOR_TRANSIENT.CSS_DRAGGING);

      // Remove count badges
      $('.drag-count-badge').remove();
    }
  };

  /**
   * Handle editor image click with modifier key support
   */
  JournalEditor.prototype.handleEditorImageClick = function(img, event) {
    var $img = $(img);
    var uuid = $img.data(Tt.JOURNAL_UUID_ATTR);
    var modifiers = getSelectionModifiers(event);

    // Clear text selection (contenteditable conflict prevention)
    this.clearTextSelection();

    if (modifiers.isShift && this.lastSelectedEditorIndex !== null) {
      this.handleEditorRangeSelection($img);
    } else if (modifiers.isCtrlOrCmd) {
      this.toggleEditorImageSelection($img, uuid);
    } else {
      this.clearEditorImageSelections();
      this.toggleEditorImageSelection($img, uuid);
    }

    this.updateEditorSelectionUI();
  };

  /**
   * Clear text selection in contenteditable
   */
  JournalEditor.prototype.clearTextSelection = function() {
    if (window.getSelection) {
      var selection = window.getSelection();
      if (selection.rangeCount > 0) {
        selection.removeAllRanges();
      }
    }
  };

  /**
   * Handle Shift+click range selection for editor images
   */
  JournalEditor.prototype.handleEditorRangeSelection = function($clickedImg) {
    var $allImages = this.$editor.find(Tt.JOURNAL_IMAGE_SELECTOR);
    var clickedIndex = $allImages.index($clickedImg);
    var startIndex = Math.min(this.lastSelectedEditorIndex, clickedIndex);
    var endIndex = Math.max(this.lastSelectedEditorIndex, clickedIndex);

    for (var i = startIndex; i <= endIndex; i++) {
      var $img = $allImages.eq(i);
      var uuid = $img.data(Tt.JOURNAL_UUID_ATTR);
      this.selectedEditorImages.add(uuid);
      $img.closest(Tt.JOURNAL_IMAGE_WRAPPER_SELECTOR).addClass(EDITOR_TRANSIENT.CSS_SELECTED);
    }
  };

  /**
   * Toggle selection state for a single editor image
   */
  JournalEditor.prototype.toggleEditorImageSelection = function($img, uuid) {
    var $wrapper = $img.closest(Tt.JOURNAL_IMAGE_WRAPPER_SELECTOR);

    if (this.selectedEditorImages.has(uuid)) {
      this.selectedEditorImages.delete(uuid);
      $wrapper.removeClass(EDITOR_TRANSIENT.CSS_SELECTED);
    } else {
      this.selectedEditorImages.add(uuid);
      $wrapper.addClass(EDITOR_TRANSIENT.CSS_SELECTED);
    }

    var $allImages = this.$editor.find(Tt.JOURNAL_IMAGE_SELECTOR);
    this.lastSelectedEditorIndex = $allImages.index($img);
  };

  /**
   * Clear all editor image selections
   */
  JournalEditor.prototype.clearEditorImageSelections = function() {
    this.selectedEditorImages.clear();
    this.$editor.find(Tt.JOURNAL_IMAGE_WRAPPER_SELECTOR).removeClass(EDITOR_TRANSIENT.CSS_SELECTED);
    this.lastSelectedEditorIndex = null;
    this.updateEditorSelectionUI();
  };

  /**
   * Update editor selection count badge UI
   */
  JournalEditor.prototype.updateEditorSelectionUI = function() {
    var count = this.selectedEditorImages.size;
    this.editorBadgeManager.update(count);

    // Notify coordinator when selections change
    imageSelectionCoordinator.notifyEditorSelection(count > 0);
  };

  /**
   * Setup image reordering within editor
   */
  JournalEditor.prototype.setupImageReordering = function() {
    var self = this;

    // Handle dragstart for images already in editor
    this.$editor.on('dragstart', Tt.JOURNAL_IMAGE_SELECTOR, function(e) {
      var $img = $(this);
      var $wrapper = $img.closest(Tt.JOURNAL_IMAGE_WRAPPER_SELECTOR);

      self.draggedElement = $wrapper[0]; // Store wrapper, not image
      self.dragSource = 'editor';

      // Update visual feedback (handles multi-image .dragging and count badge)
      self.updateDraggingVisuals(true);

      e.originalEvent.dataTransfer.effectAllowed = 'move';
      e.originalEvent.dataTransfer.setData('text/plain', '');
    });

    // Handle dragend for images in editor
    this.$editor.on('dragend', Tt.JOURNAL_IMAGE_SELECTOR, function(e) {
      // Clean up visual feedback (handles multi-image .dragging and count badge)
      self.updateDraggingVisuals(false);
      self.clearDropZones();
      self.draggedElement = null;
      self.dragSource = null;
    });

    // Drop handling is now unified in setupImageDragDrop()
    // No separate drop handler needed here
  };

  /**
   * Handle image reordering within editor (supports multi-image move)
   */
  JournalEditor.prototype.handleImageReorder = function(e) {
    if (!this.draggedElement) {
      return;
    }

    // Get wrappers to move (1 or many)
    var wrappersToMove = this.getEditorWrappersToMove();
    if (wrappersToMove.length === 0) {
      return;
    }

    // CRITICAL: Detach all wrappers first to prevent DOM issues
    // Store them in an array with their DOM elements
    var wrappersData = [];
    for (var i = 0; i < wrappersToMove.length; i++) {
      var $wrapper = wrappersToMove[i];
      var oldLayout = $wrapper.attr('data-' + Tt.JOURNAL_LAYOUT_ATTR);
      wrappersData.push({
        element: $wrapper.get(0),  // Store raw DOM element
        $wrapper: $wrapper,
        oldLayout: oldLayout
      });
      $wrapper.detach();  // Detach (not remove) to preserve event handlers
    }

    // Determine target layout and position (same logic as before)
    var $target = $(e.target);
    var $paragraph = $target.closest('p');
    var newLayout = LAYOUT_VALUES.FULL_WIDTH;
    var $insertTarget = null;
    var insertMode = null; // 'prepend-paragraph', 'after-wrapper', 'before-element', 'append-editor'

    if ($paragraph.length && $paragraph.parent().is(this.$editor)) {
      // Dropped into a paragraph
      newLayout = LAYOUT_VALUES.FLOAT_RIGHT;
      $insertTarget = $paragraph;
      insertMode = 'prepend-paragraph';
    } else {
      // Dropped outside paragraphs (full-width area)
      newLayout = LAYOUT_VALUES.FULL_WIDTH;

      // Check if dropping on/near a specific full-width image wrapper
      var $targetImageWrapper = $target.closest(Tt.JOURNAL_IMAGE_WRAPPER_FULL_SELECTOR);

      if ($targetImageWrapper.length && $targetImageWrapper.closest(this.$editor).length) {
        // Dropping on a specific full-width image - insert after it (within same group)
        $insertTarget = $targetImageWrapper;
        insertMode = 'after-wrapper';
      } else {
        // Dropped between major sections - find closest paragraph or group
        var mouseY = e.clientY;
        var $children = this.$editor.children('p, .' + Tt.JOURNAL_FULL_WIDTH_GROUP_CLASS);
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
          $insertTarget = $(closestElement);
          insertMode = 'before-element';
        } else {
          $insertTarget = this.$editor;
          insertMode = 'append-editor';
        }
      }
    }

    // Insert each wrapper using existing logic
    var $lastMoved = null;
    for (var i = 0; i < wrappersData.length; i++) {
      var wrapperData = wrappersData[i];
      var $wrapper = wrapperData.$wrapper;

      // Insert wrapper at target
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
          // For float-right, prepend each one (so they appear in order)
          $insertTarget.prepend($wrapper);
        } else {
          // For full-width, insert after last moved
          $lastMoved.after($wrapper);
        }
      }

      // Update layout attribute if changed
      if (newLayout !== wrapperData.oldLayout) {
        $wrapper.attr('data-' + Tt.JOURNAL_LAYOUT_ATTR, newLayout);
      }

      $lastMoved = $wrapper;
    }

    // NOW enforce 2-image limit per paragraph (after all insertions)
    if (insertMode === 'prepend-paragraph') {
      var existingWrappers = $insertTarget.find(Tt.JOURNAL_IMAGE_WRAPPER_FLOAT_SELECTOR);
      while (existingWrappers.length > 2) {
        // Remove rightmost (last) wrapper
        existingWrappers.last().remove();
        existingWrappers = $insertTarget.find(Tt.JOURNAL_IMAGE_WRAPPER_FLOAT_SELECTOR);
      }
    }

    // Trigger layout refresh + autosave (ONCE, not per wrapper)
    this.handleContentChange();

    // Clear editor selections if multiple wrappers were moved
    if (wrappersToMove.length > 1) {
      this.clearEditorImageSelections();
    }
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

      var $wrapper = $(this).closest(Tt.JOURNAL_IMAGE_WRAPPER_SELECTOR);
      var $img = $wrapper.find(Tt.JOURNAL_IMAGE_SELECTOR);

      self.removeImage($img);
    });

    // Keyboard support for image deletion
    this.$editor.on('keydown', function(e) {
      if (e.key === 'Delete' || e.key === 'Backspace') {
        var selection = window.getSelection();
        if (selection.rangeCount > 0) {
          var range = selection.getRangeAt(0);
          var node = range.startContainer;

          // Check if we're at an image
          var $img = null;
          if (node.nodeType === Node.ELEMENT_NODE && $(node).is(Tt.JOURNAL_IMAGE_SELECTOR)) {
            $img = $(node);
          } else if (node.nodeType === Node.ELEMENT_NODE) {
            $img = $(node).find(Tt.JOURNAL_IMAGE_SELECTOR).first();
          }

          if ($img && $img.length) {
            e.preventDefault();
            self.removeImage($img);
          }
        }
      }
    });
  };

  /**
   * Remove image from editor
   */
  JournalEditor.prototype.removeImage = function($img) {
    // Images are always wrapped, so remove the wrapper
    var $wrapper = $img.closest(Tt.JOURNAL_IMAGE_WRAPPER_SELECTOR);
    $wrapper.remove();

    // Trigger autosave
    this.handleContentChange();

    // Update image panel badges (if applicable)
    // This would be handled by the backend on next autosave
  };

  /**
   * Setup keyboard navigation and shortcuts
   */
  JournalEditor.prototype.setupKeyboardNavigation = function() {
    var self = this;

    // Global keyboard shortcut handler
    $(document).on('keydown', function(e) {
      self.handleGlobalKeyboardShortcut(e);
    });
  };

  /**
   * Global keyboard shortcut handler
   * Routes shortcuts based on active context
   */
  JournalEditor.prototype.handleGlobalKeyboardShortcut = function(e) {
    var context = this.determineActiveContext();
    var isCtrlOrCmd = e.ctrlKey || e.metaKey;

    // GLOBAL shortcuts (work in all contexts)
    // Ctrl/Cmd+/ - Show keyboard shortcuts help (STUB)
    if (isCtrlOrCmd && e.key === '/') {
      e.preventDefault();
      this.showKeyboardShortcutsHelp();
      return;
    }

    // TEXT EDITING CONTEXT shortcuts
    if (context === 'text') {
      // Ctrl/Cmd+B - Bold
      if (isCtrlOrCmd && e.key === 'b') {
        e.preventDefault();
        document.execCommand('bold', false, null);
        return;
      }

      // Ctrl/Cmd+I - Italic
      if (isCtrlOrCmd && e.key === 'i') {
        e.preventDefault();
        document.execCommand('italic', false, null);
        return;
      }

      // All other text shortcuts: preserve browser defaults
      return;
    }

    // PICKER IMAGES CONTEXT shortcuts
    if (context === 'picker') {
      // Escape - Clear all selections
      if (e.key === 'Escape') {
        e.preventDefault();
        if (this.imagePicker) {
          this.imagePicker.clearAllSelections();
        }
        return;
      }

      // Delete/Backspace - Clear selection (same as Escape)
      if (e.key === 'Delete' || e.key === 'Backspace') {
        e.preventDefault();
        if (this.imagePicker) {
          this.imagePicker.clearAllSelections();
        }
        return;
      }

      // Ctrl/Cmd+R - Set representative image (STUB)
      if (isCtrlOrCmd && e.key === 'r') {
        e.preventDefault();
        this.setReferenceImageFromPicker();
        return;
      }

      return;
    }

    // EDITOR IMAGES CONTEXT shortcuts
    if (context === 'editor-images') {
      // Escape - Clear selections
      if (e.key === 'Escape') {
        e.preventDefault();
        this.clearEditorImageSelections();
        return;
      }

      // Delete/Backspace - Remove from editor
      if (e.key === 'Delete' || e.key === 'Backspace') {
        e.preventDefault();
        this.batchRemoveEditorImages(this.selectedEditorImages);
        return;
      }

      // Ctrl/Cmd+R - Set representative image (STUB)
      if (isCtrlOrCmd && e.key === 'r') {
        e.preventDefault();
        this.setReferenceImageFromEditor();
        return;
      }

      return;
    }
  };

  /**
   * Determine active context for keyboard shortcuts
   * Returns: 'text' | 'picker' | 'editor-images'
   *
   * Context Priority:
   * 1. Picker selections (highest priority)
   * 2. Editor image selections
   * 3. Text editing (default)
   */
  JournalEditor.prototype.determineActiveContext = function() {
    // Check if picker has selections
    if (this.imagePicker && this.imagePicker.selectedImages.size > 0) {
      return 'picker';
    }

    // Check if editor has image selections
    if (this.selectedEditorImages.size > 0) {
      return 'editor-images';
    }

    // Default to text editing context
    return 'text';
  };

  /**
   * Batch remove editor images by UUID set
   * @param {Set} uuidSet - Set of UUIDs to remove
   */
  JournalEditor.prototype.batchRemoveEditorImages = function(uuidSet) {
    if (uuidSet.size === 0) {
      return;
    }

    // Find and remove all wrappers with matching UUIDs
    this.$editor.find(Tt.JOURNAL_IMAGE_WRAPPER_SELECTOR).each(function() {
      var $wrapper = $(this);
      var $img = $wrapper.find(Tt.JOURNAL_IMAGE_SELECTOR);
      var uuid = $img.data(Tt.JOURNAL_UUID_ATTR);

      if (uuidSet.has(uuid)) {
        $wrapper.remove();
      }
    });

    // Clear selections
    this.clearEditorImageSelections();

    // Trigger autosave
    this.handleContentChange();
  };

  /**
   * Set reference image from picker selection (STUB)
   * Entry point for future representative image feature
   */
  JournalEditor.prototype.setReferenceImageFromPicker = function() {
    if (!this.imagePicker || this.imagePicker.selectedImages.size === 0) {
      console.log('[Keyboard Shortcut] Ctrl+R: No picker images selected');
      return;
    }

    // Get first selected UUID
    var firstUuid = Array.from(this.imagePicker.selectedImages)[0];
    console.log('[Keyboard Shortcut] Ctrl+R: Set reference image from picker (STUB)', firstUuid);
    console.log('[Future Feature] This will set the reference image for the journal entry');
  };

  /**
   * Set reference image from editor selection (STUB)
   * Entry point for future representative image feature
   */
  JournalEditor.prototype.setReferenceImageFromEditor = function() {
    if (this.selectedEditorImages.size === 0) {
      console.log('[Keyboard Shortcut] Ctrl+R: No editor images selected');
      return;
    }

    // Get first selected UUID
    var firstUuid = Array.from(this.selectedEditorImages)[0];
    console.log('[Keyboard Shortcut] Ctrl+R: Set reference image from editor (STUB)', firstUuid);
    console.log('[Future Feature] This will set the reference image for the journal entry');
  };

  /**
   * Show keyboard shortcuts help modal
   * Opens editing help modal via AN.get() to fetch from server
   */
  JournalEditor.prototype.showKeyboardShortcutsHelp = function() {
    // Construct URL to editor help endpoint (no parameters needed)
    var helpUrl = '/journal/editor-help';

    // Use antinode.js to fetch and display modal
    if (typeof AN !== 'undefined' && AN.get) {
      AN.get(helpUrl);
    } else {
      console.error('Antinode.js not available');
    }
  };

  /**
   * Utility: Get CSRF token
   */
  JournalEditor.prototype.getCSRFToken = function() {
    return Cookies.get('csrftoken');
  };

  /**
   * Initialize editor on document ready
   */
  $(document).ready(function() {
    var $editor = $('#' + Tt.JOURNAL_EDITOR_ID);

    if ($editor.length && $editor.attr('contenteditable') === 'true') {
      editorInstance = new JournalEditor($editor);
    }
  });

  // Expose for debugging
  window.JournalEditor = {
    getInstance: function() {
      return editorInstance;
    }
  };

})(jQuery);
