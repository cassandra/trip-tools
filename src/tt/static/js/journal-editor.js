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
 * - Full keyboard navigation support
 *
 * ============================================================
 * HTML CONTRACT: PERSISTENT vs TRANSIENT
 * ============================================================
 *
 * PERSISTENT HTML (saved to database, visible in public view):
 * - <span class="trip-image-wrapper" data-layout="float-right|full-width">
 * - <img class="trip-image" data-uuid="..." src="..." alt="...">
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
      $(this).addClass(EDITOR_TRANSIENT.CSS_DRAGGING);

      // Set drag data
      e.originalEvent.dataTransfer.effectAllowed = 'copy';
      e.originalEvent.dataTransfer.setData('text/plain', ''); // Required for Firefox
    });

    // Handle dragend from picker
    $(document).on('dragend', Tt.JOURNAL_IMAGE_CARD_SELECTOR, function(e) {
      $(this).removeClass(EDITOR_TRANSIENT.CSS_DRAGGING);
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
   * Handle image drop into editor
   */
  JournalEditor.prototype.handleImageDrop = function(e) {
    if (!this.draggedElement) {
      return;
    }

    var $card = $(this.draggedElement);
    var imageUuid = $card.data('image-uuid');
    var imageUrl = $card.data('image-url');
    var caption = $card.data('caption') || 'Untitled';

    var $target = $(e.target);
    var $paragraph = $target.closest('p');
    var $imageWrapper = $target.closest(Tt.JOURNAL_IMAGE_WRAPPER_FULL_SELECTOR);

    var layout = LAYOUT_VALUES.FULL_WIDTH;
    var $insertTarget = null;

    if ($paragraph.length && $paragraph.parent().is(this.$editor)) {
      // Dropped into a paragraph - float-right layout
      layout = LAYOUT_VALUES.FLOAT_RIGHT;
      $insertTarget = $paragraph;

      // Check and enforce 2-image limit per paragraph
      var existingWrappers = $paragraph.find(Tt.JOURNAL_IMAGE_WRAPPER_FLOAT_SELECTOR);
      if (existingWrappers.length >= 2) {
        // Remove the rightmost wrapper (with image inside)
        existingWrappers.last().remove();
      }
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

    // Create wrapped image element
    var $wrappedImage = this.createImageElement(imageUuid, imageUrl, caption, layout);

    // Insert the wrapped image
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

    // Trigger autosave
    this.handleContentChange();
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

    // Create delete button
    var $deleteBtn = $('<button>', {
      'class': EDITOR_TRANSIENT.CSS_DELETE_BTN,
      'type': 'button',
      'title': 'Remove image',
      'text': '×'
    });

    // Assemble: wrapper contains image and delete button
    $wrapper.append($img, $deleteBtn);

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
      $wrapper.addClass(EDITOR_TRANSIENT.CSS_DRAGGING);

      e.originalEvent.dataTransfer.effectAllowed = 'move';
      e.originalEvent.dataTransfer.setData('text/plain', '');
    });

    // Handle dragend for images in editor
    this.$editor.on('dragend', Tt.JOURNAL_IMAGE_SELECTOR, function(e) {
      var $img = $(this);
      var $wrapper = $img.closest(Tt.JOURNAL_IMAGE_WRAPPER_SELECTOR);

      $wrapper.removeClass(EDITOR_TRANSIENT.CSS_DRAGGING);
      self.clearDropZones();
      self.draggedElement = null;
      self.dragSource = null;
    });

    // Drop handling is now unified in setupImageDragDrop()
    // No separate drop handler needed here
  };

  /**
   * Handle image reordering
   */
  JournalEditor.prototype.handleImageReorder = function(e) {
    if (!this.draggedElement) {
      return;
    }

    var $wrapper = $(this.draggedElement);
    var $target = $(e.target);
    var $paragraph = $target.closest('p');

    var oldLayout = $wrapper.data('layout');
    var newLayout = LAYOUT_VALUES.FULL_WIDTH;

    if ($paragraph.length && $paragraph.parent().is(this.$editor)) {
      // Dropped into a paragraph
      newLayout = LAYOUT_VALUES.FLOAT_RIGHT;

      // Remove from old location
      $wrapper.remove();

      // Check 2-image limit
      var existingWrappers = $paragraph.find(Tt.JOURNAL_IMAGE_WRAPPER_FLOAT_SELECTOR);
      if (existingWrappers.length >= 2) {
        existingWrappers.last().remove();
      }

      // Insert at beginning of paragraph
      $paragraph.prepend($wrapper);
    } else {
      // Dropped outside paragraphs (full-width area)
      newLayout = LAYOUT_VALUES.FULL_WIDTH;

      // Remove from old location
      $wrapper.remove();

      // Check if dropping on/near a specific full-width image wrapper
      var $targetImageWrapper = $target.closest(Tt.JOURNAL_IMAGE_WRAPPER_FULL_SELECTOR);

      if ($targetImageWrapper.length && $targetImageWrapper.closest(this.$editor).length) {
        // Dropping on a specific full-width image - insert after it (within same group)
        $targetImageWrapper.after($wrapper);
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

        // Insert before closest element
        if (closestElement) {
          $(closestElement).before($wrapper);
        } else {
          this.$editor.append($wrapper);
        }
      }
    }

    // Update layout attribute if changed
    if (newLayout !== oldLayout) {
      $wrapper.attr('data-' + Tt.JOURNAL_LAYOUT_ATTR, newLayout);
    }

    // Trigger autosave
    this.handleContentChange();
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
   * Setup keyboard navigation
   */
  JournalEditor.prototype.setupKeyboardNavigation = function() {
    var self = this;

    // Tab to navigate between images
    this.$editor.on('keydown', function(e) {
      if (e.key === 'Tab') {
        var $images = self.$editor.find(Tt.JOURNAL_IMAGE_SELECTOR);

        if ($images.length > 0) {
          var selection = window.getSelection();
          var currentNode = selection.anchorNode;

          // Find current image
          var currentIndex = -1;
          $images.each(function(index) {
            if (this === currentNode || $.contains(this, currentNode)) {
              currentIndex = index;
              return false;
            }
          });

          // Navigate to next/previous image
          var nextIndex = e.shiftKey ? currentIndex - 1 : currentIndex + 1;

          if (nextIndex >= 0 && nextIndex < $images.length) {
            e.preventDefault();
            var range = document.createRange();
            range.selectNode($images[nextIndex]);
            selection.removeAllRanges();
            selection.addRange(range);
          }
        }
      }
    });
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
