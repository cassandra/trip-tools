/**
 * Keyboard Manager for Journal Editor
 *
 * Manages keyboard navigation and shortcuts for the journal editor.
 * Extracted from journal-editor.js as part of modular refactoring (Phase 3).
 *
 * Features:
 * - Enter key handling: Escape from lists/blockquotes at boundaries
 * - Backspace handling: Escape from empty block elements
 * - Global shortcuts: Ctrl/Cmd+B (bold), Ctrl/Cmd+I (italic)
 * - Cursor position helpers for boundary detection
 *
 * Dependencies:
 * - jQuery ($)
 * - Tt.JournalEditor.HTML_STRUCTURE (from html-normalization.js)
 *
 * @namespace Tt.JournalEditor
 */

(function($) {
  'use strict';

  // Ensure namespace exists
  window.Tt = window.Tt || {};
  window.Tt.JournalEditor = window.Tt.JournalEditor || {};

  // Reference to HTML_STRUCTURE constants from html-normalization.js
  var HTML_STRUCTURE = Tt.JournalEditor.HTML_STRUCTURE;

  /**
   * KeyboardNavigationManager
   *
   * Manages keyboard handling for the journal editor including:
   * - Block element escape logic (Enter/Backspace at boundaries)
   * - Global keyboard shortcuts
   *
   * @constructor
   * @param {Object} options - Configuration options
   * @param {jQuery} options.$editor - jQuery-wrapped contenteditable editor element
   * @param {Function} [options.onContentChange] - Callback when content changes
   */
  function KeyboardNavigationManager(options) {
    this.$editor = options.$editor;
    this.editor = options.$editor[0];
    this.onContentChange = options.onContentChange || function() {};

    // Bind document-level events
    this._boundGlobalShortcutHandler = this._handleGlobalKeyboardShortcut.bind(this);
  }

  // ============================================================
  // CURSOR POSITION HELPERS
  // ============================================================

  /**
   * Check if cursor is at the absolute end of an element
   * @param {Range} range - Current selection range
   * @param {HTMLElement} element - Element to check
   * @returns {boolean} True if cursor is at end
   */
  KeyboardNavigationManager.prototype.isCursorAtEnd = function(range, element) {
    // Create a range from cursor to end of element
    var testRange = document.createRange();
    testRange.setStart(range.endContainer, range.endOffset);
    testRange.setEndAfter(element);

    // If the range is empty (collapsed), cursor is at end
    var text = testRange.toString();
    return text.length === 0;
  };

  /**
   * Check if cursor is at the absolute start of an element
   * @param {Range} range - Current selection range
   * @param {HTMLElement} element - Element to check
   * @returns {boolean} True if cursor is at start
   */
  KeyboardNavigationManager.prototype.isCursorAtStart = function(range, element) {
    // Create a range from start of element to cursor
    var testRange = document.createRange();
    testRange.setStartBefore(element);
    testRange.setEnd(range.startContainer, range.startOffset);

    // If the range is empty (collapsed), cursor is at start
    var text = testRange.toString();
    return text.length === 0;
  };

  /**
   * Position cursor at the start of an element
   * @param {HTMLElement} element - Element to position cursor in
   */
  KeyboardNavigationManager.prototype.setCursorAtStart = function(element) {
    var range = document.createRange();
    var selection = window.getSelection();

    range.selectNodeContents(element);
    range.collapse(true); // Collapse to start

    selection.removeAllRanges();
    selection.addRange(range);
  };

  // ============================================================
  // EVENT SETUP
  // ============================================================

  /**
   * Setup keyboard event handlers on the editor
   * Call this after constructing the manager
   */
  KeyboardNavigationManager.prototype.setup = function() {
    var self = this;

    // Handle Enter and Backspace keys for block escape and paragraph structure
    this.$editor.on('keydown.keyboardManager', function(e) {
      if (e.key === 'Enter' && !e.shiftKey && !e.ctrlKey && !e.metaKey) {
        // First check if we should escape from a block element
        self.handleEnterInBlock(e);

        // Then ensure we get <p> tags for normal Enter
        document.execCommand('defaultParagraphSeparator', false, 'p');
      } else if (e.key === 'Backspace') {
        // Check if we should escape from a block element
        self.handleBackspaceInBlock(e);
      }
    });

    // Global keyboard shortcut handler
    $(document).on('keydown.keyboardManager', this._boundGlobalShortcutHandler);
  };

  /**
   * Remove all keyboard event handlers
   * Call this when destroying the manager
   */
  KeyboardNavigationManager.prototype.destroy = function() {
    this.$editor.off('.keyboardManager');
    $(document).off('keydown.keyboardManager', this._boundGlobalShortcutHandler);
  };

  // ============================================================
  // ENTER KEY HANDLING
  // ============================================================

  /**
   * Handle Enter key in block elements (blockquote, lists, code)
   * Single Enter at start/end of block escapes to new paragraph
   * Enter in middle extends block (native behavior)
   *
   * @param {Event} e - Keydown event
   */
  KeyboardNavigationManager.prototype.handleEnterInBlock = function(e) {
    var selection = window.getSelection();
    if (!selection.rangeCount) return;

    var range = selection.getRangeAt(0);
    var $target = $(range.startContainer);
    var self = this;

    // === LISTS (ul/ol) ===
    var $li = $target.closest('li');
    if ($li.length) {
      var $list = $li.closest('ul, ol');
      var $allItems = $list.find('> li');

      // Check if this is the last item
      if ($allItems.last()[0] === $li[0]) {
        // Check if cursor is at end of last item
        if (this.isCursorAtEnd(range, $li[0])) {
          // ESCAPE AFTER: Create new paragraph after list
          e.preventDefault();

          var $textBlockContainer = $list.closest(HTML_STRUCTURE.TEXT_BLOCK_SELECTOR);
          var $newParagraph = $('<p class="' + HTML_STRUCTURE.TEXT_BLOCK_CLASS + '"><br></p>');
          $textBlockContainer.after($newParagraph);

          // Move cursor to new paragraph
          this.setCursorAtStart($newParagraph[0]);

          return;
        }
      }

      // Check if this is the first item
      if ($allItems.first()[0] === $li[0]) {
        // Check if cursor is at start of first item
        if (this.isCursorAtStart(range, $li[0])) {
          // ESCAPE BEFORE: Create new paragraph before list
          e.preventDefault();

          var $textBlockContainer = $list.closest(HTML_STRUCTURE.TEXT_BLOCK_SELECTOR);
          var $newParagraph = $('<p class="' + HTML_STRUCTURE.TEXT_BLOCK_CLASS + '"><br></p>');
          $textBlockContainer.before($newParagraph);

          // Move cursor to new paragraph
          this.setCursorAtStart($newParagraph[0]);

          return;
        }
      }

      // Let native behavior handle list Enter (extends list)
      return;
    }

    // === BLOCKQUOTES AND CODE BLOCKS (blockquote, pre) ===
    var $p = $target.closest('p');
    var $blockParent = $p.closest('blockquote, pre');

    if ($blockParent.length && $blockParent.closest(this.$editor).length) {
      var $paragraphs = $blockParent.find('p');

      // Check if we're in the last paragraph
      if ($paragraphs.last()[0] === $p[0]) {
        // Check if cursor is at end of last paragraph
        if (this.isCursorAtEnd(range, $p[0])) {
          // ESCAPE AFTER: Create new paragraph after block
          e.preventDefault();

          var $textBlockContainer = $blockParent.closest(HTML_STRUCTURE.TEXT_BLOCK_SELECTOR);
          var $newParagraph = $('<p class="' + HTML_STRUCTURE.TEXT_BLOCK_CLASS + '"><br></p>');
          $textBlockContainer.after($newParagraph);

          // Move cursor to new paragraph
          this.setCursorAtStart($newParagraph[0]);

          return;
        }
      }

      // Check if we're in the first paragraph
      if ($paragraphs.first()[0] === $p[0]) {
        // Check if cursor is at start of first paragraph
        if (this.isCursorAtStart(range, $p[0])) {
          // ESCAPE BEFORE: Create new paragraph before block
          e.preventDefault();

          var $textBlockContainer = $blockParent.closest(HTML_STRUCTURE.TEXT_BLOCK_SELECTOR);
          var $newParagraph = $('<p class="' + HTML_STRUCTURE.TEXT_BLOCK_CLASS + '"><br></p>');
          $textBlockContainer.before($newParagraph);

          // Move cursor to new paragraph
          this.setCursorAtStart($newParagraph[0]);

          return;
        }
      }
    }

    // Let native Enter work (extends block)
  };

  // ============================================================
  // BACKSPACE KEY HANDLING
  // ============================================================

  /**
   * Handle Backspace key in block elements
   * Backspace at start of empty paragraph in block escapes to regular paragraph
   *
   * @param {Event} e - Keydown event
   */
  KeyboardNavigationManager.prototype.handleBackspaceInBlock = function(e) {
    var selection = window.getSelection();
    if (!selection.rangeCount) return;

    var range = selection.getRangeAt(0);
    var $target = $(range.startContainer);

    // Check if we're in a list item
    var $li = $target.closest('li');
    if ($li.length) {
      // Check if cursor is at start of empty list item
      var text = $li.text().trim();
      if ((text === '' || $li.html() === '<br>') && range.startOffset === 0) {
        var $list = $li.closest('ul, ol');
        var $allItems = $list.find('> li');

        // If this is the first or only item
        if ($allItems.first()[0] === $li[0]) {
          e.preventDefault();

          var $textBlockContainer = $list.closest(HTML_STRUCTURE.TEXT_BLOCK_SELECTOR);

          // If list has only one item, remove entire text-block and create paragraph
          if ($allItems.length === 1) {
            var $newParagraph = $('<p class="' + HTML_STRUCTURE.TEXT_BLOCK_CLASS + '"><br></p>');
            $textBlockContainer.replaceWith($newParagraph);

            // Move cursor to new paragraph
            var newRange = document.createRange();
            newRange.selectNodeContents($newParagraph[0]);
            newRange.collapse(true);
            selection.removeAllRanges();
            selection.addRange(newRange);
          } else {
            // Remove just this list item
            $li.remove();
          }

          return;
        }
      }
      // Let native behavior handle list Backspace
      return;
    }

    // Check if we're in a paragraph inside blockquote or pre
    var $p = $target.closest('p');
    var $blockParent = $p.closest('blockquote, pre');

    if ($blockParent.length && $blockParent.closest(this.$editor).length) {
      // Check if this <p> is empty and cursor is at start
      var text = $p.text().trim();
      if ((text === '' || $p.html() === '<br>') && range.startOffset === 0) {
        var $paragraphs = $blockParent.find('p');

        // If this is the first paragraph
        if ($paragraphs.first()[0] === $p[0]) {
          e.preventDefault();

          var $textBlockContainer = $blockParent.closest(HTML_STRUCTURE.TEXT_BLOCK_SELECTOR);

          // If blockquote has only one paragraph, remove entire text-block and create paragraph
          if ($paragraphs.length === 1) {
            var $newParagraph = $('<p class="' + HTML_STRUCTURE.TEXT_BLOCK_CLASS + '"><br></p>');
            $textBlockContainer.replaceWith($newParagraph);

            // Move cursor to new paragraph
            var newRange = document.createRange();
            newRange.selectNodeContents($newParagraph[0]);
            newRange.collapse(true);
            selection.removeAllRanges();
            selection.addRange(newRange);
          } else {
            // Remove just this paragraph
            $p.remove();
          }

          return;
        }
      }
    }

    // If we didn't escape, let native Backspace work
  };

  // ============================================================
  // GLOBAL KEYBOARD SHORTCUTS
  // ============================================================

  /**
   * Global keyboard shortcut handler
   * Handles Ctrl/Cmd+B (bold) and Ctrl/Cmd+I (italic)
   *
   * @private
   * @param {Event} e - Keydown event
   */
  KeyboardNavigationManager.prototype._handleGlobalKeyboardShortcut = function(e) {
    var isCtrlOrCmd = e.ctrlKey || e.metaKey;

    // Ctrl/Cmd+B - Bold
    if (isCtrlOrCmd && e.key === 'b') {
      e.preventDefault();
      document.execCommand('bold', false, null);
      this.onContentChange();
      return;
    }

    // Ctrl/Cmd+I - Italic
    if (isCtrlOrCmd && e.key === 'i') {
      e.preventDefault();
      document.execCommand('italic', false, null);
      this.onContentChange();
      return;
    }
  };

  // ============================================================
  // EXPORTS TO Tt.JournalEditor NAMESPACE
  // ============================================================

  Tt.JournalEditor.KeyboardNavigationManager = KeyboardNavigationManager;

  // Export cursor helpers for testing
  Tt.JournalEditor._isCursorAtEnd = function(range, element) {
    var manager = new KeyboardNavigationManager({ $editor: $('<div>') });
    return manager.isCursorAtEnd(range, element);
  };

  Tt.JournalEditor._isCursorAtStart = function(range, element) {
    var manager = new KeyboardNavigationManager({ $editor: $('<div>') });
    return manager.isCursorAtStart(range, element);
  };

})(jQuery);
