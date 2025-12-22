import json

from tt.apps.journal.enums import ImagePickerScope


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
    EDITOR_AUTOSAVE_INTERVAL_SECS        = 3
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
    JOURNAL_PREVIEW_BTN_CLASS            = 'journal-preview-btn'
    JOURNAL_EDITOR_MULTI_IMAGE_CARD_CLASS = 'journal-editor-multi-image-card'
    CURRENT_VERSION_DATA_ATTR            = 'current-version'
    IMAGE_UUID_DATA_ATTR                 = 'image-uuid'
    UUID_DATA_ATTR                       = 'uuid'
    REFERENCE_IMAGE_UUID_DATA_ATTR       = 'reference-image-uuid'
    ENTRY_UUID_DATA_ATTR                 = 'entry-uuid'
    TRIP_UUID_DATA_ATTR                  = 'trip-uuid'
    JOURNAL_IMAGE_WRAPPER_CLASS          = 'trip-image-wrapper'
    JOURNAL_IMAGE_CLASS                  = 'trip-image'
    JOURNAL_FLOAT_MARKER_CLASS           = 'has-float-image'
    LAYOUT_DATA_ATTR                     = 'layout'
    JOURNAL_CONTENT_BLOCK_CLASS          = 'content-block'
    JOURNAL_EDITOR_MULTI_IMAGE_PANEL_HEADER_CLASS = 'journal-editor-multi-image-panel-header'
    IMAGE_MEDIA_URL_DATA_ATTR            = 'image-url'
    CAPTION_DATA_ATTR                    = 'caption'
    THUMBNAIL_MEDIA_URL_DATA_ATTR        = 'thumbnail-url'

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
    LAST_USED_DATE_ATTR                  = 'last-used-date'
    INITIAL_SCOPE_DATA_ATTR              = 'initial-scope'
    IMAGE_PICKER_SCOPE_UNUSED            = str(ImagePickerScope.UNUSED)
    IMAGE_PICKER_SCOPE_USED              = str(ImagePickerScope.USED)
    IMAGE_PICKER_SCOPE_ALL               = str(ImagePickerScope.ALL)
    PICKER_DATE_PARAM                    = 'picker_date'
    PICKER_RECENT_PARAM                  = 'picker_recent'
    PICKER_SCOPE_PARAM                   = 'picker_scope'
    
    # Images Upload
    UPLOAD_SESSION_UUID_FIELD            = 'upload_session_uuid'
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

    # Browser Extension Integration
    # These constants must match values in tools/extension/src/shared/constants.js
    # Body classes added by extension content script (also in main.css)
    EXT_STATE_CLASS_AUTHORIZED           = 'tt-ext-authorized'
    EXT_STATE_CLASS_NOT_AUTHORIZED       = 'tt-ext-not-authorized'
    EXT_STATE_CLASS_ACCOUNT_MISMATCH     = 'tt-ext-account-mismatch'
    EXT_STATE_CLASS_SERVER_MISMATCH      = 'tt-ext-server-mismatch'
    # CSS visibility classes (also in main.css)
    EXT_SHOW_AUTHORIZED_CLASS            = 'tt-ext-show-authorized'
    EXT_SHOW_NOT_AUTHORIZED_CLASS        = 'tt-ext-show-not-authorized'
    EXT_SHOW_NOT_INSTALLED_CLASS         = 'tt-ext-show-not-installed'
    EXT_SHOW_ACCOUNT_MISMATCH_CLASS      = 'tt-ext-show-account-mismatch'
    EXT_SHOW_SERVER_MISMATCH_CLASS       = 'tt-ext-show-server-mismatch'
    # Data attribute for page user UUID (read by extension content script)
    EXT_USER_UUID_DATA_ATTR              = 'data-tt-user-uuid'
    # PostMessage types for extension<->page communication
    EXT_POSTMESSAGE_DATA_TYPE            = 'tt_extension_data'
    EXT_POSTMESSAGE_ACK_TYPE             = 'tt_extension_ack'
    # DOM element ID for token handoff
    EXT_TOKEN_DATA_ELEMENT_ID            = 'extension-token-data'
    # Form async DOM changes when authorizing.
    EXT_AUTH_RESULT_ID                   = 'tt-ext-auth-result'
    EXT_API_TOKEN_TABLE_ID               = 'tt-ext-api-token-table'
    EXT_AUTH_PENDING_ID                  = 'tt-ext-auth-pending'
    EXT_AUTH_SUCCESS_ID                  = 'tt-ext-auth-success'
    EXT_AUTH_FAILURE_ID                  = 'tt-ext-auth-failure'
    
    @classmethod
    def to_json_dict_str(cls):
        """Convert constants to JSON string for JavaScript injection."""
        constants = {
            key: value
            for key, value in vars(cls).items()
            if key.isupper() and ( isinstance(value, str) or isinstance(value, int))
        }
        return json.dumps(constants, indent=4)
