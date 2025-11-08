/**
 * Journal Entry Editor - ContentEditable with Image Management
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
 */

(function($) {
  'use strict';

  // Module state
  let editorInstance = null;

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
    this.autosaveUrl = '/journal/trip/' + this.tripId + '/entry/' + this.entryPk + '/save';
    this.csrfToken = this.getCSRFToken();

    this.saveTimeout = null;
    this.maxTimeout = null;
    this.isSaving = false;
    this.retryCount = 0;
    this.hasUnsavedChanges = false;
    this.lastSavedHTML = '';

    this.draggedElement = null;
    this.dragSource = null; // 'picker' or 'editor'
    this.dropZoneIndicator = null;

    this.init();
  }

  /**
   * Initialize the editor
   */
  JournalEditor.prototype.init = function() {
    if (!this.$editor.length) {
      return;
    }

    // Store initial content and metadata
    this.lastSavedHTML = this.getCleanHTML();
    this.lastSavedTitle = this.$titleInput.val() || '';
    this.lastSavedDate = this.$dateInput.val() || '';
    this.lastSavedTimezone = this.$timezoneInput.val() || '';
    this.lastSavedReferenceImage = this.getReferenceImageId();
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

    // Ensure all image wrappers have delete buttons (needed on page load)
    this.ensureDeleteButtons();

    // Wrap consecutive full-width images in groups (for CSS float clearing)
    this.wrapFullWidthImageGroups();

    // Mark paragraphs that contain float-right images for CSS float clearing
    this.markFloatParagraphs();

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
    // Wrap consecutive full-width images in groups (for CSS float clearing)
    this.wrapFullWidthImageGroups();

    // Mark paragraphs with float images (for CSS float clearing)
    this.markFloatParagraphs();

    // Check if any field has changed (use clean HTML to ignore UI wrappers)
    var htmlChanged = (this.getCleanHTML() !== this.lastSavedHTML);
    var titleChanged = (this.$titleInput.val() || '') !== this.lastSavedTitle;
    var dateChanged = (this.$dateInput.val() || '') !== this.lastSavedDate;
    var timezoneChanged = (this.$timezoneInput.val() || '') !== this.lastSavedTimezone;
    var referenceImageChanged = this.getReferenceImageId() !== this.lastSavedReferenceImage;

    this.hasUnsavedChanges = htmlChanged || titleChanged || dateChanged || timezoneChanged || referenceImageChanged;

    if (this.hasUnsavedChanges) {
      this.updateStatus('unsaved');
    }

    // Clear existing timeout
    if (this.saveTimeout) {
      clearTimeout(this.saveTimeout);
    }

    // Set maximum timeout on first change (30 seconds)
    if (!this.maxTimeout) {
      this.maxTimeout = setTimeout(function() {
        this.autoSave();
        this.maxTimeout = null;
      }.bind(this), 30000);
    }

    // Set new timeout (2 seconds)
    this.saveTimeout = setTimeout(function() {
      this.autoSave();
      // Clear max timeout since we saved via regular timeout
      if (this.maxTimeout) {
        clearTimeout(this.maxTimeout);
        this.maxTimeout = null;
      }
    }.bind(this), 2000);
  };

  /**
   * Auto-save content to server
   */
  JournalEditor.prototype.autoSave = function() {
    if (this.isSaving || !this.hasUnsavedChanges) {
      return;
    }

    this.isSaving = true;
    this.updateStatus('saving');

    // Capture snapshot of what we're saving (prevents race conditions)
    var snapshot = {
      html: this.getCleanHTML(),
      title: this.$titleInput.val() || '',
      date: this.$dateInput.val() || '',
      timezone: this.$timezoneInput.val() || '',
      referenceImage: this.getReferenceImageId()
    };

    var data = {
      text: snapshot.html,
      version: this.currentVersion,
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

          // Recheck if changes occurred during save (use clean HTML to ignore UI wrappers)
          var htmlChanged = (this.getCleanHTML() !== this.lastSavedHTML);
          var titleChanged = (this.$titleInput.val() || '') !== this.lastSavedTitle;
          var dateChanged = (this.$dateInput.val() || '') !== this.lastSavedDate;
          var timezoneChanged = (this.$timezoneInput.val() || '') !== this.lastSavedTimezone;
          var referenceImageChanged = this.getReferenceImageId() !== this.lastSavedReferenceImage;

          this.hasUnsavedChanges = htmlChanged || titleChanged || dateChanged || timezoneChanged || referenceImageChanged;

          this.currentVersion = response.version;
          this.$editor.data('current-version', response.version);
          this.retryCount = 0;

          if (this.maxTimeout) {
            clearTimeout(this.maxTimeout);
            this.maxTimeout = null;
          }

          if (this.hasUnsavedChanges) {
            this.updateStatus('unsaved');
          } else {
            this.updateStatus('saved', response.modified_datetime);
          }
        } else {
          this.updateStatus('error', response.message);
        }
      }.bind(this),
      error: function(xhr, status, error) {
        if (xhr.status === 409) {
          this.handleVersionConflict(xhr.responseJSON);
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
            this.updateStatus('error', 'Save failed - retrying (' + this.retryCount + '/3)...');

            setTimeout(function() {
              this.isSaving = false;
              this.autoSave();
            }.bind(this), delay);
          } else {
            this.updateStatus('error', errorMessage);
          }
        }
      }.bind(this),
      complete: function() {
        this.isSaving = false;
      }.bind(this)
    });
  };

  /**
   * Get clean HTML for saving (removes UI-only delete buttons, keeps wrappers)
   */
  JournalEditor.prototype.getCleanHTML = function() {
    // Clone the editor content to avoid modifying the displayed version
    var $clone = this.$editor.clone();

    // Remove delete buttons (but keep wrappers)
    $clone.find('.trip-image-delete-btn').remove();

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
      $(this).addClass('dragging');

      // Set drag data
      e.originalEvent.dataTransfer.effectAllowed = 'copy';
      e.originalEvent.dataTransfer.setData('text/plain', ''); // Required for Firefox
    });

    // Handle dragend from picker
    $(document).on('dragend', '.journal-image-card', function(e) {
      $(this).removeClass('dragging');
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
        $(this).addClass('drag-over');
      }
    });

    this.$editor.on('dragleave', function(e) {
      // Only remove if we're leaving the editor completely
      if (!$(e.relatedTarget).closest('.journal-contenteditable').length) {
        $(this).removeClass('drag-over');
        self.clearDropZones();
      }
    });

    this.$editor.on('drop', function(e) {
      e.preventDefault();
      e.stopPropagation();

      $(this).removeClass('drag-over');

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
    var $imageWrapper = $target.closest('.trip-image-wrapper[data-layout="full-width"]');

    // Clear existing indicators
    this.clearDropZones();

    if ($paragraph.length && $paragraph.parent().is(this.$editor)) {
      // Mouse is over a paragraph - show paragraph drop zone
      $paragraph.addClass('drop-zone-active');
    } else if ($imageWrapper.length && $imageWrapper.closest(this.$editor).length) {
      // Mouse is over a full-width image - highlight it to show insertion point
      // (wrapper may be inside .full-width-image-group, so check if it's within editor)
      $imageWrapper.addClass('drop-zone-active');
    } else {
      // Mouse is between paragraphs/images - show between indicator
      var mouseY = e.clientY;
      var $children = this.$editor.children('p, .trip-image-wrapper[data-layout="full-width"], .full-width-image-group');

      $children.each(function() {
        var rect = this.getBoundingClientRect();
        var betweenTop = rect.top - 20;
        var betweenBottom = rect.top + 20;

        if (mouseY >= betweenTop && mouseY <= betweenBottom) {
          var $indicator = $('<div class="drop-zone-between"></div>');
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
    this.$editor.find('p').removeClass('drop-zone-active');
    this.$editor.find('.trip-image-wrapper').removeClass('drop-zone-active');
    this.$editor.find('.drop-zone-between').remove();
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
    var $imageWrapper = $target.closest('.trip-image-wrapper[data-layout="full-width"]');

    var layout = 'full-width';
    var $insertTarget = null;

    if ($paragraph.length && $paragraph.parent().is(this.$editor)) {
      // Dropped into a paragraph - float-right layout
      layout = 'float-right';
      $insertTarget = $paragraph;

      // Check and enforce 2-image limit per paragraph
      var existingWrappers = $paragraph.find('.trip-image-wrapper[data-layout="float-right"]');
      if (existingWrappers.length >= 2) {
        // Remove the rightmost wrapper (with image inside)
        existingWrappers.last().remove();
      }
    } else if ($imageWrapper.length && $imageWrapper.closest(this.$editor).length) {
      // Dropped onto an existing full-width image - insert after it (into same group)
      layout = 'full-width';
      $insertTarget = $imageWrapper;
    } else {
      // Dropped between paragraphs/images - full-width layout
      layout = 'full-width';

      // Find the closest paragraph or full-width group to insert before/after
      var mouseY = e.clientY;
      var $children = this.$editor.children('p, .trip-image-wrapper[data-layout="full-width"], .full-width-image-group');
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
    if (layout === 'float-right') {
      // Insert at beginning of paragraph for float-right
      $insertTarget.prepend($wrappedImage);
    } else if ($insertTarget.is('.trip-image-wrapper[data-layout="full-width"]')) {
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
   * Ensure all image wrappers have delete buttons
   * Called on page load to add buttons to wrappers from saved content
   */
  JournalEditor.prototype.ensureDeleteButtons = function() {
    this.$editor.find('.trip-image-wrapper').each(function() {
      var $wrapper = $(this);

      // Check if delete button already exists
      if ($wrapper.find('.trip-image-delete-btn').length === 0) {
        // Add delete button
        var $deleteBtn = $('<button>', {
          'class': 'trip-image-delete-btn',
          'type': 'button',
          'title': 'Remove image',
          'text': '×'
        });
        $wrapper.append($deleteBtn);
      }
    });
  };

  /**
   * Mark paragraphs that contain float-right images
   * This allows CSS to clear floats appropriately
   */
  JournalEditor.prototype.markFloatParagraphs = function() {
    // Remove existing marks
    this.$editor.find('p').removeClass('has-float-image');

    // Mark paragraphs with float-right images
    this.$editor.find('p').each(function() {
      var $p = $(this);
      if ($p.find('.trip-image-wrapper[data-layout="float-right"]').length > 0) {
        $p.addClass('has-float-image');
      }
    });
  };

  /**
   * Wrap consecutive full-width images in container divs
   * This allows them to clear floats properly
   */
  JournalEditor.prototype.wrapFullWidthImageGroups = function() {
    var self = this;

    // Remove existing wrappers first
    this.$editor.find('.full-width-image-group').each(function() {
      var $group = $(this);
      $group.children('.trip-image-wrapper[data-layout="full-width"]').unwrap();
    });

    // Group consecutive full-width images
    var groups = [];
    var currentGroup = [];

    this.$editor.children().each(function() {
      var $child = $(this);
      if ($child.is('.trip-image-wrapper[data-layout="full-width"]')) {
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
      $(group).wrapAll('<div class="full-width-image-group"></div>');
    });
  };

  /**
   * Create image element with proper attributes
   */
  JournalEditor.prototype.createImageElement = function(uuid, url, caption, layout) {
    // Create the image element
    var $img = $('<img>', {
      'src': url,
      'alt': caption,
      'class': 'trip-image',
      'data-uuid': uuid,
      'draggable': true
    });

    // Create wrapper with layout attribute
    var $wrapper = $('<span>', {
      'class': 'trip-image-wrapper',
      'data-layout': layout
    });

    // Create delete button
    var $deleteBtn = $('<button>', {
      'class': 'trip-image-delete-btn',
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
    this.$editor.on('dragstart', 'img.trip-image', function(e) {
      var $img = $(this);
      var $wrapper = $img.closest('.trip-image-wrapper');

      self.draggedElement = $wrapper[0]; // Store wrapper, not image
      self.dragSource = 'editor';
      $wrapper.addClass('dragging');

      e.originalEvent.dataTransfer.effectAllowed = 'move';
      e.originalEvent.dataTransfer.setData('text/plain', '');
    });

    // Handle dragend for images in editor
    this.$editor.on('dragend', 'img.trip-image', function(e) {
      var $img = $(this);
      var $wrapper = $img.closest('.trip-image-wrapper');

      $wrapper.removeClass('dragging');
      self.clearDropZones();
      self.draggedElement = null;
      self.dragSource = null;
    });

    // Drop handling for reordering
    this.$editor.on('drop', function(e) {
      if (self.dragSource === 'editor' && self.draggedElement) {
        e.preventDefault();
        e.stopPropagation();

        $(this).removeClass('drag-over');
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
    var newLayout = 'full-width';

    if ($paragraph.length && $paragraph.parent().is(this.$editor)) {
      // Dropped into a paragraph
      newLayout = 'float-right';

      // Remove from old location
      $wrapper.remove();

      // Check 2-image limit
      var existingWrappers = $paragraph.find('.trip-image-wrapper[data-layout="float-right"]');
      if (existingWrappers.length >= 2) {
        existingWrappers.last().remove();
      }

      // Insert at beginning of paragraph
      $paragraph.prepend($wrapper);
    } else {
      // Dropped between paragraphs
      newLayout = 'full-width';

      // Remove from old location
      $wrapper.remove();

      // Find closest paragraph or full-width wrapper
      var mouseY = e.clientY;
      var $paragraphs = this.$editor.children('p, .trip-image-wrapper[data-layout="full-width"]');
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
      $wrapper.attr('data-layout', newLayout);
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
