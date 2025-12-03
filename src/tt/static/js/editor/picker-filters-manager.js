/**
 * Picker Filters Manager for Journal Editor
 *
 * Manages date/recent filter buttons for the image picker panel.
 * Handles the interaction between Recent button, Date input, and Last Used Date button.
 *
 * Extracted from journal-editor.js as part of modular refactoring (Phase 3).
 *
 * Dependencies:
 * - jQuery ($)
 * - TtConst (server-injected constants)
 * - AN (antinode async content loader)
 *
 * @namespace Tt.JournalEditor
 */

(function($) {
  'use strict';

  // Ensure namespace exists
  window.Tt = window.Tt || {};
  window.Tt.JournalEditor = window.Tt.JournalEditor || {};

  /**
   * Update URL with picker state (without page reload)
   * Preserves picker state across page refreshes triggered by modals.
   *
   * @param {Object} params - State parameters
   * @param {string} [params.date] - Date in YYYY-MM-DD format (for "Last Used Date" button)
   * @param {boolean} [params.recent] - True if in recent mode
   * @param {string} [params.scope] - Scope filter (unused, used, all)
   */
  function updatePickerUrlState(params) {
    var url = new URL(window.location.href);

    // Clear existing picker params
    url.searchParams.delete(TtConst.PICKER_DATE_PARAM);
    url.searchParams.delete(TtConst.PICKER_RECENT_PARAM);
    url.searchParams.delete(TtConst.PICKER_SCOPE_PARAM);

    // Always include date if available (for "Last Used Date" button, even in recent mode)
    if (params.date) {
      url.searchParams.set(TtConst.PICKER_DATE_PARAM, params.date);
    }

    // Set recent mode flag
    if (params.recent) {
      url.searchParams.set(TtConst.PICKER_RECENT_PARAM, '1');
    }

    // Only add scope to URL if not default (unused)
    if (params.scope && params.scope !== TtConst.IMAGE_PICKER_SCOPE_UNUSED) {
      url.searchParams.set(TtConst.PICKER_SCOPE_PARAM, params.scope);
    }

    // Update URL without reload
    window.history.replaceState({}, '', url.toString());
  }

  /**
   * Initialize image picker filters
   *
   * Handles Recent button and date picker interaction for the image picker panel.
   * Must be called after DOM is ready and after JournalEditor is instantiated.
   *
   * @param {JournalEditor} editorInstance - The JournalEditor instance (optional, for filter updates)
   */
  function initImagePickerFilters(editorInstance) {
    var $form = $('#' + TtConst.JOURNAL_EDITOR_MULTI_IMAGE_FILTER_FORM_ID);
    var $dateInput = $('#' + TtConst.JOURNAL_EDITOR_MULTI_IMAGE_DATE_INPUT_ID);
    var $recentBtn = $('#' + TtConst.JOURNAL_EDITOR_MULTI_IMAGE_RECENT_BTN_ID);
    var $gallery = $('#' + TtConst.JOURNAL_EDITOR_MULTI_IMAGE_GALLERY_ID);

    if ($form.length === 0 || $dateInput.length === 0 || $recentBtn.length === 0) {
      return; // Not on a page with image picker
    }

    // Track current mode (recent or date)
    // Detect initial mode from DOM: empty date input means recent mode
    var currentMode = $dateInput.val() ? 'date' : 'recent';

    /**
     * Get current scope from image picker (if available)
     */
    function getCurrentScope() {
      if (editorInstance && editorInstance.imagePicker) {
        return editorInstance.imagePicker.filterScope || TtConst.IMAGE_PICKER_SCOPE_UNUSED;
      }
      return TtConst.IMAGE_PICKER_SCOPE_UNUSED;
    }

    /**
     * Update visual state of Recent button
     * @param {boolean} isActive - Whether Recent mode is active
     */
    function updateRecentButtonState(isActive) {
      if (isActive) {
        $recentBtn.removeClass('btn-outline-primary').addClass('btn-primary');
      } else {
        $recentBtn.removeClass('btn-primary').addClass('btn-outline-primary');
      }
    }

    /**
     * Last Used Date button and tracking
     */
    var $lastUsedDateBtn = $('#' + TtConst.JOURNAL_EDITOR_MULTI_IMAGE_ENTRY_DATE_BTN_ID);
    // Initialize from button's data attribute (set by server's filter_date)
    var lastUsedDate = $lastUsedDateBtn.data(TtConst.LAST_USED_DATE_ATTR) || null;

    /**
     * Update visual state of Last Used Date button
     * @param {boolean} isActive - Whether date mode is active
     */
    function updateLastUsedDateButtonState(isActive) {
      if ($lastUsedDateBtn.length === 0) {
        return;
      }
      // Remove disabled styling class (for Prologue/Epilogue initial state)
      $lastUsedDateBtn.removeClass('btn-outline-secondary');

      if (isActive) {
        $lastUsedDateBtn.removeClass('btn-outline-primary').addClass('btn-primary');
      } else {
        $lastUsedDateBtn.removeClass('btn-primary').addClass('btn-outline-primary');
      }
    }

    /**
     * Update the Last Used Date button's label and data attribute
     * @param {string} dateValue - Date in YYYY-MM-DD format
     */
    function updateLastUsedDateButton(dateValue) {
      if ($lastUsedDateBtn.length === 0) return;

      // Enable the button (may have been disabled on initial load for Prologue/Epilogue)
      $lastUsedDateBtn.prop('disabled', false);

      // Update the data attribute (use .attr() to actually update DOM, not just jQuery cache)
      $lastUsedDateBtn.attr('data-' + TtConst.LAST_USED_DATE_ATTR, dateValue);

      // Update the button label (format: "M j" e.g., "Sep 29")
      var date = new Date(dateValue + 'T00:00:00');
      var formatted = date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
      $lastUsedDateBtn.text(formatted);

      // Update the title tooltip
      var fullFormatted = date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
      $lastUsedDateBtn.attr('title', 'Show images from ' + fullFormatted);
    }

    /**
     * Load gallery with recent images
     */
    function loadRecentImages() {
      var baseUrl = $form.attr('action');
      var url = baseUrl + '?recent=true';

      AN.loadAsyncContent({
        url: url,
        target: $gallery,
        mode: 'insert',
        success: function() {
          currentMode = 'recent';
          updateRecentButtonState(true);
          updateLastUsedDateButtonState(false);
          $dateInput.val(''); // Clear date input to show we're in Recent mode
          // Re-apply scope filter to newly loaded images
          if (editorInstance && editorInstance.imagePicker) {
            editorInstance.imagePicker.applyFilter(editorInstance.imagePicker.filterScope);
          }
          // Update URL to preserve state across page refreshes (keep lastUsedDate for convenience button)
          updatePickerUrlState({ date: lastUsedDate, recent: true, scope: getCurrentScope() });
        },
        error: function() {
          console.error('Failed to load recent images');
        }
      });
    }

    /**
     * Load gallery with date-filtered images
     * @param {string} dateValue - Date in YYYY-MM-DD format
     */
    function loadDateFilteredImages(dateValue) {
      var baseUrl = $form.attr('action');
      var url = baseUrl + '?date=' + encodeURIComponent(dateValue);

      AN.loadAsyncContent({
        url: url,
        target: $gallery,
        mode: 'insert',
        success: function() {
          currentMode = 'date';
          updateRecentButtonState(false);
          // Track and update the last used date
          lastUsedDate = dateValue;
          updateLastUsedDateButton(dateValue);
          updateLastUsedDateButtonState(true);
          // Re-apply scope filter to newly loaded images
          if (editorInstance && editorInstance.imagePicker) {
            editorInstance.imagePicker.applyFilter(editorInstance.imagePicker.filterScope);
          }
          // Update URL to preserve state across page refreshes
          updatePickerUrlState({ date: dateValue, scope: getCurrentScope() });
        },
        error: function() {
          console.error('Failed to load date-filtered images');
        }
      });
    }

    /**
     * Handle Recent button click
     */
    $recentBtn.on('click', function(e) {
      e.preventDefault();
      e.stopPropagation();

      if (currentMode !== 'recent') {
        loadRecentImages();
      }
    });

    /**
     * Handle Last Used Date button click
     * Returns to the previously used date when in Recent mode
     */
    if ($lastUsedDateBtn.length > 0) {
      $lastUsedDateBtn.on('click', function(e) {
        e.preventDefault();
        e.stopPropagation();

        // Only load if we have a date and it's different from what's currently shown
        if (lastUsedDate && $dateInput.val() !== lastUsedDate) {
          $dateInput.val(lastUsedDate);
          loadDateFilteredImages(lastUsedDate);
        }
      });
    }

    /**
     * Handle date input change
     * Load images for the selected date
     */
    $dateInput.on('change', function() {
      var dateValue = $(this).val();

      if (dateValue) {
        // Load images for the selected date
        // This updates mode tracking, button states, lastUsedDate, and applies filter
        loadDateFilteredImages(dateValue);
      }
    });

    // Initialize button state based on initial mode
    updateRecentButtonState(currentMode === 'recent');
  }

  /**
   * Refresh image picker gallery with recent images
   * Called after upload completion to show newly uploaded images
   */
  function refreshImagePickerWithRecent() {
    var $gallery = $('#' + TtConst.JOURNAL_EDITOR_MULTI_IMAGE_GALLERY_ID);
    var $form = $('#' + TtConst.JOURNAL_EDITOR_MULTI_IMAGE_FILTER_FORM_ID);
    var $dateInput = $('#' + TtConst.JOURNAL_EDITOR_MULTI_IMAGE_DATE_INPUT_ID);
    var $recentBtn = $('#' + TtConst.JOURNAL_EDITOR_MULTI_IMAGE_RECENT_BTN_ID);
    var $lastUsedDateBtn = $('#' + TtConst.JOURNAL_EDITOR_MULTI_IMAGE_ENTRY_DATE_BTN_ID);

    if ($form.length > 0 && $gallery.length > 0) {
      var baseUrl = $form.attr('action');
      var url = baseUrl + '?recent=true';

      AN.loadAsyncContent({
        url: url,
        target: $gallery,
        mode: 'insert',
        success: function() {
          // Update UI to show Recent mode is active
          if ($dateInput.length > 0) {
            $dateInput.val('');
          }
          if ($recentBtn.length > 0) {
            $recentBtn.removeClass('btn-outline-primary').addClass('btn-primary');
          }
          // Show Last Used Date button as inactive (user can click to return to that date)
          if ($lastUsedDateBtn.length > 0) {
            $lastUsedDateBtn.removeClass('btn-primary').addClass('btn-outline-primary');
          }
          // Update URL to reflect recent mode (preserve current scope and last used date)
          var currentScope = $form.find('input[name="scope"]:checked').val() || TtConst.IMAGE_PICKER_SCOPE_UNUSED;
          var lastUsedDate = $lastUsedDateBtn.length > 0 ? $lastUsedDateBtn.data(TtConst.LAST_USED_DATE_ATTR) : null;
          updatePickerUrlState({ date: lastUsedDate, recent: true, scope: currentScope });
        },
        error: function() {
          console.error('Failed to load recent images after upload');
          location.reload();
        }
      });
    } else {
      location.reload();
    }
  }

  /**
   * Refresh image picker only if images were actually uploaded
   * Called when closing the upload modal - skips refresh if no uploads occurred
   */
  function refreshImagePickerIfUploaded() {
    // Check the uploaded count in the modal
    var $uploadedCount = $('.uploaded-count');
    var uploadedCount = parseInt($uploadedCount.text(), 10) || 0;

    if (uploadedCount > 0) {
      refreshImagePickerWithRecent();
    }
    // If no uploads, do nothing - image picker stays as it was
  }

  // ============================================================
  // EXPORTS TO Tt.JournalEditor NAMESPACE
  // ============================================================

  Tt.JournalEditor.initImagePickerFilters = initImagePickerFilters;
  Tt.JournalEditor.refreshImagePickerWithRecent = refreshImagePickerWithRecent;
  Tt.JournalEditor.refreshImagePickerIfUploaded = refreshImagePickerIfUploaded;
  Tt.JournalEditor.updatePickerUrlState = updatePickerUrlState;

  // Expose functions globally for use in templates
  window.JournalEditor = window.JournalEditor || {};
  window.JournalEditor.refreshImagePickerWithRecent = refreshImagePickerWithRecent;
  window.JournalEditor.refreshImagePickerIfUploaded = refreshImagePickerIfUploaded;

})(jQuery);
