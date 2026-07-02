import adsk.core, adsk.fusion, math

def run(_context: str):
    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    root = design.rootComponent

    GAP       = 0.3    # 零件间距 3mm (cm)
    BAR_W     = 0.2    # 杆宽 2mm (cm)
    BAR_T     = 0.15   # 杆厚 1.5mm (cm)
    FRAME_PAD = 0.3    # 框架边距 3mm (cm)
    hw        = BAR_W / 2

    # 面积阈值决定连接杆数量 (cm²)
    # 投影面积 < AREA_1 → 1根; < AREA_2 → 2根; 否则 → 3根
    AREA_1 = 4.0    # 400 mm²
    AREA_2 = 16.0   # 1600 mm²

    # ── 1. 收集可见实体 ──────────────────────────────────────────
    def is_truly_visible(body):
        if not body.isLightBulbOn:
            return False
        occ = body.assemblyContext
        while occ is not None:
            if not occ.isLightBulbOn:
                return False
            occ = occ.assemblyContext
        return True

    visible_bodies = [b for b in root.bRepBodies if is_truly_visible(b)]
    n = len(visible_bodies)
    if n == 0:
        print('ERROR: 没有找到可见实体。')
        return
    print(f'找到 {n} 个可见实体。')

    moveFts = root.features.moveFeatures

    def move_translate(body, dx, dy, dz):
        t = adsk.core.Matrix3D.create()
        t.translation = adsk.core.Vector3D.create(dx, dy, dz)
        col = adsk.core.ObjectCollection.create()
        col.add(body)
        moveFts.add(moveFts.createInput(col, t))

    def move_rotate(body, angle, axis_vec, origin_pt):
        m = adsk.core.Matrix3D.create()
        m.setToRotation(angle, axis_vec, origin_pt)
        col = adsk.core.ObjectCollection.create()
        col.add(body)
        moveFts.add(moveFts.createInput(col, m))

    # ── 2. 旋转最大平面朝下 + Z=0 对齐 ──────────────────────────
    for body in visible_bodies:
        best_face, best_area = None, -1.0
        for face in body.faces:
            if face.geometry.surfaceType == adsk.core.SurfaceTypes.PlaneSurfaceType:
                if face.area > best_area:
                    best_area = face.area
                    best_face = face
        if best_face is not None:
            normal = adsk.core.Plane.cast(best_face.geometry).normal
            target = adsk.core.Vector3D.create(0, 0, -1)
            dot = normal.dotProduct(target)
            if dot < 0.9999:
                bb = body.boundingBox
                cx = (bb.minPoint.x + bb.maxPoint.x) / 2
                cy = (bb.minPoint.y + bb.maxPoint.y) / 2
                cz = (bb.minPoint.z + bb.maxPoint.z) / 2
                origin = adsk.core.Point3D.create(cx, cy, cz)
                if dot > -0.9999:
                    axis = normal.crossProduct(target)
                    axis.normalize()
                    angle = math.acos(max(-1.0, min(1.0, dot)))
                else:
                    axis = adsk.core.Vector3D.create(1, 0, 0)
                    angle = math.pi
                move_rotate(body, angle, axis, origin)
        dz = -body.boundingBox.minPoint.z
        if abs(dz) > 1e-6:
            move_translate(body, 0, 0, dz)
    print('旋转 & Z 对齐完成。')

    # ── 3. 计算行列数（接近正方形）──────────────────────────────
    best_cols, best_ratio = 1, float('inf')
    for c in range(1, n + 1):
        r = math.ceil(n / c)
        ratio = max(r, c) / max(min(r, c), 1)
        if ratio < best_ratio:
            best_ratio = ratio
            best_cols = c
    cols = best_cols
    rows = math.ceil(n / cols)
    print(f'布局: {rows} 行 x {cols} 列')

    # ── 4. 列宽 / 行深 / 偏移 ────────────────────────────────────
    col_widths = [0.0] * cols
    row_depths = [0.0] * rows
    for idx, body in enumerate(visible_bodies):
        r, c = divmod(idx, cols)
        bb = body.boundingBox
        col_widths[c] = max(col_widths[c], bb.maxPoint.x - bb.minPoint.x)
        row_depths[r] = max(row_depths[r], bb.maxPoint.y - bb.minPoint.y)

    col_offsets = [0.0]
    for c in range(cols - 1):
        col_offsets.append(col_offsets[-1] + col_widths[c] + GAP)
    row_offsets = [0.0]
    for r in range(rows - 1):
        row_offsets.append(row_offsets[-1] + row_depths[r] + GAP)

    # ── 5. 平铺移动 ───────────────────────────────────────────────
    for idx, body in enumerate(visible_bodies):
        r, c = divmod(idx, cols)
        mn = body.boundingBox.minPoint
        dx = col_offsets[c] - mn.x
        dy = row_offsets[r] - mn.y
        if abs(dx) > 1e-6 or abs(dy) > 1e-6:
            move_translate(body, dx, dy, 0)
    print('平铺排布完成。')

    # ── 6. 框架范围 & 分隔杆位置 ─────────────────────────────────
    fx0 = min(b.boundingBox.minPoint.x for b in visible_bodies) - FRAME_PAD
    fx1 = max(b.boundingBox.maxPoint.x for b in visible_bodies) + FRAME_PAD
    fy0 = min(b.boundingBox.minPoint.y for b in visible_bodies) - FRAME_PAD
    fy1 = max(b.boundingBox.maxPoint.y for b in visible_bodies) + FRAME_PAD

    col_bar_x = [col_offsets[c] + col_widths[c] + GAP / 2 - hw for c in range(cols - 1)]
    row_bar_y = [row_offsets[r] + row_depths[r] + GAP / 2 - hw for r in range(rows - 1)]

    # ── 7. 拉伸工具：每根杆独立草图 ──────────────────────────────
    extFts   = root.features.extrudeFeatures
    sketches = root.sketches
    xyPlane  = root.xYConstructionPlane
    frame_bodies = []

    def extrude_bar(x0, y0, x1, y1):
        if abs(x1 - x0) < 1e-6 or abs(y1 - y0) < 1e-6:
            return
        sk = sketches.add(xyPlane)
        sk.sketchCurves.sketchLines.addTwoPointRectangle(
            adsk.core.Point3D.create(x0, y0, 0),
            adsk.core.Point3D.create(x1, y1, 0))
        if sk.profiles.count == 0:
            sk.deleteMe()
            return
        ei = extFts.createInput(
            sk.profiles.item(0),
            adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        ei.setDistanceExtent(False, adsk.core.ValueInput.createByReal(BAR_T))
        feat = extFts.add(ei)
        for i in range(feat.bodies.count):
            frame_bodies.append(feat.bodies.item(i))

    # ── 8. 外框四边 + 分隔杆 ─────────────────────────────────────
    extrude_bar(fx0,         fy0, fx0 + BAR_W, fy1)
    extrude_bar(fx1 - BAR_W, fy0, fx1,         fy1)
    extrude_bar(fx0 + BAR_W, fy0, fx1 - BAR_W, fy0 + BAR_W)
    extrude_bar(fx0 + BAR_W, fy1 - BAR_W, fx1 - BAR_W, fy1)
    for bx in col_bar_x:
        extrude_bar(bx, fy0 + BAR_W, bx + BAR_W, fy1 - BAR_W)
    for by in row_bar_y:
        extrude_bar(fx0 + BAR_W, by, fx1 - BAR_W, by + BAR_W)
    print(f'框架杆完成，共 {len(frame_bodies)} 根。')

    # ── 9. 连接杆：按投影面积决定数量，按间距排序取最短 ──────────
    for idx, body in enumerate(visible_bodies):
        r, c = divmod(idx, cols)
        bb   = body.boundingBox
        bx0, bx1 = bb.minPoint.x, bb.maxPoint.x
        by0, by1 = bb.minPoint.y, bb.maxPoint.y
        bcx = (bx0 + bx1) / 2
        bcy = (by0 + by1) / 2

        # 根据 XY 投影面积决定需要几根连接杆
        xy_area = (bx1 - bx0) * (by1 - by0)
        need = 1 if xy_area < AREA_1 else (2 if xy_area < AREA_2 else 3)

        # 该格子四壁内表面位置
        left_wall   = fx0 + BAR_W if c == 0        else col_bar_x[c - 1] + BAR_W
        right_wall  = fx1 - BAR_W if c == cols - 1 else col_bar_x[c]
        bottom_wall = fy0 + BAR_W if r == 0        else row_bar_y[r - 1] + BAR_W
        top_wall    = fy1 - BAR_W if r == rows - 1 else row_bar_y[r]

        # 四个候选方向，只保留有实际间隙的
        candidates = []
        gap_left   = bx0 - left_wall
        gap_right  = right_wall - bx1
        gap_bottom = by0 - bottom_wall
        gap_top    = top_wall - by1

        if gap_left   > 1e-6: candidates.append((gap_left,   left_wall,  bcy-hw, bx0,        bcy+hw))
        if gap_right  > 1e-6: candidates.append((gap_right,  bx1,        bcy-hw, right_wall, bcy+hw))
        if gap_bottom > 1e-6: candidates.append((gap_bottom, bcx-hw, bottom_wall, bcx+hw, by0))
        if gap_top    > 1e-6: candidates.append((gap_top,    bcx-hw, by1,         bcx+hw, top_wall))

        # 按间距从短到长排序，取前 need 个
        candidates.sort(key=lambda x: x[0])
        for _, x0, y0, x1, y1 in candidates[:need]:
            extrude_bar(x0, y0, x1, y1)

    print(f'连接杆完成，框架实体共 {len(frame_bodies)} 个。')

    # ── 10. 合并所有实体 + 框架 ──────────────────────────────────
    tool_col = adsk.core.ObjectCollection.create()
    for body in visible_bodies[1:]:
        tool_col.add(body)
    for fb in frame_bodies:
        tool_col.add(fb)

    comb_inp = root.features.combineFeatures.createInput(
        visible_bodies[0], tool_col)
    comb_inp.operation = adsk.fusion.FeatureOperations.JoinFeatureOperation
    comb_inp.isKeepToolBodies = False
    root.features.combineFeatures.add(comb_inp)

    app.activeViewport.fit()
    print('合并完成！所有实体 + 框架已合并为一个整体。脚本执行成功。')
