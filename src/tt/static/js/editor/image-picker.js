/**
 * JournalEditorMultiImagePicker
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
 *
 * Dependencies:
 * - jQuery
 * - TtConst (from main.js)
 * - AN (antinode, for modal display)
 * - Tt.JournalEditor.SelectionBadgeManager (from selection-utils.js)
 * - Tt.JournalEditor.getSelectionModifiers (from selection-utils.js)
 * - Tt.JournalEditor.imageSelectionCoordinator (from selection-utils.js)
 * - Tt.JournalEditor.EDITOR_TRANSIENT (from layout-manager.js)
 *
 * Usage:
 *   var picker = new Tt.JournalEditor.JournalEditorMultiImagePicker($panel, editor);
 *   picker.applyFilter('unused');
 */

(function($) {
  'use strict';

  // =========================================================================
  // Dependencies from other modules
  // =========================================================================
  var SelectionBadgeManager = Tt.JournalEditor.SelectionBadgeManager;
  var getSelectionModifiers = Tt.JournalEditor.getSelectionModifiers;
  var imageSelectionCoordinator = Tt.JournalEditor.imageSelectionCoordinator;
  var EDITOR_TRANSIENT = Tt.JournalEditor.EDITOR_TRANSIENT;

  // =========================================================================
  // JournalEditorMultiImagePicker
  // =========================================================================

  /**
   * JournalEditorMultiImagePicker
   *
   * Manages image selection in the journal image picker panel.
   *
   * @param {jQuery} $panel - The picker panel container
   * @param {Object} editor - JournalEditor instance with usedImageUUIDs Map
   */
  function JournalEditorMultiImagePicker($panel, editor) {
    this.$panel = $panel;
    this.editor = editor; // Reference to JournalEditor for usedImageUUIDs
    this.selectedImages = new Set();
    this.lastSelectedIndex = null;

    // Initialize filter scope from server-provided data attribute (for URL state preservation)
    var $form = this.$panel.find('#' + TtConst.JOURNAL_EDITOR_MULTI_IMAGE_FILTER_FORM_ID);
    this.filterScope = $form.data(TtConst.INITIAL_SCOPE_DATA_ATTR) || TtConst.IMAGE_PICKER_SCOPE_UNUSED;

    // Initialize badge manager
    var $headerTitle = this.$panel.find(TtConst.JOURNAL_EDITOR_MULTI_IMAGE_PANEL_HEADER_SELECTOR + ' h5');
    this.badgeManager = new SelectionBadgeManager($headerTitle, 'selected-images-count');

    // Register with coordinator
    imageSelectionCoordinator.registerPicker(this.clearAllSelections.bind(this));

    this.init();
  }

  /**
   * Initialize image picker event handlers
   */
  JournalEditorMultiImagePicker.prototype.init = function() {
    var self = this;

    // Click handler for image selection
    $(document).on('click', TtConst.JOURNAL_EDITOR_MULTI_IMAGE_CARD_SELECTOR, function(e) {
      e.preventDefault();
      self.handleImageClick(this, e);
    });

    // Double-click handler for opening inspector modal
    $(document).on('dblclick', TtConst.JOURNAL_EDITOR_MULTI_IMAGE_CARD_SELECTOR, function(e) {
      e.preventDefault();
      self.handleImageDoubleClick(this);
    });

    // Radio button change handler for filtering
    this.$panel.find('input[name="scope"]').on('change', function(e) {
      var newScope = $(this).val();
      self.applyFilter(newScope);

      // Update URL to preserve scope across page refreshes
      if (Tt.JournalEditor.updatePickerUrlState) {
        var $dateInput = self.$panel.find('#' + TtConst.JOURNAL_EDITOR_MULTI_IMAGE_DATE_INPUT_ID);
        var dateValue = $dateInput.val();
        Tt.JournalEditor.updatePickerUrlState({
          date: dateValue || null,
          recent: !dateValue,
          scope: newScope
        });
      }
    });

    // NOTE: Initial filter is applied by JournalEditor.init() after usedImageUUIDs is populated
  };

  /**
   * Handle image card click with modifier key support
   */
  JournalEditorMultiImagePicker.prototype.handleImageClick = function(card, event) {
    var $card = $(card);
    var uuid = $card.data(TtConst.IMAGE_UUID_DATA_ATTR);
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
  JournalEditorMultiImagePicker.prototype.handleRangeSelection = function($clickedCard) {
    var $allCards = $(TtConst.JOURNAL_EDITOR_MULTI_IMAGE_CARD_SELECTOR + ':visible');
    var clickedIndex = $allCards.index($clickedCard);
    var startIndex = Math.min(this.lastSelectedIndex, clickedIndex);
    var endIndex = Math.max(this.lastSelectedIndex, clickedIndex);

    for (var i = startIndex; i <= endIndex; i++) {
      var $card = $allCards.eq(i);
      var uuid = $card.data(TtConst.IMAGE_UUID_DATA_ATTR);
      this.selectedImages.add(uuid);
      $card.addClass(EDITOR_TRANSIENT.CSS_SELECTED);
    }
  };

  /**
   * Toggle selection state for a single image
   */
  JournalEditorMultiImagePicker.prototype.toggleSelection = function($card, uuid) {
    if (this.selectedImages.has(uuid)) {
      this.selectedImages.delete(uuid);
      $card.removeClass(EDITOR_TRANSIENT.CSS_SELECTED);
    } else {
      this.selectedImages.add(uuid);
      $card.addClass(EDITOR_TRANSIENT.CSS_SELECTED);
    }

    var $allCards = $(TtConst.JOURNAL_EDITOR_MULTI_IMAGE_CARD_SELECTOR + ':visible');
    this.lastSelectedIndex = $allCards.index($card);
  };

  /**
   * Clear all selections
   */
  JournalEditorMultiImagePicker.prototype.clearAllSelections = function() {
    this.selectedImages.clear();
    $(TtConst.JOURNAL_EDITOR_MULTI_IMAGE_CARD_SELECTOR).removeClass(EDITOR_TRANSIENT.CSS_SELECTED);
    this.lastSelectedIndex = null;
  };

  /**
   * Update selection count badge UI
   */
  JournalEditorMultiImagePicker.prototype.updateSelectionUI = function() {
    var count = this.selectedImages.size;
    this.badgeManager.update(count);

    // Notify coordinator when selections change
    imageSelectionCoordinator.notifyPickerSelection(count > 0);
  };

  /**
   * Handle double-click to open Image Inspector modal
   */
  JournalEditorMultiImagePicker.prototype.handleImageDoubleClick = function(card) {
    var $card = $(card);
    var uuid = $card.data(TtConst.IMAGE_UUID_DATA_ATTR);

    if (uuid && typeof AN !== 'undefined' && AN.get) {
      var inspectUrl = Tt.buildImageInspectUrl(uuid);
      AN.get(inspectUrl);
    }
  };

  /**
   * Apply filter to image cards based on usage scope
   * @param {string} scope - TtConst.IMAGE_PICKER_SCOPE_UNUSED | _USED | _ALL
   */
  JournalEditorMultiImagePicker.prototype.applyFilter = function(scope) {
    this.filterScope = scope;
    var usedImageUUIDs = this.editor.usedImageUUIDs;

    $(TtConst.JOURNAL_EDITOR_MULTI_IMAGE_CARD_SELECTOR).each(function() {
      var $card = $(this);
      var uuid = $card.data(TtConst.IMAGE_UUID_DATA_ATTR);
      // Check if count > 0 to handle same image appearing multiple times
      var isUsed = (usedImageUUIDs.get(uuid) || 0) > 0;

      if (scope === TtConst.IMAGE_PICKER_SCOPE_ALL) {
        $card.show();
      } else if (scope === TtConst.IMAGE_PICKER_SCOPE_UNUSED) {
        $card.toggle(!isUsed);
      } else if (scope === TtConst.IMAGE_PICKER_SCOPE_USED) {
        $card.toggle(isUsed);
      }
    });
  };

  // =========================================================================
  // Export to Tt.JournalEditor namespace
  // =========================================================================
  window.Tt = window.Tt || {};
  window.Tt.JournalEditor = window.Tt.JournalEditor || {};
  window.Tt.JournalEditor.JournalEditorMultiImagePicker = JournalEditorMultiImagePicker;

})(jQuery);
