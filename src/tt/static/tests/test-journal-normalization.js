/**
 * Unit Tests for html-normalization.js
 *
 * Tests the HTML normalization system for journal entries:
 * - HTML_STRUCTURE constants
 * - ToolbarHelper DOM cleanup utilities
 * - Normalization functions (text-block wrapping, BR handling, etc.)
 * - runFullNormalization orchestration
 */

(function() {
  'use strict';

  // ===== HTML_STRUCTURE CONSTANTS TESTS =====
  QUnit.module('Tt.JournalEditor.HTML_STRUCTURE', function() {

    QUnit.test('HTML_STRUCTURE has required properties', function(assert) {
      var hs = Tt.JournalEditor.HTML_STRUCTURE;

      assert.ok(hs, 'HTML_STRUCTURE exists');
      assert.equal(hs.TEXT_BLOCK_CLASS, 'text-block', 'TEXT_BLOCK_CLASS is correct');
      assert.equal(hs.TEXT_BLOCK_SELECTOR, '.text-block', 'TEXT_BLOCK_SELECTOR is correct');
      assert.equal(hs.FULL_WIDTH_GROUP_CLASS, 'full-width-image-group', 'FULL_WIDTH_GROUP_CLASS is correct');
      assert.equal(hs.FULL_WIDTH_GROUP_SELECTOR, '.full-width-image-group', 'FULL_WIDTH_GROUP_SELECTOR is correct');
    });
  });

  // ===== TOOLBAR HELPER TESTS =====
  QUnit.module('Tt.JournalEditor.ToolbarHelper', function(hooks) {
    var $testRoot;

    hooks.beforeEach(function() {
      $testRoot = $('<div class="test-root"></div>');
      $('#qunit-fixture').append($testRoot);
    });

    // ----- removeEmptyElements -----
    QUnit.test('removeEmptyElements removes empty p tags', function(assert) {
      $testRoot.html('<p></p><p>Has content</p><p></p>');

      Tt.JournalEditor.ToolbarHelper.removeEmptyElements($testRoot);

      assert.equal($testRoot.find('p').length, 1, 'Only non-empty p remains');
      assert.equal($testRoot.find('p').text(), 'Has content', 'Content preserved');
    });

    QUnit.test('removeEmptyElements preserves p with br (cursor placeholder)', function(assert) {
      $testRoot.html('<p><br></p>');

      Tt.JournalEditor.ToolbarHelper.removeEmptyElements($testRoot);

      assert.equal($testRoot.find('p').length, 1, 'p with br preserved');
      assert.equal($testRoot.find('br').length, 1, 'br preserved');
    });

    QUnit.test('removeEmptyElements removes nested empty elements', function(assert) {
      $testRoot.html('<div><span><strong></strong></span></div><p>Keep me</p>');

      Tt.JournalEditor.ToolbarHelper.removeEmptyElements($testRoot);

      assert.equal($testRoot.find('div').length, 0, 'Empty div removed');
      assert.equal($testRoot.find('span').length, 0, 'Empty span removed');
      assert.equal($testRoot.find('strong').length, 0, 'Empty strong removed');
      assert.equal($testRoot.find('p').length, 1, 'p with content preserved');
    });

    QUnit.test('removeEmptyElements preserves elements with img children', function(assert) {
      $testRoot.html('<p><img src="test.jpg"></p>');

      Tt.JournalEditor.ToolbarHelper.removeEmptyElements($testRoot);

      assert.equal($testRoot.find('p').length, 1, 'p with img preserved');
      assert.equal($testRoot.find('img').length, 1, 'img preserved');
    });

    // ----- normalizeFormatting -----
    QUnit.test('normalizeFormatting converts b to strong', function(assert) {
      $testRoot.html('<p><b>Bold text</b></p>');

      Tt.JournalEditor.ToolbarHelper.normalizeFormatting($testRoot);

      assert.equal($testRoot.find('b').length, 0, 'b tag removed');
      assert.equal($testRoot.find('strong').length, 1, 'strong tag added');
      assert.equal($testRoot.find('strong').text(), 'Bold text', 'Text preserved');
    });

    QUnit.test('normalizeFormatting converts i to em', function(assert) {
      $testRoot.html('<p><i>Italic text</i></p>');

      Tt.JournalEditor.ToolbarHelper.normalizeFormatting($testRoot);

      assert.equal($testRoot.find('i').length, 0, 'i tag removed');
      assert.equal($testRoot.find('em').length, 1, 'em tag added');
      assert.equal($testRoot.find('em').text(), 'Italic text', 'Text preserved');
    });

    QUnit.test('normalizeFormatting unwraps nested identical tags', function(assert) {
      $testRoot.html('<p><strong><strong>Double bold</strong></strong></p>');

      Tt.JournalEditor.ToolbarHelper.normalizeFormatting($testRoot);

      assert.equal($testRoot.find('strong').length, 1, 'Nested strong unwrapped to single');
      assert.equal($testRoot.find('strong').text(), 'Double bold', 'Text preserved');
    });

    // ----- unwrapNestedTags -----
    QUnit.test('unwrapNestedTags removes nested identical tags', function(assert) {
      $testRoot.html('<strong><strong>Text</strong></strong>');

      Tt.JournalEditor.ToolbarHelper.unwrapNestedTags($testRoot, 'strong');

      var strongCount = $testRoot.find('strong').length;
      assert.equal(strongCount, 1, 'Reduced to single strong tag');
    });

    // ----- cleanupInlineStyles -----
    QUnit.test('cleanupInlineStyles removes empty style attributes', function(assert) {
      $testRoot.html('<p style="">Has empty style</p>');

      Tt.JournalEditor.ToolbarHelper.cleanupInlineStyles($testRoot);

      assert.notOk($testRoot.find('p').attr('style'), 'Empty style attribute removed');
    });

    QUnit.test('cleanupInlineStyles removes margin-left: 0px', function(assert) {
      $testRoot.html('<p style="margin-left: 0px;">Zero margin</p>');

      Tt.JournalEditor.ToolbarHelper.cleanupInlineStyles($testRoot);

      var style = $testRoot.find('p').attr('style');
      assert.ok(!style || style.indexOf('margin-left') === -1, 'Zero margin-left removed');
    });

    // ----- validateStructure -----
    QUnit.test('validateStructure wraps orphan li in ul', function(assert) {
      $testRoot.html('<li>Orphan item</li>');

      Tt.JournalEditor.ToolbarHelper.validateStructure($testRoot);

      assert.equal($testRoot.find('ul').length, 1, 'ul wrapper added');
      assert.equal($testRoot.find('li').parent('ul').length, 1, 'li is inside ul');
    });

    QUnit.test('validateStructure removes nested anchor tags', function(assert) {
      $testRoot.html('<a href="#outer"><a href="#inner">Nested link</a></a>');

      Tt.JournalEditor.ToolbarHelper.validateStructure($testRoot);

      assert.equal($testRoot.find('a').length, 1, 'Nested a removed');
    });

    QUnit.test('validateStructure removes empty anchor tags', function(assert) {
      $testRoot.html('<a href="#empty"></a><a href="#text">Has text</a>');

      Tt.JournalEditor.ToolbarHelper.validateStructure($testRoot);

      assert.equal($testRoot.find('a').length, 1, 'Empty anchor removed');
      assert.equal($testRoot.find('a').text(), 'Has text', 'Anchor with text preserved');
    });

    QUnit.test('validateStructure removes empty lists', function(assert) {
      $testRoot.html('<ul></ul><ul><li>Item</li></ul>');

      Tt.JournalEditor.ToolbarHelper.validateStructure($testRoot);

      assert.equal($testRoot.find('ul').length, 1, 'Empty ul removed');
      assert.equal($testRoot.find('li').length, 1, 'ul with items preserved');
    });

    // ----- fullCleanup -----
    QUnit.test('fullCleanup runs all cleanup operations', function(assert) {
      $testRoot.html('<b>Bold</b><p></p><span style=""></span>');

      Tt.JournalEditor.ToolbarHelper.fullCleanup($testRoot);

      assert.equal($testRoot.find('b').length, 0, 'b converted to strong');
      assert.equal($testRoot.find('strong').length, 1, 'strong exists');
      assert.equal($testRoot.find('p').length, 0, 'Empty p removed');
      assert.equal($testRoot.find('span').length, 0, 'Empty span removed');
    });
  });

  // ===== NORMALIZATION FUNCTIONS TESTS =====
  QUnit.module('Tt.JournalEditor Normalization Functions', function(hooks) {
    var $testEditor;

    hooks.beforeEach(function() {
      $testEditor = $('<div class="test-editor" contenteditable="true"></div>');
      $('#qunit-fixture').append($testEditor);
    });

    // ----- runFullNormalization -----
    QUnit.test('runFullNormalization wraps bare text in text-block', function(assert) {
      $testEditor.html('Bare text content');

      Tt.JournalEditor.runFullNormalization($testEditor[0]);

      assert.equal($testEditor.find('.text-block').length, 1, 'Text wrapped in text-block');
      assert.ok($testEditor.find('.text-block').text().indexOf('Bare text') >= 0, 'Text preserved');
    });

    QUnit.test('runFullNormalization adds text-block class to plain p', function(assert) {
      $testEditor.html('<p>Paragraph without class</p>');

      Tt.JournalEditor.runFullNormalization($testEditor[0]);

      assert.ok($testEditor.find('p').hasClass('text-block'), 'text-block class added to p');
    });

    QUnit.test('runFullNormalization preserves headings at top level', function(assert) {
      $testEditor.html('<h1>Heading 1</h1><p class="text-block">Paragraph</p>');

      Tt.JournalEditor.runFullNormalization($testEditor[0]);

      assert.equal($testEditor.children('h1').length, 1, 'h1 preserved at top level');
      assert.equal($testEditor.find('h1').text(), 'Heading 1', 'Heading text preserved');
    });

    QUnit.test('runFullNormalization handles empty editor', function(assert) {
      $testEditor.html('');

      Tt.JournalEditor.runFullNormalization($testEditor[0]);

      assert.ok($testEditor.children().length > 0, 'Editor not empty after normalization');
      assert.ok($testEditor.find('.text-block').length > 0, 'Cursor placeholder added');
    });

    QUnit.test('runFullNormalization wraps block elements in text-block', function(assert) {
      $testEditor.html('<ul><li>Item 1</li></ul>');

      Tt.JournalEditor.runFullNormalization($testEditor[0]);

      var $ul = $testEditor.find('ul');
      assert.ok($ul.parent('.text-block').length > 0 || $ul.closest('.text-block').length > 0,
                'ul wrapped in or inside text-block');
    });

    // ----- BR tag handling -----
    QUnit.test('runFullNormalization handles text-BR-text as separator', function(assert) {
      $testEditor.html('First paragraph<br>Second paragraph');

      Tt.JournalEditor.runFullNormalization($testEditor[0]);

      var textBlocks = $testEditor.find('.text-block');
      assert.ok(textBlocks.length >= 2, 'BR creates paragraph separation');
    });

    QUnit.test('runFullNormalization removes redundant BR between paragraphs', function(assert) {
      $testEditor.html('<p class="text-block">Para 1</p><br><p class="text-block">Para 2</p>');

      Tt.JournalEditor.runFullNormalization($testEditor[0]);

      // BR between existing paragraphs is redundant and should be removed
      assert.equal($testEditor.children('br').length, 0, 'Redundant BR removed');
    });

    QUnit.test('runFullNormalization consolidates multiple BRs', function(assert) {
      $testEditor.html('Text<br><br><br>More text');

      Tt.JournalEditor.runFullNormalization($testEditor[0]);

      // Multiple BRs treated as single separator
      assert.ok($testEditor.find('br').length <= 1, 'Multiple BRs consolidated');
    });

    // ----- Heading extraction -----
    QUnit.test('runFullNormalization extracts heading from text-block', function(assert) {
      $testEditor.html('<div class="text-block"><h2>Heading</h2><p>Content</p></div>');

      Tt.JournalEditor.runFullNormalization($testEditor[0]);

      // Heading should be extracted to top level
      assert.ok($testEditor.children('h2').length > 0 || $testEditor.find('h2').closest('.text-block').length === 0,
                'Heading extracted from text-block');
    });
  });

  // ===== EDGE CASES =====
  QUnit.module('Tt.JournalEditor Normalization Edge Cases', function(hooks) {
    var $testEditor;

    hooks.beforeEach(function() {
      $testEditor = $('<div class="test-editor" contenteditable="true"></div>');
      $('#qunit-fixture').append($testEditor);
    });

    QUnit.test('handles whitespace-only text nodes', function(assert) {
      $testEditor.html('   \n\t   ');

      Tt.JournalEditor.runFullNormalization($testEditor[0]);

      // Whitespace-only should result in empty editor with placeholder
      assert.ok($testEditor.find('.text-block').length > 0, 'Placeholder created');
    });

    QUnit.test('handles mixed content correctly', function(assert) {
      $testEditor.html('<p class="text-block">Text</p><h1>Heading</h1><p class="text-block">More</p>');

      Tt.JournalEditor.runFullNormalization($testEditor[0]);

      // All elements should be at top level
      assert.equal($testEditor.children('.text-block').length, 2, 'Both text-blocks preserved');
      assert.equal($testEditor.children('h1').length, 1, 'Heading preserved at top level');
    });

    QUnit.test('normalizes deeply nested invalid structure', function(assert) {
      $testEditor.html('<div><div><p>Nested content</p></div></div>');

      Tt.JournalEditor.runFullNormalization($testEditor[0]);

      // Content should be preserved even if deeply nested
      assert.ok($testEditor.text().indexOf('Nested content') >= 0, 'Content preserved');
    });

    QUnit.test('preserves inline formatting during normalization', function(assert) {
      $testEditor.html('<strong>Bold</strong> and <em>italic</em> text');

      Tt.JournalEditor.runFullNormalization($testEditor[0]);

      assert.equal($testEditor.find('strong').length, 1, 'strong preserved');
      assert.equal($testEditor.find('em').length, 1, 'em preserved');
      assert.ok($testEditor.text().indexOf('Bold') >= 0, 'Text content preserved');
    });
  });

})();
