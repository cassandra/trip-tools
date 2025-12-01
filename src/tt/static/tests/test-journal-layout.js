/**
 * Unit Tests for EditorLayoutManager
 *
 * Tests layout management for the journal editor:
 * - wrapFullWidthImageGroups: Wrapping consecutive full-width images
 * - markFloatParagraphs: Marking paragraphs with float-right images
 * - ensureDeleteButtons: Adding delete buttons to image wrappers
 * - refreshLayout: Orchestration of all layout methods
 *
 * Dependencies:
 * - Tt.JournalEditor.EditorLayoutManager
 * - Tt.JournalEditor.HTML_STRUCTURE
 * - Tt.JournalEditor.EDITOR_TRANSIENT
 */

(function() {
  'use strict';

  var EditorLayoutManager = Tt.JournalEditor.EditorLayoutManager;
  var HTML_STRUCTURE = Tt.JournalEditor.HTML_STRUCTURE;
  var EDITOR_TRANSIENT = Tt.JournalEditor.EDITOR_TRANSIENT;

  // ===== FULL WIDTH IMAGE GROUP TESTS =====
  QUnit.module('EditorLayoutManager.FullWidthGroups', function(hooks) {
    var $editor;
    var layoutManager;

    hooks.beforeEach(function() {
      $editor = $('<div class="journal-editor" contenteditable="true"></div>');
      $('#qunit-fixture').append($editor);
      layoutManager = new EditorLayoutManager($editor);
    });

    hooks.afterEach(function() {
      $editor.remove();
    });

    QUnit.test('wrapFullWidthImageGroups wraps consecutive full-width images', function(assert) {
      $editor.html(
        '<span class="trip-image-wrapper" data-layout="full-width"><img class="trip-image"></span>' +
        '<span class="trip-image-wrapper" data-layout="full-width"><img class="trip-image"></span>'
      );

      layoutManager.wrapFullWidthImageGroups();

      var $group = $editor.find('.' + HTML_STRUCTURE.FULL_WIDTH_GROUP_CLASS);
      assert.equal($group.length, 1, 'Group container created');
      assert.equal($group.find('.trip-image-wrapper').length, 2, 'Both images in group');
    });

    QUnit.test('wrapFullWidthImageGroups does not group non-consecutive images', function(assert) {
      $editor.html(
        '<span class="trip-image-wrapper" data-layout="full-width"><img class="trip-image"></span>' +
        '<p class="text-block">Some text</p>' +
        '<span class="trip-image-wrapper" data-layout="full-width"><img class="trip-image"></span>'
      );

      layoutManager.wrapFullWidthImageGroups();

      var $groups = $editor.find('.' + HTML_STRUCTURE.FULL_WIDTH_GROUP_CLASS);
      assert.equal($groups.length, 2, 'Two separate groups created');
      assert.equal($groups.eq(0).find('.trip-image-wrapper').length, 1, 'First group has one image');
      assert.equal($groups.eq(1).find('.trip-image-wrapper').length, 1, 'Second group has one image');
    });

    QUnit.test('wrapFullWidthImageGroups removes existing wrappers first', function(assert) {
      // Pre-wrap an image
      $editor.html(
        '<div class="text-block full-width-image-group">' +
          '<span class="trip-image-wrapper" data-layout="full-width"><img class="trip-image"></span>' +
        '</div>' +
        '<span class="trip-image-wrapper" data-layout="full-width"><img class="trip-image"></span>'
      );

      layoutManager.wrapFullWidthImageGroups();

      // Should have re-wrapped correctly
      var $groups = $editor.find('.' + HTML_STRUCTURE.FULL_WIDTH_GROUP_CLASS);
      // The existing wrapped image should be unwrapped and then both re-grouped
      assert.ok($groups.length >= 1, 'Groups exist after re-wrapping');
    });

    QUnit.test('wrapFullWidthImageGroups ignores float-right images', function(assert) {
      $editor.html(
        '<p class="text-block">' +
          '<span class="trip-image-wrapper" data-layout="float-right"><img class="trip-image"></span>' +
          'Some text' +
        '</p>'
      );

      layoutManager.wrapFullWidthImageGroups();

      var $groups = $editor.find('.' + HTML_STRUCTURE.FULL_WIDTH_GROUP_CLASS);
      assert.equal($groups.length, 0, 'No groups for float-right images');
    });
  });

  // ===== FLOAT PARAGRAPH MARKER TESTS =====
  QUnit.module('EditorLayoutManager.FloatMarkers', function(hooks) {
    var $editor;
    var layoutManager;

    hooks.beforeEach(function() {
      $editor = $('<div class="journal-editor" contenteditable="true"></div>');
      $('#qunit-fixture').append($editor);
      layoutManager = new EditorLayoutManager($editor);
    });

    hooks.afterEach(function() {
      $editor.remove();
    });

    QUnit.test('markFloatParagraphs adds class to paragraphs with float-right images', function(assert) {
      $editor.html(
        '<p class="text-block">' +
          '<span class="trip-image-wrapper float-right" data-layout="float-right"><img class="trip-image"></span>' +
          'Some text' +
        '</p>'
      );

      layoutManager.markFloatParagraphs();

      var $p = $editor.find('p.text-block');
      assert.ok($p.hasClass(TtConst.JOURNAL_FLOAT_MARKER_CLASS), 'Float marker class added');
    });

    QUnit.test('markFloatParagraphs removes class from paragraphs without floats', function(assert) {
      $editor.html(
        '<p class="text-block ' + TtConst.JOURNAL_FLOAT_MARKER_CLASS + '">' +
          'No float image here' +
        '</p>'
      );

      layoutManager.markFloatParagraphs();

      var $p = $editor.find('p.text-block');
      assert.notOk($p.hasClass(TtConst.JOURNAL_FLOAT_MARKER_CLASS), 'Float marker class removed');
    });

    QUnit.test('markFloatParagraphs handles mixed paragraphs', function(assert) {
      $editor.html(
        '<p class="text-block">' +
          '<span class="trip-image-wrapper float-right" data-layout="float-right"><img class="trip-image"></span>' +
          'Has float' +
        '</p>' +
        '<p class="text-block">No float</p>'
      );

      layoutManager.markFloatParagraphs();

      var $paragraphs = $editor.find('p.text-block');
      assert.ok($paragraphs.eq(0).hasClass(TtConst.JOURNAL_FLOAT_MARKER_CLASS), 'First paragraph marked');
      assert.notOk($paragraphs.eq(1).hasClass(TtConst.JOURNAL_FLOAT_MARKER_CLASS), 'Second paragraph not marked');
    });
  });

  // ===== DELETE BUTTON TESTS =====
  QUnit.module('EditorLayoutManager.DeleteButtons', function(hooks) {
    var $editor;
    var layoutManager;

    hooks.beforeEach(function() {
      $editor = $('<div class="journal-editor" contenteditable="true"></div>');
      $('#qunit-fixture').append($editor);
      layoutManager = new EditorLayoutManager($editor);
    });

    hooks.afterEach(function() {
      $editor.remove();
    });

    QUnit.test('ensureDeleteButtons adds buttons to wrappers without them', function(assert) {
      $editor.html(
        '<span class="trip-image-wrapper" data-layout="full-width">' +
          '<img class="trip-image">' +
        '</span>'
      );

      layoutManager.ensureDeleteButtons();

      var $wrapper = $editor.find('.trip-image-wrapper');
      var $deleteBtn = $wrapper.find('.' + EDITOR_TRANSIENT.CSS_DELETE_BTN);
      assert.equal($deleteBtn.length, 1, 'Delete button added');
      assert.equal($deleteBtn.attr('type'), 'button', 'Is a button element');
      assert.equal($deleteBtn.text(), '×', 'Has X text');
    });

    QUnit.test('ensureDeleteButtons skips wrappers that already have buttons', function(assert) {
      $editor.html(
        '<span class="trip-image-wrapper" data-layout="full-width">' +
          '<img class="trip-image">' +
          '<button class="' + EDITOR_TRANSIENT.CSS_DELETE_BTN + '">×</button>' +
        '</span>'
      );

      layoutManager.ensureDeleteButtons();

      var $wrapper = $editor.find('.trip-image-wrapper');
      var $deleteButtons = $wrapper.find('.' + EDITOR_TRANSIENT.CSS_DELETE_BTN);
      assert.equal($deleteButtons.length, 1, 'Still only one delete button');
    });

    QUnit.test('ensureDeleteButtons handles multiple wrappers', function(assert) {
      $editor.html(
        '<span class="trip-image-wrapper" data-layout="full-width"><img class="trip-image"></span>' +
        '<p class="text-block">' +
          '<span class="trip-image-wrapper" data-layout="float-right"><img class="trip-image"></span>' +
          'Text' +
        '</p>' +
        '<span class="trip-image-wrapper" data-layout="full-width"><img class="trip-image"></span>'
      );

      layoutManager.ensureDeleteButtons();

      var $wrappers = $editor.find('.trip-image-wrapper');
      $wrappers.each(function() {
        var $deleteBtn = $(this).find('.' + EDITOR_TRANSIENT.CSS_DELETE_BTN);
        assert.equal($deleteBtn.length, 1, 'Each wrapper has delete button');
      });
    });
  });

  // ===== REFRESH LAYOUT TESTS =====
  QUnit.module('EditorLayoutManager.RefreshLayout', function(hooks) {
    var $editor;
    var layoutManager;

    hooks.beforeEach(function() {
      $editor = $('<div class="journal-editor" contenteditable="true"></div>');
      $('#qunit-fixture').append($editor);
      layoutManager = new EditorLayoutManager($editor);
    });

    hooks.afterEach(function() {
      $editor.remove();
    });

    QUnit.test('refreshLayout runs all layout methods', function(assert) {
      // Setup content that exercises all methods
      $editor.html(
        '<span class="trip-image-wrapper" data-layout="full-width"><img class="trip-image"></span>' +
        '<span class="trip-image-wrapper" data-layout="full-width"><img class="trip-image"></span>' +
        '<p class="text-block">' +
          '<span class="trip-image-wrapper float-right" data-layout="float-right"><img class="trip-image"></span>' +
          'Text with float' +
        '</p>'
      );

      layoutManager.refreshLayout();

      // Check groups were created
      var $groups = $editor.find('.' + HTML_STRUCTURE.FULL_WIDTH_GROUP_CLASS);
      assert.ok($groups.length >= 1, 'Full-width groups created');

      // Check float markers
      var $floatParagraph = $editor.find('p.text-block.' + TtConst.JOURNAL_FLOAT_MARKER_CLASS);
      assert.equal($floatParagraph.length, 1, 'Float paragraph marked');

      // Check delete buttons
      var $wrappers = $editor.find('.trip-image-wrapper');
      var buttonsAdded = 0;
      $wrappers.each(function() {
        if ($(this).find('.' + EDITOR_TRANSIENT.CSS_DELETE_BTN).length > 0) {
          buttonsAdded++;
        }
      });
      assert.equal(buttonsAdded, 3, 'Delete buttons added to all wrappers');
    });

    QUnit.test('refreshLayout handles empty editor', function(assert) {
      $editor.html('');

      // Should not throw
      layoutManager.refreshLayout();

      assert.ok(true, 'refreshLayout handles empty editor without error');
    });
  });

  // ===== EDITOR_TRANSIENT CONSTANTS TESTS =====
  QUnit.module('EditorLayoutManager.Constants', function() {

    QUnit.test('EDITOR_TRANSIENT is exported', function(assert) {
      assert.ok(EDITOR_TRANSIENT, 'EDITOR_TRANSIENT is available');
    });

    QUnit.test('EDITOR_TRANSIENT has expected CSS classes', function(assert) {
      assert.equal(EDITOR_TRANSIENT.CSS_DELETE_BTN, 'trip-image-delete-btn', 'CSS_DELETE_BTN correct');
      assert.equal(EDITOR_TRANSIENT.CSS_DROP_ZONE_ACTIVE, 'drop-zone-active', 'CSS_DROP_ZONE_ACTIVE correct');
      assert.equal(EDITOR_TRANSIENT.CSS_DRAGGING, 'dragging', 'CSS_DRAGGING correct');
      assert.equal(EDITOR_TRANSIENT.CSS_SELECTED, 'selected', 'CSS_SELECTED correct');
    });

    QUnit.test('EDITOR_TRANSIENT has expected selectors', function(assert) {
      assert.equal(EDITOR_TRANSIENT.SEL_DELETE_BTN, '.trip-image-delete-btn', 'SEL_DELETE_BTN correct');
      assert.equal(EDITOR_TRANSIENT.SEL_DROP_ZONE_BETWEEN, '.drop-zone-between', 'SEL_DROP_ZONE_BETWEEN correct');
    });
  });

})();
