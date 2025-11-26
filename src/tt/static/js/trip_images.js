/*
 * Trip Tools - Trip Images JavaScript
 *
 * This module handles:
 * 1. Image picker functionality for selecting reference images in modals
 * 2. Drag-and-drop image uploads with progress tracking
 *
 * UPLOAD COMPONENT USAGE:
 *
 *   Tt.createImageUpload({
 *     uploadZoneSelector: '#my-upload-zone',      // Required: drag-drop area
 *     fileInputSelector: '#my-file-input',        // Required: hidden file input
 *     progressSectionSelector: '#my-progress',    // Optional: progress container
 *     progressCountSelector: '#my-count',         // Optional: "X of Y files" display
 *     fileProgressListSelector: '#my-list',       // Optional: individual file progress
 *     uploadedGridSelector: '#my-grid',           // Optional: uploaded images display
 *     uploadedCountSelector: '#my-uploaded',      // Optional: total uploaded count
 *     uploadEndpoint: '/custom/upload/',          // Optional: defaults to current URL
 *     maxFiles: 10,                               // Optional: defaults to 50
 *     onSuccess: function(result) { ... },        // Optional: per-file success callback
 *     onError: function(error) { ... },           // Optional: per-file error callback
 *     onComplete: function(allResults) { ... }    // Optional: all files done callback
 *   });
 */

// ============================================================================
// IMAGE PICKER - Reference image selection in modals
// ============================================================================

(function($) {
    'use strict';

    window.Tt = window.Tt || {};

    var TtTripImages = {
        selectReferenceImage: function(clickedElement) {
            _selectReferenceImage(clickedElement);
        }
    };

    window.Tt.tripImages = TtTripImages;

    // Global function for onclick handlers in templates (legacy)
    window.selectReferenceImage = function(clickedElement) {
        _selectReferenceImage(clickedElement);
    };

    // Initialize delegated event handlers for image picker cards
    $(document).ready(function() {
        // Delegated click handler for image picker cards
        $('body').on('click', '.' + Tt.DIVID.IMAGE_PICKER_CARD_CLASS, function(e) {
            e.preventDefault();
            _selectReferenceImage(this);
        });

        // Delegated keyboard handler for image picker cards (Enter/Space)
        $('body').on('keydown', '.' + Tt.DIVID.IMAGE_PICKER_CARD_CLASS, function(e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                _selectReferenceImage(this);
            }
        });
    });

    function _selectReferenceImage(clickedElement) {
        var $card = $(clickedElement).closest(Tt.IMAGE_PICKER_CARD_SELECTOR);
        if ($card.length === 0) {
            console.warn('selectReferenceImage: Could not find image picker card');
            return;
        }

        // Find the containing modal to scope all element lookups
        var $modal = $card.closest('.modal');
        if ($modal.length === 0) {
            console.warn('selectReferenceImage: Could not find containing modal');
            return;
        }

        // Get image data from card's data attributes
        var imageUuid = $card.data(Tt.IMAGE_PICKER_UUID_ATTR);
        var thumbnailUrl = $card.data(Tt.IMAGE_PICKER_THUMBNAIL_URL_ATTR);
        var caption = $card.data(Tt.IMAGE_PICKER_CAPTION_ATTR) || 'Untitled';

        // Update hidden input (scoped to modal)
        var $uuidInput = $modal.find(Tt.IMAGE_PICKER_UUID_INPUT_SELECTOR);
        $uuidInput.val(imageUuid);

        // Update preview image (scoped to modal)
        var $preview = $modal.find(Tt.IMAGE_PICKER_PREVIEW_SELECTOR);
        var $img = $('<img>')
            .attr('src', thumbnailUrl)
            .attr('alt', 'Selected reference')
            .css({
                'width': '100%',
                'height': '100%',
                'object-fit': 'cover'
            });
        $preview.empty().append($img);

        // Update caption text (scoped to modal)
        var $caption = $modal.find(Tt.IMAGE_PICKER_CAPTION_SELECTOR);
        $caption.text(caption);

        // Enable the SET button (scoped to modal)
        var $setBtn = $modal.find(Tt.IMAGE_PICKER_SET_BTN_SELECTOR);
        $setBtn.prop('disabled', false);

        // Update visual selection state (scoped to modal)
        $modal.find(Tt.IMAGE_PICKER_CARD_SELECTOR).each(function() {
            var $thisCard = $(this);
            if ($thisCard.data(Tt.IMAGE_PICKER_UUID_ATTR) === imageUuid) {
                $thisCard.css('border-color', '#007bff');
            } else {
                $thisCard.css('border-color', 'transparent');
            }
        });
    }

})(jQuery);

// ============================================================================
// IMAGE UPLOAD - Drag-and-drop uploads with progress tracking
// ============================================================================

(function() {
    'use strict';

    // Default configuration
    var DEFAULT_CONFIG = {
        uploadZoneSelector: null,
        fileInputSelector: null,
        progressSectionSelector: null,
        progressCountSelector: null,
        fileProgressListSelector: null,
        uploadedGridSelector: null,
        uploadedCountSelector: null,
        uploadEndpoint: null,  // null = use current URL
        maxFiles: 50,
        onSuccess: null,  // Callback: function(results) { }
        onError: null,    // Callback: function(error) { }
        onComplete: null  // Callback: function(allResults) { }
    };

    // Global timeout constant
    var UPLOAD_TIMEOUT_MS = 120000; // 2 minutes per file

    /**
     * Create a configurable image upload component
     * @param {Object} config - Configuration object
     * @returns {Object} Public API for the upload component
     */
    function createImageUpload(config) {
        // Merge config with defaults
        var settings = Object.assign({}, DEFAULT_CONFIG, config);

        // Validate required selectors
        if (!settings.uploadZoneSelector) {
            throw new Error('createImageUpload: uploadZoneSelector is required');
        }
        if (!settings.fileInputSelector) {
            throw new Error('createImageUpload: fileInputSelector is required');
        }

        // Instance state management
        var uploadQueue = [];
        var completedCount = 0;
        var currentUploadIndex = 0;
        var isUploading = false;

        // DOM element cache
        var $uploadZone;
        var $fileInput;
        var $progressSection;
        var $progressCount;
        var $fileProgressList;
        var $uploadedGrid;
        var $uploadedCount;

        /**
         * Initialize the upload interface
         */
        function init() {
            cacheDOMElements();
            initDragAndDrop();
            initFileInput();
        }

        /**
         * Cache DOM elements for performance
         */
        function cacheDOMElements() {
            $uploadZone = $(settings.uploadZoneSelector);
            $fileInput = $(settings.fileInputSelector);
            $progressSection = settings.progressSectionSelector ? $(settings.progressSectionSelector) : null;
            $progressCount = settings.progressCountSelector ? $(settings.progressCountSelector) : null;
            $fileProgressList = settings.fileProgressListSelector ? $(settings.fileProgressListSelector) : null;
            $uploadedGrid = settings.uploadedGridSelector ? $(settings.uploadedGridSelector) : null;
            $uploadedCount = settings.uploadedCountSelector ? $(settings.uploadedCountSelector) : null;

            // Validate required elements exist
            if ($uploadZone.length === 0) {
                console.error('createImageUpload: Upload zone not found:', settings.uploadZoneSelector);
            }
            if ($fileInput.length === 0) {
                console.error('createImageUpload: File input not found:', settings.fileInputSelector);
            }
        }

        /**
         * Initialize drag-and-drop handlers
         */
        function initDragAndDrop() {
            $uploadZone.on('dragover', handleDragOver);
            $uploadZone.on('dragleave', handleDragLeave);
            $uploadZone.on('drop', handleDrop);
            $uploadZone.on('click', function(e) {
                if (e.target.tagName !== 'BUTTON' && e.target.tagName !== 'INPUT') {
                    $fileInput.click();
                }
            });
        }

        /**
         * Initialize file input handler
         */
        function initFileInput() {
            $fileInput.on('change', function(e) {
                var files = e.target.files;
                if (files.length > 0) {
                    handleFiles(files);
                }
                // Reset input so same files can be selected again
                e.target.value = '';
            });
        }

        /**
         * Handle drag over event
         */
        function handleDragOver(e) {
            e.preventDefault();
            e.stopPropagation();
            $uploadZone.addClass('tt-upload-dragover');
        }

        /**
         * Handle drag leave event
         */
        function handleDragLeave(e) {
            e.preventDefault();
            e.stopPropagation();
            $uploadZone.removeClass('tt-upload-dragover');
        }

        /**
         * Handle drop event
         */
        function handleDrop(e) {
            e.preventDefault();
            e.stopPropagation();
            $uploadZone.removeClass('tt-upload-dragover');

            var files = e.originalEvent.dataTransfer.files;
            if (files.length > 0) {
                handleFiles(files);
            }
        }

        /**
         * Handle file selection
         */
        function handleFiles(files) {
            var fileArray = Array.from(files);

            // Validate file count
            if (fileArray.length > settings.maxFiles) {
                alert('Too many files selected. Maximum ' + settings.maxFiles + ' files allowed per batch.');
                return;
            }

            // Validate files
            var validFiles = fileArray.filter(function(file) {
                return validateFile(file);
            });

            if (validFiles.length === 0) {
                alert('No valid image files selected. Please select JPG, PNG, or HEIC files under 20MB.');
                return;
            }

            // Reset state
            uploadQueue = validFiles.map(function(file, index) {
                return {
                    file: file,
                    id: 'file-' + Date.now() + '-' + index,
                    status: 'queued',
                    progress: 0
                };
            });

            completedCount = 0;
            currentUploadIndex = 0;
            isUploading = false;

            // Show progress section if available
            if ($progressSection && $progressSection.length > 0) {
                $progressSection.addClass('active');
            }
            updateProgressCount();

            // Create progress items for each file
            if ($fileProgressList && $fileProgressList.length > 0) {
                $fileProgressList.empty();
                uploadQueue.forEach(function(fileItem) {
                    createProgressItem(fileItem);
                });
            }

            // Start sequential uploads
            uploadNextFile();
        }

        /**
         * Validate file
         */
        function validateFile(file) {
            var maxSize = 20 * 1024 * 1024; // 20MB
            var validTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/heic'];

            if (file.size > maxSize) {
                return false;
            }

            var fileType = file.type.toLowerCase();
            var fileName = file.name.toLowerCase();

            if (validTypes.includes(fileType)) {
                return true;
            }

            // Check extension for HEIC (some browsers don't set correct MIME type)
            if (fileName.endsWith('.heic')) {
                return true;
            }

            return false;
        }

        /**
         * Create progress item HTML
         */
        function createProgressItem(fileItem) {
            var $progressItem = $('<div></div>')
                .addClass('tt-file-progress-item')
                .attr('id', fileItem.id);

            var fileSize = formatFileSize(fileItem.file.size);

            var html =
                '<div class="tt-file-header">' +
                    '<div class="tt-file-icon"></div>' +
                    '<div class="tt-file-info">' +
                        '<div class="tt-file-name">' + escapeHtml(fileItem.file.name) + '</div>' +
                        '<div class="tt-file-size">' + fileSize + '</div>' +
                    '</div>' +
                    '<div class="tt-file-status" data-status-target>' +
                        'Queued' +
                    '</div>' +
                '</div>' +
                '<div class="tt-progress-bar-container" style="display: none;">' +
                    '<div class="tt-progress-bar-fill" data-progress-bar></div>' +
                '</div>' +
                '<div class="tt-progress-details" data-details-target></div>';

            $progressItem.html(html);
            $fileProgressList.append($progressItem);
        }

        /**
         * Upload next file in queue (sequential processing)
         */
        function uploadNextFile() {
            // Check if all files are processed
            if (currentUploadIndex >= uploadQueue.length) {
                isUploading = false;

                // Call onComplete callback if provided
                if (settings.onComplete && typeof settings.onComplete === 'function') {
                    var allResults = uploadQueue.map(function(item) {
                        return {
                            file: item.file,
                            status: item.status,
                            result: item.result
                        };
                    });
                    settings.onComplete(allResults);
                }
                return;
            }

            // Prevent concurrent uploads
            if (isUploading) {
                return;
            }

            isUploading = true;
            var fileItem = uploadQueue[currentUploadIndex];

            // Upload single file
            uploadSingleFile(fileItem, currentUploadIndex);
        }

        /**
         * Upload a single file
         */
        function uploadSingleFile(fileItem, index) {
            var formData = new FormData();
            formData.append('files', fileItem.file);

            // Mark as uploading
            updateFileStatus(fileItem.id, 'uploading', 'Uploading...', 0);

            // Track XHR for timeout handling
            var timeoutId = setTimeout(function() {
                console.error('Upload timeout for file:', fileItem.file.name);
                handleSingleFileError(fileItem, 'Upload timed out after ' + (UPLOAD_TIMEOUT_MS / 1000) + ' seconds');
            }, UPLOAD_TIMEOUT_MS);

            // Determine upload endpoint
            var uploadUrl = settings.uploadEndpoint || window.location.pathname;

            // Use jQuery AJAX for file upload
            $.ajax({
                url: uploadUrl,
                type: 'POST',
                data: formData,
                processData: false,
                contentType: false,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                },
                timeout: UPLOAD_TIMEOUT_MS,
                xhr: function() {
                    var xhr = new window.XMLHttpRequest();
                    // Upload progress tracking
                    xhr.upload.addEventListener('progress', function(e) {
                        if (e.lengthComputable) {
                            var percentComplete = Math.round((e.loaded / e.total) * 100);
                            updateFileStatus(fileItem.id, 'uploading', 'Uploading...', percentComplete);
                        }
                    }, false);
                    return xhr;
                },
                success: function(data) {
                    clearTimeout(timeoutId);
                    handleSingleFileResponse(fileItem, data, index);
                },
                error: function(xhr, textStatus, errorThrown) {
                    clearTimeout(timeoutId);
                    var errorMsg = buildErrorMessage(xhr, textStatus, errorThrown);
                    handleSingleFileError(fileItem, errorMsg);
                }
            });
        }

        /**
         * Handle single file upload response
         */
        function handleSingleFileResponse(fileItem, data, index) {
            if (!data.files || !Array.isArray(data.files) || data.files.length === 0) {
                console.error('Invalid response format for file:', fileItem.file.name, data);
                handleSingleFileError(fileItem, 'Server returned invalid response');
                return;
            }

            // Get the first (and only) file result
            var fileResult = data.files[0];

            if (fileResult.status === 'success') {
                completedCount++;
                var details = buildSuccessDetails(fileResult);
                updateFileStatus(fileItem.id, 'success', 'Complete', 100, details);

                // Store result in queue item
                uploadQueue[index].status = 'success';
                uploadQueue[index].result = fileResult;

                // Add to grid
                addImageToGrid(fileResult);

                // Call onSuccess callback if provided
                if (settings.onSuccess && typeof settings.onSuccess === 'function') {
                    settings.onSuccess(fileResult);
                }
            } else {
                completedCount++;
                var errorMsg = fileResult.error_message || 'Upload failed';
                updateFileStatus(fileItem.id, 'error', 'Failed', null, errorMsg);

                // Store error in queue item
                uploadQueue[index].status = 'error';
                uploadQueue[index].error = errorMsg;

                // Call onError callback if provided
                if (settings.onError && typeof settings.onError === 'function') {
                    settings.onError({
                        file: fileItem.file,
                        error: errorMsg
                    });
                }
            }

            updateProgressCount();
            updateUploadedCount();

            // Move to next file
            currentUploadIndex++;
            isUploading = false;
            uploadNextFile();
        }

        /**
         * Handle single file upload error
         */
        function handleSingleFileError(fileItem, errorMsg) {
            console.error('Upload error for file:', fileItem.file.name, errorMsg);

            completedCount++;
            updateFileStatus(fileItem.id, 'error', 'Failed', null, errorMsg);
            updateProgressCount();

            // Store error in queue item
            var itemIndex = uploadQueue.findIndex(function(item) {
                return item.id === fileItem.id;
            });
            if (itemIndex >= 0) {
                uploadQueue[itemIndex].status = 'error';
                uploadQueue[itemIndex].error = errorMsg;
            }

            // Call onError callback if provided
            if (settings.onError && typeof settings.onError === 'function') {
                settings.onError({
                    file: fileItem.file,
                    error: errorMsg
                });
            }

            // Move to next file even after error
            currentUploadIndex++;
            isUploading = false;
            uploadNextFile();
        }

        /**
         * Build error message from AJAX error
         */
        function buildErrorMessage(xhr, textStatus, errorThrown) {
            if (textStatus === 'timeout') {
                return 'Upload timed out - file may be too large or connection too slow';
            }

            if (xhr.status === 413) {
                return 'File too large for server (413 error)';
            }

            if (xhr.status === 0) {
                return 'Network error - please check your connection';
            }

            if (xhr.status >= 500) {
                return 'Server error (' + xhr.status + ') - please try again';
            }

            if (xhr.status >= 400) {
                // Try to parse error message from response
                try {
                    var response = JSON.parse(xhr.responseText);
                    if (response.error) {
                        return response.error;
                    }
                } catch (e) {
                    // Ignore JSON parse errors
                }
                return 'Upload failed (' + xhr.status + ')';
            }

            return errorThrown || 'Upload failed - unknown error';
        }

        /**
         * Update file status
         */
        function updateFileStatus(fileId, status, statusText, progress, details) {
            var $progressItem = $('#' + fileId);
            if ($progressItem.length === 0) return;

            // Update item class
            $progressItem.attr('class', 'tt-file-progress-item ' + status);

            // Update status badge
            var $statusTarget = $progressItem.find('[data-status-target]');
            if ($statusTarget.length > 0) {
                $statusTarget.attr('class', 'tt-file-status ' + status);

                var iconHtml = '';
                if (status === 'uploading' || status === 'processing') {
                    iconHtml = '<span class="tt-spinner"></span>';
                } else if (status === 'success') {
                    iconHtml = '<span style="color: var(--success-color);">&#10003;</span>';
                } else if (status === 'error') {
                    iconHtml = '<span style="color: var(--error-color);">!</span>';
                }

                $statusTarget.html(iconHtml + ' ' + statusText);
            }

            // Update progress bar
            var $progressBarContainer = $progressItem.find('.tt-progress-bar-container');
            var $progressBar = $progressItem.find('[data-progress-bar]');

            if (progress !== null && $progressBarContainer.length > 0 && $progressBar.length > 0) {
                $progressBarContainer.show();
                $progressBar.css('width', progress + '%');

                if (status === 'success') {
                    $progressBar.addClass('success');
                }
            }

            // Update details
            var $detailsTarget = $progressItem.find('[data-details-target]');
            if ($detailsTarget.length > 0 && details) {
                $detailsTarget.text(details);
                $detailsTarget.attr('class', 'tt-progress-details ' + status);
            }
        }

        /**
         * Build success details text
         */
        function buildSuccessDetails(fileResult) {
            var parts = [];

            if (fileResult.metadata) {
                var meta = fileResult.metadata;

                if (meta.datetime_utc) {
                    var date = new Date(meta.datetime_utc);
                    parts.push('Date: ' + date.toLocaleString());
                }

                if (meta.latitude && meta.longitude) {
                    parts.push('Location: ' + meta.latitude.toFixed(4) + ', ' + meta.longitude.toFixed(4));
                }

                if (parts.length > 0) {
                    return 'EXIF extracted - ' + parts.join(' - ');
                }
            }

            return 'Upload complete';
        }

        /**
         * Add image to grid
         */
        function addImageToGrid(fileResult) {
            if (!$uploadedGrid || $uploadedGrid.length === 0) return;

            // Remove empty state if present
            var $emptyState = $uploadedGrid.find('.empty-state');
            if ($emptyState.length > 0) {
                $emptyState.remove();
            }

            // Insert server-rendered HTML
            if (fileResult.html) {
                $uploadedGrid.prepend(fileResult.html);
            }
        }

        /**
         * Update progress count
         */
        function updateProgressCount() {
            if (!$progressCount || $progressCount.length === 0) return;
            $progressCount.text(completedCount + ' of ' + uploadQueue.length + ' files');
        }

        /**
         * Update uploaded count
         */
        function updateUploadedCount() {
            if (!$uploadedCount || $uploadedCount.length === 0) return;

            var currentCount = parseInt($uploadedCount.text()) || 0;
            var successCount = uploadQueue.filter(function(item) {
                var $elem = $('#' + item.id);
                return $elem.length > 0 && $elem.hasClass('success');
            }).length;

            $uploadedCount.text(currentCount + successCount);
        }

        /**
         * Format file size
         */
        function formatFileSize(bytes) {
            if (bytes < 1024) return bytes + ' B';
            if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
            return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
        }

        /**
         * Escape HTML to prevent XSS
         */
        function escapeHtml(text) {
            var div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        // Initialize on creation
        init();

        // Return public API
        return {
            // No public methods needed currently, but we could add:
            // reset: function() { ... },
            // addFiles: function(files) { handleFiles(files); }
        };
    }

    // Export to Tt namespace
    window.Tt = window.Tt || {};
    window.Tt.createImageUpload = createImageUpload;

})();
