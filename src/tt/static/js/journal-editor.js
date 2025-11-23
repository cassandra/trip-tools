/**
 * Journal Entry Editor - ContentEditable with Image Management
 *
 * EDITOR-ONLY JavaScript - This file is for the edit view only.
 * For the public/external journal view, see journal.js instead.
 *
 * Features:
 * - Rich text editing with automatic paragraph creation
 * - Drag-and-drop image insertion with layout detection
 * - Image click to inspect in modal
 * - Image reordering within editor
 * - Image removal with keyboard and hover controls
 * - Autosave integration with 2-second debounce
 * - Responsive design with mobile warning
 * - Simplified keyboard shortcuts (6 total)
 *   - Text formatting: Ctrl/Cmd+B/I
 *   - Picker operations: Escape, Delete, Ctrl+R (stub)
 *   - Editor operations: Escape, Delete, Ctrl+R (stub)
 *   - Global: Ctrl+/ for help (stub)
 *
 * ============================================================
 * HTML CONTRACT: PERSISTENT vs TRANSIENT
 * ============================================================
 *
 * PERSISTENT HTML (saved to database, visible in public view):
 * - <span class="trip-image-wrapper" data-layout="float-right|full-width">
 * - <img class="trip-image" data-uuid="..." src="..." alt="...">
 * - <span class="trip-image-caption">Caption text</span> (optional, if caption exists)
 * - <div class="full-width-image-group"> (wraps consecutive full-width images)
 * - <p class="has-float-image"> (paragraphs containing float-right images)
 * - data-layout attribute (float-right | full-width)
 * - data-uuid attribute (image identifier)
 *
 * TRANSIENT HTML (editor-only, removed before save):
 * - <button class="trip-image-delete-btn">× (delete button)
 * - CSS classes: .drop-zone-active, .drop-zone-between, .dragging, .drag-over, .selected
 * - Any <div class="drop-zone-between"> elements
 *
 * The getCleanHTML() method is responsible for removing ALL transient
 * elements/classes before saving. The backend HTML sanitizer (Bleach)
 * provides additional safety by whitelisting only allowed tags/attributes.
 *
 * ARCHITECTURE:
 * - EditorLayoutManager: Manages layout-related DOM manipulations
 * - AutoSaveManager: Handles saving with debouncing and retry logic
 * - JournalEditor: Main orchestrator connecting UI events to managers
 */

(function($) {
  'use strict';

  /**
   * EDITOR-ONLY TRANSIENT CONSTANTS
   * These are runtime-only CSS classes added/removed by JavaScript.
   * They are NEVER saved to the database and NEVER appear in templates.
   *
   * For shared constants (IDs, classes used in templates), see Tt namespace in main.js
   */
  const EDITOR_TRANSIENT = {
    // Transient CSS classes (editor UI only, never saved)
    CSS_DELETE_BTN: 'trip-image-delete-btn',
    CSS_DROP_ZONE_ACTIVE: 'drop-zone-active',
    CSS_DROP_ZONE_BETWEEN: 'drop-zone-between',
    CSS_DRAGGING: 'dragging',
    CSS_DRAG_OVER: 'drag-over',
    CSS_SELECTED: 'selected',

    // Transient element selectors
    SEL_DELETE_BTN: '.trip-image-delete-btn',
    SEL_DROP_ZONE_BETWEEN: '.drop-zone-between',
  };

  /**
   * LAYOUT VALUES
   * These are the actual string values for data-layout attribute.
   * Not DOM selectors, just the values.
   */
  const LAYOUT_VALUES = {
    FLOAT_RIGHT: 'float-right',
    FULL_WIDTH: 'full-width',
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
      $root.find('span:not([class]):not([style]):not([data-layout])').each(function() {
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
          var $ul = $('<ul>').append($li);
          $li.replaceWith($ul);
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
   * CONTENT NORMALIZATION
   * Enforce canonical structure after content changes
   * ============================================================
   */

  /**
   * ============================================================
   * HTML NORMALIZATION SYSTEM
   * ============================================================
   * Implements the HTML structure specification defined in:
   * docs/dev/domain/journal-entry-html-spec.md
   *
   * This system enforces canonical HTML structure for journal entries:
   * - Top-level elements: p.text-block, div.text-block, div.content-block, h1-h6
   * - Float-right images work in any .text-block
   * - Handles <br> tags per spec Section 2.1
   * - Splits headings from text blocks per spec Section 10
   *
   * NOTE: Old normalizeEditorContent() function removed 2025-01-19
   * as it did not align with new specification requirements.
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
          if (!$node.hasClass('text-block')) {
            nodesToProcess.push({type: 'addTextBlockClass', node: node});
          }
        } else if (tagName === 'div') {
          // Div: must be text-block or content-block
          var hasTextBlock = $node.hasClass('text-block');
          var hasContentBlock = $node.hasClass('content-block');

          if (!hasTextBlock && !hasContentBlock) {
            // Check if it's an image wrapper (legacy or malformed)
            if ($node.hasClass('trip-image-wrapper') || $node.hasClass('full-width-image-group')) {
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
        } else if (tagName === 'span' && $node.hasClass('trip-image-wrapper')) {
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
          var $p = $('<p class="text-block"></p>');
          $node.wrap($p);
          break;

        case 'remove':
          // Remove whitespace-only text nodes
          $node.remove();
          break;

        case 'addTextBlockClass':
          // Add text-block class to paragraph
          $node.addClass('text-block');
          break;

        case 'unwrapDiv':
          // Unwrap invalid div, promote children to top level
          var $children = $node.contents();
          $node.replaceWith($children);
          // Note: Promoted children will be processed in next normalization call
          break;

        case 'wrapElement':
          // Wrap invalid element in p.text-block
          var $wrapper = $('<p class="text-block"></p>');
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
          var $p1 = $('<p class="text-block"></p>').text($(t.textBefore).text());
          var $p2 = $('<p class="text-block"></p>').text($(t.textAfter).text());

          // Replace textBefore with p1
          $(t.textBefore).replaceWith($p1);
          // Remove BR
          $(t.brNode).remove();
          // Replace textAfter with p2
          $(t.textAfter).replaceWith($p2);
          break;

        case 'wrapTextBefore':
          // Wrap text before BR in paragraph, remove BR
          var $p = $('<p class="text-block"></p>').text($(t.textNode).text());
          $(t.textNode).replaceWith($p);
          $(t.brNode).remove();
          break;

        case 'wrapTextAfter':
          // Remove BR, wrap text after in paragraph
          $(t.brNode).remove();
          var $pAfter = $('<p class="text-block"></p>').text($(t.textNode).text());
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
        if ($parent.hasClass('text-block')) {
          return; // Already properly wrapped
        }

        // Wrap in div.text-block
        var $wrapper = $('<div class="text-block"></div>');
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
    $editor.find('.text-block').each(function() {
      var $textBlock = $(this);
      var $headings = $textBlock.find(headingSelectors);

      if ($headings.length === 0) {
        return; // No headings, skip
      }

      // Process each heading (may be multiple)
      $headings.each(function() {
        var $heading = $(this);

        // Re-query parent (may have changed if previous heading was split)
        var $currentTextBlock = $heading.closest('.text-block');
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
          var $newBeforeBlock = $('<div class="text-block"></div>');
          var $newAfterBlock = $('<div class="text-block"></div>');

          $newBeforeBlock.append($before);
          $newAfterBlock.append($after);

          // Preserve float-right image in first block
          var hasFloatImage = $currentTextBlock.hasClass('has-float-image');
          if (hasFloatImage) {
            $newBeforeBlock.addClass('has-float-image');
          }

          // Replace text-block with 3 elements
          $currentTextBlock.before($newBeforeBlock);
          $currentTextBlock.before($heading);
          $currentTextBlock.before($newAfterBlock);
          $currentTextBlock.remove();
        }
        else if (hasBefore) {
          // Case 2: Content only before → 2 elements
          var $beforeBlock = $('<div class="text-block"></div>');
          $beforeBlock.append($before);

          // Preserve float-right image class
          if ($currentTextBlock.hasClass('has-float-image')) {
            $beforeBlock.addClass('has-float-image');
          }

          $currentTextBlock.before($beforeBlock);
          $currentTextBlock.before($heading);
          $currentTextBlock.remove();
        }
        else if (hasAfter) {
          // Case 3: Content only after → 2 elements
          var $afterBlock = $('<div class="text-block"></div>');
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
    $editor.find('p.text-block').each(function() {
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
    $editor.find('div.text-block').each(function() {
      var $div = $(this);
      var blockSelectors = 'ul, ol, blockquote, pre, p';
      var $blockElements = $div.children(blockSelectors);

      if ($blockElements.length <= 1) {
        return; // Already has one or zero block elements
      }

      // Has multiple block elements - need to split
      var hasFloatImage = $div.hasClass('has-float-image');
      var $floatImage = null;

      // Find float-right image if exists
      if (hasFloatImage) {
        $floatImage = $div.children('.trip-image-wrapper[data-layout="float-right"]').first();
      }

      var isFirst = true;

      $blockElements.each(function() {
        var $block = $(this);
        var tagName = $block.prop('tagName').toLowerCase();

        if (tagName === 'p') {
          // Convert paragraph to p.text-block
          var $newP = $('<p class="text-block"></p>');
          $newP.html($block.html());

          // First block gets float-right image
          if (isFirst && hasFloatImage && $floatImage) {
            $newP.addClass('has-float-image');
            $newP.prepend($floatImage);
          }

          $div.before($newP);
        } else {
          // Wrap other block elements in new div.text-block
          var $newDiv = $('<div class="text-block"></div>');
          $newDiv.append($block.clone());

          // First block gets float-right image
          if (isFirst && hasFloatImage && $floatImage) {
            $newDiv.addClass('has-float-image');
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
    $editor.find('p.text-block').each(function() {
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
    $editor.find('.text-block').each(function() {
      var $textBlock = $(this);

      // Get text content (excluding images)
      var $clone = $textBlock.clone();
      $clone.find('.trip-image-wrapper').remove();
      var textContent = $clone.text().trim();

      if (textContent.length === 0) {
        // Text block contains only images, no text
        var $images = $textBlock.find('.trip-image-wrapper');

        if ($images.length > 0) {
          // Change all images to full-width layout
          $images.attr('data-layout', 'full-width');

          // Replace text-block with content-block
          var $contentBlock = $('<div class="content-block full-width-image-group"></div>');
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
      $editor.append('<p class="text-block"><br></p>');
    }
  }

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
      var $closestBlock = $(range.endContainer).closest('.text-block, h1, h2, h3, h4, h5, h6');
      var blockIndex = $closestBlock.length ? $editor.children().index($closestBlock) : 0;

      return {
        startTextOffset: startTextOffset,
        endTextOffset: endTextOffset,
        blockIndex: blockIndex,
        isCollapsed: range.collapsed
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
    }
  };

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
  }

  /**
   * ============================================================
   * SHARED UTILITIES FOR IMAGE SELECTION
   * ============================================================
   */

  /**
   * Get modifier key state from event
   * @param {Event} event - Mouse event
   * @returns {Object} { isCtrlOrCmd, isShift }
   */
  function getSelectionModifiers(event) {
    return {
      isCtrlOrCmd: event.ctrlKey || event.metaKey,
      isShift: event.shiftKey
    };
  }

  /**
   * SelectionBadgeManager
   *
   * Manages a selection count badge next to a reference element.
   * Used by both picker and editor to show selection counts.
   */
  function SelectionBadgeManager($referenceElement, badgeId) {
    this.$referenceElement = $referenceElement;
    this.badgeId = badgeId;
    this.$badge = null;
  }

  SelectionBadgeManager.prototype.update = function(count) {
    if (count > 0) {
      if (!this.$badge) {
        this.$badge = $('<span>')
          .attr('id', this.badgeId)
          .addClass('badge badge-primary ml-2')
          .insertAfter(this.$referenceElement);
      }
      this.$badge.text(count + ' selected');
    } else {
      this.remove();
    }
  };

  SelectionBadgeManager.prototype.remove = function() {
    if (this.$badge) {
      this.$badge.remove();
      this.$badge = null;
    }
  };

  /**
   * ImageSelectionCoordinator
   *
   * Ensures mutual exclusivity between picker and editor image selections.
   * Only one area can have selections at a time.
   *
   * Usage:
   * - Call notifyPickerSelection() when picker selections change
   * - Call notifyEditorSelection() when editor selections change
   * - Coordinator will call clearSelection() on the other area as needed
   */
  function ImageSelectionCoordinator() {
    this.pickerClearCallback = null;
    this.editorClearCallback = null;
  }

  ImageSelectionCoordinator.prototype.registerPicker = function(clearCallback) {
    this.pickerClearCallback = clearCallback;
  };

  ImageSelectionCoordinator.prototype.registerEditor = function(clearCallback) {
    this.editorClearCallback = clearCallback;
  };

  ImageSelectionCoordinator.prototype.notifyPickerSelection = function(hasSelections) {
    if (hasSelections && this.editorClearCallback) {
      this.editorClearCallback();
    }
  };

  ImageSelectionCoordinator.prototype.notifyEditorSelection = function(hasSelections) {
    if (hasSelections && this.pickerClearCallback) {
      this.pickerClearCallback();
    }
  };

  // Global singleton
  const imageSelectionCoordinator = new ImageSelectionCoordinator();

  /**
   * ImageDataService
   *
   * Centralized service for retrieving image data from picker cards.
   * Decouples features from picker DOM structure.
   *
   * All image data lookups should go through this service to avoid
   * duplicated DOM queries and tight coupling to picker implementation.
   */
  const ImageDataService = {
    /**
     * Get complete image data for a given UUID
     * @param {string} uuid - Image UUID
     * @returns {Object|null} Image data object or null if not found
     *   {
     *     uuid: string,
     *     url: string,
     *     caption: string,
     *     inspectUrl: string
     *   }
     */
    getImageDataByUUID: function(uuid) {
      if (!uuid) {
        console.error('[ImageDataService] Cannot lookup image: missing UUID');
        return null;
      }

      // Find picker card with this UUID
      var $card = $(Tt.JOURNAL_IMAGE_CARD_SELECTOR + '[data-' + Tt.JOURNAL_IMAGE_UUID_ATTR + '="' + uuid + '"]');

      if ($card.length === 0) {
        console.warn('[ImageDataService] No picker card found for UUID:', uuid);
        return null;
      }

      // Extract all data from card in one pass
      var imageUuid = $card.data('image-uuid');
      var $img = $card.find('img');
      var url = $img.attr('src') || '';
      var caption = $img.attr('alt') || '';
      var inspectUrl = $card.data('inspect-url') || '';

      if (!imageUuid) {
        console.error('[ImageDataService] Picker card missing data-image-uuid for UUID:', uuid);
        return null;
      }

      return {
        uuid: imageUuid,
        url: url,
        caption: caption,
        inspectUrl: inspectUrl
      };
    }
  };

  // Module state
  let editorInstance = null;

  /**
   * JournalEditorToolbar
   *
   * Manages the formatting toolbar for rich text editing.
   * Uses custom DOM manipulation for all operations with immediate cleanup.
   *
   * Features:
   * - Text formatting: Bold, Italic (custom implementation)
   * - Headings: H2, H3, H4 (custom implementation)
   * - Lists: Unordered (bullets), Ordered (numbers) (custom implementation)
   * - Links: Hyperlink insertion with validation (custom implementation)
   * - Code blocks: Monospace pre blocks (custom implementation)
   * - Indent/Outdent: Margin-based indentation (custom implementation)
   * - Immediate HTML cleanup after each operation via ToolbarHelper
   * - Integrates with existing autosave system
   */
  function JournalEditorToolbar($toolbar, $editor, onContentChange) {
    this.$toolbar = $toolbar;
    this.$editor = $editor;
    this.editor = $editor[0];
    this.onContentChange = onContentChange;

    this.initializeToolbar();
  }

  /**
   * COMMENTED OUT - Not needed with native execCommand approach
   * Get all top-level blocks within the current selection
   * Returns only direct children of the editor that are valid blocks
   * @returns {Array<Element>} Array of block elements (p, h2-h4, ul, ol, pre)
   */
  /*
  JournalEditorToolbar.prototype.getSelectedBlocks = function() {
    var selection = window.getSelection();
    if (!selection.rangeCount) return [];

    var range = selection.getRangeAt(0);
    var blocks = [];
    var self = this;

    console.log('getSelectedBlocks: range start=', range.startContainer, range.startOffset, 'end=', range.endContainer, range.endOffset);

    // Get all direct children of editor that fall within the selection
    var allBlocks = [];
    var startBlock = null;
    var endBlock = null;

    // Collect all valid blocks
    $(this.editor).children().each(function() {
      var tagName = this.tagName ? this.tagName.toLowerCase() : '';

      // Only include valid block types
      if (['p', 'h2', 'h3', 'h4', 'ul', 'ol', 'pre'].indexOf(tagName) === -1) {
        return; // Skip br, image wrappers, divs, etc.
      }

      allBlocks.push(this);
    });

    // Find start and end blocks
    allBlocks.forEach(function(block, index) {
      var containsStart = block.contains(range.startContainer) || block === range.startContainer;
      var containsEnd = block.contains(range.endContainer) || block === range.endContainer;

      console.log('  Block', block.tagName.toLowerCase(), $(block).text().substring(0, 20), 'containsStart=', containsStart, 'containsEnd=', containsEnd);

      if (containsStart) {
        startBlock = block;
      }
      if (containsEnd) {
        endBlock = block;
      }
    });

    // If start/end not found in blocks, check if selection is at editor level
    if (!startBlock && range.startContainer === self.editor) {
      // Selection starts at editor level - find first block at or after offset
      var startOffset = range.startOffset;
      var childAtOffset = self.editor.childNodes[startOffset];
      console.log('  Start at editor level, offset', startOffset, 'child=', childAtOffset);

      // Find the first valid block at or after this position
      var found = false;
      for (var i = 0; i < allBlocks.length; i++) {
        var blockIndex = Array.prototype.indexOf.call(self.editor.childNodes, allBlocks[i]);
        if (blockIndex >= startOffset) {
          startBlock = allBlocks[i];
          found = true;
          break;
        }
      }
      if (!found && allBlocks.length > 0) {
        startBlock = allBlocks[0];
      }
      console.log('  -> using start block', startBlock ? startBlock.tagName : 'none');
    }
    if (!endBlock && range.endContainer === self.editor) {
      // Selection ends at editor level - find last block before offset
      var endOffset = range.endOffset;
      console.log('  End at editor level, offset', endOffset);

      // Find the last valid block before or at this position
      for (var i = allBlocks.length - 1; i >= 0; i--) {
        var blockIndex = Array.prototype.indexOf.call(self.editor.childNodes, allBlocks[i]);
        if (blockIndex < endOffset) {
          endBlock = allBlocks[i];
          break;
        }
      }
      if (!endBlock && allBlocks.length > 0) {
        endBlock = allBlocks[allBlocks.length - 1];
      }
      console.log('  -> using end block', endBlock ? endBlock.tagName : 'none');
    }

    // Collect all blocks from start to end (inclusive)
    if (startBlock && endBlock) {
      var startIndex = allBlocks.indexOf(startBlock);
      var endIndex = allBlocks.indexOf(endBlock);
      if (startIndex !== -1 && endIndex !== -1) {
        for (var i = startIndex; i <= endIndex; i++) {
          blocks.push(allBlocks[i]);
        }
      }
    }

    // If no blocks found, cursor might be in a specific block - find it
    if (blocks.length === 0) {
      console.log('  No blocks found via intersection, trying fallback...');
      var container = range.commonAncestorContainer;
      var node = container.nodeType === Node.TEXT_NODE ? container.parentNode : container;

      // Walk up to find the top-level block
      while (node && node !== this.editor) {
        if (node.parentNode === this.editor) {
          var tagName = node.tagName ? node.tagName.toLowerCase() : '';
          console.log('    Found top-level node:', tagName);
          if (['p', 'h2', 'h3', 'h4', 'ul', 'ol', 'pre'].indexOf(tagName) !== -1) {
            blocks.push(node);
          }
          break;
        }
        node = node.parentNode;
      }
    }

    console.log('  Final blocks count:', blocks.length);
    return blocks;
  };
  */

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

    // Indent button
    this.$toolbar.find('[data-command="indent"]').on('click', function(e) {
      e.preventDefault();
      self.adjustIndent(40); // Increase by 40px
    });

    // Outdent button
    this.$toolbar.find('[data-command="outdent"]').on('click', function(e) {
      e.preventDefault();
      self.adjustIndent(-40); // Decrease by 40px
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
   * @param {number} level - Heading level (2, 3, or 4)
   */
  JournalEditorToolbar.prototype.applyHeading = function(level) {
    this.editor.focus();

    // Use browser's native formatBlock command
    document.execCommand('formatBlock', false, 'h' + level);

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

      // No cleanup needed - inline formatting is simple

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
   * Adjust indentation using browser's native indent/outdent commands
   * @param {number} delta - Pixels to adjust (positive = indent, negative = outdent)
   */
  JournalEditorToolbar.prototype.adjustIndent = function(delta) {
    this.editor.focus();

    // Use browser's native indent/outdent command
    var command = delta > 0 ? 'indent' : 'outdent';
    document.execCommand(command, false, null);

    // Trigger content change for autosave
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
    this.$editor.find('.' + Tt.JOURNAL_FULL_WIDTH_GROUP_CLASS).each(function() {
      var $group = $(this);
      $group.children(Tt.JOURNAL_IMAGE_WRAPPER_FULL_SELECTOR).unwrap();
    });

    // Group consecutive full-width images
    var groups = [];
    var currentGroup = [];

    this.$editor.children().each(function() {
      var $child = $(this);
      if ($child.is(Tt.JOURNAL_IMAGE_WRAPPER_FULL_SELECTOR)) {
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
      $(group).wrapAll('<div class="content-block ' + Tt.JOURNAL_FULL_WIDTH_GROUP_CLASS + '"></div>');
    });
  };

  /**
   * Mark text blocks that contain float-right images
   * This allows CSS to clear floats appropriately
   * Updated to handle both p.text-block and div.text-block per spec
   */
  EditorLayoutManager.prototype.markFloatParagraphs = function() {
    // Remove existing marks from all text blocks
    this.$editor.find('.text-block').removeClass(Tt.JOURNAL_FLOAT_MARKER_CLASS);

    // Mark text blocks (both <p> and <div>) with float-right images
    this.$editor.find('.text-block').each(function() {
      var $textBlock = $(this);
      if ($textBlock.find(Tt.JOURNAL_IMAGE_WRAPPER_FLOAT_SELECTOR).length > 0) {
        $textBlock.addClass(Tt.JOURNAL_FLOAT_MARKER_CLASS);
      }
    });
  };

  /**
   * Ensure all image wrappers have delete buttons
   * Called on page load to add buttons to wrappers from saved content
   */
  EditorLayoutManager.prototype.ensureDeleteButtons = function() {
    this.$editor.find(Tt.JOURNAL_IMAGE_WRAPPER_SELECTOR).each(function() {
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

  /**
   * AutoSaveManager
   *
   * Manages automatic saving of journal content with debouncing and retry logic.
   *
   * This manager handles:
   * - Change detection (content, title, date, timezone, reference image)
   * - Debounced auto-save with 2-second delay
   * - Save execution with retry logic
   * - Status display updates
   */
  function AutoSaveManager(editor, autosaveUrl, csrfToken) {
    this.editor = editor;
    this.autosaveUrl = autosaveUrl;
    this.csrfToken = csrfToken;

    // Save state
    this.saveTimeout = null;
    this.maxTimeout = null;
    this.isSaving = false;
    this.retryCount = 0;
    this.hasUnsavedChanges = false;

    // Tracked values for change detection
    this.lastSavedHTML = '';
    this.lastSavedTitle = '';
    this.lastSavedDate = '';
    this.lastSavedTimezone = '';
    this.lastSavedReferenceImage = '';
  }

  /**
   * Initialize with current content as "saved" baseline
   */
  AutoSaveManager.prototype.initializeBaseline = function() {
    this.lastSavedHTML = this.editor.getCleanHTML();
    this.lastSavedTitle = this.editor.$titleInput.val() || '';
    this.lastSavedDate = this.editor.$dateInput.val() || '';
    this.lastSavedTimezone = this.editor.$timezoneInput.val() || '';
    this.lastSavedReferenceImage = this.editor.getReferenceImageUuid();
    this.hasUnsavedChanges = false;
  };

  /**
   * Check if content has changed since last save
   * Returns true if any field differs from last saved state
   */
  AutoSaveManager.prototype.detectChanges = function() {
    var htmlChanged = (this.editor.getCleanHTML() !== this.lastSavedHTML);
    var titleChanged = (this.editor.$titleInput.val() || '') !== this.lastSavedTitle;
    var dateChanged = (this.editor.$dateInput.val() || '') !== this.lastSavedDate;
    var timezoneChanged = (this.editor.$timezoneInput.val() || '') !== this.lastSavedTimezone;
    var referenceImageChanged = this.editor.getReferenceImageUuid() !== this.lastSavedReferenceImage;

    return htmlChanged || titleChanged || dateChanged || timezoneChanged || referenceImageChanged;
  };

  /**
   * Schedule a save with debouncing (2 second delay, 30 second max)
   * Call this method whenever content changes
   */
  AutoSaveManager.prototype.scheduleSave = function() {
    // Update change detection
    this.hasUnsavedChanges = this.detectChanges();

    if (this.hasUnsavedChanges) {
      this.editor.updateStatus('unsaved');
    }

    // Clear existing timeout
    if (this.saveTimeout) {
      clearTimeout(this.saveTimeout);
    }

    // Set maximum timeout on first change (30 seconds)
    if (!this.maxTimeout) {
      this.maxTimeout = setTimeout(function() {
        this.executeSave();
        this.maxTimeout = null;
      }.bind(this), 30000);
    }

    // Set new timeout (2 seconds)
    this.saveTimeout = setTimeout(function() {
      this.executeSave();
      // Clear max timeout since we saved via regular timeout
      if (this.maxTimeout) {
        clearTimeout(this.maxTimeout);
        this.maxTimeout = null;
      }
    }.bind(this), 2000);
  };

  /**
   * Save immediately without debouncing
   * Called when user clicks manual "Save" button
   * Clears any pending timeouts and executes save right away
   */
  AutoSaveManager.prototype.saveNow = function() {
    // Clear any pending save timers
    if (this.saveTimeout) {
      clearTimeout(this.saveTimeout);
      this.saveTimeout = null;
    }
    if (this.maxTimeout) {
      clearTimeout(this.maxTimeout);
      this.maxTimeout = null;
    }

    // Execute save immediately
    // executeSave() has guards to prevent duplicate saves
    this.executeSave();
  };

  /**
   * Execute save to server
   */
  AutoSaveManager.prototype.executeSave = function() {
    if (this.isSaving || !this.hasUnsavedChanges) {
      return;
    }

    // Run normalization on live editor before save (so user sees normalized result)
    this.editor.runNormalizationAtIdle();

    this.isSaving = true;
    this.editor.updateStatus('saving');

    // Capture snapshot of what we're saving (prevents race conditions)
    var snapshot = {
      html: this.editor.getCleanHTML(),
      title: this.editor.$titleInput.val() || '',
      date: this.editor.$dateInput.val() || '',
      timezone: this.editor.$timezoneInput.val() || '',
      referenceImageUuid: this.editor.getReferenceImageUuid()
    };

    var data = {
      text: snapshot.html,
      version: this.editor.currentVersion,
      new_title: snapshot.title,
      new_date: snapshot.date,
      new_timezone: snapshot.timezone,
      reference_image_uuid: snapshot.referenceImageUuid || ''
    };

    $.ajax({
      url: this.autosaveUrl,
      type: 'POST',
      contentType: 'application/json',
      data: JSON.stringify(data),
      headers: {
        'X-CSRFToken': this.csrfToken
      },
      success: function(response) {
        if (response.status === 'success') {
          // Update "last saved" to match what we just successfully saved
          this.lastSavedHTML = snapshot.html;
          this.lastSavedTitle = snapshot.title;
          this.lastSavedDate = snapshot.date;
          this.lastSavedTimezone = snapshot.timezone;
          this.lastSavedReferenceImage = snapshot.referenceImageUuid;

          // Recheck if changes occurred during save
          this.hasUnsavedChanges = this.detectChanges();

          this.editor.currentVersion = response.version;
          this.editor.$editor.data('current-version', response.version);
          this.retryCount = 0;

          if (this.maxTimeout) {
            clearTimeout(this.maxTimeout);
            this.maxTimeout = null;
          }

          if (this.hasUnsavedChanges) {
            this.editor.updateStatus('unsaved');
          } else {
            this.editor.updateStatus('saved', response.modified_datetime);
          }
        } else {
          this.editor.updateStatus('error', response.message);
        }
      }.bind(this),
      error: function(xhr, status, error) {
        if (xhr.status === 409) {
          this.editor.handleVersionConflict(xhr.responseJSON);
        } else {
          console.error('Auto-save error:', error);
          var errorMessage = 'Network error';

          if (xhr.responseJSON && xhr.responseJSON.message) {
            errorMessage = xhr.responseJSON.message;
          }

          // Retry logic for server errors
          var shouldRetry = (xhr.status >= 500 || xhr.status === 0) && this.retryCount < 3;

          if (shouldRetry) {
            this.retryCount++;
            var delay = Math.pow(2, this.retryCount) * 1000;
            this.editor.updateStatus('error', 'Save failed - retrying (' + this.retryCount + '/3)...');

            setTimeout(function() {
              this.executeSave();
            }.bind(this), delay);
          } else {
            this.editor.updateStatus('error', errorMessage);
          }
        }
      }.bind(this),
      complete: function() {
        this.isSaving = false;
      }.bind(this)
    });
  };

  /**
   * JournalImagePicker
   *
   * Manages image selection in the journal image picker panel.
   *
   * Features:
   * - Single-click selection toggle
   * - Ctrl/Cmd+click for multi-select
   * - Shift+click for range selection
   * - Double-click to open Image Inspector modal
   * - Selection count badge display
   * - Client-side filtering by usage (unused/used/all)
   */
  function JournalImagePicker($panel, editor) {
    this.$panel = $panel;
    this.editor = editor; // Reference to JournalEditor for usedImageUUIDs
    this.selectedImages = new Set();
    this.lastSelectedIndex = null;
    this.filterScope = 'unused'; // Default filter: 'unused' | 'used' | 'all'

    // Initialize badge manager
    var $headerTitle = this.$panel.find('.journal-image-panel-header h5');
    this.badgeManager = new SelectionBadgeManager($headerTitle, 'selected-images-count');

    // Register with coordinator
    imageSelectionCoordinator.registerPicker(this.clearAllSelections.bind(this));

    this.init();
  }

  /**
   * Initialize image picker event handlers
   */
  JournalImagePicker.prototype.init = function() {
    var self = this;

    // Click handler for image selection
    $(document).on('click', Tt.JOURNAL_IMAGE_CARD_SELECTOR, function(e) {
      e.preventDefault();
      self.handleImageClick(this, e);
    });

    // Double-click handler for opening inspector modal
    $(document).on('dblclick', Tt.JOURNAL_IMAGE_CARD_SELECTOR, function(e) {
      e.preventDefault();
      self.handleImageDoubleClick(this);
    });

    // Radio button change handler for filtering
    this.$panel.find('input[name="scope"]').on('change', function(e) {
      var newScope = $(this).val();
      self.applyFilter(newScope);
    });

    // NOTE: Initial filter is applied by JournalEditor.init() after usedImageUUIDs is populated
  };

  /**
   * Handle image card click with modifier key support
   */
  JournalImagePicker.prototype.handleImageClick = function(card, event) {
    var $card = $(card);
    var uuid = $card.data(Tt.JOURNAL_IMAGE_UUID_ATTR);
    var modifiers = getSelectionModifiers(event);

    if (modifiers.isShift && this.lastSelectedIndex !== null) {
      this.handleRangeSelection($card);
    } else if (modifiers.isCtrlOrCmd) {
      this.toggleSelection($card, uuid);
    } else {
      this.clearAllSelections();
      this.toggleSelection($card, uuid);
    }

    this.updateSelectionUI();
  };

  /**
   * Handle Shift+click range selection
   */
  JournalImagePicker.prototype.handleRangeSelection = function($clickedCard) {
    var $allCards = $(Tt.JOURNAL_IMAGE_CARD_SELECTOR);
    var clickedIndex = $allCards.index($clickedCard);
    var startIndex = Math.min(this.lastSelectedIndex, clickedIndex);
    var endIndex = Math.max(this.lastSelectedIndex, clickedIndex);

    for (var i = startIndex; i <= endIndex; i++) {
      var $card = $allCards.eq(i);
      var uuid = $card.data(Tt.JOURNAL_IMAGE_UUID_ATTR);
      this.selectedImages.add(uuid);
      $card.addClass(EDITOR_TRANSIENT.CSS_SELECTED);
    }
  };

  /**
   * Toggle selection state for a single image
   */
  JournalImagePicker.prototype.toggleSelection = function($card, uuid) {
    if (this.selectedImages.has(uuid)) {
      this.selectedImages.delete(uuid);
      $card.removeClass(EDITOR_TRANSIENT.CSS_SELECTED);
    } else {
      this.selectedImages.add(uuid);
      $card.addClass(EDITOR_TRANSIENT.CSS_SELECTED);
    }

    var $allCards = $(Tt.JOURNAL_IMAGE_CARD_SELECTOR);
    this.lastSelectedIndex = $allCards.index($card);
  };

  /**
   * Clear all selections
   */
  JournalImagePicker.prototype.clearAllSelections = function() {
    this.selectedImages.clear();
    $(Tt.JOURNAL_IMAGE_CARD_SELECTOR).removeClass(EDITOR_TRANSIENT.CSS_SELECTED);
    this.lastSelectedIndex = null;
  };

  /**
   * Update selection count badge UI
   */
  JournalImagePicker.prototype.updateSelectionUI = function() {
    var count = this.selectedImages.size;
    this.badgeManager.update(count);

    // Notify coordinator when selections change
    imageSelectionCoordinator.notifyPickerSelection(count > 0);
  };

  /**
   * Handle double-click to open Image Inspector modal
   */
  JournalImagePicker.prototype.handleImageDoubleClick = function(card) {
    var $card = $(card);
    var inspectUrl = $card.data('inspect-url');

    if (inspectUrl && typeof AN !== 'undefined' && AN.get) {
      AN.get(inspectUrl);
    }
  };

  /**
   * Apply filter to image cards based on usage scope
   * @param {string} scope - 'unused' | 'used' | 'all'
   */
  JournalImagePicker.prototype.applyFilter = function(scope) {
    this.filterScope = scope;
    var usedImageUUIDs = this.editor.usedImageUUIDs;

    $(Tt.JOURNAL_IMAGE_CARD_SELECTOR).each(function() {
      var $card = $(this);
      var uuid = $card.data(Tt.JOURNAL_IMAGE_UUID_ATTR);
      // Check if count > 0 to handle same image appearing multiple times
      var isUsed = (usedImageUUIDs.get(uuid) || 0) > 0;

      if (scope === 'all') {
        $card.show();
      } else if (scope === 'unused') {
        $card.toggle(!isUsed);
      } else if (scope === 'used') {
        $card.toggle(isUsed);
      }
    });
  };

  /**
   * JournalEditor - Main editor class
   */
  function JournalEditor($editor) {
    this.$editor = $editor;
    this.$form = $editor.closest(Tt.JOURNAL_ENTRY_FORM_SELECTOR);
    this.$titleInput = this.$form.find('#' + Tt.JOURNAL_TITLE_INPUT_ID);
    this.$dateInput = this.$form.find('#' + Tt.JOURNAL_DATE_INPUT_ID);
    this.$timezoneInput = this.$form.find('#' + Tt.JOURNAL_TIMEZONE_INPUT_ID);
    this.$statusElement = this.$form.find('.' + Tt.JOURNAL_SAVE_STATUS_CLASS);
    this.$manualSaveBtn = this.$form.find('.journal-manual-save-btn');

    this.entryPk = $editor.data(Tt.JOURNAL_ENTRY_PK_ATTR);
    this.currentVersion = $editor.data(Tt.JOURNAL_CURRENT_VERSION_ATTR) || 1;

    this.draggedElement = null;
    this.dragSource = null; // 'picker' or 'editor'

    // Editor image selection state
    this.selectedEditorImages = new Set();
    this.lastSelectedEditorIndex = null;

    // Track usage counts of images in editor (Map<uuid, count>)
    // Used for picker filtering (unused/used/all scopes)
    // Map allows tracking same image appearing multiple times
    this.usedImageUUIDs = new Map();

    // Reference image state
    this.currentReferenceImageUuid = null;
    this.$referenceContainer = $('.journal-reference-image-container');

    // Initialize badge manager for editor selections
    this.editorBadgeManager = new SelectionBadgeManager(this.$statusElement, 'selected-editor-images-count');

    // Register with coordinator
    imageSelectionCoordinator.registerEditor(this.clearEditorImageSelections.bind(this));

    // Initialize managers
    this.editorLayoutManager = new EditorLayoutManager(this.$editor);

    var autosaveUrl = $editor.data(Tt.JOURNAL_AUTOSAVE_URL_ATTR);
    var csrfToken = this.getCSRFToken();
    this.autoSaveManager = new AutoSaveManager(this, autosaveUrl, csrfToken);

    // Initialize image picker (if panel exists)
    // IMPORTANT: Must initialize AFTER usedImageUUIDs is created
    var $imagePanel = $('.journal-image-panel');
    if ($imagePanel.length > 0) {
      this.imagePicker = new JournalImagePicker($imagePanel, this);
    }

    this.init();
  }

  /**
   * Initialize the editor
   */
  JournalEditor.prototype.init = function() {
    if (!this.$editor.length) {
      return;
    }

    // Initialize used image tracking from existing content
    this.initializeUsedImages();

    // Initialize reference image state from server data
    this.initializeReferenceImage();

    // Apply initial filter to image picker now that usedImageUUIDs is populated
    if (this.imagePicker) {
      this.imagePicker.applyFilter(this.imagePicker.filterScope);
    }

    // Initialize autosave baseline with current content
    this.autoSaveManager.initializeBaseline();
    this.updateStatus('saved');

    // Initialize ContentEditable
    this.initContentEditable();

    // Initialize toolbar
    this.initializeToolbar();

    // Setup autosave handlers
    this.setupAutosave();

    // Setup manual save button
    this.setupManualSaveButton();

    // Setup drag-and-drop for image insertion
    this.setupImageDragDrop();

    // Setup image click to inspect
    this.setupImageClickToInspect();

    // Setup image selection
    this.setupImageSelection();

    // Setup image reordering
    this.setupImageReordering();

    // Setup image removal
    this.setupImageRemoval();

    // Setup reference image functionality
    this.setupReferenceImage();

    // Setup keyboard navigation
    this.setupKeyboardNavigation();
  };

  /**
   * Initialize used image tracking from existing editor content
   * Parses all images in the editor and populates usedImageUUIDs Map with counts
   * Handles same image appearing multiple times by incrementing count
   */
  JournalEditor.prototype.initializeUsedImages = function() {
    var self = this;
    this.usedImageUUIDs.clear();

    this.$editor.find(Tt.JOURNAL_IMAGE_SELECTOR).each(function() {
      var $img = $(this);
      var uuid = $img.data(Tt.JOURNAL_UUID_ATTR);
      if (uuid) {
        var currentCount = self.usedImageUUIDs.get(uuid) || 0;
        self.usedImageUUIDs.set(uuid, currentCount + 1);
      }
    });
  };

  /**
   * Initialize reference image state from server data
   * Reads data-reference-image-uuid from container
   */
  JournalEditor.prototype.initializeReferenceImage = function() {
    if (this.$referenceContainer.length) {
      var refImageUuid = this.$referenceContainer.data('reference-image-uuid');
      if (refImageUuid) {
        this.currentReferenceImageUuid = refImageUuid;
      }
    }
  };

  /**
   * Initialize ContentEditable functionality
   */
  JournalEditor.prototype.initContentEditable = function() {
    var self = this;

    // Refresh layout on page load (delete buttons, groups, float markers)
    this.editorLayoutManager.refreshLayout();

    // Only add paragraph structure if editor is genuinely empty
    var hasTextContent = $.trim(this.$editor.text()).length > 0;
    var hasImages = this.$editor.find('img').length > 0;
    var hasContent = hasTextContent || hasImages;

    if (!hasContent && !this.$editor.children().length) {
      this.$editor.html('<p><br></p>');
    }

    // Handle paste - strip formatting and convert newlines to paragraphs
    this.$editor.on('paste', function(e) {
      e.preventDefault();
      var text = (e.originalEvent.clipboardData || window.clipboardData).getData('text/plain');

      // If empty, do nothing
      if (!text || text.trim().length === 0) {
        return;
      }

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
        var $p = $('<p class="text-block"></p>').text(nonEmptyLines[i]);
        $paragraphs.push($p[0]);
      }

      // Insert paragraphs at cursor position
      // We need to handle different insertion scenarios:
      // 1. Cursor in empty paragraph -> replace it
      // 2. Cursor at start of paragraph -> insert before
      // 3. Cursor at end of paragraph -> insert after
      // 4. Cursor in middle of paragraph -> split it

      var $currentBlock = $(range.startContainer).closest('.text-block, h1, h2, h3, h4, h5, h6');

      if ($currentBlock.length === 0) {
        // Not in a block, find insertion point
        var $editor = $(self.$editor);
        var insertionPoint = range.startContainer;

        // If we're in the editor itself, append paragraphs
        if (insertionPoint === self.$editor[0]) {
          for (var i = 0; i < $paragraphs.length; i++) {
            $editor.append($paragraphs[i]);
          }
        } else {
          // Insert before closest block element
          var $closestBlock = $(insertionPoint).closest('.text-block, h1, h2, h3, h4, h5, h6');
          if ($closestBlock.length) {
            $closestBlock.before($paragraphs);
          } else {
            $editor.append($paragraphs);
          }
        }
      } else {
        // We're in a block element
        var blockEl = $currentBlock[0];
        var textContent = $currentBlock.text().trim();

        // Check if block is empty (or only has <br>)
        if (textContent.length === 0) {
          // Replace empty block with pasted paragraphs
          $currentBlock.before($paragraphs);
          $currentBlock.remove();
        } else {
          // Block has content - we need to split it
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
            var $afterP = $('<p class="text-block"></p>').text(afterText);
            $($paragraphs[$paragraphs.length - 1]).after($afterP);
          }
        }
      }

      // Place cursor at end of last inserted paragraph
      if ($paragraphs.length > 0) {
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
      }

      // Trigger autosave (normalization will run at idle time)
      self.handleContentChange();
    });

    // Prevent dropping files directly into editor (would show file:// URLs)
    this.$editor.on('drop', function(e) {
      if (e.originalEvent.dataTransfer.files.length > 0) {
        e.preventDefault();
        return false;
      }
    });

    // Handle Enter and Backspace keys for block escape and paragraph structure
    this.$editor.on('keydown', function(e) {
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
  };

  /**
   * Initialize formatting toolbar
   */
  JournalEditor.prototype.initializeToolbar = function() {
    var $toolbar = $('.journal-editor-toolbar');
    if ($toolbar.length) {
      var self = this;
      this.toolbar = new JournalEditorToolbar(
        $toolbar,
        this.$editor,
        function() {
          self.handleContentChange();
        }
      );
    }
  };

  /**
   * Setup autosave handlers
   */
  JournalEditor.prototype.setupAutosave = function() {
    var self = this;

    // Track content changes
    this.$editor.on('input', function() {
      self.handleContentChange();
    });

    // Note: Paste normalization is not needed here because initContentEditable()
    // already handles paste events by preventing default and inserting plain text only.
    // The plain text insertion via execCommand('insertText') creates properly
    // structured content that doesn't require additional normalization.

    // Track metadata changes
    this.$titleInput.on('input', function() {
      self.handleContentChange();
    });

    this.$dateInput.on('change', function() {
      self.handleContentChange();
    });

    this.$timezoneInput.on('change', function() {
      self.handleContentChange();
    });
  };

  /**
   * Setup manual save button click handler
   */
  JournalEditor.prototype.setupManualSaveButton = function() {
    var self = this;

    if (this.$manualSaveBtn.length) {
      this.$manualSaveBtn.on('click', function() {
        self.autoSaveManager.saveNow();
      });
    }
  };

  /**
   * Refresh image layout (wrapping and float markers)
   * Only called when images are added, removed, or moved
   */
  JournalEditor.prototype.refreshImageLayout = function() {
    this.editorLayoutManager.wrapFullWidthImageGroups();
    this.editorLayoutManager.markFloatParagraphs();
  };

  /**
   * Handle content change (fired on every keystroke)
   * Note: Does NOT run normalization - that happens at idle time (see runNormalizationAtIdle)
   * Note: Does NOT refresh layout - only schedules autosave
   */
  JournalEditor.prototype.handleContentChange = function() {
    // Schedule autosave (handles change detection and debouncing)
    this.autoSaveManager.scheduleSave();
  };

  /**
   * Run normalization at idle time (after user stops typing for 2 seconds)
   * Called by autosave idle timer before actual save
   */
  JournalEditor.prototype.runNormalizationAtIdle = function() {
    // Save cursor position before normalization
    var cursor = CursorPreservation.save(this.$editor);

    // Run full HTML normalization
    runFullNormalization(this.$editor[0]);

    // Restore cursor position after normalization
    CursorPreservation.restore(this.$editor, cursor);

    // Refresh layout to update markers and groups
    this.editorLayoutManager.wrapFullWidthImageGroups();
    this.editorLayoutManager.markFloatParagraphs();
  };

  /**
   * Check if cursor is at the absolute end of an element
   * @param {Range} range - Current selection range
   * @param {HTMLElement} element - Element to check
   * @returns {boolean} True if cursor is at end
   */
  JournalEditor.prototype.isCursorAtEnd = function(range, element) {
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
  JournalEditor.prototype.isCursorAtStart = function(range, element) {
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
  JournalEditor.prototype.setCursorAtStart = function(element) {
    var range = document.createRange();
    var selection = window.getSelection();

    range.selectNodeContents(element);
    range.collapse(true); // Collapse to start

    selection.removeAllRanges();
    selection.addRange(range);
  };

  /**
   * Handle Enter key in block elements (blockquote, lists, code)
   * Single Enter at start/end of block escapes to new paragraph
   * Enter in middle extends block (native behavior)
   *
   * @param {Event} e - Keydown event
   */
  JournalEditor.prototype.handleEnterInBlock = function(e) {
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

          var $textBlockContainer = $list.closest('.text-block');
          var $newParagraph = $('<p class="text-block"><br></p>');
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

          var $textBlockContainer = $list.closest('.text-block');
          var $newParagraph = $('<p class="text-block"><br></p>');
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

          var $textBlockContainer = $blockParent.closest('.text-block');
          var $newParagraph = $('<p class="text-block"><br></p>');
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

          var $textBlockContainer = $blockParent.closest('.text-block');
          var $newParagraph = $('<p class="text-block"><br></p>');
          $textBlockContainer.before($newParagraph);

          // Move cursor to new paragraph
          this.setCursorAtStart($newParagraph[0]);

          return;
        }
      }
    }

    // Let native Enter work (extends block)
  };

  /**
   * Handle Backspace key in block elements
   * Backspace at start of empty paragraph in block escapes to regular paragraph
   *
   * @param {Event} e - Keydown event
   */
  JournalEditor.prototype.handleBackspaceInBlock = function(e) {
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

          var $textBlockContainer = $list.closest('.text-block');

          // If list has only one item, remove entire text-block and create paragraph
          if ($allItems.length === 1) {
            var $newParagraph = $('<p class="text-block"><br></p>');
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

          var $textBlockContainer = $blockParent.closest('.text-block');

          // If blockquote has only one paragraph, remove entire text-block and create paragraph
          if ($paragraphs.length === 1) {
            var $newParagraph = $('<p class="text-block"><br></p>');
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


  /**
   * Get clean HTML for saving
   *
   * Removes ALL transient (editor-only) elements and classes.
   * Only persistent HTML elements/attributes are kept.
   *
   * PERSISTENT (saved to database):
   * - <span class="trip-image-wrapper" data-layout="...">
   * - <img class="trip-image" data-uuid="..." src="...">
   * - <div class="full-width-image-group">
   * - <p class="has-float-image">
   *
   * TRANSIENT (removed before save):
   * - <button class="trip-image-delete-btn">
   * - .drop-zone-active, .drop-zone-between
   * - .dragging, .drag-over
   * - .selected
   */
  JournalEditor.prototype.getCleanHTML = function() {
    // Clone the editor content to avoid modifying the displayed version
    var $clone = this.$editor.clone();

    // Run full normalization before saving
    runFullNormalization($clone[0]);

    // Remove transient elements (never saved to database)
    $clone.find(EDITOR_TRANSIENT.SEL_DELETE_BTN).remove();
    $clone.find('.' + EDITOR_TRANSIENT.CSS_DROP_ZONE_BETWEEN).remove();

    // Remove transient classes (editor-only states)
    $clone.find('.' + EDITOR_TRANSIENT.CSS_DROP_ZONE_ACTIVE)
          .removeClass(EDITOR_TRANSIENT.CSS_DROP_ZONE_ACTIVE);
    $clone.find('.' + EDITOR_TRANSIENT.CSS_DRAGGING)
          .removeClass(EDITOR_TRANSIENT.CSS_DRAGGING);
    $clone.removeClass(EDITOR_TRANSIENT.CSS_DRAG_OVER);

    // Remove selected state (editor UI only)
    $clone.find('.' + EDITOR_TRANSIENT.CSS_SELECTED).removeClass(EDITOR_TRANSIENT.CSS_SELECTED);

    return $clone.html();
  };

  /**
   * Get current reference image UUID
   * Returns current reference image UUID for autosave
   */
  JournalEditor.prototype.getReferenceImageUuid = function() {
    return this.currentReferenceImageUuid;
  };

  /**
   * Handle version conflict
   */
  JournalEditor.prototype.handleVersionConflict = function(data) {
    console.warn('Version conflict detected');
    this.updateStatus('error', 'Conflict detected - please review changes');

    // Display the conflict modal if provided
    if (data && data.modal) {
      AN.processModalAction(data.modal);
    }
  };

  /**
   * Update save status display
   */
  JournalEditor.prototype.updateStatus = function(status, message) {
    var statusText = '';
    var statusClass = 'badge-secondary';

    switch (status) {
      case 'saved':
        statusText = 'Saved';
        statusClass = 'badge-success';
        if (message) {
          var savedDate = new Date(message);
          var now = new Date();
          var diffSeconds = Math.floor((now - savedDate) / 1000);

          if (diffSeconds < 60) {
            statusText = 'Saved ' + diffSeconds + ' seconds ago';
          } else {
            var diffMinutes = Math.floor(diffSeconds / 60);
            statusText = 'Saved ' + diffMinutes + ' minutes ago';
          }
        }
        break;
      case 'unsaved':
        statusText = 'Unsaved changes';
        statusClass = 'badge-warning';
        break;
      case 'saving':
        statusText = 'Saving...';
        statusClass = 'badge-info';
        break;
      case 'error':
        statusText = message || 'Error saving';
        statusClass = 'badge-danger';
        break;
    }

    this.$statusElement
      .removeClass('badge-secondary badge-success badge-warning badge-info badge-danger')
      .addClass(statusClass)
      .text(statusText);

    // Show manual save button only when there are unsaved changes
    if (this.$manualSaveBtn.length) {
      this.$manualSaveBtn.toggle(status === 'unsaved');
    }
  };

  /**
   * Setup drag-and-drop for image insertion from picker
   */
  JournalEditor.prototype.setupImageDragDrop = function() {
    var self = this;

    // Make picker images draggable (already set in HTML)
    // Handle dragstart from picker
    $(document).on('dragstart', Tt.JOURNAL_IMAGE_CARD_SELECTOR, function(e) {
      self.draggedElement = this;
      self.dragSource = 'picker';

      // Update visual feedback (handles multi-image .dragging and count badge)
      self.updateDraggingVisuals(true);

      // Set drag data
      e.originalEvent.dataTransfer.effectAllowed = 'copy';
      e.originalEvent.dataTransfer.setData('text/plain', ''); // Required for Firefox
    });

    // Handle dragend from picker
    $(document).on('dragend', Tt.JOURNAL_IMAGE_CARD_SELECTOR, function(e) {
      // Visual cleanup only - state cleanup happens in drop handlers
      self.updateDraggingVisuals(false);
      self.clearDropZones();
    });

    // Editor drag events
    this.$editor.on('dragover', function(e) {
      e.preventDefault();

      // Set appropriate drop effect based on drag source
      if (self.dragSource === 'editor') {
        e.originalEvent.dataTransfer.dropEffect = 'move';
      } else {
        e.originalEvent.dataTransfer.dropEffect = 'copy';
      }

      // Show drop zones for both picker and editor drags
      if (self.dragSource === 'picker' || self.dragSource === 'editor') {
        self.showDropZones(e);
      }
    });

    this.$editor.on('dragenter', function(e) {
      if (self.dragSource === 'picker' || self.dragSource === 'editor') {
        $(this).addClass(EDITOR_TRANSIENT.CSS_DRAG_OVER);
      }
    });

    this.$editor.on('dragleave', function(e) {
      // Only remove if we're leaving the editor completely
      if (!$(e.relatedTarget).closest('.' + Tt.JOURNAL_EDITOR_CLASS).length) {
        $(this).removeClass(EDITOR_TRANSIENT.CSS_DRAG_OVER);
        self.clearDropZones();
      }
    });

    this.$editor.on('drop', function(e) {
      // Check if drop is actually on reference container - if so, let it handle the drop
      var $target = $(e.target);
      if ($target.closest('.journal-reference-image-container').length) {
        return; // Don't preventDefault, don't stopPropagation - let reference handler get it
      }

      e.preventDefault();
      e.stopPropagation();

      $(this).removeClass(EDITOR_TRANSIENT.CSS_DRAG_OVER);

      if (self.dragSource === 'picker' && self.draggedElement) {
        self.handleImageDrop(e);
      } else if (self.dragSource === 'editor' && self.draggedElement) {
        self.handleImageReorder(e);
      }

      self.clearDropZones();

      // Clean up drag state after processing
      self.draggedElement = null;
      self.dragSource = null;
    });

    // Handle Escape key to cancel drag operation
    $(document).on('keydown', function(e) {
      if (e.key === 'Escape' && (self.draggedElement || self.dragSource)) {
        self.updateDraggingVisuals(false);
        self.clearDropZones();
        self.draggedElement = null;
        self.dragSource = null;
      }
    });

    // Make picker panel a drop target for editor and reference images (drag-to-remove)
    var $pickerGallery = $('.journal-image-gallery');
    if ($pickerGallery.length) {
      $pickerGallery.on('dragover', function(e) {
        // Allow drops from editor or reference (removal), not from picker (no-op)
        if (self.dragSource === 'editor' || self.dragSource === 'reference') {
          e.preventDefault();
          e.originalEvent.dataTransfer.dropEffect = 'move';
          $(this).addClass('drop-target-active'); // Visual feedback
        }
      });

      $pickerGallery.on('dragleave', function(e) {
        // Only remove if we're leaving the gallery completely
        if (!$(e.relatedTarget).closest('.journal-image-gallery').length) {
          $(this).removeClass('drop-target-active');
        }
      });

      $pickerGallery.on('drop', function(e) {
        if (self.dragSource === 'editor' || self.dragSource === 'reference') {
          e.preventDefault();
          $(this).removeClass('drop-target-active');
          self.handleImageRemovalDrop(e);
        }
      });
    }
  };

  /**
   * Show drop zones based on mouse position
   */
  JournalEditor.prototype.showDropZones = function(e) {
    var $target = $(e.target);
    var $textBlock = $target.closest('.text-block');
    var $imageWrapper = $target.closest(Tt.JOURNAL_IMAGE_WRAPPER_FULL_SELECTOR);

    // Clear existing indicators
    this.clearDropZones();

    if ($textBlock.length && $textBlock.parent().is(this.$editor)) {
      // Mouse is over a text block (p or div) - show drop zone
      $textBlock.addClass(EDITOR_TRANSIENT.CSS_DROP_ZONE_ACTIVE);
    } else if ($imageWrapper.length && $imageWrapper.closest(this.$editor).length) {
      // Mouse is over a full-width image - highlight it to show insertion point
      // (wrapper may be inside .full-width-image-group, so check if it's within editor)
      $imageWrapper.addClass(EDITOR_TRANSIENT.CSS_DROP_ZONE_ACTIVE);
    } else {
      // Mouse is between blocks - show between indicator
      var mouseY = e.clientY;
      var $children = this.$editor.children('.text-block, div.content-block, h1, h2, h3, h4, h5, h6');

      $children.each(function() {
        var rect = this.getBoundingClientRect();
        var betweenTop = rect.top - 20;
        var betweenBottom = rect.top + 20;

        if (mouseY >= betweenTop && mouseY <= betweenBottom) {
          var $indicator = $('<div class="' + EDITOR_TRANSIENT.CSS_DROP_ZONE_BETWEEN + '"></div>');
          $(this).before($indicator);
          return false;
        }
      });
    }
  };

  /**
   * Clear drop zone indicators
   */
  JournalEditor.prototype.clearDropZones = function() {
    this.$editor.find('.text-block').removeClass(EDITOR_TRANSIENT.CSS_DROP_ZONE_ACTIVE);
    this.$editor.find(Tt.JOURNAL_IMAGE_WRAPPER_SELECTOR).removeClass(EDITOR_TRANSIENT.CSS_DROP_ZONE_ACTIVE);
    this.$editor.find('.' + EDITOR_TRANSIENT.CSS_DROP_ZONE_BETWEEN).remove();
  };

  /**
   * Handle image drop into editor (supports multi-image drop)
   */
  JournalEditor.prototype.handleImageDrop = function(e) {
    if (!this.draggedElement) {
      return;
    }

    // Get images to insert (1 or many)
    var imagesToInsert = this.getPickerImagesToInsert();
    if (imagesToInsert.length === 0) {
      return;
    }

    // Determine drop layout and target (same logic as before)
    var $target = $(e.target);
    var $textBlock = $target.closest('.text-block');
    var $imageWrapper = $target.closest(Tt.JOURNAL_IMAGE_WRAPPER_FULL_SELECTOR);

    var layout = LAYOUT_VALUES.FULL_WIDTH;
    var $insertTarget = null;

    if ($textBlock.length && $textBlock.parent().is(this.$editor)) {
      // Dropped into a text block (p or div) - float-right layout
      layout = LAYOUT_VALUES.FLOAT_RIGHT;
      $insertTarget = $textBlock;
    } else if ($imageWrapper.length && $imageWrapper.closest(this.$editor).length) {
      // Dropped onto an existing full-width image - insert after it (into same group)
      layout = LAYOUT_VALUES.FULL_WIDTH;
      $insertTarget = $imageWrapper;
    } else {
      // Dropped between blocks - full-width layout
      layout = LAYOUT_VALUES.FULL_WIDTH;

      // Find the closest block to insert before/after
      var mouseY = e.clientY;
      var $children = this.$editor.children('.text-block, div.content-block, h1, h2, h3, h4, h5, h6');
      var closestElement = null;
      var minDistance = Infinity;

      $children.each(function() {
        var rect = this.getBoundingClientRect();
        var distance = Math.abs(rect.top - mouseY);

        if (distance < minDistance) {
          minDistance = distance;
          closestElement = this;
        }
      });

      $insertTarget = $(closestElement);
    }

    // Insert each image using existing logic
    var $lastInserted = null;
    for (var i = 0; i < imagesToInsert.length; i++) {
      var imageData = imagesToInsert[i];

      // Create wrapped image element
      var $wrappedImage = this.createImageElement(
        imageData.uuid,
        imageData.url,
        imageData.caption,
        layout
      );

      // Insert the wrapped image
      if (!$lastInserted) {
        // First insertion - use original target logic
        if (layout === LAYOUT_VALUES.FLOAT_RIGHT) {
          // Insert at beginning of paragraph for float-right
          $insertTarget.prepend($wrappedImage);
        } else if ($insertTarget.is(Tt.JOURNAL_IMAGE_WRAPPER_FULL_SELECTOR)) {
          // Insert after the target image wrapper (will be in same group)
          $insertTarget.after($wrappedImage);
        } else {
          // Insert before the target element for full-width
          $insertTarget.before($wrappedImage);
        }
      } else {
        // Subsequent insertions - chain after last inserted
        if (layout === LAYOUT_VALUES.FLOAT_RIGHT) {
          // For float-right, prepend each one (so they appear in order)
          $insertTarget.prepend($wrappedImage);
        } else {
          // For full-width, insert after last
          $lastInserted.after($wrappedImage);
        }
      }

      $lastInserted = $wrappedImage;
    }

    // NOW enforce 2-image limit per paragraph (after all insertions)
    if (layout === LAYOUT_VALUES.FLOAT_RIGHT) {
      var existingWrappers = $insertTarget.find(Tt.JOURNAL_IMAGE_WRAPPER_FLOAT_SELECTOR);
      var evicted = false;
      while (existingWrappers.length > 2) {
        // Remove rightmost (last) wrapper - FIFO eviction
        // Use helper to ensure usage tracking is updated
        this._removeWrapperAndUpdateUsage(existingWrappers.last());
        existingWrappers = $insertTarget.find(Tt.JOURNAL_IMAGE_WRAPPER_FLOAT_SELECTOR);
        evicted = true;
      }

      // Update picker filter once if any images were evicted
      if (evicted && this.imagePicker) {
        this.imagePicker.applyFilter(this.imagePicker.filterScope);
      }
    }

    // Refresh layout (images changed) + trigger autosave
    this.refreshImageLayout();
    this.handleContentChange();

    // Clear picker selections if multiple images were inserted
    if (this.imagePicker && imagesToInsert.length > 1) {
      this.imagePicker.clearAllSelections();
    }
  };


  /**
   * Create image element with proper attributes
   */
  JournalEditor.prototype.createImageElement = function(uuid, url, caption, layout) {
    // Create the image element
    var $img = $('<img>', {
      'src': url,
      'alt': caption,
      'class': Tt.JOURNAL_IMAGE_CLASS,
    });
    $img.attr('data-' + Tt.JOURNAL_UUID_ATTR, uuid);
    $img.attr('draggable', true);

    // Create wrapper with layout attribute
    var $wrapper = $('<span>', {
      'class': Tt.JOURNAL_IMAGE_WRAPPER_CLASS
    });
    $wrapper.attr('data-' + Tt.JOURNAL_LAYOUT_ATTR, layout);

    // Create caption span if caption exists and is non-empty
    var $captionSpan = null;
    if (caption && $.trim(caption).length > 0) {
      $captionSpan = $('<span>', {
        'class': 'trip-image-caption',
        'text': caption
      });
    }

    // Create delete button (TRANSIENT)
    var $deleteBtn = $('<button>', {
      'class': EDITOR_TRANSIENT.CSS_DELETE_BTN,
      'type': 'button',
      'title': 'Remove image',
      'text': '×'
    });

    // Assemble: wrapper contains image, optional caption, and delete button
    $wrapper.append($img);
    if ($captionSpan) {
      $wrapper.append($captionSpan);
    }
    $wrapper.append($deleteBtn);

    // Track this image as used (for picker filtering)
    // Increment count to handle same image appearing multiple times
    var currentCount = this.usedImageUUIDs.get(uuid) || 0;
    this.usedImageUUIDs.set(uuid, currentCount + 1);

    // Update picker filter if it exists
    if (this.imagePicker) {
      this.imagePicker.applyFilter(this.imagePicker.filterScope);
    }

    return $wrapper;
  };

  /**
   * Setup image double-click to inspect
   * Single-click is reserved for future selection feature
   */
  JournalEditor.prototype.setupImageClickToInspect = function() {
    var self = this;

    // Double-click to open Image Inspector modal (consistent with picker behavior)
    this.$editor.on('dblclick', Tt.JOURNAL_IMAGE_SELECTOR, function(e) {
      e.preventDefault();
      e.stopPropagation();

      var $img = $(this);
      var uuid = $img.data('uuid');

      // Get inspect URL from the corresponding picker card
      var $pickerCard = $(Tt.JOURNAL_IMAGE_CARD_SELECTOR + '[data-' + Tt.JOURNAL_IMAGE_UUID_ATTR + '="' + uuid + '"]');
      var inspectUrl = $pickerCard.data('inspect-url');

      if (inspectUrl) {
        AN.get(inspectUrl);
      } else {
        console.warn('No inspect URL found for image:', uuid);
      }
    });

    // Single-click handler - now implemented for selection
    this.$editor.on('click', Tt.JOURNAL_IMAGE_SELECTOR, function(e) {
      e.preventDefault();
      e.stopPropagation();

      self.handleEditorImageClick(this, e);
    });

    // Prevent default drag on existing images (handled in setupImageReordering)
    this.$editor.on('dragstart', Tt.JOURNAL_IMAGE_SELECTOR, function(e) {
      // This is handled in setupImageReordering
    });
  };

  /**
   * Setup image selection in editor
   */
  JournalEditor.prototype.setupImageSelection = function() {
    // Event handlers are already set up in setupImageClickToInspect()
    // This method is a placeholder for any future initialization needs
  };

  /**
   * Get picker images to insert (for multi-image drag-and-drop)
   * Returns array of image data objects: [{uuid, url, caption}, ...]
   */
  JournalEditor.prototype.getPickerImagesToInsert = function() {
    if (!this.draggedElement || !this.imagePicker) {
      return [];
    }

    var self = this;
    var $draggedCard = $(this.draggedElement);
    var draggedUuid = $draggedCard.data(Tt.JOURNAL_IMAGE_UUID_ATTR);

    // Check if dragged card is part of selection
    var isDraggedSelected = this.imagePicker.selectedImages.has(draggedUuid);

    var imagesToInsert = [];

    if (isDraggedSelected && this.imagePicker.selectedImages.size > 1) {
      // Multi-image insert: get all selected cards in DOM order
      var selectedUuids = this.imagePicker.selectedImages;
      $(Tt.JOURNAL_IMAGE_CARD_SELECTOR).each(function() {
        var $card = $(this);
        var uuid = $card.data(Tt.JOURNAL_IMAGE_UUID_ATTR);
        if (selectedUuids.has(uuid)) {
          var imageData = self.getImageDataFromUUID(uuid);
          if (imageData) {
            imagesToInsert.push(imageData);
          }
        }
      });
    } else {
      // Single-image insert: just the dragged card
      var imageData = this.getImageDataFromUUID(draggedUuid);
      if (imageData) {
        imagesToInsert.push(imageData);
      }
    }

    return imagesToInsert;
  };

  /**
   * Get image data object from UUID by looking up picker card
   * @param {string} uuid - Image UUID
   * @returns {Object|null} {uuid, url, caption} or null if not found
   */
  JournalEditor.prototype.getImageDataFromUUID = function(uuid) {
    var $card = $(Tt.JOURNAL_IMAGE_CARD_SELECTOR + '[data-' + Tt.JOURNAL_IMAGE_UUID_ATTR + '="' + uuid + '"]');

    if (!$card.length) {
      return null;
    }

    return {
      uuid: uuid,
      url: $card.data('image-url'),
      caption: $card.data('caption') || 'Untitled'
    };
  };

  /**
   * Get image data for currently dragged image(s)
   * Returns single image data or null (for reference area use - multi-select not allowed)
   * @returns {Object|null} {uuid, url, caption} or null if multi-select or no drag
   */
  JournalEditor.prototype.getDraggedImageData = function() {
    if (!this.draggedElement || !this.dragSource) {
      return null;
    }

    if (this.dragSource === 'picker') {
      // Use existing helper that handles picker selection logic
      var imagesToInsert = this.getPickerImagesToInsert();
      return (imagesToInsert.length === 1) ? imagesToInsert[0] : null;
    } else if (this.dragSource === 'editor') {
      // Use existing helper that handles editor selection logic
      var wrappersToMove = this.getEditorWrappersToMove();
      if (wrappersToMove.length !== 1) {
        return null;
      }

      // Get UUID from the single wrapper
      var $wrapper = wrappersToMove[0];
      var $img = $wrapper.find(Tt.JOURNAL_IMAGE_SELECTOR);
      var uuid = $img.data(Tt.JOURNAL_UUID_ATTR);

      // Look up full image data from picker card
      return this.getImageDataFromUUID(uuid);
    }

    return null;
  };

  /**
   * Check if reference drop zone should highlight
   * (Only for single-image drags, not multi-select)
   * @returns {boolean}
   */
  JournalEditor.prototype.shouldShowReferenceDropZone = function() {
    return this.getDraggedImageData() !== null;
  };

  /**
   * Set visibility of reference drop zone highlighting
   * Uses CSS constant for consistency with editor drop zones
   * @param {boolean} visible - true to show drop zone, false to hide
   */
  JournalEditor.prototype.setReferenceDropZoneVisible = function(visible) {
    if (!this.$referenceContainer || !this.$referenceContainer.length) {
      return;
    }

    var $target = this.$referenceContainer.find('.journal-reference-image-placeholder, .journal-reference-image-preview');

    if (visible) {
      $target.addClass(EDITOR_TRANSIENT.CSS_DROP_ZONE_ACTIVE);
    } else {
      $target.removeClass(EDITOR_TRANSIENT.CSS_DROP_ZONE_ACTIVE);
    }
  };

  /**
   * Get editor wrappers to move (for multi-image drag-and-drop)
   * Returns array of jQuery wrapper objects: [$wrapper1, $wrapper2, ...]
   */
  JournalEditor.prototype.getEditorWrappersToMove = function() {
    if (!this.draggedElement) {
      return [];
    }

    var $draggedWrapper = $(this.draggedElement);
    var $draggedImg = $draggedWrapper.find(Tt.JOURNAL_IMAGE_SELECTOR);
    var draggedUuid = $draggedImg.data(Tt.JOURNAL_UUID_ATTR);

    // Check if dragged wrapper is part of selection
    var isDraggedSelected = this.selectedEditorImages.has(draggedUuid);

    var wrappersToMove = [];

    if (isDraggedSelected && this.selectedEditorImages.size > 1) {
      // Multi-image move: get all selected wrappers in DOM order
      var selectedUuids = this.selectedEditorImages;
      var self = this;
      this.$editor.find(Tt.JOURNAL_IMAGE_WRAPPER_SELECTOR).each(function() {
        var $wrapper = $(this);
        var $img = $wrapper.find(Tt.JOURNAL_IMAGE_SELECTOR);
        var uuid = $img.data(Tt.JOURNAL_UUID_ATTR);
        if (selectedUuids.has(uuid)) {
          wrappersToMove.push($wrapper);
        }
      });
    } else {
      // Single-image move: just the dragged wrapper
      wrappersToMove.push($draggedWrapper);
    }

    return wrappersToMove;
  };

  /**
   * Update dragging visuals (count badge and .dragging class)
   * @param {boolean} isDragging - true to show, false to hide
   */
  JournalEditor.prototype.updateDraggingVisuals = function(isDragging) {
    if (isDragging) {
      var count = 0;
      var $elementsToMark = [];

      if (this.dragSource === 'picker' && this.imagePicker) {
        var draggedUuid = $(this.draggedElement).data(Tt.JOURNAL_IMAGE_UUID_ATTR);
        var isDraggedSelected = this.imagePicker.selectedImages.has(draggedUuid);

        if (isDraggedSelected && this.imagePicker.selectedImages.size > 1) {
          // Mark all selected cards
          count = this.imagePicker.selectedImages.size;
          var selectedUuids = this.imagePicker.selectedImages;
          $(Tt.JOURNAL_IMAGE_CARD_SELECTOR).each(function() {
            var $card = $(this);
            if (selectedUuids.has($card.data(Tt.JOURNAL_IMAGE_UUID_ATTR))) {
              $elementsToMark.push($card);
            }
          });
        } else {
          // Just the dragged card
          count = 1;
          $elementsToMark.push($(this.draggedElement));
        }
      } else if (this.dragSource === 'editor') {
        var $draggedWrapper = $(this.draggedElement);
        var $draggedImg = $draggedWrapper.find(Tt.JOURNAL_IMAGE_SELECTOR);
        var draggedUuid = $draggedImg.data(Tt.JOURNAL_UUID_ATTR);
        var isDraggedSelected = this.selectedEditorImages.has(draggedUuid);

        if (isDraggedSelected && this.selectedEditorImages.size > 1) {
          // Mark all selected wrappers
          count = this.selectedEditorImages.size;
          var selectedUuids = this.selectedEditorImages;
          var self = this;
          this.$editor.find(Tt.JOURNAL_IMAGE_WRAPPER_SELECTOR).each(function() {
            var $wrapper = $(this);
            var $img = $wrapper.find(Tt.JOURNAL_IMAGE_SELECTOR);
            if (selectedUuids.has($img.data(Tt.JOURNAL_UUID_ATTR))) {
              $elementsToMark.push($wrapper);
            }
          });
        } else {
          // Just the dragged wrapper
          count = 1;
          $elementsToMark.push($draggedWrapper);
        }
      }

      // Apply .dragging class
      $elementsToMark.forEach(function($el) {
        $el.addClass(EDITOR_TRANSIENT.CSS_DRAGGING);
      });

      // Add count badge if multiple images
      if (count > 1 && this.draggedElement) {
        var $badge = $('<span>')
          .addClass('drag-count-badge')
          .text(count + ' images');
        $(this.draggedElement).append($badge);
      }
    } else {
      // Remove .dragging class from all elements
      $(Tt.JOURNAL_IMAGE_CARD_SELECTOR).removeClass(EDITOR_TRANSIENT.CSS_DRAGGING);
      this.$editor.find(Tt.JOURNAL_IMAGE_WRAPPER_SELECTOR).removeClass(EDITOR_TRANSIENT.CSS_DRAGGING);

      // Remove count badges
      $('.drag-count-badge').remove();
    }
  };

  /**
   * Handle editor image click with modifier key support
   */
  JournalEditor.prototype.handleEditorImageClick = function(img, event) {
    var $img = $(img);
    var uuid = $img.data(Tt.JOURNAL_UUID_ATTR);
    var modifiers = getSelectionModifiers(event);

    // Clear text selection (contenteditable conflict prevention)
    this.clearTextSelection();

    if (modifiers.isShift && this.lastSelectedEditorIndex !== null) {
      this.handleEditorRangeSelection($img);
    } else if (modifiers.isCtrlOrCmd) {
      this.toggleEditorImageSelection($img, uuid);
    } else {
      this.clearEditorImageSelections();
      this.toggleEditorImageSelection($img, uuid);
    }

    this.updateEditorSelectionUI();
  };

  /**
   * Clear text selection in contenteditable
   */
  JournalEditor.prototype.clearTextSelection = function() {
    if (window.getSelection) {
      var selection = window.getSelection();
      if (selection.rangeCount > 0) {
        selection.removeAllRanges();
      }
    }
  };

  /**
   * Handle Shift+click range selection for editor images
   */
  JournalEditor.prototype.handleEditorRangeSelection = function($clickedImg) {
    var $allImages = this.$editor.find(Tt.JOURNAL_IMAGE_SELECTOR);
    var clickedIndex = $allImages.index($clickedImg);
    var startIndex = Math.min(this.lastSelectedEditorIndex, clickedIndex);
    var endIndex = Math.max(this.lastSelectedEditorIndex, clickedIndex);

    for (var i = startIndex; i <= endIndex; i++) {
      var $img = $allImages.eq(i);
      var uuid = $img.data(Tt.JOURNAL_UUID_ATTR);
      this.selectedEditorImages.add(uuid);
      $img.closest(Tt.JOURNAL_IMAGE_WRAPPER_SELECTOR).addClass(EDITOR_TRANSIENT.CSS_SELECTED);
    }
  };

  /**
   * Toggle selection state for a single editor image
   */
  JournalEditor.prototype.toggleEditorImageSelection = function($img, uuid) {
    var $wrapper = $img.closest(Tt.JOURNAL_IMAGE_WRAPPER_SELECTOR);

    if (this.selectedEditorImages.has(uuid)) {
      this.selectedEditorImages.delete(uuid);
      $wrapper.removeClass(EDITOR_TRANSIENT.CSS_SELECTED);
    } else {
      this.selectedEditorImages.add(uuid);
      $wrapper.addClass(EDITOR_TRANSIENT.CSS_SELECTED);
    }

    var $allImages = this.$editor.find(Tt.JOURNAL_IMAGE_SELECTOR);
    this.lastSelectedEditorIndex = $allImages.index($img);
  };

  /**
   * Clear all editor image selections
   */
  JournalEditor.prototype.clearEditorImageSelections = function() {
    this.selectedEditorImages.clear();
    this.$editor.find(Tt.JOURNAL_IMAGE_WRAPPER_SELECTOR).removeClass(EDITOR_TRANSIENT.CSS_SELECTED);
    this.lastSelectedEditorIndex = null;
    this.updateEditorSelectionUI();
  };

  /**
   * Update editor selection count badge UI
   */
  JournalEditor.prototype.updateEditorSelectionUI = function() {
    var count = this.selectedEditorImages.size;
    this.editorBadgeManager.update(count);

    // Notify coordinator when selections change
    imageSelectionCoordinator.notifyEditorSelection(count > 0);
  };

  /**
   * Setup image reordering within editor
   */
  JournalEditor.prototype.setupImageReordering = function() {
    var self = this;

    // Handle dragstart for images already in editor
    this.$editor.on('dragstart', Tt.JOURNAL_IMAGE_SELECTOR, function(e) {
      var $img = $(this);
      var $wrapper = $img.closest(Tt.JOURNAL_IMAGE_WRAPPER_SELECTOR);

      self.draggedElement = $wrapper[0]; // Store wrapper, not image
      self.dragSource = 'editor';

      // Update visual feedback (handles multi-image .dragging and count badge)
      self.updateDraggingVisuals(true);

      e.originalEvent.dataTransfer.effectAllowed = 'move';
      e.originalEvent.dataTransfer.setData('text/plain', '');
    });

    // Handle dragend for images in editor
    this.$editor.on('dragend', Tt.JOURNAL_IMAGE_SELECTOR, function(e) {
      // Visual cleanup only - state cleanup happens in drop handlers
      self.updateDraggingVisuals(false);
      self.clearDropZones();
    });

    // Drop handling is now unified in setupImageDragDrop()
    // No separate drop handler needed here
  };

  /**
   * Handle image reordering within editor (supports multi-image move)
   */
  JournalEditor.prototype.handleImageReorder = function(e) {
    if (!this.draggedElement) {
      return;
    }

    // Get wrappers to move (1 or many)
    var wrappersToMove = this.getEditorWrappersToMove();
    if (wrappersToMove.length === 0) {
      return;
    }

    // CRITICAL: Detach all wrappers first to prevent DOM issues
    // Store them in an array with their DOM elements
    var wrappersData = [];
    for (var i = 0; i < wrappersToMove.length; i++) {
      var $wrapper = wrappersToMove[i];
      var oldLayout = $wrapper.attr('data-' + Tt.JOURNAL_LAYOUT_ATTR);
      wrappersData.push({
        element: $wrapper.get(0),  // Store raw DOM element
        $wrapper: $wrapper,
        oldLayout: oldLayout
      });
      $wrapper.detach();  // Detach (not remove) to preserve event handlers
    }

    // Determine target layout and position (same logic as before)
    var $target = $(e.target);
    var $textBlock = $target.closest('.text-block');
    var newLayout = LAYOUT_VALUES.FULL_WIDTH;
    var $insertTarget = null;
    var insertMode = null; // 'prepend-paragraph', 'after-wrapper', 'before-element', 'append-editor'

    if ($textBlock.length && $textBlock.parent().is(this.$editor)) {
      // Dropped into a text block (p or div)
      newLayout = LAYOUT_VALUES.FLOAT_RIGHT;
      $insertTarget = $textBlock;
      insertMode = 'prepend-paragraph';
    } else {
      // Dropped outside text blocks (full-width area)
      newLayout = LAYOUT_VALUES.FULL_WIDTH;

      // Check if dropping on/near a specific full-width image wrapper
      var $targetImageWrapper = $target.closest(Tt.JOURNAL_IMAGE_WRAPPER_FULL_SELECTOR);

      if ($targetImageWrapper.length && $targetImageWrapper.closest(this.$editor).length) {
        // Dropping on a specific full-width image - insert after it (within same group)
        $insertTarget = $targetImageWrapper;
        insertMode = 'after-wrapper';
      } else {
        // Dropped between major sections - find closest block or group
        var mouseY = e.clientY;
        var $children = this.$editor.children('.text-block, div.content-block, h1, h2, h3, h4, h5, h6');
        var closestElement = null;
        var minDistance = Infinity;

        $children.each(function() {
          var rect = this.getBoundingClientRect();
          var distance = Math.abs(rect.top - mouseY);

          if (distance < minDistance) {
            minDistance = distance;
            closestElement = this;
          }
        });

        if (closestElement) {
          $insertTarget = $(closestElement);
          insertMode = 'before-element';
        } else {
          $insertTarget = this.$editor;
          insertMode = 'append-editor';
        }
      }
    }

    // Insert each wrapper using existing logic
    var $lastMoved = null;
    for (var i = 0; i < wrappersData.length; i++) {
      var wrapperData = wrappersData[i];
      var $wrapper = wrapperData.$wrapper;

      // Insert wrapper at target
      if (!$lastMoved) {
        // First move - use original target logic
        if (insertMode === 'prepend-paragraph') {
          $insertTarget.prepend($wrapper);
        } else if (insertMode === 'after-wrapper') {
          $insertTarget.after($wrapper);
        } else if (insertMode === 'before-element') {
          $insertTarget.before($wrapper);
        } else if (insertMode === 'append-editor') {
          $insertTarget.append($wrapper);
        }
      } else {
        // Subsequent moves - chain after last moved
        if (insertMode === 'prepend-paragraph') {
          // For float-right, prepend each one (so they appear in order)
          $insertTarget.prepend($wrapper);
        } else {
          // For full-width, insert after last moved
          $lastMoved.after($wrapper);
        }
      }

      // Update layout attribute if changed
      if (newLayout !== wrapperData.oldLayout) {
        $wrapper.attr('data-' + Tt.JOURNAL_LAYOUT_ATTR, newLayout);
      }

      $lastMoved = $wrapper;
    }

    // NOW enforce 2-image limit per paragraph (after all insertions)
    if (insertMode === 'prepend-paragraph') {
      var existingWrappers = $insertTarget.find(Tt.JOURNAL_IMAGE_WRAPPER_FLOAT_SELECTOR);
      var evicted = false;
      while (existingWrappers.length > 2) {
        // Remove rightmost (last) wrapper - FIFO eviction
        // Use helper to ensure usage tracking is updated
        this._removeWrapperAndUpdateUsage(existingWrappers.last());
        existingWrappers = $insertTarget.find(Tt.JOURNAL_IMAGE_WRAPPER_FLOAT_SELECTOR);
        evicted = true;
      }

      // Update picker filter once if any images were evicted
      if (evicted && this.imagePicker) {
        this.imagePicker.applyFilter(this.imagePicker.filterScope);
      }
    }

    // Refresh layout (images removed) + trigger autosave
    this.refreshImageLayout();
    this.handleContentChange();

    // Clear editor selections if multiple wrappers were moved
    if (wrappersToMove.length > 1) {
      this.clearEditorImageSelections();
    }
  };

  /**
   * Handle dropping editor or reference images onto picker panel (drag-to-remove)
   * Supports multi-image removal if multiple images selected
   *
   * This provides an intuitive UX: dragging from picker to editor inserts,
   * so dragging from editor back to picker should remove (reverse operation)
   */
  JournalEditor.prototype.handleImageRemovalDrop = function(e) {
    if (!this.draggedElement) {
      return;
    }

    if (this.dragSource === 'editor') {
      // Get wrappers to remove (1 or many, based on selection)
      var wrappersToRemove = this.getEditorWrappersToMove();

      // Remove each wrapper (reuses existing removal logic)
      for (var i = 0; i < wrappersToRemove.length; i++) {
        var $wrapper = wrappersToRemove[i];
        var $img = $wrapper.find(Tt.JOURNAL_IMAGE_SELECTOR);
        this.removeImage($img);
      }

      // Clear editor selections if multiple images were removed
      if (wrappersToRemove.length > 1) {
        this.clearEditorImageSelections();
      }
    } else if (this.dragSource === 'reference') {
      // Clear reference image
      this.clearReferenceImage();
    }

    // Clean up drag state
    this.draggedElement = null;
    this.dragSource = null;
  };

  /**
   * Setup image removal
   */
  JournalEditor.prototype.setupImageRemoval = function() {
    var self = this;

    // Note: Images are always wrapped with delete button at creation time
    // No need for hover-based wrapping

    // Handle delete button click
    this.$editor.on('click', EDITOR_TRANSIENT.SEL_DELETE_BTN, function(e) {
      e.preventDefault();
      e.stopPropagation();

      var $wrapper = $(this).closest(Tt.JOURNAL_IMAGE_WRAPPER_SELECTOR);
      var $img = $wrapper.find(Tt.JOURNAL_IMAGE_SELECTOR);

      self.removeImage($img);
    });

    // Keyboard support for image deletion
    this.$editor.on('keydown', function(e) {
      if (e.key === 'Delete' || e.key === 'Backspace') {
        var selection = window.getSelection();
        if (selection.rangeCount > 0) {
          var range = selection.getRangeAt(0);
          var node = range.startContainer;

          // Check if we're at an image
          var $img = null;
          if (node.nodeType === Node.ELEMENT_NODE && $(node).is(Tt.JOURNAL_IMAGE_SELECTOR)) {
            $img = $(node);
          } else if (node.nodeType === Node.ELEMENT_NODE) {
            $img = $(node).find(Tt.JOURNAL_IMAGE_SELECTOR).first();
          }

          if ($img && $img.length) {
            e.preventDefault();
            self.removeImage($img);
          }
        }
      }
    });
  };

  /**
   * Remove wrapper from DOM and update usage tracking (private helper)
   *
   * This couples the DOM removal with data structure update to ensure
   * they always happen together. Does NOT trigger side effects (autosave,
   * filter updates) - caller is responsible for those.
   *
   * @param {jQuery} $wrapper - The image wrapper to remove
   * @returns {string|null} The UUID of the removed image, or null if none
   * @private
   */
  JournalEditor.prototype._removeWrapperAndUpdateUsage = function($wrapper) {
    // Extract UUID before removing
    var $img = $wrapper.find(Tt.JOURNAL_IMAGE_SELECTOR);
    var uuid = $img.data(Tt.JOURNAL_UUID_ATTR);

    // Remove wrapper from DOM
    $wrapper.remove();

    // Update usage tracking (always paired with DOM removal)
    // Decrement count to handle same image appearing multiple times
    if (uuid) {
      var currentCount = this.usedImageUUIDs.get(uuid) || 0;
      if (currentCount > 1) {
        this.usedImageUUIDs.set(uuid, currentCount - 1);
      } else {
        this.usedImageUUIDs.delete(uuid);
      }
    }

    return uuid;
  };

  /**
   * Remove image from editor
   */
  JournalEditor.prototype.removeImage = function($img) {
    // Get wrapper and remove it (updates usage tracking)
    var $wrapper = $img.closest(Tt.JOURNAL_IMAGE_WRAPPER_SELECTOR);
    var uuid = this._removeWrapperAndUpdateUsage($wrapper);

    // Update picker filter if image was tracked
    if (uuid && this.imagePicker) {
      this.imagePicker.applyFilter(this.imagePicker.filterScope);
    }

    // Refresh layout (image removed) + trigger autosave
    this.refreshImageLayout();
    this.handleContentChange();
  };

  /**
   * Setup reference image drag-and-drop, clear button, and double-click
   */
  JournalEditor.prototype.setupReferenceImage = function() {
    var self = this;

    if (!this.$referenceContainer.length) {
      return;
    }

    // Setup drag-and-drop on placeholder/preview
    this.$referenceContainer.on('dragover', function(e) {
      e.preventDefault();
      e.stopPropagation();

      // Set dropEffect based on drag source
      // Editor drags are 'move', picker drags are 'copy'
      if (self.dragSource === 'editor') {
        e.originalEvent.dataTransfer.dropEffect = 'move';
      } else {
        e.originalEvent.dataTransfer.dropEffect = 'copy';
      }

      if (self.shouldShowReferenceDropZone()) {
        self.setReferenceDropZoneVisible(true);
      }
    });

    this.$referenceContainer.on('dragleave', function(e) {
      // Only remove if we're leaving the container completely
      if (!$(e.relatedTarget).closest('.journal-reference-image-container').length) {
        self.setReferenceDropZoneVisible(false);
      }
    });

    this.$referenceContainer.on('drop', function(e) {
      e.preventDefault();
      e.stopPropagation();

      self.setReferenceDropZoneVisible(false);

      try {
        var imageData = self.getDraggedImageData();
        if (imageData) {
          self.setReferenceImage(imageData);
        } else {
          console.warn('[JournalEditor] Drop failed: no image data available');
        }
      } catch (error) {
        console.error('[JournalEditor] Error setting reference image:', error);
        // Show user-friendly notification if toast system is available
        if (typeof Tt !== 'undefined' && Tt.showToast) {
          Tt.showToast('error', 'Could not set reference image. Please try again.');
        }
      } finally {
        // Always clean up drag state, even if error occurred
        self.draggedElement = null;
        self.dragSource = null;
      }
    });

    // Setup clear button click
    this.$referenceContainer.on('click', '.journal-reference-image-clear', function(e) {
      e.preventDefault();
      e.stopPropagation();
      self.clearReferenceImage();
    });

    // Setup double-click to open inspector
    this.$referenceContainer.on('dblclick', '.journal-reference-image-thumbnail', function(e) {
      e.preventDefault();
      var inspectUrl = $(this).data('inspect-url');
      if (inspectUrl && typeof AN !== 'undefined' && AN.get) {
        AN.get(inspectUrl);
      }
    });

    // Setup reference image dragging (for drag-to-remove)
    this.$referenceContainer.on('dragstart', '.journal-reference-image-thumbnail', function(e) {
      self.draggedElement = this;
      self.dragSource = 'reference';

      e.originalEvent.dataTransfer.effectAllowed = 'move';
      e.originalEvent.dataTransfer.setData('text/plain', '');
    });

    this.$referenceContainer.on('dragend', '.journal-reference-image-thumbnail', function(e) {
      // Visual cleanup happens in drop handlers
      self.draggedElement = null;
      self.dragSource = null;
    });
  };

  /**
   * Set reference image from image data
   * @param {Object} imageData - {uuid, url, caption, inspectUrl (optional)}
   */
  JournalEditor.prototype.setReferenceImage = function(imageData) {
    // Use ImageDataService to get complete data if needed
    var completeData = imageData;
    if (!imageData.inspectUrl) {
      completeData = ImageDataService.getImageDataByUUID(imageData.uuid);
      if (!completeData) {
        console.error('[JournalEditor] Cannot set reference image: lookup failed for UUID', imageData.uuid);
        return;
      }
    }

    // Update state
    this.currentReferenceImageUuid = completeData.uuid;
    this.$referenceContainer.data('reference-image-uuid', this.currentReferenceImageUuid);

    // Update preview image attributes
    var $preview = this.$referenceContainer.find('.journal-reference-image-preview');
    var $placeholder = this.$referenceContainer.find('.journal-reference-image-placeholder');
    var $img = $preview.find('.journal-reference-image-thumbnail');

    $img.attr('src', completeData.url);
    $img.attr('alt', completeData.caption || 'Reference');
    $img.attr('data-inspect-url', completeData.inspectUrl);

    // Show preview, hide placeholder
    $placeholder.addClass('d-none');
    $preview.removeClass('d-none');

    // Trigger autosave
    this.handleContentChange();
  };

  /**
   * Clear reference image
   */
  JournalEditor.prototype.clearReferenceImage = function() {
    // Update state - set to null (matches title/date/timezone pattern)
    this.currentReferenceImageUuid = null;
    this.$referenceContainer.data('reference-image-uuid', '');

    // Hide preview, show placeholder
    this.$referenceContainer.find('.journal-reference-image-preview').addClass('d-none');
    this.$referenceContainer.find('.journal-reference-image-placeholder').removeClass('d-none');

    // Trigger autosave (will send empty string to backend to clear the field)
    this.handleContentChange();
  };

  /**
   * Setup keyboard navigation and shortcuts
   */
  JournalEditor.prototype.setupKeyboardNavigation = function() {
    var self = this;

    // Global keyboard shortcut handler
    $(document).on('keydown', function(e) {
      self.handleGlobalKeyboardShortcut(e);
    });
  };

  /**
   * Global keyboard shortcut handler
   * Routes shortcuts based on active context
   */
  JournalEditor.prototype.handleGlobalKeyboardShortcut = function(e) {
    var context = this.determineActiveContext();
    var isCtrlOrCmd = e.ctrlKey || e.metaKey;

    // GLOBAL shortcuts (work in all contexts)
    // Ctrl/Cmd+/ - Show keyboard shortcuts help (STUB)
    if (isCtrlOrCmd && e.key === '/') {
      e.preventDefault();
      this.showKeyboardShortcutsHelp();
      return;
    }

    // TEXT EDITING CONTEXT shortcuts
    if (context === 'text') {
      // Ctrl/Cmd+B - Bold
      if (isCtrlOrCmd && e.key === 'b') {
        e.preventDefault();
        document.execCommand('bold', false, null);
        return;
      }

      // Ctrl/Cmd+I - Italic
      if (isCtrlOrCmd && e.key === 'i') {
        e.preventDefault();
        document.execCommand('italic', false, null);
        return;
      }

      // All other text shortcuts: preserve browser defaults
      return;
    }

    // PICKER IMAGES CONTEXT shortcuts
    if (context === 'picker') {
      // Escape - Clear all selections
      if (e.key === 'Escape') {
        e.preventDefault();
        if (this.imagePicker) {
          this.imagePicker.clearAllSelections();
        }
        return;
      }

      // Delete/Backspace - Clear selection (same as Escape)
      if (e.key === 'Delete' || e.key === 'Backspace') {
        e.preventDefault();
        if (this.imagePicker) {
          this.imagePicker.clearAllSelections();
        }
        return;
      }

      // Ctrl/Cmd+R - Set representative image (STUB)
      if (isCtrlOrCmd && e.key === 'r') {
        e.preventDefault();
        this.setReferenceImageFromPicker();
        return;
      }

      return;
    }

    // EDITOR IMAGES CONTEXT shortcuts
    if (context === 'editor-images') {
      // Escape - Clear selections
      if (e.key === 'Escape') {
        e.preventDefault();
        this.clearEditorImageSelections();
        return;
      }

      // Delete/Backspace - Remove from editor
      if (e.key === 'Delete' || e.key === 'Backspace') {
        e.preventDefault();
        this.batchRemoveEditorImages(this.selectedEditorImages);
        return;
      }

      // Ctrl/Cmd+R - Set representative image (STUB)
      if (isCtrlOrCmd && e.key === 'r') {
        e.preventDefault();
        this.setReferenceImageFromEditor();
        return;
      }

      return;
    }
  };

  /**
   * Determine active context for keyboard shortcuts
   * Returns: 'text' | 'picker' | 'editor-images'
   *
   * Context Priority:
   * 1. Picker selections (highest priority)
   * 2. Editor image selections
   * 3. Text editing (default)
   */
  JournalEditor.prototype.determineActiveContext = function() {
    // Check if picker has selections
    if (this.imagePicker && this.imagePicker.selectedImages.size > 0) {
      return 'picker';
    }

    // Check if editor has image selections
    if (this.selectedEditorImages.size > 0) {
      return 'editor-images';
    }

    // Default to text editing context
    return 'text';
  };

  /**
   * Batch remove editor images by UUID set
   * @param {Set} uuidSet - Set of UUIDs to remove
   */
  JournalEditor.prototype.batchRemoveEditorImages = function(uuidSet) {
    if (uuidSet.size === 0) {
      return;
    }

    var self = this;

    // Find and remove all wrappers with matching UUIDs
    this.$editor.find(Tt.JOURNAL_IMAGE_WRAPPER_SELECTOR).each(function() {
      var $wrapper = $(this);
      var $img = $wrapper.find(Tt.JOURNAL_IMAGE_SELECTOR);
      var uuid = $img.data(Tt.JOURNAL_UUID_ATTR);

      if (uuidSet.has(uuid)) {
        $wrapper.remove();

        // Remove from used images tracking (for picker filtering)
        // Decrement count to handle same image appearing multiple times
        var currentCount = self.usedImageUUIDs.get(uuid) || 0;
        if (currentCount > 1) {
          self.usedImageUUIDs.set(uuid, currentCount - 1);
        } else {
          self.usedImageUUIDs.delete(uuid);
        }
      }
    });

    // Update picker filter if it exists
    if (this.imagePicker) {
      this.imagePicker.applyFilter(this.imagePicker.filterScope);
    }

    // Clear selections
    this.clearEditorImageSelections();

    // Refresh layout (images removed) + trigger autosave
    this.refreshImageLayout();
    this.handleContentChange();
  };

  /**
   * Set reference image from picker selection
   * Called by Ctrl+R keyboard shortcut when picker has selections
   */
  JournalEditor.prototype.setReferenceImageFromPicker = function() {
    if (!this.imagePicker || this.imagePicker.selectedImages.size === 0) {
      console.log('[Keyboard Shortcut] Ctrl+R: No picker images selected');
      return;
    }

    // Only use first selected image (single selection only)
    var firstUuid = Array.from(this.imagePicker.selectedImages)[0];
    var imageData = this.getImageDataFromUUID(firstUuid);

    if (!imageData) {
      console.error('Cannot find picker card for UUID:', firstUuid);
      return;
    }

    // Set as reference image
    this.setReferenceImage(imageData);

    // Clear picker selection after setting
    if (this.imagePicker) {
      this.imagePicker.clearAllSelections();
    }
  };

  /**
   * Set reference image from editor selection
   * Called by Ctrl+R keyboard shortcut when editor has selections
   */
  JournalEditor.prototype.setReferenceImageFromEditor = function() {
    if (this.selectedEditorImages.size === 0) {
      console.log('[Keyboard Shortcut] Ctrl+R: No editor images selected');
      return;
    }

    // Only use first selected image (single selection only)
    var firstUuid = Array.from(this.selectedEditorImages)[0];
    var imageData = this.getImageDataFromUUID(firstUuid);

    if (!imageData) {
      console.error('Cannot find picker card for UUID:', firstUuid);
      return;
    }

    // Set as reference image
    this.setReferenceImage(imageData);

    // Clear editor selections after setting
    this.clearEditorImageSelections();
  };

  /**
   * Show keyboard shortcuts help modal
   * Opens editing help modal via AN.get() to fetch from server
   */
  JournalEditor.prototype.showKeyboardShortcutsHelp = function() {
    // Construct URL to editor help endpoint (no parameters needed)
    var helpUrl = '/journal/editor-help';

    // Use antinode.js to fetch and display modal
    if (typeof AN !== 'undefined' && AN.get) {
      AN.get(helpUrl);
    } else {
      console.error('Antinode.js not available');
    }
  };

  /**
   * Utility: Get CSRF token
   */
  JournalEditor.prototype.getCSRFToken = function() {
    return Cookies.get('csrftoken');
  };

  /**
   * Check if editor has unsaved content
   * Public method for beforeunload handler to check unsaved state
   * @returns {boolean} true if there are unsaved changes
   */
  JournalEditor.prototype.hasUnsavedContent = function() {
    return this.autoSaveManager && this.autoSaveManager.hasUnsavedChanges;
  };

  /**
   * Initialize editor on document ready
   */
  $(document).ready(function() {
    var $editor = $('#' + Tt.JOURNAL_EDITOR_ID);

    if ($editor.length && $editor.attr('contenteditable') === 'true') {
      editorInstance = new JournalEditor($editor);
    }
  });

  /**
   * Global beforeunload handler
   * Warns user before navigating away from page with unsaved changes
   *
   * Browser will display standard warning message (cannot be customized)
   */
  $(window).on('beforeunload', function(e) {
    if (editorInstance && editorInstance.hasUnsavedContent()) {
      // Prevent default behavior
      e.preventDefault();

      // Required for Chrome
      e.returnValue = '';

      // Required for other browsers
      return '';
    }
  });

  // ========================================
  // JOURNAL REFERENCE IMAGE PICKER
  // ========================================

  /**
   * Initialize the journal reference image picker modal.
   * Handles image selection and form submission.
   */
  function initJournalReferenceImagePicker() {
    // Use MutationObserver to detect when modal is added to DOM
    const observer = new MutationObserver(function(mutations) {
      mutations.forEach(function(mutation) {
        mutation.addedNodes.forEach(function(node) {
          if (node.nodeType === 1 && node.id === 'journal-reference-image-picker-modal') {
            setupReferenceImagePickerHandlers(node);
          }
        });
      });
    });

    observer.observe(document.body, { childList: true, subtree: true });
  }

  /**
   * Set up handlers for the reference image picker modal.
   * @param {HTMLElement} modal - The modal element
   */
  function setupReferenceImagePickerHandlers(modal) {
    const hiddenInput = modal.querySelector('#reference-image-uuid-input');
    const submitButton = modal.querySelector('#reference-image-set-btn');
    const galleryContainer = modal.querySelector('#reference-image-gallery-container');
    const previewContainer = modal.querySelector('#reference-image-preview');
    const captionElement = modal.querySelector('#reference-image-caption');

    if (!hiddenInput || !submitButton || !galleryContainer || !previewContainer || !captionElement) {
      console.error('Reference image picker: Required elements not found');
      return;
    }

    // Function to update the preview thumbnail
    function updatePreview(imageUrl, caption) {
      previewContainer.innerHTML = '';

      if (imageUrl) {
        const img = document.createElement('img');
        img.src = imageUrl;
        img.alt = 'Selected reference';
        img.style.width = '100%';
        img.style.height = '100%';
        img.style.objectFit = 'cover';
        previewContainer.appendChild(img);

        captionElement.textContent = caption || 'No caption';
      } else {
        // Show placeholder
        const placeholder = document.createElement('div');
        placeholder.className = 'bg-light d-flex align-items-center justify-content-center text-muted h-100';
        placeholder.innerHTML = '<svg class="tt-icon tt-icon-lg" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M12 12c1.66 0 3-1.34 3-3s-1.34-3-3-3-3 1.34-3 3 1.34 3 3 3zm0 2c-2.33 0-7 1.17-7 3.5V19h14v-1.5c0-2.33-4.67-3.5-7-3.5z"/></svg>';
        previewContainer.appendChild(placeholder);

        captionElement.textContent = 'No reference image set';
      }
    }

    // Function to attach click handlers to image cards
    function attachImageCardHandlers() {
      const imageCards = galleryContainer.querySelectorAll('.journal-image-card');

      imageCards.forEach(function(card) {
        card.addEventListener('click', function(e) {
          e.preventDefault();

          // Get image data from card
          const imageUuid = this.dataset.imageUuid;
          const thumbnailUrl = this.dataset.thumbnailUrl;
          const imageCaption = this.dataset.caption || '';

          if (imageUuid && thumbnailUrl) {
            // Update preview thumbnail
            updatePreview(thumbnailUrl, imageCaption);

            // Update hidden input
            hiddenInput.value = imageUuid;

            // Enable submit button
            submitButton.disabled = false;
          }
        });
      });
    }

    // Initial setup
    attachImageCardHandlers();

    // Re-attach handlers when gallery is updated via async reload (date change)
    const galleryObserver = new MutationObserver(function() {
      attachImageCardHandlers();
      // Don't reset selection when gallery changes - keep preview as is
    });

    galleryObserver.observe(galleryContainer, { childList: true, subtree: true });
  }

  // Initialize on DOM ready
  $(document).ready(function() {
    initJournalReferenceImagePicker();
  });

  // Expose for debugging
  window.JournalEditor = {
    getInstance: function() {
      return editorInstance;
    }
  };

})(jQuery);
