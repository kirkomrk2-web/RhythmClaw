/**
 * Universal client-side form handler for Wallestars ecosystem.
 * Handles contact forms, newsletter forms, and page analytics.
 * Drop this into any site's script.js or include as separate <script>.
 */

(function() {
  'use strict';

  // ─── Analytics: track page view on load ───
  function trackPageView() {
    const payload = {
      page_path: window.location.pathname,
      referrer: document.referrer || '',
      session_id: getSessionId()
    };
    fetch('/api/analytics', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    }).catch(function() {}); // silent fail for analytics
  }

  // In-memory session ID (iframe-compatible, no browser storage APIs)
  var _memorySessionId = Math.random().toString(36).slice(2) + Date.now().toString(36);
  function getSessionId() {
    return _memorySessionId;
  }

  // ─── Form submission handler ───
  function handleFormSubmit(form, endpoint, successMsg) {
    if (!form) return;

    form.addEventListener('submit', function(e) {
      e.preventDefault();

      var btn = form.querySelector('button[type="submit"]');
      var originalText = btn ? btn.textContent : '';
      if (btn) {
        btn.disabled = true;
        btn.textContent = '⏳';
      }

      var formData = new FormData(form);
      var payload = {};
      formData.forEach(function(value, key) {
        payload[key] = value;
      });

      fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })
      .then(function(res) { return res.json(); })
      .then(function(data) {
        if (data.success) {
          showToast(successMsg || 'Success!', 'success');
          form.reset();
        } else {
          showToast(data.error || 'Something went wrong', 'error');
        }
      })
      .catch(function() {
        showToast('Network error. Please try again.', 'error');
      })
      .finally(function() {
        if (btn) {
          btn.disabled = false;
          btn.textContent = originalText;
        }
      });
    });
  }

  // ─── Toast notification ───
  function showToast(message, type) {
    var existing = document.querySelector('.wse-toast');
    if (existing) existing.remove();

    var toast = document.createElement('div');
    toast.className = 'wse-toast wse-toast--' + (type || 'info');
    toast.textContent = message;
    toast.setAttribute('role', 'alert');

    // Inline styles so it works without extra CSS
    Object.assign(toast.style, {
      position: 'fixed',
      bottom: '24px',
      right: '24px',
      padding: '14px 24px',
      borderRadius: '10px',
      fontSize: '14px',
      fontWeight: '500',
      color: '#fff',
      zIndex: '10000',
      opacity: '0',
      transform: 'translateY(12px)',
      transition: 'opacity 0.3s ease, transform 0.3s ease',
      maxWidth: '360px',
      boxShadow: '0 8px 32px rgba(0,0,0,0.2)',
      background: type === 'success' ? '#10b981' : type === 'error' ? '#ef4444' : '#3b82f6'
    });

    document.body.appendChild(toast);

    // Animate in
    requestAnimationFrame(function() {
      toast.style.opacity = '1';
      toast.style.transform = 'translateY(0)';
    });

    // Auto-remove after 4s
    setTimeout(function() {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(12px)';
      setTimeout(function() { toast.remove(); }, 300);
    }, 4000);
  }

  // ─── Initialize ───
  document.addEventListener('DOMContentLoaded', function() {
    // Track page view
    trackPageView();

    // Bind contact form
    var contactForm = document.querySelector('.contact-form');
    handleFormSubmit(contactForm, '/api/contact', '✓ Message sent successfully!');

    // Bind newsletter form
    var newsletterForm = document.querySelector('.newsletter-form');
    handleFormSubmit(newsletterForm, '/api/newsletter', '✓ Successfully subscribed!');
  });
})();
