/**
 * Unit Tests for JournalEditorMultiImagePicker
 *
 * Tests image picker functionality for the journal editor:
 * - Single click selection toggle
 * - Ctrl/Cmd+click multi-select
 * - Shift+click range selection
 * - Selection clearing
 * - Filter application (unused/used/all)
 *
 * Dependencies:
 * - Tt.JournalEditor.JournalEditorMultiImagePicker
 * - Tt.JournalEditor.EDITOR_TRANSIENT
 */

(function() {
  'use strict';

  var JournalEditorMultiImagePicker = Tt.JournalEditor.JournalEditorMultiImagePicker;
  var EDITOR_TRANSIENT = Tt.JournalEditor.EDITOR_TRANSIENT;

  // ===== PICKER INITIALIZATION TESTS =====
  QUnit.module('JournalEditorMultiImagePicker.Init', function(hooks) {
    var $panel;
    var $headerTitle;
    var mockEditor;

    hooks.beforeEach(function() {
      // Create mock panel structure
      $panel = $('<div class="journal-editor-multi-image-panel">' +
        '<div class="journal-editor-multi-image-panel-header"><h5>Images</h5></div>' +
        '<div class="journal-editor-multi-image-gallery"></div>' +
        '</div>');
      $headerTitle = $panel.find('h5');
      $('#qunit-fixture').append($panel);

      // Create mock editor with usedImageUUIDs
      mockEditor = {
        usedImageUUIDs: new Map()
      };
    });

    hooks.afterEach(function() {
      $panel.remove();
    });

    QUnit.test('constructor initializes with panel and editor', function(assert) {
      var picker = new JournalEditorMultiImagePicker($panel, mockEditor);

      assert.ok(picker.$panel, 'Panel is stored');
      assert.ok(picker.editor, 'Editor is stored');
      assert.ok(picker.selectedImages instanceof Set, 'selectedImages is a Set');
      assert.equal(picker.selectedImages.size, 0, 'No images selected initially');
      assert.equal(picker.filterScope, 'unused', 'Default filter is unused');
    });

    QUnit.test('constructor initializes badge manager', function(assert) {
      var picker = new JournalEditorMultiImagePicker($panel, mockEditor);

      assert.ok(picker.badgeManager, 'Badge manager created');
    });
  });

  // ===== SELECTION TESTS =====
  QUnit.module('JournalEditorMultiImagePicker.Selection', function(hooks) {
    var $panel;
    var $cards;
    var mockEditor;
    var picker;

    hooks.beforeEach(function() {
      // Create mock panel with image cards
      $panel = $('<div class="journal-editor-multi-image-panel">' +
        '<div class="journal-editor-multi-image-panel-header"><h5>Images</h5></div>' +
        '<input type="radio" name="scope" value="unused" checked>' +
        '<input type="radio" name="scope" value="used">' +
        '<input type="radio" name="scope" value="all">' +
        '<div class="journal-editor-multi-image-gallery">' +
          '<div class="journal-editor-multi-image-card" data-image-uuid="uuid-1"></div>' +
          '<div class="journal-editor-multi-image-card" data-image-uuid="uuid-2"></div>' +
          '<div class="journal-editor-multi-image-card" data-image-uuid="uuid-3"></div>' +
        '</div>' +
        '</div>');
      $cards = $panel.find('.journal-editor-multi-image-card');
      $('#qunit-fixture').append($panel);

      mockEditor = {
        usedImageUUIDs: new Map()
      };

      picker = new JournalEditorMultiImagePicker($panel, mockEditor);
    });

    hooks.afterEach(function() {
      $panel.remove();
    });

    QUnit.test('toggleSelection adds UUID to selectedImages', function(assert) {
      var $card = $cards.first();
      var uuid = $card.data('image-uuid');

      picker.toggleSelection($card, uuid);

      assert.ok(picker.selectedImages.has(uuid), 'UUID added to selection');
      assert.ok($card.hasClass(EDITOR_TRANSIENT.CSS_SELECTED), 'Card has selected class');
    });

    QUnit.test('toggleSelection removes UUID if already selected', function(assert) {
      var $card = $cards.first();
      var uuid = $card.data('image-uuid');

      // Select first
      picker.toggleSelection($card, uuid);
      assert.ok(picker.selectedImages.has(uuid), 'UUID added');

      // Toggle again - should remove
      picker.toggleSelection($card, uuid);
      assert.notOk(picker.selectedImages.has(uuid), 'UUID removed');
      assert.notOk($card.hasClass(EDITOR_TRANSIENT.CSS_SELECTED), 'Selected class removed');
    });

    QUnit.test('clearAllSelections clears Set and removes CSS', function(assert) {
      // Select multiple cards
      $cards.each(function() {
        var $card = $(this);
        var uuid = $card.data('image-uuid');
        picker.selectedImages.add(uuid);
        $card.addClass(EDITOR_TRANSIENT.CSS_SELECTED);
      });

      assert.equal(picker.selectedImages.size, 3, 'All selected');

      picker.clearAllSelections();

      assert.equal(picker.selectedImages.size, 0, 'All cleared from Set');
      $cards.each(function() {
        assert.notOk($(this).hasClass(EDITOR_TRANSIENT.CSS_SELECTED), 'CSS removed');
      });
      assert.equal(picker.lastSelectedIndex, null, 'Last selected index reset');
    });

    QUnit.test('handleRangeSelection selects range of cards', function(assert) {
      // First, select the first card to establish lastSelectedIndex
      var $firstCard = $cards.eq(0);
      picker.toggleSelection($firstCard, $firstCard.data('image-uuid'));
      picker.lastSelectedIndex = 0;

      // Now shift-click the third card
      var $thirdCard = $cards.eq(2);
      picker.handleRangeSelection($thirdCard);

      // All three cards should be selected
      assert.ok(picker.selectedImages.has('uuid-1'), 'First card selected');
      assert.ok(picker.selectedImages.has('uuid-2'), 'Second card selected');
      assert.ok(picker.selectedImages.has('uuid-3'), 'Third card selected');
    });
  });

  // ===== FILTER TESTS =====
  QUnit.module('JournalEditorMultiImagePicker.Filter', function(hooks) {
    var $panel;
    var $cards;
    var mockEditor;
    var picker;

    hooks.beforeEach(function() {
      $panel = $('<div class="journal-editor-multi-image-panel">' +
        '<div class="journal-editor-multi-image-panel-header"><h5>Images</h5></div>' +
        '<div class="journal-editor-multi-image-gallery">' +
          '<div class="journal-editor-multi-image-card" data-image-uuid="used-1"></div>' +
          '<div class="journal-editor-multi-image-card" data-image-uuid="used-2"></div>' +
          '<div class="journal-editor-multi-image-card" data-image-uuid="unused-1"></div>' +
          '<div class="journal-editor-multi-image-card" data-image-uuid="unused-2"></div>' +
        '</div>' +
        '</div>');
      $cards = $panel.find('.journal-editor-multi-image-card');
      $('#qunit-fixture').append($panel);

      // Mock editor with some used images
      mockEditor = {
        usedImageUUIDs: new Map([
          ['used-1', 1],
          ['used-2', 2]
        ])
      };

      picker = new JournalEditorMultiImagePicker($panel, mockEditor);
    });

    hooks.afterEach(function() {
      $panel.remove();
    });

    QUnit.test('applyFilter "all" shows all images', function(assert) {
      picker.applyFilter('all');

      $cards.each(function() {
        assert.ok($(this).is(':visible'), 'Card is visible');
      });
    });

    QUnit.test('applyFilter "unused" hides used images', function(assert) {
      picker.applyFilter('unused');

      assert.notOk($cards.eq(0).is(':visible'), 'used-1 hidden');
      assert.notOk($cards.eq(1).is(':visible'), 'used-2 hidden');
      assert.ok($cards.eq(2).is(':visible'), 'unused-1 visible');
      assert.ok($cards.eq(3).is(':visible'), 'unused-2 visible');
    });

    QUnit.test('applyFilter "used" hides unused images', function(assert) {
      picker.applyFilter('used');

      assert.ok($cards.eq(0).is(':visible'), 'used-1 visible');
      assert.ok($cards.eq(1).is(':visible'), 'used-2 visible');
      assert.notOk($cards.eq(2).is(':visible'), 'unused-1 hidden');
      assert.notOk($cards.eq(3).is(':visible'), 'unused-2 hidden');
    });

    QUnit.test('applyFilter updates filterScope', function(assert) {
      assert.equal(picker.filterScope, 'unused', 'Initial filter');

      picker.applyFilter('all');
      assert.equal(picker.filterScope, 'all', 'Filter updated to all');

      picker.applyFilter('used');
      assert.equal(picker.filterScope, 'used', 'Filter updated to used');
    });
  });

  // ===== SELECTION UI TESTS =====
  QUnit.module('JournalEditorMultiImagePicker.SelectionUI', function(hooks) {
    var $panel;
    var mockEditor;
    var picker;

    hooks.beforeEach(function() {
      $panel = $('<div class="journal-editor-multi-image-panel">' +
        '<div class="journal-editor-multi-image-panel-header"><h5>Images</h5></div>' +
        '<div class="journal-editor-multi-image-gallery">' +
          '<div class="journal-editor-multi-image-card" data-image-uuid="uuid-1"></div>' +
        '</div>' +
        '</div>');
      $('#qunit-fixture').append($panel);

      mockEditor = {
        usedImageUUIDs: new Map()
      };

      picker = new JournalEditorMultiImagePicker($panel, mockEditor);
    });

    hooks.afterEach(function() {
      $panel.remove();
    });

    QUnit.test('updateSelectionUI updates badge count', function(assert) {
      // Add some selections
      picker.selectedImages.add('uuid-1');
      picker.selectedImages.add('uuid-2');

      picker.updateSelectionUI();

      // Check badge exists and has correct text
      var $badge = $panel.find('#selected-images-count');
      assert.equal($badge.length, 1, 'Badge exists');
      assert.equal($badge.text(), '2 selected', 'Badge shows correct count');
    });

    QUnit.test('updateSelectionUI removes badge when count is 0', function(assert) {
      // First add some and update
      picker.selectedImages.add('uuid-1');
      picker.updateSelectionUI();
      assert.equal($panel.find('#selected-images-count').length, 1, 'Badge exists');

      // Now clear and update
      picker.selectedImages.clear();
      picker.updateSelectionUI();

      assert.equal($panel.find('#selected-images-count').length, 0, 'Badge removed');
    });
  });

})();
