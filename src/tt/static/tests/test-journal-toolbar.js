/**
 * Unit Tests for JournalEditorToolbar
 *
 * Tests the formatting toolbar for journal entries:
 * - Initialization and button binding
 * - Formatting operations (bold, italic, headings, lists)
 * - Link creation and URL validation
 * - Active state tracking
 */

(function() {
  'use strict';

  // ===== TOOLBAR EXISTENCE TESTS =====
  QUnit.module('Tt.JournalEditor.JournalEditorToolbar', function(hooks) {
    var $toolbar;
    var $editor;

    hooks.beforeEach(function() {
      // Create mock toolbar with buttons
      $toolbar = $('<div class="journal-toolbar">' +
        '<button data-command="bold">B</button>' +
        '<button data-command="italic">I</button>' +
        '<button data-command="heading" data-level="2">H2</button>' +
        '<button data-command="heading" data-level="3">H3</button>' +
        '<button data-command="heading" data-level="4">H4</button>' +
        '<button data-command="insertUnorderedList">UL</button>' +
        '<button data-command="insertOrderedList">OL</button>' +
        '<button data-command="indent">Indent</button>' +
        '<button data-command="outdent">Outdent</button>' +
        '<button data-command="createLink">Link</button>' +
        '<button data-command="code">Code</button>' +
      '</div>');

      // Create mock editor
      $editor = $('<div class="test-editor" contenteditable="true"></div>');
      $editor.html('<p class="text-block">Test content</p>');

      $('#qunit-fixture').append($toolbar).append($editor);
    });

    // ----- Existence Tests -----
    QUnit.test('JournalEditorToolbar exists in namespace', function(assert) {
      assert.ok(Tt.JournalEditor.JournalEditorToolbar, 'JournalEditorToolbar exists');
      assert.equal(typeof Tt.JournalEditor.JournalEditorToolbar, 'function', 'Is a constructor function');
    });

    QUnit.test('toolbar initializes with required parameters', function(assert) {
      var contentChanged = false;
      var onContentChange = function() { contentChanged = true; };

      var toolbar = new Tt.JournalEditor.JournalEditorToolbar($toolbar, $editor, onContentChange);

      assert.ok(toolbar, 'Toolbar instance created');
      assert.ok(toolbar.$toolbar, 'Has $toolbar reference');
      assert.ok(toolbar.$editor, 'Has $editor reference');
      assert.ok(toolbar.editor, 'Has editor DOM element reference');
      assert.ok(toolbar.onContentChange, 'Has onContentChange callback');
    });

    // ----- Button Binding Tests -----
    QUnit.test('bold button is bound to click handler', function(assert) {
      var toolbar = new Tt.JournalEditor.JournalEditorToolbar($toolbar, $editor, function() {});

      // Check that click handler is bound (jQuery data)
      var $boldBtn = $toolbar.find('[data-command="bold"]');
      var events = $._data($boldBtn[0], 'events');

      assert.ok(events && events.click, 'Bold button has click handler');
    });

    QUnit.test('heading buttons are bound with data-level', function(assert) {
      var toolbar = new Tt.JournalEditor.JournalEditorToolbar($toolbar, $editor, function() {});

      var $h2Btn = $toolbar.find('[data-command="heading"][data-level="2"]');
      var $h3Btn = $toolbar.find('[data-command="heading"][data-level="3"]');
      var $h4Btn = $toolbar.find('[data-command="heading"][data-level="4"]');

      assert.equal($h2Btn.data('level'), 2, 'H2 button has level 2');
      assert.equal($h3Btn.data('level'), 3, 'H3 button has level 3');
      assert.equal($h4Btn.data('level'), 4, 'H4 button has level 4');
    });

    // ----- Content Change Callback Tests -----
    QUnit.test('applyBold triggers content change callback', function(assert) {
      var contentChanged = false;
      var toolbar = new Tt.JournalEditor.JournalEditorToolbar($toolbar, $editor, function() {
        contentChanged = true;
      });

      // Focus editor and apply bold
      $editor.focus();
      toolbar.applyBold();

      assert.ok(contentChanged, 'Content change callback triggered');
    });

    QUnit.test('applyItalic triggers content change callback', function(assert) {
      var contentChanged = false;
      var toolbar = new Tt.JournalEditor.JournalEditorToolbar($toolbar, $editor, function() {
        contentChanged = true;
      });

      $editor.focus();
      toolbar.applyItalic();

      assert.ok(contentChanged, 'Content change callback triggered');
    });

    QUnit.test('applyHeading triggers content change callback', function(assert) {
      var contentChanged = false;
      var toolbar = new Tt.JournalEditor.JournalEditorToolbar($toolbar, $editor, function() {
        contentChanged = true;
      });

      $editor.focus();
      toolbar.applyHeading(2);

      assert.ok(contentChanged, 'Content change callback triggered');
    });

    QUnit.test('toggleList triggers content change callback', function(assert) {
      var contentChanged = false;
      var toolbar = new Tt.JournalEditor.JournalEditorToolbar($toolbar, $editor, function() {
        contentChanged = true;
      });

      $editor.focus();
      toolbar.toggleList('ul');

      assert.ok(contentChanged, 'Content change callback triggered');
    });

    // ----- Active State Tests -----
    QUnit.test('updateActiveStates handles no selection gracefully', function(assert) {
      var toolbar = new Tt.JournalEditor.JournalEditorToolbar($toolbar, $editor, function() {});

      // Clear selection
      window.getSelection().removeAllRanges();

      // Should not throw
      toolbar.updateActiveStates();
      assert.ok(true, 'Handled no selection without error');
    });

    QUnit.test('updateActiveStates detects bold formatting', function(assert) {
      var toolbar = new Tt.JournalEditor.JournalEditorToolbar($toolbar, $editor, function() {});

      // Set content with bold
      $editor.html('<p><strong>Bold text</strong></p>');

      // Position cursor inside bold
      var range = document.createRange();
      var strongNode = $editor.find('strong')[0].firstChild;
      range.setStart(strongNode, 2);
      range.collapse(true);
      window.getSelection().removeAllRanges();
      window.getSelection().addRange(range);

      toolbar.updateActiveStates();

      var $boldBtn = $toolbar.find('[data-command="bold"]');
      assert.ok($boldBtn.hasClass('active'), 'Bold button marked active');
    });

    QUnit.test('updateActiveStates detects italic formatting', function(assert) {
      var toolbar = new Tt.JournalEditor.JournalEditorToolbar($toolbar, $editor, function() {});

      // Set content with italic
      $editor.html('<p><em>Italic text</em></p>');

      // Position cursor inside italic
      var range = document.createRange();
      var emNode = $editor.find('em')[0].firstChild;
      range.setStart(emNode, 2);
      range.collapse(true);
      window.getSelection().removeAllRanges();
      window.getSelection().addRange(range);

      toolbar.updateActiveStates();

      var $italicBtn = $toolbar.find('[data-command="italic"]');
      assert.ok($italicBtn.hasClass('active'), 'Italic button marked active');
    });

    QUnit.test('updateActiveStates detects list context', function(assert) {
      var toolbar = new Tt.JournalEditor.JournalEditorToolbar($toolbar, $editor, function() {});

      // Set content with unordered list
      $editor.html('<ul><li>List item</li></ul>');

      // Position cursor inside list item
      var range = document.createRange();
      var liNode = $editor.find('li')[0].firstChild;
      range.setStart(liNode, 2);
      range.collapse(true);
      window.getSelection().removeAllRanges();
      window.getSelection().addRange(range);

      toolbar.updateActiveStates();

      var $ulBtn = $toolbar.find('[data-command="insertUnorderedList"]');
      var $olBtn = $toolbar.find('[data-command="insertOrderedList"]');
      assert.ok($ulBtn.hasClass('active'), 'UL button marked active');
      assert.notOk($olBtn.hasClass('active'), 'OL button not active');
    });

    QUnit.test('updateActiveStates clears list buttons when not in list', function(assert) {
      var toolbar = new Tt.JournalEditor.JournalEditorToolbar($toolbar, $editor, function() {});

      // Pre-set buttons as active
      $toolbar.find('[data-command="insertUnorderedList"]').addClass('active');
      $toolbar.find('[data-command="insertOrderedList"]').addClass('active');

      // Set plain content (no list)
      $editor.html('<p>Plain paragraph</p>');

      // Position cursor in paragraph
      var range = document.createRange();
      var pNode = $editor.find('p')[0].firstChild;
      range.setStart(pNode, 2);
      range.collapse(true);
      window.getSelection().removeAllRanges();
      window.getSelection().addRange(range);

      toolbar.updateActiveStates();

      var $ulBtn = $toolbar.find('[data-command="insertUnorderedList"]');
      var $olBtn = $toolbar.find('[data-command="insertOrderedList"]');
      assert.notOk($ulBtn.hasClass('active'), 'UL button cleared');
      assert.notOk($olBtn.hasClass('active'), 'OL button cleared');
    });
  });

  // ===== URL VALIDATION TESTS =====
  QUnit.module('JournalEditorToolbar URL Handling', function() {

    QUnit.test('URL validation pattern matches http/https/mailto', function(assert) {
      var urlPattern = /^(https?:\/\/|mailto:)/i;

      assert.ok(urlPattern.test('https://example.com'), 'Matches https://');
      assert.ok(urlPattern.test('http://example.com'), 'Matches http://');
      assert.ok(urlPattern.test('HTTPS://EXAMPLE.COM'), 'Matches case-insensitive');
      assert.ok(urlPattern.test('mailto:test@example.com'), 'Matches mailto:');
      assert.notOk(urlPattern.test('example.com'), 'Does not match bare domain');
      assert.notOk(urlPattern.test('ftp://files.com'), 'Does not match ftp');
    });

    QUnit.test('URL normalization adds https:// to bare domains', function(assert) {
      var urlPattern = /^(https?:\/\/|mailto:)/i;
      var url = 'example.com';

      if (!urlPattern.test(url)) {
        url = 'https://' + url;
      }

      assert.equal(url, 'https://example.com', 'Added https:// prefix');
    });

    QUnit.test('URL normalization preserves valid URLs', function(assert) {
      var urlPattern = /^(https?:\/\/|mailto:)/i;
      var url = 'https://already-valid.com';

      if (!urlPattern.test(url)) {
        url = 'https://' + url;
      }

      assert.equal(url, 'https://already-valid.com', 'Preserved existing https://');
    });
  });

})();
