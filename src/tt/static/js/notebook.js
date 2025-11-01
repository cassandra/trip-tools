(function() {
  'use strict';

  var NotebookEditor = {
    saveTimeout: null,
    isSaving: false,
    hasUnsavedChanges: false,
    lastSavedText: '',
    lastSavedDate: '',

    init: function() {
      this.textarea = document.getElementById('id_text');
      this.dateInput = document.getElementById('id_date');
      this.statusElement = document.getElementById('save-status');

      if (!this.textarea || !this.statusElement || !this.dateInput) return;

      // Initialize autosize
      if (typeof autosize !== 'undefined') {
        autosize(this.textarea);
      }

      // Store initial values
      this.lastSavedText = this.textarea.value;
      this.lastSavedDate = this.dateInput.value;
      this.updateStatus('saved');

      // Setup auto-save on input
      this.textarea.addEventListener('input', this.handleInput.bind(this));
      this.dateInput.addEventListener('change', this.handleInput.bind(this));

      // Warn on navigation with unsaved changes
      window.addEventListener('beforeunload', this.handleBeforeUnload.bind(this));
    },

    handleInput: function() {
      this.hasUnsavedChanges = (
        this.textarea.value !== this.lastSavedText ||
        this.dateInput.value !== this.lastSavedDate
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
    },

    autoSave: function() {
      if (this.isSaving || !this.hasUnsavedChanges) return;

      this.isSaving = true;
      this.updateStatus('saving');

      var data = {
        date: this.dateInput.value,
        text: this.textarea.value
      };

      fetch(window.notebookConfig.autosaveUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': window.notebookConfig.csrfToken
        },
        body: JSON.stringify(data)
      })
      .then(response => response.json())
      .then(data => {
        if (data.status === 'success') {
          this.lastSavedText = this.textarea.value;
          this.lastSavedDate = this.dateInput.value;
          this.hasUnsavedChanges = false;
          this.updateStatus('saved', data.modified_datetime);
        } else {
          this.updateStatus('error', data.message);
        }
      })
      .catch(error => {
        console.error('Auto-save error:', error);
        this.updateStatus('error', 'Network error');
      })
      .finally(() => {
        this.isSaving = false;
      });
    },

    updateStatus: function(status, message) {
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

      this.statusElement.innerHTML = '<small><em>' + statusText + '</em></small>';
      this.statusElement.className = statusClass;
    },

    handleBeforeUnload: function(e) {
      if (this.hasUnsavedChanges) {
        e.preventDefault();
        e.returnValue = '';
        return '';
      }
    }
  };

  // Initialize when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() {
      NotebookEditor.init();
    });
  } else {
    NotebookEditor.init();
  }
})();
