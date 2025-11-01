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
      text: this.$textarea.val()
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
          this.updateStatus('saved', data.modified_datetime);
        } else {
          this.updateStatus('error', data.message);
        }
      }.bind(this),
      error: function(xhr, status, error) {
        console.error('Auto-save error:', error);
        this.updateStatus('error', 'Network error');
      }.bind(this),
      complete: function() {
        this.isSaving = false;
      }.bind(this)
    });
  };

  NotebookEditor.prototype.updateStatus = function(status, message) {
    var statusText = '';
    var statusClass = 'text-light';

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
      case 'error':
        statusText = 'Save failed: ' + (message || 'Unknown error');
        statusClass = 'text-danger';
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
