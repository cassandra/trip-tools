/**
 * AutoSaveManager
 *
 * Manages automatic saving of journal content with debouncing and retry logic.
 *
 * Features:
 * - Change detection (content, title, date, timezone, reference image, publish flag)
 * - Debounced auto-save with configurable delay
 * - Maximum delay to force save during continuous typing
 * - Retry logic with exponential backoff for server errors
 * - Version tracking for conflict detection
 * - Status display updates
 *
 * Dependencies:
 * - jQuery ($.ajax)
 * - TtConst.CURRENT_VERSION_DATA_ATTR
 * - AN.displayModal (for refresh modal on date change)
 *
 * Usage:
 *   var autosave = new Tt.JournalEditor.AutoSaveManager(editor, autosaveUrl, csrfToken);
 *   autosave.initializeBaseline();
 *   autosave.scheduleSave(); // Call on content changes
 *   autosave.saveNow();      // Manual save button
 */

(function($) {
  'use strict';

  // =========================================================================
  // AutoSave Configuration
  // =========================================================================
  var AUTOSAVE_DEBOUNCE_MS = TtConst.EDITOR_AUTOSAVE_INTERVAL_SECS * 1000;   // Delay after typing stops before saving
  var AUTOSAVE_MAX_DELAY_MS = 30000; // Maximum time before forcing a save

  /**
   * STATUS VALUES
   * Status messages for the save status indicator.
   */
  var STATUS = {
    SAVED: 'saved',
    SAVING: 'saving',
    ERROR: 'error',
  };

  /**
   * AutoSaveManager
   *
   * Manages automatic saving of journal content with debouncing and retry logic.
   *
   * This manager handles:
   * - Change detection (content, title, date, timezone, reference image)
   * - Debounced auto-save (configurable via AUTOSAVE_DEBOUNCE_MS)
   * - Save execution with retry logic
   * - Status display updates
   *
   * @param {Object} editor - JournalEditor instance with required interface:
   *   - getCleanHTML() -> string
   *   - $titleInput, $dateInput, $timezoneInput, $includeInPublishInput (jQuery elements)
   *   - getReferenceImageUuid() -> string|null
   *   - updateStatus(status, message?)
   *   - runNormalizationAtIdle()
   *   - currentVersion (number)
   *   - $editor (jQuery element)
   *   - handleTitleUpdate(newTitle)
   *   - handleVersionConflict(data)
   * @param {string} autosaveUrl - URL endpoint for autosave POST
   * @param {string} csrfToken - CSRF token for POST requests
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
    this.lastSavedIncludeInPublish = true;
  }

  /**
   * Initialize with current content as "saved" baseline
   */
  AutoSaveManager.prototype.initializeBaseline = function() {
    this.lastSavedHTML = this.editor.getCleanHTML();
    this.lastSavedTitle = this.editor.$titleInput.val() || '';
    this.lastSavedDate = this.editor.$dateInput.val() || '';
    this.lastSavedTimezone = this.editor.$timezoneInput.val() || '';
    this.lastSavedReferenceImage = this.editor.getReferenceImageUuid();
    this.lastSavedIncludeInPublish = this.editor.$includeInPublishInput.is(':checked');
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
    var referenceImageChanged = this.editor.getReferenceImageUuid() !== this.lastSavedReferenceImage;
    var includeInPublishChanged = this.editor.$includeInPublishInput.is(':checked') !== this.lastSavedIncludeInPublish;

    return htmlChanged || titleChanged || dateChanged || timezoneChanged || referenceImageChanged || includeInPublishChanged;
  };

  /**
   * Schedule a save with debouncing.
   * Call this method whenever content changes.
   */
  AutoSaveManager.prototype.scheduleSave = function() {
    // Update change detection
    this.hasUnsavedChanges = this.detectChanges();

    if (this.hasUnsavedChanges) {
      this.editor.updateStatus('unsaved');
    } else {
      // Content reverted to saved state - update status and clear pending saves
      this.editor.updateStatus(STATUS.SAVED);
      if (this.saveTimeout) {
        clearTimeout(this.saveTimeout);
        this.saveTimeout = null;
      }
      if (this.maxTimeout) {
        clearTimeout(this.maxTimeout);
        this.maxTimeout = null;
      }
      return;  // No need to schedule save
    }

    // Clear existing timeout
    if (this.saveTimeout) {
      clearTimeout(this.saveTimeout);
    }

    // Set maximum timeout on first change to ensure saves during continuous typing
    if (!this.maxTimeout) {
      this.maxTimeout = setTimeout(function() {
        this.executeSave();
        this.maxTimeout = null;
      }.bind(this), AUTOSAVE_MAX_DELAY_MS);
    }

    // Set debounce timeout - saves after user stops typing
    this.saveTimeout = setTimeout(function() {
      this.executeSave();
      // Clear max timeout since we saved via regular timeout
      if (this.maxTimeout) {
        clearTimeout(this.maxTimeout);
        this.maxTimeout = null;
      }
    }.bind(this), AUTOSAVE_DEBOUNCE_MS);
  };

  /**
   * Save immediately without debouncing
   * Called when user clicks manual "Save" button
   * Clears any pending timeouts and executes save right away
   */
  AutoSaveManager.prototype.saveNow = function() {
    // Clear any pending save timers
    if (this.saveTimeout) {
      clearTimeout(this.saveTimeout);
      this.saveTimeout = null;
    }
    if (this.maxTimeout) {
      clearTimeout(this.maxTimeout);
      this.maxTimeout = null;
    }

    // Execute save immediately
    // executeSave() has guards to prevent duplicate saves
    this.executeSave();
  };

  /**
   * Execute save to server
   */
  AutoSaveManager.prototype.executeSave = function() {
    if (this.isSaving || !this.hasUnsavedChanges) {
      return;
    }

    // Run normalization on live editor before save (so user sees normalized result)
    this.editor.runNormalizationAtIdle();

    this.isSaving = true;
    this.editor.updateStatus('saving');

    // Capture snapshot of what we're saving (prevents race conditions)
    var snapshot = {
      html: this.editor.getCleanHTML(),
      title: this.editor.$titleInput.val() || '',
      date: this.editor.$dateInput.val() || '',
      timezone: this.editor.$timezoneInput.val() || '',
      referenceImageUuid: this.editor.getReferenceImageUuid(),
      includeInPublish: this.editor.$includeInPublishInput.is(':checked')
    };

    var data = {
      text: snapshot.html,
      version: this.editor.currentVersion,
      new_title: snapshot.title,
      new_date: snapshot.date,
      new_timezone: snapshot.timezone,
      reference_image_uuid: snapshot.referenceImageUuid || '',
      include_in_publish: snapshot.includeInPublish
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
          this.lastSavedReferenceImage = snapshot.referenceImageUuid;
          this.lastSavedIncludeInPublish = snapshot.includeInPublish;

          // Recheck if changes occurred during save
          this.hasUnsavedChanges = this.detectChanges();

          this.editor.currentVersion = response.version;
          this.editor.$editor.data(TtConst.CURRENT_VERSION_DATA_ATTR, response.version);
          this.retryCount = 0;

          if (this.maxTimeout) {
            clearTimeout(this.maxTimeout);
            this.maxTimeout = null;
          }

          // Handle title update notification if backend regenerated the title
          if (response.title_updated) {
            this.editor.handleTitleUpdate(snapshot.title);
          }

          // Handle date change - show refresh modal if provided by backend
          if (response.modal) {
            AN.displayModal(response.modal);
          }

          if (this.hasUnsavedChanges) {
            this.editor.updateStatus('unsaved');
          } else {
            this.editor.updateStatus(STATUS.SAVED, response.modified_datetime);
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

  // =========================================================================
  // Export to Tt.JournalEditor namespace
  // =========================================================================
  window.Tt = window.Tt || {};
  window.Tt.JournalEditor = window.Tt.JournalEditor || {};
  window.Tt.JournalEditor.AutoSaveManager = AutoSaveManager;

  // Export constants for testing
  window.Tt.JournalEditor.AUTOSAVE_DEBOUNCE_MS = AUTOSAVE_DEBOUNCE_MS;
  window.Tt.JournalEditor.AUTOSAVE_MAX_DELAY_MS = AUTOSAVE_MAX_DELAY_MS;
  window.Tt.JournalEditor.STATUS = STATUS;

})(jQuery);
