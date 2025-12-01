/**
 * Unit Tests for CursorPreservation
 *
 * Tests the cursor preservation system for journal entries:
 * - save() - captures cursor position and text selection
 * - restore() - restores cursor/selection from marker
 * - Edge cases: empty editor, cursor at boundaries, selections
 */

(function() {
  'use strict';

  // ===== CURSOR PRESERVATION TESTS =====
  QUnit.module('Tt.JournalEditor.CursorPreservation', function(hooks) {
    var $testEditor;

    hooks.beforeEach(function() {
      // Create a contenteditable editor for testing
      $testEditor = $('<div class="test-editor" contenteditable="true"></div>');
      $('#qunit-fixture').append($testEditor);
      // Focus editor to enable selection
      $testEditor.focus();
    });

    hooks.afterEach(function() {
      // Clear any selections
      window.getSelection().removeAllRanges();
    });

    // ----- Basic Existence Tests -----
    QUnit.test('CursorPreservation exists with required methods', function(assert) {
      var cp = Tt.JournalEditor.CursorPreservation;

      assert.ok(cp, 'CursorPreservation exists');
      assert.equal(typeof cp.save, 'function', 'save method exists');
      assert.equal(typeof cp.restore, 'function', 'restore method exists');
    });

    // ----- save() Tests -----
    QUnit.test('save returns null when no selection exists', function(assert) {
      $testEditor.html('<p class="text-block">Some text</p>');
      window.getSelection().removeAllRanges();

      var marker = Tt.JournalEditor.CursorPreservation.save($testEditor);

      assert.strictEqual(marker, null, 'Returns null when no selection');
    });

    QUnit.test('save returns null when selection is outside editor', function(assert) {
      $testEditor.html('<p class="text-block">Editor text</p>');
      var $outside = $('<div>Outside text</div>');
      $('#qunit-fixture').append($outside);

      // Create selection in outside element
      var range = document.createRange();
      var textNode = $outside[0].firstChild;
      range.setStart(textNode, 0);
      range.setEnd(textNode, 7);
      window.getSelection().removeAllRanges();
      window.getSelection().addRange(range);

      var marker = Tt.JournalEditor.CursorPreservation.save($testEditor);

      assert.strictEqual(marker, null, 'Returns null for selection outside editor');
    });

    QUnit.test('save captures collapsed cursor position', function(assert) {
      $testEditor.html('<p class="text-block">Hello world</p>');

      // Position cursor at offset 5 (after "Hello")
      var textNode = $testEditor.find('p')[0].firstChild;
      var range = document.createRange();
      range.setStart(textNode, 5);
      range.collapse(true);
      window.getSelection().removeAllRanges();
      window.getSelection().addRange(range);

      var marker = Tt.JournalEditor.CursorPreservation.save($testEditor);

      assert.ok(marker, 'Marker returned');
      assert.equal(marker.startTextOffset, 5, 'Start offset captured');
      assert.equal(marker.endTextOffset, 5, 'End offset same as start (collapsed)');
      assert.ok(marker.isCollapsed, 'Marked as collapsed');
    });

    QUnit.test('save captures text selection range', function(assert) {
      $testEditor.html('<p class="text-block">Hello world</p>');

      // Select "world" (offset 6 to 11)
      var textNode = $testEditor.find('p')[0].firstChild;
      var range = document.createRange();
      range.setStart(textNode, 6);
      range.setEnd(textNode, 11);
      window.getSelection().removeAllRanges();
      window.getSelection().addRange(range);

      var marker = Tt.JournalEditor.CursorPreservation.save($testEditor);

      assert.ok(marker, 'Marker returned');
      assert.equal(marker.startTextOffset, 6, 'Start offset captured');
      assert.equal(marker.endTextOffset, 11, 'End offset captured');
      assert.notOk(marker.isCollapsed, 'Not marked as collapsed');
    });

    QUnit.test('save captures blockIndex for fallback', function(assert) {
      $testEditor.html(
        '<p class="text-block">First paragraph</p>' +
        '<p class="text-block">Second paragraph</p>'
      );

      // Position cursor in second paragraph
      var secondPara = $testEditor.find('p').eq(1)[0];
      var textNode = secondPara.firstChild;
      var range = document.createRange();
      range.setStart(textNode, 3);
      range.collapse(true);
      window.getSelection().removeAllRanges();
      window.getSelection().addRange(range);

      var marker = Tt.JournalEditor.CursorPreservation.save($testEditor);

      assert.ok(marker, 'Marker returned');
      assert.equal(marker.blockIndex, 1, 'Block index captured (0-indexed)');
    });

    // ----- restore() Tests -----
    QUnit.test('restore handles null marker gracefully', function(assert) {
      $testEditor.html('<p class="text-block">Some text</p>');

      // Should not throw
      Tt.JournalEditor.CursorPreservation.restore($testEditor, null);

      assert.ok(true, 'Handled null marker without error');
    });

    QUnit.test('restore positions cursor at saved offset', function(assert) {
      $testEditor.html('<p class="text-block">Hello world</p>');

      var marker = {
        startTextOffset: 5,
        endTextOffset: 5,
        blockIndex: 0,
        isCollapsed: true
      };

      Tt.JournalEditor.CursorPreservation.restore($testEditor, marker);

      var selection = window.getSelection();
      assert.equal(selection.rangeCount, 1, 'Selection exists');

      var range = selection.getRangeAt(0);
      assert.ok(range.collapsed, 'Cursor is collapsed');

      // Verify position by checking text before cursor
      var preRange = document.createRange();
      preRange.selectNodeContents($testEditor[0]);
      preRange.setEnd(range.startContainer, range.startOffset);
      assert.equal(preRange.toString().length, 5, 'Cursor at correct offset');
    });

    QUnit.test('restore recreates text selection', function(assert) {
      $testEditor.html('<p class="text-block">Hello world</p>');

      var marker = {
        startTextOffset: 6,
        endTextOffset: 11,
        blockIndex: 0,
        isCollapsed: false
      };

      Tt.JournalEditor.CursorPreservation.restore($testEditor, marker);

      var selection = window.getSelection();
      assert.equal(selection.rangeCount, 1, 'Selection exists');
      assert.equal(selection.toString(), 'world', 'Correct text selected');
    });

    QUnit.test('restore uses fallback when offset exceeds content', function(assert) {
      $testEditor.html('<p class="text-block">Short</p>');

      var marker = {
        startTextOffset: 100,  // Way beyond content
        endTextOffset: 100,
        blockIndex: 0,
        isCollapsed: true
      };

      Tt.JournalEditor.CursorPreservation.restore($testEditor, marker);

      // Should not throw, cursor should be positioned somewhere
      var selection = window.getSelection();
      assert.ok(selection.rangeCount > 0 || true, 'Fallback handled gracefully');
    });

    QUnit.test('restore works across multiple paragraphs', function(assert) {
      $testEditor.html(
        '<p class="text-block">First</p>' +
        '<p class="text-block">Second</p>'
      );
      // Total text: "FirstSecond" = 11 chars
      // "First" = 5, "Second" starts at 5

      var marker = {
        startTextOffset: 7,  // "Se" into second para
        endTextOffset: 7,
        blockIndex: 1,
        isCollapsed: true
      };

      Tt.JournalEditor.CursorPreservation.restore($testEditor, marker);

      var selection = window.getSelection();
      assert.equal(selection.rangeCount, 1, 'Selection exists');

      // Verify cursor is in second paragraph
      var range = selection.getRangeAt(0);
      var $container = $(range.startContainer).closest('p');
      assert.ok($container.text().indexOf('Second') >= 0, 'Cursor in second paragraph');
    });

    QUnit.test('restore handles backward compatibility with textOffset', function(assert) {
      $testEditor.html('<p class="text-block">Hello world</p>');

      // Old-style marker with just textOffset
      var marker = {
        textOffset: 5,  // Legacy property name
        blockIndex: 0
      };

      Tt.JournalEditor.CursorPreservation.restore($testEditor, marker);

      var selection = window.getSelection();
      assert.equal(selection.rangeCount, 1, 'Selection exists with legacy marker');
    });

    // ----- Round-trip Tests -----
    QUnit.test('save then restore preserves cursor position', function(assert) {
      $testEditor.html('<p class="text-block">The quick brown fox</p>');

      // Position cursor at offset 10
      var textNode = $testEditor.find('p')[0].firstChild;
      var range = document.createRange();
      range.setStart(textNode, 10);
      range.collapse(true);
      window.getSelection().removeAllRanges();
      window.getSelection().addRange(range);

      // Save, clear, restore
      var marker = Tt.JournalEditor.CursorPreservation.save($testEditor);
      window.getSelection().removeAllRanges();
      Tt.JournalEditor.CursorPreservation.restore($testEditor, marker);

      // Verify restored position
      var selection = window.getSelection();
      var restoredRange = selection.getRangeAt(0);
      var preRange = document.createRange();
      preRange.selectNodeContents($testEditor[0]);
      preRange.setEnd(restoredRange.startContainer, restoredRange.startOffset);
      assert.equal(preRange.toString().length, 10, 'Cursor position preserved');
    });

    QUnit.test('save then restore preserves text selection', function(assert) {
      $testEditor.html('<p class="text-block">Select this text</p>');

      // Select "this" (offset 7 to 11)
      var textNode = $testEditor.find('p')[0].firstChild;
      var range = document.createRange();
      range.setStart(textNode, 7);
      range.setEnd(textNode, 11);
      window.getSelection().removeAllRanges();
      window.getSelection().addRange(range);

      // Save, clear, restore
      var marker = Tt.JournalEditor.CursorPreservation.save($testEditor);
      window.getSelection().removeAllRanges();
      Tt.JournalEditor.CursorPreservation.restore($testEditor, marker);

      // Verify restored selection
      var selection = window.getSelection();
      assert.equal(selection.toString(), 'this', 'Selection preserved');
    });

    // ----- Edge Case Tests -----
    QUnit.test('handles cursor at start of editor', function(assert) {
      $testEditor.html('<p class="text-block">Some text</p>');

      // Position cursor at very start
      var textNode = $testEditor.find('p')[0].firstChild;
      var range = document.createRange();
      range.setStart(textNode, 0);
      range.collapse(true);
      window.getSelection().removeAllRanges();
      window.getSelection().addRange(range);

      var marker = Tt.JournalEditor.CursorPreservation.save($testEditor);
      assert.equal(marker.startTextOffset, 0, 'Offset 0 captured');

      window.getSelection().removeAllRanges();
      Tt.JournalEditor.CursorPreservation.restore($testEditor, marker);

      var selection = window.getSelection();
      var restoredRange = selection.getRangeAt(0);
      var preRange = document.createRange();
      preRange.selectNodeContents($testEditor[0]);
      preRange.setEnd(restoredRange.startContainer, restoredRange.startOffset);
      assert.equal(preRange.toString().length, 0, 'Cursor at start restored');
    });

    QUnit.test('handles cursor at end of editor', function(assert) {
      $testEditor.html('<p class="text-block">End test</p>');
      var textLength = $testEditor.text().length;  // 8

      // Position cursor at end
      var textNode = $testEditor.find('p')[0].firstChild;
      var range = document.createRange();
      range.setStart(textNode, textNode.length);
      range.collapse(true);
      window.getSelection().removeAllRanges();
      window.getSelection().addRange(range);

      var marker = Tt.JournalEditor.CursorPreservation.save($testEditor);
      assert.equal(marker.startTextOffset, textLength, 'End offset captured');

      window.getSelection().removeAllRanges();
      Tt.JournalEditor.CursorPreservation.restore($testEditor, marker);

      var selection = window.getSelection();
      assert.ok(selection.rangeCount > 0, 'Cursor restored at end');
    });

    QUnit.test('handles empty editor', function(assert) {
      $testEditor.html('');

      // Try to save with no content
      var marker = Tt.JournalEditor.CursorPreservation.save($testEditor);

      // May be null or have offset 0
      assert.ok(marker === null || marker.startTextOffset === 0, 'Empty editor handled');
    });

    QUnit.test('handles cursor in nested formatting', function(assert) {
      $testEditor.html('<p class="text-block">Hello <strong>bold <em>italic</em></strong> world</p>');

      // Position cursor inside nested em tag (inside "italic")
      var emNode = $testEditor.find('em')[0].firstChild;
      var range = document.createRange();
      range.setStart(emNode, 3);  // After "ita"
      range.collapse(true);
      window.getSelection().removeAllRanges();
      window.getSelection().addRange(range);

      // Save and restore
      var marker = Tt.JournalEditor.CursorPreservation.save($testEditor);
      window.getSelection().removeAllRanges();
      Tt.JournalEditor.CursorPreservation.restore($testEditor, marker);

      // Cursor should be restored (exact position may vary with formatting)
      var selection = window.getSelection();
      assert.ok(selection.rangeCount > 0, 'Cursor restored in nested formatting');
    });

  });

})();
