/* Controls: top bar (mode, warp, wind chip + environment popover) and the control dock
 * (manual sliders, autopilot course editor). The server owns the state; sliders are NOT overwritten by polls
 * while the human is using them. */
(function (C) {
    'use strict';

    const $ = id => document.getElementById(id);
    const ENV_DEBOUNCE_MS = 150;
    const SEND_EVERY_MS = 70;

    let api, state = null;
    let uiMode = 'manual';
    let modePendingUntil = 0, autoTrimPendingUntil = 0, lastEnvInput = 0, lastLoopClick = 0;
    let chipSig = '';
    let envTimer = null;
    const el = {};

    function throttled(fn, ms) {
        let lastAt = 0, timer = null, pending;
        return function (v) {
            pending = v;
            const wait = ms - (Date.now() - lastAt);
            if (wait <= 0) { lastAt = Date.now(); fn(pending); }
            else if (!timer) {
                timer = setTimeout(function () { timer = null; lastAt = Date.now(); fn(pending); }, wait);
            }
        };
    }

    const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
    const rudderText = v => v === 0 ? '0°' : Math.round(Math.abs(v) * 0.45) + '° ' + (v < 0 ? 'P' : 'S');

    // --- manual controls --------------------------------------------------------------------------------

    const sendRudder = throttled(v => api.control({ command: 'rudder', value: v }), SEND_EVERY_MS);
    const sendSheet = throttled(v => api.control({ command: 'sails', value: v }), SEND_EVERY_MS);
    const sendMotor = throttled(v => api.control({ command: 'throttle', value: v }), SEND_EVERY_MS);

    function showRudder(v) {
        el.rudderOut.textContent = rudderText(v);
        el.rudderOut.className = v === 0 ? '' : v < 0 ? 'port' : 'stbd';
        el.rudderOut.style.color = v === 0 ? '' : v < 0 ? '#ff8585' : '#5fe08a';
    }
    function showSheet(v) { el.sheetOut.textContent = Math.round(v) + '%'; }
    function showMotor(v) { el.motorOut.textContent = Math.round(v) + '%'; }

    function setRudder(v, send) {
        v = clamp(Math.round(v), -100, 100);
        el.rudder.value = v; showRudder(v);
        if (send) sendRudder(v);
    }
    function setSheet(v, send) {
        v = clamp(Math.round(v), 0, 100);
        el.sheet.value = v; showSheet(v);
        if (send) sendSheet(v);
    }

    /** Copy the server's rudder / sheet / motor into the sliders (used when entering manual, after Stop / Reset). */
    function syncManualSliders() {
        if (!state) return;
        el.rudder.value = Math.round(state.rudder); showRudder(Math.round(state.rudder));
        el.sheet.value = Math.round(state.trim); showSheet(state.trim);
        el.motor.value = Math.round(state.throttle); showMotor(state.throttle);
    }

    function bindManual() {
        el.rudder.addEventListener('input', () => setRudder(parseFloat(el.rudder.value), true));
        el.rudder.addEventListener('dblclick', () => setRudder(0, true));
        el.sheet.addEventListener('input', () => setSheet(parseFloat(el.sheet.value), true));
        el.motor.addEventListener('input', () => { const v = parseFloat(el.motor.value); showMotor(v); sendMotor(v); });
        el.autoTrim.addEventListener('change', () => {
            autoTrimPendingUntil = Date.now() + 700;
            api.control({ auto_trim: el.autoTrim.checked }).then(syncManualSliders);
            updateEnabled();
        });
    }

    function updateEnabled() {
        const auto = uiMode === 'auto';
        const trim = el.autoTrim.checked;
        el.sheet.disabled = auto || trim;
        el.rudder.disabled = auto;
    }

    // --- top bar ----------------------------------------------------------------------------------------

    function setMode(mode, fromUser) {
        uiMode = mode;
        if (fromUser) modePendingUntil = Date.now() + 800;
        document.querySelectorAll('#mode-switch button').forEach(b => b.setAttribute('aria-selected', String(b.dataset.mode === mode)));
        $('panel-manual').hidden = mode !== 'manual';
        $('panel-auto').hidden = mode !== 'auto';
        C.Map.setEditing(mode === 'auto');
        updateEnabled();
    }

    function bindTopBar() {
        document.querySelectorAll('#mode-switch button').forEach(b => b.addEventListener('click', () => {
            const mode = b.dataset.mode;
            if (mode === uiMode) return;
            setMode(mode, true);
            api.control({ mode: mode }).then(() => { if (mode === 'manual') syncManualSliders(); });
        }));
        document.querySelectorAll('#warp button').forEach(b => b.addEventListener('click', () => {
            api.control({ time_scale: parseFloat(b.dataset.warp) });
            document.querySelectorAll('#warp button').forEach(x => x.setAttribute('aria-pressed', String(x === b)));
        }));

        // Environment popover
        const chip = $('wind-chip'), pop = $('env-popover');
        const toggle = open => { pop.hidden = !open; chip.setAttribute('aria-expanded', String(open)); };
        chip.addEventListener('click', e => { e.stopPropagation(); toggle(pop.hidden); });
        document.addEventListener('click', e => { if (!pop.hidden && !pop.contains(e.target)) toggle(false); });
        document.addEventListener('keydown', e => { if (e.key === 'Escape') toggle(false); });

        const fields = [
            ['env-wind-speed', v => v.toFixed(1) + ' kn'],
            ['env-wind-dir', v => Math.round(v) + '°'],
            ['env-cur-speed', v => v.toFixed(1) + ' kn'],
            ['env-cur-dir', v => Math.round(v) + '°']
        ];
        fields.forEach(([id, fmt]) => {
            const input = $(id), out = $(id + '-out');
            input.addEventListener('input', () => {
                out.textContent = fmt(parseFloat(input.value));
                lastEnvInput = Date.now();
                clearTimeout(envTimer);
                envTimer = setTimeout(sendEnvironment, ENV_DEBOUNCE_MS);
            });
        });
    }

    function sendEnvironment() {
        api.control({
            command: 'set_environment',
            value: {
                wind_speed: parseFloat($('env-wind-speed').value),
                wind_direction: parseFloat($('env-wind-dir').value),
                current_speed: parseFloat($('env-cur-speed').value),
                current_direction: parseFloat($('env-cur-dir').value)
            }
        });
    }

    function syncEnvironment(s) {
        if (Date.now() - lastEnvInput < 1200) return;  // the human is dragging: leave the sliders alone
        const set = (id, v, text) => { const i = $(id); i.value = v; $(id + '-out').textContent = text; };
        set('env-wind-speed', s.tws, s.tws.toFixed(1) + ' kn');
        set('env-wind-dir', s.twd, Math.round(s.twd) + '°');
        set('env-cur-speed', s.current_speed, s.current_speed.toFixed(1) + ' kn');
        set('env-cur-dir', s.current_direction, Math.round(s.current_direction) + '°');
    }

    // --- autopilot --------------------------------------------------------------------------------------

    function courseBody(marks, extra) {
        const course = state.course;
        return Object.assign({ marks: marks, loop: course.loop, active: course.active }, extra || {});
    }
    const plain = marks => marks.map(m => ({ lat: m.lat, lng: m.lng }));

    function addMark(latlng) {
        if (!state) return;
        const marks = plain(state.course.marks);
        marks.push({ lat: latlng.lat, lng: latlng.lng });
        api.course(courseBody(marks));
    }
    function moveMark(i, latlng) {
        const marks = plain(state.course.marks);
        marks[i] = { lat: latlng.lat, lng: latlng.lng };
        api.course(courseBody(marks));
    }
    function removeMark(i) {
        const marks = plain(state.course.marks);
        marks.splice(i, 1);
        let active = state.course.active;
        if (i < active) active -= 1;
        api.course(courseBody(marks, { active: Math.max(0, Math.min(active, marks.length - 1)) }));
    }

    function bindAuto() {
        $('btn-demo').addEventListener('click', () => {
            api.demo({}).then(s => { if (s && !C.Map.isFollowing()) C.Map.fitCourse(s); });
        });
        $('btn-start').addEventListener('click', () => {
            if (!state) return;
            api.control({ mode: 'auto', running: !(state.mode === 'auto' && state.running) });
        });
        $('btn-clear').addEventListener('click', () => api.clearCourse());
        $('loop-toggle').addEventListener('change', () => {
            lastLoopClick = Date.now();
            if (!state) return;
            api.course(courseBody(plain(state.course.marks), { loop: $('loop-toggle').checked }));
        });
        $('mark-chips').addEventListener('click', e => {
            const btn = e.target.closest('button[data-remove]');
            if (btn) removeMark(parseInt(btn.dataset.remove, 10));
        });
    }

    function renderChips(s) {
        const course = s.course;
        const upwindTo = new Set((course.legs || []).filter(l => l.upwind).map(l => l.to));
        const sig = JSON.stringify([course.marks.length, course.active, course.finished, [...upwindTo]]);
        if (sig === chipSig) return;
        chipSig = sig;
        $('mark-chips').innerHTML = course.marks.map((m, i) =>
            '<span class="mark-chip' + (i === course.active && !course.finished ? ' active' : '') + (upwindTo.has(i) ? ' up' : '') + '">' +
            '<span class="n">' + (i + 1) + '</span>' +
            '<button type="button" data-remove="' + i + '" aria-label="Remove mark ' + (i + 1) + '">×</button></span>'
        ).join('');
    }

    function renderAutoStatus(s) {
        const course = s.course, n = course.marks.length;
        const running = s.mode === 'auto' && s.running;
        let html;
        if (!n) html = 'No marks yet.';
        else if (course.finished) html = 'Course finished.';
        else if (s.to_mark) {
            const head = running ? 'Heading to ' : 'Next: ';
            html = head + '<b>mark ' + (s.to_mark.index + 1) + '</b> · ' + C.Instruments.fmtDist(s.to_mark.distance_m) + ' · ' + C.Instruments.pad3(s.to_mark.bearing);
            if (course.laps) html += ' · lap ' + (course.laps + 1);
        } else html = '';
        if (s.to_mark && s.to_mark.upwind && n) html += ' <span class="warn">· upwind</span>';
        $('auto-status').innerHTML = html;

        const start = $('btn-start');
        start.textContent = running ? 'Pause' : (course.finished ? 'Restart' : 'Start');
        start.classList.toggle('running', running);
        start.disabled = !n;
        $('btn-clear').disabled = !n;
    }

    function renderToast(s) {
        const toast = $('toast');
        const warn = s.mode === 'auto' && s.warnings && s.warnings.length;
        const text = 'Upwind leg — navigator can’t tack yet';
        if (warn && toast.hidden) { toast.textContent = text; toast.hidden = false; }
        if (!warn && !toast.hidden) toast.hidden = true;
    }

    // --- dock footer + keyboard -------------------------------------------------------------------------

    function setFollowUI(on) {
        C.Map.setFollow(on);
        $('btn-follow').setAttribute('aria-pressed', String(on));
    }

    function bindFooter() {
        $('btn-stop').addEventListener('click', () => {
            el.rudder.value = 0; showRudder(0);
            el.sheet.value = 0; showSheet(0);
            el.motor.value = 0; showMotor(0);
            el.autoTrim.checked = false;
            setMode('manual', true);
            api.control({ command: 'emergency_stop' });
        });
        $('btn-reset').addEventListener('click', () => {
            api.reset({}).then(() => { C.Map.clearWake(); syncManualSliders(); el.autoTrim.checked = false; setMode('manual', true); });
        });
        $('btn-follow').addEventListener('click', () => setFollowUI(!C.Map.isFollowing()));
        document.addEventListener('keydown', onKey);
    }

    function onKey(e) {
        if (e.ctrlKey || e.metaKey || e.altKey) return;
        const t = e.target;
        if (t && (t.tagName === 'SELECT' || (t.tagName === 'INPUT' && t.type !== 'range' && t.type !== 'checkbox'))) return;
        const manual = uiMode === 'manual';
        switch (e.key) {
            case 'ArrowLeft': if (manual) { setRudder(parseFloat(el.rudder.value) - 10, true); e.preventDefault(); } break;
            case 'ArrowRight': if (manual) { setRudder(parseFloat(el.rudder.value) + 10, true); e.preventDefault(); } break;
            case 'ArrowUp': if (manual && !el.sheet.disabled) { setSheet(parseFloat(el.sheet.value) + 5, true); e.preventDefault(); } break;
            case 'ArrowDown': if (manual && !el.sheet.disabled) { setSheet(parseFloat(el.sheet.value) - 5, true); e.preventDefault(); } break;
            case 'f': case 'F': setFollowUI(!C.Map.isFollowing()); break;
            default: break;
        }
    }

    // --- per-poll sync ----------------------------------------------------------------------------------

    function onState(s) {
        const first = state === null;
        state = s;
        if (first) syncManualSliders();

        if (Date.now() > modePendingUntil && s.mode !== uiMode) {
            setMode(s.mode, false);
            if (s.mode === 'manual') syncManualSliders();
        }
        if (Date.now() > autoTrimPendingUntil) el.autoTrim.checked = !!s.auto_trim;
        updateEnabled();

        document.querySelectorAll('#warp button').forEach(b =>
            b.setAttribute('aria-pressed', String(Math.abs(parseFloat(b.dataset.warp) - s.time_scale) < 0.01)));

        $('wind-chip-text').textContent = Math.round(s.twd) + '° · ' + s.tws.toFixed(0) + ' kn';
        $('wind-chip-arrow').style.transform = 'rotate(' + s.twd.toFixed(0) + 'deg)';
        syncEnvironment(s);

        // The sheet slider follows the server while the autopilot owns the sheet; the human owns it otherwise
        if (el.sheet.disabled) { el.sheet.value = Math.round(s.trim); showSheet(s.trim); }
        const optPct = clamp(s.opt_trim, 0, 100);
        $('slider-opt').style.left = 'calc(8px + (100% - 16px) * ' + (optPct / 100).toFixed(4) + ')';

        renderChips(s);
        renderAutoStatus(s);
        renderToast(s);
        if (Date.now() - lastLoopClick > 800) $('loop-toggle').checked = !!s.course.loop;
    }

    function setLive(ok, ageMs) {
        const live = $('live');
        live.classList.toggle('ok', ok);
        live.classList.toggle('lost', !ok);
        live.title = ok ? 'Connected to the simulator' : 'No response from the simulator';
        live.querySelector('.live-text').textContent = ok ? 'Live' : 'Offline';
    }

    function init(options) {
        api = options.api;
        el.rudder = $('rudder-slider'); el.rudderOut = $('rudder-out');
        el.sheet = $('sheet-slider'); el.sheetOut = $('sheet-out');
        el.motor = $('motor-slider'); el.motorOut = $('motor-out');
        el.autoTrim = $('auto-trim');
        bindManual(); bindTopBar(); bindAuto(); bindFooter();
        setMode('manual', false);
        setRudder(0, false); setSheet(0, false); showMotor(0);
    }

    C.Controls = {
        init: init,
        get mode() { return uiMode; },
        onState: onState,
        setLive: setLive,
        addMark: addMark,
        moveMark: moveMark,
        setFollowUI: setFollowUI,
        syncManualSliders: syncManualSliders
    };
})(window.Corto = window.Corto || {});
