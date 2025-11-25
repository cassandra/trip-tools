(function() {
    
    const Tt = {

        // TtClientConfig comes from server-side template injection. This module
        // (main.css) should be the only Javaacript that knows about
        // TtClientConfig and the coordination mechanism with those
        // server-delivered config settings.  All other JS modules should
        // look to this module to relay any needed config settings (via
        // variable below).
        //
        DEBUG: window.TtClientConfig?.DEBUG ?? false,
        isEditMode: window.TtClientConfig?.IS_EDIT_MODE ?? false,
        
        generateUniqueId: function() {
            return _generateUniqueId();
        },
        setCookie: function( name, value, days = 365, sameSite = 'Lax' ) {
            return _setCookie( name, value, days, sameSite );
        },
        getCookie: function( name ) {
            return _getCookie( name );
        },
        submitForm: function( formElement ) {
            return _submitForm( formElement );
        },
        togglePasswordField: function( toggleCheckbox ) {
            return _togglePasswordField( toggleCheckbox );
        },
        toggleDetails: function( elementId ) {
            return _toggleDetails( elementId );
        },
        getScreenCenterPoint: function( element ) {
            return _getScreenCenterPoint( element );
        },
        getRotationAngle: function( centerX, centerY, startX, startY, endX, endY ) {
            return _getRotationAngle( centerX, centerY, startX, startY, endX, endY );
        },
        normalizeAngle: function(angle) {
            return _normalizeAngle(angle);
        },
        displayEventInfo: function ( label, event ) {
            return _displayEventInfo( label, event );
        },
        displayElementInfo: function( label, element ) {
            return _displayElementInfo( label, element );
        },
        
        // Entity Attribute Editing V2 - IDs and Classes
        ATTR_V2_CONTENT_CLASS: 'attr-v2-content',
        ATTR_V2_UPLOAD_FORM_CONTAINER_ID: 'attr-v2-upload-form-container',
        ATTR_V2_FILE_INPUT_ID: 'attr-v2-file-input',
        ATTR_V2_FILE_TITLE_INPUT_CLASS: 'attr-v2-file-title-input',
        ATTR_V2_DIRTY_MESSAGE_CLASS: 'attr-v2-dirty-message',
        ATTR_V2_STATUS_MESSAGE_CLASS: 'attr-v2-status-message',
        ATTR_V2_UPDATE_BTN_CLASS: 'attr-v2-update-btn',

        ATTR_V2_ATTRIBUTE_NAME_CLASS: 'attr-v2-attribute-name',
        // Ready-to-use jQuery selectors
        ATTR_V2_FORM_CLASS_SELECTOR: '.attr-v2-form',        // Form class
        ATTR_V2_CONTAINER_SELECTOR: '.attr-v2-container',
        ATTR_V2_FILE_INPUT_SELECTOR: '.attr-v2-file-input',
        ATTR_V2_STATUS_MESSAGE_SELECTOR: '.attr-v2-status-message',
        ATTR_V2_DIRTY_MESSAGE_SELECTOR: '.attr-v2-dirty-message',
        ATTR_V2_HISTORY_LINK_SELECTOR: '.attr-v2-history-link',
        ATTR_V2_RESTORE_LINK_SELECTOR: '.attr-v2-restore-link',
        ATTR_V2_ATTRIBUTE_CARD_SELECTOR: '.attr-v2-attribute-card',
        ATTR_V2_NEW_ATTRIBUTE_SELECTOR: '.attr-v2-new-attribute',
        ATTR_V2_FILE_TITLE_INPUT_SELECTOR: '.attr-v2-file-title-input',
        ATTR_V2_FILE_INFO_SELECTOR: '.attr-v2-file-info',
        ATTR_V2_ATTRIBUTE_NAME_SELECTOR: '.attr-v2-attribute-name',
        ATTR_V2_DELETE_BTN_SELECTOR: '.attr-v2-delete-btn',
        ATTR_V2_UNDO_BTN_SELECTOR: '.attr-v2-undo-btn',
        ATTR_V2_FILE_CARD_SELECTOR: '.attr-v2-file-card',
        ATTR_V2_SECRET_INPUT_WRAPPER_SELECTOR: '.attr-v2-secret-input-wrapper',
        ATTR_V2_FORM_DISPLAY_LABEL_SELECTOR: '.attr-v2-form-display-label',
        ATTR_V2_SECRET_INPUT_SELECTOR: '.attr-v2-secret-input',
        ATTR_V2_ICON_SHOW_SELECTOR: '.attr-v2-icon-show',
        ATTR_V2_ICON_HIDE_SELECTOR: '.attr-v2-icon-hide',
        ATTR_V2_TEXTAREA_SELECTOR: '.attr-v2-textarea',
        ATTR_V2_TEXT_VALUE_WRAPPER_SELECTOR: '.attr-v2-text-value-wrapper',
        ATTR_V2_EXPAND_CONTROLS_SELECTOR: '.attr-v2-expand-controls',
        ATTR_V2_AUTO_DISMISS_SELECTOR: '.attr-v2-auto-dismiss',
        ATTR_V2_UPDATE_BTN_SELECTOR: '.attr-v2-update-btn',
        ATTR_V2_DISPLAY_FIELD_SELECTOR: '.display-field',
        ATTR_V2_SHOW_MORE_TEXT_SELECTOR: '.show-more-text',
        ATTR_V2_SHOW_LESS_TEXT_SELECTOR: '.show-less-text',
        
        // Data attributes set by server, read by JS
        DATA_ATTRIBUTE_ID_ATTR: 'data-attribute-id',
        DATA_HIDDEN_FIELD_ATTR: 'data-hidden-field',
        DATA_OVERFLOW_ATTR: 'data-overflow',
        DATA_LINE_COUNT_ATTR: 'data-line-count',
        DATA_ORIGINAL_VALUE_ATTR: 'data-original-value',
        ATTR_V2_DELETE_FILE_ATTR: 'delete_file_attribute',

        // Journal Editor - IDs
        JOURNAL_EDITOR_ID: 'id_entry_text',
        JOURNAL_TITLE_INPUT_ID: 'id_entry_title',
        JOURNAL_DATE_INPUT_ID: 'id_entry_date',
        JOURNAL_TIMEZONE_INPUT_ID: 'id_entry_timezone',

        // Journal Editor - Classes
        JOURNAL_EDITOR_CLASS: 'journal-contenteditable',
        JOURNAL_ENTRY_FORM_CLASS: 'journal-entry-form',
        JOURNAL_SAVE_STATUS_CLASS: 'journal-save-status',
        JOURNAL_IMAGE_CARD_CLASS: 'journal-image-card',

        // Journal - Data Attributes
        JOURNAL_ENTRY_PK_ATTR: 'entry-pk',
        JOURNAL_CURRENT_VERSION_ATTR: 'current-version',
        JOURNAL_IMAGE_UUID_ATTR: 'image-uuid',
        JOURNAL_AUTOSAVE_URL_ATTR: 'autosave-url',

        // Journal - Persistent HTML Elements (saved to database)
        JOURNAL_IMAGE_WRAPPER_CLASS: 'trip-image-wrapper',
        JOURNAL_IMAGE_CLASS: 'trip-image',
        JOURNAL_FULL_WIDTH_GROUP_CLASS: 'full-width-image-group',
        JOURNAL_FLOAT_MARKER_CLASS: 'has-float-image',
        JOURNAL_LAYOUT_ATTR: 'layout',
        JOURNAL_UUID_ATTR: 'uuid',
        JOURNAL_TEXT_BLOCK_CLASS: 'text-block',
        JOURNAL_CONTENT_BLOCK_CLASS: 'content-block',

        // Journal Image Picker - UI Elements
        JOURNAL_IMAGE_PANEL_HEADER_CLASS: 'journal-image-panel-header',

        // Journal Image Picker - Data Attributes
        JOURNAL_INSPECT_URL_ATTR: 'inspect-url',
        JOURNAL_IMAGE_URL_ATTR: 'image-url',
        JOURNAL_CAPTION_ATTR: 'caption',

        // Journal Reference Image - UI Elements
        JOURNAL_REFERENCE_IMAGE_CONTAINER_CLASS: 'journal-reference-image-container',
        JOURNAL_REFERENCE_IMAGE_PLACEHOLDER_CLASS: 'journal-reference-image-placeholder',
        JOURNAL_REFERENCE_IMAGE_PREVIEW_CLASS: 'journal-reference-image-preview',
        JOURNAL_REFERENCE_IMAGE_CLEAR_CLASS: 'journal-reference-image-clear',
        JOURNAL_REFERENCE_IMAGE_THUMBNAIL_CLASS: 'journal-reference-image-thumbnail',

        // Journal Reference Image - Data Attributes
        JOURNAL_REFERENCE_IMAGE_UUID_ATTR: 'reference-image-uuid',

        // Image Picker - Classes
        IMAGE_PICKER_CARD_CLASS: 'image-picker-card',
        IMAGE_PICKER_UUID_INPUT_CLASS: 'image-picker-uuid-input',
        IMAGE_PICKER_PREVIEW_CLASS: 'image-picker-preview',
        IMAGE_PICKER_CAPTION_CLASS: 'image-picker-caption',
        IMAGE_PICKER_SET_BTN_CLASS: 'image-picker-set-btn',

        // Image Picker - Data Attributes
        IMAGE_PICKER_UUID_ATTR: 'image-uuid',
        IMAGE_PICKER_THUMBNAIL_URL_ATTR: 'thumbnail-url',
        IMAGE_PICKER_CAPTION_ATTR: 'caption',

        // Image Picker - Ready-to-use selectors
        IMAGE_PICKER_CARD_SELECTOR: '.image-picker-card',
        IMAGE_PICKER_UUID_INPUT_SELECTOR: '.image-picker-uuid-input',
        IMAGE_PICKER_PREVIEW_SELECTOR: '.image-picker-preview',
        IMAGE_PICKER_CAPTION_SELECTOR: '.image-picker-caption',
        IMAGE_PICKER_SET_BTN_SELECTOR: '.image-picker-set-btn',

        // Journal - Ready-to-use selectors
        JOURNAL_EDITOR_SELECTOR: '#id_entry_text',
        JOURNAL_TITLE_INPUT_SELECTOR: '#id_entry_title',
        JOURNAL_DATE_INPUT_SELECTOR: '#id_entry_date',
        JOURNAL_TIMEZONE_INPUT_SELECTOR: '#id_entry_timezone',
        JOURNAL_ENTRY_FORM_SELECTOR: '.journal-entry-form',
        JOURNAL_SAVE_STATUS_SELECTOR: '.journal-save-status',
        JOURNAL_IMAGE_CARD_SELECTOR: '.journal-image-card',
        JOURNAL_IMAGE_WRAPPER_SELECTOR: '.trip-image-wrapper',
        JOURNAL_IMAGE_WRAPPER_FLOAT_SELECTOR: '.trip-image-wrapper[data-layout="float-right"]',
        JOURNAL_IMAGE_WRAPPER_FULL_SELECTOR: '.trip-image-wrapper[data-layout="full-width"]',
        JOURNAL_IMAGE_SELECTOR: 'img.trip-image',
        JOURNAL_FULL_WIDTH_GROUP_SELECTOR: '.full-width-image-group',
        JOURNAL_FLOAT_MARKER_SELECTOR: '.has-float-image',
        JOURNAL_TEXT_BLOCK_SELECTOR: '.text-block',
        JOURNAL_CONTENT_BLOCK_SELECTOR: '.content-block',
        JOURNAL_IMAGE_PANEL_HEADER_SELECTOR: '.journal-image-panel-header',
        JOURNAL_REFERENCE_IMAGE_CONTAINER_SELECTOR: '.journal-reference-image-container',
        JOURNAL_REFERENCE_IMAGE_PLACEHOLDER_SELECTOR: '.journal-reference-image-placeholder',
        JOURNAL_REFERENCE_IMAGE_PREVIEW_SELECTOR: '.journal-reference-image-preview',
        JOURNAL_REFERENCE_IMAGE_CLEAR_SELECTOR: '.journal-reference-image-clear',
        JOURNAL_REFERENCE_IMAGE_THUMBNAIL_SELECTOR: '.journal-reference-image-thumbnail',

        // Trip Images Upload - DIVID constants
        DIVID: {
            IMAGES_UPLOAD_ZONE_ID: 'images-upload-zone',
            IMAGES_FILE_INPUT_ID: 'images-file-input',
            IMAGES_PROGRESS_SECTION_ID: 'images-progress-section',
            IMAGES_PROGRESS_COUNT_ID: 'images-progress-count',
            IMAGES_FILE_PROGRESS_LIST_ID: 'images-file-progress-list',
            IMAGES_UPLOADED_GRID_ID: 'images-uploaded-grid',
            IMAGES_UPLOADED_COUNT_ID: 'images-uploaded-count'
        }
    };

    window.Tt = Tt;

    function _generateUniqueId() {
        return 'id-' + Date.now() + '-' + Math.floor(Math.random() * 1000);
    }

    function _setCookie( name, value, days, sameSite ) {
        const expires = new Date();
        expires.setTime( expires.getTime() + days * 24 * 60 * 60 * 1000 );
        const secureFlag = sameSite === 'None' ? '; Secure' : '';
        document.cookie = `${name}=${encodeURIComponent(value)}; expires=${expires.toUTCString()}; path=/; SameSite=${sameSite}${secureFlag}`;
        return true;
    }

    function _getCookie( name ) {
        const nameEQ = `${encodeURIComponent(name)}=`;
        const cookies = document.cookie.split(';'); // SPlit into key-pairs
        for ( let i = 0; i < cookies.length; i++ ) {
            let cookie = cookies[i].trim();
            if (cookie.startsWith( nameEQ )) {
                return decodeURIComponent( cookie.substring( nameEQ.length ));
            }
        }
        return null;    
    }
    
    function _submitForm( formElement ) {
        let form = $(formElement).closest('form');
        if ( Tt.DEBUG ) { console.debug( 'Submitting form:', formElement, form ); }
        $(form).submit();
    }
    
    function _togglePasswordField( toggleCheckbox ) {

        let passwordField = $(toggleCheckbox).closest(Tt.FORM_FIELD_CONTAINER_SELECTOR).find('input[type="password"], input[type="text"]');
        if ( toggleCheckbox.checked ) {
            passwordField.attr('type', 'text');
            $('label[for="' +  $(toggleCheckbox).attr('id') + '"]').text('Hide');
        } else {
            passwordField.attr('type', 'password');
            $('label[for="' +  $(toggleCheckbox).attr('id') + '"]').text('Show');
        }
    }

    function _toggleDetails( elementId ) {
        if (!elementId || elementId.trim() === '') {
            console.warn('_toggleDetails called with empty elementId');
            return;
        }
        const el = document.getElementById(elementId);
        if (el) {
            $(el).toggle();
        } else {
            console.warn('_toggleDetails: Element not found with ID:', elementId);
        }
    }
    
    function _getScreenCenterPoint( element ) {
        try {
            let rect = $(element)[0].getBoundingClientRect();
            if ( rect ) {
                const screenCenterX = rect.left + ( rect.width / 2.0 );
                const screenCenterY = rect.top + ( rect.height / 2.0 );
                return {
                    x: rect.left + ( rect.width / 2.0 ),
                    y: rect.top + ( rect.height / 2.0 )
                };
            }
        } catch (e) {
            console.debug( `Problem getting bounding box: ${e}` );
        }
        return null;
    }
    
    function _getRotationAngle( centerX, centerY, startX, startY, endX, endY ) {

        const startVectorX = startX - centerX;
        const startVectorY = startY - centerY;

        const endVectorX = endX - centerX;
        const endVectorY = endY - centerY;

        const startAngle = Math.atan2( startVectorY, startVectorX );
        const endAngle = Math.atan2( endVectorY, endVectorX );

        let angleDifference = endAngle - startAngle;

        // Normalize the angle to be between -π and π
        if ( angleDifference > Math.PI ) {
            angleDifference -= 2 * Math.PI;
        } else if ( angleDifference < -Math.PI ) {
            angleDifference += 2 * Math.PI;
        }

        const angleDifferenceDegrees = angleDifference * ( 180 / Math.PI );

        return angleDifferenceDegrees;
    }

    function _normalizeAngle(angle) {
        return (angle % 360 + 360) % 360;
    }

    function _displayEventInfo ( label, event ) {
        if ( ! Tt.DEBUG ) { return; }
        if ( ! event ) {
            console.log( 'No element to display info for.' );
            return;
        }
        console.log( `${label} Event: 
    Type: ${event.type}, 
    Key: ${event.key},
    KeyCode: ${event.keyCode},
    Pos: ( ${event.clientX}, ${event.clientY} )` );
    }

    function _displayElementInfo( label, element ) {
        if ( ! Tt.DEBUG ) { return; }
        if ( ! element ) {
            console.log( 'No element to display info for.' );
            return;
        }
        const elementTag = $(element).prop('tagName');
        const elementId = $(element).attr('id') || 'No ID';
        const elementClasses = $(element).attr('class') || 'No Classes';
        
        let rectStr = 'No Bounding Rect';
        try {
            let rect = $(element)[0].getBoundingClientRect();
            if ( rect ) {
                rectStr = `Dim: ${rect.width}px x ${rect.height}px,
    Pos: left=${rect.left}px, top=${rect.top}px`;
            }
        } catch (e) {
        }
        
        let offsetStr = 'No Offset';
        const offset = $(element).offset();
        if ( offset ) {
            offsetStr = `Offset: ( ${offset.left}px,  ${offset.top}px )`;
        }
        
        let svgStr = 'Not an SVG';
        if ( elementTag == 'svg' ) {
            let viewBox = $(element).attr( 'viewBox' );
            if ( viewBox != null ) {
                svgStr = `Viewbox: ${viewBox}`;
            } else {
                svgStr = 'No viewbox attribute';
            }
        }
        
        console.log( `${label}:
    Name: ${elementTag},
    Id: ${elementId},
    Classes: ${elementClasses},
    ${svgStr},
    ${offsetStr},
    ${rectStr}`) ;

    }

})();

// Radio button show/hide utility
// Uses data-show-when-checked and data-hide-when-checked attributes
(function() {
    'use strict';

    function updateRadioVisibility($context) {
        // If no context provided, search entire document
        $context = $context || $(document);

        // Find all radios with show/hide data attributes in this context
        // Only process CHECKED radios - unchecked radios should not affect visibility
        $context.find('input[type="radio"][data-show-when-checked]:checked, input[type="radio"][data-hide-when-checked]:checked').each(function() {
            const $radio = $(this);

            // Handle data-show-when-checked (this radio is checked, so show target)
            const showSelector = $radio.data('show-when-checked');
            if (showSelector) {
                $(showSelector).show();
            }

            // Handle data-hide-when-checked (this radio is checked, so hide target)
            const hideSelector = $radio.data('hide-when-checked');
            if (hideSelector) {
                $(hideSelector).hide();
            }
        });
    }

    // Event delegation for radio changes (works for all radios, including in modals)
    $(document).on('change', 'input[type="radio"][data-show-when-checked], input[type="radio"][data-hide-when-checked]', function() {
        updateRadioVisibility();
    });

    // Initialize on page load
    $(document).ready(function() {
        updateRadioVisibility();
    });

    // Initialize when modals are about to be shown (before animation)
    $('body').on('show.bs.modal', '.modal', function() {
        updateRadioVisibility($(this));
    });

    // Also initialize after modals are fully shown (handles edge cases)
    $('body').on('shown.bs.modal', '.modal', function() {
        updateRadioVisibility($(this));
    });
})();
