/* Instruments: the wind/compass dial, the numeric tiles, the rudder bar and the sheet bar.
 * The SVG skeleton is in index.html; this file builds the ticks and moves things each frame.
 * A value the source does not report (the boat has no COG, SOG, wind speed, apparent wind or heel; none of
 * it before its first report) is null in the state and shows as "--" here. */
(function (C) {
    'use strict';

    const NS = 'http://www.w3.org/2000/svg';
    const CX = 120, CY = 120;
    const RUDDER_FULL_DEG = 45;
    const TRIM_OK_BAND = 10;   // +/- sheet points around the optimal trim that still count as TRIMMED

    const el = {};
    const last = new Map();
    const ringLabels = [];
    let lastLabelHeading = null;

    const $ = id => document.getElementById(id);

    /** Write text only when it changed, so per-frame calls stay cheap. */
    function setText(node, text) {
        if (last.get(node) !== text) { last.set(node, text); node.textContent = text; }
    }

    /** Show a number, or "--" muted when the source does not report it. */
    function setNum(node, text, missing) {
        setText(node, missing ? '--' : text);
        const key = node.id + ':na';
        if (last.get(key) !== missing) { last.set(key, missing); node.classList.toggle('na', missing); }
    }

    function setAttr(node, name, value) {
        const key = node.id + ':' + name;
        if (last.get(key) !== value) { last.set(key, value); node.setAttribute(name, value); }
    }

    function polar(r, deg) {
        const a = deg * Math.PI / 180;
        return [CX + r * Math.sin(a), CY - r * Math.cos(a)];
    }

    function arc(r, fromDeg, toDeg) {
        const a = polar(r, fromDeg), b = polar(r, toDeg);
        return 'M' + a[0].toFixed(2) + ' ' + a[1].toFixed(2) + ' A' + r + ' ' + r + ' 0 0 1 ' + b[0].toFixed(2) + ' ' + b[1].toFixed(2);
    }

    function svg(tag, attrs, text) {
        const n = document.createElementNS(NS, tag);
        for (const k in attrs) n.setAttribute(k, attrs[k]);
        if (text != null) n.textContent = text;
        return n;
    }

    function buildDial() {
        // Close-hauled sectors, fixed to the boat: wind 30..50 degrees off the bow on either side
        $('sector-port').setAttribute('d', arc(111, -50, -30));
        $('sector-stbd').setAttribute('d', arc(111, 30, 50));

        const ticks = $('ring-ticks');
        for (let d = 0; d < 360; d += 10) {
            const major = d % 30 === 0;
            const p1 = polar(106, d), p2 = polar(major ? 95 : 101, d);
            ticks.appendChild(svg('line', {
                x1: p1[0].toFixed(2), y1: p1[1].toFixed(2), x2: p2[0].toFixed(2), y2: p2[1].toFixed(2),
                class: major ? 'tick major' : 'tick'
            }));
        }
        const labels = $('ring-labels');
        const cardinal = { 0: 'N', 90: 'E', 180: 'S', 270: 'W' };
        for (let d = 0; d < 360; d += 30) {
            const isCard = d in cardinal;
            const p = polar(isCard ? 82 : 84, d);
            const t = svg('text', {
                x: p[0].toFixed(2), y: p[1].toFixed(2),
                class: 'ring-label' + (isCard ? ' cardinal' : '') + (d === 0 ? ' north' : '')
            }, isCard ? cardinal[d] : String(d));
            t._pivot = p[0].toFixed(2) + ' ' + p[1].toFixed(2);
            labels.appendChild(t);
            ringLabels.push(t);
        }
    }

    function init() {
        ['dial', 'ring', 'true-wind', 'app-wind', 'mark-tick', 'sil-boom', 'dial-hdg',
            't-hdg', 't-cog', 't-sog', 't-stw', 't-heel', 't-tws', 't-twa', 't-aws', 't-awa', 't-dist', 't-brg', 'tile-mark',
            'rudder-read', 'rudder-fill-port', 'rudder-fill-stbd', 'sheet-read', 'sheet-state', 'sheet-fill', 'sheet-opt',
            'lg-app'
        ].forEach(id => { el[id] = $(id); });
        buildDial();
    }

    const wrapDelta = (a, b) => ((a - b + 540) % 360) - 180;
    const pad3 = deg => String(((Math.round(deg) % 360) + 360) % 360).padStart(3, '0') + '°';
    const side = v => v < 0 ? 'P' : 'S';
    const fmtKn = v => (Math.abs(v) < 0.05 ? 0 : v).toFixed(1);

    function fmtDist(m) {
        return m < 1000 ? Math.round(m) + ' m' : (m / 1000).toFixed(2) + ' km';
    }

    /** Called every animation frame with the smoothed `view` and the latest raw `state`. */
    function render(view, state) {
        setAttr(el['ring'], 'transform', 'rotate(' + (-view.heading).toFixed(2) + ' 120 120)');
        // Keep the ring labels upright while the ring turns underneath them
        if (lastLabelHeading === null || Math.abs(wrapDelta(view.heading, lastLabelHeading)) > 0.15) {
            lastLabelHeading = view.heading;
            const rot = 'rotate(' + view.heading.toFixed(2) + ' ';
            for (const t of ringLabels) t.setAttribute('transform', rot + t._pivot + ')');
        }
        setAttr(el['true-wind'], 'transform', 'rotate(' + view.twd.toFixed(2) + ' 120 120)');
        setAttr(el['true-wind'], 'visibility', state.twd == null ? 'hidden' : 'visible');
        setAttr(el['app-wind'], 'transform', 'rotate(' + view.awa.toFixed(2) + ' 120 120)');
        // No apparent wind from the boat: no arrow and no legend entry for it
        setAttr(el['app-wind'], 'visibility', state.awa == null ? 'hidden' : 'visible');
        if (last.get('lg-app') !== (state.awa == null)) { last.set('lg-app', state.awa == null); el['lg-app'].classList.toggle('na', state.awa == null); }
        setAttr(el['sil-boom'], 'transform', 'rotate(' + view.boom.toFixed(1) + ' 0 -4)');

        const hasMark = !!state.to_mark;
        el['tile-mark'].classList.toggle('idle', !hasMark);
        setAttr(el['mark-tick'], 'visibility', hasMark ? 'visible' : 'hidden');
        if (hasMark) setAttr(el['mark-tick'], 'transform', 'rotate(' + view.brg.toFixed(2) + ' 120 120)');

        const hdg = state.heading == null ? '---°' : pad3(view.heading);
        setText(el['dial-hdg'], hdg);
        setText(el['t-hdg'], hdg);
        setNum(el['t-cog'], pad3(view.cog), state.cog == null);
        setNum(el['t-sog'], fmtKn(view.sog), state.sog == null);
        setNum(el['t-stw'], fmtKn(view.stw), state.stw == null);
        const heel = Math.abs(view.heel);
        setNum(el['t-heel'], heel < 0.5 ? '0°' : Math.round(heel) + '° ' + (view.heel < 0 ? 'P' : 'S'), state.heel == null);
        setNum(el['t-tws'], fmtKn(view.tws), state.tws == null);
        setNum(el['t-twa'], Math.round(Math.abs(view.twa)) + '° ' + side(view.twa), state.twa == null);
        setNum(el['t-aws'], fmtKn(view.aws), state.aws == null);
        setNum(el['t-awa'], Math.round(Math.abs(view.awa)) + '° ' + side(view.awa), state.awa == null);
        setText(el['t-dist'], hasMark ? fmtDist(view.dist) : '--');
        setText(el['t-brg'], hasMark ? pad3(view.brg) : '---°');

        // Rudder bar: centred, red to port, green to starboard, +/-45 degrees full scale
        const deg = Math.max(-RUDDER_FULL_DEG, Math.min(RUDDER_FULL_DEG, view.rudder_deg));
        const half = Math.abs(deg) / RUDDER_FULL_DEG * 50;
        setAttr(el['rudder-fill-port'], 'style', 'width:' + (deg < 0 ? half : 0).toFixed(2) + '%');
        setAttr(el['rudder-fill-stbd'], 'style', 'width:' + (deg > 0 ? half : 0).toFixed(2) + '%');
        const rr = Math.round(Math.abs(deg));
        setText(el['rudder-read'], state.rudder_deg == null ? '--' : rr === 0 ? '0°' : rr + '° ' + (deg < 0 ? 'P' : 'S'));
        el['rudder-read'].className = 'bar-read' + (rr === 0 ? '' : deg < 0 ? ' port' : ' stbd');

        // Sheet bar: eased (left) to sheeted in (right), with the optimal marker and a state word
        const trim = Math.max(0, Math.min(100, view.trim));
        setAttr(el['sheet-fill'], 'style', 'width:calc(' + trim.toFixed(2) + '% - 2px)');
        setAttr(el['sheet-opt'], 'style', state.opt_trim == null ? 'display:none' : 'left:' + view.opt_trim.toFixed(2) + '%');
        setText(el['sheet-read'], state.trim == null ? '--' : Math.round(trim) + '%');
        const diff = state.trim - state.opt_trim;
        let word = 'TRIMMED', cls = 'ok';
        if (state.trim == null || state.opt_trim == null) { word = ''; cls = ''; }
        else if (diff < -TRIM_OK_BAND) { word = 'LUFFING'; cls = 'warn'; }
        else if (diff > TRIM_OK_BAND) { word = 'OVER-TRIMMED'; cls = 'warn'; }
        setText(el['sheet-state'], word);
        setAttr(el['sheet-state'], 'class', 'sheet-state ' + cls);
    }

    C.Instruments = { init: init, render: render, fmtDist: fmtDist, pad3: pad3 };
})(window.Corto = window.Corto || {});
