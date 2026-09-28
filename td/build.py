"""
Curiosity Loop - network builder.

Save your .toe in the repo root (next to /td and /photos), then in the Textport:

    exec(open(project.folder + '/td/build.py', encoding='utf-8').read())

Re-running is safe: it rebuilds /project1/curiosity_loop and keeps the values
of its custom parameters (tracking CHOP paths, tuning, etc).
Re-run it whenever you add or remove photos.
"""

import os


def _build():
    # CURIOSITY_ROOT lets you build before the .toe is saved in the repo folder
    root_dir = globals().get('CURIOSITY_ROOT') or project.folder
    rel = os.path.normpath(root_dir) == os.path.normpath(project.folder)

    def path(*parts):   # relative to the .toe when possible, so the repo stays portable
        return '/'.join(parts) if rel else os.path.join(root_dir, *parts)
    td_dir = os.path.join(root_dir, 'td')
    photo_dir = os.path.join(root_dir, 'photos')
    if not os.path.isfile(os.path.join(td_dir, 'loop_core.py')):
        print('!! Could not find td/loop_core.py next to this .toe (project.folder = %s).' % root_dir)
        print('!! Save the .toe inside the curiosity-loop folder, then run build again.')
        return

    parent_comp = op('/project1')
    warnings = []

    def setp(o, **pars):
        for name, val in pars.items():
            try:
                p = getattr(o.par, name)
                if isinstance(val, str) and val.startswith('='):
                    p.expr = val[1:]
                else:
                    p.val = val
            except Exception as e:
                warnings.append('%s.par.%s: %s' % (o.path, name, e))

    def place(o, x, y):
        o.nodeX, o.nodeY = x * 180, -y * 140
        return o

    # ---------------------------------------------------------- keep settings
    saved = {}
    old = parent_comp.op('curiosity_loop')
    if old is not None:
        for p in old.customPars:
            if p.mode == ParMode.CONSTANT:
                saved[p.name] = p.val
        old.destroy()

    base = parent_comp.create(baseCOMP, 'curiosity_loop')
    base.nodeX, base.nodeY = 0, 0
    base.color = (0.35, 0.25, 0.5)

    # ---------------------------------------------------------- custom pars
    def f(page, name, label, default, lo, hi, clamp=False):
        par = page.appendFloat(name, label=label)[0]
        par.default = default
        par.val = default
        par.normMin, par.normMax = lo, hi
        if clamp:
            par.clampMin, par.clampMax = True, True
            par.min, par.max = lo, hi
        return par

    def t(page, name, label, default):
        par = page.appendToggle(name, label=label)[0]
        par.default = default
        par.val = default
        return par

    inp = base.appendCustomPage('Input')
    inp.appendCHOP('Handchop', label='Hand Tracking CHOP')
    inp.appendCHOP('Posechop', label='Pose Tracking CHOP')
    inp.appendTOP('Videotop', label='Webcam TOP (ghost)')
    t(inp, 'Mirrorx', 'Mirror X', True)
    m = inp.appendMenu('Yaxis', label='Raw Y Axis')[0]
    m.menuNames, m.menuLabels = ['auto', 'down', 'up'], ['Auto (from pose)', 'Down (MediaPipe raw)', 'Up']
    m = inp.appendMenu('Range', label='Coordinate Range')[0]
    m.menuNames, m.menuLabels = ['auto', 'zeroone', 'm05to05', 'm1to1'], ['Auto', '0 to 1', '-0.5 to 0.5', '-1 to 1']
    f(inp, 'Nearsw', 'Shoulder Width: Close', 0.40, 0.1, 0.8)
    f(inp, 'Farsw', 'Shoulder Width: Far', 0.12, 0.0, 0.5)
    f(inp, 'Ghost', 'Ghost Mirror Opacity', 0.10, 0.0, 1.0)
    t(inp, 'Debug', 'Debug Overlay', False)

    tune = base.appendCustomPage('Tuning')
    f(tune, 'Awarenessgain', 'Awareness Gain (subtle)', 0.3, 0, 1)
    f(tune, 'Orbitgain', 'Orbit Gain (strong)', 1.0, 0, 2)
    f(tune, 'Onehandtime', 'One-Hand Reveal Time (0=off)', 1.5, 0, 5)
    f(tune, 'Dwelltime', 'Point Dwell Time', 1.2, 0.2, 4)
    f(tune, 'Hoverdwelltime', 'Open-Hand Dwell (0=off)', 0.0, 0, 6)
    f(tune, 'Stilltime', 'Stillness Before Forget', 2.5, 0.5, 8)
    f(tune, 'Stillthreshold', 'Stillness Threshold', 0.12, 0, 1)

    sim = base.appendCustomPage('Simulate')
    t(sim, 'Simulate', 'Simulate (no camera)', True)
    t(sim, 'Simperson', 'Person Present', False)
    f(sim, 'Simbodyx', 'Body X', 0.0, -1, 1)
    f(sim, 'Simprox', 'Proximity', 0.5, 0, 1)
    ip = sim.appendInt('Simhands', label='Hands Visible')[0]
    ip.normMin, ip.normMax, ip.clampMin, ip.clampMax, ip.min, ip.max = 0, 2, True, True, 0, 2
    f(sim, 'Simh1x', 'Hand 1 X', -0.4, -1, 1)
    f(sim, 'Simh1y', 'Hand 1 Y', 0.0, -1, 1)
    f(sim, 'Simh2x', 'Hand 2 X', 0.4, -1, 1)
    f(sim, 'Simh2y', 'Hand 2 Y', 0.0, -1, 1)
    t(sim, 'Simpoint', 'Hand 1 Pointing', False)
    f(sim, 'Simhandsize', 'Hand Size (zoom)', 0.12, 0.05, 0.3)

    for name, val in saved.items():
        try:
            getattr(base.par, name).val = val
        except Exception:
            pass

    # ---------------------------------------------------------- scripts
    core = place(base.create(textDAT, 'loop_core'), 0, 0)
    setp(core, file=path('td', 'loop_core.py'), syncfile=True)
    glue = place(base.create(textDAT, 'loop_td'), 1, 0)
    setp(glue, file=path('td', 'loop_td.py'), syncfile=True)
    ex = place(base.create(executeDAT, 'frame_exec'), 2, 0)
    ex.text = (
        "# Runs the Curiosity Loop once per frame. Logic lives in loop_core / loop_td.\n"
        "def onFrameStart(frame):\n"
        "\top('loop_td').module.update()\n"
        "\treturn\n")
    setp(ex, framestart=True, active=True)

    # ---------------------------------------------------------- photos
    exts = ('.jpg', '.jpeg', '.png', '.tif', '.tiff', '.bmp', '.webp', '.exr')
    files = sorted(fn for fn in os.listdir(photo_dir) if fn.lower().endswith(exts)) if os.path.isdir(photo_dir) else []
    files = files[:24]
    if not files:
        print('!! No images in %s - run tools/make_placeholders.py or add photos.' % photo_dir)

    for i, fn in enumerate(files):
        row, col = 2 + (i // 8) * 3, i % 8
        img = place(base.create(moviefileinTOP, 'img%d' % i), col, row)
        setp(img, file=path('photos', fn))
        mat = place(base.create(constantMAT, 'mat_photo%d' % i), col, row + 1)
        setp(mat, colormap=img.name, blending=True, alpha=1.0)
        geo = place(base.create(geometryCOMP, 'photo%d' % i), col, row + 2)
        for child in list(geo.children):
            child.destroy()
        rect = geo.create(rectangleSOP, 'rect')
        setp(rect, sizex=2.4, sizey=1.8, texture='face')
        rect.render = rect.display = True
        setp(geo, material=mat.path)

    # ---------------------------------------------------------- hand cursors
    for i in range(2):
        mat = place(base.create(constantMAT, 'mat_cursor%d' % i), 9 + i, 2)
        # no depth: a faint cursor must never punch a hole in the photo behind it
        setp(mat, colorr=1.0, colorg=0.95, colorb=0.85, alpha=0.0, blending=True,
             depthtest=False, depthwriting=False)
        geo = place(base.create(geometryCOMP, 'cursor%d' % i), 9 + i, 3)
        for child in list(geo.children):
            child.destroy()
        circ = geo.create(circleSOP, 'circ')
        setp(circ, radx=1.0, rady=1.0, divs=48)
        circ.render = circ.display = True
        setp(geo, material=mat.path, render=False, drawpriority=-1)

    # ---------------------------------------------------------- render
    cam = place(base.create(cameraCOMP, 'cam'), 11, 2)
    setp(cam, tz=10, projection='ortho', orthowidth=16)
    render = place(base.create(renderTOP, 'render1'), 12, 2)
    setp(render, camera='cam', geometry='photo* cursor*', outputresolution='custom',
         resolutionw=1280, resolutionh=720, bgcolorr=0, bgcolorg=0, bgcolorb=0, bgcolora=0)

    # trails: the "memory" that only appears in the final Orbit stage
    fb = place(base.create(feedbackTOP, 'fb'), 12, 4)
    fb.inputConnectors[0].connect(render)
    decay = place(base.create(levelTOP, 'fb_decay'), 13, 4)
    decay.inputConnectors[0].connect(fb)
    setp(decay, opacity=0.0)
    trail_over = place(base.create(overTOP, 'trail_over'), 14, 2)
    trail_over.inputConnectors[0].connect(render)
    trail_over.inputConnectors[1].connect(decay)
    trail_out = place(base.create(nullTOP, 'trail_out'), 15, 2)
    trail_out.inputConnectors[0].connect(trail_over)
    setp(fb, top='trail_out')

    # optional ghost of the webcam behind everything
    black = place(base.create(constantTOP, 'black'), 12, 6)
    setp(black, outputresolution='custom', resolutionw=1280, resolutionh=720,
         colorr=0, colorg=0, colorb=0, alpha=1)
    gsel = place(base.create(selectTOP, 'ghost_sel'), 13, 7)
    setp(gsel, top='black')
    gflip = place(base.create(flipTOP, 'ghost_flip'), 14, 7)
    gflip.inputConnectors[0].connect(gsel)
    setp(gflip, flipx="=parent().par.Mirrorx")
    gfit = place(base.create(fitTOP, 'ghost_fit'), 15, 7)
    gfit.inputConnectors[0].connect(gflip)
    setp(gfit, outputresolution='custom', resolutionw=1280, resolutionh=720)
    glevel = place(base.create(levelTOP, 'ghost_level'), 16, 7)
    glevel.inputConnectors[0].connect(gfit)
    setp(glevel, opacity=0.1)
    gover = place(base.create(overTOP, 'ghost_over'), 17, 6)
    gover.inputConnectors[0].connect(glevel)
    gover.inputConnectors[1].connect(black)
    gswitch = place(base.create(switchTOP, 'ghost_switch'), 18, 6)
    gswitch.inputConnectors[0].connect(black)
    gswitch.inputConnectors[1].connect(gover)
    setp(gswitch, index=0)

    scene = place(base.create(overTOP, 'scene'), 19, 2)
    scene.inputConnectors[0].connect(trail_out)
    scene.inputConnectors[1].connect(gswitch)

    # warp driven by hand velocity during Distortion
    noise = place(base.create(noiseTOP, 'warp_noise'), 19, 4)
    setp(noise, outputresolution='custom', resolutionw=256, resolutionh=256, mono=False,
         tz='=absTime.seconds * 0.35')
    warp = place(base.create(displaceTOP, 'warp'), 20, 2)
    warp.inputConnectors[0].connect(scene)
    warp.inputConnectors[1].connect(noise)
    setp(warp, displaceweightx=0.0, displaceweighty=0.0)

    master = place(base.create(levelTOP, 'master'), 21, 2)
    master.inputConnectors[0].connect(warp)

    dtext = place(base.create(textTOP, 'debug_text'), 21, 4)
    setp(dtext, outputresolution='custom', resolutionw=1280, resolutionh=720,
         bgalpha=0.0, fontsizex=18, alignx='left', aligny='top', text='')
    dover = place(base.create(overTOP, 'debug_over'), 22, 4)
    dover.inputConnectors[0].connect(dtext)
    dover.inputConnectors[1].connect(master)
    dswitch = place(base.create(switchTOP, 'debug_switch'), 23, 2)
    dswitch.inputConnectors[0].connect(master)
    dswitch.inputConnectors[1].connect(dover)

    out = place(base.create(nullTOP, 'out'), 24, 2)
    out.inputConnectors[0].connect(dswitch)
    out_top = place(base.create(outTOP, 'out1'), 25, 2)
    out_top.inputConnectors[0].connect(out)
    base.viewer = True

    win = place(base.create(windowCOMP, 'window'), 25, 4)
    setp(win, winop='out', winw=1280, winh=720, borders=False)

    # ---------------------------------------------------------- done
    try:
        glue.module.Reset()
    except Exception as e:
        warnings.append('loop_td reset: %s' % e)
    print('== Curiosity Loop built: %d photos -> %s' % (len(files), base.path))
    if warnings:
        print('== %d parameter warnings (usually harmless - paste to Claude if visuals look wrong):' % len(warnings))
        for w in warnings:
            print('   ', w)
    if rel:
        try:
            project.save()
            print('== Saved %s' % project.name)
        except Exception as e:
            print('!! Could not save the project: %s' % e)
    print('== Next: Simulate page -> toggle Person Present, set Hands Visible = 2, etc.')
    print('== Or wire MediaPipe: set Input page -> Hand/Pose Tracking CHOP, turn off Simulate.')


_build()
