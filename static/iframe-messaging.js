/**
 * Iframe Messaging System
 * Handles communication between iframe content and parent window
 */

(function() {
  'use strict';

  // Check if we're in an iframe
  const isInIframe = window !== window.top;
  
  // Event listeners storage
  const eventListeners = new Map();
  
  // Initialize messaging system
  function initMessaging() {
    if (!isInIframe) {
      return;
    }
    
    try {
      // Set up message listener for incoming messages from parent
      window.addEventListener('message', function(event) {
        try {
          // Only handle messages from parent window
          if (event.source === window.parent) {
            handleMessage(event.data);
          }
        } catch (error) {
          console.error('IframeMessaging: Error in message listener', error);
        }
      });
      
      // Notify parent that iframe is ready
      notifyParent('iframeReady', {
        timestamp: Date.now(),
        url: window.location.href
      });
      

    } catch (error) {
      console.error('IframeMessaging: Failed to initialize', error);
    }
  }
  
  // Handle incoming messages
  function handleMessage(data) {
    try {
      if (!data || !data.type) {
        return;
      }
      
      const listeners = eventListeners.get(data.type) || [];
      listeners.forEach(callback => {
        try {
          callback(data.payload);
        } catch (error) {
          console.error('IframeMessaging: Error in message handler', error);
        }
      });
    } catch (error) {
      console.error('IframeMessaging: Error handling message', error);
    }
  }
  
  // Send message to parent
  function notifyParent(type, payload) {
    if (!isInIframe) {
      return;
    }
    
    try {
      const message = {
        type: type,
        payload: payload,
        timestamp: Date.now(),
        source: 'iframe'
      };
      
      // Use simple postMessage instead of MessageChannel to avoid channel closure issues
      window.parent.postMessage(message, '*');
    } catch (error) {
      console.error('IframeMessaging: Failed to send message', error);
    }
  }
  
  // Public API
  window.iframeMessaging = {
    // Initialize the messaging system
    init: function() {
      initMessaging();
    },
    
    // Add event listener
    on: function(type, callback) {
      if (!eventListeners.has(type)) {
        eventListeners.set(type, []);
      }
      eventListeners.get(type).push(callback);
    },
    
    // Remove event listener
    off: function(type, callback) {
      const listeners = eventListeners.get(type);
      if (listeners) {
        const index = listeners.indexOf(callback);
        if (index > -1) {
          listeners.splice(index, 1);
        }
      }
    },
    
    // Notify parent of filter changes
    notifyFilterChanged: function(filterState) {
      notifyParent('filterChanged', filterState);
    },
    
    // Notify parent of data updates
    notifyDataUpdated: function(dataInfo) {
      notifyParent('dataUpdated', dataInfo);
    },
    
    // Notify parent of state changes
    notifyStateChanged: function(stateInfo) {
      notifyParent('stateChanged', stateInfo);
    },
    
    // Send custom message
    send: function(type, payload) {
      notifyParent(type, payload);
    },
    
    // Check if messaging is available
    isAvailable: function() {
      return isInIframe;
    }
  };
  
  // Auto-initialize when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() {
      setTimeout(initMessaging, 100);
    });
  } else {
    setTimeout(initMessaging, 100);
  }
  
  // Handle page unload
  window.addEventListener('beforeunload', function() {
    try {
      notifyParent('iframeUnloading', {
        timestamp: Date.now()
      });
    } catch (error) {
      // Ignore errors during unload
    }
  });
  
})();
