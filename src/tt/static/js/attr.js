/*
 * Trip Tools - Attribute Editing JavaScript
 * Core attribute editing functionality for entities, locations, and configurations
 * Provides container-aware form handling, AJAX operations, and UI management
 */

(function() {
    'use strict';
    
    // Internal constants - JS-only, no server dependency
    const ATTR_V2_INTERNAL = {
        // State management data keys (different granularity levels)
        INITIALIZED_DATA_KEY: 'attr-v2-initialized',      // Container-level flag
        PROCESSED_DATA_KEY: 'attr-v2-processed',          // Element-level flag
        
        // Event namespaces
        AJAX_EVENT_NAMESPACE: 'attr-v2-ajax',
        OVERFLOW_EVENT_NAMESPACE: 'input.overflow',
        
        // HTTP/AJAX constants
        CSRF_TOKEN_NAME: 'csrfmiddlewaretoken',
        XML_HTTP_REQUEST_HEADER: 'X-Requested-With',
        AUTOSIZE_INITIALIZED_ATTR: 'data-autosize-initialized',
        
        // CSS state classes (JS-managed, not in templates)
        TRUNCATED_CLASS: 'truncated',
        MARKED_FOR_DELETION_CLASS: 'marked-for-deletion',
        ACTIVATED_CLASS: 'activated',
        HAS_DIRTY_INDICATOR_CLASS: 'has-dirty-indicator',
        HAS_DIRTY_FIELD_CLASS: 'has-dirty-field',
        ACTIVE_CLASS: 'active',
        
        // Form field name patterns
        NAME_FIELD_SUFFIX: '-name',
        VALUE_FIELD_SUFFIX: '-value',
        DELETE_FIELD_SUFFIX: '-DELETE',
        
        // Status message CSS classes (Bootstrap)
        STATUS_SUCCESS_CLASS: 'text-success',
        STATUS_ERROR_CLASS: 'text-danger',
        STATUS_INFO_CLASS: 'text-info',
        STATUS_WARNING_CLASS: 'text-warning',
        
        // Bootstrap/generic classes
        MODAL_SELECTOR: '.modal',
        FORM_GROUP_SELECTOR: '.form-group'
    };
    
    // Status message type constants - exposed for public use
    const STATUS_TYPE = {
        SUCCESS: 'success',
        ERROR: 'error',
        WARNING: 'warning',
        INFO: 'info'
    };
    
    // Create the main Tt.attr namespace
    window.Tt = window.Tt || {};
    
    const TtAttr = {
        // Status message types
        STATUS_TYPE: STATUS_TYPE,
        
        // Container Management
        initializeContainer: function(containerSelector) {
            const $container = $(containerSelector);
            if ($container.length > 0) {
                _initializeContainer($container);
            }
        },
        
        reinitializeContainer: function(containerId) {
            const $container = $(`#${containerId}`);
            if ($container.length > 0) {
                _initializeContainer($container);
            }
        },
        
        // Form Operations
        submitForm: function(form, options = {}) {
            return _ajax.submitFormWithAjax(form, options);
        },
        
        updateFormAction: function(newUrl, containerId, labelText = null) {
            return _updateFormAction(newUrl, containerId, labelText);
        },
        
        // Content Management
        loadContent: function(url, target, options = {}) {
            return _ajax.loadContentIntoTarget(url, target, options);
        },
        
        updateElement: function(selector, html, mode = 'replace') {
            return _ajax.updateDOMElement(selector, html, mode);
        },
        
        // Status & Messages
        showStatusMessage: function(message, type = 'info', form = null) {
            return _ajax.showStatusMessage(message, type, form);
        },
        
        // UI Actions
        showAddAttribute: function(containerSelector = null) {
            return _showAddAttribute(containerSelector);
        },
        
        toggleSecretField: function(button) {
            return _toggleSecretField(button);
        },
        
        updateBooleanHiddenField: function(checkbox) {
            return _updateBooleanHiddenField(checkbox);
        },
        
        toggleExpandedView: function(button) {
            return _toggleExpandedView(button);
        },
        
        // Initialization
        init: function() {
            _initializeAllContainers();
        }
    };
    
    // Export to Hi namespace
    window.Tt.attr = TtAttr;
    
    // Private Ajax Infrastructure
    const _ajax = {
        // Submit form with custom Ajax handling
        submitFormWithAjax: function(form, options = {}) {
            const $form = $(form);
            
            // Ensure we have a valid form element
            if ($form.length === 0 || !$form[0] || $form[0].tagName !== 'FORM') {
                console.error('DEBUG: Invalid form element passed to submitFormWithAjax:', form);
                return;
            }
            
            // Find the container and sync textarea values to hidden fields before submission
            const $container = $form.closest(Tt.ATTR_V2_CONTAINER_SELECTOR);
            if ($container.length > 0) {
                _syncTextareaValuesToHiddenFields($container);
            }
            
            const formData = new FormData($form[0]);
            const url = $form.attr('action');
            const method = $form.attr('method') || 'POST';
            
            // Add CSRF token if not already present
            if (!formData.has(ATTR_V2_INTERNAL.CSRF_TOKEN_NAME)) {
                const csrfToken = $(`[name=${ATTR_V2_INTERNAL.CSRF_TOKEN_NAME}]`).val();
                if (csrfToken) {
                    formData.append(ATTR_V2_INTERNAL.CSRF_TOKEN_NAME, csrfToken);
                }
            }
            
            return $.ajax({
                url: url,
                method: method,
                data: formData,
                processData: false,
                contentType: false,
                headers: {
                    [ATTR_V2_INTERNAL.XML_HTTP_REQUEST_HEADER]: 'XMLHttpRequest'
                }
            }).done((response) => {
                this.handleFormSuccess(response, $form, options);
            }).fail((xhr) => {
                this.handleFormError(xhr, $form);
            });
        },
        
        // Load content into target via GET request
        loadContentIntoTarget: function(url, target, options = {}) {
            return $.ajax({
                url: url,
                method: 'GET',
                headers: {
                    [ATTR_V2_INTERNAL.XML_HTTP_REQUEST_HEADER]: 'XMLHttpRequest'
                }
            }).done((response) => {
                // Handle response for content loading
                if (typeof response === 'string') {
                    this.updateDOMElement(target, response, options.mode || 'replace');
                } else {
                    console.warn('loadContentIntoTarget: Unexpected response type:', typeof response);
                }
            }).fail((xhr) => {
                console.error('Failed to load content:', xhr);
                
                // Show error message to user if we can find a form context
                const $target = $(target);
                const $form = $target.closest('form');
                if ($form.length > 0) {
                    this.handleFormError(xhr, $form);
                } else {
                    // Fallback: show error in any available status container
                    // These are transient errors (like history loading), so allow auto-dismiss
                    const errorMessage = this.getErrorMessageForStatus(xhr.status, xhr.statusText);
                    this.showStatusMessage(errorMessage, STATUS_TYPE.ERROR, null, 5000);
                }
            });
        },
        
        // Handle successful form submission
        // Parse response data into normalized format
        parseResponse: function(response) {
            // Handle null/undefined responses
            if (!response) {
                return {};
            }
            
            // Handle string responses
            if (typeof response === 'string') {
                if (response.trim() === '') {
                    return {};
                }
                try {
                    return JSON.parse(response);
                } catch (e) {
                    console.warn('Failed to parse response as JSON:', e);
                    return { message: response }; // Treat as plain text message
                }
            }
            
            // Handle object responses
            if (typeof response === 'object') {
                return response;
            }
            
            // Handle other types (number, boolean, etc.)
            console.warn('Unexpected response type:', typeof response);
            return { message: String(response) };
        },
        
        // Process DOM updates from response data
        processDOMUpdates: function(data, options = {}) {
            // Track the last append target for scrolling decision
            // When scrollToNewContent is requested and multiple updates occur,
            // we scroll to the LAST appended content. This decision assumes that
            // in most cases (like file uploads), the last append is the most
            // relevant/newest content the user wants to see. If different behavior
            // is needed, the caller should handle scrolling manually.
            let lastAppendTarget = null;
            
            if (data.updates && Array.isArray(data.updates)) {
                data.updates.forEach(update => {
                    if (update.target && update.html) {
                        this.updateDOMElement(update.target, update.html, update.mode || 'replace');
                        
                        // Track append operations for potential scrolling
                        if (update.mode === 'append') {
                            lastAppendTarget = update.target;
                        }
                    }
                });
            }
            
            return lastAppendTarget;
        },
        
        // Process status message from response data
        processStatusMessage: function(data, $form, isError = false) {
            
            // Handle explicit messages from server
            if (data && data.message) {
                const messageType = isError ? STATUS_TYPE.ERROR : STATUS_TYPE.SUCCESS;
                
                // For form validation errors, make them persistent (no auto-dismiss)
                const timeout = isError ? 0 : null; // 0 = no auto-dismiss for errors, null = default for success
                this.showStatusMessage(data.message, messageType, $form, timeout);
                return;
            }
            
            // Provide default messages when server doesn't provide one
            if (!isError) {
                // Success case with no explicit message
                this.showStatusMessage('Success', STATUS_TYPE.SUCCESS, $form);
            } else {
                // Error case with no explicit message - make persistent
                this.showStatusMessage('An error occurred while processing your request', STATUS_TYPE.ERROR, $form, 0);
            }
        },
        
        // Unified response handler for both success and error responses
        handleResponse: function(response, $form, options = {}, isError = false) {
            // Parse response into normalized format
            const data = this.parseResponse(response);
            
            // Handle redirects first - if redirect is present, do it immediately
            if (data.redirect) {
                if ( Tt.DEBUG ) { console.log('Form response contains redirect, navigating to:', data.redirect); }
                window.location.href = data.redirect;
                return;
            }
            
            // Process DOM updates first (works for both success and error)
            const lastAppendTarget = this.processDOMUpdates(data, options);
            
            // Handle scroll-to-new-content if requested by caller
            if (options.scrollToNewContent && lastAppendTarget) {
                const element = document.querySelector(lastAppendTarget);
                if (element) {
                    // Small delay to ensure DOM is fully updated before scrolling
                    setTimeout(() => {
                        element.scrollIntoView({ behavior: 'smooth', block: 'start' });
                    }, 100);
                }
            }
            
            // Show status message
            this.processStatusMessage(data, $form, isError);
            
            // Re-initialize containers after update
            setTimeout(() => {
                _initializeAllContainers();
            }, 50);
        },
        
        // Handle successful form submission - now delegates to unified handler
        handleFormSuccess: function(response, $form, options = {}) {
            this.handleResponse(response, $form, options, false);
        },
        
        // Handle form submission errors - now delegates to unified handler
        handleFormError: function(xhr, $form) {
            let response;
            let hasValidResponse = false;
            
            // Try to parse error response if we have content
            if (xhr.responseText && xhr.responseText.trim()) {
                try {
                    response = JSON.parse(xhr.responseText);
                    hasValidResponse = true;
                } catch (e) {
                    console.warn('Failed to parse error response JSON:', e);
                    // Continue to create fallback response
                }
            }
            
            // Create fallback error response if parsing fails or no content
            if (!hasValidResponse) {
                const fallbackMessage = this.getErrorMessageForStatus(xhr.status, xhr.statusText);
                response = {
                    success: false,
                    message: fallbackMessage
                };
            } else {
                // If we have a parsed response but no message, add status-based message
                if (!response.message) {
                    response.message = this.getErrorMessageForStatus(xhr.status, xhr.statusText);
                }
            }
            
            // Ensure response has required structure
            if (!response.hasOwnProperty('success')) {
                response.success = false;
            }
            
            // Use unified handler to process error response (including DOM updates)
            this.handleResponse(response, $form, {}, true);
        },
        
        // Generate appropriate error message based on HTTP status code
        getErrorMessageForStatus: function(status, statusText) {
            switch (status) {
                case 400:
                    return 'Bad request - please check your input and try again';
                case 401:
                    return 'Authentication required - please log in and try again';
                case 403:
                    return 'Access denied - you do not have permission for this action';
                case 404:
                    return 'The requested resource was not found';
                case 408:
                    return 'Request timeout - please try again';
                case 500:
                    return 'Server error occurred - please try again later';
                case 502:
                    return 'Bad gateway - server is temporarily unavailable';
                case 503:
                    return 'Service unavailable - please try again later';
                case 504:
                    return 'Gateway timeout - please try again later';
                case 0:
                    return 'Network error - please check your connection and try again';
                default:
                    if (status >= 400 && status < 500) {
                        return `Client error (${status}): ${statusText || 'Please check your request and try again'}`;
                    } else if (status >= 500) {
                        return `Server error (${status}): ${statusText || 'Please try again later'}`;
                    } else {
                        return `Unexpected error (${status}): ${statusText || 'Please try again'}`;
                    }
            }
        },
        
        // Update DOM element with new content
        updateDOMElement: function(selector, html, mode = 'replace') {
            const $target = $(selector);
            if ($target.length === 0) {
                console.warn('Target element not found:', selector);
                return;
            }
            
            switch (mode) {
                case 'replace':
                    $target.html(html);
                    break;
                case 'append':
                    $target.append(html);
                    break;
                case 'prepend':
                    $target.prepend(html);
                    break;
                default:
                    $target.html(html);
            }
        },
        
        // Show status message in appropriate container
        // $element can be the container itself or any element within it
        showStatusMessage: function(message, type = STATUS_TYPE.INFO, $element = null, timeout = null) {
            // If $element is provided, find its container (or itself if it IS the container)
            // Otherwise use the first container on the page
            const $container = $element ? $($element).closest(Tt.ATTR_V2_CONTAINER_SELECTOR) : $(Tt.ATTR_V2_CONTAINER_SELECTOR).first();
            const $statusMsg = $container.find(Tt.ATTR_V2_STATUS_MESSAGE_SELECTOR);
            
            if ($statusMsg.length === 0) return;
            
            // Map type to CSS class
            const cssClass = type === STATUS_TYPE.SUCCESS ? ATTR_V2_INTERNAL.STATUS_SUCCESS_CLASS : 
                           type === STATUS_TYPE.ERROR ? ATTR_V2_INTERNAL.STATUS_ERROR_CLASS : 
                           type === STATUS_TYPE.WARNING ? ATTR_V2_INTERNAL.STATUS_WARNING_CLASS :
                           ATTR_V2_INTERNAL.STATUS_INFO_CLASS;
            
            // Set default timeout based on type if not provided
            if (timeout === null) {
                timeout = type === STATUS_TYPE.SUCCESS ? 3000 : 5000;
            }
            
            // Update message with proper styling
            $statusMsg.text(message)
                     .removeClass(`${ATTR_V2_INTERNAL.STATUS_SUCCESS_CLASS} ${ATTR_V2_INTERNAL.STATUS_ERROR_CLASS} ${ATTR_V2_INTERNAL.STATUS_INFO_CLASS} ${ATTR_V2_INTERNAL.STATUS_WARNING_CLASS}`)
                     .addClass(cssClass + ' ml-2')  // ml-2 for consistency with existing usage
                     .show();
            
            // Auto-dismiss after specified timeout (0 = no auto-dismiss)
            if (timeout > 0) {
                setTimeout(() => {
                    $statusMsg.text('')
                             .attr('class', `${Tt.ATTR_V2_STATUS_MESSAGE_CLASS} ml-2`);  // Reset to base class
                }, timeout);
            }
        }
    };
    
    // Initialize all V2 containers when DOM is ready
    document.addEventListener('DOMContentLoaded', function() {
        _initializeAllContainers();
    });
    
    // No longer using antinode.js - initialization handled by custom Ajax callbacks
    
    // Listen for any modal shown events and initialize V2 containers
    $(document).on('shown.bs.modal', ATTR_V2_INTERNAL.MODAL_SELECTOR, function(e) {
        _initializeAllContainers();
        e.stopPropagation(); // Prevent bubbling to other handlers
    });
    
    // Container-aware utility function for updating form actions and browser history
    // This is a generic helper that can be called from template onclick handlers
    function _updateFormAction(newUrl, containerId, labelText = null) {
        if (!newUrl || !containerId) {
            console.warn('Tt.attr.updateFormAction: newUrl and containerId are required');
            return;
        }

        // Find the form within the specific container
        const $container = $(`#${containerId}`);
        if ($container.length === 0) {
            console.warn('Tt.attr.updateFormAction: Container not found:', containerId);
            return;
        }

        const $form = $container.find(Tt.ATTR_V2_FORM_CLASS_SELECTOR);
        if ($form.length === 0) {
            console.warn('Tt.attr.updateFormAction: No form found in container:', containerId);
            return;
        }

        // Update form action
        $form.attr('action', newUrl);

        // Update form display label if provided
        if (labelText) {
            const $label = $container.find(Tt.ATTR_V2_FORM_DISPLAY_LABEL_SELECTOR);
            if ($label.length > 0) {
                $label.text(labelText);
            }
        }

        // Update browser history without page reload
        history.pushState(null, '', newUrl);
    };
    
    
    // Multi-instance container initialization
    function _initializeAllContainers() {
        // Initialize all attribute editing containers found on page
        $(Tt.ATTR_V2_CONTAINER_SELECTOR).each(function() {
            _initializeContainer($(this));
        });
    }
    
    function _initializeContainer($container) {
        // Check if this container is already initialized to prevent double-initialization
        if ($container.data(ATTR_V2_INTERNAL.INITIALIZED_DATA_KEY)) {
            // Always reprocess AJAX handlers to handle newly loaded content
            _setupCustomAjaxHandlers($container);
            // Re-initialize textareas after content updates (DOM may have changed)
            _reinitializeTextareas($container);
            // Reinitialize dirty tracking for new content
            if (window.Tt.attr.dirtyTracking) {
                window.Tt.attr.dirtyTracking.reinitializeContainer($container.attr('id'));
            }
            return;
        }
        
        // Full container initialization - don't assume what persists across AJAX updates
        _setupBasicEventListeners($container);
        _initializeExpandableTextareas($container); // Must come BEFORE autosize
        _initializeAutosizeTextareas($container); // Now only applies to non-truncated
        // Note: Form submission handler removed - textarea sync now handled in Ajax submission
        _setupCustomAjaxHandlers($container); // NEW: Custom Ajax form handling
        
        // Reinitialize dirty tracking for this container
        if (window.Tt && window.Tt.attr && window.Tt.attr.dirtyTracking) {
            window.Tt.attr.dirtyTracking.reinitializeContainer($container.attr('id'));
        }
        
        // Handle auto-dismiss messages for this container
        _handleAutoDismissMessages($container);
        
        // Mark this container as initialized
        $container.data(ATTR_V2_INTERNAL.INITIALIZED_DATA_KEY, true);
    }
    
    function _handleAutoDismissMessages($container) {
        const $statusMsg = $container.find(Tt.ATTR_V2_STATUS_MESSAGE_SELECTOR);
        const $dismissibleElements = $statusMsg.find(Tt.ATTR_V2_AUTO_DISMISS_SELECTOR);
        if ($dismissibleElements.length > 0) {
            setTimeout(() => {
                $dismissibleElements.remove();
                // Hide the entire status message container if it's now empty
                if ($statusMsg.text().trim() === '') {
                    $statusMsg.hide();
                }
            }, 5000);
        }
    }
    
    // Setup custom Ajax handlers for forms and links in this container
    function _setupCustomAjaxHandlers($container) {
        // Handle main form submissions
        const $forms = $container.find(`form${Tt.ATTR_V2_FORM_CLASS_SELECTOR}`);
        $forms.each(function(index) {
            const form = this;
            const $form = $(form);
            
            // Remove any existing handlers to avoid duplicates
            $form.off(`submit.${ATTR_V2_INTERNAL.AJAX_EVENT_NAMESPACE}`);
            
            // Add custom Ajax submission handler
            $form.on(`submit.${ATTR_V2_INTERNAL.AJAX_EVENT_NAMESPACE}`, function(e) {
                e.preventDefault();
                
                _ajax.submitFormWithAjax(form);
            });
        });
        
        // Handle history links
        const $historyLinks = $container.find(Tt.ATTR_V2_HISTORY_LINK_SELECTOR);
        $historyLinks.each(function() {
            const $link = $(this);
            
            // Skip if already processed
            if ($link.data(ATTR_V2_INTERNAL.PROCESSED_DATA_KEY)) {
                return;
            }
            
            $link.data(ATTR_V2_INTERNAL.PROCESSED_DATA_KEY, true);
            $link.off(`click.${ATTR_V2_INTERNAL.AJAX_EVENT_NAMESPACE}`);
            
            $link.on(`click.${ATTR_V2_INTERNAL.AJAX_EVENT_NAMESPACE}`, function(e) {
                e.preventDefault();
                
                const url = $link.attr('href');
                
                // Server will return JSON response with target selector and HTML
                $.ajax({
                    url: url,
                    method: 'GET',
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                }).done((response) => {
                    _ajax.handleFormSuccess(response, $container.find(Tt.ATTR_V2_FORM_CLASS_SELECTOR));
                }).fail((xhr) => {
                    _ajax.handleFormError(xhr, $container.find(Tt.ATTR_V2_FORM_CLASS_SELECTOR));
                });
            });
        });
        
        // Handle value restore links  
        const $restoreLinks = $container.find(Tt.ATTR_V2_RESTORE_LINK_SELECTOR);
        $restoreLinks.each(function() {
            const $link = $(this);
            
            // Skip if already processed
            if ($link.data(ATTR_V2_INTERNAL.PROCESSED_DATA_KEY)) {
                return;
            }
            
            $link.data(ATTR_V2_INTERNAL.PROCESSED_DATA_KEY, true);
            $link.off(`click.${ATTR_V2_INTERNAL.AJAX_EVENT_NAMESPACE}`);
            
            $link.on(`click.${ATTR_V2_INTERNAL.AJAX_EVENT_NAMESPACE}`, function(e) {
                e.preventDefault();
                
                const url = $link.attr('href');
                
                // Server will return JSON response with target selector and HTML
                $.ajax({
                    url: url,
                    method: 'GET',
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                }).done((response) => {
                    _ajax.handleFormSuccess(response, $container.find(Tt.ATTR_V2_FORM_CLASS_SELECTOR));
                }).fail((xhr) => {
                    _ajax.handleFormError(xhr, $container.find(Tt.ATTR_V2_FORM_CLASS_SELECTOR));
                });
            });
        });
        
        // Handle file upload forms - find the context-specific file input
        const $fileInput = $container.find(Tt.ATTR_V2_FILE_INPUT_SELECTOR);
        
        if ($fileInput.length > 0) {
            // Skip if already processed
            if ($fileInput.data(ATTR_V2_INTERNAL.PROCESSED_DATA_KEY)) {
                return;
            }
            
            $fileInput.data(ATTR_V2_INTERNAL.PROCESSED_DATA_KEY, true);
            $fileInput.off(`change.${ATTR_V2_INTERNAL.AJAX_EVENT_NAMESPACE}`);
            
            $fileInput.on(`change.${ATTR_V2_INTERNAL.AJAX_EVENT_NAMESPACE}`, function(e) {
                const fileInput = this;
                const $uploadForm = $fileInput.closest('form');
                
                
                if (fileInput.files && fileInput.files[0] && $uploadForm.length) {
                    // Use our custom Ajax submission with scroll-to-new-content option
                    // File uploads append new content that users want to see
                    _ajax.submitFormWithAjax($uploadForm[0], {
                        scrollToNewContent: true
                    });
                } 
            });
        }
    }
    
    
    

    function _setupBasicEventListeners($container) {
        // Simple ENTER key prevention for attribute forms - scoped to this container
        const $forms = $container.find(`form${Tt.ATTR_V2_FORM_CLASS_SELECTOR}`);
        
        $forms.each(function() {
            const form = this;
            
            // Remove any existing keydown handlers to avoid duplicates
            $(form).off('keydown.attr-v2-enter');
            
            // Prevent ENTER from submitting forms (except textareas and submit buttons)
            $(form).on('keydown.attr-v2-enter', function(event) {
                if (event.key === 'Enter' && 
                    event.target.tagName !== 'TEXTAREA' && 
                    event.target.type !== 'submit') {
                    event.preventDefault();
                    return false;
                }
            });
        });
    }

    // Simple add attribute - just show the last (empty) formset form
    function _showAddAttribute(containerSelector = null) {
        // Find the last attribute card (should be the empty extra form)
        const scope = containerSelector ? $(containerSelector) : $(document);
        const attributeCards = scope.find(Tt.ATTR_V2_ATTRIBUTE_CARD_SELECTOR);
        
        if (attributeCards.length > 0) {
            const lastCard = attributeCards[attributeCards.length - 1];
            const $lastCard = $(lastCard);
            
            // Show the card if hidden
            $lastCard.show();
            
            // Focus on the name field
            const nameField = $lastCard.find('input[name$="-name"]')[0];
            if (nameField) {
                nameField.focus();
            }
            
            // Initialize autosize on any textarea in the new card
            const textarea = $lastCard.find('textarea')[0];
            if (textarea && !textarea.hasAttribute('data-autosize-initialized')) {
                autosize($(textarea));
                textarea.setAttribute('data-autosize-initialized', 'true');
            }
            
            // Scroll into view
            lastCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
    };
    
    // Removed dedicated add attribute form functions - using Django formset approach only
    
    
    window.markFileForDeletion = function(attributeId, containerSelector = null) {
        // Find the file card, scoped to container if provided
        const scope = containerSelector ? $(containerSelector) : $(document);
        const $fileCard = scope.find(`${Tt.ATTR_V2_FILE_CARD_SELECTOR}[${Tt.DATA_ATTRIBUTE_ID_ATTR}="${attributeId}"]`);
        if ($fileCard.length === 0) return;
        
        // The display "name" for a file is its attribute.value, *not* attribute.name
        const fileValue = $fileCard.find(Tt.ATTR_V2_FILE_TITLE_INPUT_SELECTOR).val().trim();

        // Find and mark the server-rendered DELETE field for deletion
        const $deleteField = $fileCard.find(`input[name="${Tt.ATTR_V2_DELETE_FILE_ATTR}"]`);
        if ($deleteField.length > 0) {
            // Set value to the attribute ID to mark for deletion
            $deleteField.val(attributeId);
            
            // Directly notify dirty tracking system
            const $container = $fileCard.closest(Tt.ATTR_V2_CONTAINER_SELECTOR);
            if ($container.length > 0 && window.Tt.attr.dirtyTracking) {
                const containerId = $container.attr('id');
                const instance = window.Tt.attr.dirtyTracking.getInstance(containerId);
                instance.handleFieldChange($deleteField[0]);
            }
        } else {
            console.warn(`DELETE field not found for file attribute ${attributeId}`);
            return;
        }
        
        // Visual feedback - CSS handles all styling
        $fileCard.addClass('marked-for-deletion');
        
        // Hide delete button and show undo button (both server-rendered)
        $fileCard.find(Tt.ATTR_V2_DELETE_BTN_SELECTOR).hide();
        $fileCard.find(Tt.ATTR_V2_UNDO_BTN_SELECTOR).show();
        
        // Show status message (scoped to container)
        _ajax.showStatusMessage(`"${fileValue}" will be deleted when you save`, STATUS_TYPE.WARNING, scope);
    };
    
    window.undoFileDeletion = function(attributeId, containerSelector = null) {
        // Find the file card, scoped to container if provided
        const scope = containerSelector ? $(containerSelector) : $(document);
        const $fileCard = scope.find(`${Tt.ATTR_V2_FILE_CARD_SELECTOR}[${Tt.DATA_ATTRIBUTE_ID_ATTR}="${attributeId}"]`);
        if ($fileCard.length === 0) return;

        // The display "name" for a file is its attribute.value, *not* attribute.name
        const fileValue = $fileCard.find(Tt.ATTR_V2_FILE_TITLE_INPUT_SELECTOR).val().trim();

        // Unmark the DELETE field
        const $deleteField = $fileCard.find(`input[name="${Tt.ATTR_V2_DELETE_FILE_ATTR}"]`);
        if ($deleteField.length > 0) {
            $deleteField.val("");
            
            // Directly notify dirty tracking system
            const $container = $fileCard.closest(Tt.ATTR_V2_CONTAINER_SELECTOR);
            if ($container.length > 0 && window.Tt.attr.dirtyTracking) {
                const containerId = $container.attr('id');
                const instance = window.Tt.attr.dirtyTracking.getInstance(containerId);
                instance.handleFieldChange($deleteField[0]);
            }
        }
        
        // Remove visual feedback - CSS handles all styling
        $fileCard.removeClass('marked-for-deletion');
        
        // Show delete button and hide undo button (both server-rendered)
        $fileCard.find(Tt.ATTR_V2_DELETE_BTN_SELECTOR).show();
        $fileCard.find(Tt.ATTR_V2_UNDO_BTN_SELECTOR).hide();
        
        // Show status message (scoped to container)
        _ajax.showStatusMessage(`Deletion of "${fileValue}" cancelled`, STATUS_TYPE.SUCCESS, scope);
    };
    
    // History functionality now handled by antinode async pattern
    // History button uses data-async to load content, no JavaScript needed
    
    window.markAttributeForDeletion = function(attributeId, containerSelector = null) {
        // Find the attribute card, scoped to container if provided
        const scope = containerSelector ? $(containerSelector) : $(document);
        const $attributeCard = scope.find(`[${Tt.DATA_ATTRIBUTE_ID_ATTR}="${attributeId}"]`);
        if ($attributeCard.length === 0) return;
        
        const attributeName = $attributeCard.find(Tt.ATTR_V2_ATTRIBUTE_NAME_SELECTOR).text().trim().replace('•', '').trim();
        
        // Find and mark the server-rendered DELETE field for deletion
        const $deleteField = $attributeCard.find('input[name$="-DELETE"]');
        if ($deleteField.length > 0) {
            // For hidden fields, set value to "on" (what browsers send for checked checkboxes)
            $deleteField.val("on");
        } else {
            console.warn(`DELETE field not found for attribute ${attributeId}`);
            return;
        }
        
        // Visual feedback - CSS handles all styling
        $attributeCard.addClass('marked-for-deletion');
        
        // Hide delete button and show undo button (both server-rendered)
        $attributeCard.find(Tt.ATTR_V2_DELETE_BTN_SELECTOR).hide();
        $attributeCard.find(Tt.ATTR_V2_UNDO_BTN_SELECTOR).show();
        
        // Show status message (scoped to container)
        _ajax.showStatusMessage(`"${attributeName}" will be deleted when you save`, STATUS_TYPE.WARNING, scope);
    };
    
    window.undoAttributeDeletion = function(attributeId, containerSelector = null) {
        // Find the attribute card, scoped to container if provided
        const scope = containerSelector ? $(containerSelector) : $(document);
        const $attributeCard = scope.find(`[${Tt.DATA_ATTRIBUTE_ID_ATTR}="${attributeId}"]`);
        if ($attributeCard.length === 0) return;
        
        const attributeName = $attributeCard.find(Tt.ATTR_V2_ATTRIBUTE_NAME_SELECTOR).text().trim().replace('•', '').trim();
        
        // Unmark the DELETE field
        const $deleteField = $attributeCard.find('input[name$="-DELETE"]');
        if ($deleteField.length > 0) {
            $deleteField.val("");
        }
        
        // Remove visual feedback - CSS handles all styling
        $attributeCard.removeClass('marked-for-deletion');
        
        // Show delete button and hide undo button (both server-rendered)
        $attributeCard.find(Tt.ATTR_V2_DELETE_BTN_SELECTOR).show();
        $attributeCard.find(Tt.ATTR_V2_UNDO_BTN_SELECTOR).hide();
        
        // Show status message (scoped to container)
        _ajax.showStatusMessage(`Deletion of "${attributeName}" cancelled`, STATUS_TYPE.SUCCESS, scope);
    };

    function _toggleSecretField(button) {
        const $button = $(button);
        const $input = $button.closest(Tt.ATTR_V2_SECRET_INPUT_WRAPPER_SELECTOR).find(Tt.ATTR_V2_SECRET_INPUT_SELECTOR);
        const $showIcon = $button.find(Tt.ATTR_V2_ICON_SHOW_SELECTOR);
        const $hideIcon = $button.find(Tt.ATTR_V2_ICON_HIDE_SELECTOR);
        const isPassword = $input.attr('type') === 'password';
        
        // Check if field is disabled (non-editable attributes should stay disabled)
        const isDisabled = $input.prop('disabled');
        
        if (isPassword) {
            // Currently hidden - show as text and make editable
            $input.attr('type', 'text');
            $button.attr('title', 'Hide value');
            
            // Remove readonly to allow editing, but only if not disabled
            if (!isDisabled) {
                $input.prop('readonly', false);
                $input.removeAttr('readonly');
            }
            
            // Show hide icon, hide show icon
            $showIcon.hide();
            $hideIcon.show();
        } else {
            // Currently showing - hide as password and make readonly
            $input.attr('type', 'password');
            $button.attr('title', 'Show value');
            
            // Set readonly to prevent editing obfuscated text
            if (!isDisabled) {
                $input.prop('readonly', true);
                $input.attr('readonly', 'readonly');
            }
            
            // Show show icon, hide hide icon
            $showIcon.show();
            $hideIcon.hide();
        }
    };
    
    // Update hidden field when boolean checkbox changes
    function _updateBooleanHiddenField(checkbox) {
        const hiddenFieldId = checkbox.getAttribute(Tt.DATA_HIDDEN_FIELD_ATTR);
        const hiddenField = document.getElementById(hiddenFieldId);
        
        if (hiddenField) {
            // Update hidden field value based on checkbox state
            hiddenField.value = checkbox.checked ? 'True' : 'False';
        }
    };
    
    
    // Initialize autosize for all textareas in the modal
    function _initializeAutosizeTextareas() {
        // Initialize autosize for existing textareas, but exclude truncated ones
        const textareas = $(Tt.ATTR_V2_TEXTAREA_SELECTOR).not('.truncated');
        if (textareas.length > 0) {
            autosize(textareas);
            
            // Update when modal is shown (in case of display issues)
            $('.modal').on('shown.bs.modal', function () {
                autosize.update(textareas);
            });
        }
    }
    
    // Lightweight reinitialization for ajax content updates
    function _reinitializeTextareas($container = null) {
        // Find textareas that need initialization (scoped to container if provided)
        const textareas = $container ? 
            $container.find(Tt.ATTR_V2_TEXTAREA_SELECTOR) : 
            $(Tt.ATTR_V2_TEXTAREA_SELECTOR);
        
        // Remove any previous autosize instances to avoid duplicates
        textareas.each(function() {
            if (this._autosize) {
                autosize.destroy($(this));
            }
        });
        
        // Initialize overflow state based on server-rendered attributes
        textareas.each(function() {
            const textarea = $(this);
            const wrapper = textarea.closest(Tt.ATTR_V2_TEXT_VALUE_WRAPPER_SELECTOR);
            const isOverflowing = wrapper.attr(Tt.DATA_OVERFLOW_ATTR) === 'true';
            
            // Check if this is a display field (new pattern) or legacy textarea
            const hiddenFieldId = textarea.attr(Tt.DATA_HIDDEN_FIELD_ATTR);
            const hiddenField = hiddenFieldId ? $('#' + hiddenFieldId) : null;
            
            if (isOverflowing) {
                if (hiddenField && hiddenField.length > 0) {
                    _applyTruncationFromHidden(textarea, hiddenField);
                } else {
                    _applyTruncation(textarea);
                }
            }
        });
        
        // THEN: Apply autosize only to editable, non-truncated textareas 
        // (readonly textareas don't need dynamic resizing)
        const editableTextareas = $(Tt.ATTR_V2_TEXTAREA_SELECTOR).not('.truncated').not('[readonly]');
        if (editableTextareas.length > 0) {
            autosize(editableTextareas);
        }
        
        // Trigger autosize update for editable textareas only
        if (editableTextareas.length > 0) {
            autosize.update(editableTextareas);
        }
    }
    
    // Update overflow state based on current content
    function _updateOverflowState(textarea) {
        const content = textarea.val() || '';
        const lineCount = (content.match(/\n/g) || []).length + 1;
        const overflows = lineCount > 4;
        
        const wrapper = textarea.closest(Tt.ATTR_V2_TEXT_VALUE_WRAPPER_SELECTOR);
        wrapper.attr(Tt.DATA_OVERFLOW_ATTR, overflows ? 'true' : 'false');
        wrapper.attr(Tt.DATA_LINE_COUNT_ATTR, lineCount);
        
        return { lineCount, overflows };
    }
    
    // Apply truncation using hidden field as source (new pattern)
    function _applyTruncationFromHidden(displayField, hiddenField) {
        const fullValue = hiddenField.val() || '';
        
        // Destroy autosize first to prevent height override
        if (window.autosize && displayField[0]._autosize) {
            autosize.destroy(displayField);
        }
        
        const lines = fullValue.split('\n');
        const truncatedValue = lines.slice(0, 4).join('\n');
        
        // Apply truncated display
        displayField.val(truncatedValue + '...');
        // Clear any explicit height style that might override rows
        displayField.css('height', '');
        displayField.attr('rows', 4);
        displayField.attr('readonly', 'readonly');
        displayField.prop('readonly', true);
        displayField.addClass(ATTR_V2_INTERNAL.TRUNCATED_CLASS);
        
        // Show expand controls
        const wrapper = displayField.closest(Tt.ATTR_V2_TEXT_VALUE_WRAPPER_SELECTOR);
        const expandControls = wrapper.find(Tt.ATTR_V2_EXPAND_CONTROLS_SELECTOR);
        expandControls.show();
        
        // Add click handler to make textarea clickable for expansion
        displayField.off('click.expand').on('click.expand', function(e) {
            // Only expand if textarea is currently in readonly/truncated state
            if ($(this).prop('readonly') && $(this).hasClass('truncated')) {
                e.preventDefault();
                e.stopPropagation();
                
                // Find the associated "Show more" button and trigger its click
                const expandButton = expandControls.find('button');
                if (expandButton.length > 0) {
                    expandButton.click();
                }
            }
            // If not readonly/truncated, let normal textarea behavior happen (cursor placement)
        });
    }
    
    // Legacy function - kept for compatibility with reinitializeTextareas
    function _applyTruncation(textarea) {
        const value = textarea.val() || '';
        
        // Destroy autosize first to prevent height override
        if (window.autosize && textarea[0]._autosize) {
            autosize.destroy(textarea);
        }
        
        const lines = value.split('\n');
        const truncatedValue = lines.slice(0, 4).join('\n');
        
        // Store full value and show truncated
        textarea.data('full-value', value);
        textarea.data('truncated-value', truncatedValue);
        textarea.val(truncatedValue + '...');
        // Clear any explicit height style that might override rows
        textarea.css('height', '');
        textarea.attr('rows', 4);
        textarea.attr('readonly', 'readonly');
        textarea.prop('readonly', true);
        textarea.addClass(ATTR_V2_INTERNAL.TRUNCATED_CLASS);
        
        // Show expand controls
        const wrapper = textarea.closest(Tt.ATTR_V2_TEXT_VALUE_WRAPPER_SELECTOR);
        const expandControls = wrapper.find(Tt.ATTR_V2_EXPAND_CONTROLS_SELECTOR);
        expandControls.show();
    }
    
    function _initializeExpandableTextareas() {
        // Initialize based on server-rendered overflow state using hidden field pattern
        const displayTextareas = $(Tt.ATTR_V2_DISPLAY_FIELD_SELECTOR);
        
        displayTextareas.each(function() {
            const displayField = $(this);
            const isOverflowing = displayField.attr(Tt.DATA_OVERFLOW_ATTR) === 'true';
            const hiddenFieldId = displayField.attr(Tt.DATA_HIDDEN_FIELD_ATTR);
            const hiddenField = $('#' + hiddenFieldId);
            
            if (isOverflowing && hiddenField.length > 0) {
                // Apply truncation using hidden field as source
                _applyTruncationFromHidden(displayField, hiddenField);
            }
            // For non-overflowing content, display field already has correct content from server
        });
    }
    
    // Global function for expand/collapse button (namespaced) - enhanced for hidden field pattern
    function _toggleExpandedView(button) {
        const $button = $(button);
        const wrapper = $button.closest(Tt.ATTR_V2_TEXT_VALUE_WRAPPER_SELECTOR);
        const displayField = wrapper.find(Tt.ATTR_V2_DISPLAY_FIELD_SELECTOR
                                          + ', ' + Tt.ATTR_V2_TEXTAREA_SELECTOR); // Support both new and legacy
        const showMoreText = $button.find(Tt.ATTR_V2_SHOW_MORE_TEXT_SELECTOR);
        const showLessText = $button.find(Tt.ATTR_V2_SHOW_LESS_TEXT_SELECTOR);
        
        // Get hidden field if using new pattern
        const hiddenFieldId = displayField.attr(Tt.DATA_HIDDEN_FIELD_ATTR);
        const hiddenField = hiddenFieldId ? $('#' + hiddenFieldId) : null;
        
        if (displayField.prop('readonly')) {
            // Currently collapsed - expand it (Show More)
            let fullValue;
            if (hiddenField && hiddenField.length > 0) {
                // New pattern: Get from hidden field
                fullValue = hiddenField.val() || '';
            } else {
                // Legacy pattern: Get from stored data
                fullValue = displayField.data('full-value') || '';
            }
            
            const lineCount = (fullValue.match(/\n/g) || []).length + 1;
            
            displayField.val(fullValue);
            displayField.attr('rows', Math.max(lineCount, 5));
            displayField.prop('readonly', false);
            displayField.attr('readonly', false); // Remove readonly attribute
            displayField.removeClass(ATTR_V2_INTERNAL.TRUNCATED_CLASS);
            
            showMoreText.hide();
            showLessText.show();
            
            // Apply autosize now that display field is editable
            if (window.autosize) {
                autosize(displayField);
                autosize.update(displayField);
            }
            
            // Set up listener to track content changes
            displayField.off('input.overflow').on('input.overflow', function() {
                _updateOverflowState($(this));
            });
        } else {
            // Currently expanded - check if we should collapse (Show Less)
            const { lineCount, overflows } = _updateOverflowState(displayField);
            
            if (!overflows) {
                // Content now fits in 4 lines - remove truncation UI
                displayField.attr('rows', lineCount);
                displayField.prop('readonly', false);
                displayField.removeClass(ATTR_V2_INTERNAL.TRUNCATED_CLASS);
                wrapper.find(Tt.ATTR_V2_EXPAND_CONTROLS_SELECTOR).hide();
                
                // Update wrapper state
                wrapper.attr(Tt.DATA_OVERFLOW_ATTR, 'false');
                
                // Sync to hidden field if using new pattern
                if (hiddenField && hiddenField.length > 0) {
                    hiddenField.val(displayField.val());
                }
            } else {
                // Still overflows - apply truncation with hidden field sync
                const currentValue = displayField.val();
                
                // Sync current content to hidden field before truncating display
                if (hiddenField && hiddenField.length > 0) {
                    hiddenField.val(currentValue);
                    
                    // Apply truncation using hidden field
                    _applyTruncationFromHidden(displayField, hiddenField);
                } else {
                    // Legacy pattern
                    _applyTruncation(displayField);
                }
                
                showMoreText.show();
                showLessText.hide();
            }
            
            // Remove the input listener
            displayField.off('input.overflow');
        }
    }
    
    // Sync textarea values to hidden fields before form submission
    function _syncTextareaValuesToHiddenFields($container) {
        // Process all display fields within this container
        $container.find(Tt.ATTR_V2_DISPLAY_FIELD_SELECTOR).each(function() {
            const displayField = $(this);
            const hiddenFieldId = displayField.attr(Tt.DATA_HIDDEN_FIELD_ATTR);
            const hiddenField = hiddenFieldId ? $container.find('#' + hiddenFieldId) : null;
            
            if (hiddenField && hiddenField.length > 0) {
                // Only sync if display field is NOT showing truncated data
                if (!displayField.prop('readonly') && !displayField.hasClass(ATTR_V2_INTERNAL.TRUNCATED_CLASS)) {
                    // Display field contains user's edits - copy to hidden field
                    const displayValue = displayField.val();
                    hiddenField.val(displayValue);
                }
                // Display field is readonly/truncated - hidden field already has correct full content
            }
        });
    }
    
    
})();
