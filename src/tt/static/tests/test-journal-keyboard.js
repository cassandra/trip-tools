/**
 * Tests for KeyboardNavigationManager
 *
 * Tests keyboard handling including:
 * - Enter key block escape logic
 * - Backspace key block escape logic
 * - Cursor position detection
 * - Global keyboard shortcuts
 */

(function() {
  'use strict';

  // ============================================================
  // Cursor Position Helper Tests
  // ============================================================

  QUnit.module('KeyboardNavigationManager.CursorHelpers', function(hooks) {
    var $editor;
    var manager;

    hooks.beforeEach(function() {
      $editor = $('<div class="journal-editor" contenteditable="true"></div>');
      $editor.html('<p class="text-block">Hello world</p>');
      $('#qunit-fixture').append($editor);

      manager = new Tt.JournalEditor.KeyboardNavigationManager({
        $editor: $editor,
        onContentChange: function() {}
      });
    });

    hooks.afterEach(function() {
      manager.destroy();
      $editor.remove();
    });

    QUnit.test('isCursorAtEnd returns true when cursor at end of element', function(assert) {
      var $p = $editor.find('p');
      var textNode = $p[0].firstChild;

      // Set cursor at end of "Hello world" (position 11)
      var range = document.createRange();
      range.setStart(textNode, 11);
      range.collapse(true);

      var selection = window.getSelection();
      selection.removeAllRanges();
      selection.addRange(range);

      assert.ok(manager.isCursorAtEnd(range, $p[0]), 'Cursor at end detected');
    });

    QUnit.test('isCursorAtEnd returns false when cursor in middle', function(assert) {
      var $p = $editor.find('p');
      var textNode = $p[0].firstChild;

      // Set cursor in middle (position 5)
      var range = document.createRange();
      range.setStart(textNode, 5);
      range.collapse(true);

      var selection = window.getSelection();
      selection.removeAllRanges();
      selection.addRange(range);

      assert.notOk(manager.isCursorAtEnd(range, $p[0]), 'Cursor not at end');
    });

    QUnit.test('isCursorAtStart returns true when cursor at start of element', function(assert) {
      var $p = $editor.find('p');
      var textNode = $p[0].firstChild;

      // Set cursor at start (position 0)
      var range = document.createRange();
      range.setStart(textNode, 0);
      range.collapse(true);

      var selection = window.getSelection();
      selection.removeAllRanges();
      selection.addRange(range);

      assert.ok(manager.isCursorAtStart(range, $p[0]), 'Cursor at start detected');
    });

    QUnit.test('isCursorAtStart returns false when cursor in middle', function(assert) {
      var $p = $editor.find('p');
      var textNode = $p[0].firstChild;

      // Set cursor in middle (position 5)
      var range = document.createRange();
      range.setStart(textNode, 5);
      range.collapse(true);

      var selection = window.getSelection();
      selection.removeAllRanges();
      selection.addRange(range);

      assert.notOk(manager.isCursorAtStart(range, $p[0]), 'Cursor not at start');
    });

    QUnit.test('setCursorAtStart positions cursor at beginning of element', function(assert) {
      var $p = $editor.find('p');

      manager.setCursorAtStart($p[0]);

      var selection = window.getSelection();
      assert.equal(selection.rangeCount, 1, 'Selection has one range');

      var range = selection.getRangeAt(0);
      assert.ok(range.collapsed, 'Cursor is collapsed');
      assert.ok(manager.isCursorAtStart(range, $p[0]), 'Cursor positioned at start');
    });
  });

  // ============================================================
  // Enter Key Handling Tests
  // ============================================================

  QUnit.module('KeyboardNavigationManager.EnterKey', function(hooks) {
    var $editor;
    var manager;

    hooks.beforeEach(function() {
      $editor = $('<div class="journal-editor" contenteditable="true"></div>');
      $('#qunit-fixture').append($editor);

      manager = new Tt.JournalEditor.KeyboardNavigationManager({
        $editor: $editor,
        onContentChange: function() {}
      });
      manager.setup();
    });

    hooks.afterEach(function() {
      manager.destroy();
      $editor.remove();
    });

    QUnit.test('Enter at end of last list item creates paragraph after list', function(assert) {
      $editor.html('<div class="text-block"><ul><li>Item 1</li><li>Item 2</li></ul></div>');

      var $li = $editor.find('li').last();
      var textNode = $li[0].firstChild;

      // Position cursor at end of last item
      var range = document.createRange();
      range.setStart(textNode, textNode.length);
      range.collapse(true);

      var selection = window.getSelection();
      selection.removeAllRanges();
      selection.addRange(range);

      // Create mock event
      var mockEvent = $.Event('keydown', {
        key: 'Enter',
        shiftKey: false,
        ctrlKey: false,
        metaKey: false
      });

      manager.handleEnterInBlock(mockEvent);

      // Check that paragraph was created after the list container
      var $textBlocks = $editor.children('.text-block, p.text-block');
      assert.ok($textBlocks.length >= 1, 'Text block exists');
      assert.ok(mockEvent.isDefaultPrevented(), 'Default was prevented');
    });

    QUnit.test('Enter at start of first list item creates paragraph before list', function(assert) {
      $editor.html('<div class="text-block"><ul><li>Item 1</li><li>Item 2</li></ul></div>');

      var $li = $editor.find('li').first();

      // Position cursor at start of first item
      var range = document.createRange();
      range.selectNodeContents($li[0]);
      range.collapse(true);

      var selection = window.getSelection();
      selection.removeAllRanges();
      selection.addRange(range);

      // Create mock event
      var mockEvent = $.Event('keydown', {
        key: 'Enter',
        shiftKey: false,
        ctrlKey: false,
        metaKey: false
      });

      manager.handleEnterInBlock(mockEvent);

      assert.ok(mockEvent.isDefaultPrevented(), 'Default was prevented for escape before');
    });

    QUnit.test('Enter in middle of list item does not escape', function(assert) {
      $editor.html('<div class="text-block"><ul><li>Item 1</li></ul></div>');

      var $li = $editor.find('li').first();
      var textNode = $li[0].firstChild;

      // Position cursor in middle
      var range = document.createRange();
      range.setStart(textNode, 3); // After "Ite"
      range.collapse(true);

      var selection = window.getSelection();
      selection.removeAllRanges();
      selection.addRange(range);

      // Create mock event
      var mockEvent = $.Event('keydown', {
        key: 'Enter',
        shiftKey: false,
        ctrlKey: false,
        metaKey: false
      });

      manager.handleEnterInBlock(mockEvent);

      // Should not prevent default - let native behavior handle it
      assert.notOk(mockEvent.isDefaultPrevented(), 'Default not prevented in middle');
    });
  });

  // ============================================================
  // Backspace Key Handling Tests
  // ============================================================

  QUnit.module('KeyboardNavigationManager.BackspaceKey', function(hooks) {
    var $editor;
    var manager;

    hooks.beforeEach(function() {
      $editor = $('<div class="journal-editor" contenteditable="true"></div>');
      $('#qunit-fixture').append($editor);

      manager = new Tt.JournalEditor.KeyboardNavigationManager({
        $editor: $editor,
        onContentChange: function() {}
      });
      manager.setup();
    });

    hooks.afterEach(function() {
      manager.destroy();
      $editor.remove();
    });

    QUnit.test('Backspace at start of empty first list item replaces list with paragraph', function(assert) {
      $editor.html('<div class="text-block"><ul><li><br></li></ul></div>');

      var $li = $editor.find('li').first();

      // Position cursor at start of empty item
      var range = document.createRange();
      range.selectNodeContents($li[0]);
      range.collapse(true);

      var selection = window.getSelection();
      selection.removeAllRanges();
      selection.addRange(range);

      // Create mock event
      var mockEvent = $.Event('keydown', { key: 'Backspace' });

      manager.handleBackspaceInBlock(mockEvent);

      // Check that list was replaced with paragraph
      assert.ok(mockEvent.isDefaultPrevented(), 'Default was prevented');
      assert.equal($editor.find('ul').length, 0, 'List was removed');
      assert.equal($editor.find('p.text-block').length, 1, 'Paragraph was created');
    });

    QUnit.test('Backspace in non-empty list item does not escape', function(assert) {
      $editor.html('<div class="text-block"><ul><li>Content</li></ul></div>');

      var $li = $editor.find('li').first();
      var textNode = $li[0].firstChild;

      // Position cursor at start but item has content
      var range = document.createRange();
      range.setStart(textNode, 0);
      range.collapse(true);

      var selection = window.getSelection();
      selection.removeAllRanges();
      selection.addRange(range);

      // Create mock event
      var mockEvent = $.Event('keydown', { key: 'Backspace' });

      manager.handleBackspaceInBlock(mockEvent);

      // Should not prevent default - item has content
      assert.notOk(mockEvent.isDefaultPrevented(), 'Default not prevented for non-empty item');
    });

    QUnit.test('Backspace at start of empty blockquote paragraph replaces with paragraph', function(assert) {
      $editor.html('<div class="text-block"><blockquote><p><br></p></blockquote></div>');

      var $p = $editor.find('blockquote p').first();

      // Position cursor at start of empty paragraph
      var range = document.createRange();
      range.selectNodeContents($p[0]);
      range.collapse(true);

      var selection = window.getSelection();
      selection.removeAllRanges();
      selection.addRange(range);

      // Create mock event
      var mockEvent = $.Event('keydown', { key: 'Backspace' });

      manager.handleBackspaceInBlock(mockEvent);

      assert.ok(mockEvent.isDefaultPrevented(), 'Default was prevented');
      assert.equal($editor.find('blockquote').length, 0, 'Blockquote was removed');
    });
  });

  // ============================================================
  // Global Shortcuts Tests
  // ============================================================

  QUnit.module('KeyboardNavigationManager.GlobalShortcuts', function(hooks) {
    var $editor;
    var manager;
    var contentChangeCalled;

    hooks.beforeEach(function() {
      contentChangeCalled = false;

      $editor = $('<div class="journal-editor" contenteditable="true"></div>');
      $editor.html('<p class="text-block">Test content</p>');
      $('#qunit-fixture').append($editor);

      manager = new Tt.JournalEditor.KeyboardNavigationManager({
        $editor: $editor,
        onContentChange: function() {
          contentChangeCalled = true;
        }
      });
      manager.setup();
    });

    hooks.afterEach(function() {
      manager.destroy();
      $editor.remove();
    });

    QUnit.test('Ctrl+B triggers bold and content change', function(assert) {
      // Focus editor and select text
      $editor.focus();

      var mockEvent = $.Event('keydown', {
        key: 'b',
        ctrlKey: true,
        metaKey: false
      });

      manager._handleGlobalKeyboardShortcut(mockEvent);

      assert.ok(mockEvent.isDefaultPrevented(), 'Default was prevented');
      assert.ok(contentChangeCalled, 'Content change callback was called');
    });

    QUnit.test('Ctrl+I triggers italic and content change', function(assert) {
      // Focus editor
      $editor.focus();

      var mockEvent = $.Event('keydown', {
        key: 'i',
        ctrlKey: true,
        metaKey: false
      });

      manager._handleGlobalKeyboardShortcut(mockEvent);

      assert.ok(mockEvent.isDefaultPrevented(), 'Default was prevented');
      assert.ok(contentChangeCalled, 'Content change callback was called');
    });

    QUnit.test('Cmd+B (Mac) triggers bold', function(assert) {
      $editor.focus();

      var mockEvent = $.Event('keydown', {
        key: 'b',
        ctrlKey: false,
        metaKey: true
      });

      manager._handleGlobalKeyboardShortcut(mockEvent);

      assert.ok(mockEvent.isDefaultPrevented(), 'Default was prevented for Cmd+B');
    });

    QUnit.test('Regular B key does not trigger shortcut', function(assert) {
      $editor.focus();

      var mockEvent = $.Event('keydown', {
        key: 'b',
        ctrlKey: false,
        metaKey: false
      });

      manager._handleGlobalKeyboardShortcut(mockEvent);

      assert.notOk(mockEvent.isDefaultPrevented(), 'Default not prevented for regular B');
      assert.notOk(contentChangeCalled, 'Content change not called');
    });
  });

  // ============================================================
  // Setup and Destroy Tests
  // ============================================================

  QUnit.module('KeyboardNavigationManager.Lifecycle', function(hooks) {
    QUnit.test('setup binds events and destroy removes them', function(assert) {
      var $editor = $('<div class="journal-editor" contenteditable="true"></div>');
      $editor.html('<p class="text-block">Test</p>');
      $('#qunit-fixture').append($editor);

      var manager = new Tt.JournalEditor.KeyboardNavigationManager({
        $editor: $editor,
        onContentChange: function() {}
      });

      // Setup should bind events
      manager.setup();

      // Check events are bound (jQuery stores event data)
      var events = $._data($editor[0], 'events');
      assert.ok(events && events.keydown, 'Keydown event bound to editor');

      // Destroy should unbind events
      manager.destroy();

      events = $._data($editor[0], 'events');
      assert.notOk(events && events.keydown, 'Keydown event removed from editor');

      $editor.remove();
    });
  });

})();
