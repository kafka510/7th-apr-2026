/**
 * Light Encryption Utilities for localStorage
 * Provides simple Base64 encoding/decoding for localStorage data
 * 
 * This utility encrypts sensitive localStorage data to prevent
 * easy access to user preferences and filter selections.
 */

class LocalStorageEncryption {
    constructor() {
        // Simple key for encoding (you can make this more complex)
        this.encodingKey = 'peak_energy_2024_secure';
    }

    /**
     * Encrypt data before storing in localStorage
     * @param {string} key - localStorage key
     * @param {any} value - data to encrypt
     */
    encrypt(key, value) {
        try {
            const dataString = JSON.stringify(value);
            // Simple XOR encryption with the key
            const encrypted = this.xorEncrypt(dataString, this.encodingKey);
            // Base64 encode for safe storage
            const encoded = btoa(encrypted);
            localStorage.setItem(key, encoded);
        } catch (error) {
            console.warn('Failed to encrypt localStorage data:', error);
            // Fallback to unencrypted storage
            localStorage.setItem(key, JSON.stringify(value));
        }
    }

    /**
     * Decrypt data from localStorage
     * @param {string} key - localStorage key
     * @returns {any} - decrypted data or null if not found
     */
    decrypt(key) {
        try {
            const encoded = localStorage.getItem(key);
            if (!encoded) return null;
            
            // Base64 decode
            const encrypted = atob(encoded);
            // XOR decrypt
            const decrypted = this.xorDecrypt(encrypted, this.encodingKey);
            return JSON.parse(decrypted);
        } catch (error) {
            console.warn('Failed to decrypt localStorage data:', error);
            // Try to get unencrypted data as fallback
            try {
                return JSON.parse(localStorage.getItem(key));
            } catch (e) {
                return null;
            }
        }
    }

    /**
     * Simple XOR encryption
     * @param {string} text - text to encrypt
     * @param {string} key - encryption key
     * @returns {string} - encrypted text
     */
    xorEncrypt(text, key) {
        let result = '';
        for (let i = 0; i < text.length; i++) {
            result += String.fromCharCode(
                text.charCodeAt(i) ^ key.charCodeAt(i % key.length)
            );
        }
        return result;
    }

    /**
     * Simple XOR decryption
     * @param {string} encryptedText - encrypted text
     * @param {string} key - decryption key
     * @returns {string} - decrypted text
     */
    xorDecrypt(encryptedText, key) {
        return this.xorEncrypt(encryptedText, key); // XOR is symmetric
    }

    /**
     * Remove encrypted data from localStorage
     * @param {string} key - localStorage key
     */
    remove(key) {
        localStorage.removeItem(key);
    }

    /**
     * Check if data exists in localStorage (encrypted or unencrypted)
     * @param {string} key - localStorage key
     * @returns {boolean} - true if data exists
     */
    exists(key) {
        return localStorage.getItem(key) !== null;
    }

    /**
     * Clear all encrypted data (useful for logout)
     * @param {Array} keys - array of keys to clear
     */
    clearEncryptedData(keys = []) {
        keys.forEach(key => {
            this.remove(key);
        });
    }
}

// Create global instance
window.localStorageEncryption = new LocalStorageEncryption();

// Export for module systems if needed
if (typeof module !== 'undefined' && module.exports) {
    module.exports = LocalStorageEncryption;
}
