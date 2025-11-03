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

  NotebookEditor.prototype.handleVersionConflict = function(conflictData) {
    this.updateStatus('conflict', conflictData.message);
    this.showConflictDetails(conflictData);
  };

  NotebookEditor.prototype.showConflictDetails = function(conflictData) {
    var serverDate = new Date(conflictData.server_modified_at);
    var timeStr = serverDate.toLocaleString();

    var modalHtml = [
      '<div class="modal fade" id="conflictModal" tabindex="-1" role="dialog">',
      '  <div class="modal-dialog modal-lg" role="document">',
      '    <div class="modal-content">',
      '      <div class="modal-header">',
      '        <h5 class="modal-title">Version Conflict Detected</h5>',
      '        <button type="button" class="close" data-dismiss="modal">',
      '          <span>&times;</span>',
      '        </button>',
      '      </div>',
      '      <div class="modal-body">',
      '        <div class="alert alert-warning">',
      '          <strong>⚠️ Another user has modified this entry</strong><br>',
      '          This notebook entry was modified by <strong>' + conflictData.modified_by_name + '</strong> ',
      '          at <strong>' + timeStr + '</strong>.<br><br>',
      '          <em>Your unsaved changes may be lost if you refresh. Consider copying your changes before refreshing.</em>',
      '        </div>',
      '        <h6>Changes Comparison:</h6>',
      '        <p class="text-muted small">Review what changed on the server before deciding to refresh:</p>',
      '        <div class="diff-container">' + conflictData.diff_html + '</div>',
      '      </div>',
      '      <div class="modal-footer">',
      '        <button type="button" class="btn btn-secondary" data-dismiss="modal">Close (Keep Editing)</button>',
      '        <button type="button" class="btn btn-primary" id="refreshFromModal">Refresh to See Latest</button>',
      '      </div>',
      '    </div>',
      '  </div>',
      '</div>'
    ].join('');

    var $modal = $(modalHtml);
    $('body').append($modal);
    $modal.modal('show');

    $modal.find('#refreshFromModal').on('click', function() {
      // Force full page reload with cache-busting to get latest server content
      window.location.href = window.location.pathname + '?_=' + Date.now();
    });

    $modal.on('hidden.bs.modal', function() {
      $modal.remove();
    });
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
        statusClass = 'text-warning';
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
