DELETE FROM traces_closedsurface
WHERE trace_id = %s
  AND id IN (
    SELECT inner_surf.id
    FROM traces_closedsurface inner_surf
    JOIN traces_closedsurface outer_surf
      ON outer_surf.trace_id = inner_surf.trace_id
     AND outer_surf.id != inner_surf.id
    WHERE inner_surf.trace_id = %s
      AND ST_Within(inner_surf.polygon, outer_surf.polygon)
  )
