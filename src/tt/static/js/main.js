(function() {

    // ==========================================================================
    // TtConst Selector Derivation
    // ==========================================================================
    // TtConst is injected by server via <script> in pages/base.html with all shared constants.
    // Here we extend it with derived CSS selectors for JavaScript use.

    const C = window.TtConst;

    // Attribute Editing - class selectors
    C.ATTR_FILE_INPUT_SELECTOR = '.' + C.ATTR_FILE_INPUT_CLASS;
    C.ATTR_FILE_TITLE_INPUT_SELECTOR = '.' + C.ATTR_FILE_TITLE_INPUT_CLASS;
    C.ATTR_DIRTY_MESSAGE_SELECTOR = '.' + C.ATTR_DIRTY_MESSAGE_CLASS;
    C.ATTR_STATUS_MESSAGE_SELECTOR = '.' + C.ATTR_STATUS_MESSAGE_CLASS;
    C.ATTR_UPDATE_BTN_SELECTOR = '.' + C.ATTR_UPDATE_BTN_CLASS;
    C.ATTR_ATTRIBUTE_NAME_SELECTOR = '.' + C.ATTR_ATTRIBUTE_NAME_CLASS;
    C.ATTR_FORM_CLASS_SELECTOR = '.' + C.ATTR_FORM_CLASS;
    C.ATTR_FORM_DISPLAY_LABEL_SELECTOR = '.' + C.ATTR_FORM_DISPLAY_LABEL_CLASS;
    C.ATTR_CONTAINER_SELECTOR = '.' + C.ATTR_CONTAINER_CLASS;
    C.ATTR_HISTORY_LINK_SELECTOR = '.' + C.ATTR_HISTORY_LINK_CLASS;
    C.ATTR_RESTORE_LINK_SELECTOR = '.' + C.ATTR_RESTORE_LINK_CLASS;
    C.ATTR_ATTRIBUTE_CARD_SELECTOR = '.' + C.ATTR_ATTRIBUTE_CARD_CLASS;
    C.ATTR_NEW_ATTRIBUTE_SELECTOR = '.' + C.ATTR_NEW_ATTRIBUTE_CLASS;
    C.ATTR_FILE_INFO_SELECTOR = '.' + C.ATTR_FILE_INFO_CLASS;
    C.ATTR_DELETE_BTN_SELECTOR = '.' + C.ATTR_DELETE_BTN_CLASS;
    C.ATTR_UNDO_BTN_SELECTOR = '.' + C.ATTR_UNDO_BTN_CLASS;
    C.ATTR_FILE_CARD_SELECTOR = '.' + C.ATTR_FILE_CARD_CLASS;
    C.ATTR_SECRET_INPUT_WRAPPER_SELECTOR = '.' + C.ATTR_SECRET_INPUT_WRAPPER_CLASS;
    C.ATTR_SECRET_INPUT_SELECTOR = '.' + C.ATTR_SECRET_INPUT_CLASS;
    C.ATTR_ICON_SHOW_SELECTOR = '.' + C.ATTR_ICON_SHOW_CLASS;
    C.ATTR_ICON_HIDE_SELECTOR = '.' + C.ATTR_ICON_HIDE_CLASS;
    C.ATTR_TEXTAREA_SELECTOR = '.' + C.ATTR_TEXTAREA_CLASS;
    C.ATTR_TEXT_VALUE_WRAPPER_SELECTOR = '.' + C.ATTR_TEXT_VALUE_WRAPPER_CLASS;
    C.ATTR_EXPAND_CONTROLS_SELECTOR = '.' + C.ATTR_EXPAND_CONTROLS_CLASS;
    C.ATTR_DISPLAY_FIELD_SELECTOR = '.' + C.ATTR_DISPLAY_FIELD_CLASS;
    C.ATTR_SHOW_MORE_TEXT_SELECTOR = '.' + C.ATTR_SHOW_MORE_TEXT_CLASS;
    C.ATTR_SHOW_LESS_TEXT_SELECTOR = '.' + C.ATTR_SHOW_LESS_TEXT_CLASS;

    // Journal - ID selectors
    C.JOURNAL_EDITOR_ID_SELECTOR = '#' + C.JOURNAL_EDITOR_ID;
    C.JOURNAL_TITLE_INPUT_ID_SELECTOR = '#' + C.JOURNAL_TITLE_INPUT_ID;
    C.JOURNAL_DATE_INPUT_ID_SELECTOR = '#' + C.JOURNAL_DATE_INPUT_ID;
    C.JOURNAL_TIMEZONE_INPUT_SELECTOR = '#' + C.JOURNAL_TIMEZONE_INPUT_ID;

    // Journal - class selectors
    C.JOURNAL_EDITOR_SELECTOR = '.' + C.JOURNAL_EDITOR_CLASS;
    C.JOURNAL_ENTRY_FORM_SELECTOR = '.' + C.JOURNAL_ENTRY_FORM_CLASS;
    C.JOURNAL_SAVE_STATUS_SELECTOR = '.' + C.JOURNAL_SAVE_STATUS_CLASS;
    C.JOURNAL_PREVIEW_BTN_SELECTOR = '.' + C.JOURNAL_PREVIEW_BTN_CLASS;
    C.JOURNAL_EDITOR_MULTI_IMAGE_CARD_SELECTOR = '.' + C.JOURNAL_EDITOR_MULTI_IMAGE_CARD_CLASS;
    C.JOURNAL_IMAGE_WRAPPER_SELECTOR = '.' + C.JOURNAL_IMAGE_WRAPPER_CLASS;
    C.JOURNAL_IMAGE_SELECTOR = 'img.' + C.JOURNAL_IMAGE_CLASS;
    C.JOURNAL_EDITOR_MULTI_IMAGE_PANEL_HEADER_SELECTOR = '.' + C.JOURNAL_EDITOR_MULTI_IMAGE_PANEL_HEADER_CLASS;

    // Journal - complex selectors with attribute filters
    C.JOURNAL_IMAGE_WRAPPER_FLOAT_SELECTOR = '.' + C.JOURNAL_IMAGE_WRAPPER_CLASS + '[data-' + C.LAYOUT_DATA_ATTR + '="float-right"]';
    C.JOURNAL_IMAGE_WRAPPER_FULL_SELECTOR = '.' + C.JOURNAL_IMAGE_WRAPPER_CLASS + '[data-' + C.LAYOUT_DATA_ATTR + '="full-width"]';

    // Image picker selectors
    C.IMAGE_PICKER_CAPTION_SELECTOR = '.' + C.IMAGE_PICKER_CAPTION_CLASS;
    C.JOURNAL_REFERENCE_IMAGE_CONTAINER_SELECTOR = '.' + C.JOURNAL_REFERENCE_IMAGE_CONTAINER_CLASS;
    C.JOURNAL_REFERENCE_IMAGE_PLACEHOLDER_SELECTOR = '.' + C.JOURNAL_REFERENCE_IMAGE_PLACEHOLDER_CLASS;
    C.JOURNAL_REFERENCE_IMAGE_PREVIEW_SELECTOR = '.' + C.JOURNAL_REFERENCE_IMAGE_PREVIEW_CLASS;
    C.JOURNAL_REFERENCE_IMAGE_CLEAR_SELECTOR = '.' + C.JOURNAL_REFERENCE_IMAGE_CLEAR_CLASS;
    C.JOURNAL_REFERENCE_IMAGE_THUMBNAIL_SELECTOR = '.' + C.JOURNAL_REFERENCE_IMAGE_THUMBNAIL_CLASS;
    C.IMAGE_PICKER_CARD_SELECTOR = '.' + C.IMAGE_PICKER_CARD_CLASS;
    C.IMAGE_PICKER_UUID_INPUT_SELECTOR = '.' + C.IMAGE_PICKER_UUID_INPUT_CLASS;
    C.IMAGE_PICKER_PREVIEW_SELECTOR = '.' + C.IMAGE_PICKER_PREVIEW_CLASS;
    C.IMAGE_PICKER_SET_BTN_SELECTOR = '.' + C.IMAGE_PICKER_SET_BTN_CLASS;
    C.IMAGES_UPLOADED_ITEM_SELECTOR = '.' + C.IMAGES_UPLOADED_ITEM_CLASS;
    C.JOURNAL_EDITOR_MULTI_IMAGE_GALLERY_SELECTOR = '.' + C.JOURNAL_EDITOR_MULTI_IMAGE_GALLERY_CLASS;

    // ==========================================================================
    // Tt Namespace - Utilities and Runtime Config
    // ==========================================================================
    // Tt provides utility functions and runtime configuration.
    // TtClientConfig comes from server-side template injection. This module
    // (main.js) should be the only JavaScript that knows about TtClientConfig.
    // All other JS modules should look to Tt for runtime config.

    const Tt = {

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

    };

    window.Tt = Tt;

    // ==========================================================================
    // Private Utility Functions
    // ==========================================================================

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
        const cookies = document.cookie.split(';'); // Split into key-pairs
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
