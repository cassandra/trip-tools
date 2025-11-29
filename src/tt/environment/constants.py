from dataclasses import dataclass, asdict
import json


@dataclass(frozen=True)
class SharedConstants:
    """
    String values that are needed on client and server side to ensure single source of truth.
    """
    DATA_ATTRIBUTE_ID_ATTR  : str  = 'data-attribute-id'
    DATA_HIDDEN_FIELD_ATTR  : str  = 'data-hidden-field'
    DATA_OVERFLOW_ATTR  : str  = 'data-overflow'
    DATA_LINE_COUNT_ATTR  : str  = 'data-line-count'
    DATA_ORIGINAL_VALUE_ATTR  : str  = 'data-original-value'

    # Attribute Editing
    ATTR_FILE_INPUT_CLASS  : str  = 'attr-file-input'
    ATTR_FILE_TITLE_INPUT_CLASS  : str  = 'attr-file-title-input'
    ATTR_DIRTY_MESSAGE_CLASS  : str  = 'attr-dirty-message'
    ATTR_STATUS_MESSAGE_ID  : str  = 'attr-status-message'
    ATTR_STATUS_MESSAGE_CLASS  : str  = 'attr-status-message'
    ATTR_UPDATE_BTN_CLASS  : str  = 'attr-update-btn'
    ATTR_ATTRIBUTE_NAME_CLASS  : str  = 'attr-attribute-name'
    ATTR_FORM_CLASS  : str  = 'attr-form'
    ATTR_FORM_DISPLAY_LABEL_CLASS  : str  = 'attr-form-display-label'
    ATTR_CONTAINER_CLASS  : str  = 'attr-container'
    ATTR_HISTORY_LINK_CLASS  : str  = 'attr-history-link'
    ATTR_RESTORE_LINK_CLASS  : str  = 'attr-restore-link'
    ATTR_ATTRIBUTE_CARD_CLASS  : str  = 'attr-attribute-card'
    ATTR_NEW_ATTRIBUTE_CLASS  : str  = 'attr-new-attribute'
    ATTR_FILE_INFO_CLASS  : str  = 'attr-file-info'
    ATTR_DELETE_BTN_CLASS  : str  = 'attr-delete-btn'
    ATTR_UNDO_BTN_CLASS  : str  = 'attr-undo-btn'
    ATTR_FILE_CARD_CLASS  : str  = 'attr-file-card'
    ATTR_SECRET_INPUT_WRAPPER_CLASS  : str  = 'attr-secret-input-wrapper'
    ATTR_SECRET_INPUT_CLASS  : str  = 'attr-secret-input'
    ATTR_ICON_SHOW_CLASS  : str  = 'attr-icon-show'
    ATTR_ICON_HIDE_CLASS  : str  = 'attr-icon-hide'
    ATTR_TEXTAREA_CLASS  : str  = 'attr-textarea'
    ATTR_TEXT_VALUE_WRAPPER_CLASS  : str  = 'attr-text-value-wrapper'
    ATTR_EXPAND_CONTROLS_CLASS  : str  = 'attr-expand-controls'
    ATTR_AUTO_DISMISS_CLASS  : str  = 'attr-auto-dismiss'
    ATTR_DISPLAY_FIELD_CLASS  : str  = 'display-field'
    ATTR_SHOW_MORE_TEXT_CLASS  : str  = 'show-more-text'
    ATTR_SHOW_LESS_TEXT_CLASS  : str  = 'show-less-text'
    ATTR_DELETE_FILE_ATTR  : str  = 'delete_file_attribute'

    JOURNAL_EDITOR_ID  : str  = 'id_entry_text'
    JOURNAL_TITLE_INPUT_ID  : str  = 'id_entry_title'
    JOURNAL_DATE_INPUT_ID  : str  = 'id_entry_date'
    JOURNAL_TIMEZONE_INPUT_ID  : str  = 'id_entry_timezone'
    JOURNAL_EDITOR_CLASS  : str  = 'journal-contenteditable'
    JOURNAL_ENTRY_FORM_CLASS  : str  = 'journal-entry-form'
    JOURNAL_SAVE_STATUS_CLASS  : str  = 'journal-save-status'
    JOURNAL_EDITOR_MULTI_IMAGE_CARD_CLASS  : str  = 'journal-editor-multi-image-card'
    JOURNAL_CURRENT_VERSION_ATTR  : str  = 'current-version'
    JOURNAL_IMAGE_UUID_ATTR  : str  = 'image-uuid'
    IMAGE_PICKER_UUID_ATTR  : str  = 'image-uuid'
    JOURNAL_REFERENCE_IMAGE_UUID_ATTR  : str  = 'reference-image-uuid'
    JOURNAL_AUTOSAVE_URL_ATTR  : str  = 'autosave-url'
    JOURNAL_IMAGE_WRAPPER_CLASS  : str  = 'trip-image-wrapper'
    JOURNAL_IMAGE_CLASS  : str  = 'trip-image'
    JOURNAL_FULL_WIDTH_GROUP_CLASS  : str  = 'full-width-image-group'
    JOURNAL_FLOAT_MARKER_CLASS  : str  = 'has-float-image'
    JOURNAL_DATA_LAYOUT_ATTR  : str  = 'data-layout'
    JOURNAL_UUID_ATTR  : str  = 'uuid'
    JOURNAL_DATA_UUID_ATTR  : str  = 'data-uuid'
    JOURNAL_TEXT_BLOCK_CLASS  : str  = 'text-block'
    JOURNAL_CONTENT_BLOCK_CLASS  : str  = 'content-block'
    JOURNAL_EDITOR_MULTI_IMAGE_PANEL_HEADER_CLASS  : str  = 'journal-editor-multi-image-panel-header'
    JOURNAL_INSPECT_URL_ATTR  : str  = 'inspect-url'
    JOURNAL_EDITOR_MULTI_IMAGE_INSPECT_URL_ATTR  : str  = 'inspect-url'
    JOURNAL_EDITOR_MULTI_IMAGE_URL_ATTR  : str  = 'image-url'
    JOURNAL_EDITOR_MULTI_IMAGE_CAPTION_ATTR  : str  = 'caption'
    IMAGE_PICKER_CAPTION_CLASS  : str  = 'image-picker-caption'
    IMAGE_PICKER_CAPTION_ATTR  : str  = 'caption'
    TRIP_IMAGE_CAPTION_CLASS  : str  = 'trip-image-caption'
    JOURNAL_REFERENCE_IMAGE_CONTAINER_CLASS  : str  = 'journal-reference-image-container'
    JOURNAL_REFERENCE_IMAGE_PLACEHOLDER_CLASS  : str  = 'journal-reference-image-placeholder'
    JOURNAL_REFERENCE_IMAGE_PREVIEW_CLASS  : str  = 'journal-reference-image-preview'
    JOURNAL_REFERENCE_IMAGE_CLEAR_CLASS  : str  = 'journal-reference-image-clear'
    JOURNAL_REFERENCE_IMAGE_THUMBNAIL_CLASS  : str  = 'journal-reference-image-thumbnail'
    IMAGE_PICKER_CARD_CLASS  : str  = 'image-picker-card'
    IMAGE_PICKER_UUID_INPUT_CLASS  : str  = 'image-picker-uuid-input'
    IMAGE_PICKER_PREVIEW_CLASS  : str  = 'image-picker-preview'
    IMAGE_PICKER_SET_BTN_CLASS  : str  = 'image-picker-set-btn'
    IMAGE_PICKER_THUMBNAIL_URL_ATTR  : str  = 'thumbnail-url'
    IMAGES_UPLOADED_ITEM_CLASS  : str  = 'uploaded-item-link'
    IMAGES_UPLOAD_ZONE_ID  : str  = 'images-upload-zone'
    IMAGES_FILE_INPUT_ID  : str  = 'images-file-input'
    IMAGES_PROGRESS_SECTION_ID  : str  = 'images-progress-section'
    IMAGES_PROGRESS_COUNT_ID  : str  = 'images-progress-count'
    IMAGES_FILE_PROGRESS_LIST_ID  : str  = 'images-file-progress-list'
    IMAGES_UPLOADED_GRID_ID  : str  = 'images-uploaded-grid'
    IMAGES_UPLOADED_COUNT_ID  : str  = 'images-uploaded-count'
    JOURNAL_EDITOR_MULTI_IMAGE_GALLERY_ID  : str  = 'journal-editor-multi-image-gallery'
    JOURNAL_EDITOR_MULTI_IMAGE_GALLERY_CLASS  : str  = 'journal-editor-multi-image-gallery'
    JOURNAL_EDITOR_MULTI_IMAGE_FILTER_FORM_ID  : str  = 'image-filter-form'
    JOURNAL_EDITOR_MULTI_IMAGE_DATE_INPUT_ID  : str  = 'id_image_date_filter'
    JOURNAL_EDITOR_MULTI_IMAGE_ENTRY_DATE_BTN_ID  : str  = 'btn-entry-date-images'
    JOURNAL_EDITOR_MULTI_IMAGE_RECENT_BTN_ID  : str  = 'btn-recent-images'

    #  TODO: Below here, only seem to be used in attribute module templates
    ATTR_CONTENT_ID  : str  = 'attr-content'
    ATTR_FILE_GRID_ID  : str  = 'attr-file-grid'
    ATTR_FILE_GRID_CLASS  : str  = 'attr-file-grid'
    ATTR_FILE_NAME_CLASS  : str  = 'attr-file-filename'
    ATTR_ADD_ATTRIBUTE_BTN_ID  : str  = 'attr-add-attribute-btn'
    ATTR_SCROLLABLE_CONTENT_ID  : str  = 'attr-scrollable-content'
    ATTR_SCROLLABLE_CONTENT_CLASS  : str  = 'attr-scrollable-content'
    ATTR_STICKY_PANEL_CLASS  : str  = 'attr-sticky-panel'
    ATTR_ACTION_BAR_CLASS  : str  = 'attr-action-bar'
    ATTR_ACTION_BAR_CONTENT_CLASS  : str  = 'attr-action-bar-content'
    ATTR_ACTION_BUTTONS_CLASS  : str  = 'attr-action-buttons'
    ATTR_HISTORY_INLINE_CONTENT_CLASS  : str  = 'attr-history-inline-content'
    ATTR_HISTORY_HEADER_CLASS  : str  = 'attr-history-header'
    ATTR_HISTORY_CLOSE_CLASS  : str  = 'attr-history-close'
    ATTR_HISTORY_CURRENT_CLASS  : str  = 'attr-history-current'
    ATTR_HISTORY_RECORDS_CLASS  : str  = 'attr-history-records'
    ATTR_HISTORY_RECORD_CLASS  : str  = 'attr-history-record'
    ATTR_HISTORY_TOGGLE_CLASS  : str  = 'attr-history-toggle'
    ATTR_HISTORY_EMPTY_CLASS  : str  = 'attr-history-empty'
    ATTR_ATTRIBUTE_HEADER_CLASS  : str  = 'attr-attribute-header'
    ATTR_ATTRIBUTE_ACTIONS_CLASS  : str  = 'attr-attribute-actions'
    ATTR_ATTRIBUTE_VALUE_CLASS  : str  = 'attr-attribute-value'
    ATTR_TEXT_VALUE_CLASS  : str  = 'attr-text-value'
    ATTR_SECRET_CHECKBOX_CLASS  : str  = 'attr-secret-checkbox'
    ATTR_INLINE_HISTORY_CLASS  : str  = 'attr-inline-history'

    def to_json_dict_str(self) -> str:
        """
        Convert to dictionary suitable for JSON serialization in templates.
        Ensures proper JavaScript boolean/null handling.
        """
        return json.dumps({
            key: (value if value is not None else 'null')
            for key, value in asdict(self).items()
        }, indent=4 )


# Singleton for constants
TtConst = SharedConstants()
