/* Main: API client, 10 Hz polling, requestAnimationFrame smoothing, and URL parameters
 *   ?demo=1&warp=15   simulator only: reset, load the demo course, start the autopilot, follow camera at zoom 18, hints hidden
 *   ?warp=N           simulator only: simulation speed (1..30)
 *   ?scale=1          simulator only: demo course scale (default 1.5)
 *   ?zoom=N ?follow=1 ?hints=0   camera zoom, follow camera, hide the hints
 * With the real boat (body data-source="boat") some state is null: the boat has no GPS fix yet, or its protocol
 * does not carry the value. Nothing here assumes a number.
 */
(function (C) {
    'use strict';

    const BOAT = document.body.dataset.source === 'boat';
    const POLL_MS = 100;
    const TAU_S = BOAT ? 0.7 : 0.08;  // smoothing time constant for what is drawn between polls (the boat reports every 2 s)
    const DEFAULT_CENTER = [43.6545, -70.2230];  // where the map starts until the boat has a position
    const SNAP_JUMP_M = 40;       // a jump bigger than this (a reset) snaps instead of gliding
    const M_PER_DEG = 111320;
    const params = new URLSearchParams(location.search);

    let state = null, view = null;
    let seq = 0, accepted = 0, lastOk = 0, lastSign = 1, centred = false;

    // --- API ----------------------------------------------------------------------------------------------

    function request(method, url, body) {
        const id = ++seq;
        return fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: body === undefined ? undefined : JSON.stringify(body)
        }).then(r => r.json().then(j => {
            if (!r.ok) throw new Error(j.message || ('HTTP ' + r.status));
            if (j.state) { accept(j.state, id); return j.state; }
            return j;
        })).catch(err => { console.warn('Corto request failed:', method, url, err.message); });
    }

    const api = {
        control: body => request('POST', '/api/control', body),
        course: body => request('POST', '/api/course', body),
        clearCourse: () => request('DELETE', '/api/course'),
        demo: body => request('POST', '/api/course/demo', body),
        reset: body => request('POST', '/api/reset', body)
    };
    C.api = api;

    // --- state + smoothing ----------------------------------------------------------------------------------

    const wrap180 = a => ((a + 540) % 360) - 180;

    /** What to draw: the state's numbers, where a null (no fix, or not reported) keeps the previous value so nothing
     *  glides off to 0 or snaps to north. The instruments show "--" for those from the raw state. */
    function targetFrom(s, prev) {
        const tm = s.to_mark;
        const keep = (key, dflt) => s[key] != null ? s[key] : (prev && prev[key] != null ? prev[key] : dflt);
        const trim = keep('trim', 0);
        const boomDeg = 6 + (100 - trim) / 100 * 74;
        // The boom swings to leeward. The boat reports no apparent wind, so its true wind angle gives the side.
        const side = s.awa != null ? s.awa : s.twa;
        if (side != null && Math.abs(side) > 1) lastSign = Math.sign(side);
        return {
            lat: keep('lat', DEFAULT_CENTER[0]), lng: keep('lng', DEFAULT_CENTER[1]),
            heading: keep('heading', 0), cog: keep('cog', 0), twd: keep('twd', 0), awa: keep('awa', 0), twa: keep('twa', 0),
            brg: tm ? tm.bearing : (prev ? prev.brg : 0), dist: tm ? tm.distance_m : 0,
            rudder_deg: keep('rudder_deg', 0), trim: trim, opt_trim: keep('opt_trim', 50), heel: keep('heel', 0),
            aws: keep('aws', 0), tws: keep('tws', 0), sog: keep('sog', 0), stw: keep('stw', 0), boom: lastSign * boomDeg
        };
    }

    const ANGLES = ['heading', 'cog', 'twd', 'awa', 'twa', 'brg'];
    const LINEAR = ['lat', 'lng', 'dist', 'rudder_deg', 'trim', 'opt_trim', 'heel', 'aws', 'tws', 'sog', 'stw', 'boom'];

    const hasFix = s => s.lat != null && s.lng != null;

    function metresApart(a, b) {
        const dy = (a.lat - b.lat) * M_PER_DEG, dx = (a.lng - b.lng) * M_PER_DEG * Math.cos(a.lat * Math.PI / 180);
        return Math.hypot(dx, dy);
    }

    function accept(s, id) {
        if (id !== undefined) {
            if (id < accepted) return;  // an older response arriving late
            accepted = id;
        }
        const target = targetFrom(s, view);
        if (!view || metresApart(view, target) > SNAP_JUMP_M) {
            view = Object.assign({}, target);
        }
        state = s;
        state._target = target;
        C.Controls.onState(s);
        C.Map.syncCourse(s, C.Controls.mode === 'auto');
        if (!centred && hasFix(s)) {  // the boat's first fix: bring the map to it, once
            centred = true;
            C.Map.centerOn(s.lat, s.lng, parseInt(params.get('zoom'), 10) > 0 ? parseInt(params.get('zoom'), 10) : 17);
        }
    }

    function smooth(dt) {
        const k = 1 - Math.exp(-dt / TAU_S);
        const t = state._target;
        for (const key of LINEAR) view[key] += (t[key] - view[key]) * k;
        for (const key of ANGLES) view[key] = (view[key] + wrap180(t[key] - view[key]) * k + 360) % 360;
        // Signed wind angles stay in (-180, 180] so the boom and the arrows know the side
        view.awa = wrap180(view.awa);
        view.twa = wrap180(view.twa);
    }

    // --- loops --------------------------------------------------------------------------------------------

    let lastFrame = 0;
    function frame(now) {
        const dt = Math.min(0.1, Math.max(0.001, (now - lastFrame) / 1000 || 0.016));
        lastFrame = now;
        if (state && view) {
            smooth(dt);
            const upwind = !!(state.to_mark && state.to_mark.upwind);
            // The simulator's autopilot is a mode; with the boat the line shows while a course is being sent
            const approach = BOAT ? (!!state.running || (C.Controls.mode === 'auto' && upwind))
                : state.mode === 'auto' && (state.running || upwind);
            C.Map.render(view, state, now, approach && hasFix(state));
            C.Instruments.render(view, state);
        }
        requestAnimationFrame(frame);
    }

    function poll() {
        const t0 = performance.now();
        const id = ++seq;
        fetch('/api/state', { cache: 'no-store' })
            .then(r => r.json())
            .then(s => { accept(s, id); lastOk = performance.now(); C.Controls.setLink(true, s); })
            .catch(err => {
                console.warn('Corto poll failed:', err && err.message);
                if (performance.now() - lastOk > 1500) C.Controls.setLink(false, null);
            })
            .then(() => setTimeout(poll, Math.max(0, POLL_MS - (performance.now() - t0))));
    }

    // Instruments grow a little on tall windows (rail width is fixed, so the scale tops out at 1.3)
    function fitScale() {
        const s = Math.min(1.3, Math.max(1, (window.innerHeight - 48) / 700));
        document.documentElement.style.setProperty('--s', s.toFixed(3));
    }
    window.addEventListener('resize', fitScale);
    fitScale();

    // --- start up -----------------------------------------------------------------------------------------

    function applyParams() {
        // demo and warp are the simulator's; with the real boat they are ignored
        const warp = BOAT ? NaN : parseFloat(params.get('warp'));
        const demo = !BOAT && params.get('demo') === '1';
        const zoom = parseInt(params.get('zoom'), 10);
        if (demo || params.get('hints') === '0') document.body.classList.add('no-hints');

        let chain = Promise.resolve();
        if (demo) {
            const scale = parseFloat(params.get('scale'));
            chain = chain
                .then(() => api.reset({}))
                .then(() => api.demo(scale > 0 ? { scale: scale } : {}))
                .then(() => api.control({ mode: 'auto', running: true, time_scale: warp > 0 ? warp : 15 }))
                .then(s => {
                    C.Map.clearWake();
                    C.Controls.setFollowUI(true);
                    if (s) C.Map.centerOn(s.lat, s.lng, zoom > 0 ? zoom : 18);
                });
        } else {
            if (warp > 0) chain = chain.then(() => api.control({ time_scale: warp }));
            if (params.get('follow') === '1') C.Controls.setFollowUI(true);
            if (zoom > 0 && state && hasFix(state)) C.Map.centerOn(state.lat, state.lng, zoom);
        }
        return chain;
    }

    function start() {
        fetch('/api/state', { cache: 'no-store' }).then(r => r.json()).then(first => {
            C.Map.init({
                center: hasFix(first) ? [first.lat, first.lng] : DEFAULT_CENTER,
                onAddMark: C.Controls.addMark,
                onMoveMark: C.Controls.moveMark,
                onUserPan: () => C.Controls.setFollowUI(false)
            });
            C.Instruments.init();
            C.Controls.init({ api: api });
            centred = hasFix(first);  // otherwise accept() centres the map on the boat's first fix
            accept(first);
            if (centred) C.Map.centerOn(first.lat, first.lng, 17);
            lastOk = performance.now();
            C.Controls.setLink(true, first);
            applyParams().then(() => { poll(); });
            requestAnimationFrame(frame);
        }).catch(() => setTimeout(start, 1000));
    }

    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start);
    else start();
})(window.Corto = window.Corto || {});
