(function($) {
  'use strict';

  // Constructor for individual notebook editor instances
  function NotebookEditor($container) {
    this.$container = $container;
    this.$form = $container.find('.notebook-form');
    this.$textarea = $container.find('.notebook-textarea');
    this.$dateInput = $container.find('.notebook-date');
    this.$statusElement = $container.find('.notebook-status');
    this.$dayOfWeek = $container.find('.notebook-day-of-week');

    this.saveTimeout = null;
    this.maxTimeout = null;
    this.isSaving = false;
    this.retryCount = 0;
    this.hasUnsavedChanges = false;
    this.lastSavedText = '';
    this.lastSavedDate = '';
    this.autosaveUrl = $container.data('autosave-url');
    this.csrfToken = $container.data('csrf-token');
    this.currentVersion = $container.data('current-version') || 1;

    this.init();
  }

  NotebookEditor.prototype.init = function() {
    if (!this.$textarea.length || !this.$statusElement.length || !this.$dateInput.length) {
      return;
    }

    // Initialize autosize
    if (typeof autosize !== 'undefined') {
      autosize(this.$textarea[0]);
    }

    // Store initial values
    this.lastSavedText = this.$textarea.val();
    this.lastSavedDate = this.$dateInput.val();
    this.updateStatus('saved');

    // Setup auto-save using event delegation on container
    this.$container.on('input', '.notebook-textarea', this.handleInput.bind(this));
    this.$container.on('input', '.notebook-date', this.handleInput.bind(this));

    // Setup day of week update on date change
    this.$container.on('change', '.notebook-date', this.updateDayOfWeek.bind(this));
  };

  NotebookEditor.prototype.handleInput = function() {
    this.hasUnsavedChanges = (
      this.$textarea.val() !== this.lastSavedText ||
      this.$dateInput.val() !== this.lastSavedDate
    );

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

  NotebookEditor.prototype.autoSave = function() {
    if (this.isSaving || !this.hasUnsavedChanges) return;

    this.isSaving = true;
    this.updateStatus('saving');

    var data = {
      date: this.$dateInput.val(),
      text: this.$textarea.val(),
      version: this.currentVersion
    };

    $.ajax({
      url: this.autosaveUrl,
      type: 'POST',
      contentType: 'application/json',
      data: JSON.stringify(data),
      headers: {
        'X-CSRFToken': this.csrfToken
      },
      success: function(data) {
        if (data.status === 'success') {
          this.lastSavedText = this.$textarea.val();
          this.lastSavedDate = this.$dateInput.val();
          this.hasUnsavedChanges = false;
          this.currentVersion = data.version;
          this.$container.data('current-version', data.version);
          this.retryCount = 0;
          // Clear max timeout since we saved successfully
          if (this.maxTimeout) {
            clearTimeout(this.maxTimeout);
            this.maxTimeout = null;
          }
          this.updateStatus('saved', data.modified_datetime);
        } else {
          this.updateStatus('error', data.message);
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
          } else if (xhr.responseText) {
            try {
              var response = JSON.parse(xhr.responseText);
              if (response.message) {
                errorMessage = response.message;
              }
            } catch (e) {
              // Keep default 'Network error' message
            }
          }

          // Retry logic for server errors (5xx) and network errors (status 0)
          var shouldRetry = (xhr.status >= 500 || xhr.status === 0) && this.retryCount < 3;

          if (shouldRetry) {
            this.retryCount++;
            var delay = Math.pow(2, this.retryCount) * 1000; // 2s, 4s, 8s
            this.updateStatus('error', 'Save failed - retrying (' + this.retryCount + '/3)...');

            setTimeout(function() {
              this.isSaving = false; // Reset flag before retry
              this.autoSave();
            }.bind(this), delay);
          } else {
            // Final failure - reset retry count and show error
            this.retryCount = 0;
            this.updateStatus('error', errorMessage);
          }
        }
      }.bind(this),
      complete: function() {
        this.isSaving = false;
      }.bind(this)
    });
  };

  NotebookEditor.prototype.handleVersionConflict = function(responseData) {
    this.updateStatus('conflict', 'Version conflict detected');

    // The response contains a 'modal' key with backend-rendered HTML
    if (responseData && responseData.modal) {
      // Generate unique modal ID
      var modalId = 'notebook-conflict-modal-' + Date.now();
      var $modal = $('<div id="' + modalId + '" class="modal fade" tabindex="-1" role="dialog"></div>');

      // Insert modal content from backend
      $modal.html(responseData.modal);

      // Append to body and show
      $('body').append($modal);
      $modal.modal('show');

      // Remove modal from DOM after it's hidden
      $modal.on('hidden.bs.modal', function() {
        $modal.remove();
      });
    }
  };

  NotebookEditor.prototype.updateStatus = function(status, message) {
    var statusText = '';
    var statusClass = 'badge badge-secondary';

    // Hide error alert for non-error statuses (conflicts now use modal only)
    if (status !== 'error') {
      var $errorAlert = this.$container.find('.notebook-error-alert');
      if ($errorAlert.is(':visible')) {
        $errorAlert.slideUp();
      }
    }

    switch(status) {
      case 'unsaved':
        statusText = 'Unsaved changes';
        statusClass = 'badge badge-warning';
        break;
      case 'saving':
        statusText = 'Saving...';
        statusClass = 'badge badge-info';
        break;
      case 'saved':
        if (message) {
          var date = new Date(message);
          statusText = 'Saved at ' + date.toLocaleTimeString();
        } else {
          statusText = 'Saved';
        }
        statusClass = 'badge badge-success';
        break;
      case 'conflict':
        statusText = 'Version conflict detected';
        statusClass = 'badge badge-danger';
        break;
      case 'error':
        statusText = 'Save failed: ' + (message || 'Unknown error');
        statusClass = 'badge badge-danger';

        // Show error in prominent alert banner
        var $errorAlert = this.$container.find('.notebook-error-alert');
        var $errorMessage = this.$container.find('.notebook-error-message');
        if ($errorAlert.length && message) {
          $errorMessage.text(message);
          $errorAlert.slideDown();

          // Auto-hide after 10 seconds for non-critical errors
          // Keep visible for duplicate date errors (user must resolve)
          if (!message.toLowerCase().includes('already exists')) {
            setTimeout(function() {
              $errorAlert.slideUp();
            }, 10000);
          }
        }
        break;
    }

    this.$statusElement.text(statusText);
    this.$statusElement.attr('class', 'notebook-status ' + statusClass);
  };

  NotebookEditor.prototype.updateDayOfWeek = function() {
    if (!this.$dayOfWeek.length) {
      return;
    }

    var dateValue = this.$dateInput.val();
    if (!dateValue) {
      this.$dayOfWeek.text('');
      return;
    }

    // Parse the date (format is YYYY-MM-DD from date input)
    var date = new Date(dateValue + 'T00:00:00');

    // Get day of week name
    var dayNames = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
    var dayOfWeek = dayNames[date.getDay()];

    // Update the display
    this.$dayOfWeek.text('(' + dayOfWeek + ')');
  };

  NotebookEditor.prototype.hasUnsavedContent = function() {
    return this.hasUnsavedChanges;
  };

  // Global beforeunload handler that checks all editor instances
  var editorInstances = [];

  $(window).on('beforeunload', function(e) {
    var hasUnsaved = editorInstances.some(function(editor) {
      return editor.hasUnsavedContent();
    });

    if (hasUnsaved) {
      e.preventDefault();
      e.returnValue = '';
      return '';
    }
  });

  // Initialize all notebook editors on the page
  $(function() {
    $('.notebook-editor-container').each(function() {
      var editor = new NotebookEditor($(this));
      editorInstances.push(editor);
    });
  });

  // Expose for dynamic initialization if needed
  window.NotebookEditor = NotebookEditor;
  window.notebookEditorInstances = editorInstances;

})(jQuery);
