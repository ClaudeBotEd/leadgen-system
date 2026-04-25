/**
 * Lead form handler — installatiebedrijven landing page.
 *
 * Posts JSON to WEBHOOK_URL (configure below).
 * Default target: n8n webhook from /n8n/workflow-lead-intake.json.
 *
 * Replace WEBHOOK_URL with your live endpoint before deploy.
 */

(function () {
  'use strict';

  // ===== CONFIGURATION =====
  // Set this to your n8n webhook URL or any endpoint accepting JSON POST.
  // Examples:
  //   https://n8n.yourdomain.com/webhook/lead-intake
  //   https://hook.eu1.make.com/xxxxxxxxxxxx
  //   https://hooks.zapier.com/hooks/catch/xxxxxx/yyyyyy/
  var WEBHOOK_URL = 'https://CHANGE_ME.example.com/webhook/lead-intake';

  // Set true to log payloads to console for debugging.
  var DEBUG = false;

  // Set the year in footer
  var yearEl = document.getElementById('year');
  if (yearEl) yearEl.textContent = String(new Date().getFullYear());

  var form = document.getElementById('lead-form');
  var status = document.getElementById('form-status');
  if (!form || !status) return;

  form.addEventListener('submit', function (event) {
    event.preventDefault();
    setStatus('', '');

    if (!form.reportValidity()) return;

    // Honeypot check — if filled, silently "succeed" without sending
    var hp = form.elements['hp_field'];
    if (hp && hp.value.trim() !== '') {
      setStatus('Bedankt, wij nemen binnen 1 werkdag contact op.', 'success');
      form.reset();
      return;
    }

    var consent = form.elements['consent_processing'];
    if (consent && !consent.checked) {
      setStatus('U dient akkoord te gaan met de verwerking van uw gegevens.', 'error');
      return;
    }

    var payload = collectPayload(form);

    if (DEBUG) console.log('[lead-form] payload', payload);

    var submitBtn = form.querySelector('button[type="submit"]');
    var originalText = submitBtn ? submitBtn.textContent : '';
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.textContent = 'Versturen...';
    }

    fetch(WEBHOOK_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      mode: 'cors',
      credentials: 'omit'
    })
      .then(function (response) {
        if (!response.ok) throw new Error('HTTP ' + response.status);
        return response.text().catch(function () { return ''; });
      })
      .then(function () {
        setStatus(
          'Bedankt! Wij nemen binnen 1 werkdag contact op om uw 3 gratis leads te bespreken.',
          'success'
        );
        form.reset();
      })
      .catch(function (err) {
        if (DEBUG) console.error('[lead-form] submit error', err);
        setStatus(
          'Er ging iets mis bij verzenden. Mail gerust direct naar het adres in de voettekst.',
          'error'
        );
      })
      .finally(function () {
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.textContent = originalText;
        }
      });
  });

  function collectPayload(formEl) {
    var data = new FormData(formEl);
    var obj = {};
    data.forEach(function (value, key) {
      if (key === 'hp_field') return; // never include honeypot
      obj[key] = typeof value === 'string' ? value.trim() : value;
    });

    obj.consent_processing = !!formEl.elements['consent_processing'].checked;
    obj.submitted_at = new Date().toISOString();
    obj.page_url = window.location.href;
    obj.referrer = document.referrer || null;
    obj.user_agent = navigator.userAgent;
    obj.utm = readUtm();

    return obj;
  }

  function readUtm() {
    var params = new URLSearchParams(window.location.search);
    var utm = {};
    ['utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content'].forEach(function (k) {
      var v = params.get(k);
      if (v) utm[k] = v;
    });
    return Object.keys(utm).length ? utm : null;
  }

  function setStatus(text, type) {
    status.textContent = text;
    status.className = 'form-status' + (type ? ' ' + type : '');
  }
})();
