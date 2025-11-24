/*
 * Trip Tools - Trip Images Upload
 * Handles drag-and-drop image uploads with progress tracking
 */

(function() {
    'use strict';

    // State management
    var uploadQueue = [];
    var completedCount = 0;

    // DOM element cache
    var $uploadZone;
    var $fileInput;
    var $progressSection;
    var $progressCount;
    var $fileProgressList;
    var $uploadedGrid;
    var $uploadedCount;

    // Module API
    var TripImagesUpload = {
        init: init
    };

    // Initialize the upload interface
    function init() {
        cacheDOMElements();
        initDragAndDrop();
        initFileInput();
    }

    // Cache DOM elements for performance
    function cacheDOMElements() {
        $uploadZone = $('#' + Tt.DIVID.IMAGES_UPLOAD_ZONE_ID);
        $fileInput = $('#' + Tt.DIVID.IMAGES_FILE_INPUT_ID);
        $progressSection = $('#' + Tt.DIVID.IMAGES_PROGRESS_SECTION_ID);
        $progressCount = $('#' + Tt.DIVID.IMAGES_PROGRESS_COUNT_ID);
        $fileProgressList = $('#' + Tt.DIVID.IMAGES_FILE_PROGRESS_LIST_ID);
        $uploadedGrid = $('#' + Tt.DIVID.IMAGES_UPLOADED_GRID_ID);
        $uploadedCount = $('#' + Tt.DIVID.IMAGES_UPLOADED_COUNT_ID);
    }

    // Initialize drag-and-drop handlers
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

    // Initialize file input handler
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

    // Handle drag over event
    function handleDragOver(e) {
        e.preventDefault();
        e.stopPropagation();
        $uploadZone.addClass('dragover');
    }

    // Handle drag leave event
    function handleDragLeave(e) {
        e.preventDefault();
        e.stopPropagation();
        $uploadZone.removeClass('dragover');
    }

    // Handle drop event
    function handleDrop(e) {
        e.preventDefault();
        e.stopPropagation();
        $uploadZone.removeClass('dragover');

        var files = e.originalEvent.dataTransfer.files;
        if (files.length > 0) {
            handleFiles(files);
        }
    }

    // Handle file selection
    function handleFiles(files) {
        var fileArray = Array.from(files);

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

        // Show progress section
        $progressSection.addClass('active');
        updateProgressCount();

        // Create progress items for each file
        $fileProgressList.empty();
        uploadQueue.forEach(function(fileItem) {
            createProgressItem(fileItem);
        });

        // Start uploads
        uploadFiles();
    }

    // Validate file
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

    // Create progress item HTML
    function createProgressItem(fileItem) {
        var $progressItem = $('<div></div>')
            .addClass('file-progress-item')
            .attr('id', fileItem.id);

        var fileSize = formatFileSize(fileItem.file.size);

        var html =
            '<div class="file-header">' +
                '<div class="file-icon"></div>' +
                '<div class="file-info">' +
                    '<div class="file-name">' + escapeHtml(fileItem.file.name) + '</div>' +
                    '<div class="file-size">' + fileSize + '</div>' +
                '</div>' +
                '<div class="file-status" data-status-target>' +
                    'Queued' +
                '</div>' +
            '</div>' +
            '<div class="progress-bar-container" style="display: none;">' +
                '<div class="progress-bar-fill" data-progress-bar></div>' +
            '</div>' +
            '<div class="progress-details" data-details-target></div>';

        $progressItem.html(html);
        $fileProgressList.append($progressItem);
    }

    // Upload files
    function uploadFiles() {
        var formData = new FormData();

        uploadQueue.forEach(function(fileItem) {
            formData.append('files', fileItem.file);
        });

        // Mark all as uploading
        uploadQueue.forEach(function(fileItem) {
            updateFileStatus(fileItem.id, 'uploading', 'Uploading...', 0);
        });

        // Use jQuery AJAX directly for file upload
        $.ajax({
            url: window.location.pathname,
            type: 'POST',
            data: formData,
            processData: false,
            contentType: false,
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            },
            success: function(data) {
                handleUploadResponse(data);
            },
            error: function(xhr) {
                handleUploadError(xhr);
            }
        });
    }

    // Handle upload response
    function handleUploadResponse(data) {
        if (!data.files || !Array.isArray(data.files)) {
            console.error('Invalid response format', data);
            uploadQueue.forEach(function(fileItem) {
                updateFileStatus(fileItem.id, 'error', 'Upload failed', null, 'Server returned invalid response');
            });
            return;
        }

        // Match response files to queue items by index
        data.files.forEach(function(fileResult, index) {
            var queueItem = uploadQueue[index];
            if (!queueItem) return;

            if (fileResult.status === 'success') {
                completedCount++;
                var details = buildSuccessDetails(fileResult);
                updateFileStatus(queueItem.id, 'success', 'Complete', 100, details);

                // Add to grid
                addImageToGrid(fileResult);
            } else {
                completedCount++;
                var errorMsg = fileResult.error_message || 'Upload failed';
                updateFileStatus(queueItem.id, 'error', 'Failed', null, errorMsg);
            }
        });

        updateProgressCount();
        updateUploadedCount();
    }

    // Handle upload error
    function handleUploadError(xhr) {
        console.error('Upload error', xhr);
        uploadQueue.forEach(function(fileItem) {
            updateFileStatus(fileItem.id, 'error', 'Failed', null, 'Network error or server unavailable');
        });
        completedCount = uploadQueue.length;
        updateProgressCount();
    }

    // Update file status
    function updateFileStatus(fileId, status, statusText, progress, details) {
        var $progressItem = $('#' + fileId);
        if ($progressItem.length === 0) return;

        // Update item class
        $progressItem.attr('class', 'file-progress-item ' + status);

        // Update status badge
        var $statusTarget = $progressItem.find('[data-status-target]');
        if ($statusTarget.length > 0) {
            $statusTarget.attr('class', 'file-status ' + status);

            var iconHtml = '';
            if (status === 'uploading' || status === 'processing') {
                iconHtml = '<span class="spinner"></span>';
            } else if (status === 'success') {
                iconHtml = '<span style="color: var(--success-color);">&#10003;</span>';
            } else if (status === 'error') {
                iconHtml = '<span style="color: var(--error-color);">!</span>';
            }

            $statusTarget.html(iconHtml + ' ' + statusText);
        }

        // Update progress bar
        var $progressBarContainer = $progressItem.find('.progress-bar-container');
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
            $detailsTarget.attr('class', 'progress-details ' + status);
        }
    }

    // Build success details text
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

    // Add image to grid
    function addImageToGrid(fileResult) {
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

    // Update progress count
    function updateProgressCount() {
        $progressCount.text(completedCount + ' of ' + uploadQueue.length + ' files');
    }

    // Update uploaded count
    function updateUploadedCount() {
        var currentCount = parseInt($uploadedCount.text()) || 0;
        var successCount = uploadQueue.filter(function(item) {
            var $elem = $('#' + item.id);
            return $elem.length > 0 && $elem.hasClass('success');
        }).length;

        $uploadedCount.text(currentCount + successCount);
    }

    // Format file size
    function formatFileSize(bytes) {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
        return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    }

    // Escape HTML to prevent XSS
    function escapeHtml(text) {
        var div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Export to Tt namespace
    window.Tt = window.Tt || {};
    window.Tt.tripImagesUpload = TripImagesUpload;

    // Initialize on document ready
    $(document).ready(function() {
        TripImagesUpload.init();
    });

})();
