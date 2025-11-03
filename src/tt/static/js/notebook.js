(function($) {
  'use strict';

  // Constructor for individual notebook editor instances
  function NotebookEditor($container) {
    this.$container = $container;
    this.$form = $container.find('.notebook-form');
    this.$textarea = $container.find('.notebook-textarea');
    this.$dateInput = $container.find('.notebook-date');
    this.$statusElement = $container.find('.notebook-status');

    this.saveTimeout = null;
    this.isSaving = false;
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
    this.$container.on('change', '.notebook-date', this.handleInput.bind(this));
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

    // Set new timeout (2 seconds)
    this.saveTimeout = setTimeout(this.autoSave.bind(this), 2000);
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

          this.updateStatus('error', errorMessage);
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
    var statusClass = 'text-light';

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
        statusClass = 'text-danger';
        break;
      case 'saving':
        statusText = 'Saving...';
        statusClass = 'text-info';
        break;
      case 'saved':
        if (message) {
          var date = new Date(message);
          statusText = 'Saved at ' + date.toLocaleTimeString();
        } else {
          statusText = 'Saved';
        }
        statusClass = 'text-success';
        break;
      case 'conflict':
        statusText = 'Version conflict detected';
        statusClass = 'text-danger';
        break;
      case 'error':
        statusText = 'Save failed: ' + (message || 'Unknown error');
        statusClass = 'text-danger';

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

    this.$statusElement.html('<small><em>' + statusText + '</em></small>');
    this.$statusElement.attr('class', statusClass);
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
