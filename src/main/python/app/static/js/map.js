/* Map: Leaflet basemap + seamarks, the boat, its wake, the course. Everything here is created once and
 * mutated in place; the boat is never re-created (no setIcon) when a new state arrives. */
(function (C) {
    'use strict';

    const COLORS = { mark: '#f97316', port: '#ef4444', wake: '#0b6bcb' };
    const DEFAULT_ZOOM = 17;
    const WAKE_SIM_SECONDS = 90;   // how much sim time of wake to keep
    const WAKE_CHUNKS = 18;        // fading polylines the wake is split into
    const WAKE_MIN_STEP_M = 1.2;   // distance between wake samples
    const WAKE_REFRESH_MS = 90;
    const BOAT_SIZE = [34, 68];
    const UPWIND_TIP = "Upwind leg — navigator can’t tack yet";
    const M_PER_DEG = 111320;

    const HULL_SVG = `
<svg viewBox="0 0 48 100" aria-hidden="true">
  <g id="boat-rudder" transform="rotate(0 24 90)"><rect x="22.5" y="88" width="3" height="11" rx="1.3" fill="#0b1620"/></g>
  <path d="M24 4 C34 20 38.5 42 37.5 62 C37 76 34.5 86 31.5 90 L16.5 90 C13.5 86 11 76 10.5 62 C9.5 42 14 20 24 4 Z"
        fill="#f5f8fb" stroke="#0b1620" stroke-width="2.2" stroke-linejoin="round"/>
  <path d="M24 13 C27.5 26 29.5 44 28.5 60 L19.5 60 C18.5 44 20.5 26 24 13 Z" fill="#dbe4ec"/>
  <g id="boat-boom" transform="rotate(0 24 38)">
    <path id="boat-sail-halo" d="M24 38 Q19 63 24 87" fill="none" stroke="#0b1620" stroke-width="6" stroke-linecap="round"/>
    <path id="boat-sail" d="M24 38 Q19 63 24 87" fill="none" stroke="#ffffff" stroke-width="3.4" stroke-linecap="round"/>
  </g>
  <circle cx="24" cy="38" r="3.2" fill="#0b1620"/>
</svg>`;

    let map, boatMarker, boatRot, boomEl, sailEl, sailHaloEl, rudderEl;
    let wakeRenderer, wakePolys = [], wakePts = [], lastWakeDraw = 0;
    let courseSig = '', markMarkers = [], legLines = [], activeRing = null, approach = null, approachHit = null, approachUp = false;
    let following = false, editing = false, draggingMark = false, sailSign = 1;
    let opts = {};
    let railEl = null;

    function railHalf() {
        if (!railEl) railEl = document.querySelector('.rail');
        return railEl ? railEl.offsetWidth / 2 : 0;
    }

    function init(options) {
        opts = options || {};
        map = L.map('map', { zoomControl: true, minZoom: 3, maxZoom: 20, zoomSnap: 1, worldCopyJump: false });
        const tileOpts = { keepBuffer: 4, updateWhenZooming: false };

        L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
            ...tileOpts,
            maxZoom: 19,
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        }).addTo(map);

        map.createPane('seamarks').style.zIndex = 250;
        L.tileLayer('https://tiles.openseamap.org/seamark/{z}/{x}/{y}.png', {
            ...tileOpts,
            pane: 'seamarks',
            maxZoom: 20,
            maxNativeZoom: 18,
            attribution: 'Seamarks &copy; <a href="https://www.openseamap.org">OpenSeaMap</a>'
        }).addTo(map);

        L.control.scale({ metric: true, imperial: false, position: 'bottomright', maxWidth: 140 }).addTo(map);

        map.createPane('wake').style.zIndex = 380;
        wakeRenderer = L.canvas({ pane: 'wake', padding: 0.5 });

        const start = opts.center || [43.6545, -70.223];
        map.setView(start, DEFAULT_ZOOM, { animate: false });

        // The boat: one persistent marker whose inner element is rotated with a CSS transform
        const icon = L.divIcon({
            className: 'boat-icon',
            html: '<div class="boat-rot">' + HULL_SVG + '</div>',
            iconSize: BOAT_SIZE,
            iconAnchor: [BOAT_SIZE[0] / 2, BOAT_SIZE[1] / 2]
        });
        boatMarker = L.marker(start, { icon: icon, interactive: false, keyboard: false, zIndexOffset: 1000 }).addTo(map);
        const el = boatMarker.getElement();
        boatRot = el.querySelector('.boat-rot');
        boomEl = el.querySelector('#boat-boom');
        sailEl = el.querySelector('#boat-sail');
        sailHaloEl = el.querySelector('#boat-sail-halo');
        rudderEl = el.querySelector('#boat-rudder');

        map.on('click', function (e) {
            if (editing && opts.onAddMark) opts.onAddMark(e.latlng);
        });
        map.on('dragstart', function () {
            if (following && opts.onUserPan) opts.onUserPan();
        });
        return map;
    }

    // --- camera -----------------------------------------------------------------------------------------

    /** Centre the map so that `ll` sits in the middle of the part of the map not covered by the rail. */
    function centerOn(lat, lng, zoom) {
        const z = zoom == null ? map.getZoom() : zoom;
        const p = map.project(L.latLng(lat, lng), z).add([railHalf(), 0]);
        map.setView(map.unproject(p, z), z, { animate: false });
    }

    function followStep(lat, lng) {
        const z = map.getZoom();
        const want = map.project(L.latLng(lat, lng), z).add([railHalf(), 0]);
        const have = map.project(map.getCenter(), z);
        const d = want.subtract(have);
        if (Math.abs(d.x) >= 0.5 || Math.abs(d.y) >= 0.5) map.panBy(d, { animate: false, noMoveStart: true });
    }

    function setFollow(on) { following = !!on; }
    function isFollowing() { return following; }
    function setZoom(z) { map.setZoom(z, { animate: false }); }

    function fitCourse(state, maxZoom) {
        const pts = (state.course.marks || []).map(m => [m.lat, m.lng]);
        pts.push([state.lat, state.lng]);
        if (pts.length < 2) { centerOn(state.lat, state.lng, DEFAULT_ZOOM); return; }
        const b = L.latLngBounds(pts);
        map.fitBounds(b, {
            animate: false,
            maxZoom: maxZoom || 18,
            paddingTopLeft: [60, 60],
            paddingBottomRight: [railHalf() * 2 + 60, 190]
        });
    }

    // --- wake -------------------------------------------------------------------------------------------

    function metres(a, b) {
        const dy = (b[0] - a[0]) * M_PER_DEG;
        const dx = (b[1] - a[1]) * M_PER_DEG * Math.cos(a[0] * Math.PI / 180);
        return Math.hypot(dx, dy);
    }

    function clearWake() {
        wakePts = [];
        wakePolys.forEach(p => p.setLatLngs([]));
    }

    function updateWake(ll, simTime, nowMs) {
        const last = wakePts[wakePts.length - 1];
        if (last && (simTime < last.t - 1 || metres(last.ll, ll) > 150)) { clearWake(); }  // reset / jump
        const tail = wakePts[wakePts.length - 1];
        if (!tail || metres(tail.ll, ll) >= WAKE_MIN_STEP_M) wakePts.push({ ll: ll, t: simTime });
        while (wakePts.length && wakePts[0].t < simTime - WAKE_SIM_SECONDS) wakePts.shift();

        if (nowMs - lastWakeDraw < WAKE_REFRESH_MS) return;
        lastWakeDraw = nowMs;
        if (!wakePolys.length) {
            for (let i = 0; i < WAKE_CHUNKS; i++) {
                wakePolys.push(L.polyline([], { renderer: wakeRenderer, interactive: false, color: COLORS.wake, lineCap: 'round', lineJoin: 'round' }).addTo(map));
            }
        }
        const pts = wakePts.map(p => p.ll);
        pts.push(ll);
        const n = pts.length;
        for (let i = 0; i < WAKE_CHUNKS; i++) {
            const a = Math.floor(i * (n - 1) / WAKE_CHUNKS);
            const b = Math.floor((i + 1) * (n - 1) / WAKE_CHUNKS);
            const youth = (i + 1) / WAKE_CHUNKS;  // 1 = newest
            wakePolys[i].setLatLngs(n > 1 && b > a ? pts.slice(a, b + 1) : []);
            wakePolys[i].setStyle({ opacity: 0.15 + 0.75 * Math.pow(youth, 1.3), weight: 1.8 + 3.6 * youth });
        }
    }

    // --- course -----------------------------------------------------------------------------------------

    function markIcon(n, active, done) {
        return L.divIcon({
            className: 'mark-icon',
            html: '<div class="mark-disc' + (active ? ' active' : '') + (done ? ' done' : '') + '">' + n + '</div>',
            iconSize: [28, 28],
            iconAnchor: [14, 14]
        });
    }

    function clearCourseLayers() {
        markMarkers.forEach(m => map.removeLayer(m));
        legLines.forEach(l => map.removeLayer(l));
        markMarkers = []; legLines = [];
        if (activeRing) { map.removeLayer(activeRing); activeRing = null; }
        if (approach) { map.removeLayer(approach); approach = null; }
        if (approachHit) { map.removeLayer(approachHit); approachHit = null; }
    }

    function tipFor(line) {
        line.bindTooltip(UPWIND_TIP, { sticky: true, direction: 'top', className: 'corto-tip up', opacity: 1 });
    }

    function syncCourse(state, editable) {
        if (draggingMark) return;
        const course = state.course;
        const marks = course.marks || [];
        const sig = JSON.stringify([marks, course.loop, course.active, course.finished, (course.legs || []).map(l => l.upwind ? 1 : 0), !!editable]);
        if (sig === courseSig) return;
        courseSig = sig;
        clearCourseLayers();
        if (!marks.length) return;

        const ll = marks.map(m => [m.lat, m.lng]);
        // A two-mark loop sails the same line both ways: draw it once, red if either direction is upwind
        const byLine = {};
        (course.legs || []).forEach(function (leg) {
            const key = Math.min(leg.from, leg.to) + '-' + Math.max(leg.from, leg.to);
            if (!byLine[key]) byLine[key] = Object.assign({}, leg);
            else byLine[key].upwind = byLine[key].upwind || leg.upwind;
        });
        Object.keys(byLine).map(k => byLine[k]).forEach(function (leg) {
            const pts = [ll[leg.from], ll[leg.to]];
            const up = !!leg.upwind;
            const line = L.polyline(pts, {
                color: up ? COLORS.port : COLORS.mark, weight: 2.4, opacity: up ? 0.95 : 0.85,
                dashArray: up ? '3 8' : '9 8', interactive: false, className: up ? 'leg leg-upwind' : 'leg'
            }).addTo(map);
            legLines.push(line);
            if (up) {
                // A fat invisible line on top makes the dashed leg easy to hover
                const hit = L.polyline(pts, { color: '#000', weight: 18, opacity: 0, className: 'leg-hit leg-upwind-hit' }).addTo(map);
                tipFor(hit);
                legLines.push(hit);
            }
        });

        marks.forEach(function (m, i) {
            const marker = L.marker([m.lat, m.lng], {
                icon: markIcon(i + 1, i === course.active && !course.finished, course.finished || i < course.active),
                draggable: !!editable, keyboard: false, zIndexOffset: 500, title: 'Mark ' + (i + 1)
            }).addTo(map);
            marker.on('dragstart', function () { draggingMark = true; });
            marker.on('dragend', function (e) {
                draggingMark = false;
                if (opts.onMoveMark) opts.onMoveMark(i, e.target.getLatLng());
            });
            markMarkers.push(marker);
        });

        if (!course.finished && marks[course.active]) {
            const a = marks[course.active];
            activeRing = L.circle([a.lat, a.lng], {
                radius: course.radius_m || 15, color: COLORS.mark, weight: 1.6, dashArray: '3 4', fillColor: COLORS.mark, fillOpacity: 0.1, interactive: false
            }).addTo(map);
        }
    }

    function updateApproach(ll, state, show) {
        const target = state.to_mark && state.course.marks[state.to_mark.index];
        if (!show || !target) {
            if (approach) { map.removeLayer(approach); approach = null; }
            if (approachHit) { map.removeLayer(approachHit); approachHit = null; }
            return;
        }
        const up = !!state.to_mark.upwind;
        const pts = [ll, [target.lat, target.lng]];
        if (!approach || approachUp !== up) {
            if (approach) map.removeLayer(approach);
            if (approachHit) { map.removeLayer(approachHit); approachHit = null; }
            approach = L.polyline(pts, {
                color: up ? COLORS.port : COLORS.mark, weight: up ? 2.6 : 1.8, opacity: up ? 0.95 : 0.65,
                dashArray: up ? '3 8' : '2 7', interactive: false, className: up ? 'leg leg-upwind leg-approach' : 'leg leg-approach'
            }).addTo(map);
            if (up) {
                // The boat moves, so give the dashed line a fat invisible twin that is easy to hover
                approachHit = L.polyline(pts, { color: '#000', weight: 18, opacity: 0, className: 'leg-hit leg-upwind-hit' }).addTo(map);
                tipFor(approachHit);
            }
            approachUp = up;
        } else {
            approach.setLatLngs(pts);
            if (approachHit) approachHit.setLatLngs(pts);
        }
    }

    function setEditing(on) {
        editing = !!on;
        map.getContainer().classList.toggle('editing', editing);
        courseSig = '';  // marks need to flip draggable on/off
    }

    // --- per-frame --------------------------------------------------------------------------------------

    function render(view, state, nowMs, autoMode) {
        const ll = [view.lat, view.lng];
        boatMarker.setLatLng(ll);
        boatRot.style.transform = 'rotate(' + view.heading.toFixed(2) + 'deg)';

        // Boom angle (signed, + = swung to port, i.e. wind over the starboard side) is eased by main.js from the
        // sheet setting: sheeted in (100) is nearly fore-and-aft, eased (0) is far out.
        const rot = view.boom;
        boomEl.setAttribute('transform', 'rotate(' + rot.toFixed(2) + ' 24 38)');
        const sign = Math.abs(rot) > 2 ? Math.sign(rot) : sailSign;
        if (sign !== sailSign) {
            sailSign = sign;
            const d = 'M24 38 Q' + (24 - 5 * sign) + ' 63 24 87';
            sailEl.setAttribute('d', d);
            sailHaloEl.setAttribute('d', d);
        }
        rudderEl.setAttribute('transform', 'rotate(' + (-view.rudder_deg).toFixed(2) + ' 24 90)');

        if (following) followStep(view.lat, view.lng);
        updateWake(ll, state.sim_time, nowMs);
        updateApproach(ll, state, autoMode);
    }

    C.Map = {
        init: init,
        render: render,
        syncCourse: syncCourse,
        setFollow: setFollow,
        isFollowing: isFollowing,
        setEditing: setEditing,
        centerOn: centerOn,
        setZoom: setZoom,
        fitCourse: fitCourse,
        clearWake: clearWake,
        get leaflet() { return map; }
    };
})(window.Corto = window.Corto || {});
