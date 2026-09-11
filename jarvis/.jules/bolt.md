## 2026-08-17 - Avoid D3 SVG teardown on hover state updates

**Learning:** Including temporary UI state (such as `hoveredNode` or `hoveredMilestone`) in a `useEffect` dependency array that manages D3 SVG DOM construction causes D3 to completely tear down (`svg.selectAll("*").remove()`) and re-render the entire SVG DOM tree on every hover event (`mouseenter` and `mouseleave`). Since hover tooltips are rendered via React JSX overlay on top of the SVG canvas, the D3 canvas effect only needs to depend on layout dimensions and underlying data models.

**Action:** Ensure D3 simulation/rendering effects in React components only depend on structural properties like `dimensions` and `data`. Manage hover and tooltip overlays in React state without adding hover state variables to the D3 rendering `useEffect` dependencies.

## 2026-08-15 - Memoize Dynamic Render Array Calculations in React

**Learning:** In React components with frequent state updates (like HUD chat inputs or mic volume meters), inline calculations generating random values or dynamic layout heights on every render cause unnecessary recalculations, DOM layout thrashing, and flickering.

**Action:** Always wrap static/mock dataset generator arrays in `useMemo` when rendering UI widgets inside high-frequency reactive components.
