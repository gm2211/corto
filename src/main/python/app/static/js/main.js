/* Main: API client, 10 Hz polling, requestAnimationFrame smoothing, and URL parameters
 *   ?demo=1&warp=15   reset, load the demo course, start the autopilot, follow camera at zoom 18, hints hidden
 *   ?warp=N           simulation speed (1..30)
 *   ?scale=1          demo course scale (default 1.5)
 *   ?zoom=N ?follow=1 ?hints=0   camera zoom, follow camera, hide the hints
 */
(function (C) {
    'use strict';

    const POLL_MS = 100;
    const TAU_S = 0.08;           // smoothing time constant for what is drawn between polls
    const SNAP_JUMP_M = 40;       // a jump bigger than this (a reset) snaps instead of gliding
    const M_PER_DEG = 111320;
    const params = new URLSearchParams(location.search);

    let state = null, view = null;
    let seq = 0, accepted = 0, lastOk = 0, lastSign = 1;

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

    function targetFrom(s, prev) {
        const tm = s.to_mark;
        const boomDeg = 6 + (100 - s.trim) / 100 * 74;
        if (Math.abs(s.awa) > 1) lastSign = Math.sign(s.awa);
        return {
            lat: s.lat, lng: s.lng, heading: s.heading, cog: s.cog, twd: s.twd, awa: s.awa, twa: s.twa,
            brg: tm ? tm.bearing : (prev ? prev.brg : 0), dist: tm ? tm.distance_m : 0,
            rudder_deg: s.rudder_deg, trim: s.trim, opt_trim: s.opt_trim, heel: s.heel,
            aws: s.aws, tws: s.tws, sog: s.sog, stw: s.stw, boom: lastSign * boomDeg
        };
    }

    const ANGLES = ['heading', 'cog', 'twd', 'awa', 'twa', 'brg'];
    const LINEAR = ['lat', 'lng', 'dist', 'rudder_deg', 'trim', 'opt_trim', 'heel', 'aws', 'tws', 'sog', 'stw', 'boom'];

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
            C.Map.render(view, state, now, state.mode === 'auto' && (state.running || !!(state.to_mark && state.to_mark.upwind)));
            C.Instruments.render(view, state);
        }
        requestAnimationFrame(frame);
    }

    function poll() {
        const t0 = performance.now();
        const id = ++seq;
        fetch('/api/state', { cache: 'no-store' })
            .then(r => r.json())
            .then(s => { accept(s, id); lastOk = performance.now(); C.Controls.setLive(true); })
            .catch(() => { if (performance.now() - lastOk > 1500) C.Controls.setLive(false); })
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
        const warp = parseFloat(params.get('warp'));
        const demo = params.get('demo') === '1';
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
            if (zoom > 0 && state) C.Map.centerOn(state.lat, state.lng, zoom);
        }
        return chain;
    }

    function start() {
        fetch('/api/state', { cache: 'no-store' }).then(r => r.json()).then(first => {
            C.Map.init({
                center: [first.lat, first.lng],
                onAddMark: C.Controls.addMark,
                onMoveMark: C.Controls.moveMark,
                onUserPan: () => C.Controls.setFollowUI(false)
            });
            C.Instruments.init();
            C.Controls.init({ api: api });
            accept(first);
            C.Map.centerOn(first.lat, first.lng, 17);
            lastOk = performance.now();
            C.Controls.setLive(true);
            applyParams().then(() => { poll(); });
            requestAnimationFrame(frame);
        }).catch(() => setTimeout(start, 1000));
    }

    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start);
    else start();
})(window.Corto = window.Corto || {});
