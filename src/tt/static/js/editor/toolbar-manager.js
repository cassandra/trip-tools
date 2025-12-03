/**
 * Toolbar Manager for Journal Editor
 *
 * Manages the formatting toolbar for journal content editing.
 * Extracted from journal-editor.js as part of modular refactoring.
 *
 * Features:
 * - Text formatting: Bold, Italic (custom implementation)
 * - Headings: H2, H3, H4 (custom implementation)
 * - Lists: Unordered (bullets), Ordered (numbers) (custom implementation)
 * - Links: Hyperlink insertion with validation (custom implementation)
 * - Code blocks: Monospace pre blocks (custom implementation)
 * - Indent/Outdent: Margin-based indentation (custom implementation)
 * - Active state tracking for toolbar buttons
 *
 * @namespace Tt.JournalEditor
 */

(function($) {
  'use strict';

  // Ensure namespace exists
  window.Tt = window.Tt || {};
  window.Tt.JournalEditor = window.Tt.JournalEditor || {};

  /**
   * JournalEditorToolbar
   *
   * Manages the formatting toolbar for the journal editor.
   * Uses browser's native execCommand for most operations.
   *
   * @constructor
   * @param {jQuery} $toolbar - jQuery-wrapped toolbar element
   * @param {jQuery} $editor - jQuery-wrapped contenteditable editor element
   * @param {Function} onContentChange - Callback to trigger when content changes
   */
  function JournalEditorToolbar($toolbar, $editor, onContentChange) {
    this.$toolbar = $toolbar;
    this.$editor = $editor;
    this.editor = $editor[0];
    this.onContentChange = onContentChange;

    this.initializeToolbar();
  }

  /**
   * Initialize toolbar event handlers
   */
  JournalEditorToolbar.prototype.initializeToolbar = function() {
    var self = this;

    // Bold button
    this.$toolbar.find('[data-command="bold"]').on('click', function(e) {
      e.preventDefault();
      self.applyBold();
    });

    // Italic button
    this.$toolbar.find('[data-command="italic"]').on('click', function(e) {
      e.preventDefault();
      self.applyItalic();
    });

    // Heading buttons (H2, H3, H4)
    this.$toolbar.find('[data-command="heading"]').on('click', function(e) {
      e.preventDefault();
      var level = $(this).data('level');
      self.applyHeading(level);
    });

    // Unordered list button
    this.$toolbar.find('[data-command="insertUnorderedList"]').on('click', function(e) {
      e.preventDefault();
      self.toggleList('ul');
    });

    // Ordered list button
    this.$toolbar.find('[data-command="insertOrderedList"]').on('click', function(e) {
      e.preventDefault();
      self.toggleList('ol');
    });

    // Indent button (simple indentation)
    this.$toolbar.find('[data-command="indent"]').on('click', function(e) {
      e.preventDefault();
      self.applyIndent();
    });

    // Quote button (quotation styling)
    this.$toolbar.find('[data-command="quote"]').on('click', function(e) {
      e.preventDefault();
      self.applyQuote();
    });

    // Link button
    this.$toolbar.find('[data-command="createLink"]').on('click', function(e) {
      e.preventDefault();
      self.createLink();
    });

    // Code block button
    this.$toolbar.find('[data-command="code"]').on('click', function(e) {
      e.preventDefault();
      self.insertCodeBlock();
    });

    // Update active states on selection change
    this.$editor.on('mouseup keyup', function() {
      self.updateActiveStates();
    });
  };

  /**
   * Apply bold formatting to selection
   * Respects block boundaries - applies <strong> within each block separately
   */
  JournalEditorToolbar.prototype.applyBold = function() {
    this.editor.focus();

    // Use browser's native execCommand which respects block boundaries
    document.execCommand('bold', false, null);

    // Trigger autosave (which will normalize after idle period)
    if (this.onContentChange) {
      this.onContentChange();
    }
  };

  /**
   * Apply italic formatting to selection
   * Respects block boundaries - applies <em> within each block separately
   */
  JournalEditorToolbar.prototype.applyItalic = function() {
    this.editor.focus();

    // Use browser's native execCommand which respects block boundaries
    document.execCommand('italic', false, null);

    // Trigger autosave
    if (this.onContentChange) {
      this.onContentChange();
    }
  };

  /**
   * Apply heading format using browser's native formatBlock
   * @param {number|string} level - Heading level (2, 3, or 4) or 'p' for paragraph
   */
  JournalEditorToolbar.prototype.applyHeading = function(level) {
    this.editor.focus();

    // Use browser's native formatBlock command
    // 'p' converts to paragraph, numeric levels convert to headings
    var tag = level === 'p' ? 'p' : 'h' + level;
    document.execCommand('formatBlock', false, tag);

    // Trigger autosave
    if (this.onContentChange) {
      this.onContentChange();
    }
  };

  /**
   * Toggle list formatting using browser's native command
   * @param {string} listType - 'ul' or 'ol'
   */
  JournalEditorToolbar.prototype.toggleList = function(listType) {
    this.editor.focus();

    // Use browser's native list toggle command
    var command = listType === 'ul' ? 'insertUnorderedList' : 'insertOrderedList';
    document.execCommand(command, false, null);

    // Trigger autosave
    if (this.onContentChange) {
      this.onContentChange();
    }
  };

  /**
   * Create a hyperlink with URL validation
   */
  JournalEditorToolbar.prototype.createLink = function() {
    this.editor.focus();
    var selection = window.getSelection();
    if (!selection.rangeCount) return;

    var range = selection.getRangeAt(0);

    // Check if already in a link
    var container = range.commonAncestorContainer;
    var $container = container.nodeType === Node.TEXT_NODE ? $(container.parentNode) : $(container);
    var $linkParent = $container.closest('a');

    if ($linkParent.length > 0) {
      // Already in a link - remove it
      $linkParent.contents().unwrap();

      // Trigger autosave
      if (this.onContentChange) {
        this.onContentChange();
      }
      return;
    }

    // Not in a link - prompt for URL
    var url = prompt('Enter URL:', 'https://');

    if (url && url.trim() !== '' && url !== 'https://') {
      // Basic URL validation
      var urlPattern = /^(https?:\/\/|mailto:)/i;
      if (!urlPattern.test(url)) {
        url = 'https://' + url;
      }

      // Create link element
      var link = document.createElement('a');
      link.href = url;

      // Wrap selection or insert link with selected text
      try {
        range.surroundContents(link);
      } catch (e) {
        // surroundContents fails if range spans multiple elements
        // Fallback: wrap extracted contents
        var fragment = range.extractContents();
        link.appendChild(fragment);
        range.insertNode(link);
      }

      // Trigger autosave
      if (this.onContentChange) {
        this.onContentChange();
      }
    }
  };

  /**
   * Insert a code block using browser's native formatBlock
   */
  JournalEditorToolbar.prototype.insertCodeBlock = function() {
    this.editor.focus();

    // Use browser's native formatBlock with 'pre'
    document.execCommand('formatBlock', false, 'pre');

    // Trigger content change for autosave
    if (this.onContentChange) {
      this.onContentChange();
    }
  };

  /**
   * Toggle simple indentation (blockquote without quote styling)
   *
   * Behavior:
   * - Plain text -> Create blockquote
   * - Indented (blockquote) -> Remove blockquote
   * - Quoted (blockquote.quote) -> Convert to plain indent (remove .quote class)
   */
  JournalEditorToolbar.prototype.applyIndent = function() {
    this.editor.focus();

    var selection = window.getSelection();
    if (!selection.rangeCount) return;

    var $existing = $(selection.getRangeAt(0).commonAncestorContainer).closest('blockquote');

    if ($existing && $existing.length) {
      if ($existing.hasClass('quote')) {
        // Quoted -> Indented: remove quote class
        $existing.removeClass('quote');
      } else {
        // Indented -> Plain: remove blockquote entirely
        document.execCommand('outdent', false, null);
      }
    } else {
      // Plain -> Indented: create blockquote
      document.execCommand('indent', false, null);
    }

    if (this.onContentChange) {
      this.onContentChange();
    }
  };

  /**
   * Toggle quotation styling (blockquote with .quote class)
   *
   * Behavior:
   * - Plain text -> Create blockquote with .quote class
   * - Indented (blockquote) -> Convert to quote (add .quote class)
   * - Quoted (blockquote.quote) -> Remove blockquote entirely
   */
  JournalEditorToolbar.prototype.applyQuote = function() {
    this.editor.focus();

    var selection = window.getSelection();
    if (!selection.rangeCount) return;

    var $existing = $(selection.getRangeAt(0).commonAncestorContainer).closest('blockquote');

    if ($existing && $existing.length) {
      if ($existing.hasClass('quote')) {
        // Quoted -> Plain: remove blockquote entirely
        document.execCommand('outdent', false, null);
      } else {
        // Indented -> Quoted: add quote class
        $existing.addClass('quote');
      }
    } else {
      // Plain -> Quoted: create blockquote with quote class
      document.execCommand('indent', false, null);

      // Find the newly created blockquote and add quote class
      var newSelection = window.getSelection();
      if (newSelection.rangeCount) {
        var $blockquote = $(newSelection.getRangeAt(0).commonAncestorContainer).closest('blockquote');
        $blockquote.addClass('quote');
      }
    }

    if (this.onContentChange) {
      this.onContentChange();
    }
  };

  /**
   * Update active states of toolbar buttons based on current selection
   * Uses DOM traversal instead of queryCommandState for accurate detection
   */
  JournalEditorToolbar.prototype.updateActiveStates = function() {
    var selection = window.getSelection();
    if (!selection.rangeCount) return;

    var range = selection.getRangeAt(0);
    var container = range.commonAncestorContainer;
    var $container = container.nodeType === Node.TEXT_NODE ? $(container.parentNode) : $(container);

    // Check for bold (strong or b tag)
    var isBold = $container.closest('strong, b').length > 0;
    this.$toolbar.find('[data-command="bold"]').toggleClass('active', isBold);

    // Check for italic (em or i tag)
    var isItalic = $container.closest('em, i').length > 0;
    this.$toolbar.find('[data-command="italic"]').toggleClass('active', isItalic);

    // Check for lists (li element indicates we're in a list)
    var $listItem = $container.closest('li');
    if ($listItem.length > 0) {
      var $list = $listItem.parent();
      var isUL = $list.prop('tagName').toLowerCase() === 'ul';
      var isOL = $list.prop('tagName').toLowerCase() === 'ol';

      this.$toolbar.find('[data-command="insertUnorderedList"]').toggleClass('active', isUL);
      this.$toolbar.find('[data-command="insertOrderedList"]').toggleClass('active', isOL);
    } else {
      this.$toolbar.find('[data-command="insertUnorderedList"]').removeClass('active');
      this.$toolbar.find('[data-command="insertOrderedList"]').removeClass('active');
    }
  };

  // ============================================================
  // EXPORTS TO Tt.JournalEditor NAMESPACE
  // ============================================================

  Tt.JournalEditor.JournalEditorToolbar = JournalEditorToolbar;

})(jQuery);
