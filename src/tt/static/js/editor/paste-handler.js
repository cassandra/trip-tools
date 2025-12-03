/**
 * PasteHandler
 *
 * Handles paste events in the journal editor, stripping formatting
 * and converting newlines to proper paragraph structure.
 *
 * Features:
 * - Strips all formatting from pasted content
 * - Converts newlines to paragraph breaks
 * - Handles multiple consecutive blank lines (collapse to single break)
 * - Handles insertion at various cursor positions (start, end, middle of block)
 * - Properly splits paragraphs when pasting in the middle
 *
 * Dependencies:
 * - jQuery
 * - Tt.JournalEditor.HTML_STRUCTURE (from html-normalization.js)
 *
 * Usage:
 *   var pasteHandler = new Tt.JournalEditor.PasteHandler($editor, {
 *     onContentChange: function() { ... }
 *   });
 *   pasteHandler.setup();
 */

(function($) {
  'use strict';

  // =========================================================================
  // Dependencies from other modules
  // =========================================================================
  var HTML_STRUCTURE = Tt.JournalEditor.HTML_STRUCTURE;

  // =========================================================================
  // PasteHandler
  // =========================================================================

  /**
   * PasteHandler
   *
   * Handles paste events, stripping formatting and creating proper paragraph structure.
   *
   * @param {jQuery} $editor - The contenteditable editor element
   * @param {Object} options - Configuration options
   * @param {Function} options.onContentChange - Callback when content changes
   */
  function PasteHandler($editor, options) {
    this.$editor = $editor;
    this.options = options || {};
    this.onContentChange = options.onContentChange || function() {};
  }

  /**
   * Set up paste event handler
   */
  PasteHandler.prototype.setup = function() {
    var self = this;

    this.$editor.on('paste.pasteHandler', function(e) {
      self.handlePaste(e);
    });
  };

  /**
   * Remove paste event handler
   */
  PasteHandler.prototype.destroy = function() {
    this.$editor.off('paste.pasteHandler');
  };

  /**
   * Handle paste event
   * @param {Event} e - jQuery paste event
   */
  PasteHandler.prototype.handlePaste = function(e) {
    var self = this;

    e.preventDefault();
    var text = (e.originalEvent.clipboardData || window.clipboardData).getData('text/plain');

    // If empty, do nothing
    if (!text || text.trim().length === 0) {
      return;
    }

    // Decode common HTML entities that may appear in pasted text
    text = this._decodeHtmlEntities(text);

    // Split on newlines (handle both \n and \r\n)
    var lines = text.split(/\r?\n/);

    // Filter out empty lines (per spec: multiple blank lines = single paragraph break)
    var nonEmptyLines = lines.filter(function(line) {
      return line.trim().length > 0;
    });

    // If only one line, use simple insertText (no paragraph creation needed)
    if (nonEmptyLines.length === 1) {
      document.execCommand('insertText', false, nonEmptyLines[0]);
      return;
    }

    // Multiple lines: create paragraphs
    var selection = window.getSelection();
    if (!selection.rangeCount) {
      return;
    }

    var range = selection.getRangeAt(0);
    range.deleteContents(); // Remove any selected text first

    // Create paragraph elements for each line
    var $paragraphs = [];
    for (var i = 0; i < nonEmptyLines.length; i++) {
      var $p = $('<p class="' + HTML_STRUCTURE.TEXT_BLOCK_CLASS + '"></p>').text(nonEmptyLines[i]);
      $paragraphs.push($p[0]);
    }

    // Insert paragraphs at cursor position
    this._insertParagraphsAtCursor(range, $paragraphs);

    // Place cursor at end of last inserted paragraph
    this._placeCursorAtEnd($paragraphs, selection);

    // Trigger content change callback
    this.onContentChange();
  };

  /**
   * Insert paragraphs at the current cursor position
   * Handles different insertion scenarios:
   * 1. Cursor in empty paragraph -> replace it
   * 2. Cursor at start of paragraph -> insert before
   * 3. Cursor at end of paragraph -> insert after
   * 4. Cursor in middle of paragraph -> split it
   *
   * @param {Range} range - Current selection range
   * @param {Array} $paragraphs - Array of paragraph DOM elements
   */
  PasteHandler.prototype._insertParagraphsAtCursor = function(range, $paragraphs) {
    var $currentBlock = $(range.startContainer).closest(HTML_STRUCTURE.TEXT_BLOCK_SELECTOR + ', h1, h2, h3, h4, h5, h6');

    if ($currentBlock.length === 0) {
      // Not in a block, find insertion point
      this._insertAtEditorLevel(range, $paragraphs);
    } else {
      // We're in a block element
      this._insertInBlock($currentBlock, range, $paragraphs);
    }
  };

  /**
   * Insert paragraphs when cursor is at editor level (not in a block)
   * @param {Range} range - Current selection range
   * @param {Array} $paragraphs - Array of paragraph DOM elements
   */
  PasteHandler.prototype._insertAtEditorLevel = function(range, $paragraphs) {
    var $editor = this.$editor;
    var insertionPoint = range.startContainer;

    // If we're in the editor itself, append paragraphs
    if (insertionPoint === this.$editor[0]) {
      for (var i = 0; i < $paragraphs.length; i++) {
        $editor.append($paragraphs[i]);
      }
    } else {
      // Insert before closest block element
      var $closestBlock = $(insertionPoint).closest(HTML_STRUCTURE.TEXT_BLOCK_SELECTOR + ', h1, h2, h3, h4, h5, h6');
      if ($closestBlock.length) {
        $closestBlock.before($paragraphs);
      } else {
        $editor.append($paragraphs);
      }
    }
  };

  /**
   * Insert paragraphs when cursor is inside a block element
   * @param {jQuery} $currentBlock - The block element containing the cursor
   * @param {Range} range - Current selection range
   * @param {Array} $paragraphs - Array of paragraph DOM elements
   */
  PasteHandler.prototype._insertInBlock = function($currentBlock, range, $paragraphs) {
    var blockEl = $currentBlock[0];
    var textContent = $currentBlock.text().trim();

    // Check if block is empty (or only has <br>)
    if (textContent.length === 0) {
      // Replace empty block with pasted paragraphs
      $currentBlock.before($paragraphs);
      $currentBlock.remove();
    } else {
      // Block has content - we need to determine where cursor is
      this._insertInNonEmptyBlock($currentBlock, blockEl, range, $paragraphs);
    }
  };

  /**
   * Insert paragraphs in a non-empty block, handling split if needed
   * @param {jQuery} $currentBlock - The block element
   * @param {Element} blockEl - The block DOM element
   * @param {Range} range - Current selection range
   * @param {Array} $paragraphs - Array of paragraph DOM elements
   */
  PasteHandler.prototype._insertInNonEmptyBlock = function($currentBlock, blockEl, range, $paragraphs) {
    // Extract content before and after cursor
    var beforeRange = document.createRange();
    beforeRange.setStart(blockEl, 0);
    beforeRange.setEnd(range.startContainer, range.startOffset);
    var beforeText = beforeRange.toString().trim();

    var afterRange = document.createRange();
    afterRange.setStart(range.startContainer, range.startOffset);
    afterRange.setEnd(blockEl, blockEl.childNodes.length);
    var afterText = afterRange.toString().trim();

    if (beforeText.length === 0) {
      // Cursor at start - insert before
      $currentBlock.before($paragraphs);
    } else if (afterText.length === 0) {
      // Cursor at end - insert after
      $currentBlock.after($paragraphs);
    } else {
      // Cursor in middle - split the paragraph
      // Keep 'before' content in current block
      $currentBlock.text(beforeText);

      // Insert pasted paragraphs
      $currentBlock.after($paragraphs);

      // Create new paragraph for 'after' content
      var $afterP = $('<p class="' + HTML_STRUCTURE.TEXT_BLOCK_CLASS + '"></p>').text(afterText);
      $($paragraphs[$paragraphs.length - 1]).after($afterP);
    }
  };

  /**
   * Place cursor at end of last inserted paragraph
   * @param {Array} $paragraphs - Array of paragraph DOM elements
   * @param {Selection} selection - Current selection object
   */
  PasteHandler.prototype._placeCursorAtEnd = function($paragraphs, selection) {
    if ($paragraphs.length === 0) {
      return;
    }

    var lastParagraph = $paragraphs[$paragraphs.length - 1];
    var newRange = document.createRange();
    var textNode = lastParagraph.firstChild;

    if (textNode && textNode.nodeType === Node.TEXT_NODE) {
      newRange.setStart(textNode, textNode.length);
      newRange.setEnd(textNode, textNode.length);
    } else {
      newRange.selectNodeContents(lastParagraph);
      newRange.collapse(false);
    }

    selection.removeAllRanges();
    selection.addRange(newRange);
  };

  /**
   * Decode common HTML entities in text
   * Handles entities that may appear when copying from web pages or HTML sources
   * @param {string} text - Text that may contain HTML entities
   * @returns {string} Text with entities decoded
   */
  PasteHandler.prototype._decodeHtmlEntities = function(text) {
    // Use a temporary element to decode entities properly
    // This handles all HTML entities including numeric ones
    var temp = document.createElement('textarea');
    temp.innerHTML = text;
    return temp.value;
  };

  // =========================================================================
  // Export to Tt.JournalEditor namespace
  // =========================================================================
  window.Tt = window.Tt || {};
  window.Tt.JournalEditor = window.Tt.JournalEditor || {};
  window.Tt.JournalEditor.PasteHandler = PasteHandler;

})(jQuery);
