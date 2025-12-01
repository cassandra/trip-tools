/**
 * Unit Tests for Selection Utilities
 *
 * Tests selection-related utilities for the journal editor:
 * - getSelectionModifiers: Modifier key detection
 * - SelectionBadgeManager: Selection count badge UI
 * - ImageSelectionCoordinator: Selection state coordination
 * - ImageDataService: Image data lookup from picker cards
 *
 * Dependencies:
 * - Tt.JournalEditor.getSelectionModifiers
 * - Tt.JournalEditor.SelectionBadgeManager
 * - Tt.JournalEditor.ImageSelectionCoordinator
 * - Tt.JournalEditor.ImageDataService
 */

(function() {
  'use strict';

  var getSelectionModifiers = Tt.JournalEditor.getSelectionModifiers;
  var SelectionBadgeManager = Tt.JournalEditor.SelectionBadgeManager;
  var ImageSelectionCoordinator = Tt.JournalEditor.ImageSelectionCoordinator;
  var ImageDataService = Tt.JournalEditor.ImageDataService;

  // ===== getSelectionModifiers TESTS =====
  QUnit.module('getSelectionModifiers', function() {

    QUnit.test('detects Ctrl key', function(assert) {
      var event = { ctrlKey: true, metaKey: false, shiftKey: false };
      var modifiers = getSelectionModifiers(event);

      assert.ok(modifiers.isCtrlOrCmd, 'Ctrl detected as isCtrlOrCmd');
      assert.notOk(modifiers.isShift, 'Shift not detected');
    });

    QUnit.test('detects Meta (Cmd) key', function(assert) {
      var event = { ctrlKey: false, metaKey: true, shiftKey: false };
      var modifiers = getSelectionModifiers(event);

      assert.ok(modifiers.isCtrlOrCmd, 'Meta detected as isCtrlOrCmd');
      assert.notOk(modifiers.isShift, 'Shift not detected');
    });

    QUnit.test('detects Shift key', function(assert) {
      var event = { ctrlKey: false, metaKey: false, shiftKey: true };
      var modifiers = getSelectionModifiers(event);

      assert.notOk(modifiers.isCtrlOrCmd, 'Ctrl/Cmd not detected');
      assert.ok(modifiers.isShift, 'Shift detected');
    });

    QUnit.test('detects multiple modifiers', function(assert) {
      var event = { ctrlKey: true, metaKey: false, shiftKey: true };
      var modifiers = getSelectionModifiers(event);

      assert.ok(modifiers.isCtrlOrCmd, 'Ctrl detected');
      assert.ok(modifiers.isShift, 'Shift detected');
    });

    QUnit.test('no modifiers when none pressed', function(assert) {
      var event = { ctrlKey: false, metaKey: false, shiftKey: false };
      var modifiers = getSelectionModifiers(event);

      assert.notOk(modifiers.isCtrlOrCmd, 'No Ctrl/Cmd');
      assert.notOk(modifiers.isShift, 'No Shift');
    });
  });

  // ===== SelectionBadgeManager TESTS =====
  QUnit.module('SelectionBadgeManager', function(hooks) {
    var $referenceElement;
    var badgeManager;

    hooks.beforeEach(function() {
      $referenceElement = $('<h5>Panel Title</h5>');
      $('#qunit-fixture').append($referenceElement);
    });

    hooks.afterEach(function() {
      if (badgeManager) {
        badgeManager.remove();
      }
      $referenceElement.remove();
    });

    QUnit.test('constructor initializes with reference element and badge ID', function(assert) {
      badgeManager = new SelectionBadgeManager($referenceElement, 'test-badge-id');

      assert.equal(badgeManager.$referenceElement[0], $referenceElement[0], 'Reference element stored');
      assert.equal(badgeManager.badgeId, 'test-badge-id', 'Badge ID stored');
      assert.equal(badgeManager.$badge, null, 'Badge not created yet');
    });

    QUnit.test('update creates badge when count > 0', function(assert) {
      badgeManager = new SelectionBadgeManager($referenceElement, 'test-badge');

      badgeManager.update(5);

      assert.ok(badgeManager.$badge, 'Badge created');
      assert.equal(badgeManager.$badge.attr('id'), 'test-badge', 'Badge has correct ID');
      assert.ok(badgeManager.$badge.hasClass('badge'), 'Badge has badge class');
      assert.equal(badgeManager.$badge.text(), '5 selected', 'Badge shows correct count');
    });

    QUnit.test('update updates existing badge text', function(assert) {
      badgeManager = new SelectionBadgeManager($referenceElement, 'test-badge');

      badgeManager.update(3);
      assert.equal(badgeManager.$badge.text(), '3 selected', 'Initial count');

      badgeManager.update(10);
      assert.equal(badgeManager.$badge.text(), '10 selected', 'Updated count');
    });

    QUnit.test('update removes badge when count becomes 0', function(assert) {
      badgeManager = new SelectionBadgeManager($referenceElement, 'test-badge');

      badgeManager.update(5);
      assert.ok(badgeManager.$badge, 'Badge exists');

      badgeManager.update(0);
      assert.equal(badgeManager.$badge, null, 'Badge removed');
      assert.equal($('#test-badge').length, 0, 'Badge not in DOM');
    });

    QUnit.test('badge is inserted after reference element', function(assert) {
      badgeManager = new SelectionBadgeManager($referenceElement, 'test-badge');

      badgeManager.update(1);

      var $badge = $referenceElement.next();
      assert.equal($badge.attr('id'), 'test-badge', 'Badge is next sibling of reference');
    });

    QUnit.test('remove cleans up badge from DOM', function(assert) {
      badgeManager = new SelectionBadgeManager($referenceElement, 'test-badge');
      badgeManager.update(5);

      badgeManager.remove();

      assert.equal(badgeManager.$badge, null, 'Badge reference cleared');
      assert.equal($('#test-badge').length, 0, 'Badge not in DOM');
    });
  });

  // ===== ImageSelectionCoordinator TESTS =====
  QUnit.module('ImageSelectionCoordinator', function() {

    QUnit.test('constructor initializes with null callback', function(assert) {
      var coordinator = new ImageSelectionCoordinator();

      assert.equal(coordinator.pickerClearCallback, null, 'Callback is null initially');
    });

    QUnit.test('registerPicker stores callback', function(assert) {
      var coordinator = new ImageSelectionCoordinator();
      var clearFn = function() {};

      coordinator.registerPicker(clearFn);

      assert.equal(coordinator.pickerClearCallback, clearFn, 'Callback stored');
    });

    QUnit.test('notifyPickerSelection accepts boolean parameter', function(assert) {
      var coordinator = new ImageSelectionCoordinator();

      // Should not throw
      coordinator.notifyPickerSelection(true);
      coordinator.notifyPickerSelection(false);

      assert.ok(true, 'notifyPickerSelection accepts boolean without error');
    });
  });

  // ===== ImageDataService TESTS =====
  QUnit.module('ImageDataService', function(hooks) {
    var $pickerCard;

    hooks.beforeEach(function() {
      // Create mock picker card (no data-inspect-url - it's now built from UUID via Tt.buildImageInspectUrl)
      $pickerCard = $('<div class="journal-editor-multi-image-card" ' +
        'data-image-uuid="test-uuid-123">' +
        '<img src="/images/test.jpg" alt="Test Caption">' +
        '</div>');
      $('#qunit-fixture').append($pickerCard);
    });

    hooks.afterEach(function() {
      $pickerCard.remove();
    });

    QUnit.test('getImageDataByUUID returns null for missing UUID', function(assert) {
      var result = ImageDataService.getImageDataByUUID(null);

      assert.equal(result, null, 'Returns null for null UUID');
    });

    QUnit.test('getImageDataByUUID returns null for undefined UUID', function(assert) {
      var result = ImageDataService.getImageDataByUUID(undefined);

      assert.equal(result, null, 'Returns null for undefined UUID');
    });

    QUnit.test('getImageDataByUUID returns null for unknown UUID', function(assert) {
      var result = ImageDataService.getImageDataByUUID('unknown-uuid');

      assert.equal(result, null, 'Returns null for unknown UUID');
    });

    QUnit.test('getImageDataByUUID returns complete data object', function(assert) {
      var result = ImageDataService.getImageDataByUUID('test-uuid-123');

      assert.ok(result, 'Returns data object');
      assert.equal(result.uuid, 'test-uuid-123', 'UUID is correct');
      assert.equal(result.url, '/images/test.jpg', 'URL from img src');
      assert.equal(result.caption, 'Test Caption', 'Caption from img alt');
      // inspectUrl is now built from UUID via Tt.buildImageInspectUrl
      var expectedInspectUrl = Tt.buildImageInspectUrl('test-uuid-123');
      assert.equal(result.inspectUrl, expectedInspectUrl, 'Inspect URL built from UUID');
    });

    QUnit.test('getImageDataByUUID handles missing alt text', function(assert) {
      // Create card without alt text
      var $cardNoAlt = $('<div class="journal-editor-multi-image-card" ' +
        'data-image-uuid="no-alt-uuid">' +
        '<img src="/images/no-alt.jpg">' +
        '</div>');
      $('#qunit-fixture').append($cardNoAlt);

      var result = ImageDataService.getImageDataByUUID('no-alt-uuid');

      assert.ok(result, 'Returns data object');
      assert.equal(result.caption, '', 'Caption is empty string');

      $cardNoAlt.remove();
    });

    QUnit.test('getImageDataByUUID always generates inspectUrl from UUID', function(assert) {
      // inspectUrl is now built from UUID via Tt.buildImageInspectUrl, not from data attribute
      var $card = $('<div class="journal-editor-multi-image-card" ' +
        'data-image-uuid="another-uuid">' +
        '<img src="/images/test.jpg" alt="Caption">' +
        '</div>');
      $('#qunit-fixture').append($card);

      var result = ImageDataService.getImageDataByUUID('another-uuid');

      assert.ok(result, 'Returns data object');
      var expectedUrl = Tt.buildImageInspectUrl('another-uuid');
      assert.equal(result.inspectUrl, expectedUrl, 'Inspect URL built from UUID');

      $card.remove();
    });
  });

})();
