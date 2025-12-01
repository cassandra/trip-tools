/**
 * Journal Editor - HTML Normalization Module
 *
 * Extracted from journal-editor.js for modularity and testability.
 * This module handles all HTML structure normalization for the journal editor.
 *
 * Implements the HTML structure specification defined in:
 * docs/dev/domain/journal-entry-html-spec.md
 *
 * Exports to Tt.JournalEditor namespace:
 * - HTML_STRUCTURE: Constants for text-block classes/selectors
 * - ToolbarHelper: DOM cleanup and formatting normalization utilities
 * - CursorPreservation: Save/restore cursor position across DOM changes
 * - runFullNormalization: Master orchestrator for all normalization
 *
 * Dependencies:
 * - jQuery ($)
 * - TtConst (server-injected constants)
 */

(function($) {
  'use strict';

  // Initialize Tt.JournalEditor namespace
  window.Tt = window.Tt || {};
  window.Tt.JournalEditor = window.Tt.JournalEditor || {};

  /**
   * HTML STRUCTURE CONSTANTS
   * CSS classes for the persistent HTML structure in journal entries.
   * These are editor-only (not shared with server templates).
   */
  var HTML_STRUCTURE = {
    TEXT_BLOCK_CLASS: 'text-block',
    TEXT_BLOCK_SELECTOR: '.text-block',
    FULL_WIDTH_GROUP_CLASS: 'full-width-image-group',
    FULL_WIDTH_GROUP_SELECTOR: '.full-width-image-group',
  };

  /**
   * ============================================================
   * TOOLBAR HELPER - DOM CLEANUP AND NORMALIZATION
   * ============================================================
   *
   * Provides centralized DOM cleanup utilities for toolbar operations.
   * Ensures clean, normalized HTML structure after formatting operations.
   *
   * Key responsibilities:
   * - Remove empty/whitespace-only elements
   * - Normalize formatting tags (b→strong, i→em)
   * - Clean up inline styles (remove empty/zero-value attributes)
   * - Validate and fix HTML structure
   */
  var ToolbarHelper = {
    /**
     * Remove empty or whitespace-only elements
     * Aggressively cleans up artifacts from editing operations
     *
     * @param {jQuery} $root - Root element to clean (will clean descendants)
     */
    removeEmptyElements: function($root) {
      var self = this;

      // Tags that should be removed if empty
      var emptyCheckTags = ['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
                            'ul', 'ol', 'li', 'strong', 'em', 'b', 'i',
                            'a', 'span', 'div', 'blockquote', 'pre'];

      // Void elements that are allowed to be "empty" (self-closing)
      var voidElements = ['br', 'hr', 'img'];

      // Process multiple times to handle nested empty elements
      // (removing outer empty might reveal inner empty)
      var maxIterations = 5;
      var iteration = 0;
      var removedCount;

      do {
        removedCount = 0;
        iteration++;

        emptyCheckTags.forEach(function(tag) {
          $root.find(tag).each(function() {
            var $elem = $(this);

            // Protect caption spans from removal - they should persist even when empty
            // This allows users to click and re-add caption text later
            if (tag === 'span' && $elem.hasClass(TtConst.TRIP_IMAGE_CAPTION_CLASS)) {
              return; // Skip removal - captions are protected
            }

            // Get text content without considering child elements
            var textContent = $elem.contents().filter(function() {
              return this.nodeType === Node.TEXT_NODE;
            }).text().trim();

            // Check if element has any non-empty child elements
            var hasNonEmptyChildren = false;
            $elem.children().each(function() {
              var childTag = this.tagName.toLowerCase();
              // If child is a void element, consider it non-empty
              if (voidElements.indexOf(childTag) !== -1) {
                hasNonEmptyChildren = true;
                return false; // break
              }
              // If child has actual content, consider it non-empty
              if ($(this).text().trim().length > 0) {
                hasNonEmptyChildren = true;
                return false; // break
              }
            });

            // Remove if:
            // 1. No text content AND
            // 2. No non-empty children AND
            // 3. Not a special case (like <br> inside <p>)
            if (textContent.length === 0 && !hasNonEmptyChildren) {
              // Special case: <p><br></p> is valid (cursor position), but only if it's the only child
              if (tag === 'p' && $elem.children().length === 1 && $elem.children('br').length === 1) {
                // Keep this - it's a valid cursor position
                return;
              }

              $elem.remove();
              removedCount++;
            }
          });
        });
      } while (removedCount > 0 && iteration < maxIterations);
    },

    /**
     * Normalize formatting tags to semantic HTML
     * Converts <b> to <strong>, <i> to <em>
     * Unwraps nested identical formatting tags
     *
     * @param {jQuery} $root - Root element to normalize
     */
    normalizeFormatting: function($root) {
      // Convert <b> to <strong>
      $root.find('b').each(function() {
        var $b = $(this);
        var $strong = $('<strong>').html($b.html());
        // Preserve attributes if any
        $.each(this.attributes, function() {
          $strong.attr(this.name, this.value);
        });
        $b.replaceWith($strong);
      });

      // Convert <i> to <em>
      $root.find('i').each(function() {
        var $i = $(this);
        var $em = $('<em>').html($i.html());
        // Preserve attributes if any
        $.each(this.attributes, function() {
          $em.attr(this.name, this.value);
        });
        $i.replaceWith($em);
      });

      // Unwrap nested identical formatting tags
      // e.g., <strong><strong>text</strong></strong> → <strong>text</strong>
      this.unwrapNestedTags($root, 'strong');
      this.unwrapNestedTags($root, 'em');

      // Remove unnecessary spans with no attributes
      $root.find('span:not([class]):not([style]):not([data-' + TtConst.LAYOUT_DATA_ATTR + '])').each(function() {
        var $span = $(this);
        $span.replaceWith($span.html());
      });
    },

    /**
     * Unwrap nested identical tags
     * @param {jQuery} $root - Root element
     * @param {string} tagName - Tag name to unwrap (e.g., 'strong', 'em')
     */
    unwrapNestedTags: function($root, tagName) {
      var found;
      var maxIterations = 10;
      var iteration = 0;

      do {
        found = false;
        iteration++;

        $root.find(tagName).each(function() {
          var $outer = $(this);
          var $directChild = $outer.children(tagName).first();

          if ($directChild.length > 0) {
            // If the only child is the same tag, unwrap it
            if ($outer.children().length === 1) {
              $outer.replaceWith($directChild);
              found = true;
            }
            // If parent has no direct text content, just nested tag
            else if ($outer.contents().filter(function() {
              return this.nodeType === Node.TEXT_NODE && this.textContent.trim().length > 0;
            }).length === 0) {
              $outer.replaceWith($outer.html());
              found = true;
            }
          }
        });
      } while (found && iteration < maxIterations);
    },

    /**
     * Clean up inline styles
     * Remove empty style attributes and zero-value margins
     *
     * @param {jQuery} $root - Root element to clean
     */
    cleanupInlineStyles: function($root) {
      $root.find('[style]').each(function() {
        var $elem = $(this);
        var styleAttr = $elem.attr('style');

        if (!styleAttr || styleAttr.trim() === '') {
          // Remove empty style attribute
          $elem.removeAttr('style');
          return;
        }

        // Check for margin-left: 0px (from indent/outdent)
        var marginLeft = $elem.css('margin-left');
        if (marginLeft === '0px' || marginLeft === '0' || parseInt(marginLeft) === 0) {
          // Remove margin-left from style
          $elem.css('margin-left', '');

          // If style is now empty, remove the attribute
          if (!$elem.attr('style') || $elem.attr('style').trim() === '') {
            $elem.removeAttr('style');
          }
        }
      });
    },

    /**
     * Validate and fix HTML structure
     * - Move orphaned list items into proper lists
     * - Unwrap block elements from inline contexts
     * - Remove nested anchor tags
     *
     * @param {jQuery} $root - Root element to validate
     */
    validateStructure: function($root) {
      // Fix orphaned list items (li elements not inside ul/ol)
      $root.find('li').each(function() {
        var $li = $(this);
        var $parent = $li.parent();

        // If parent is not ul or ol, wrap in ul
        if ($parent[0].tagName.toLowerCase() !== 'ul' && $parent[0].tagName.toLowerCase() !== 'ol') {
          $li.wrap('<ul>');
        }
      });

      // Remove nested anchor tags (invalid HTML)
      $root.find('a a').each(function() {
        var $innerA = $(this);
        $innerA.replaceWith($innerA.html());
      });

      // Remove empty anchor tags
      $root.find('a').each(function() {
        var $a = $(this);
        if ($a.text().trim() === '' && $a.children('img').length === 0) {
          $a.remove();
        }
      });

      // Remove empty lists
      $root.find('ul, ol').each(function() {
        var $list = $(this);
        if ($list.children('li').length === 0) {
          $list.remove();
        }
      });
    },

    /**
     * Full cleanup - runs all cleanup operations in order
     * Call this after any toolbar operation
     *
     * @param {jQuery} $root - Root element to clean (usually $editor)
     */
    fullCleanup: function($root) {
      this.normalizeFormatting($root);
      this.validateStructure($root);
      this.cleanupInlineStyles($root);
      this.removeEmptyElements($root);
    }
  };

  /**
   * ============================================================
   * CONTENT NORMALIZATION FUNCTIONS
   * ============================================================
   */

  /**
   * Normalize top-level structure: wrap naked content and remove invalid elements
   *
   * Enforces these rules:
   * - All text nodes must be inside p.text-block or div.text-block
   * - Only allowed at top level: p.text-block, div.text-block, div.content-block, h1-h6
   * - Block elements (ul, ol, blockquote, pre) are handled by wrapOrphanBlockElements()
   * - <br> tags handled by handleTopLevelBrTags()
   *
   * @param {HTMLElement} editor - The contenteditable editor element
   */
  function normalizeTopLevelStructure(editor) {
    var $editor = $(editor);
    var nodesToProcess = [];

    // First pass: identify nodes that need wrapping or processing
    $editor.contents().each(function() {
      var node = this;
      var nodeType = node.nodeType;

      if (nodeType === Node.TEXT_NODE) {
        // Naked text node - needs to be wrapped
        var text = node.textContent;
        if (text.trim().length > 0) {
          nodesToProcess.push({type: 'wrapText', node: node});
        } else {
          // Remove whitespace-only text nodes
          nodesToProcess.push({type: 'remove', node: node});
        }
      } else if (nodeType === Node.ELEMENT_NODE) {
        var $node = $(node);
        var tagName = node.tagName.toLowerCase();

        // Check if element is allowed at top level
        if (tagName === 'p') {
          // Paragraph: ensure it has text-block class
          if (!$node.hasClass(HTML_STRUCTURE.TEXT_BLOCK_CLASS)) {
            nodesToProcess.push({type: 'addTextBlockClass', node: node});
          }
        } else if (tagName === 'div') {
          // Div: must be text-block or content-block
          var hasTextBlock = $node.hasClass(HTML_STRUCTURE.TEXT_BLOCK_CLASS);
          var hasContentBlock = $node.hasClass(TtConst.JOURNAL_CONTENT_BLOCK_CLASS);

          if (!hasTextBlock && !hasContentBlock) {
            // Check if it's an image wrapper (legacy or malformed)
            if ($node.hasClass(TtConst.JOURNAL_IMAGE_WRAPPER_CLASS) || $node.hasClass(HTML_STRUCTURE.FULL_WIDTH_GROUP_CLASS)) {
              // Will be handled by wrapFullWidthImageGroups()
              // For now, skip processing
            } else {
              // Invalid div - wrap its contents in text blocks
              nodesToProcess.push({type: 'unwrapDiv', node: node});
            }
          }
        } else if (['h1', 'h2', 'h3', 'h4', 'h5', 'h6'].indexOf(tagName) !== -1) {
          // Headings are allowed at top level
          // No action needed
        } else if (tagName === 'br') {
          // <br> tags handled by separate function
          // No action needed here
        } else if (['ul', 'ol', 'blockquote', 'pre'].indexOf(tagName) !== -1) {
          // Block elements - will be wrapped by wrapOrphanBlockElements()
          // No action needed here
        } else if (tagName === 'span' && $node.hasClass(TtConst.JOURNAL_IMAGE_WRAPPER_CLASS)) {
          // Image wrapper spans are allowed
          // No action needed
        } else {
          // Invalid element at top level - wrap in text block
          nodesToProcess.push({type: 'wrapElement', node: node});
        }
      }
    });

    // Second pass: apply transformations
    nodesToProcess.forEach(function(item) {
      var $node = $(item.node);

      switch (item.type) {
        case 'wrapText':
          // Wrap naked text in p.text-block
          var $p = $('<p class="' + HTML_STRUCTURE.TEXT_BLOCK_CLASS + '"></p>');
          $node.wrap($p);
          break;

        case 'remove':
          // Remove whitespace-only text nodes
          $node.remove();
          break;

        case 'addTextBlockClass':
          // Add text-block class to paragraph
          $node.addClass(HTML_STRUCTURE.TEXT_BLOCK_CLASS);
          break;

        case 'unwrapDiv':
          // Unwrap invalid div, promote children to top level
          var $children = $node.contents();
          $node.replaceWith($children);
          // Note: Promoted children will be processed in next normalization call
          break;

        case 'wrapElement':
          // Wrap invalid element in p.text-block
          var $wrapper = $('<p class="' + HTML_STRUCTURE.TEXT_BLOCK_CLASS + '"></p>');
          $node.wrap($wrapper);
          break;
      }
    });
  }

  /**
   * Handle top-level <br> tags per spec Section 2.1
   *
   * Implements 7 scenarios:
   * 1. BR between paragraphs → strip (redundant)
   * 2. BR with text before → wrap text, strip BR
   * 3. BR with text after → strip BR, wrap text
   * 4. Text-BR-Text → create two paragraphs (separator)
   * 5. Multiple BRs → treat as single separator
   * 6. BR inside paragraph → leave alone (valid line break)
   * 7. Trailing BR → strip, ensure cursor placeholder
   *
   * Key: BR never creates empty paragraphs, acts as paragraph separator
   *
   * @param {HTMLElement} editor - The contenteditable editor element
   */
  function handleTopLevelBrTags(editor) {
    var $editor = $(editor);
    var transformations = [];
    var contents = $editor.contents().toArray();

    // Helper: check if node is element node
    function isElement(node) {
      return node && node.nodeType === Node.ELEMENT_NODE;
    }

    // Helper: check if node is non-empty text node
    function isNonEmptyText(node) {
      return node &&
             node.nodeType === Node.TEXT_NODE &&
             node.textContent.trim().length > 0;
    }

    // Helper: check if node is a <br> element
    function isBr(node) {
      return isElement(node) && node.tagName.toLowerCase() === 'br';
    }

    // Helper: find previous non-whitespace sibling
    function getPreviousSignificant(node) {
      var prev = node.previousSibling;
      while (prev && prev.nodeType === Node.TEXT_NODE && !prev.textContent.trim()) {
        prev = prev.previousSibling;
      }
      return prev;
    }

    // Helper: find next non-whitespace sibling
    function getNextSignificant(node) {
      var next = node.nextSibling;
      while (next && next.nodeType === Node.TEXT_NODE && !next.textContent.trim()) {
        next = next.nextSibling;
      }
      return next;
    }

    // Helper: consolidate consecutive BR tags
    function consolidateBrTags() {
      var i = 0;
      while (i < contents.length) {
        if (isBr(contents[i])) {
          var brCount = 1;
          var j = i + 1;

          // Count consecutive BRs (skip whitespace text nodes)
          while (j < contents.length) {
            if (isBr(contents[j])) {
              brCount++;
              j++;
            } else if (contents[j].nodeType === Node.TEXT_NODE && !contents[j].textContent.trim()) {
              // Skip whitespace between BRs
              j++;
            } else {
              break;
            }
          }

          // If multiple BRs, mark extras for removal
          if (brCount > 1) {
            for (var k = i + 1; k < j; k++) {
              if (isBr(contents[k])) {
                transformations.push({type: 'removeBr', node: contents[k]});
              }
            }
          }

          i = j;
        } else {
          i++;
        }
      }
    }

    // First pass: consolidate consecutive BRs
    consolidateBrTags();

    // Second pass: process each remaining top-level BR
    for (var i = 0; i < contents.length; i++) {
      var node = contents[i];

      if (!isBr(node)) {
        continue;
      }

      // Skip if already marked for removal
      var alreadyMarked = transformations.some(function(t) {
        return t.type === 'removeBr' && t.node === node;
      });
      if (alreadyMarked) {
        continue;
      }

      var prev = getPreviousSignificant(node);
      var next = getNextSignificant(node);

      var hasTextBefore = isNonEmptyText(prev);
      var hasTextAfter = isNonEmptyText(next);
      var hasElementBefore = isElement(prev) && !isBr(prev);
      var hasElementAfter = isElement(next) && !isBr(next);

      // Scenario 4: Text-BR-Text (separator)
      if (hasTextBefore && hasTextAfter) {
        transformations.push({
          type: 'splitTextWithBr',
          brNode: node,
          textBefore: prev,
          textAfter: next
        });
      }
      // Scenario 2: Text before, no text after
      else if (hasTextBefore && !hasTextAfter) {
        transformations.push({
          type: 'wrapTextBefore',
          brNode: node,
          textNode: prev
        });
      }
      // Scenario 3: Text after, no text before
      else if (!hasTextBefore && hasTextAfter) {
        transformations.push({
          type: 'wrapTextAfter',
          brNode: node,
          textNode: next
        });
      }
      // Scenario 1: BR between elements (redundant)
      // Scenario 5: Multiple BRs (already consolidated)
      // Scenario 7: Trailing BR
      else {
        transformations.push({
          type: 'removeBr',
          node: node
        });
      }
    }

    // Third pass: apply transformations
    transformations.forEach(function(t) {
      var $node = $(t.node || t.brNode);

      switch (t.type) {
        case 'splitTextWithBr':
          // Create two paragraphs from text-BR-text
          var $p1 = $('<p class="' + HTML_STRUCTURE.TEXT_BLOCK_CLASS + '"></p>').text($(t.textBefore).text());
          var $p2 = $('<p class="' + HTML_STRUCTURE.TEXT_BLOCK_CLASS + '"></p>').text($(t.textAfter).text());

          // Replace textBefore with p1
          $(t.textBefore).replaceWith($p1);
          // Remove BR
          $(t.brNode).remove();
          // Replace textAfter with p2
          $(t.textAfter).replaceWith($p2);
          break;

        case 'wrapTextBefore':
          // Wrap text before BR in paragraph, remove BR
          var $p = $('<p class="' + HTML_STRUCTURE.TEXT_BLOCK_CLASS + '"></p>').text($(t.textNode).text());
          $(t.textNode).replaceWith($p);
          $(t.brNode).remove();
          break;

        case 'wrapTextAfter':
          // Remove BR, wrap text after in paragraph
          $(t.brNode).remove();
          var $pAfter = $('<p class="' + HTML_STRUCTURE.TEXT_BLOCK_CLASS + '"></p>').text($(t.textNode).text());
          $(t.textNode).replaceWith($pAfter);
          break;

        case 'removeBr':
          // Just remove the BR
          $node.remove();
          break;
      }
    });
  }

  /**
   * Wrap orphan block elements in div.text-block containers
   *
   * Block elements (ul, ol, blockquote, pre) cannot appear at top level.
   * They must be wrapped in div.text-block per spec Section 3.
   *
   * Float-right images at the beginning of these elements are preserved
   * inside the wrapper.
   *
   * @param {HTMLElement} editor - The contenteditable editor element
   */
  function wrapOrphanBlockElements(editor) {
    var $editor = $(editor);
    var blockElementSelectors = ['ul', 'ol', 'blockquote', 'pre'];

    blockElementSelectors.forEach(function(tagName) {
      // Find all top-level block elements of this type
      $editor.children(tagName).each(function() {
        var $blockElement = $(this);

        // Check if already wrapped in text-block
        var $parent = $blockElement.parent();
        if ($parent.hasClass(HTML_STRUCTURE.TEXT_BLOCK_CLASS)) {
          return; // Already properly wrapped
        }

        // Wrap in div.text-block
        var $wrapper = $('<div class="' + HTML_STRUCTURE.TEXT_BLOCK_CLASS + '"></div>');
        $blockElement.wrap($wrapper);
      });
    });
  }

  /**
   * Split text-blocks that contain headings (spec Section 10)
   *
   * Headings (h1-h6) cannot appear inside .text-block elements.
   * Split into 1-3 elements depending on content position:
   * - Content before AND after: 3 elements (block, heading, block)
   * - Content only before OR after: 2 elements
   * - Heading alone: 1 element (unwrap)
   *
   * Float-right images stay with first content block.
   *
   * @param {jQuery} $editor - jQuery-wrapped contenteditable element
   */
  function splitHeadingsFromTextBlocks($editor) {
    var headingSelectors = 'h1, h2, h3, h4, h5, h6';

    // Process all text-blocks that contain headings
    $editor.find(HTML_STRUCTURE.TEXT_BLOCK_SELECTOR).each(function() {
      var $textBlock = $(this);
      var $headings = $textBlock.find(headingSelectors);

      if ($headings.length === 0) {
        return; // No headings, skip
      }

      // Process each heading (may be multiple)
      $headings.each(function() {
        var $heading = $(this);

        // Re-query parent (may have changed if previous heading was split)
        var $currentTextBlock = $heading.closest(HTML_STRUCTURE.TEXT_BLOCK_SELECTOR);
        if ($currentTextBlock.length === 0) {
          return; // Heading already moved to top level
        }

        // Get all children of text-block
        var $children = $currentTextBlock.children();
        var headingIndex = $children.index($heading);

        // Split into before/heading/after groups
        var $before = $children.slice(0, headingIndex);
        var $after = $children.slice(headingIndex + 1);

        var hasBefore = $before.length > 0;
        var hasAfter = $after.length > 0;

        if (hasBefore && hasAfter) {
          // Case 1: Content before AND after → 3 elements
          var $newBeforeBlock = $('<div class="' + HTML_STRUCTURE.TEXT_BLOCK_CLASS + '"></div>');
          var $newAfterBlock = $('<div class="' + HTML_STRUCTURE.TEXT_BLOCK_CLASS + '"></div>');

          $newBeforeBlock.append($before);
          $newAfterBlock.append($after);

          // Preserve float-right image in first block
          var hasFloatImage = $currentTextBlock.hasClass(TtConst.JOURNAL_FLOAT_MARKER_CLASS);
          if (hasFloatImage) {
            $newBeforeBlock.addClass(TtConst.JOURNAL_FLOAT_MARKER_CLASS);
          }

          // Replace text-block with 3 elements
          $currentTextBlock.before($newBeforeBlock);
          $currentTextBlock.before($heading);
          $currentTextBlock.before($newAfterBlock);
          $currentTextBlock.remove();
        }
        else if (hasBefore) {
          // Case 2: Content only before → 2 elements
          var $beforeBlock = $('<div class="' + HTML_STRUCTURE.TEXT_BLOCK_SELECTOR + '"></div>');
          $beforeBlock.append($before);

          // Preserve float-right image class
          if ($currentTextBlock.hasClass(TtConst.JOURNAL_FLOAT_MARKER_CLASS)) {
            $beforeBlock.addClass(TtConst.JOURNAL_FLOAT_MARKER_CLASS);
          }

          $currentTextBlock.before($beforeBlock);
          $currentTextBlock.before($heading);
          $currentTextBlock.remove();
        }
        else if (hasAfter) {
          // Case 3: Content only after → 2 elements
          var $afterBlock = $('<div class="' + HTML_STRUCTURE.TEXT_BLOCK_CLASS + '"></div>');
          $afterBlock.append($after);

          $currentTextBlock.before($heading);
          $currentTextBlock.before($afterBlock);
          $currentTextBlock.remove();
        }
        else {
          // Case 4: Heading alone → unwrap to top level
          $currentTextBlock.before($heading);
          $currentTextBlock.remove();
        }
      });
    });

    // Also handle headings inside p.text-block (shouldn't happen, but be defensive)
    $editor.find('p.' + HTML_STRUCTURE.TEXT_BLOCK_CLASS).each(function() {
      var $p = $(this);
      var $headings = $p.find(headingSelectors);

      if ($headings.length > 0) {
        // Invalid: heading inside paragraph
        // Unwrap the paragraph, promote heading to top level
        var $contents = $p.contents();
        $p.replaceWith($contents);
      }
    });
  }

  /**
   * Enforce one block element per div.text-block (spec Section 8.2)
   *
   * Rules:
   * - One block element (ul, ol, blockquote, pre) per div.text-block
   * - One paragraph per p.text-block
   * - Multiple paragraphs in div.text-block → convert each to p.text-block
   * - Multiple block elements in div.text-block → split into separate divs
   *
   * Float-right images stay with first block.
   *
   * @param {jQuery} $editor - jQuery-wrapped contenteditable element
   */
  function enforceOneBlockPerTextBlock($editor) {
    // Process div.text-block elements
    $editor.find('div.' + HTML_STRUCTURE.TEXT_BLOCK_CLASS).each(function() {
      var $div = $(this);
      var blockSelectors = 'ul, ol, blockquote, pre, p';
      var $blockElements = $div.children(blockSelectors);

      if ($blockElements.length <= 1) {
        return; // Already has one or zero block elements
      }

      // Has multiple block elements - need to split
      var hasFloatImage = $div.hasClass(TtConst.JOURNAL_FLOAT_MARKER_CLASS);
      var $floatImage = null;

      // Find float-right image if exists
      if (hasFloatImage) {
        $floatImage = $div.children(TtConst.JOURNAL_IMAGE_WRAPPER_FLOAT_SELECTOR).first();
      }

      var isFirst = true;

      $blockElements.each(function() {
        var $block = $(this);
        var tagName = $block.prop('tagName').toLowerCase();

        if (tagName === 'p') {
          // Convert paragraph to p.text-block
          var $newP = $('<p class="' + HTML_STRUCTURE.TEXT_BLOCK_CLASS + '"></p>');
          $newP.html($block.html());

          // First block gets float-right image
          if (isFirst && hasFloatImage && $floatImage) {
            $newP.addClass(TtConst.JOURNAL_FLOAT_MARKER_CLASS);
            $newP.prepend($floatImage);
          }

          $div.before($newP);
        } else {
          // Wrap other block elements in new div.text-block
          var $newDiv = $('<div class="' + HTML_STRUCTURE.TEXT_BLOCK_CLASS + '"></div>');
          $newDiv.append($block.clone());

          // First block gets float-right image
          if (isFirst && hasFloatImage && $floatImage) {
            $newDiv.addClass(TtConst.JOURNAL_FLOAT_MARKER_CLASS);
            $newDiv.prepend($floatImage);
          }

          $div.before($newDiv);
        }

        isFirst = false;
      });

      // Remove original div (now empty)
      $div.remove();
    });

    // Process p.text-block that somehow contains nested paragraphs
    $editor.find('p.' + HTML_STRUCTURE.TEXT_BLOCK_CLASS).each(function() {
      var $p = $(this);
      var $nestedPs = $p.find('p');

      if ($nestedPs.length > 0) {
        // Invalid: nested paragraphs
        // Unwrap outer paragraph, convert children to text-blocks
        var $children = $p.contents();
        $p.replaceWith($children);
      }
    });
  }

  /**
   * Convert image-only text-blocks to full-width image groups
   *
   * Text-blocks must contain text content. If a text-block contains only
   * images (no text), convert it to a content-block full-width-image-group.
   *
   * This handles cases where float-right images end up alone after
   * normalization splits.
   *
   * @param {jQuery} $editor - jQuery-wrapped contenteditable element
   */
  function convertImageOnlyTextBlocks($editor) {
    $editor.find(HTML_STRUCTURE.TEXT_BLOCK_SELECTOR).each(function() {
      var $textBlock = $(this);

      // Get text content (excluding images)
      var $clone = $textBlock.clone();
      $clone.find(TtConst.JOURNAL_IMAGE_WRAPPER_SELECTOR).remove();
      var textContent = $clone.text().trim();

      if (textContent.length === 0) {
        // Text block contains only images, no text
        var $images = $textBlock.find(TtConst.JOURNAL_IMAGE_WRAPPER_SELECTOR);

        if ($images.length > 0) {
          // Change all images to full-width layout
          $images.attr('data-' + TtConst.LAYOUT_DATA_ATTR, 'full-width');

          // Replace text-block with content-block
          var $contentBlock = $('<div class="' + TtConst.JOURNAL_CONTENT_BLOCK_CLASS + ' ' + HTML_STRUCTURE.FULL_WIDTH_GROUP_CLASS + '"></div>');
          $contentBlock.append($images);
          $textBlock.replaceWith($contentBlock);
        } else {
          // Empty text block with no images - remove it
          $textBlock.remove();
        }
      }
    });
  }

  /**
   * Ensure editor is never completely empty
   *
   * Safety net: if editor has no content after normalization,
   * add an empty paragraph with <br> for cursor positioning.
   *
   * @param {HTMLElement} editor - The contenteditable editor element
   */
  function ensureEditorNotEmpty(editor) {
    var $editor = $(editor);

    if ($editor.children().length === 0) {
      // Editor is completely empty - add cursor placeholder
      $editor.append('<p class="' + HTML_STRUCTURE.TEXT_BLOCK_CLASS + '"><br></p>');
    }
  }

  /**
   * ============================================================
   * CURSOR PRESERVATION
   * ============================================================
   */

  /**
   * Cursor Preservation Utility
   *
   * Saves and restores cursor position across DOM transformations.
   * Uses text offset approach for robustness when nodes are moved/wrapped.
   */
  var CursorPreservation = {
    /**
     * Save current cursor position or text selection
     * @param {jQuery} $editor - jQuery-wrapped editor element
     * @returns {Object|null} Marker object for restoration, or null if no selection
     */
    save: function($editor) {
      var selection = window.getSelection();
      if (!selection || selection.rangeCount === 0) {
        return null;
      }

      var range = selection.getRangeAt(0);
      var editor = $editor[0];

      // Check if selection is inside editor
      if (!editor.contains(range.commonAncestorContainer)) {
        return null;
      }

      // Check if cursor is inside an image caption (special handling needed)
      var $captionElement = $(range.startContainer).closest(TtConst.JOURNAL_IMAGE_CAPTION_SELECTOR);
      var captionContext = null;

      if ($captionElement.length > 0) {
        // Find the parent image wrapper to get UUID
        var $imageWrapper = $captionElement.closest(TtConst.JOURNAL_IMAGE_WRAPPER_SELECTOR);
        var $img = $imageWrapper.find('img');
        // Note: Images use UUID_DATA_ATTR (data-uuid), not IMAGE_UUID_DATA_ATTR
        var imageUuid = $img.data(TtConst.UUID_DATA_ATTR);

        if (imageUuid) {
          // Calculate offset within caption only
          var captionRange = range.cloneRange();
          captionRange.selectNodeContents($captionElement[0]);
          captionRange.setEnd(range.startContainer, range.startOffset);
          var captionOffset = captionRange.toString().length;

          captionContext = {
            imageUuid: imageUuid,
            offsetInCaption: captionOffset
          };
        }
      }

      // Calculate START text offset (for selections)
      var preStartRange = range.cloneRange();
      preStartRange.selectNodeContents(editor);
      preStartRange.setEnd(range.startContainer, range.startOffset);
      var startTextOffset = preStartRange.toString().length;

      // Calculate END text offset
      var preEndRange = range.cloneRange();
      preEndRange.selectNodeContents(editor);
      preEndRange.setEnd(range.endContainer, range.endOffset);
      var endTextOffset = preEndRange.toString().length;

      // Also store visual element reference for fallback
      var $closestBlock = $(range.endContainer).closest(HTML_STRUCTURE.TEXT_BLOCK_SELECTOR + ', h1, h2, h3, h4, h5, h6');
      var blockIndex = $closestBlock.length ? $editor.children().index($closestBlock) : 0;

      return {
        startTextOffset: startTextOffset,
        endTextOffset: endTextOffset,
        blockIndex: blockIndex,
        isCollapsed: range.collapsed,
        captionContext: captionContext
      };
    },

    /**
     * Restore cursor position or text selection from marker
     * @param {jQuery} $editor - jQuery-wrapped editor element
     * @param {Object} marker - Marker object from save()
     */
    restore: function($editor, marker) {
      if (!marker) {
        return;
      }

      var editor = $editor[0];

      try {
        // Check for caption context first - this handles the edge case where
        // cursor at start of caption has same text offset as end of preceding text
        if (marker.captionContext) {
          var restored = this.restoreCaptionCursor($editor, marker.captionContext);
          if (restored) {
            return; // Successfully restored to caption
          }
          // Fall through to regular restoration if caption not found
        }

        var range = document.createRange();

        // Backward compatibility: handle old markers with only textOffset
        var startTextOffset = marker.startTextOffset !== undefined ? marker.startTextOffset : marker.textOffset;
        var endTextOffset = marker.endTextOffset !== undefined ? marker.endTextOffset : marker.textOffset;

        var currentOffset = 0;
        var startNode = null;
        var startOffset = 0;
        var endNode = null;
        var endOffset = 0;

        // Walk through text nodes to find both start and end positions
        var walker = document.createTreeWalker(
          editor,
          NodeFilter.SHOW_TEXT,
          null,
          false
        );

        var node;
        while (node = walker.nextNode()) {
          var nodeLength = node.textContent.length;

          // Find start position
          if (!startNode && currentOffset + nodeLength >= startTextOffset) {
            startNode = node;
            startOffset = Math.min(startTextOffset - currentOffset, nodeLength);
          }

          // Find end position
          if (!endNode && currentOffset + nodeLength >= endTextOffset) {
            endNode = node;
            endOffset = Math.min(endTextOffset - currentOffset, nodeLength);
            break; // Found both positions
          }

          currentOffset += nodeLength;
        }

        if (startNode && endNode) {
          // Successfully found both positions - restore selection or cursor
          range.setStart(startNode, startOffset);
          range.setEnd(endNode, endOffset);
        } else {
          // Fallback: position at end of block at saved index
          var $children = $editor.children();
          var $targetBlock = $children.eq(Math.min(marker.blockIndex, $children.length - 1));

          if ($targetBlock.length) {
            range.selectNodeContents($targetBlock[0]);
            range.collapse(false); // Collapse to end
          } else {
            // Ultimate fallback: end of editor
            range.selectNodeContents(editor);
            range.collapse(false);
          }
        }

        // Apply the range
        var selection = window.getSelection();
        selection.removeAllRanges();
        selection.addRange(range);
      } catch (e) {
        // If restoration fails, just log and continue
        // Better to have working editor without cursor than to crash
        console.warn('Cursor restoration failed:', e);
      }
    },

    /**
     * Restore cursor position specifically within an image caption
     * Uses image UUID as stable identifier to find the correct caption
     * @param {jQuery} $editor - jQuery-wrapped editor element
     * @param {Object} captionContext - {imageUuid, offsetInCaption}
     * @returns {boolean} True if restoration succeeded, false otherwise
     */
    restoreCaptionCursor: function($editor, captionContext) {
      // Find the image by UUID (images use data-uuid attribute)
      var $image = $editor.find('img[data-' + TtConst.UUID_DATA_ATTR + '="' + captionContext.imageUuid + '"]');
      if ($image.length === 0) {
        return false;
      }

      // Find the caption within that image wrapper
      var $wrapper = $image.closest(TtConst.JOURNAL_IMAGE_WRAPPER_SELECTOR);
      var $caption = $wrapper.find(TtConst.JOURNAL_IMAGE_CAPTION_SELECTOR);
      if ($caption.length === 0) {
        return false;
      }

      // Find the text node and position within caption
      var targetOffset = captionContext.offsetInCaption;
      var currentOffset = 0;
      var targetNode = null;
      var nodeOffset = 0;

      var walker = document.createTreeWalker(
        $caption[0],
        NodeFilter.SHOW_TEXT,
        null,
        false
      );

      var node;
      while (node = walker.nextNode()) {
        var nodeLength = node.textContent.length;
        if (currentOffset + nodeLength >= targetOffset) {
          targetNode = node;
          nodeOffset = targetOffset - currentOffset;
          break;
        }
        currentOffset += nodeLength;
      }

      if (targetNode) {
        var range = document.createRange();
        range.setStart(targetNode, Math.min(nodeOffset, targetNode.textContent.length));
        range.collapse(true);

        var selection = window.getSelection();
        selection.removeAllRanges();
        selection.addRange(range);
        return true;
      }

      // Caption exists but has no text nodes (empty caption)
      // Position cursor at start of caption element
      if ($caption[0].childNodes.length === 0) {
        // Empty caption - create a text node for cursor positioning
        var textNode = document.createTextNode('');
        $caption[0].appendChild(textNode);

        var range = document.createRange();
        range.setStart(textNode, 0);
        range.collapse(true);

        var selection = window.getSelection();
        selection.removeAllRanges();
        selection.addRange(range);
        return true;
      }

      return false;
    }
  };

  /**
   * Ensure all caption elements have at least an empty text node for cursor positioning.
   * This allows users to click on empty captions and start typing.
   *
   * @param {jQuery} $editor - jQuery-wrapped contenteditable element
   */
  function ensureCaptionTextNodes($editor) {
    $editor.find(TtConst.JOURNAL_IMAGE_CAPTION_SELECTOR).each(function() {
      // If caption has no child nodes at all, add empty text node for cursor positioning
      if (this.childNodes.length === 0) {
        this.appendChild(document.createTextNode(''));
      }
    });
  }

  /**
   * ============================================================
   * MASTER NORMALIZATION FUNCTION
   * ============================================================
   */

  /**
   * Master Normalization Function
   *
   * Orchestrates all normalization operations in correct sequence.
   * This is the single entry point for running full normalization.
   *
   * @param {HTMLElement} editor - The contenteditable editor element
   */
  function runFullNormalization(editor) {
    var $editor = $(editor);

    // Run normalization functions in correct order
    normalizeTopLevelStructure(editor);
    handleTopLevelBrTags(editor);
    wrapOrphanBlockElements(editor);
    splitHeadingsFromTextBlocks($editor);
    enforceOneBlockPerTextBlock($editor);
    convertImageOnlyTextBlocks($editor);
    ensureEditorNotEmpty(editor);

    // Run existing cleanup helpers
    ToolbarHelper.fullCleanup($editor);

    // Ensure captions have text nodes for cursor positioning
    // Must run after cleanup to ensure empty captions aren't removed
    ensureCaptionTextNodes($editor);
  }

  /**
   * ============================================================
   * EXPORTS TO Tt.JournalEditor NAMESPACE
   * ============================================================
   */

  Tt.JournalEditor.HTML_STRUCTURE = HTML_STRUCTURE;
  Tt.JournalEditor.ToolbarHelper = ToolbarHelper;
  Tt.JournalEditor.CursorPreservation = CursorPreservation;
  Tt.JournalEditor.runFullNormalization = runFullNormalization;

  // Also export individual normalization functions for testing
  Tt.JournalEditor._normalizeTopLevelStructure = normalizeTopLevelStructure;
  Tt.JournalEditor._handleTopLevelBrTags = handleTopLevelBrTags;
  Tt.JournalEditor._wrapOrphanBlockElements = wrapOrphanBlockElements;
  Tt.JournalEditor._splitHeadingsFromTextBlocks = splitHeadingsFromTextBlocks;
  Tt.JournalEditor._enforceOneBlockPerTextBlock = enforceOneBlockPerTextBlock;
  Tt.JournalEditor._convertImageOnlyTextBlocks = convertImageOnlyTextBlocks;
  Tt.JournalEditor._ensureEditorNotEmpty = ensureEditorNotEmpty;

})(jQuery);
