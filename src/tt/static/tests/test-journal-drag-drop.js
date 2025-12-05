/**
 * Tests for DragDropManager
 *
 * Tests drag-and-drop logic including:
 * - Wrapper detachment and layout attribute reading
 * - Wrapper insertion at various positions
 * - Drop target determination (layout and position)
 * - Float limit enforcement
 * - Closest block finding with midpoint logic
 */

(function() {
  'use strict';

  var DragDropManager = Tt.JournalEditor.DragDropManager;
  var LAYOUT_VALUES = Tt.JournalEditor.LAYOUT_VALUES;
  var HTML_STRUCTURE = Tt.JournalEditor.HTML_STRUCTURE;

  // ============================================================
  // Helper Functions
  // ============================================================

  /**
   * Create a mock event with clientY for position-based tests.
   * Since getBoundingClientRect needs rendered elements, we use
   * absolutely positioned elements with known coordinates.
   */
  function createMockEvent(clientY, target) {
    return {
      clientY: clientY,
      target: target || document.body
    };
  }

  /**
   * Create a mock ImageManager with minimal functionality
   */
  function createMockImageManager() {
    return {
      usedImageUUIDs: new Map(),
      _removeWrapperAndUpdateUsage: function($wrapper) {
        var $img = $wrapper.find(TtConst.JOURNAL_IMAGE_SELECTOR);
        var uuid = $img.data(TtConst.UUID_DATA_ATTR);
        $wrapper.remove();
        return uuid;
      }
    };
  }

  // ============================================================
  // _detachWrappers Tests
  // ============================================================

  QUnit.module('DragDropManager._detachWrappers', function(hooks) {
    var $editor;
    var manager;

    hooks.beforeEach(function() {
      $editor = $('<div class="journal-editor" contenteditable="true"></div>');
      $('#qunit-fixture').append($editor);

      manager = new DragDropManager({
        $editor: $editor,
        imageManager: createMockImageManager(),
        refreshImageLayout: function() {},
        handleContentChange: function() {}
      });
    });

    hooks.afterEach(function() {
      $editor.remove();
    });

    QUnit.test('detaches wrapper from DOM', function(assert) {
      var $wrapper = $('<span class="trip-image-wrapper" data-layout="float-right"><img class="trip-image"></span>');
      $editor.append($wrapper);

      manager._detachWrappers([$wrapper]);

      assert.equal($editor.find('.trip-image-wrapper').length, 0, 'Wrapper removed from DOM');
    });

    QUnit.test('returns wrapper data with correct oldLayout', function(assert) {
      var $wrapper = $('<span class="trip-image-wrapper" data-layout="full-width"><img class="trip-image"></span>');
      $editor.append($wrapper);

      var result = manager._detachWrappers([$wrapper]);

      assert.equal(result.length, 1, 'Returns one wrapper data');
      assert.equal(result[0].oldLayout, 'full-width', 'Captures old layout');
      assert.ok(result[0].$wrapper.is($wrapper), 'Returns same wrapper');
    });

    QUnit.test('reads layout from attr not data cache (bug fix verification)', function(assert) {
      // This test verifies the fix for the .data() vs .attr() bug
      var $wrapper = $('<span class="trip-image-wrapper"><img class="trip-image"></span>');
      // Set via attr (how createImageElement does it)
      $wrapper.attr('data-layout', 'float-right');
      $editor.append($wrapper);

      // Simulate what happens if .data() was cached differently
      // In jQuery, .data() caches on first read, .attr() always reads DOM
      $wrapper.data('layout', 'stale-cached-value');

      var result = manager._detachWrappers([$wrapper]);

      // Should read from attr, not data cache
      assert.equal(result[0].oldLayout, 'float-right', 'Reads from attr, not data cache');
    });

    QUnit.test('handles multiple wrappers', function(assert) {
      var $wrapper1 = $('<span class="trip-image-wrapper" data-layout="float-right"><img class="trip-image"></span>');
      var $wrapper2 = $('<span class="trip-image-wrapper" data-layout="full-width"><img class="trip-image"></span>');
      $editor.append($wrapper1).append($wrapper2);

      var result = manager._detachWrappers([$wrapper1, $wrapper2]);

      assert.equal(result.length, 2, 'Returns two wrapper data');
      assert.equal(result[0].oldLayout, 'float-right', 'First has correct layout');
      assert.equal(result[1].oldLayout, 'full-width', 'Second has correct layout');
      assert.equal($editor.find('.trip-image-wrapper').length, 0, 'Both removed from DOM');
    });
  });

  // ============================================================
  // _insertMovedWrapper Tests
  // ============================================================

  QUnit.module('DragDropManager._insertMovedWrapper', function(hooks) {
    var $editor;
    var manager;

    hooks.beforeEach(function() {
      $editor = $('<div class="journal-editor" contenteditable="true"></div>');
      $('#qunit-fixture').append($editor);

      manager = new DragDropManager({
        $editor: $editor,
        imageManager: createMockImageManager(),
        refreshImageLayout: function() {},
        handleContentChange: function() {}
      });
    });

    hooks.afterEach(function() {
      $editor.remove();
    });

    QUnit.test('prepend-paragraph mode prepends to target', function(assert) {
      var $paragraph = $('<p class="text-block">Existing text</p>');
      $editor.append($paragraph);
      var $wrapper = $('<span class="trip-image-wrapper"><img class="trip-image"></span>');

      manager._insertMovedWrapper($wrapper, $paragraph, 'prepend-paragraph', null);

      assert.equal($paragraph.children().first().is($wrapper), true, 'Wrapper is first child');
    });

    QUnit.test('after-wrapper mode inserts after target', function(assert) {
      var $existingWrapper = $('<span class="trip-image-wrapper" data-layout="full-width"><img class="trip-image"></span>');
      $editor.append($existingWrapper);
      var $newWrapper = $('<span class="trip-image-wrapper"><img class="trip-image"></span>');

      manager._insertMovedWrapper($newWrapper, $existingWrapper, 'after-wrapper', null);

      assert.equal($existingWrapper.next().is($newWrapper), true, 'New wrapper is after existing');
    });

    QUnit.test('after-element mode inserts after target', function(assert) {
      var $block = $('<p class="text-block">Block 1</p>');
      $editor.append($block);
      var $wrapper = $('<span class="trip-image-wrapper"><img class="trip-image"></span>');

      manager._insertMovedWrapper($wrapper, $block, 'after-element', null);

      assert.equal($block.next().is($wrapper), true, 'Wrapper is after block');
    });

    QUnit.test('before-element mode inserts before target', function(assert) {
      var $block = $('<p class="text-block">Block 1</p>');
      $editor.append($block);
      var $wrapper = $('<span class="trip-image-wrapper"><img class="trip-image"></span>');

      manager._insertMovedWrapper($wrapper, $block, 'before-element', null);

      assert.equal($block.prev().is($wrapper), true, 'Wrapper is before block');
    });

    QUnit.test('append-editor mode appends to editor', function(assert) {
      var $wrapper = $('<span class="trip-image-wrapper"><img class="trip-image"></span>');

      manager._insertMovedWrapper($wrapper, $editor, 'append-editor', null);

      assert.equal($editor.children().last().is($wrapper), true, 'Wrapper is last child of editor');
    });

    QUnit.test('subsequent moves chain after lastMoved', function(assert) {
      var $block = $('<p class="text-block">Block</p>');
      $editor.append($block);
      var $wrapper1 = $('<span class="trip-image-wrapper" data-layout="full-width"><img class="trip-image"></span>');
      var $wrapper2 = $('<span class="trip-image-wrapper" data-layout="full-width"><img class="trip-image"></span>');

      var $lastMoved = manager._insertMovedWrapper($wrapper1, $block, 'before-element', null);
      manager._insertMovedWrapper($wrapper2, $block, 'before-element', $lastMoved);

      // wrapper1 should be before block, wrapper2 should be after wrapper1
      assert.equal($wrapper1.next().is($wrapper2), true, 'Second wrapper chains after first');
    });
  });

  // ============================================================
  // _enforceFloatLimit Tests
  // ============================================================

  QUnit.module('DragDropManager._enforceFloatLimit', function(hooks) {
    var $editor;
    var manager;
    var mockImageManager;

    hooks.beforeEach(function() {
      $editor = $('<div class="journal-editor" contenteditable="true"></div>');
      $('#qunit-fixture').append($editor);

      mockImageManager = createMockImageManager();

      manager = new DragDropManager({
        $editor: $editor,
        imageManager: mockImageManager,
        refreshImageLayout: function() {},
        handleContentChange: function() {}
      });
    });

    hooks.afterEach(function() {
      $editor.remove();
    });

    QUnit.test('does nothing when 2 or fewer float images', function(assert) {
      var $paragraph = $('<p class="text-block">' +
        '<span class="trip-image-wrapper" data-layout="float-right"><img class="trip-image"></span>' +
        '<span class="trip-image-wrapper" data-layout="float-right"><img class="trip-image"></span>' +
        'Some text</p>');
      $editor.append($paragraph);

      manager._enforceFloatLimit($paragraph);

      assert.equal($paragraph.find('.trip-image-wrapper').length, 2, 'Both images remain');
    });

    QUnit.test('removes excess float images down to 2', function(assert) {
      var $paragraph = $('<p class="text-block">' +
        '<span class="trip-image-wrapper" data-layout="float-right"><img class="trip-image" data-uuid="img1"></span>' +
        '<span class="trip-image-wrapper" data-layout="float-right"><img class="trip-image" data-uuid="img2"></span>' +
        '<span class="trip-image-wrapper" data-layout="float-right"><img class="trip-image" data-uuid="img3"></span>' +
        'Some text</p>');
      $editor.append($paragraph);

      manager._enforceFloatLimit($paragraph);

      assert.equal($paragraph.find('.trip-image-wrapper').length, 2, 'Only 2 images remain');
    });

    QUnit.test('removes rightmost (last) images first', function(assert) {
      var $paragraph = $('<p class="text-block">' +
        '<span class="trip-image-wrapper" data-layout="float-right"><img class="trip-image" data-uuid="first"></span>' +
        '<span class="trip-image-wrapper" data-layout="float-right"><img class="trip-image" data-uuid="second"></span>' +
        '<span class="trip-image-wrapper" data-layout="float-right"><img class="trip-image" data-uuid="third"></span>' +
        'Some text</p>');
      $editor.append($paragraph);

      manager._enforceFloatLimit($paragraph);

      var remainingUuids = $paragraph.find('.trip-image').map(function() {
        return $(this).data('uuid');
      }).get();

      assert.deepEqual(remainingUuids, ['first', 'second'], 'First two remain, third removed');
    });

    QUnit.test('ignores full-width images in paragraph', function(assert) {
      // Edge case: full-width image somehow in paragraph (shouldn't happen, but defensive)
      var $paragraph = $('<p class="text-block">' +
        '<span class="trip-image-wrapper" data-layout="float-right"><img class="trip-image"></span>' +
        '<span class="trip-image-wrapper" data-layout="float-right"><img class="trip-image"></span>' +
        '<span class="trip-image-wrapper" data-layout="full-width"><img class="trip-image"></span>' +
        'Some text</p>');
      $editor.append($paragraph);

      manager._enforceFloatLimit($paragraph);

      // Should only count float-right, so all 3 remain (2 float + 1 full)
      assert.equal($paragraph.find('.trip-image-wrapper').length, 3, 'Full-width not counted in limit');
    });
  });

  // ============================================================
  // _findClosestBlockForReorder Tests (Position Logic)
  // ============================================================

  QUnit.module('DragDropManager._findClosestBlockForReorder', function(hooks) {
    var $editor;
    var manager;

    hooks.beforeEach(function() {
      // Create editor with absolute positioning so getBoundingClientRect works
      $editor = $('<div class="journal-editor" contenteditable="true" style="position: absolute; top: 0; left: 0; width: 500px;"></div>');
      $('#qunit-fixture').css('position', 'relative');
      $('#qunit-fixture').append($editor);

      manager = new DragDropManager({
        $editor: $editor,
        imageManager: createMockImageManager(),
        refreshImageLayout: function() {},
        handleContentChange: function() {}
      });
    });

    hooks.afterEach(function() {
      $editor.remove();
      $('#qunit-fixture').css('position', '');
    });

    QUnit.test('returns append-editor when no children', function(assert) {
      var mockEvent = createMockEvent(100);

      var result = manager._findClosestBlockForReorder(mockEvent);

      assert.equal(result.insertMode, 'append-editor', 'Returns append mode for empty editor');
      assert.ok(result.$insertTarget.is($editor), 'Target is editor');
    });

    QUnit.test('returns before-element when mouse in upper half of block', function(assert) {
      // Create block with known height
      var $block = $('<p class="text-block" style="height: 100px; margin: 0; padding: 0;">Block content</p>');
      $editor.append($block);

      // Get actual position after render
      var rect = $block[0].getBoundingClientRect();
      // Mouse at 25% of block height (upper half)
      var mouseY = rect.top + (rect.height * 0.25);

      var mockEvent = createMockEvent(mouseY, $block[0]);

      var result = manager._findClosestBlockForReorder(mockEvent);

      assert.equal(result.insertMode, 'before-element', 'Upper half returns before-element');
    });

    QUnit.test('returns after-element when mouse in lower half of block', function(assert) {
      var $block = $('<p class="text-block" style="height: 100px; margin: 0; padding: 0;">Block content</p>');
      $editor.append($block);

      var rect = $block[0].getBoundingClientRect();
      // Mouse at 75% of block height (lower half)
      var mouseY = rect.top + (rect.height * 0.75);

      var mockEvent = createMockEvent(mouseY, $block[0]);

      var result = manager._findClosestBlockForReorder(mockEvent);

      assert.equal(result.insertMode, 'after-element', 'Lower half returns after-element');
    });

    QUnit.test('finds correct block when between two blocks', function(assert) {
      var $block1 = $('<p class="text-block" style="height: 50px; margin: 0; padding: 0;">Block 1</p>');
      var $block2 = $('<p class="text-block" style="height: 50px; margin: 0; padding: 0;">Block 2</p>');
      $editor.append($block1).append($block2);

      var rect1 = $block1[0].getBoundingClientRect();
      var rect2 = $block2[0].getBoundingClientRect();

      // Mouse just above block2's top (closer to block1's bottom)
      var mouseY = rect2.top - 5;

      var mockEvent = createMockEvent(mouseY);

      var result = manager._findClosestBlockForReorder(mockEvent);

      // Should be after block1 (closer to block1's bottom than block2's top)
      assert.equal(result.insertMode, 'after-element', 'Between blocks, closer to bottom = after');
      assert.ok(result.$insertTarget.is($block1), 'Target is block1');
    });

    QUnit.test('handles full-width image groups as blocks', function(assert) {
      var $group = $('<div class="text-block full-width-image-group" style="height: 100px; margin: 0; padding: 0;">' +
        '<span class="trip-image-wrapper" data-layout="full-width"><img class="trip-image"></span>' +
        '</div>');
      $editor.append($group);

      var rect = $group[0].getBoundingClientRect();
      var mouseY = rect.top + (rect.height * 0.75);

      var mockEvent = createMockEvent(mouseY, $group[0]);

      var result = manager._findClosestBlockForReorder(mockEvent);

      assert.equal(result.insertMode, 'after-element', 'Image group treated as block');
    });
  });

  // ============================================================
  // _determineReorderTarget Tests
  // ============================================================

  QUnit.module('DragDropManager._determineReorderTarget', function(hooks) {
    var $editor;
    var manager;

    hooks.beforeEach(function() {
      $editor = $('<div class="journal-editor" contenteditable="true" style="position: absolute; top: 0; left: 0; width: 500px;"></div>');
      $('#qunit-fixture').css('position', 'relative');
      $('#qunit-fixture').append($editor);

      manager = new DragDropManager({
        $editor: $editor,
        imageManager: createMockImageManager(),
        refreshImageLayout: function() {},
        handleContentChange: function() {}
      });
    });

    hooks.afterEach(function() {
      $editor.remove();
      $('#qunit-fixture').css('position', '');
    });

    QUnit.test('returns float-right layout when dropping into text block', function(assert) {
      var $paragraph = $('<p class="text-block" style="height: 50px;">Some text</p>');
      $editor.append($paragraph);

      var mockEvent = createMockEvent(25, $paragraph[0]);

      var result = manager._determineReorderTarget(mockEvent);

      assert.equal(result.newLayout, LAYOUT_VALUES.FLOAT_RIGHT, 'Layout is float-right');
      assert.equal(result.insertMode, 'prepend-paragraph', 'Mode is prepend-paragraph');
      assert.ok(result.$insertTarget.is($paragraph), 'Target is the paragraph');
    });

    QUnit.test('returns full-width layout when dropping onto full-width image', function(assert) {
      var $wrapper = $('<span class="trip-image-wrapper" data-layout="full-width" style="display: block; height: 50px;"><img class="trip-image"></span>');
      $editor.append($wrapper);

      var mockEvent = createMockEvent(25, $wrapper[0]);

      var result = manager._determineReorderTarget(mockEvent);

      assert.equal(result.newLayout, LAYOUT_VALUES.FULL_WIDTH, 'Layout is full-width');
      assert.equal(result.insertMode, 'after-wrapper', 'Mode is after-wrapper');
    });

    QUnit.test('returns full-width layout when dropping between blocks', function(assert) {
      var $block1 = $('<p class="text-block" style="height: 50px; margin: 0;">Block 1</p>');
      var $block2 = $('<p class="text-block" style="height: 50px; margin: 0;">Block 2</p>');
      $editor.append($block1).append($block2);

      // Drop in the space that's not directly on either block
      // Target the editor itself
      var rect = $block1[0].getBoundingClientRect();
      var mockEvent = createMockEvent(rect.bottom + 2, $editor[0]);

      var result = manager._determineReorderTarget(mockEvent);

      assert.equal(result.newLayout, LAYOUT_VALUES.FULL_WIDTH, 'Layout is full-width');
      assert.ok(result.insertMode === 'before-element' || result.insertMode === 'after-element',
        'Mode is before or after element');
    });
  });

  // ============================================================
  // getEditorWrappersToMove Tests
  // ============================================================

  QUnit.module('DragDropManager.getEditorWrappersToMove', function(hooks) {
    var $editor;
    var manager;

    hooks.beforeEach(function() {
      $editor = $('<div class="journal-editor" contenteditable="true"></div>');
      $('#qunit-fixture').append($editor);

      manager = new DragDropManager({
        $editor: $editor,
        imageManager: createMockImageManager(),
        refreshImageLayout: function() {},
        handleContentChange: function() {}
      });
    });

    hooks.afterEach(function() {
      $editor.remove();
    });

    QUnit.test('returns empty array when no dragged element', function(assert) {
      manager.draggedElement = null;

      var result = manager.getEditorWrappersToMove();

      assert.deepEqual(result, [], 'Returns empty array');
    });

    QUnit.test('returns array with dragged wrapper', function(assert) {
      var $wrapper = $('<span class="trip-image-wrapper"><img class="trip-image"></span>');
      $editor.append($wrapper);
      manager.draggedElement = $wrapper[0];

      var result = manager.getEditorWrappersToMove();

      assert.equal(result.length, 1, 'Returns one wrapper');
      assert.ok(result[0].is($wrapper), 'Returns the dragged wrapper');
    });
  });

  // ============================================================
  // Constants Export Tests
  // ============================================================

  QUnit.module('DragDropManager.Constants', function() {

    QUnit.test('LAYOUT_VALUES is exported', function(assert) {
      assert.ok(LAYOUT_VALUES, 'LAYOUT_VALUES is available');
      assert.equal(LAYOUT_VALUES.FLOAT_RIGHT, 'float-right', 'FLOAT_RIGHT value correct');
      assert.equal(LAYOUT_VALUES.FULL_WIDTH, 'full-width', 'FULL_WIDTH value correct');
    });

    QUnit.test('DRAG_SOURCE is exported', function(assert) {
      var DRAG_SOURCE = Tt.JournalEditor.DRAG_SOURCE;
      assert.ok(DRAG_SOURCE, 'DRAG_SOURCE is available');
      assert.equal(DRAG_SOURCE.PICKER, 'picker', 'PICKER value correct');
      assert.equal(DRAG_SOURCE.EDITOR, 'editor', 'EDITOR value correct');
      assert.equal(DRAG_SOURCE.REFERENCE, 'reference', 'REFERENCE value correct');
    });
  });

})();
