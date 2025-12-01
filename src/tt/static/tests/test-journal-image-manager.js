/**
 * Tests for ImageManager
 *
 * Tests image operations including:
 * - Usage tracking (Map operations)
 * - Image element creation
 * - Image removal
 * - Image data lookup
 */

(function() {
  'use strict';

  // ============================================================
  // Usage Tracking Tests
  // ============================================================

  QUnit.module('ImageManager.UsageTracking', function(hooks) {
    var $editor;
    var manager;

    hooks.beforeEach(function() {
      $editor = $('<div class="journal-editor" contenteditable="true"></div>');
      $('#qunit-fixture').append($editor);

      manager = new Tt.JournalEditor.ImageManager({
        $editor: $editor
      });
    });

    hooks.afterEach(function() {
      $editor.remove();
    });

    QUnit.test('initializeUsedImages populates map from existing images', function(assert) {
      // Add some images to editor
      $editor.html(
        '<span class="trip-image-wrapper">' +
          '<img class="trip-image" data-uuid="uuid-1">' +
        '</span>' +
        '<span class="trip-image-wrapper">' +
          '<img class="trip-image" data-uuid="uuid-2">' +
        '</span>'
      );

      manager.initializeUsedImages();

      assert.ok(manager.isImageUsed('uuid-1'), 'uuid-1 is tracked');
      assert.ok(manager.isImageUsed('uuid-2'), 'uuid-2 is tracked');
      assert.notOk(manager.isImageUsed('uuid-3'), 'uuid-3 is not tracked');
    });

    QUnit.test('initializeUsedImages handles same image multiple times', function(assert) {
      // Same UUID appears twice
      $editor.html(
        '<span class="trip-image-wrapper">' +
          '<img class="trip-image" data-uuid="uuid-1">' +
        '</span>' +
        '<span class="trip-image-wrapper">' +
          '<img class="trip-image" data-uuid="uuid-1">' +
        '</span>'
      );

      manager.initializeUsedImages();

      assert.equal(manager.getImageUsageCount('uuid-1'), 2, 'Count is 2 for duplicate');
    });

    QUnit.test('isImageUsed returns correct boolean', function(assert) {
      manager.usedImageUUIDs.set('test-uuid', 1);

      assert.ok(manager.isImageUsed('test-uuid'), 'Returns true for tracked UUID');
      assert.notOk(manager.isImageUsed('unknown-uuid'), 'Returns false for unknown UUID');
    });

    QUnit.test('getUsedImageUUIDs returns Set of UUIDs', function(assert) {
      manager.usedImageUUIDs.set('uuid-1', 1);
      manager.usedImageUUIDs.set('uuid-2', 2);

      var uuids = manager.getUsedImageUUIDs();

      assert.ok(uuids instanceof Set, 'Returns a Set');
      assert.ok(uuids.has('uuid-1'), 'Contains uuid-1');
      assert.ok(uuids.has('uuid-2'), 'Contains uuid-2');
      assert.equal(uuids.size, 2, 'Has correct size');
    });
  });

  // ============================================================
  // Image Element Creation Tests
  // ============================================================

  QUnit.module('ImageManager.CreateElement', function(hooks) {
    var $editor;
    var manager;
    var addedUuids;

    hooks.beforeEach(function() {
      addedUuids = [];

      $editor = $('<div class="journal-editor" contenteditable="true"></div>');
      $('#qunit-fixture').append($editor);

      manager = new Tt.JournalEditor.ImageManager({
        $editor: $editor,
        onImageAdded: function(uuid) {
          addedUuids.push(uuid);
        }
      });
    });

    hooks.afterEach(function() {
      $editor.remove();
    });

    QUnit.test('createImageElement returns wrapper with correct structure', function(assert) {
      var $wrapper = manager.createImageElement('test-uuid', '/test.jpg', 'Test Caption', 'float-right');

      assert.ok($wrapper.hasClass('trip-image-wrapper'), 'Has wrapper class');
      assert.equal($wrapper.attr('data-layout'), 'float-right', 'Has layout attribute');

      var $img = $wrapper.find('.trip-image');
      assert.equal($img.length, 1, 'Contains image');
      assert.equal($img.attr('src'), '/test.jpg', 'Image has correct src');
      assert.equal($img.attr('alt'), 'Test Caption', 'Image has correct alt');
      assert.equal($img.attr('data-uuid'), 'test-uuid', 'Image has UUID');
    });

    QUnit.test('createImageElement adds caption span when caption provided', function(assert) {
      var $wrapper = manager.createImageElement('uuid', '/test.jpg', 'My Caption', 'full-width');

      var $caption = $wrapper.find('.trip-image-caption');
      assert.equal($caption.length, 1, 'Caption span exists');
      assert.equal($caption.text(), 'My Caption', 'Caption has correct text');
    });

    QUnit.test('createImageElement omits caption span when caption empty', function(assert) {
      var $wrapper = manager.createImageElement('uuid', '/test.jpg', '', 'full-width');

      var $caption = $wrapper.find('.trip-image-caption');
      assert.equal($caption.length, 0, 'No caption span for empty caption');
    });

    QUnit.test('createImageElement adds delete button', function(assert) {
      var $wrapper = manager.createImageElement('uuid', '/test.jpg', 'Caption', 'float-right');

      var $deleteBtn = $wrapper.find('.trip-image-delete-btn');
      assert.equal($deleteBtn.length, 1, 'Delete button exists');
      assert.equal($deleteBtn.attr('type'), 'button', 'Is a button element');
    });

    QUnit.test('createImageElement updates usage tracking', function(assert) {
      assert.equal(manager.getImageUsageCount('new-uuid'), 0, 'Initially not tracked');

      manager.createImageElement('new-uuid', '/test.jpg', 'Caption', 'float-right');

      assert.equal(manager.getImageUsageCount('new-uuid'), 1, 'Now tracked with count 1');
    });

    QUnit.test('createImageElement increments count for duplicate UUID', function(assert) {
      manager.createImageElement('dup-uuid', '/test1.jpg', 'Caption 1', 'float-right');
      manager.createImageElement('dup-uuid', '/test2.jpg', 'Caption 2', 'full-width');

      assert.equal(manager.getImageUsageCount('dup-uuid'), 2, 'Count is 2 for duplicate');
    });

    QUnit.test('createImageElement calls onImageAdded callback', function(assert) {
      manager.createImageElement('callback-uuid', '/test.jpg', 'Caption', 'float-right');

      assert.deepEqual(addedUuids, ['callback-uuid'], 'Callback was called with UUID');
    });
  });

  // ============================================================
  // Image Removal Tests
  // ============================================================

  QUnit.module('ImageManager.Removal', function(hooks) {
    var $editor;
    var manager;
    var removedUuids;
    var contentChangeCalled;
    var layoutRefreshed;

    hooks.beforeEach(function() {
      removedUuids = [];
      contentChangeCalled = false;
      layoutRefreshed = false;

      $editor = $('<div class="journal-editor" contenteditable="true"></div>');
      $('#qunit-fixture').append($editor);

      manager = new Tt.JournalEditor.ImageManager({
        $editor: $editor,
        onImageRemoved: function(uuid) {
          removedUuids.push(uuid);
        },
        onContentChange: function() {
          contentChangeCalled = true;
        },
        refreshLayout: function() {
          layoutRefreshed = true;
        }
      });
    });

    hooks.afterEach(function() {
      $editor.remove();
    });

    QUnit.test('_removeWrapperAndUpdateUsage removes wrapper from DOM', function(assert) {
      var $wrapper = $('<span class="trip-image-wrapper"><img class="trip-image" data-uuid="rem-uuid"></span>');
      $editor.append($wrapper);
      manager.usedImageUUIDs.set('rem-uuid', 1);

      manager._removeWrapperAndUpdateUsage($wrapper);

      assert.equal($editor.find('.trip-image-wrapper').length, 0, 'Wrapper removed from DOM');
    });

    QUnit.test('_removeWrapperAndUpdateUsage updates tracking', function(assert) {
      var $wrapper = $('<span class="trip-image-wrapper"><img class="trip-image" data-uuid="track-uuid"></span>');
      $editor.append($wrapper);
      manager.usedImageUUIDs.set('track-uuid', 1);

      manager._removeWrapperAndUpdateUsage($wrapper);

      assert.notOk(manager.isImageUsed('track-uuid'), 'UUID no longer tracked');
    });

    QUnit.test('_removeWrapperAndUpdateUsage decrements count for duplicates', function(assert) {
      var $wrapper = $('<span class="trip-image-wrapper"><img class="trip-image" data-uuid="dup-uuid"></span>');
      $editor.append($wrapper);
      manager.usedImageUUIDs.set('dup-uuid', 3); // Simulate 3 copies

      manager._removeWrapperAndUpdateUsage($wrapper);

      assert.equal(manager.getImageUsageCount('dup-uuid'), 2, 'Count decremented to 2');
    });

    QUnit.test('_removeWrapperAndUpdateUsage returns UUID', function(assert) {
      var $wrapper = $('<span class="trip-image-wrapper"><img class="trip-image" data-uuid="ret-uuid"></span>');
      $editor.append($wrapper);
      manager.usedImageUUIDs.set('ret-uuid', 1);

      var uuid = manager._removeWrapperAndUpdateUsage($wrapper);

      assert.equal(uuid, 'ret-uuid', 'Returns the removed UUID');
    });

    QUnit.test('removeImage triggers all callbacks', function(assert) {
      var $wrapper = $('<span class="trip-image-wrapper"><img class="trip-image" data-uuid="cb-uuid"></span>');
      $editor.append($wrapper);
      manager.usedImageUUIDs.set('cb-uuid', 1);

      var $img = $wrapper.find('.trip-image');
      manager.removeImage($img);

      assert.deepEqual(removedUuids, ['cb-uuid'], 'onImageRemoved called');
      assert.ok(contentChangeCalled, 'onContentChange called');
      assert.ok(layoutRefreshed, 'refreshLayout called');
    });
  });

  // ============================================================
  // Image Data Lookup Tests
  // ============================================================

  QUnit.module('ImageManager.DataLookup', function(hooks) {
    var $editor;
    var $pickerCard;
    var manager;

    hooks.beforeEach(function() {
      $editor = $('<div class="journal-editor" contenteditable="true"></div>');
      $('#qunit-fixture').append($editor);

      // Create a mock picker card
      $pickerCard = $('<div class="journal-editor-multi-image-card" ' +
        'data-image-uuid="lookup-uuid" ' +
        'data-image-url="/looked-up.jpg" ' +
        'data-caption="Looked Up Caption"></div>');
      $('#qunit-fixture').append($pickerCard);

      manager = new Tt.JournalEditor.ImageManager({
        $editor: $editor
      });
    });

    hooks.afterEach(function() {
      $editor.remove();
      $pickerCard.remove();
    });

    QUnit.test('getImageDataFromUUID returns data for existing card', function(assert) {
      var data = manager.getImageDataFromUUID('lookup-uuid');

      assert.ok(data, 'Returns data object');
      assert.equal(data.uuid, 'lookup-uuid', 'Has correct UUID');
      assert.equal(data.url, '/looked-up.jpg', 'Has correct URL');
      assert.equal(data.caption, 'Looked Up Caption', 'Has correct caption');
    });

    QUnit.test('getImageDataFromUUID returns null for unknown UUID', function(assert) {
      var data = manager.getImageDataFromUUID('unknown-uuid');

      assert.equal(data, null, 'Returns null for unknown UUID');
    });

    QUnit.test('getImageDataFromUUID uses default caption when empty', function(assert) {
      // Create card without caption
      var $cardNoCaption = $('<div class="journal-editor-multi-image-card" ' +
        'data-image-uuid="no-caption-uuid" ' +
        'data-image-url="/no-caption.jpg"></div>');
      $('#qunit-fixture').append($cardNoCaption);

      var data = manager.getImageDataFromUUID('no-caption-uuid');

      assert.equal(data.caption, 'Untitled', 'Uses default caption');

      $cardNoCaption.remove();
    });
  });

})();
