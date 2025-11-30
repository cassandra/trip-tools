/**
 * EditorLayoutManager
 *
 * Manages layout-related DOM manipulations for the journal editor.
 * Responsible for maintaining the structure of persistent HTML elements.
 *
 * Features:
 * - Wrapping consecutive full-width images in groups
 * - Marking paragraphs with float-right images for CSS clearing
 * - Ensuring delete buttons exist on all image wrappers
 * - Unified layout refresh orchestration
 *
 * Dependencies:
 * - jQuery
 * - TtConst (from main.js)
 * - Tt.JournalEditor.HTML_STRUCTURE (from html-normalization.js)
 * - Tt.JournalEditor.runFullNormalization (from html-normalization.js)
 *
 * Usage:
 *   var layoutManager = new Tt.JournalEditor.EditorLayoutManager($editor);
 *   layoutManager.refreshLayout();
 */

(function($) {
  'use strict';

  // =========================================================================
  // Dependencies from other modules
  // =========================================================================
  var HTML_STRUCTURE = Tt.JournalEditor.HTML_STRUCTURE;
  var runFullNormalization = Tt.JournalEditor.runFullNormalization;

  // =========================================================================
  // Editor Transient Constants
  // =========================================================================

  /**
   * EDITOR-ONLY TRANSIENT CONSTANTS
   * These are runtime-only CSS classes added/removed by JavaScript.
   * They are NEVER saved to the database and NEVER appear in templates.
   *
   * For shared constants (IDs, classes used in templates), see Tt namespace in main.js
   */
  var EDITOR_TRANSIENT = {
    // Transient CSS classes (editor UI only, never saved)
    CSS_DELETE_BTN: 'trip-image-delete-btn',
    CSS_DROP_ZONE_ACTIVE: 'drop-zone-active',
    CSS_DROP_ZONE_BETWEEN: 'drop-zone-between',
    CSS_DRAGGING: 'dragging',
    CSS_DRAG_OVER: 'drag-over',
    CSS_SELECTED: 'selected',
    CSS_JOURNAL_EDITOR_MULTI_IMAGE_PANEL: 'journal-editor-multi-image-panel',

    // Transient element selectors
    SEL_DELETE_BTN: '.trip-image-delete-btn',
    SEL_DROP_ZONE_BETWEEN: '.drop-zone-between',
    SEL_JOURNAL_EDITOR_MULTI_IMAGE_PANEL: '.journal-editor-multi-image-panel',
  };

  // =========================================================================
  // EditorLayoutManager
  // =========================================================================

  /**
   * EditorLayoutManager
   *
   * Manages layout-related DOM manipulations for the editor.
   * Responsible for maintaining the structure of persistent HTML elements.
   *
   * This manager handles:
   * - Wrapping consecutive full-width images in groups
   * - Marking paragraphs with float-right images for CSS clearing
   * - Ensuring delete buttons exist on all image wrappers
   *
   * @param {jQuery} $editor - The contenteditable editor element
   */
  function EditorLayoutManager($editor) {
    this.$editor = $editor;
  }

  /**
   * Wrap consecutive full-width images in container divs
   * This allows them to clear floats properly (block-level element needed)
   */
  EditorLayoutManager.prototype.wrapFullWidthImageGroups = function() {
    // Remove existing wrappers first
    this.$editor.find(HTML_STRUCTURE.FULL_WIDTH_GROUP_SELECTOR).each(function() {
      var $group = $(this);
      $group.children(TtConst.JOURNAL_IMAGE_WRAPPER_FULL_SELECTOR).unwrap();
    });

    // Group consecutive full-width images
    var groups = [];
    var currentGroup = [];

    this.$editor.children().each(function() {
      var $child = $(this);
      if ($child.is(TtConst.JOURNAL_IMAGE_WRAPPER_FULL_SELECTOR)) {
        currentGroup.push(this);
      } else {
        if (currentGroup.length > 0) {
          groups.push(currentGroup);
          currentGroup = [];
        }
      }
    });

    // Don't forget the last group
    if (currentGroup.length > 0) {
      groups.push(currentGroup);
    }

    // Wrap each group with content-block class per spec
    groups.forEach(function(group) {
      $(group).wrapAll('<div class="' + TtConst.JOURNAL_CONTENT_BLOCK_CLASS + ' ' + HTML_STRUCTURE.FULL_WIDTH_GROUP_CLASS + '"></div>');
    });
  };

  /**
   * Mark text blocks that contain float-right images
   * This allows CSS to clear floats appropriately
   * Updated to handle both p.text-block and div.text-block per spec
   */
  EditorLayoutManager.prototype.markFloatParagraphs = function() {
    // Remove existing marks from all text blocks
    this.$editor.find(HTML_STRUCTURE.TEXT_BLOCK_SELECTOR).removeClass(TtConst.JOURNAL_FLOAT_MARKER_CLASS);

    // Mark text blocks (both <p> and <div>) with float-right images
    this.$editor.find(HTML_STRUCTURE.TEXT_BLOCK_SELECTOR).each(function() {
      var $textBlock = $(this);
      if ($textBlock.find(TtConst.JOURNAL_IMAGE_WRAPPER_FLOAT_SELECTOR).length > 0) {
        $textBlock.addClass(TtConst.JOURNAL_FLOAT_MARKER_CLASS);
      }
    });
  };

  /**
   * Ensure all image wrappers have delete buttons
   * Called on page load to add buttons to wrappers from saved content
   */
  EditorLayoutManager.prototype.ensureDeleteButtons = function() {
    this.$editor.find(TtConst.JOURNAL_IMAGE_WRAPPER_SELECTOR).each(function() {
      var $wrapper = $(this);

      // Check if delete button already exists
      if ($wrapper.find(EDITOR_TRANSIENT.SEL_DELETE_BTN).length === 0) {
        // Add delete button
        var $deleteBtn = $('<button>', {
          'class': EDITOR_TRANSIENT.CSS_DELETE_BTN,
          'type': 'button',
          'title': 'Remove image',
          'text': '×'
        });
        $wrapper.append($deleteBtn);
      }
    });
  };

  /**
   * Unified layout refresh method
   * Calls all layout methods in the correct order
   * This ensures consistent layout behavior across all operations
   */
  EditorLayoutManager.prototype.refreshLayout = function() {
    // 1. Run full HTML normalization first
    runFullNormalization(this.$editor[0]);

    // 2. Ensure delete buttons exist (must happen after normalization)
    this.ensureDeleteButtons();

    // 3. Wrap full-width image groups (affects DOM structure)
    this.wrapFullWidthImageGroups();

    // 4. Mark float paragraphs (depends on DOM structure being finalized)
    this.markFloatParagraphs();
  };

  // =========================================================================
  // Export to Tt.JournalEditor namespace
  // =========================================================================
  window.Tt = window.Tt || {};
  window.Tt.JournalEditor = window.Tt.JournalEditor || {};
  window.Tt.JournalEditor.EditorLayoutManager = EditorLayoutManager;
  window.Tt.JournalEditor.EDITOR_TRANSIENT = EDITOR_TRANSIENT;

})(jQuery);
