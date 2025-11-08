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
   * CONSTANTS - True magic strings that appear in multiple locations
   * These strings are used in both JavaScript and CSS, and changing them
   * requires updates in multiple files.
   */
  const EDITOR_CONSTANTS = {
    // CSS Classes - Persistent (saved to database)
    CSS_WRAPPER: 'trip-image-wrapper',
    CSS_IMAGE: 'trip-image',
    CSS_FULL_WIDTH_GROUP: 'full-width-image-group',
    CSS_FLOAT_MARKER: 'has-float-image',

    // CSS Classes - Transient (editor-only, never saved)
    CSS_DELETE_BTN: 'trip-image-delete-btn',
    CSS_DROP_ZONE_ACTIVE: 'drop-zone-active',
    CSS_DROP_ZONE_BETWEEN: 'drop-zone-between',
    CSS_DRAGGING: 'dragging',
    CSS_DRAG_OVER: 'drag-over',

    // Data Attributes
    ATTR_LAYOUT: 'data-layout',
    ATTR_UUID: 'data-uuid',

    // Layout Values
    LAYOUT_FLOAT_RIGHT: 'float-right',
    LAYOUT_FULL_WIDTH: 'full-width',

    // Commonly used selectors
    SEL_WRAPPER: '.trip-image-wrapper',
    SEL_IMAGE: 'img.trip-image',
    SEL_DELETE_BTN: '.trip-image-delete-btn',
    SEL_WRAPPER_FLOAT: '.trip-image-wrapper[data-layout="float-right"]',
    SEL_WRAPPER_FULL: '.trip-image-wrapper[data-layout="full-width"]',
  };

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
    this.$editor.find('.' + EDITOR_CONSTANTS.CSS_FULL_WIDTH_GROUP).each(function() {
      var $group = $(this);
      $group.children(EDITOR_CONSTANTS.SEL_WRAPPER_FULL).unwrap();
    });

    // Group consecutive full-width images
    var groups = [];
    var currentGroup = [];

    this.$editor.children().each(function() {
      var $child = $(this);
      if ($child.is(EDITOR_CONSTANTS.SEL_WRAPPER_FULL)) {
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
      $(group).wrapAll('<div class="' + EDITOR_CONSTANTS.CSS_FULL_WIDTH_GROUP + '"></div>');
    });
  };

  /**
   * Mark paragraphs that contain float-right images
   * This allows CSS to clear floats appropriately
   */
  EditorLayoutManager.prototype.markFloatParagraphs = function() {
    // Remove existing marks
    this.$editor.find('p').removeClass(EDITOR_CONSTANTS.CSS_FLOAT_MARKER);

    // Mark paragraphs with float-right images
    this.$editor.find('p').each(function() {
      var $p = $(this);
      if ($p.find(EDITOR_CONSTANTS.SEL_WRAPPER_FLOAT).length > 0) {
        $p.addClass(EDITOR_CONSTANTS.CSS_FLOAT_MARKER);
      }
    });
  };

  /**
   * Ensure all image wrappers have delete buttons
   * Called on page load to add buttons to wrappers from saved content
   */
  EditorLayoutManager.prototype.ensureDeleteButtons = function() {
    this.$editor.find(EDITOR_CONSTANTS.SEL_WRAPPER).each(function() {
      var $wrapper = $(this);

      // Check if delete button already exists
      if ($wrapper.find(EDITOR_CONSTANTS.SEL_DELETE_BTN).length === 0) {
        // Add delete button
        var $deleteBtn = $('<button>', {
          'class': EDITOR_CONSTANTS.CSS_DELETE_BTN,
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
              this.isSaving = false;
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
   * JournalEditor - Main editor class
   */
  function JournalEditor($editor) {
    this.$editor = $editor;
    this.$form = $editor.closest('.journal-entry-form');
    this.$titleInput = this.$form.find('#id_entry_title');
    this.$dateInput = this.$form.find('#id_entry_date');
    this.$timezoneInput = this.$form.find('#id_entry_timezone');
    this.$statusElement = this.$form.find('.journal-save-status');

    this.entryPk = $editor.data('entry-pk');
    this.currentVersion = $editor.data('current-version') || 1;
    this.tripId = this.getTripIdFromUrl();

    this.draggedElement = null;
    this.dragSource = null; // 'picker' or 'editor'
    this.dropZoneIndicator = null;

    // Initialize managers
    this.editorLayoutManager = new EditorLayoutManager(this.$editor);

    var autosaveUrl = '/journal/trip/' + this.tripId + '/entry/' + this.entryPk + '/save';
    var csrfToken = this.getCSRFToken();
    this.autoSaveManager = new AutoSaveManager(this, autosaveUrl, csrfToken);

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
    $clone.find(EDITOR_CONSTANTS.SEL_DELETE_BTN).remove();
    $clone.find('.' + EDITOR_CONSTANTS.CSS_DROP_ZONE_BETWEEN).remove();

    // Remove transient classes (editor-only states)
    $clone.find('.' + EDITOR_CONSTANTS.CSS_DROP_ZONE_ACTIVE)
          .removeClass(EDITOR_CONSTANTS.CSS_DROP_ZONE_ACTIVE);
    $clone.find('.' + EDITOR_CONSTANTS.CSS_DRAGGING)
          .removeClass(EDITOR_CONSTANTS.CSS_DRAGGING);
    $clone.removeClass(EDITOR_CONSTANTS.CSS_DRAG_OVER);

    // Remove selected state (editor UI only)
    $clone.find('.selected').removeClass('selected');

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
    $(document).on('dragstart', '.journal-image-card', function(e) {
      self.draggedElement = this;
      self.dragSource = 'picker';
      $(this).addClass(EDITOR_CONSTANTS.CSS_DRAGGING);

      // Set drag data
      e.originalEvent.dataTransfer.effectAllowed = 'copy';
      e.originalEvent.dataTransfer.setData('text/plain', ''); // Required for Firefox
    });

    // Handle dragend from picker
    $(document).on('dragend', '.journal-image-card', function(e) {
      $(this).removeClass(EDITOR_CONSTANTS.CSS_DRAGGING);
      self.clearDropZones();
      self.draggedElement = null;
      self.dragSource = null;
    });

    // Editor drag events
    this.$editor.on('dragover', function(e) {
      e.preventDefault();
      e.originalEvent.dataTransfer.dropEffect = 'copy';

      if (self.dragSource === 'picker') {
        self.showDropZones(e);
      }
    });

    this.$editor.on('dragenter', function(e) {
      if (self.dragSource === 'picker') {
        $(this).addClass(EDITOR_CONSTANTS.CSS_DRAG_OVER);
      }
    });

    this.$editor.on('dragleave', function(e) {
      // Only remove if we're leaving the editor completely
      if (!$(e.relatedTarget).closest('.journal-contenteditable').length) {
        $(this).removeClass(EDITOR_CONSTANTS.CSS_DRAG_OVER);
        self.clearDropZones();
      }
    });

    this.$editor.on('drop', function(e) {
      e.preventDefault();
      e.stopPropagation();

      $(this).removeClass(EDITOR_CONSTANTS.CSS_DRAG_OVER);

      if (self.dragSource === 'picker' && self.draggedElement) {
        self.handleImageDrop(e);
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
    var $imageWrapper = $target.closest(EDITOR_CONSTANTS.SEL_WRAPPER_FULL);

    // Clear existing indicators
    this.clearDropZones();

    if ($paragraph.length && $paragraph.parent().is(this.$editor)) {
      // Mouse is over a paragraph - show paragraph drop zone
      $paragraph.addClass(EDITOR_CONSTANTS.CSS_DROP_ZONE_ACTIVE);
    } else if ($imageWrapper.length && $imageWrapper.closest(this.$editor).length) {
      // Mouse is over a full-width image - highlight it to show insertion point
      // (wrapper may be inside .full-width-image-group, so check if it's within editor)
      $imageWrapper.addClass(EDITOR_CONSTANTS.CSS_DROP_ZONE_ACTIVE);
    } else {
      // Mouse is between paragraphs/images - show between indicator
      var mouseY = e.clientY;
      var $children = this.$editor.children('p, ' + EDITOR_CONSTANTS.SEL_WRAPPER_FULL + ', .' + EDITOR_CONSTANTS.CSS_FULL_WIDTH_GROUP);

      $children.each(function() {
        var rect = this.getBoundingClientRect();
        var betweenTop = rect.top - 20;
        var betweenBottom = rect.top + 20;

        if (mouseY >= betweenTop && mouseY <= betweenBottom) {
          var $indicator = $('<div class="' + EDITOR_CONSTANTS.CSS_DROP_ZONE_BETWEEN + '"></div>');
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
    this.$editor.find('p').removeClass(EDITOR_CONSTANTS.CSS_DROP_ZONE_ACTIVE);
    this.$editor.find(EDITOR_CONSTANTS.SEL_WRAPPER).removeClass(EDITOR_CONSTANTS.CSS_DROP_ZONE_ACTIVE);
    this.$editor.find('.' + EDITOR_CONSTANTS.CSS_DROP_ZONE_BETWEEN).remove();
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
    var $imageWrapper = $target.closest(EDITOR_CONSTANTS.SEL_WRAPPER_FULL);

    var layout = EDITOR_CONSTANTS.LAYOUT_FULL_WIDTH;
    var $insertTarget = null;

    if ($paragraph.length && $paragraph.parent().is(this.$editor)) {
      // Dropped into a paragraph - float-right layout
      layout = EDITOR_CONSTANTS.LAYOUT_FLOAT_RIGHT;
      $insertTarget = $paragraph;

      // Check and enforce 2-image limit per paragraph
      var existingWrappers = $paragraph.find(EDITOR_CONSTANTS.SEL_WRAPPER_FLOAT);
      if (existingWrappers.length >= 2) {
        // Remove the rightmost wrapper (with image inside)
        existingWrappers.last().remove();
      }
    } else if ($imageWrapper.length && $imageWrapper.closest(this.$editor).length) {
      // Dropped onto an existing full-width image - insert after it (into same group)
      layout = EDITOR_CONSTANTS.LAYOUT_FULL_WIDTH;
      $insertTarget = $imageWrapper;
    } else {
      // Dropped between paragraphs/images - full-width layout
      layout = EDITOR_CONSTANTS.LAYOUT_FULL_WIDTH;

      // Find the closest paragraph or full-width group to insert before/after
      var mouseY = e.clientY;
      var $children = this.$editor.children('p, ' + EDITOR_CONSTANTS.SEL_WRAPPER_FULL + ', .' + EDITOR_CONSTANTS.CSS_FULL_WIDTH_GROUP);
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
    if (layout === EDITOR_CONSTANTS.LAYOUT_FLOAT_RIGHT) {
      // Insert at beginning of paragraph for float-right
      $insertTarget.prepend($wrappedImage);
    } else if ($insertTarget.is(EDITOR_CONSTANTS.SEL_WRAPPER_FULL)) {
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
      'class': EDITOR_CONSTANTS.CSS_IMAGE,
    });
    $img.attr(EDITOR_CONSTANTS.ATTR_UUID, uuid);
    $img.attr('draggable', true);

    // Create wrapper with layout attribute
    var $wrapper = $('<span>', {
      'class': EDITOR_CONSTANTS.CSS_WRAPPER
    });
    $wrapper.attr(EDITOR_CONSTANTS.ATTR_LAYOUT, layout);

    // Create delete button
    var $deleteBtn = $('<button>', {
      'class': EDITOR_CONSTANTS.CSS_DELETE_BTN,
      'type': 'button',
      'title': 'Remove image',
      'text': '×'
    });

    // Assemble: wrapper contains image and delete button
    $wrapper.append($img, $deleteBtn);

    return $wrapper;
  };

  /**
   * Setup image click to inspect
   */
  JournalEditor.prototype.setupImageClickToInspect = function() {
    var self = this;

    // Use event delegation for dynamically added images
    this.$editor.on('click', 'img.trip-image', function(e) {
      e.preventDefault();
      e.stopPropagation();

      var $img = $(this);
      var uuid = $img.data('uuid');

      // Get inspect URL from the corresponding picker card
      var $pickerCard = $('.journal-image-card[data-image-uuid="' + uuid + '"]');
      var inspectUrl = $pickerCard.data('inspect-url');

      if (inspectUrl) {
        AN.get(inspectUrl);
      } else {
        console.warn('No inspect URL found for image:', uuid);
      }
    });

    // Prevent default drag on existing images (handled in setupImageReordering)
    this.$editor.on('dragstart', 'img.trip-image', function(e) {
      // This is handled in setupImageReordering
    });
  };

  /**
   * Setup image reordering within editor
   */
  JournalEditor.prototype.setupImageReordering = function() {
    var self = this;

    // Handle dragstart for images already in editor
    this.$editor.on('dragstart', EDITOR_CONSTANTS.SEL_IMAGE, function(e) {
      var $img = $(this);
      var $wrapper = $img.closest(EDITOR_CONSTANTS.SEL_WRAPPER);

      self.draggedElement = $wrapper[0]; // Store wrapper, not image
      self.dragSource = 'editor';
      $wrapper.addClass(EDITOR_CONSTANTS.CSS_DRAGGING);

      e.originalEvent.dataTransfer.effectAllowed = 'move';
      e.originalEvent.dataTransfer.setData('text/plain', '');
    });

    // Handle dragend for images in editor
    this.$editor.on('dragend', EDITOR_CONSTANTS.SEL_IMAGE, function(e) {
      var $img = $(this);
      var $wrapper = $img.closest(EDITOR_CONSTANTS.SEL_WRAPPER);

      $wrapper.removeClass(EDITOR_CONSTANTS.CSS_DRAGGING);
      self.clearDropZones();
      self.draggedElement = null;
      self.dragSource = null;
    });

    // Drop handling for reordering
    this.$editor.on('drop', function(e) {
      if (self.dragSource === 'editor' && self.draggedElement) {
        e.preventDefault();
        e.stopPropagation();

        $(this).removeClass(EDITOR_CONSTANTS.CSS_DRAG_OVER);
        self.handleImageReorder(e);
        self.clearDropZones();
      }
    });
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
    var newLayout = EDITOR_CONSTANTS.LAYOUT_FULL_WIDTH;

    if ($paragraph.length && $paragraph.parent().is(this.$editor)) {
      // Dropped into a paragraph
      newLayout = EDITOR_CONSTANTS.LAYOUT_FLOAT_RIGHT;

      // Remove from old location
      $wrapper.remove();

      // Check 2-image limit
      var existingWrappers = $paragraph.find(EDITOR_CONSTANTS.SEL_WRAPPER_FLOAT);
      if (existingWrappers.length >= 2) {
        existingWrappers.last().remove();
      }

      // Insert at beginning of paragraph
      $paragraph.prepend($wrapper);
    } else {
      // Dropped between paragraphs
      newLayout = EDITOR_CONSTANTS.LAYOUT_FULL_WIDTH;

      // Remove from old location
      $wrapper.remove();

      // Find closest paragraph or full-width wrapper
      var mouseY = e.clientY;
      var $paragraphs = this.$editor.children('p, ' + EDITOR_CONSTANTS.SEL_WRAPPER_FULL);
      var closestElement = null;
      var minDistance = Infinity;

      $paragraphs.each(function() {
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

    // Update layout attribute if changed
    if (newLayout !== oldLayout) {
      $wrapper.attr(EDITOR_CONSTANTS.ATTR_LAYOUT, newLayout);
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
    this.$editor.on('click', '.trip-image-delete-btn', function(e) {
      e.preventDefault();
      e.stopPropagation();

      var $wrapper = $(this).closest('.trip-image-wrapper');
      var $img = $wrapper.find('img.trip-image');

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
          if (node.nodeType === Node.ELEMENT_NODE && $(node).is('img.trip-image')) {
            $img = $(node);
          } else if (node.nodeType === Node.ELEMENT_NODE) {
            $img = $(node).find('img.trip-image').first();
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
    var $wrapper = $img.closest('.trip-image-wrapper');
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
        var $images = self.$editor.find('img.trip-image');

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
   * Utility: Get trip ID from URL
   */
  JournalEditor.prototype.getTripIdFromUrl = function() {
    var matches = window.location.pathname.match(/\/trip\/(\d+)\//);
    return matches ? matches[1] : null;
  };

  /**
   * Initialize editor on document ready
   */
  $(document).ready(function() {
    var $editor = $('#id_entry_text');

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
