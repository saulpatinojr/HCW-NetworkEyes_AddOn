/* Network assessment pane. Vanilla, no storage, no analytics; every dynamic string goes through text nodes.
 * Posts {type:'hcw-addon', id:'network-assessment', state} to each site origin from /api/health.siteOrigins when framed.
 * States: loading (on load) -> ready (health ok) | unavailable (health failed); working during an upload, then ready. */
(function () {
  'use strict';
  var ADDON_ID = 'network-assessment';
  var UNAVAILABLE = "This tool isn't available right now.";
  var ACTION = 'network-assessment-upload';
  var VERIFICATION_SCRIPT = 'https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit';
  var SEVERITIES = ['critical', 'high', 'medium', 'low', 'informational'];

  var state = {
    siteOrigins: [],
    health: null,
    file: null,            // { name, text, format }
    verificationToken: null,
    verificationWidget: null,
    assessment: null,      // { id, ownerToken, expiresAt, summary, warnings }
    detail: null,          // full assessment document
    resources: {},         // resource id -> resource view
    reportMd: '',
    selected: null
  };

  var $ = function (id) { return document.getElementById(id); };
  var text = function (el, value) { el.textContent = value == null ? '' : String(value); return el; };
  var el = function (tag, cls, value) { var n = document.createElement(tag); if (cls) n.className = cls; if (value != null) n.textContent = String(value); return n; };
  var clear = function (node) { while (node.firstChild) node.removeChild(node.firstChild); };

  // ----- theme: ?theme=dark|light on the frame URL wins; otherwise prefers-color-scheme through theme.css -----
  (function theme() {
    var params = new URLSearchParams(window.location.search);
    var t = params.get('theme');
    if (t === 'dark') document.documentElement.classList.add('dark');
    if (t === 'light') document.documentElement.classList.add('light');
  })();

  // ----- pane protocol -----
  var framed = window.parent && window.parent !== window;
  function post(paneState) {
    if (!framed) return;
    state.siteOrigins.forEach(function (origin) {
      try { window.parent.postMessage({ type: 'hcw-addon', id: ADDON_ID, state: paneState }, origin); } catch (e) { /* ignore */ }
    });
  }

  function setStatus(words) { text($('status'), words); }
  function unavailable() {
    setStatus('Unavailable');
    $('unavailable').hidden = false;
    $('step-upload').hidden = true;
    post('unavailable');
  }

  // ----- API -----
  function api(path, options) {
    options = options || {};
    var headers = options.headers || {};
    if (state.assessment && state.assessment.ownerToken && !headers['x-owner-token']) headers['x-owner-token'] = state.assessment.ownerToken;
    return fetch(path, { method: options.method || 'GET', headers: headers, body: options.body, credentials: 'omit' });
  }
  function errorMessage(body, status) {
    if (body && body.error && typeof body.error.message === 'string') return body.error.message;
    if (status === 413) return 'The upload is larger than the limit.';
    return 'The request could not be completed.';
  }

  // ----- human verification (widget renders only when the API publishes a site key) -----
  function setupVerification(health) {
    var container = $('verification');
    clear(container);
    if (!health.turnstile || !health.turnstile.required) { text($('run-note'), ''); return; }
    if (!health.turnstile.siteKey) { text($('run-note'), 'Uploads are not available until human verification is configured.'); return; }
    var script = document.createElement('script');
    script.src = VERIFICATION_SCRIPT;
    script.async = true;
    script.onload = function () {
      if (!window.turnstile) return;
      state.verificationWidget = window.turnstile.render(container, {
        sitekey: health.turnstile.siteKey,
        action: ACTION,
        callback: function (token) { state.verificationToken = token; updateRunButton(); },
        'expired-callback': function () { state.verificationToken = null; updateRunButton(); },
        'error-callback': function () { state.verificationToken = null; updateRunButton(); }
      });
    };
    script.onerror = function () { text($('run-note'), 'Human verification could not load; reload to try again.'); };
    document.head.appendChild(script);
  }
  function verificationNeeded() {
    return !!(state.health && state.health.turnstile && state.health.turnstile.required);
  }
  function resetVerification() {
    state.verificationToken = null;
    if (state.verificationWidget != null && window.turnstile) { try { window.turnstile.reset(state.verificationWidget); } catch (e) { /* ignore */ } }
  }
  function updateRunButton() {
    var ready = !!state.file && (!verificationNeeded() || !!state.verificationToken);
    $('run').disabled = !ready;
    if (state.file && verificationNeeded() && !state.verificationToken) text($('run-note'), 'Complete the human verification to run the assessment.');
    else if (state.file) text($('run-note'), 'Ready: ' + state.file.name + ' (' + state.file.format + ').');
  }

  // ----- upload and preview -----
  function detectFormat(name, content) {
    var trimmed = content.replace(/^﻿/, '').trimStart();
    if (/\.json$/i.test(name) || trimmed[0] === '[' || trimmed[0] === '{') return 'arg-json';
    return 'arg-csv';
  }
  function previewRows(format, content) {
    var rows = [], columns = [];
    try {
      if (format === 'arg-json') {
        var doc = JSON.parse(content.replace(/^﻿/, ''));
        var data = Array.isArray(doc) ? doc : (doc && Array.isArray(doc.data) ? doc.data : []);
        rows = data.slice(0, 5).filter(function (r) { return r && typeof r === 'object'; });
        var seen = {};
        rows.forEach(function (r) { Object.keys(r).forEach(function (k) { if (!seen[k] && columns.length < 8) { seen[k] = 1; columns.push(k); } }); });
        return { total: data.length, columns: columns, rows: rows.map(function (r) { return columns.map(function (c) { var v = r[c]; return v == null ? '' : (typeof v === 'object' ? JSON.stringify(v) : String(v)); }); }) };
      }
      var lines = content.replace(/^﻿/, '').split(/\r?\n/).filter(function (l) { return l.trim() !== ''; });
      var delim = [',', ';', '\t'].sort(function (a, b) { return lines[0].split(b).length - lines[0].split(a).length; })[0];
      columns = lines[0].split(delim).slice(0, 8).map(function (c) { return c.replace(/^"|"$/g, ''); });
      rows = lines.slice(1, 6).map(function (l) { return l.split(delim).slice(0, 8).map(function (c) { return c.replace(/^"|"$/g, '').slice(0, 60); }); });
      return { total: Math.max(0, lines.length - 1), columns: columns, rows: rows };
    } catch (e) {
      return { total: 0, columns: [], rows: [], error: 'The file could not be previewed; the server will report what is wrong.' };
    }
  }
  function acceptFile(name, content) {
    var format = detectFormat(name, content);
    state.file = { name: name, text: content, format: format };
    var p = previewRows(format, content);
    var wrap = $('preview-wrap');
    wrap.hidden = false;
    text($('preview-summary'), p.error ? p.error : (p.total + ' rows detected; first ' + p.rows.length + ' shown (' + format + ').'));
    var thead = $('preview').querySelector('thead'), tbody = $('preview').querySelector('tbody');
    clear(thead); clear(tbody);
    var tr = el('tr'); p.columns.forEach(function (c) { tr.appendChild(el('th', null, c)); }); thead.appendChild(tr);
    p.rows.forEach(function (r) { var row = el('tr'); r.forEach(function (c) { row.appendChild(el('td', null, c.length > 80 ? c.slice(0, 80) + '…' : c)); }); tbody.appendChild(row); });
    var warnings = $('preview-warnings'); clear(warnings);
    if (format === 'arg-csv' && !/properties/i.test(p.columns.join(','))) warnings.appendChild(el('li', null, 'No properties column: the rules that read properties will be reported as unknown from this file.'));
    if (content.length > 5 * 1024 * 1024) warnings.appendChild(el('li', null, 'This file is larger than 5 MB and will be refused.'));
    updateRunButton();
  }
  function readFile(file) {
    if (!file) return;
    var reader = new FileReader();
    reader.onload = function () { acceptFile(file.name, String(reader.result || '')); };
    reader.readAsText(file);
  }

  // ----- run -----
  function run() {
    if (!state.file) return;
    $('run').disabled = true;
    setStatus('Assessing…');
    post('working');
    var headers = { 'content-type': 'application/json' };
    if (state.verificationToken) headers['x-turnstile-token'] = state.verificationToken;
    var body = JSON.stringify({ format: state.file.format, content: state.file.text, fileName: /^[\w .()-]{1,120}\.(json|csv)$/.test(state.file.name) ? state.file.name : undefined });
    var status = 0;
    api('/api/assessments', { method: 'POST', headers: headers, body: body })
      .then(function (r) { status = r.status; return r.json().catch(function () { return null; }); })
      .then(function (json) {
        if (status !== 201) throw new Error(errorMessage(json, status));
        state.assessment = { id: json.assessmentId, ownerToken: json.ownerToken, expiresAt: json.expiresAt, summary: json.summary, warnings: json.ingestionWarnings || [] };
        return api('/api/assessments/' + encodeURIComponent(json.assessmentId)).then(function (r) { return r.json(); });
      })
      .then(function (full) {
        state.detail = full.assessment;
        state.resources = {};
        (full.assessment.resources || []).forEach(function (r) { state.resources[r.id.toLowerCase()] = r; });
        return api('/api/assessments/' + encodeURIComponent(state.assessment.id) + '/report.md').then(function (r) { return r.text(); });
      })
      .then(function (md) {
        state.reportMd = md;
        render();
        setStatus('Ready');
        post('ready');
      })
      .catch(function (err) {
        text($('run-note'), err && err.message ? err.message : 'The request could not be completed.');
        setStatus('Ready');
        post('ready');
      })
      .finally(function () { resetVerification(); updateRunButton(); });
  }

  // ----- render results -----
  function render() {
    var a = state.assessment, d = state.detail, s = a.summary;
    ['step-summary', 'step-findings', 'step-unknown', 'step-cannot', 'step-actions'].forEach(function (id) { $(id).hidden = false; });
    text($('summary-line'), s.resourceCount + ' network resources in ' + s.rowCount + ' rows across ' + s.subscriptions.length + ' subscription(s); ' + s.rulesEvaluated + ' rules evaluated, ' + s.unknownRules + ' could not be answered from this export.');
    var tiles = $('tiles'); clear(tiles);
    var tile = function (label, value) { var t = el('div', 'tile'); t.appendChild(el('div', 'value', value)); t.appendChild(el('div', 'label', label)); tiles.appendChild(t); };
    tile('Findings', s.findingsCount);
    SEVERITIES.forEach(function (sev) { tile(sev, (s.findingsBySeverity && s.findingsBySeverity[sev]) || 0); });
    tile('Unknown rules', s.unknownRules);
    var topo = $('topology'); clear(topo);
    topo.appendChild(el('strong', null, 'Topology: ' + s.topology.pattern.replace('_', '-')));
    topo.appendChild(document.createTextNode(' — ' + s.topology.rationale));
    (s.topology.hubVnetIds || []).forEach(function (id) { var p = el('div', 'small'); p.appendChild(el('span', null, 'hub ')); p.appendChild(el('code', null, id)); topo.appendChild(p); });
    (s.topology.spokeVnetIds || []).forEach(function (id) { var p = el('div', 'small'); p.appendChild(el('span', null, 'spoke ')); p.appendChild(el('code', null, id)); topo.appendChild(p); });
    var warn = $('ingestion-warnings'); clear(warn);
    (a.warnings || []).forEach(function (w) { warn.appendChild(el('li', null, w)); });
    var cat = $('f-category'); clear(cat); cat.appendChild(el('option', null, 'All')).value = '';
    var cats = {};
    d.findings.forEach(function (f) { cats[f.category] = 1; });
    Object.keys(cats).sort().forEach(function (c) { var o = el('option', null, c); o.value = c; cat.appendChild(o); });
    renderFindings();
    var ul = $('unknown-list'); clear(ul);
    (d.unknowns || []).forEach(function (u) { var li = el('li'); li.appendChild(el('strong', 'mono', u.ruleId + ': ')); li.appendChild(document.createTextNode(u.reason)); ul.appendChild(li); });
    text($('expiry'), 'Expires ' + new Date(a.expiresAt).toLocaleString() + ' or when you delete it.');
    text($('report'), state.reportMd);
    text($('copy-note'), '');
    renderResources();
    showTab('report');
  }
  function renderFindings() {
    var d = state.detail; if (!d) return;
    var sev = $('f-severity').value, cat = $('f-category').value, q = $('f-search').value.trim().toLowerCase();
    var tbody = $('findings').querySelector('tbody'); clear(tbody);
    var shown = 0;
    d.findings.forEach(function (f, i) {
      if (sev && f.severity !== sev) return;
      if (cat && f.category !== cat) return;
      if (q && ((f.resourceId || '') + ' ' + f.ruleId + ' ' + (f.resourceType || '') + ' ' + f.title).toLowerCase().indexOf(q) < 0) return;
      shown++;
      var tr = el('tr', 'finding' + (state.selected === i ? ' selected' : ''));
      tr.setAttribute('tabindex', '0');
      tr.appendChild(el('td', 'mono', f.ruleId));
      tr.appendChild(el('td', 'sev-' + f.severity, f.severity));
      tr.appendChild(el('td', null, shortName(f.resourceId)));
      tr.appendChild(el('td', 'small', (f.resourceType || '').replace(/^Microsoft\.Network\//, '')));
      tr.appendChild(el('td', 'small', f.category || ''));
      tr.appendChild(el('td', 'small', f.observedState ? f.observedState.fact : ''));
      var open = function () { state.selected = i; renderDetail(f); renderFindings(); };
      tr.addEventListener('click', open);
      tr.addEventListener('keydown', function (e) { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); open(); } });
      tbody.appendChild(tr);
    });
    text($('findings-count'), shown + ' of ' + d.findings.length + ' findings');
  }
  function shortName(id) { return id ? String(id).split('/').pop() : '(estate)'; }
  function resourceFor(id) {
    var low = (id || '').toLowerCase();
    var best = null;
    Object.keys(state.resources).forEach(function (k) { if ((low === k || low.indexOf(k + '/') === 0) && (!best || k.length > best.length)) best = k; });
    return best ? state.resources[best] : null;
  }
  function renderDetail(f) {
    var dl = $('detail-list'); clear(dl);
    var add = function (k, v) { dl.appendChild(el('dt', null, k)); var dd = el('dd'); if (v && v.href) { var a = el('a', null, v.href); a.href = v.href; a.target = '_blank'; a.rel = 'noopener noreferrer'; dd.appendChild(a); } else text(dd, v); dl.appendChild(dd); };
    add('Rule', f.ruleId + ' v' + f.ruleVersion + ' (' + f.category + ', ' + f.severity + ')');
    add('Title', f.title);
    add('Resource', (f.resourceId || '(estate)'));
    add('Type', f.resourceType || '—');
    add('Subscription', f.subscriptionId || '—');
    add('Fact', f.observedState ? f.observedState.fact : '—');
    add('Evidence', f.observedState ? f.observedState.evidenceRef : '—');
    add('Description', f.description || '—');
    add('Remediation', f.remediation || '—');
    add('Traffic plane', f.trafficDirection || 'unclassified');
    add('Frameworks', (f.frameworkMappings || []).map(function (m) { return m.framework + (m.control ? ' ' + m.control : m.controlId ? ' ' + m.controlId : ''); }).join('; ') + ' (marked for verification)');
    if (/^https:\/\/learn\.microsoft\.com\//.test(f.learnUrl || '')) add('Learn more', { href: f.learnUrl });
    var r = resourceFor(f.resourceId);
    if (r) {
      add('Resource name', r.name + ' (' + r.type + ', ' + (r.location || '—') + ', ' + (r.resourceGroup || '—') + ')');
      add('Facts the rules read', JSON.stringify(r.facts || {}));
      add('Findings on this resource', (r.findingIds || []).map(function (id) { return id.split(':')[0]; }).join(', ') || '—');
    }
    $('detail').hidden = false;
  }
  function renderResources() {
    var tbody = $('resources').querySelector('tbody'); clear(tbody);
    (state.detail.resources || []).forEach(function (r) {
      var tr = el('tr');
      tr.appendChild(el('td', null, r.name));
      tr.appendChild(el('td', 'small', r.type.replace(/^microsoft\.network\//, '')));
      tr.appendChild(el('td', 'mono small', r.subscriptionId || ''));
      tr.appendChild(el('td', 'small', (r.findingIds || []).map(function (id) { return id.split(':')[0]; }).join(', ')));
      tbody.appendChild(tr);
    });
  }
  function showTab(which) {
    $('tab-report').setAttribute('aria-selected', which === 'report' ? 'true' : 'false');
    $('tab-resources').setAttribute('aria-selected', which === 'resources' ? 'true' : 'false');
    $('report').hidden = which !== 'report';
    $('resources-wrap').hidden = which !== 'resources';
  }

  // ----- actions -----
  function downloadBundle() {
    api('/api/assessments/' + encodeURIComponent(state.assessment.id) + '/bundle.zip')
      .then(function (r) { if (!r.ok) throw new Error('download'); return r.blob(); })
      .then(function (blob) {
        var url = URL.createObjectURL(blob);
        var a = document.createElement('a'); a.href = url; a.download = 'assessment-' + state.assessment.id.slice(0, 8) + '.zip';
        document.body.appendChild(a); a.click(); a.remove();
        setTimeout(function () { URL.revokeObjectURL(url); }, 2000);
        text($('copy-note'), 'If the download did not start, use Copy report: downloads can be blocked inside an embedded pane.');
      })
      .catch(function () { text($('copy-note'), 'The bundle could not be downloaded here; use Copy report instead.'); });
  }
  function copyReport() {
    var done = function () { text($('copy-note'), 'Report copied to the clipboard as Markdown.'); };
    var fallback = function () {
      try {
        var pre = $('report'); var range = document.createRange(); range.selectNodeContents(pre);
        var sel = window.getSelection(); sel.removeAllRanges(); sel.addRange(range);
        var ok = document.execCommand('copy'); sel.removeAllRanges();
        text($('copy-note'), ok ? 'Report copied to the clipboard as Markdown.' : 'Select the report text below and copy it.');
      } catch (e) { text($('copy-note'), 'Select the report text below and copy it.'); }
    };
    if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(state.reportMd).then(done, fallback); else fallback();
  }
  function openWorkspace() {
    if (!state.assessment) return;
    var status = 0;
    api('/api/assessments/' + encodeURIComponent(state.assessment.id) + '/workspace', { method: 'POST' })
      .then(function (r) { status = r.status; return r.json().catch(function () { return null; }); })
      .then(function (json) {
        if (status !== 202 || !json || !json.launchUrl) throw new Error(errorMessage(json, status));
        var note = $('copy-note'); clear(note);
        note.appendChild(document.createTextNode('Lab workspace ready (' + json.workspaceId + '): '));
        var a = el('a', null, 'Open lab workspace');
        a.href = json.launchUrl; a.target = '_blank'; a.rel = 'noopener noreferrer';
        note.appendChild(a);
      })
      .catch(function (err) {
        text($('copy-note'), err && err.message ? err.message : 'The guided workspace could not be started right now.');
      });
  }
  function deleteNow() {
    if (!state.assessment) return;
    if (!window.confirm('Delete this assessment and its files now?')) return;
    api('/api/assessments/' + encodeURIComponent(state.assessment.id), { method: 'DELETE' })
      .finally(function () {
        state.assessment = null; state.detail = null; state.reportMd = ''; state.selected = null; state.resources = {};
        ['step-summary', 'step-findings', 'step-unknown', 'step-cannot', 'step-actions'].forEach(function (id) { $(id).hidden = true; });
        $('detail').hidden = true;
        updateRunButton();
        text($('run-note'), 'Your data was deleted.');
      });
  }

  // ----- wiring -----
  function wire() {
    var dz = $('dropzone');
    ['dragenter', 'dragover'].forEach(function (ev) { dz.addEventListener(ev, function (e) { e.preventDefault(); dz.classList.add('active'); }); });
    ['dragleave', 'drop'].forEach(function (ev) { dz.addEventListener(ev, function (e) { e.preventDefault(); dz.classList.remove('active'); }); });
    dz.addEventListener('drop', function (e) { if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0]) readFile(e.dataTransfer.files[0]); });
    dz.addEventListener('keydown', function (e) { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); $('file').click(); } });
    $('file').addEventListener('change', function () { readFile($('file').files[0]); });
    $('use-sample').addEventListener('click', function () {
      fetch('/api/sample.json', { credentials: 'omit' }).then(function (r) { return r.text(); }).then(function (t) { acceptFile('sample-resource-graph.json', t); });
    });
    $('run').addEventListener('click', run);
    ['f-severity', 'f-category'].forEach(function (id) { $(id).addEventListener('change', renderFindings); });
    $('f-search').addEventListener('input', renderFindings);
    $('tab-report').addEventListener('click', function () { showTab('report'); });
    $('tab-resources').addEventListener('click', function () { showTab('resources'); });
    $('download-bundle').addEventListener('click', downloadBundle);
    $('copy-report').addEventListener('click', copyReport);
    $('open-workspace').addEventListener('click', openWorkspace);
    $('delete').addEventListener('click', deleteNow);
  }

  function boot() {
    wire();
    setStatus('Checking…');
    fetch('/api/health', { credentials: 'omit', headers: { accept: 'application/json' } })
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, body: j }; }); })
      .then(function (res) {
        var h = res.body || {};
        state.siteOrigins = Array.isArray(h.siteOrigins) ? h.siteOrigins.filter(function (o) { return typeof o === 'string' && /^https?:\/\/[^\s/]+$/.test(o); }) : [];
        post('loading');
        if (!res.ok || h.ok !== true || h.id !== ADDON_ID) { unavailable(); return; }
        state.health = h;
        setupVerification(h);
        setStatus('Ready');
        post('ready');
      })
      .catch(function () { unavailable(); });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();
})();
