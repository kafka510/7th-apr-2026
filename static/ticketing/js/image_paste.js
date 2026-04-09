/**
 * Image Paste Handler for Ticket Attachments
 * Allows users to paste images directly into the upload area
 */
(function() {
    'use strict';
    
    function initImagePaste() {
        const pasteAreas = document.querySelectorAll('.paste-image-area');
        
        pasteAreas.forEach(pasteArea => {
            const fileInput = pasteArea.closest('form')?.querySelector('input[type="file"]');
            const pastedImageInput = pasteArea.closest('form')?.querySelector('#pasted-image-input');
            const preview = pasteArea.querySelector('.paste-preview');
            
            if (!fileInput || !pastedImageInput) return;
            
            // Show paste area on focus
            fileInput.addEventListener('focus', () => {
                pasteArea.style.display = 'block';
            });
            
            // Handle paste event
            pasteArea.addEventListener('paste', (e) => {
                e.preventDefault();
                const items = e.clipboardData.items;
                
                for (let i = 0; i < items.length; i++) {
                    if (items[i].type.indexOf('image') !== -1) {
                        const blob = items[i].getAsFile();
                        const reader = new FileReader();
                        
                        reader.onload = function(event) {
                            const base64 = event.target.result;
                            pastedImageInput.value = base64;
                            
                            // Show preview
                            if (preview) {
                                preview.innerHTML = `<img src="${base64}" style="max-width: 100%; max-height: 200px; border-radius: 4px;" alt="Pasted image preview">`;
                            }
                            
                            // Create a file object for the file input
                            const dataTransfer = new DataTransfer();
                            dataTransfer.items.add(blob);
                            fileInput.files = dataTransfer.files;
                            
                            // Trigger change event
                            fileInput.dispatchEvent(new Event('change', { bubbles: true }));
                        };
                        
                        reader.readAsDataURL(blob);
                        break;
                    }
                }
            });
            
            // Handle drag and drop
            pasteArea.addEventListener('dragover', (e) => {
                e.preventDefault();
                pasteArea.classList.add('drag-over');
            });
            
            pasteArea.addEventListener('dragleave', () => {
                pasteArea.classList.remove('drag-over');
            });
            
            pasteArea.addEventListener('drop', (e) => {
                e.preventDefault();
                pasteArea.classList.remove('drag-over');
                
                const files = e.dataTransfer.files;
                if (files.length > 0 && files[0].type.startsWith('image/')) {
                    const file = files[0];
                    const reader = new FileReader();
                    
                    reader.onload = function(event) {
                        const base64 = event.target.result;
                        pastedImageInput.value = base64;
                        
                        // Show preview
                        if (preview) {
                            preview.innerHTML = `<img src="${base64}" style="max-width: 100%; max-height: 200px; border-radius: 4px;" alt="Dropped image preview">`;
                        }
                        
                        // Set file input
                        const dataTransfer = new DataTransfer();
                        dataTransfer.items.add(file);
                        fileInput.files = dataTransfer.files;
                    };
                    
                    reader.readAsDataURL(file);
                }
            });
            
            // Clear preview when file input changes
            fileInput.addEventListener('change', () => {
                if (fileInput.files.length === 0) {
                    pastedImageInput.value = '';
                    if (preview) {
                        preview.innerHTML = '';
                    }
                }
            });
        });
        
        // Global paste handler for when form is focused
        document.addEventListener('paste', (e) => {
            const activeElement = document.activeElement;
            const forms = document.querySelectorAll('#attachment-upload-form');
            
            forms.forEach(form => {
                if (form.contains(activeElement) || form === activeElement) {
                    const pasteArea = form.querySelector('.paste-image-area');
                    const pastedImageInput = form.querySelector('#pasted-image-input');
                    const fileInput = form.querySelector('input[type="file"]');
                    
                    if (pasteArea && pastedImageInput && fileInput) {
                        const items = e.clipboardData.items;
                        
                        for (let i = 0; i < items.length; i++) {
                            if (items[i].type.indexOf('image') !== -1) {
                                e.preventDefault();
                                const blob = items[i].getAsFile();
                                const reader = new FileReader();
                                
                                reader.onload = function(event) {
                                    const base64 = event.target.result;
                                    pastedImageInput.value = base64;
                                    
                                    const preview = pasteArea.querySelector('.paste-preview');
                                    if (preview) {
                                        preview.innerHTML = `<img src="${base64}" style="max-width: 100%; max-height: 200px; border-radius: 4px;" alt="Pasted image preview">`;
                                    }
                                    
                                    const dataTransfer = new DataTransfer();
                                    dataTransfer.items.add(blob);
                                    fileInput.files = dataTransfer.files;
                                };
                                
                                reader.readAsDataURL(blob);
                                break;
                            }
                        }
                    }
                }
            });
        });
    }
    
    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initImagePaste);
    } else {
        initImagePaste();
    }
})();

