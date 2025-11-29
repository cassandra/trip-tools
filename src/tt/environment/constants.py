import json


class TtConst:
    """
    Single source of truth for constants shared between Python and JavaScript.

    Usage:
        - Template access: Use `{{ TtConst.CONSTANT_NAME }}` (injected via context processor)
        - JavaScript access: Use `TtConst.CONSTANT_NAME` (via <script> in `pages/base.html`)

    Conventions:
        - Javascript responsible for defining derived CSS selector versions as needed

    Data attributes
       - values are keys for jQuery .data() (without "data-" prefix)
       - convention is to name with "_DATA_ATTR" suffix
       - For raw HTML/CSS selectors, prepend "data-" explicitly
    """
    ATTRIBUTE_ID_DATA_ATTR               = 'attribute-id'
    HIDDEN_FIELD_DATA_ATTR               = 'hidden-field'
    OVERFLOW_DATA_ATTR                   = 'overflow'
    LINE_COUNT_DATA_ATTR                 = 'line-count'
    ORIGINAL_VALUE_DATA_ATTR             = 'original-value'

    # Attribute Editing
    ATTR_FILE_INPUT_CLASS                = 'attr-file-input'
    ATTR_FILE_TITLE_INPUT_CLASS          = 'attr-file-title-input'
    ATTR_DIRTY_MESSAGE_CLASS             = 'attr-dirty-message'
    ATTR_STATUS_MESSAGE_ID               = 'attr-status-message'
    ATTR_STATUS_MESSAGE_CLASS            = 'attr-status-message'
    ATTR_UPDATE_BTN_CLASS                = 'attr-update-btn'
    ATTR_ATTRIBUTE_NAME_CLASS            = 'attr-attribute-name'
    ATTR_FORM_CLASS                      = 'attr-form'
    ATTR_FORM_DISPLAY_LABEL_CLASS        = 'attr-form-display-label'
    ATTR_CONTAINER_CLASS                 = 'attr-container'
    ATTR_HISTORY_LINK_CLASS              = 'attr-history-link'
    ATTR_RESTORE_LINK_CLASS              = 'attr-restore-link'
    ATTR_ATTRIBUTE_CARD_CLASS            = 'attr-attribute-card'
    ATTR_NEW_ATTRIBUTE_CLASS             = 'attr-new-attribute'
    ATTR_FILE_INFO_CLASS                 = 'attr-file-info'
    ATTR_DELETE_BTN_CLASS                = 'attr-delete-btn'
    ATTR_UNDO_BTN_CLASS                  = 'attr-undo-btn'
    ATTR_FILE_CARD_CLASS                 = 'attr-file-card'
    ATTR_SECRET_INPUT_WRAPPER_CLASS      = 'attr-secret-input-wrapper'
    ATTR_SECRET_INPUT_CLASS              = 'attr-secret-input'
    ATTR_ICON_SHOW_CLASS                 = 'attr-icon-show'
    ATTR_ICON_HIDE_CLASS                 = 'attr-icon-hide'
    ATTR_TEXTAREA_CLASS                  = 'attr-textarea'
    ATTR_TEXT_VALUE_WRAPPER_CLASS        = 'attr-text-value-wrapper'
    ATTR_EXPAND_CONTROLS_CLASS           = 'attr-expand-controls'
    ATTR_DISPLAY_FIELD_CLASS             = 'display-field'
    ATTR_SHOW_MORE_TEXT_CLASS            = 'show-more-text'
    ATTR_SHOW_LESS_TEXT_CLASS            = 'show-less-text'
    ATTR_DELETE_FILE_ATTR                = 'delete_file_attribute'

    # Journal Editor
    JOURNAL_EDITOR_ID                    = 'id_entry_text'
    JOURNAL_TITLE_INPUT_ID               = 'id_entry_title'
    JOURNAL_DATE_INPUT_ID                = 'id_entry_date'
    JOURNAL_TIMEZONE_INPUT_ID            = 'id_entry_timezone'
    JOURNAL_EDITOR_CLASS                 = 'journal-contenteditable'
    JOURNAL_ENTRY_FORM_CLASS             = 'journal-entry-form'
    JOURNAL_SAVE_STATUS_CLASS            = 'journal-save-status'
    JOURNAL_EDITOR_MULTI_IMAGE_CARD_CLASS = 'journal-editor-multi-image-card'
    CURRENT_VERSION_DATA_ATTR            = 'current-version'
    IMAGE_UUID_DATA_ATTR                 = 'image-uuid'
    UUID_DATA_ATTR                       = 'uuid'
    REFERENCE_IMAGE_UUID_DATA_ATTR       = 'reference-image-uuid'
    AUTOSAVE_URL_DATA_ATTR               = 'autosave-url'
    JOURNAL_IMAGE_WRAPPER_CLASS          = 'trip-image-wrapper'
    JOURNAL_IMAGE_CLASS                  = 'trip-image'
    JOURNAL_FLOAT_MARKER_CLASS           = 'has-float-image'
    LAYOUT_DATA_ATTR                     = 'layout'
    JOURNAL_CONTENT_BLOCK_CLASS          = 'content-block'
    JOURNAL_EDITOR_MULTI_IMAGE_PANEL_HEADER_CLASS = 'journal-editor-multi-image-panel-header'
    INSPECT_URL_DATA_ATTR                = 'inspect-url'
    IMAGE_URL_DATA_ATTR                  = 'image-url'
    CAPTION_DATA_ATTR                    = 'caption'
    THUMBNAIL_URL_DATA_ATTR              = 'thumbnail-url'

    # Image Picker
    IMAGE_PICKER_CAPTION_CLASS           = 'image-picker-caption'
    TRIP_IMAGE_CAPTION_CLASS             = 'trip-image-caption'
    JOURNAL_REFERENCE_IMAGE_CONTAINER_CLASS = 'journal-reference-image-container'
    JOURNAL_REFERENCE_IMAGE_PLACEHOLDER_CLASS = 'journal-reference-image-placeholder'
    JOURNAL_REFERENCE_IMAGE_PREVIEW_CLASS = 'journal-reference-image-preview'
    JOURNAL_REFERENCE_IMAGE_CLEAR_CLASS  = 'journal-reference-image-clear'
    JOURNAL_REFERENCE_IMAGE_THUMBNAIL_CLASS = 'journal-reference-image-thumbnail'
    IMAGE_PICKER_CARD_CLASS              = 'image-picker-card'
    IMAGE_PICKER_UUID_INPUT_CLASS        = 'image-picker-uuid-input'
    IMAGE_PICKER_PREVIEW_CLASS           = 'image-picker-preview'
    IMAGE_PICKER_SET_BTN_CLASS           = 'image-picker-set-btn'

    # Images Upload
    IMAGES_UPLOADED_ITEM_CLASS           = 'uploaded-item-link'
    IMAGES_UPLOAD_ZONE_ID                = 'images-upload-zone'
    IMAGES_FILE_INPUT_ID                 = 'images-file-input'
    IMAGES_PROGRESS_SECTION_ID           = 'images-progress-section'
    IMAGES_PROGRESS_COUNT_ID             = 'images-progress-count'
    IMAGES_FILE_PROGRESS_LIST_ID         = 'images-file-progress-list'
    IMAGES_UPLOADED_GRID_ID              = 'images-uploaded-grid'
    IMAGES_UPLOADED_COUNT_ID             = 'images-uploaded-count'
    JOURNAL_EDITOR_MULTI_IMAGE_GALLERY_ID = 'journal-editor-multi-image-gallery'
    JOURNAL_EDITOR_MULTI_IMAGE_GALLERY_CLASS = 'journal-editor-multi-image-gallery'
    JOURNAL_EDITOR_MULTI_IMAGE_FILTER_FORM_ID = 'image-filter-form'
    JOURNAL_EDITOR_MULTI_IMAGE_DATE_INPUT_ID = 'id_image_date_filter'
    JOURNAL_EDITOR_MULTI_IMAGE_ENTRY_DATE_BTN_ID = 'btn-entry-date-images'
    JOURNAL_EDITOR_MULTI_IMAGE_RECENT_BTN_ID = 'btn-recent-images'

    @classmethod
    def to_json_dict_str(cls):
        """Convert constants to JSON string for JavaScript injection."""
        constants = {
            key: value
            for key, value in vars(cls).items()
            if key.isupper() and isinstance(value, str)
        }
        return json.dumps(constants, indent=4)
